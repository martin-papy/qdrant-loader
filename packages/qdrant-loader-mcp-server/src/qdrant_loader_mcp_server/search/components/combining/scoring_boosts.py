from __future__ import annotations

from typing import Any


def boost_score_with_metadata(
    base_score: float, metadata: dict, query_context: dict, *, spacy_analyzer=None
) -> float:
    boosted_score = base_score
    boost_factor = 0.0

    search_intent = query_context.get("search_intent")
    adaptive_config = query_context.get("adaptive_config")

    if search_intent and adaptive_config:
        boost_factor += apply_intent_boosting(
            metadata, search_intent, adaptive_config, query_context
        )

    boost_factor += apply_content_type_boosting(metadata, query_context)
    boost_factor += apply_section_level_boosting(metadata)
    boost_factor += apply_content_quality_boosting(metadata)
    boost_factor += apply_conversion_boosting(metadata, query_context)

    if spacy_analyzer:
        boost_factor += apply_semantic_boosting(metadata, query_context, spacy_analyzer)
    else:
        boost_factor += apply_fallback_semantic_boosting(metadata, query_context)

    boost_factor = min(boost_factor, 0.5)
    return boosted_score * (1 + boost_factor)


def apply_intent_boosting(
    metadata: dict, search_intent: Any, adaptive_config: Any, query_context: dict
) -> float:
    boost_factor = 0.0
    ranking_boosts = adaptive_config.ranking_boosts
    source_type_preferences = adaptive_config.source_type_preferences

    source_type = metadata.get("source_type", "")
    if source_type in source_type_preferences:
        boost_factor += (source_type_preferences[source_type] - 1.0) * 0.2

    for boost_key, boost_value in ranking_boosts.items():
        if boost_key == "section_type" and isinstance(boost_value, dict):
            section_type = metadata.get("section_type", "")
            if section_type in boost_value:
                boost_factor += (boost_value[section_type] - 1.0) * 0.15
        elif boost_key == "source_type" and isinstance(boost_value, dict):
            if source_type in boost_value:
                boost_factor += (boost_value[source_type] - 1.0) * 0.15
        elif boost_key in metadata and metadata[boost_key]:
            if isinstance(boost_value, int | float):
                boost_factor += (boost_value - 1.0) * 0.1

    boost_factor += search_intent.confidence * 0.05
    return boost_factor


def apply_content_type_boosting(metadata: dict, query_context: dict) -> float:
    boost_factor = 0.0
    content_analysis = metadata.get("content_type_analysis", {})

    if query_context.get("prefers_code") and content_analysis.get("has_code_blocks"):
        boost_factor += 0.15
    if query_context.get("prefers_tables") and content_analysis.get("has_tables"):
        boost_factor += 0.12
    if query_context.get("prefers_images") and content_analysis.get("has_images"):
        boost_factor += 0.10
    if query_context.get("prefers_docs") and not content_analysis.get(
        "has_code_blocks"
    ):
        boost_factor += 0.08
    return boost_factor


def apply_section_level_boosting(metadata: dict) -> float:
    boost_factor = 0.0
    section_level = metadata.get("section_level")
    if section_level is not None:
        if section_level <= 2:
            boost_factor += 0.10
        elif section_level <= 3:
            boost_factor += 0.05
    return boost_factor


def apply_content_quality_boosting(metadata: dict) -> float:
    boost_factor = 0.0
    content_analysis = metadata.get("content_type_analysis", {})
    word_count = content_analysis.get("word_count") or 0
    if word_count > 100:
        boost_factor += 0.05
    if word_count > 500:
        boost_factor += 0.05
    return boost_factor


def apply_conversion_boosting(metadata: dict, query_context: dict) -> float:
    boost_factor = 0.0
    if metadata.get("is_converted") and metadata.get("original_file_type") in [
        "docx",
        "xlsx",
        "pdf",
    ]:
        boost_factor += 0.08
    if metadata.get("is_excel_sheet") and any(
        term in " ".join(query_context.get("keywords", []))
        for term in ["data", "table", "sheet", "excel", "csv"]
    ):
        boost_factor += 0.12
    return boost_factor


def apply_semantic_boosting(
    metadata: dict, query_context: dict, spacy_analyzer: Any
) -> float:
    boost_factor = 0.0
    if "spacy_analysis" not in query_context:
        return boost_factor
    spacy_analysis = query_context["spacy_analysis"]

    entities = metadata.get("entities", [])
    if entities and spacy_analysis.entities:
        max_entity_similarity = 0.0
        for entity in entities:
            entity_text = (
                entity if isinstance(entity, str) else entity.get("text", str(entity))
            )
            similarity = spacy_analyzer.semantic_similarity_matching(
                spacy_analysis, entity_text
            )
            max_entity_similarity = max(max_entity_similarity, similarity)
        if max_entity_similarity > 0.6:
            boost_factor += 0.15
        elif max_entity_similarity > 0.4:
            boost_factor += 0.10
        elif max_entity_similarity > 0.2:
            boost_factor += 0.05

    topics = metadata.get("topics", [])
    if topics and spacy_analysis.main_concepts:
        max_topic_similarity = 0.0
        for topic in topics:
            topic_text = (
                topic if isinstance(topic, str) else topic.get("text", str(topic))
            )
            for concept in spacy_analysis.main_concepts:
                similarity = spacy_analyzer.semantic_similarity_matching(
                    spacy_analysis, f"{topic_text} {concept}"
                )
                max_topic_similarity = max(max_topic_similarity, similarity)
        if max_topic_similarity > 0.5:
            boost_factor += 0.12
        elif max_topic_similarity > 0.3:
            boost_factor += 0.08
    return boost_factor


def apply_fallback_semantic_boosting(metadata: dict, query_context: dict) -> float:
    boost_factor = 0.0
    entities = metadata.get("entities", [])
    if entities:
        query_keywords = set(query_context.get("keywords", []))
        entity_texts = set()
        for entity in entities:
            if isinstance(entity, str):
                entity_texts.add(entity.lower())
            elif isinstance(entity, dict):
                if "text" in entity:
                    entity_texts.add(str(entity["text"]).lower())
                elif "entity" in entity:
                    entity_texts.add(str(entity["entity"]).lower())
                else:
                    entity_texts.add(str(entity).lower())
        if query_keywords.intersection(entity_texts):
            boost_factor += 0.10

    topics = metadata.get("topics", [])
    if topics:
        query_keywords = set(query_context.get("keywords", []))
        topic_texts = set()
        for topic in topics:
            if isinstance(topic, str):
                topic_texts.add(topic.lower())
            elif isinstance(topic, dict):
                if "text" in topic:
                    topic_texts.add(str(topic["text"]).lower())
                elif "topic" in topic:
                    topic_texts.add(str(topic["topic"]).lower())
                else:
                    topic_texts.add(str(topic).lower())
        if query_keywords.intersection(topic_texts):
            boost_factor += 0.08
    return boost_factor
