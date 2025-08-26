from __future__ import annotations

from typing import Any

from qdrant_loader.core.chunking.strategy.code.parser.common import (
    CodeElement,
    CodeElementType,
)


def extract_tree_sitter_elements(
    root_node: Any,
    content_bytes: bytes,
    *,
    language: str,
    max_recursion_depth: int,
    max_element_size: int,
) -> list[CodeElement]:
    elements: list[CodeElement] = []

    def _walk(node, level: int = 0):
        if level > max_recursion_depth:
            return
        for child in getattr(node, "children", []):
            try:
                start_line = child.start_point[0] + 1
                end_line = child.end_point[0] + 1
            except Exception:
                continue
            if end_line - start_line > max_element_size:
                continue
            try:
                snippet = content_bytes[child.start_byte : child.end_byte].decode(
                    "utf-8", errors="ignore"
                )
            except Exception:
                snippet = ""
            if not snippet.strip():
                continue
            elem_type = (
                CodeElementType.FUNCTION
                if getattr(child, "type", "")
                in ("function_declaration", "method_definition")
                else CodeElementType.MODULE
            )
            element = CodeElement(
                name=getattr(child, "field_name", None)
                or getattr(child, "type", "node"),
                element_type=elem_type,
                content=snippet,
                start_line=start_line,
                end_line=end_line,
                level=level,
            )
            elements.append(element)
            _walk(child, level + 1)

    _walk(root_node, 0)
    return elements
