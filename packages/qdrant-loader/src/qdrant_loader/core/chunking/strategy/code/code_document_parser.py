"""Code document parser for AST analysis and language detection."""

import ast
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog

# Tree-sitter imports with error handling
try:
    from tree_sitter_languages import get_parser
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    get_parser = None

from qdrant_loader.core.chunking.strategy.base.document_parser import BaseDocumentParser

logger = structlog.get_logger(__name__)

# Performance constants - Universal limits for all code files
MAX_FILE_SIZE_FOR_AST = 75_000  # 75KB limit for AST parsing
MAX_ELEMENTS_TO_PROCESS = 800  # Limit number of elements to prevent timeouts
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
    children: List["CodeElement"] = field(default_factory=list)
    docstring: str = None
    decorators: List[str] = field(default_factory=list)
    parameters: List[str] = field(default_factory=list)
    return_type: str = None
    visibility: str = "public"  # public, private, protected
    is_async: bool = False
    is_static: bool = False
    is_abstract: bool = False
    complexity: int = 0  # Cyclomatic complexity
    dependencies: List[str] = field(default_factory=list)
    
    def add_child(self, child: "CodeElement"):
        """Add a child element."""
        self.children.append(child)
        child.parent = self


class CodeDocumentParser(BaseDocumentParser):
    """Parser for code documents with AST analysis and language detection."""
    
    def __init__(self, settings):
        """Initialize the code document parser.
        
        Args:
            settings: Configuration settings
        """
        self.settings = settings
        self.logger = logger
        
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
    
    def parse_document_structure(self, content: str) -> Dict[str, Any]:
        """Parse code document structure and extract programming language information.
        
        Args:
            content: Source code content
            
        Returns:
            Dictionary containing code document structure information
        """
        # For base analysis, we return general structure info
        lines = content.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        # Basic code metrics
        structure = {
            "total_lines": len(lines),
            "non_empty_lines": len(non_empty_lines),
            "blank_lines": len(lines) - len(non_empty_lines),
            "avg_line_length": sum(len(line) for line in lines) / len(lines) if lines else 0,
            "max_line_length": max(len(line) for line in lines) if lines else 0,
            "structure_type": "code",
            "has_comments": any(line.strip().startswith(('#', '//', '/*', '--')) for line in lines),
            "has_docstrings": '"""' in content or "'''" in content,
            "complexity_indicators": {
                "if_statements": content.count('if '),
                "loop_statements": content.count('for ') + content.count('while '),
                "function_definitions": content.count('def ') + content.count('function '),
                "class_definitions": content.count('class '),
            }
        }
        
        return structure
    
    def extract_section_metadata(self, element: CodeElement) -> Dict[str, Any]:
        """Extract metadata from a code element.
        
        Args:
            element: Code element to extract metadata from
            
        Returns:
            Dictionary containing element metadata
        """
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
            "child_count": len(element.children)
        }
        
        # Add optional fields if present
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
    
    def parse_code_elements(self, content: str, language: str) -> List[CodeElement]:
        """Parse code content into structured elements using AST.
        
        Args:
            content: Source code content
            language: Programming language
            
        Returns:
            List of code elements
        """
        # Performance check: universal size limit for all languages
        if len(content) > MAX_FILE_SIZE_FOR_AST:
            self.logger.info(
                f"{language.title()} file too large for AST parsing ({len(content)} bytes), skipping"
            )
            return []
        
        elements = []
        
        # Try language-specific parsing
        if language == "python":
            # Try Python AST first for Python files
            self.logger.debug("Parsing Python with built-in AST")
            elements = self._parse_python_ast(content)
            
            # Fallback to tree-sitter if Python AST fails
            if not elements and TREE_SITTER_AVAILABLE:
                self.logger.debug("Falling back to Tree-sitter for Python")
                elements = self._parse_with_tree_sitter(content, language)
                
        elif language != "unknown" and TREE_SITTER_AVAILABLE:
            # Use tree-sitter for other supported languages
            self.logger.debug(f"Parsing {language} with Tree-sitter")
            elements = self._parse_with_tree_sitter(content, language)
        
        return elements
    
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
    
    def _parse_with_tree_sitter(self, content: str, language: str) -> List[CodeElement]:
        """Parse code using Tree-sitter AST.
        
        Args:
            content: Source code content
            language: Programming language
            
        Returns:
            List of code elements
        """
        parser = self._get_tree_sitter_parser(language)
        if not parser:
            return []
        
        try:
            tree = parser.parse(content.encode("utf-8"))
            root_node = tree.root_node
            
            elements = []
            self._extract_tree_sitter_elements(
                root_node, content.encode("utf-8"), elements, language, level=0
            )
            
            # Limit elements to prevent timeouts
            if len(elements) > MAX_ELEMENTS_TO_PROCESS:
                self.logger.warning(
                    f"Too many elements ({len(elements)}), limiting to {MAX_ELEMENTS_TO_PROCESS}"
                )
                elements = elements[:MAX_ELEMENTS_TO_PROCESS]
            
            return elements
            
        except Exception as e:
            self.logger.warning(f"Tree-sitter parsing failed for {language}: {e}")
            return []
    
    def _extract_tree_sitter_elements(
        self, node, content_bytes: bytes, elements: List[CodeElement], 
        language: str, level: int = 0
    ):
        """Extract elements from Tree-sitter AST node.
        
        Args:
            node: Tree-sitter node
            content_bytes: Source code as bytes
            elements: List to append elements to
            language: Programming language
            level: Current nesting level
        """
        if level > MAX_RECURSION_DEPTH:
            return
        
        # Define element type mapping based on node type
        element_type_map = {
            "function_definition": CodeElementType.FUNCTION,
            "method_definition": CodeElementType.METHOD,
            "class_definition": CodeElementType.CLASS,
            "interface_declaration": CodeElementType.INTERFACE,
            "enum_declaration": CodeElementType.ENUM,
            "struct_declaration": CodeElementType.STRUCT,
            "variable_declaration": CodeElementType.VARIABLE,
            "import_statement": CodeElementType.IMPORT,
            "comment": CodeElementType.COMMENT,
        }
        
        # Map node type to code element type
        element_type = element_type_map.get(node.type)
        
        if element_type:
            # Extract element content
            element_content = content_bytes[node.start_byte:node.end_byte].decode("utf-8")
            
            # Skip overly large elements
            if len(element_content) > MAX_ELEMENT_SIZE:
                self.logger.debug(f"Skipping large {node.type} element ({len(element_content)} chars)")
                return
            
            # Extract element name
            element_name = self._extract_element_name(node, content_bytes, language)
            
            # Create code element
            element = CodeElement(
                name=element_name,
                element_type=element_type,
                content=element_content,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                level=level,
            )
            
            # Extract additional metadata
            self._enrich_element_metadata(element, node, content_bytes, language)
            
            elements.append(element)
        
        # Recursively process child nodes
        for child in node.children:
            self._extract_tree_sitter_elements(
                child, content_bytes, elements, language, level + 1
            )
    
    def _extract_element_name(self, node, content_bytes: bytes, language: str) -> str:
        """Extract element name from Tree-sitter node.
        
        Args:
            node: Tree-sitter node
            content_bytes: Source code as bytes
            language: Programming language
            
        Returns:
            Element name or default name
        """
        # Try to find identifier child node
        for child in node.children:
            if child.type == "identifier":
                return content_bytes[child.start_byte:child.end_byte].decode("utf-8")
        
        # Fallback to node type
        return f"unnamed_{node.type}"
    
    def _enrich_element_metadata(
        self, element: CodeElement, node, content_bytes: bytes, language: str
    ):
        """Enrich code element with additional metadata from AST node.
        
        Args:
            element: Code element to enrich
            node: Tree-sitter node
            content_bytes: Source code as bytes
            language: Programming language
        """
        # Extract decorators, parameters, etc. based on language
        if language == "python":
            self._enrich_python_metadata(element, node, content_bytes)
        elif language in ["javascript", "typescript"]:
            self._enrich_javascript_metadata(element, node, content_bytes)
        # Add more language-specific enrichment as needed
    
    def _enrich_python_metadata(self, element: CodeElement, node, content_bytes: bytes):
        """Enrich element with Python-specific metadata."""
        # Look for decorators
        for child in node.children:
            if child.type == "decorator":
                decorator_name = content_bytes[child.start_byte:child.end_byte].decode("utf-8")
                element.decorators.append(decorator_name.strip())
        
        # Check for async
        element.is_async = any(child.type == "async" for child in node.children)
    
    def _enrich_javascript_metadata(self, element: CodeElement, node, content_bytes: bytes):
        """Enrich element with JavaScript/TypeScript-specific metadata."""
        # Check for async
        element.is_async = any(child.type == "async" for child in node.children)
        
        # Check for static
        element.is_static = any(child.type == "static" for child in node.children)
    
    def _parse_python_ast(self, content: str) -> List[CodeElement]:
        """Parse Python code using built-in AST module.
        
        Args:
            content: Python source code
            
        Returns:
            List of code elements
        """
        try:
            tree = ast.parse(content)
            elements = []
            self._extract_ast_elements(tree, content, elements, level=0)
            return elements
            
        except SyntaxError as e:
            self.logger.warning(f"Python AST parsing failed: {e}")
            return []
        except Exception as e:
            self.logger.warning(f"Unexpected error in Python AST parsing: {e}")
            return []
    
    def _extract_ast_elements(
        self, node: ast.AST, content: str, elements: List[CodeElement], level: int = 0
    ):
        """Extract elements from Python AST node.
        
        Args:
            node: AST node
            content: Source code content
            elements: List to append elements to
            level: Current nesting level
        """
        if level > MAX_RECURSION_DEPTH:
            return
        
        lines = content.split('\n')
        
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            element_type = CodeElementType.METHOD if level > 0 else CodeElementType.FUNCTION
            
            # Extract function content
            start_line = node.lineno
            end_line = node.end_lineno or start_line
            element_content = '\n'.join(lines[start_line-1:end_line])
            
            element = CodeElement(
                name=node.name,
                element_type=element_type,
                content=element_content,
                start_line=start_line,
                end_line=end_line,
                level=level,
                is_async=isinstance(node, ast.AsyncFunctionDef),
                parameters=[arg.arg for arg in node.args.args],
                decorators=[self._get_decorator_name(d) for d in node.decorator_list],
            )
            
            # Extract docstring
            if (node.body and isinstance(node.body[0], ast.Expr) 
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)):
                element.docstring = node.body[0].value.value
            
            elements.append(element)
            
        elif isinstance(node, ast.ClassDef):
            start_line = node.lineno
            end_line = node.end_lineno or start_line
            element_content = '\n'.join(lines[start_line-1:end_line])
            
            element = CodeElement(
                name=node.name,
                element_type=CodeElementType.CLASS,
                content=element_content,
                start_line=start_line,
                end_line=end_line,
                level=level,
                decorators=[self._get_decorator_name(d) for d in node.decorator_list],
            )
            
            # Extract docstring
            if (node.body and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)):
                element.docstring = node.body[0].value.value
            
            elements.append(element)
        
        # Recursively process child nodes
        for child in ast.iter_child_nodes(node):
            self._extract_ast_elements(child, content, elements, level + 1)
    
    def _get_decorator_name(self, decorator: ast.AST) -> str:
        """Extract decorator name from AST node.
        
        Args:
            decorator: AST decorator node
            
        Returns:
            Decorator name as string
        """
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return f"{self._get_decorator_name(decorator.value)}.{decorator.attr}"
        elif isinstance(decorator, ast.Call):
            return f"{self._get_decorator_name(decorator.func)}()"
        else:
            return "unknown_decorator" 