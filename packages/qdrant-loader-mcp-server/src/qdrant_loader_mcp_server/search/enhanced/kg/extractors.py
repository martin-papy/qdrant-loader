from __future__ import annotations

from typing import Any


def extract_entities_from_result(result: Any) -> list[str]:
    entities: list[str] = []
    if result.source_title:
        entities.append(result.source_title)
    if result.parent_title:
        entities.append(result.parent_title)
    if result.section_title:
        entities.append(result.section_title)
    if result.project_name:
        entities.append(result.project_name)
    return list(set(entities))


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
    keywords: list[str] = []
    text_words = result.text.lower().split()[:10]
    keywords.extend([word for word in text_words if len(word) > 3 and word.isalpha()])
    if result.source_title:
        title_words = result.source_title.lower().split()
        keywords.extend([word for word in title_words if len(word) > 3 and word.isalpha()])
    return list(set(keywords))


