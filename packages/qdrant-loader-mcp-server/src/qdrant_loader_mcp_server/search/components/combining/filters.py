from __future__ import annotations

from typing import Any


def should_skip_result(
    metadata: dict[str, Any],
    result_filters: dict[str, Any],
    query_context: dict[str, Any],
) -> bool:
    # Content type filtering
    if "content_type" in result_filters:
        allowed_content_types = result_filters["content_type"]
        content_analysis = metadata.get("content_type_analysis", {})

        has_matching_content = False
        for content_type in allowed_content_types:
            if content_type == "code" and content_analysis.get("has_code_blocks"):
                has_matching_content = True
                break
            elif content_type == "documentation" and not content_analysis.get(
                "has_code_blocks"
            ):
                has_matching_content = True
                break
            elif content_type == "technical" and query_context.get("is_technical"):
                has_matching_content = True
                break
            elif content_type in ["requirements", "business", "strategy"]:
                if count_business_indicators(metadata) > 0:
                    has_matching_content = True
                    break
            elif content_type in ["guide", "tutorial", "procedure"]:
                section_type = metadata.get("section_type", "").lower()
                if any(
                    proc_word in section_type
                    for proc_word in ["step", "guide", "procedure", "tutorial"]
                ):
                    has_matching_content = True
                    break

        if not has_matching_content:
            return True

    return False


def count_business_indicators(metadata: dict) -> int:
    business_terms = [
        "requirement",
        "business",
        "strategy",
        "goal",
        "objective",
        "process",
    ]
    title = metadata.get("title", "").lower()
    content = metadata.get("content", "").lower()

    return sum(1 for term in business_terms if term in title or term in content)
