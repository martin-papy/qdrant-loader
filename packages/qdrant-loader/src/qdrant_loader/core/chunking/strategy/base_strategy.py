"""Base abstract class for chunking strategies."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import tiktoken

from qdrant_loader.config import Settings
from qdrant_loader.core.document import Document
from qdrant_loader.core.text_processing.text_processor import TextProcessor
from qdrant_loader.utils.logging import LoggingConfig

if TYPE_CHECKING:
    from qdrant_loader.config import Settings

logger = LoggingConfig.get_logger(__name__)


class BaseChunkingStrategy(ABC):
    """Base abstract class for all chunking strategies.

    This class defines the interface that all chunking strategies must implement.
    Each strategy should provide its own implementation of how to split documents
    into chunks while preserving their semantic meaning and structure.
    """

    def __init__(
        self,
        settings: "Settings",
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ):
        """Initialize the chunking strategy.

        Args:
            settings: Application settings containing configuration for the strategy
            chunk_size: Maximum number of tokens per chunk (optional, defaults to settings value)
            chunk_overlap: Number of tokens to overlap between chunks (optional, defaults to settings value)
        """
        self.settings = settings
        self.logger = LoggingConfig.get_logger(self.__class__.__name__)

        # Initialize token-based chunking parameters
        self.chunk_size = chunk_size or settings.global_config.chunking.chunk_size
        self.chunk_overlap = (
            chunk_overlap or settings.global_config.chunking.chunk_overlap
        )
        self.tokenizer = settings.global_config.embedding.tokenizer

        # Initialize tokenizer based on configuration
        if self.tokenizer == "none":
            self.encoding = None
        else:
            try:
                self.encoding = tiktoken.get_encoding(self.tokenizer)
            except Exception as e:
                logger.warning(
                    "Failed to initialize tokenizer, falling back to simple character counting",
                    error=str(e),
                    tokenizer=self.tokenizer,
                )
                self.encoding = None

        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("Chunk overlap must be less than chunk size")

        # Initialize text processor
        self.text_processor = TextProcessor(settings)

    def _count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text string."""
        if self.encoding is None:
            # Fallback to character count if no tokenizer is available
            return len(text)
        return len(self.encoding.encode(text))

    def _process_text(self, text: str) -> dict:
        """Process text using the text processor.

        Args:
            text: Text to process

        Returns:
            dict: Processed text features
        """
        return self.text_processor.process_text(text)

    def _should_apply_nlp(
        self, content: str, file_path: str = "", content_type: str = ""
    ) -> bool:
        """Determine if NLP processing should be applied to content.

        Args:
            content: The content to analyze
            file_path: File path for extension-based detection
            content_type: Content type if available

        Returns:
            bool: True if NLP processing would be valuable
        """
        # Skip NLP for very large content (performance)
        if len(content) > 20000:  # 20KB limit
            return False

        # Get file extension
        ext = ""
        if file_path and "." in file_path:
            ext = f".{file_path.lower().split('.')[-1]}"

        # Skip NLP for code files (except comments/docstrings)
        code_extensions = {
            ".py",
            ".pyx",
            ".pyi",
            ".java",
            ".js",
            ".jsx",
            ".mjs",
            ".ts",
            ".tsx",
            ".go",
            ".rs",
            ".cpp",
            ".cc",
            ".cxx",
            ".c",
            ".h",
            ".cs",
            ".php",
            ".rb",
            ".kt",
            ".scala",
            ".swift",
            ".dart",
            ".sh",
            ".bash",
            ".zsh",
            ".sql",
            ".r",
            ".m",
            ".pl",
            ".lua",
            ".vim",
            ".asm",
        }
        if ext in code_extensions:
            return False

        # Skip NLP for structured data files
        structured_extensions = {
            ".json",
            ".xml",
            ".yaml",
            ".yml",
            ".toml",
            ".ini",
            ".cfg",
            ".conf",
            ".csv",
            ".tsv",
            ".log",
            ".properties",
        }
        if ext in structured_extensions:
            return False

        # Skip NLP for binary/encoded content
        binary_extensions = {
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".ppt",
            ".pptx",
            ".zip",
            ".tar",
            ".gz",
            ".bz2",
            ".7z",
            ".rar",
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
            ".svg",
            ".mp3",
            ".mp4",
            ".avi",
            ".mov",
            ".wav",
            ".flac",
        }
        if ext in binary_extensions:
            return False

        # Apply NLP for documentation and text files
        text_extensions = {".md", ".txt", ".rst", ".adoc", ".tex", ".rtf"}
        if ext in text_extensions:
            return True

        # Apply NLP for HTML content (but be selective)
        if ext in {".html", ".htm"} or content_type == "html":
            return True

        # For unknown extensions, check content characteristics
        if not ext:
            # Skip if content looks like code (high ratio of special characters)
            special_chars = sum(1 for c in content if c in "{}[]();,=<>!&|+-*/%^~`")
            if len(content) > 0 and special_chars / len(content) > 0.15:
                return False

            # Skip if content looks like structured data
            if content.strip().startswith(("{", "[", "<")) or "=" in content[:100]:
                return False

        # Default to applying NLP for text-like content
        return True

    def _extract_nlp_worthy_content(self, content: str, element_type: str = "") -> str:
        """Extract only the parts of content that are worth NLP processing.

        For code files, this extracts comments and docstrings.
        For other files, returns the full content.

        Args:
            content: The content to process
            element_type: Type of code element (if applicable)

        Returns:
            str: Content suitable for NLP processing
        """
        # For code elements, only process comments and docstrings
        if element_type in ["comment", "docstring"]:
            return content

        # For other code elements, extract comments
        if element_type in ["function", "method", "class", "module"]:
            return self._extract_comments_and_docstrings(content)

        # For non-code content, return as-is
        return content

    def _extract_comments_and_docstrings(self, code_content: str) -> str:
        """Extract comments and docstrings from code content.

        Args:
            code_content: Code content to extract from

        Returns:
            str: Extracted comments and docstrings
        """
        extracted_text = []
        lines = code_content.split("\n")

        in_multiline_comment = False
        in_docstring = False
        docstring_delimiter = None

        for line in lines:
            stripped = line.strip()

            # Python/Shell style comments
            if stripped.startswith("#"):
                comment = stripped[1:].strip()
                if comment:  # Skip empty comments
                    extracted_text.append(comment)

            # C/Java/JS style single line comments
            elif "//" in stripped:
                comment_start = stripped.find("//")
                comment = stripped[comment_start + 2 :].strip()
                if comment:
                    extracted_text.append(comment)

            # C/Java/JS style multiline comments
            elif "/*" in stripped and not in_multiline_comment:
                in_multiline_comment = True
                comment_start = stripped.find("/*")
                comment = stripped[comment_start + 2 :]
                if "*/" in comment:
                    comment = comment[: comment.find("*/")]
                    in_multiline_comment = False
                comment = comment.strip()
                if comment:
                    extracted_text.append(comment)

            elif in_multiline_comment:
                if "*/" in stripped:
                    comment = stripped[: stripped.find("*/")]
                    in_multiline_comment = False
                else:
                    comment = stripped
                comment = comment.strip("* \t")
                if comment:
                    extracted_text.append(comment)

            # Python docstrings
            elif ('"""' in stripped or "'''" in stripped) and not in_docstring:
                for delimiter in ['"""', "'''"]:
                    if delimiter in stripped:
                        in_docstring = True
                        docstring_delimiter = delimiter
                        start_idx = stripped.find(delimiter)
                        docstring_content = stripped[start_idx + 3 :]

                        # Check if docstring ends on same line
                        if delimiter in docstring_content:
                            end_idx = docstring_content.find(delimiter)
                            docstring_text = docstring_content[:end_idx].strip()
                            if docstring_text:
                                extracted_text.append(docstring_text)
                            in_docstring = False
                            docstring_delimiter = None
                        else:
                            if docstring_content.strip():
                                extracted_text.append(docstring_content.strip())
                        break

            elif in_docstring and docstring_delimiter:
                if docstring_delimiter in stripped:
                    end_idx = stripped.find(docstring_delimiter)
                    docstring_text = stripped[:end_idx].strip()
                    if docstring_text:
                        extracted_text.append(docstring_text)
                    in_docstring = False
                    docstring_delimiter = None
                else:
                    if stripped:
                        extracted_text.append(stripped)

        return "\n".join(extracted_text)

    def _create_chunk_document(
        self,
        original_doc: Document,
        chunk_content: str,
        chunk_index: int,
        total_chunks: int,
        skip_nlp: bool = False,
    ) -> Document:
        """Create a new document for a chunk with enhanced metadata.

        Args:
            original_doc: Original document
            chunk_content: Content of the chunk
            chunk_index: Index of the chunk
            total_chunks: Total number of chunks
            skip_nlp: Whether to skip expensive NLP processing

        Returns:
            Document: New document instance for the chunk
        """
        # Create enhanced metadata
        metadata = original_doc.metadata.copy()
        metadata.update(
            {
                "chunk_index": chunk_index,
                "total_chunks": total_chunks,
            }
        )

        # Smart NLP decision based on content type and characteristics
        file_path = original_doc.metadata.get("file_name", "") or original_doc.source
        content_type = original_doc.content_type or ""
        element_type = metadata.get("element_type", "")

        # For converted files, use the converted content type instead of original file extension
        conversion_method = metadata.get("conversion_method")
        if conversion_method == "markitdown":
            # File was converted to markdown, so treat it as markdown for NLP purposes
            file_path = "converted.md"  # Use .md extension for NLP decision
            content_type = "md"

        should_apply_nlp = (
            not skip_nlp
            and len(chunk_content) <= 10000  # Size limit
            and total_chunks <= 50  # Chunk count limit
            and self._should_apply_nlp(chunk_content, file_path, content_type)
        )

        if not should_apply_nlp:
            # Skip NLP processing
            skip_reason = "performance_optimization"
            if len(chunk_content) > 10000:
                skip_reason = "chunk_too_large"
            elif total_chunks > 50:
                skip_reason = "too_many_chunks"
            elif not self._should_apply_nlp(chunk_content, file_path, content_type):
                skip_reason = "content_type_inappropriate"

            metadata.update(
                {
                    "entities": [],
                    "pos_tags": [],
                    "nlp_skipped": True,
                    "skip_reason": skip_reason,
                }
            )
        else:
            try:
                # For code content, only process comments/docstrings
                nlp_content = self._extract_nlp_worthy_content(
                    chunk_content, element_type
                )

                if nlp_content.strip():
                    # Process the NLP-worthy content
                    processed = self._process_text(nlp_content)
                    metadata.update(
                        {
                            "entities": processed["entities"],
                            "pos_tags": processed["pos_tags"],
                            "nlp_skipped": False,
                            "nlp_content_extracted": len(nlp_content)
                            < len(chunk_content),
                            "nlp_content_ratio": (
                                len(nlp_content) / len(chunk_content)
                                if chunk_content
                                else 0
                            ),
                        }
                    )
                else:
                    # No NLP-worthy content found
                    metadata.update(
                        {
                            "entities": [],
                            "pos_tags": [],
                            "nlp_skipped": True,
                            "skip_reason": "no_nlp_worthy_content",
                        }
                    )
            except Exception as e:
                self.logger.warning(
                    f"NLP processing failed for chunk {chunk_index}: {e}"
                )
                metadata.update(
                    {
                        "entities": [],
                        "pos_tags": [],
                        "nlp_skipped": True,
                        "skip_reason": "nlp_error",
                    }
                )

        return Document(
            content=chunk_content,
            metadata=metadata,
            source=original_doc.source,
            source_type=original_doc.source_type,
            url=original_doc.url,
            title=original_doc.title,
            content_type=original_doc.content_type,
        )

    @abstractmethod
    def chunk_document(self, document: Document) -> list[Document]:
        """Split a document into chunks while preserving metadata.

        This method should:
        1. Split the document content into appropriate chunks
        2. Preserve all metadata from the original document
        3. Add chunk-specific metadata (e.g., chunk index, total chunks)
        4. Return a list of new Document instances

        Args:
            document: The document to chunk

        Returns:
            List of chunked documents with preserved metadata

        Raises:
            NotImplementedError: If the strategy doesn't implement this method
        """
        raise NotImplementedError(
            "Chunking strategy must implement chunk_document method"
        )

    @abstractmethod
    def _split_text(self, text: str) -> list[str]:
        """Split text into chunks based on strategy-specific rules.

        This method should:
        1. Implement the specific chunking logic for the strategy
        2. Return a list of text chunks
        3. Preserve the semantic meaning of the content

        Args:
            text: The text to split into chunks

        Returns:
            List of text chunks

        Raises:
            NotImplementedError: If the strategy doesn't implement this method
        """
        raise NotImplementedError("Chunking strategy must implement _split_text method")
