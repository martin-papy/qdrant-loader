from __future__ import annotations

import time
from typing import Any

from ...enhanced.cross_document_intelligence import ClusteringStrategy
from ...components.search_result_models import HybridSearchResult


async def cluster_documents(
    engine: Any,
    documents: list[HybridSearchResult],
    strategy: ClusteringStrategy = ClusteringStrategy.MIXED_FEATURES,
    max_clusters: int = 10,
    min_cluster_size: int = 2,
) -> dict[str, Any]:
    """Cluster documents using engine's CDI with delegated helpers."""
    start_time = time.time()

    engine.logger.info(
        f"Starting clustering with {len(documents)} documents using {strategy.value}"
    )

    clusters = engine.cross_document_engine.cluster_analyzer.create_clusters(
        documents, strategy, max_clusters, min_cluster_size
    )

    # Build robust document lookup with multiple strategies
    doc_lookup = engine._build_document_lookup(documents, robust=True)

    cluster_data = []
    total_matched_docs = 0
    total_requested_docs = 0

    for i, cluster in enumerate(clusters):
        cluster_documents = []
        doc_ids_found = []
        doc_ids_missing = []

        total_requested_docs += len(cluster.documents)

        for doc_id in cluster.documents:
            matched_doc = engine._find_document_by_id(doc_id, doc_lookup)
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

        # Calculate cluster quality metrics
        cluster_quality = engine._calculate_cluster_quality(cluster, cluster_documents)

        cluster_data.append(
            {
                "id": cluster.cluster_id,
                "name": cluster.name,
                "documents": cluster_documents,
                "centroid_topics": cluster.shared_topics,
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

    clustering_metadata = engine._build_enhanced_metadata(
        clusters,
        documents,
        strategy,
        processing_time,
        total_matched_docs,
        total_requested_docs,
    )

    cluster_relationships = engine._analyze_cluster_relationships(clusters, documents)

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


