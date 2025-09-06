from __future__ import annotations

from typing import Any


def describe_conflict(_detector: Any, indicators: list) -> str:
    if not indicators:
        return "No specific conflict indicators found."
    descriptions: list[str] = []
    for indicator in indicators[:3]:
        if isinstance(indicator, dict) and "type" in indicator:
            descriptions.append(f"{indicator['type']} conflict detected")
        elif isinstance(indicator, str):
            descriptions.append(indicator)
        else:
            descriptions.append("General conflict indicator")
    return (
        "; ".join(descriptions)
        if descriptions
        else "Multiple conflict indicators found."
    )


def generate_resolution_suggestions(_detector: Any, conflicts: Any) -> dict[str, str]:
    if not conflicts:
        return {"general": "No conflicts detected - no resolution needed."}

    suggestions: dict[str, str] = {}

    if hasattr(conflicts, "conflict_categories"):
        for category, _pairs in conflicts.conflict_categories.items():
            if category == "version":
                suggestions[category] = (
                    "Consider consolidating version information across documents."
                )
            elif category == "procedural":
                suggestions[category] = "Review and standardize procedural steps."
            elif category == "data":
                suggestions[category] = (
                    "Verify and update data consistency across sources."
                )
            else:
                suggestions[category] = f"Review and resolve {category} conflicts."
        return suggestions or {
            "general": "Review conflicting documents and update accordingly."
        }

    if isinstance(conflicts, list):
        for i, conflict in enumerate(conflicts[:3]):
            key = f"conflict_{i+1}"
            if isinstance(conflict, dict):
                ctype = conflict.get("type", "unknown").lower()
                if "version" in ctype:
                    suggestions[key] = (
                        "Consider consolidating version information across documents."
                    )
                elif "procedure" in ctype or "process" in ctype:
                    suggestions[key] = "Review and standardize procedural steps."
                elif "data" in ctype:
                    suggestions[key] = (
                        "Verify and update data consistency across sources."
                    )
                else:
                    suggestions[key] = (
                        "Review conflicting information and update as needed."
                    )
            else:
                suggestions[key] = "Review and resolve identified conflicts."
        return suggestions or {
            "general": "Review conflicting documents and update accordingly."
        }

    return {"general": "Review and resolve detected conflicts."}


def extract_context_snippet(
    _detector: Any,
    text: str,
    keyword: str,
    context_length: int = 100,
    max_length: int | None = None,
) -> str:
    if not keyword or not text:
        return ""
    keyword_lower = keyword.lower()
    text_lower = text.lower()
    effective_length = max_length if max_length is not None else context_length
    start_idx = text_lower.find(keyword_lower)
    if start_idx == -1:
        return text[:effective_length].strip()
    context_start = max(0, start_idx - effective_length // 2)
    context_end = min(len(text), start_idx + len(keyword) + effective_length // 2)
    return text[context_start:context_end].strip()
