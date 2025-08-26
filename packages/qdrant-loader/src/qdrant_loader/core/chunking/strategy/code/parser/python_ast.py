from __future__ import annotations

import ast

from qdrant_loader.core.chunking.strategy.code.parser.common import (
    CodeElement,
    CodeElementType,
)


def parse_python_ast(
    content: str,
    *,
    max_elements_to_process: int,
) -> list[CodeElement]:
    try:
        tree = ast.parse(content)
    except Exception:
        return []

    elements: list[CodeElement] = []

    class Visitor(ast.NodeVisitor):
        def __init__(self):
            self.level = 0

        def generic_visit(self, node):
            if len(elements) >= max_elements_to_process:
                return
            node_type = type(node).__name__
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                elem_type = CodeElementType.FUNCTION
            elif isinstance(node, ast.ClassDef):
                elem_type = CodeElementType.CLASS
            else:
                elem_type = CodeElementType.MODULE

            try:
                start_line = getattr(node, "lineno", 1)
                end_line = getattr(node, "end_lineno", start_line)
            except Exception:
                start_line = 1
                end_line = start_line

            snippet_lines = content.split("\n")[start_line - 1 : end_line]
            snippet = "\n".join(snippet_lines)
            if not snippet.strip():
                return

            element = CodeElement(
                name=getattr(node, "name", node_type),
                element_type=elem_type,
                content=snippet,
                start_line=start_line,
                end_line=end_line,
                level=self.level,
            )
            elements.append(element)
            self.level += 1
            super().generic_visit(node)
            self.level = max(0, self.level - 1)

    Visitor().visit(tree)
    return elements
