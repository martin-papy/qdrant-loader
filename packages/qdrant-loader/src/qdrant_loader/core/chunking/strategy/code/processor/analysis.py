from __future__ import annotations

from typing import Any


def analyze_code_content(content: str) -> dict[str, Any]:
    lines = content.split("\n")
    non_empty_lines = [line for line in lines if line.strip()]
    comment_lines = [
        line for line in lines if line.strip().startswith(("#", "//", "/*", "--"))
    ]
    return {
        "total_lines": len(lines),
        "code_lines": len(non_empty_lines) - len(comment_lines),
        "comment_lines": len(comment_lines),
        "blank_lines": len(lines) - len(non_empty_lines),
        "comment_ratio": (
            len(comment_lines) / len(non_empty_lines) if non_empty_lines else 0
        ),
        "avg_line_length": (
            sum(len(line) for line in lines) / len(lines) if lines else 0
        ),
        "max_line_length": max(len(line) for line in lines) if lines else 0,
        "indentation_consistency": _check_indentation_consistency(lines),
        "has_documentation": '"""' in content or "'''" in content or "/*" in content,
    }


def _check_indentation_consistency(lines: list[str]) -> bool:
    spaces = sum(1 for line in lines if line.startswith(" "))
    tabs = sum(1 for line in lines if line.startswith("\t"))
    return not (spaces > 0 and tabs > 0)


def extract_language_context(
    content: str, chunk_metadata: dict[str, Any]
) -> dict[str, Any]:
    language = chunk_metadata.get("language", "unknown")
    return {
        "language": language,
        "paradigm": _identify_programming_paradigm(content, language),
        "framework_indicators": _identify_frameworks(content, language),
        "version_indicators": _identify_language_version(content, language),
        "style_conventions": _analyze_style_conventions(content, language),
    }


def _identify_programming_paradigm(content: str, language: str) -> str:
    if language in ["python", "java", "c_sharp", "typescript", "javascript"]:
        return "object_oriented"
    if language in ["c", "cpp", "go", "rust"]:
        return "procedural"
    return "mixed"


def _identify_frameworks(content: str, language: str) -> list[str]:
    lower = content.lower()
    if language in ["python"] and any(
        k in lower for k in ["django", "flask", "fastapi"]
    ):
        return [k for k in ["django", "flask", "fastapi"] if k in lower]
    if language in ["javascript", "typescript"] and any(
        k in lower for k in ["react", "vue", "angular", "next"]
    ):
        return [k for k in ["react", "vue", "angular", "next"] if k in lower]
    return []


def _identify_language_version(content: str, language: str) -> str:
    if language == "python" and (":=" in content or "match " in content):
        return "3.x"
    if language in ["javascript", "typescript"] and any(
        k in content for k in ["=>", "const", "let"]
    ):
        return "ES6+"
    return "unknown"


def _analyze_style_conventions(content: str, language: str) -> dict[str, Any]:
    lines = content.split("\n")
    snake_case = sum(1 for line in lines if "_" in line)
    camel_case = sum(1 for line in lines if any(c.isupper() for c in line.split()))
    return {
        "snake_case_indicators": snake_case,
        "camel_case_indicators": camel_case,
    }
