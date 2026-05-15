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
    content_lines = content.split("\n")

    def add_element(node: ast.AST, elem_type: CodeElementType, level: int) -> bool:
        """Add a code element from an AST node. Returns False if limit reached."""
        if len(elements) >= max_elements_to_process:
            return False
        try:
            start_line: int = node.lineno  # type: ignore[attr-defined]
            end_line: int = node.end_lineno  # type: ignore[attr-defined]
        except AttributeError:
            return True
        snippet = "\n".join(content_lines[start_line - 1 : end_line])
        if not snippet.strip():
            return True
        elements.append(
            CodeElement(
                name=getattr(node, "name", type(node).__name__),
                element_type=elem_type,
                content=snippet,
                start_line=start_line,
                end_line=end_line,
                level=level,
            )
        )
        return True

    def flush_module_group(group: list[ast.AST]) -> bool:
        """Combine consecutive module-level statements into one MODULE element."""
        if not group:
            return True
        try:
            start_line: int = group[0].lineno  # type: ignore[attr-defined]
            end_line: int = group[-1].end_lineno  # type: ignore[attr-defined]
        except AttributeError:
            return True
        snippet = "\n".join(content_lines[start_line - 1 : end_line])
        if not snippet.strip():
            return True
        if len(elements) >= max_elements_to_process:
            return False
        elements.append(
            CodeElement(
                name="module",
                element_type=CodeElementType.MODULE,
                content=snippet,
                start_line=start_line,
                end_line=end_line,
                level=0,
            )
        )
        return True

    # Walk only the top-level statements of the module so we get exactly
    # one element per top-level class / function, with no overlap from
    # nested methods, assignments, or control-flow nodes.
    # Non-class/function statements (imports, constants, if __name__ == ..., etc.)
    # are grouped together and emitted as a MODULE element.
    current_group: list[ast.AST] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            if not flush_module_group(current_group):
                break
            current_group = []
            if not add_element(node, CodeElementType.CLASS, 0):
                break
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not flush_module_group(current_group):
                break
            current_group = []
            if not add_element(node, CodeElementType.FUNCTION, 0):
                break
        else:
            current_group.append(node)

    # Flush any trailing module-level code (e.g. if __name__ == "__main__")
    flush_module_group(current_group)

    return elements
