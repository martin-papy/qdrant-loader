"""Code document parser for AST analysis and language detection."""

from typing import Any

import structlog

# Tree-sitter imports with error handling
try:
    from tree_sitter_languages import get_parser

    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    get_parser = None

from qdrant_loader.core.chunking.strategy.base.document_parser import BaseDocumentParser
from qdrant_loader.core.chunking.strategy.code.parser.common import (
    CodeElement,  # re-export for backward compatibility
)
from qdrant_loader.core.chunking.strategy.code.parser.python_ast import parse_python_ast
from qdrant_loader.core.chunking.strategy.code.parser.tree_sitter import (
    extract_tree_sitter_elements,
)

logger = structlog.get_logger(__name__)

# Performance constants - Universal limits for all code files
MAX_FILE_SIZE_FOR_AST = 75_000  # 75KB limit for AST parsing
MAX_ELEMENTS_TO_PROCESS = 800  # Limit number of elements to prevent timeouts
MAX_RECURSION_DEPTH = 8  # Limit AST recursion depth
MAX_ELEMENT_SIZE = 20_000  # Skip individual elements larger than this


class CodeDocumentParser(BaseDocumentParser):
    """Parser for code documents with AST analysis and language detection."""

    def __init__(self, settings):
        self.settings = settings
        self.logger = logger
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
        self._parsers = {}
        if not TREE_SITTER_AVAILABLE:
            self.logger.warning("Tree-sitter not available, will use fallback parsing")

    def parse_document_structure(self, content: str) -> dict[str, Any]:
        lines = content.split("\n")
        non_empty_lines = [line for line in lines if line.strip()]
        structure = {
            "total_lines": len(lines),
            "non_empty_lines": len(non_empty_lines),
            "blank_lines": len(lines) - len(non_empty_lines),
            "avg_line_length": (
                sum(len(line) for line in lines) / len(lines) if lines else 0
            ),
            "max_line_length": max(len(line) for line in lines) if lines else 0,
            "structure_type": "code",
            "has_comments": any(
                line.strip().startswith(("#", "//", "/*", "--")) for line in lines
            ),
            "has_docstrings": '"""' in content or "'''" in content,
            "complexity_indicators": {
                "if_statements": content.count("if "),
                "loop_statements": content.count("for ") + content.count("while "),
                "function_definitions": content.count("def ")
                + content.count("function "),
                "class_definitions": content.count("class "),
            },
        }
        return structure

    def extract_section_metadata(self, element: CodeElement) -> dict[str, Any]:
        metadata = {
            "element_type": element.element_type.value,
            "element_name": element.name,
            "start_line": element.start_line,
            "end_line": element.end_line,
            "line_count": element.end_line - element.start_line + 1,
            "level": element.level,
            "visibility": element.visibility,
            "is_async": element.is_async,
            "is_static": element.is_static,
            "is_abstract": element.is_abstract,
            "complexity": element.complexity,
            "has_docstring": bool(element.docstring),
            "decorator_count": len(element.decorators),
            "parameter_count": len(element.parameters),
            "dependency_count": len(element.dependencies),
            "child_count": len(element.children),
        }
        if element.docstring:
            metadata["docstring_length"] = len(element.docstring)
        if element.decorators:
            metadata["decorators"] = element.decorators
        if element.parameters:
            metadata["parameters"] = element.parameters
        if element.return_type:
            metadata["return_type"] = element.return_type
        if element.dependencies:
            metadata["dependencies"] = element.dependencies
        return metadata

    def detect_language(self, file_path: str, content: str) -> str:
        ext = f".{file_path.lower().split('.')[-1]}" if "." in file_path else ""
        return self.language_patterns.get(ext, "unknown")

    def parse_code_elements(self, content: str, language: str) -> list[CodeElement]:
        if len(content) > MAX_FILE_SIZE_FOR_AST:
            self.logger.info(
                f"{language.title()} file too large for AST parsing ({len(content)} bytes), skipping"
            )
            return []

        elements: list[CodeElement] = []
        if language == "python":
            self.logger.debug("Parsing Python with built-in AST")
            elements = parse_python_ast(
                content, max_elements_to_process=MAX_ELEMENTS_TO_PROCESS
            )
            if not elements and TREE_SITTER_AVAILABLE:
                self.logger.debug("Falling back to Tree-sitter for Python")
                elements = self._parse_with_tree_sitter(content, language)
        elif language != "unknown" and TREE_SITTER_AVAILABLE:
            self.logger.debug(f"Parsing {language} with Tree-sitter")
            elements = self._parse_with_tree_sitter(content, language)
        return elements

    def _get_tree_sitter_parser(self, language: str):
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
        parser = self._get_tree_sitter_parser(language)
        if not parser:
            return []
        try:
            tree = parser.parse(content.encode("utf-8"))
            root_node = tree.root_node
            elements = extract_tree_sitter_elements(
                root_node,
                content.encode("utf-8"),
                language=language,
                max_recursion_depth=MAX_RECURSION_DEPTH,
                max_element_size=MAX_ELEMENT_SIZE,
            )
            return elements[:MAX_ELEMENTS_TO_PROCESS]
        except Exception as e:
            self.logger.warning(
                f"Tree-sitter parsing failed for {language}: {e}. Using fallback."
            )
            return []
