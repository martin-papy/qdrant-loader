"""Code-specific chunking strategy for programming languages."""

import ast
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import structlog

# Tree-sitter imports with error handling
try:
    from tree_sitter_languages import get_language, get_parser

    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    get_language = None
    get_parser = None

from qdrant_loader.config import Settings
from qdrant_loader.core.chunking.strategy.base_strategy import BaseChunkingStrategy
from qdrant_loader.core.chunking.progress_tracker import ChunkingProgressTracker
from qdrant_loader.core.document import Document

logger = structlog.get_logger(__name__)

# Performance constants - Universal limits for all code files
MAX_FILE_SIZE_FOR_AST = (
    75_000  # 75KB limit for AST parsing (balanced for all languages)
)
MAX_ELEMENTS_TO_PROCESS = 800  # Limit number of elements to prevent timeouts
CHUNK_SIZE_THRESHOLD = 40_000  # Files larger than this use simple chunking
MAX_RECURSION_DEPTH = 8  # Limit AST recursion depth
MAX_ELEMENT_SIZE = 20_000  # Skip individual elements larger than this


class CodeElementType(Enum):
    """Types of code elements."""

    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    PROPERTY = "property"
    VARIABLE = "variable"
    IMPORT = "import"
    COMMENT = "comment"
    DOCSTRING = "docstring"
    DECORATOR = "decorator"
    CONSTANT = "constant"
    INTERFACE = "interface"
    ENUM = "enum"
    STRUCT = "struct"
    NAMESPACE = "namespace"
    PACKAGE = "package"


@dataclass
class CodeElement:
    """Represents a code element with its metadata."""

    name: str
    element_type: CodeElementType
    content: str
    start_line: int
    end_line: int
    level: int = 0
    parent: Optional["CodeElement"] = None
    children: list["CodeElement"] = field(default_factory=list)
    docstring: str | None = None
    decorators: list[str] = field(default_factory=list)
    parameters: list[str] = field(default_factory=list)
    return_type: str | None = None
    visibility: str = "public"  # public, private, protected
    is_async: bool = False
    is_static: bool = False
    is_abstract: bool = False
    complexity: int = 0  # Cyclomatic complexity
    dependencies: list[str] = field(default_factory=list)

    def add_child(self, child: "CodeElement"):
        """Add a child element."""
        self.children.append(child)
        child.parent = self


