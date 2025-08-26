from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class CodeElementType(Enum):
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
    name: str
    element_type: CodeElementType
    content: str
    start_line: int
    end_line: int
    level: int = 0
    parent: CodeElement | None = None
    children: list[CodeElement] = field(default_factory=list)
    docstring: str = None
    decorators: list[str] = field(default_factory=list)
    parameters: list[str] = field(default_factory=list)
    return_type: str = None
    visibility: str = "public"
    is_async: bool = False
    is_static: bool = False
    is_abstract: bool = False
    complexity: int = 0
    dependencies: list[str] = field(default_factory=list)

    def add_child(self, child: CodeElement) -> None:
        self.children.append(child)
        child.parent = self
