from __future__ import annotations

import math


def calculate_complexity_metrics(content: str) -> dict[str, float | int]:
    lines = content.split("\n")
    non_empty_lines = [line for line in lines if line.strip()]

    indicators = [
        "if ",
        "elif ",
        "else:",
        "while ",
        "for ",
        "try:",
        "except:",
        "case ",
        "&&",
        "||",
        "?",
        "and ",
        "or ",
        "switch",
    ]

    cyclomatic_complexity = 1
    for indicator in indicators:
        cyclomatic_complexity += content.lower().count(indicator.lower())

    max_nesting = 0
    current_nesting = 0
    for line in lines:
        stripped = line.strip()
        if any(k in stripped for k in ["if", "for", "while", "try", "def", "class"]):
            current_nesting += 1
            max_nesting = max(max_nesting, current_nesting)
        elif stripped in ["end", "}"] or (
            stripped.startswith("except") or stripped.startswith("finally")
        ):
            current_nesting = max(0, current_nesting - 1)

    return {
        "cyclomatic_complexity": cyclomatic_complexity,
        "lines_of_code": len(non_empty_lines),
        "total_lines": len(lines),
        "nesting_depth": max_nesting,
        "complexity_density": cyclomatic_complexity / max(len(non_empty_lines), 1),
        "maintainability_index": calculate_maintainability_index(content),
    }


def calculate_maintainability_index(content: str) -> float:
    if not content.strip():
        return 50

    lines = content.split("\n")
    non_empty_lines = [line for line in lines if line.strip()]
    loc = len(non_empty_lines)

    complexity = 1
    for indicator in [
        "if ",
        "elif ",
        "else:",
        "while ",
        "for ",
        "try:",
        "except:",
        "case ",
    ]:
        complexity += content.lower().count(indicator.lower())

    operators = len(__import__("re").findall(r"[+\-*/=<>!&|%^~]", content))
    operands = len(__import__("re").findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", content))

    if operands == 0:
        halstead_volume = 0
    else:
        vocabulary = operators + operands
        length = operators + operands
        halstead_volume = length * math.log2(vocabulary) if vocabulary > 1 else 0

    if loc > 0 and halstead_volume > 0:
        mi = (
            171
            - 5.2 * math.log(halstead_volume)
            - 0.23 * complexity
            - 16.2 * math.log(loc)
        )
        return max(0, min(100, mi))

    return 50
