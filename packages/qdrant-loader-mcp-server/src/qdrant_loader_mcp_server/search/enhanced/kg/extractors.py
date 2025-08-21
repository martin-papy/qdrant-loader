from __future__ import annotations

from typing import Any


def extract_entities_from_result(result: Any) -> list[str]:
    entities: set[str] = set()

    for attr_name in ("source_title", "parent_title", "section_title", "project_name"):
        value = getattr(result, attr_name, None)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                entities.add(stripped)

    return list(entities)


def extract_topics_from_result(result: Any) -> list[str]:
    topics: list[str] = []
    if result.breadcrumb_text:
        topics.extend([section.strip() for section in result.breadcrumb_text.split(" > ")])
    if result.section_type:
        topics.append(result.section_type)
    if result.source_type:
        topics.append(result.source_type)
    return list(set(topics))


def extract_concepts_from_result(result: Any) -> list[str]:
    concepts: list[str] = []
    if result.section_title:
        concepts.append(result.section_title)
    if result.hierarchy_context:
        concepts.append(result.hierarchy_context)
    return list(set(concepts))


def extract_keywords_from_result(result: Any) -> list[str]:
    keywords_set: set[str] = set()

    def filtered_words(text: Any, limit: int | None = 10) -> list[str]:
        if not isinstance(text, str):
            return []
        words = text.lower().split()
        if limit is not None:
            words = words[:limit]
        return [w for w in words if len(w) > 3 and w.isalpha()]

    text = getattr(result, "text", None)
    keywords_set.update(filtered_words(text, 10))

    source_title = getattr(result, "source_title", None)
    keywords_set.update(filtered_words(source_title, None))

    return list(keywords_set)


