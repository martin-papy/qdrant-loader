from __future__ import annotations

from typing import Any


def analyze_entity_overlap(cluster_a, cluster_b) -> dict[str, Any] | None:
    # Defensive input validation
    if cluster_a is None or cluster_b is None:
        return None
    entities_a = set(getattr(cluster_a, "shared_entities", []) or [])
    entities_b = set(getattr(cluster_b, "shared_entities", []) or [])
    if not entities_a or not entities_b:
        return None
    overlap = entities_a & entities_b
    union = entities_a | entities_b
    if not overlap:
        return None
    strength = len(overlap) / len(union)
    return {
        "type": "entity_overlap",
        "strength": strength,
        "description": f"Share {len(overlap)} common entities: {', '.join(list(overlap)[:3])}",
        "shared_elements": list(overlap),
    }


def analyze_topic_overlap(cluster_a, cluster_b) -> dict[str, Any] | None:
    # Defensive input validation similar to analyze_entity_overlap
    if cluster_a is None or cluster_b is None:
        return None
    topics_a_raw = getattr(cluster_a, "shared_topics", None)
    topics_b_raw = getattr(cluster_b, "shared_topics", None)
    if not topics_a_raw or not topics_b_raw:
        return None
    try:
        topics_a = set(topics_a_raw)
        topics_b = set(topics_b_raw)
    except TypeError:
        return None
    if not topics_a or not topics_b:
        return None
    overlap = topics_a & topics_b
    union = topics_a | topics_b
    if not overlap:
        return None
    strength = len(overlap) / len(union)
    return {
        "type": "topic_overlap",
        "strength": strength,
        "description": f"Share {len(overlap)} common topics: {', '.join(list(overlap)[:3])}",
        "shared_elements": list(overlap),
    }


def analyze_source_similarity(
    docs_a: list[Any], docs_b: list[Any]
) -> dict[str, Any] | None:
    sources_a = {getattr(doc, "source_type", None) for doc in docs_a if doc}
    sources_b = {getattr(doc, "source_type", None) for doc in docs_b if doc}
    sources_a.discard(None)
    sources_b.discard(None)
    if not sources_a or not sources_b:
        return None
    overlap = sources_a & sources_b
    union = sources_a | sources_b
    if not overlap:
        return None
    strength = len(overlap) / len(union)
    if len(sources_a) == 1 and len(sources_b) == 1 and sources_a == sources_b:
        strength = min(1.0, strength + 0.3)
    return {
        "type": "source_similarity",
        "strength": strength,
        "description": f"Both contain {', '.join(overlap)} documents",
        "shared_elements": list(overlap),
    }


def analyze_hierarchy_relationship(
    docs_a: list[Any], docs_b: list[Any]
) -> dict[str, Any] | None:
    breadcrumbs_a = [getattr(doc, "breadcrumb_text", "") for doc in docs_a if doc]
    breadcrumbs_b = [getattr(doc, "breadcrumb_text", "") for doc in docs_b if doc]
    if not breadcrumbs_a or not breadcrumbs_b:
        return None
    parent_child_count = 0
    for bc_a in breadcrumbs_a:
        for bc_b in breadcrumbs_b:
            if bc_a and bc_b:
                if bc_a in bc_b or bc_b in bc_a:
                    parent_child_count += 1
    if parent_child_count == 0:
        return None
    total_comparisons = len(breadcrumbs_a) * len(breadcrumbs_b)
    strength = parent_child_count / total_comparisons if total_comparisons > 0 else 0
    return {
        "type": "hierarchical",
        "strength": strength,
        "description": f"Hierarchically related documents ({parent_child_count} connections)",
        "shared_elements": [],
    }


def analyze_content_similarity(
    docs_a: list[Any], docs_b: list[Any]
) -> dict[str, Any] | None:
    has_code_a = any(getattr(doc, "has_code_blocks", False) for doc in docs_a if doc)
    has_code_b = any(getattr(doc, "has_code_blocks", False) for doc in docs_b if doc)
    word_counts_a = [getattr(doc, "word_count", 0) or 0 for doc in docs_a if doc]
    word_counts_b = [getattr(doc, "word_count", 0) or 0 for doc in docs_b if doc]
    avg_size_a = sum(word_counts_a) / len(word_counts_a) if word_counts_a else 0
    avg_size_b = sum(word_counts_b) / len(word_counts_b) if word_counts_b else 0

    similarity_factors: list[float] = []
    if has_code_a and has_code_b:
        similarity_factors.append(0.4)
    elif not has_code_a and not has_code_b:
        similarity_factors.append(0.2)

    if avg_size_a > 0 and avg_size_b > 0:
        size_ratio = min(avg_size_a, avg_size_b) / max(avg_size_a, avg_size_b)
        if size_ratio > 0.5:
            similarity_factors.append(size_ratio * 0.3)

    if not similarity_factors:
        return None

    strength = sum(similarity_factors)
    if strength < 0.1:
        return None

    description_parts: list[str] = []
    if has_code_a and has_code_b:
        description_parts.append("both contain code")
    if (
        avg_size_a > 0
        and avg_size_b > 0
        and abs(avg_size_a - avg_size_b) / max(avg_size_a, avg_size_b) < 0.5
    ):
        description_parts.append("similar document sizes")

    description = (
        f"Content similarity: {', '.join(description_parts)}"
        if description_parts
        else "Similar content characteristics"
    )

    return {
        "type": "content_similarity",
        "strength": strength,
        "description": description,
        "shared_elements": [],
    }