class CodeChunkingStrategy(BaseChunkingStrategy):
    """Strategy for chunking code files based on programming language structure.

    This strategy uses AST parsing (primarily tree-sitter) to split code files into
    chunks based on semantic code elements, preserving the code structure and hierarchy.
    """

    def __init__(self, settings: Settings):
        """Initialize the code chunking strategy.

        Args:
            settings: Configuration settings
        """
        super().__init__(settings)
        self.logger = logger
        self.progress_tracker = ChunkingProgressTracker(logger)

        # Language detection patterns
        self.language_patterns = {
            ".py": "python",
            ".pyx": "python",
            ".pyi": "python",
            ".java": "java",
            ".js": "javascript",
            ".jsx": "javascript",
            ".mjs": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".go": "go",
            ".rs": "rust",
            ".cpp": "cpp",
            ".cc": "cpp",
            ".cxx": "cpp",
            ".c": "c",
            ".h": "c",
            ".cs": "c_sharp",
            ".php": "php",
            ".rb": "ruby",
            ".kt": "kotlin",
            ".scala": "scala",
            ".swift": "swift",
            ".dart": "dart",
        }

        # Cache for Tree-sitter parsers
        self._parsers = {}

        # Check tree-sitter availability
        if not TREE_SITTER_AVAILABLE:
            self.logger.warning("Tree-sitter not available, will use fallback parsing")

    def _detect_language(self, file_path: str, content: str) -> str:
        """Detect programming language from file extension.

        Args:
            file_path: Path to the file
            content: File content (for future content-based detection)

        Returns:
            Detected language name or "unknown"
        """
        # Get file extension
        ext = f".{file_path.lower().split('.')[-1]}" if "." in file_path else ""

        return self.language_patterns.get(ext, "unknown")

    def _get_tree_sitter_parser(self, language: str):
        """Get or create a Tree-sitter parser for the given language.

        Args:
            language: Tree-sitter language name

        Returns:
            Tree-sitter parser or None if not available
        """
        if not TREE_SITTER_AVAILABLE or get_parser is None:
            return None

        if language in self._parsers:
            return self._parsers[language]

        try:
            parser = get_parser(language)
            self._parsers[language] = parser
            return parser
        except Exception as e:
            self.logger.warning(f"Failed to get Tree-sitter parser for {language}: {e}")
            return None

    def _parse_with_tree_sitter(self, content: str, language: str) -> list[CodeElement]:
        """Parse code using Tree-sitter AST.

        Args:
            content: Source code content
            language: Programming language

        Returns:
            List of code elements
        """
        # Performance check: universal size limit for all languages
        if len(content) > MAX_FILE_SIZE_FOR_AST:
            self.logger.info(
                f"{language.title()} file too large for AST parsing ({len(content)} bytes), using fallback"
            )
            return []

        parser = self._get_tree_sitter_parser(language)
        if not parser:
            return []

        try:
            tree = parser.parse(content.encode("utf-8"))
            root_node = tree.root_node

            elements = []
            self._extract_ast_elements(root_node, content, elements, language)

            # Limit number of elements to prevent timeouts (universal limit)
            if len(elements) > MAX_ELEMENTS_TO_PROCESS:
                self.logger.warning(
                    f"Too many {language} elements ({len(elements)}), truncating to {MAX_ELEMENTS_TO_PROCESS}"
                )
                elements = elements[:MAX_ELEMENTS_TO_PROCESS]

            return elements

        except Exception as e:
            self.logger.warning(f"Failed to parse with Tree-sitter for {language}: {e}")
            return []

    def _extract_ast_elements(
        self,
        node,
        content: str,
        elements: list[CodeElement],
        language: str,
        level: int = 0,
    ):
        """Extract code elements from Tree-sitter AST node.

        Args:
            node: Tree-sitter AST node
            content: Source code content
            elements: List to append elements to
            language: Programming language
            level: Nesting level
        """
        # Performance check: limit recursion depth
        if level > MAX_RECURSION_DEPTH:  # Prevent deep recursion
            return

        # Performance check: limit total elements (universal limit)
        if len(elements) >= MAX_ELEMENTS_TO_PROCESS:
            return

        # Define node types that represent code elements for different languages
        element_mappings = {
            "python": {
                "function_definition": CodeElementType.FUNCTION,
                "async_function_definition": CodeElementType.FUNCTION,
                "class_definition": CodeElementType.CLASS,
                "import_statement": CodeElementType.IMPORT,
                "import_from_statement": CodeElementType.IMPORT,
            },
            "java": {
                "method_declaration": CodeElementType.METHOD,
                "constructor_declaration": CodeElementType.METHOD,
                "class_declaration": CodeElementType.CLASS,
                "interface_declaration": CodeElementType.INTERFACE,
                "import_declaration": CodeElementType.IMPORT,
            },
            "javascript": {
                "function_declaration": CodeElementType.FUNCTION,
                "method_definition": CodeElementType.METHOD,
                "class_declaration": CodeElementType.CLASS,
                "import_statement": CodeElementType.IMPORT,
                "variable_declaration": CodeElementType.VARIABLE,
            },
            "typescript": {
                "function_declaration": CodeElementType.FUNCTION,
                "method_definition": CodeElementType.METHOD,
                "class_declaration": CodeElementType.CLASS,
                "interface_declaration": CodeElementType.INTERFACE,
                "import_statement": CodeElementType.IMPORT,
            },
            "go": {
                "function_declaration": CodeElementType.FUNCTION,
                "method_declaration": CodeElementType.METHOD,
                "type_declaration": CodeElementType.STRUCT,
                "import_declaration": CodeElementType.IMPORT,
            },
            "rust": {
                "function_item": CodeElementType.FUNCTION,
                "impl_item": CodeElementType.CLASS,
                "struct_item": CodeElementType.STRUCT,
                "enum_item": CodeElementType.ENUM,
                "trait_item": CodeElementType.INTERFACE,
                "use_declaration": CodeElementType.IMPORT,
            },
            "cpp": {
                "function_definition": CodeElementType.FUNCTION,
                "class_specifier": CodeElementType.CLASS,
                "struct_specifier": CodeElementType.STRUCT,
                "namespace_definition": CodeElementType.NAMESPACE,
                "preproc_include": CodeElementType.IMPORT,
            },
            "c": {
                "function_definition": CodeElementType.FUNCTION,
                "struct_specifier": CodeElementType.STRUCT,
                "preproc_include": CodeElementType.IMPORT,
            },
        }

        # Get element types for this language
        lang_elements = element_mappings.get(language, {})

        # Check if this node represents a code element
        if node.type in lang_elements:
            element_type = lang_elements[node.type]

            # Extract element name
            name = self._extract_element_name(node, language)

            # Get node text
            start_byte = node.start_byte
            end_byte = node.end_byte
            element_content = content[start_byte:end_byte]

            # Skip very large elements to prevent timeouts (universal limit)
            if len(element_content) > MAX_ELEMENT_SIZE:
                self.logger.debug(
                    f"Skipping large {language} element {name} ({len(element_content)} bytes)"
                )
                return

            # Create code element
            element = CodeElement(
                name=name,
                element_type=element_type,
                content=element_content,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                level=level,
            )

            # Extract additional metadata (simplified for performance)
            if element.element_type in [
                CodeElementType.FUNCTION,
                CodeElementType.METHOD,
            ]:
                params_node = node.child_by_field_name("parameters")
                if params_node:
                    element.parameters = self._extract_parameters_from_node(params_node)

            elements.append(element)

            # Process children with increased level (limited depth)
            if level < MAX_RECURSION_DEPTH - 3:  # Leave room for deeper nesting
                for child in node.children:
                    self._extract_ast_elements(
                        child, content, elements, language, level + 1
                    )
        else:
            # Process children at same level (limited depth)
            if level < MAX_RECURSION_DEPTH:  # Use full depth limit
                for child in node.children:
                    self._extract_ast_elements(
                        child, content, elements, language, level
                    )

    def _extract_element_name(self, node, language: str) -> str:
        """Extract the name of a code element from Tree-sitter node.

        Args:
            node: Tree-sitter AST node
            language: Programming language

        Returns:
            Element name or "unknown"
        """
        # Common patterns for finding names in different node types
        name_fields = ["name", "identifier", "field_identifier"]

        for field_name in name_fields:
            name_node = node.child_by_field_name(field_name)
            if name_node:
                return name_node.text.decode("utf-8")

        # Fallback: look for identifier children (limited search)
        for i, child in enumerate(node.children):
            if i > 5:  # Limit search to first few children
                break
            if child.type == "identifier":
                return child.text.decode("utf-8")

        return "unknown"

    def _extract_parameters_from_node(self, params_node) -> list[str]:
        """Extract parameter names from a parameters node.

        Args:
            params_node: Tree-sitter parameters node

        Returns:
            List of parameter names
        """
        parameters = []
        for i, child in enumerate(params_node.children):
            if i > 20:  # Limit to prevent timeouts
                break
            if child.type in ["identifier", "parameter", "typed_parameter"]:
                if child.type == "identifier":
                    parameters.append(child.text.decode("utf-8"))
                else:
                    # Look for identifier within parameter
                    for subchild in child.children:
                        if subchild.type == "identifier":
                            parameters.append(subchild.text.decode("utf-8"))
                            break
        return parameters

    def _parse_python_ast(self, content: str) -> list[CodeElement]:
        """Parse Python code using Python's built-in AST as fallback.

        Args:
            content: Python source code

        Returns:
            List of code elements
        """
        # Performance check: skip AST parsing for very large files
        if len(content) > MAX_FILE_SIZE_FOR_AST:
            self.logger.info(
                f"Python file too large for AST parsing ({len(content)} bytes)"
            )
            return []

        elements = []

        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            self.logger.warning(f"Failed to parse Python AST: {e}")
            return []

        def extract_docstring(node) -> str | None:
            """Extract docstring from a node."""
            if (
                isinstance(node, ast.FunctionDef | ast.ClassDef | ast.AsyncFunctionDef)
                and node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                return node.body[0].value.value
            return None

        def get_decorators(node) -> list[str]:
            """Extract decorator names from a node."""
            decorators = []
            if hasattr(node, "decorator_list"):
                for decorator in node.decorator_list[:5]:  # Limit decorators
                    if isinstance(decorator, ast.Name):
                        decorators.append(decorator.id)
                    elif isinstance(decorator, ast.Attribute):
                        decorators.append(f"{decorator.attr}")
            return decorators

        def get_parameters(node) -> list[str]:
            """Extract parameter names from a function node."""
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                return []

            params = []
            for arg in node.args.args[:20]:  # Limit parameters
                params.append(arg.arg)
            return params

        def visit_node(node, level=0, parent_element=None):
            """Recursively visit AST nodes."""
            # Performance checks
            if level > MAX_RECURSION_DEPTH:  # Limit recursion depth
                return
            if len(elements) >= MAX_ELEMENTS_TO_PROCESS:
                return

            element = None

            if isinstance(node, ast.ClassDef):
                element = CodeElement(
                    name=node.name,
                    element_type=CodeElementType.CLASS,
                    content=ast.get_source_segment(content, node) or "",
                    start_line=node.lineno,
                    end_line=node.end_lineno or node.lineno,
                    level=level,
                    docstring=extract_docstring(node),
                    decorators=get_decorators(node),
                )

            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                element_type = (
                    CodeElementType.METHOD if level > 0 else CodeElementType.FUNCTION
                )
                element = CodeElement(
                    name=node.name,
                    element_type=element_type,
                    content=ast.get_source_segment(content, node) or "",
                    start_line=node.lineno,
                    end_line=node.end_lineno or node.lineno,
                    level=level,
                    docstring=extract_docstring(node),
                    decorators=get_decorators(node),
                    parameters=get_parameters(node),
                    is_async=isinstance(node, ast.AsyncFunctionDef),
                )

            elif isinstance(node, ast.Import | ast.ImportFrom):
                import_names = []
                if isinstance(node, ast.Import):
                    import_names = [
                        alias.name for alias in node.names[:10]
                    ]  # Limit imports
                else:
                    module = node.module or ""
                    import_names = [
                        f"{module}.{alias.name}" for alias in node.names[:10]
                    ]

                element = CodeElement(
                    name=", ".join(import_names),
                    element_type=CodeElementType.IMPORT,
                    content=ast.get_source_segment(content, node) or "",
                    start_line=node.lineno,
                    end_line=node.end_lineno or node.lineno,
                    level=level,
                    dependencies=import_names,
                )

            if element:
                # Skip very large elements
                if len(element.content) > MAX_ELEMENT_SIZE:
                    return

                if parent_element:
                    parent_element.add_child(element)
                else:
                    elements.append(element)

                # Recursively process children (limited depth)
                if level < MAX_RECURSION_DEPTH - 3:  # Leave room for deeper nesting
                    for child in ast.iter_child_nodes(node):
                        visit_node(child, level + 1, element)
            else:
                # For nodes we don't handle, still process their children (limited depth)
                if level < MAX_RECURSION_DEPTH:  # Use full depth limit
                    for child in ast.iter_child_nodes(node):
                        visit_node(child, level, parent_element)

        # Start processing from the root
        for node in ast.iter_child_nodes(tree):
            visit_node(node)

        return elements

    def _extract_code_metadata(
        self, element: CodeElement, language: str
    ) -> dict[str, Any]:
        """Extract metadata from a code element.

        Args:
            element: The code element to analyze
            language: Programming language

        Returns:
            Dictionary containing element metadata
        """
        metadata = {
            "element_type": element.element_type.value,
            "name": element.name,
            "language": language,
            "start_line": element.start_line,
            "end_line": element.end_line,
            "line_count": element.end_line - element.start_line + 1,
            "level": element.level,
            "visibility": element.visibility,
            "is_async": element.is_async,
            "is_static": element.is_static,
            "is_abstract": element.is_abstract,
            "complexity": element.complexity,
            "has_docstring": element.docstring is not None,
            "docstring_length": len(element.docstring) if element.docstring else 0,
            "parameter_count": len(element.parameters),
            "decorator_count": len(element.decorators),
            "child_count": len(element.children),
            "dependency_count": len(element.dependencies),
        }

        # Add specific metadata based on element type
        if element.element_type in [CodeElementType.FUNCTION, CodeElementType.METHOD]:
            metadata.update(
                {
                    "parameters": element.parameters,
                    "return_type": element.return_type,
                    "decorators": element.decorators,
                }
            )

        if element.element_type == CodeElementType.CLASS:
            metadata.update(
                {
                    "method_count": len(
                        [
                            c
                            for c in element.children
                            if c.element_type == CodeElementType.METHOD
                        ]
                    ),
                    "property_count": len(
                        [
                            c
                            for c in element.children
                            if c.element_type == CodeElementType.PROPERTY
                        ]
                    ),
                }
            )

        if element.element_type == CodeElementType.IMPORT:
            metadata.update({"dependencies": element.dependencies})

        # Add parent context
        if element.parent:
            metadata.update(
                {
                    "parent_name": element.parent.name,
                    "parent_type": element.parent.element_type.value,
                    "parent_level": element.parent.level,
                }
            )

        return metadata

    def _merge_small_elements(
        self, elements: list[CodeElement], min_size: int = 200
    ) -> list[CodeElement]:
        """Merge small code elements to create more meaningful chunks.

        Args:
            elements: List of code elements
            min_size: Minimum size for standalone elements

        Returns:
            List of merged elements
        """
        if not elements:
            return []

        merged = []
        current_group = []
        current_size = 0

        for element in elements:
            element_size = len(element.content)

            # If element is large enough or is a significant code structure, keep it separate
            if (
                element_size >= min_size
                or element.element_type
                in [CodeElementType.CLASS, CodeElementType.FUNCTION]
                or (
                    element.element_type == CodeElementType.METHOD
                    and element_size > 100
                )
            ):
                # First, add any accumulated small elements
                if current_group:
                    merged_element = self._create_merged_element(current_group)
                    merged.append(merged_element)
                    current_group = []
                    current_size = 0

                # Add the large element
                merged.append(element)
            else:
                # Accumulate small elements
                current_group.append(element)
                current_size += element_size

                # If accumulated size is large enough, create a merged element
                if current_size >= min_size:
                    merged_element = self._create_merged_element(current_group)
                    merged.append(merged_element)
                    current_group = []
                    current_size = 0

        # Handle remaining small elements
        if current_group:
            merged_element = self._create_merged_element(current_group)
            merged.append(merged_element)

        return merged

    def _create_merged_element(self, elements: list[CodeElement]) -> CodeElement:
        """Create a merged element from a list of small elements.

        Args:
            elements: List of elements to merge

        Returns:
            Merged code element
        """
        if not elements:
            raise ValueError("Cannot merge empty list of elements")

        if len(elements) == 1:
            return elements[0]

        # Create merged element
        merged_content = "\n\n".join(element.content for element in elements)
        merged_names = [element.name for element in elements]

        merged_element = CodeElement(
            name=f"merged_({', '.join(merged_names[:3])}{'...' if len(merged_names) > 3 else ''})",
            element_type=CodeElementType.MODULE,  # Use module as generic container
            content=merged_content,
            start_line=elements[0].start_line,
            end_line=elements[-1].end_line,
            level=min(element.level for element in elements),
        )

        # Merge dependencies
        all_dependencies = []
        for element in elements:
            all_dependencies.extend(element.dependencies)
        merged_element.dependencies = list(set(all_dependencies))

        return merged_element

    def _split_text(self, content: str) -> list[dict[str, Any]]:
        """Split code content into chunks based on programming language structure.

        Args:
            content: The code content to split

        Returns:
            List of dictionaries with chunk content and metadata
        """
        # This method is required by the base class but not used in our implementation
        # We override chunk_document instead
        return [{"content": content, "metadata": {"element_type": "unknown"}}]

    def chunk_document(self, document: Document) -> list[Document]:
        """Chunk a code document using AST parsing.

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

        try:
            # Detect language from file path first for language-specific optimizations
            file_path = document.metadata.get("file_name", "") or document.source
            language = self._detect_language(file_path, document.content)

            # Performance check: universal threshold for all code files
            if len(document.content) > CHUNK_SIZE_THRESHOLD:
                self.progress_tracker.log_fallback(
                    document.id,
                    f"Large {language} file ({len(document.content)} bytes)",
                )
                return self._fallback_chunking(document)

            self.logger.debug(f"Detected language: {language}")

            # Parse code structure using AST
            elements = []
            parsing_method = "unknown"

            if language == "python":
                # Try Python AST first for Python files
                self.logger.debug("Parsing Python with built-in AST")
                elements = self._parse_python_ast(document.content)
                parsing_method = "python_ast"

                # Fallback to tree-sitter if Python AST fails
                if not elements and TREE_SITTER_AVAILABLE:
                    self.logger.debug("Falling back to Tree-sitter for Python")
                    elements = self._parse_with_tree_sitter(document.content, language)
                    parsing_method = "tree_sitter"
            elif language != "unknown" and TREE_SITTER_AVAILABLE:
                # Use tree-sitter for other supported languages
                self.logger.debug(f"Parsing {language} with Tree-sitter")
                elements = self._parse_with_tree_sitter(document.content, language)
                parsing_method = "tree_sitter"

            if not elements:
                self.progress_tracker.log_fallback(
                    document.id, f"No {language} elements found"
                )
                return self._fallback_chunking(document)

            # Merge small elements to optimize chunk size
            final_elements = self._merge_small_elements(elements)
            if len(final_elements) > 100:  # Limit total chunks
                final_elements = final_elements[:100]

            # Create chunked documents
            chunked_docs = []
            for i, element in enumerate(final_elements):
                self.logger.debug(
                    f"Processing element {i+1}/{len(final_elements)}",
                    extra={
                        "element_name": element.name,
                        "element_type": element.element_type.value,
                        "content_size": len(element.content),
                    },
                )

                # Create chunk document with optimized metadata processing
                chunk_doc = self._create_chunk_document(
                    original_doc=document,
                    chunk_content=element.content,
                    chunk_index=i,
                    total_chunks=len(final_elements),
                    skip_nlp=False,
                )

                # Add code-specific metadata
                code_metadata = self._extract_code_metadata(element, language)
                code_metadata["parsing_method"] = parsing_method
                code_metadata["chunking_strategy"] = "code"
                code_metadata["parent_document_id"] = document.id
                chunk_doc.metadata.update(code_metadata)

                chunked_docs.append(chunk_doc)

            # Finish progress tracking
            self.progress_tracker.finish_chunking(
                document.id, len(chunked_docs), f"code ({language})"
            )
            return chunked_docs

        except Exception as e:
            self.progress_tracker.log_error(document.id, str(e))
            # Fallback to default chunking
            self.progress_tracker.log_fallback(
                document.id, f"Code parsing failed: {str(e)}"
            )
            return self._fallback_chunking(document)

    def _fallback_chunking(self, document: Document) -> list[Document]:
        """Fallback to simple text-based chunking when AST parsing fails.

        Args:
            document: Document to chunk

        Returns:
            List of chunked documents
        """
        self.logger.warning("Falling back to simple text chunking for code document")

        # Use simple line-based splitting for code (optimized)
        lines = document.content.split("\n")
        chunks = []
        current_chunk = []
        current_size = 0

        for line in lines:
            line_size = len(line) + 1  # +1 for newline

            if current_size + line_size > self.chunk_size and current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = [line]
                current_size = line_size
            else:
                current_chunk.append(line)
                current_size += line_size

        # Add remaining lines
        if current_chunk:
            chunks.append("\n".join(current_chunk))

        # Create chunk documents (limited)
        chunked_docs = []
        for i, chunk_content in enumerate(chunks[:50]):  # Limit chunks
            chunk_doc = self._create_chunk_document(
                original_doc=document,
                chunk_content=chunk_content,
                chunk_index=i,
                total_chunks=len(chunks),
            )

            chunk_doc.id = Document.generate_chunk_id(document.id, i)
            chunk_doc.metadata["parent_document_id"] = document.id
            chunk_doc.metadata["chunking_method"] = "fallback_text"

            chunked_docs.append(chunk_doc)

        return chunked_docs
