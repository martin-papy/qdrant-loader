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
    # breadcrumb_text may be missing or non-string
    breadcrumb_text = getattr(result, "breadcrumb_text", None)
    if isinstance(breadcrumb_text, str):
        stripped_breadcrumb = breadcrumb_text.strip()
        if stripped_breadcrumb:
            topics.extend(
                [
                    section.strip()
                    for section in stripped_breadcrumb.split(" > ")
                    if section.strip()
                ]
            )

    # section_type and source_type may be missing
    section_type = getattr(result, "section_type", None)
    if isinstance(section_type, str) and section_type.strip():
        topics.append(section_type.strip())

    source_type = getattr(result, "source_type", None)
    if isinstance(source_type, str) and source_type.strip():
        topics.append(source_type.strip())

    return list(set(topics))


def extract_concepts_from_result(result: Any) -> list[str]:
    concepts: list[str] = []

    section_title = getattr(result, "section_title", None)
    if isinstance(section_title, str):
        stripped_section = section_title.strip()
        if stripped_section:
            concepts.append(stripped_section)

    hierarchy_context = getattr(result, "hierarchy_context", None)
    if isinstance(hierarchy_context, str):
        stripped_hierarchy = hierarchy_context.strip()
        if stripped_hierarchy:
            concepts.append(stripped_hierarchy)

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
