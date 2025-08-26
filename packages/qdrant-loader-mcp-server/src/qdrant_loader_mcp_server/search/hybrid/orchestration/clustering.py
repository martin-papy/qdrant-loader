from __future__ import annotations

import time
from typing import Any

from ...components.search_result_models import HybridSearchResult
from ...enhanced.cdi.models import ClusteringStrategy


async def cluster_documents(
    engine: Any,
    documents: list[HybridSearchResult],
    strategy: ClusteringStrategy = ClusteringStrategy.MIXED_FEATURES,
    max_clusters: int = 10,
    min_cluster_size: int = 2,
) -> dict[str, Any]:
    """Cluster documents using engine's CDI with delegated helpers.

    Args:
        engine: The hybrid search engine instance providing CDI and helper APIs.
        documents: Non-empty list of `HybridSearchResult` to cluster.
        strategy: Clustering strategy (instance of `ClusteringStrategy`).
        max_clusters: Maximum number of clusters to produce. Must be int > 0.
        min_cluster_size: Minimum documents per cluster. Must be int >= 1 and <= total documents.

    Returns:
        Dict with the following structure:
        - "clusters": list[dict]
          Each cluster dict contains:
            - "id": str | int
            - "name": str | None
            - "documents": list[HybridSearchResult]
            - "centroid_topics": list[str] | None
            - "shared_entities": list[str] | None
            - "coherence_score": float | None
            - "cluster_summary": str | None
            - "representative_doc_id": str | None
            - "cluster_strategy": str (the strategy value)
            - "quality_metrics": dict[str, Any]
            - "document_count": int
            - "expected_document_count": int
        - "clustering_metadata": dict[str, Any]
          Aggregate stats, counts, parameters, and quality assessments for the run.
        - "cluster_relationships": list[dict[str, Any]]
          Relationship analysis between clusters.

    Raises:
        ValueError: If inputs are invalid, e.g. documents is not a non-empty list,
                    strategy is not a `ClusteringStrategy`, or constraints on
                    max_clusters/min_cluster_size are violated.
    """
    # Input validation
    if not isinstance(documents, list):
        raise ValueError("'documents' must be a list of HybridSearchResult")
    if len(documents) == 0:
        raise ValueError("'documents' must be a non-empty list")
    if not isinstance(max_clusters, int) or max_clusters <= 0:
        raise ValueError("'max_clusters' must be an int greater than 0")
    if not isinstance(min_cluster_size, int) or min_cluster_size < 1:
        raise ValueError("'min_cluster_size' must be an int greater than or equal to 1")
    total_documents = len(documents)
    # Allow max_clusters greater than total documents; downstream analyzer may cap it.
    if min_cluster_size > total_documents:
        raise ValueError(
            "'min_cluster_size' cannot exceed the total number of documents"
        )
    if not isinstance(strategy, ClusteringStrategy):
        raise ValueError("'strategy' must be an instance of ClusteringStrategy")
    start_time = time.time()

    engine.logger.info(
        f"Starting clustering with {len(documents)} documents using {strategy.value}"
    )

    clusters = engine.cross_document_engine.cluster_analyzer.create_clusters(
        documents, strategy, max_clusters, min_cluster_size
    )

    # Build robust document lookup with multiple strategies via public API
    doc_lookup = engine.build_document_lookup(documents, robust=True)

    cluster_data = []
    total_matched_docs = 0
    total_requested_docs = 0

    for i, cluster in enumerate(clusters):
        cluster_documents = []
        doc_ids_found = []
        doc_ids_missing = []

        total_requested_docs += len(cluster.documents)

        for doc_id in cluster.documents:
            matched_doc = engine.find_document_by_id(doc_id, doc_lookup)
            if matched_doc:
                cluster_documents.append(matched_doc)
                doc_ids_found.append(doc_id)
                total_matched_docs += 1
            else:
                doc_ids_missing.append(doc_id)
                engine.logger.warning(f"Document not found in lookup: {doc_id}")

        engine.logger.info(
            f"Cluster {i}: Found {len(doc_ids_found)}/{len(cluster.documents)} documents"
        )
        if doc_ids_missing:
            engine.logger.warning(
                f"Missing documents in cluster {i}: {doc_ids_missing[:3]}"
            )

        # Calculate cluster quality metrics via public API
        cluster_quality = engine.calculate_cluster_quality(cluster, cluster_documents)

        cluster_data.append(
            {
                "id": cluster.cluster_id,
                "name": cluster.name,
                "documents": cluster_documents,
                "centroid_topics": (
                    getattr(cluster, "centroid_topics", None)
                    or getattr(cluster, "shared_topics", [])
                ),
                "shared_entities": cluster.shared_entities,
                "coherence_score": cluster.coherence_score,
                "cluster_summary": cluster.cluster_description,
                "representative_doc_id": cluster.representative_doc_id,
                "cluster_strategy": strategy.value,
                "quality_metrics": cluster_quality,
                "document_count": len(cluster_documents),
                "expected_document_count": len(cluster.documents),
            }
        )

    processing_time = (time.time() - start_time) * 1000

    clustering_metadata = engine.build_enhanced_metadata(
        clusters,
        documents,
        strategy,
        processing_time,
        total_matched_docs,
        total_requested_docs,
    )

    cluster_relationships = engine.analyze_cluster_relationships(clusters, documents)

    engine.logger.info(
        f"Clustering completed: {len(clusters)} clusters, "
        f"{total_matched_docs}/{total_requested_docs} documents matched, "
        f"{len(cluster_relationships)} relationships identified"
    )

    return {
        "clusters": cluster_data,
        "clustering_metadata": clustering_metadata,
        "cluster_relationships": cluster_relationships,
    }
