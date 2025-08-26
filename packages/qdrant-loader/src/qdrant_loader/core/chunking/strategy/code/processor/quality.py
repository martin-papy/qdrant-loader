from __future__ import annotations

from typing import Any

from qdrant_loader.core.chunking.strategy.code.processor.utils import (
    determine_learning_level as _determine_learning_level,
)
from qdrant_loader.core.chunking.strategy.code.processor.utils import (
    has_meaningful_names as _has_meaningful_names,
)
from qdrant_loader.core.chunking.strategy.code.processor.utils import (
    identify_programming_concepts as _identify_programming_concepts,
)


def assess_code_quality(content: str, chunk_metadata: dict[str, Any]) -> dict[str, Any]:
    complexity = chunk_metadata.get("complexity", 0)
    quality_score = 100
    if complexity > 10:
        quality_score -= 20
    elif complexity > 5:
        quality_score -= 10
    lines = content.split("\n")
    long_lines = [line for line in lines if len(line) > 120]
    if len(long_lines) > len(lines) * 0.3:
        quality_score -= 15
    has_docs = '"""' in content or "'''" in content
    if not has_docs and len(content) > 500:
        quality_score -= 10
    meaningful = _has_meaningful_names(content)
    quality_score += 5 if meaningful else -10
    return {
        "quality_score": max(0, quality_score),
        "complexity_level": (
            "low" if complexity < 3 else "medium" if complexity < 8 else "high"
        ),
        "readability_indicators": {
            "has_documentation": has_docs,
            "reasonable_line_length": (
                len(long_lines) / len(lines) < 0.1 if lines else True
            ),
            "meaningful_names": meaningful,
        },
    }


def assess_educational_value(
    content: str, chunk_metadata: dict[str, Any]
) -> dict[str, Any]:
    educational_indicators: list[str] = []
    if "example" in content.lower() or "demo" in content.lower():
        educational_indicators.append("example_code")
    if '"""' in content or "'''" in content:
        educational_indicators.append("well_documented")
    if "TODO" in content or "FIXME" in content:
        educational_indicators.append("learning_opportunity")
    complexity = chunk_metadata.get("complexity", 0)
    if 2 <= complexity <= 6:
        educational_indicators.append("good_complexity_for_learning")
    element_type = chunk_metadata.get("element_type", "unknown")
    if element_type in ["class", "interface"]:
        educational_indicators.append("object_oriented_concepts")
    return {
        "educational_indicators": educational_indicators,
        "learning_level": _determine_learning_level(complexity),
        "concepts_demonstrated": _identify_programming_concepts(content),
    }


def calculate_reusability_score(content: str, chunk_metadata: dict[str, Any]) -> int:
    score = 50
    element_type = chunk_metadata.get("element_type", "unknown")
    if element_type in ["function", "class", "interface"]:
        score += 20
    elif element_type == "method":
        score += 10
    if '"""' in content or "'''" in content:
        score += 15
    if "def " in content and "(" in content:
        param_count = content.count(",") + 1 if "(" in content else 0
        if param_count > 0:
            score += min(15, param_count * 3)
    if any(p in content for p in ["localhost", "127.0.0.1", "C:\\", "/tmp/"]):
        score -= 10
    if any(k in content.lower() for k in ["specific", "hardcode", "hack", "temporary"]):
        score -= 15
    return max(0, min(100, score))
