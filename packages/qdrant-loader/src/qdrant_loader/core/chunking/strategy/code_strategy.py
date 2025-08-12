"""Code-specific chunking strategy for programming languages."""

import structlog

from qdrant_loader.config import Settings
from qdrant_loader.core.chunking.progress_tracker import ChunkingProgressTracker
from qdrant_loader.core.chunking.strategy.base_strategy import BaseChunkingStrategy
from qdrant_loader.core.document import Document

from .code import (
    CodeChunkProcessor,
    CodeDocumentParser,
    CodeMetadataExtractor,
    CodeSectionSplitter,
)

logger = structlog.get_logger(__name__)


class CodeChunkingStrategy(BaseChunkingStrategy):
    """Modern code chunking strategy using modular architecture.

    This strategy uses AST parsing (primarily tree-sitter) to split code files into
    chunks based on semantic code elements, preserving the code structure and hierarchy.
    Uses modular components for parsing, splitting, metadata extraction, and chunk processing.
    """

    def __init__(self, settings: Settings):
        """Initialize the code chunking strategy.

        Args:
            settings: Configuration settings
        """
        super().__init__(settings)
        self.logger = logger
        self.progress_tracker = ChunkingProgressTracker(logger)

        # Initialize modular components
        self.document_parser = CodeDocumentParser(settings)
        self.section_splitter = CodeSectionSplitter(settings)
        self.metadata_extractor = CodeMetadataExtractor(settings)
        self.chunk_processor = CodeChunkProcessor(settings)

        # Code-specific configuration
        self.code_config = settings.global_config.chunking.strategies.code
        self.chunk_size_threshold = getattr(
            self.code_config, "max_file_size_for_ast", 40000
        )

        logger.info(
            "CodeChunkingStrategy initialized with modular architecture",
            extra={
                "chunk_size": settings.global_config.chunking.chunk_size,
                "chunk_overlap": settings.global_config.chunking.chunk_overlap,
                "max_file_size_for_ast": self.code_config.max_file_size_for_ast,
                "enable_ast_parsing": self.code_config.enable_ast_parsing,
                "enable_dependency_analysis": self.code_config.enable_dependency_analysis,
                "chunking_method": "intelligent_ast_parsing",
            },
        )

    def chunk_document(self, document: Document) -> list[Document]:
        """Chunk a code document using modern modular approach.

        Args:
            document: Document to chunk

        Returns:
            List of chunked documents
        """
        file_name = (
            document.metadata.get("file_name")
            or document.metadata.get("original_filename")
            or document.title
            or f"{document.source_type}:{document.source}"
        )

        # Start progress tracking
        self.progress_tracker.start_chunking(
            document.id,
            document.source,
            document.source_type,
            len(document.content),
            file_name,
        )

        # Provide user guidance on expected chunk count
        estimated_chunks = self.chunk_processor.estimate_chunk_count(document.content)
        logger.info(
            f"Processing code document: {document.title} ({len(document.content):,} chars)",
            extra={
                "estimated_chunks": estimated_chunks,
                "chunk_size": self.settings.global_config.chunking.chunk_size,
                "max_chunks_allowed": self.settings.global_config.chunking.max_chunks_per_document,
                "file_type": "code",
            },
        )

        try:
            # Parse document structure first
            logger.debug("Analyzing code document structure")
            document_structure = self.document_parser.parse_document_structure(
                document.content
            )

            # Split content into intelligent sections using the section splitter
            logger.debug("Splitting code into semantic sections")
            chunks_metadata = self.section_splitter.split_sections(
                document.content, document
            )

            if not chunks_metadata:
                self.progress_tracker.finish_chunking(document.id, 0, "code")
                return []

            # Apply configuration-driven safety limit
            max_chunks = self.settings.global_config.chunking.max_chunks_per_document
            if len(chunks_metadata) > max_chunks:
                logger.warning(
                    f"Code document generated {len(chunks_metadata)} chunks, limiting to {max_chunks} per config. "
                    f"Consider increasing max_chunks_per_document in config or using larger chunk_size. "
                    f"Document: {document.title}"
                )
                chunks_metadata = chunks_metadata[:max_chunks]

            # Create chunk documents
            chunked_docs = []
            for i, chunk_meta in enumerate(chunks_metadata):
                chunk_content = chunk_meta["content"]
                logger.debug(
                    f"Processing code chunk {i+1}/{len(chunks_metadata)}",
                    extra={
                        "chunk_size": len(chunk_content),
                        "element_type": chunk_meta.get("element_type", "unknown"),
                        "language": chunk_meta.get("language", "unknown"),
                    },
                )

                # Add document structure info to chunk metadata
                chunk_meta.update(
                    {
                        "document_structure": document_structure,
                        "chunking_strategy": "code_modular",
                    }
                )

                # Enhanced: Use hierarchical metadata extraction
                enriched_metadata = (
                    self.metadata_extractor.extract_hierarchical_metadata(
                        chunk_content, chunk_meta, document
                    )
                )

                # Create chunk document using the chunk processor
                # Skip NLP for large code chunks or generated code
                skip_nlp, skip_reason = (
                    self.chunk_processor.should_skip_semantic_analysis(
                        chunk_content, enriched_metadata
                    )
                )

                chunk_doc = self.chunk_processor.create_chunk_document(
                    original_doc=document,
                    chunk_content=chunk_content,
                    chunk_index=i,
                    total_chunks=len(chunks_metadata),
                    chunk_metadata=enriched_metadata,
                    skip_nlp=skip_nlp,
                )

                chunked_docs.append(chunk_doc)

            # Finish progress tracking
            avg_chunk_size = (
                sum(len(doc.content) for doc in chunked_docs) // len(chunked_docs)
                if chunked_docs
                else 0
            )
            self.progress_tracker.finish_chunking(
                document.id, len(chunked_docs), "code_modular"
            )

            logger.info(
                "Successfully chunked code document with modular architecture",
                extra={
                    "document_id": document.id,
                    "num_chunks": len(chunked_docs),
                    "avg_chunk_size": avg_chunk_size,
                    "strategy": "code_modular",
                },
            )

            return chunked_docs

        except Exception as e:
            self.progress_tracker.log_error(document.id, str(e))
            logger.error(f"Code chunking failed: {e}", exc_info=True)
            # Fallback to default chunking
            self.progress_tracker.log_fallback(
                document.id, f"Code parsing failed: {str(e)}"
            )
            return self._fallback_chunking(document)

    def _fallback_chunking(self, document: Document) -> list[Document]:
        """Fallback chunking using simple text-based approach.

        Args:
            document: Document to chunk

        Returns:
            List of chunked documents using fallback approach
        """
        logger.info(
            f"Using fallback chunking for large code document: {document.title}"
        )

        # Use the section splitter's fallback method
        fallback_sections = self.section_splitter._fallback_text_split(document.content)

        # Create chunk documents
        chunked_docs = []
        for i, section in enumerate(fallback_sections):
            chunk_content = section["content"]
            chunk_metadata = section["metadata"]

            # Add fallback-specific metadata
            chunk_metadata.update(
                {
                    "chunking_strategy": "code_fallback",
                    "fallback_reason": "file_too_large",
                }
            )

            # Create chunk document
            chunk_doc = self.chunk_processor.create_chunk_document(
                original_doc=document,
                chunk_content=chunk_content,
                chunk_index=i,
                total_chunks=len(fallback_sections),
                chunk_metadata=chunk_metadata,
                skip_nlp=True,  # Skip NLP for fallback chunks
            )

            chunked_docs.append(chunk_doc)

        return chunked_docs

    def shutdown(self):
        """Clean up resources used by the code chunking strategy."""
        logger.debug("Shutting down CodeChunkingStrategy")

        # Clean up document parser resources
        if hasattr(self.document_parser, "_parsers"):
            self.document_parser._parsers.clear()

        # No additional cleanup needed for other components
        logger.debug("CodeChunkingStrategy shutdown complete")
