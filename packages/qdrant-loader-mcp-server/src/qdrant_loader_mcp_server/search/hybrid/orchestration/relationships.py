from __future__ import annotations

from typing import Any

from ...components.search_result_models import HybridSearchResult
from ...enhanced.cross_document_intelligence import (  # noqa: F401 - type hint usage
    ClusteringStrategy,
    DocumentCluster,
)
from ...hybrid.components.relationships import (
    analyze_content_similarity,
    analyze_entity_overlap,
    analyze_hierarchy_relationship,
    analyze_source_similarity,
    analyze_topic_overlap,
)


def analyze_cluster_relationships(
    engine: Any, clusters: list[DocumentCluster], documents: list[HybridSearchResult]
) -> list[dict[str, Any]]:
    if len(clusters) < 2:
        return []

    relationships: list[dict[str, Any]] = []
    doc_lookup = engine._build_document_lookup(documents, robust=True)

    for i, cluster_a in enumerate(clusters):
        for _, cluster_b in enumerate(clusters[i + 1 :], i + 1):
            relationship = analyze_cluster_pair(
                engine, cluster_a, cluster_b, doc_lookup
            )
            if relationship and relationship["strength"] > 0.1:
                relationships.append(
                    {
                        "cluster_a_id": cluster_a.cluster_id,
                        "cluster_b_id": cluster_b.cluster_id,
                        "cluster_a_name": cluster_a.name,
                        "cluster_b_name": cluster_b.name,
                        "relationship_type": relationship["type"],
                        "strength": relationship["strength"],
                        "description": relationship["description"],
                        "shared_elements": relationship["shared_elements"],
                    }
                )

    relationships.sort(key=lambda x: x["strength"], reverse=True)
    return relationships[:10]


def analyze_cluster_pair(
    engine: Any,
    cluster_a: DocumentCluster,
    cluster_b: DocumentCluster,
    doc_lookup: dict,
) -> dict[str, Any] | None:
    docs_a: list[HybridSearchResult] = []
    for doc_id in cluster_a.documents:
        doc = engine._find_document_by_id(doc_id, doc_lookup)
        if doc:
            docs_a.append(doc)

    docs_b: list[HybridSearchResult] = []
    for doc_id in cluster_b.documents:
        doc = engine._find_document_by_id(doc_id, doc_lookup)
        if doc:
            docs_b.append(doc)

    if not docs_a or not docs_b:
        return None

    candidates: list[dict[str, Any]] = []

    rel = analyze_entity_overlap(cluster_a, cluster_b)
    if rel:
        candidates.append(rel)

    rel = analyze_topic_overlap(cluster_a, cluster_b)
    if rel:
        candidates.append(rel)

    rel = analyze_source_similarity(docs_a, docs_b)
    if rel:
        candidates.append(rel)

    rel = analyze_hierarchy_relationship(docs_a, docs_b)
    if rel:
        candidates.append(rel)

    rel = analyze_content_similarity(docs_a, docs_b)
    if rel:
        candidates.append(rel)

    if candidates:
        return max(candidates, key=lambda x: x["strength"])
    return None
