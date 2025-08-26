from __future__ import annotations

import re


def calculate_doc_coverage(content: str) -> dict[str, float | int | bool]:
    function_count = len(re.findall(r"^\s*def\s+\w+", content, re.MULTILINE))
    function_count += len(re.findall(r"^\s*function\s+\w+", content, re.MULTILINE))

    class_count = len(re.findall(r"^\s*class\s+\w+", content, re.MULTILINE))

    docstring_count = content.count('"""') // 2 + content.count("'''") // 2

    comment_lines = len(
        [
            line
            for line in content.split("\n")
            if line.strip().startswith(("#", "//", "/*"))
        ]
    )

    total_elements = function_count + class_count
    doc_coverage = (docstring_count / total_elements * 100) if total_elements > 0 else 0

    return {
        "total_functions": function_count,
        "total_classes": class_count,
        "documented_elements": docstring_count,
        "comment_lines": comment_lines,
        "documentation_coverage_percent": doc_coverage,
        "has_module_docstring": content.strip().startswith('"""')
        or content.strip().startswith("'''"),
        "avg_comment_density": (
            comment_lines / len(content.split("\n")) if content else 0
        ),
    }
