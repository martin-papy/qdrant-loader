from __future__ import annotations

from typing import Any, List, Optional

from ...components.search_result_models import HybridSearchResult
from ...enhanced.cross_document_intelligence import DocumentCluster
from ...enhanced.cross_document_intelligence import ClusteringStrategy  # noqa: F401 - type hint usage
from ...hybrid.components.relationships import (
    analyze_entity_overlap,
    analyze_topic_overlap,
    analyze_source_similarity,
    analyze_hierarchy_relationship,
    analyze_content_similarity,
)


def analyze_cluster_relationships(
    engine: Any, clusters: List[DocumentCluster], documents: List[HybridSearchResult]
) -> List[dict[str, Any]]:
    if len(clusters) < 2:
        return []

    relationships: List[dict[str, Any]] = []
    doc_lookup = engine._build_document_lookup(documents, robust=True)

    for i, cluster_a in enumerate(clusters):
        for _, cluster_b in enumerate(clusters[i + 1 :], i + 1):
            relationship = analyze_cluster_pair(engine, cluster_a, cluster_b, doc_lookup)
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
    engine: Any, cluster_a: DocumentCluster, cluster_b: DocumentCluster, doc_lookup: dict
) -> Optional[dict[str, Any]]:
    docs_a: List[HybridSearchResult] = []
    for doc_id in cluster_a.documents:
        doc = engine._find_document_by_id(doc_id, doc_lookup)
        if doc:
            docs_a.append(doc)

    docs_b: List[HybridSearchResult] = []
    for doc_id in cluster_b.documents:
        doc = engine._find_document_by_id(doc_id, doc_lookup)
        if doc:
            docs_b.append(doc)

    if not docs_a or not docs_b:
        return None

    candidates: List[dict[str, Any]] = []

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


