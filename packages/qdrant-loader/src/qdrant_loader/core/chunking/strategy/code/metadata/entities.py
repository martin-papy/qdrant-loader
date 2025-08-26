from __future__ import annotations

import re


def extract_entities(text: str) -> list[str]:
    entities: list[str] = []

    class_pattern = r"\b(?:class|interface|struct|enum)\s+([A-Z][a-zA-Z0-9_]*)"
    entities.extend(re.findall(class_pattern, text))

    function_patterns = [
        r"\bdef\s+([a-zA-Z_][a-zA-Z0-9_]*)",
        r"\bfunction\s+([a-zA-Z_][a-zA-Z0-9_]*)",
        r"\b(?:public|private|protected)?\s*(?:static\s+)?[a-zA-Z_][a-zA-Z0-9_<>]*\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(",
    ]
    for pattern in function_patterns:
        entities.extend(re.findall(pattern, text))

    constant_pattern = r"\b([A-Z][A-Z0-9_]{2,})\b"
    entities.extend(re.findall(constant_pattern, text))

    return list(set(entities))
