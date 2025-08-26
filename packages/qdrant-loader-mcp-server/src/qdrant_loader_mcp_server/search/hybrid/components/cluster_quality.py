from __future__ import annotations

from typing import Any


def calculate_std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return variance**0.5


def assess_overall_quality(clusters, matched_docs: int, requested_docs: int) -> float:
    if not clusters:
        return 0.0

    retrieval_score = matched_docs / requested_docs if requested_docs > 0 else 0
    coherence_scores = [c.coherence_score for c in clusters if c.coherence_score > 0]
    coherence_score = (
        sum(coherence_scores) / len(coherence_scores) if coherence_scores else 0
    )

    cluster_sizes = [len(c.documents) for c in clusters]
    size_distribution_score = 1.0
    if len(clusters) == 1 and len(cluster_sizes) > 0 and cluster_sizes[0] > 10:
        size_distribution_score = 0.7
    elif len([s for s in cluster_sizes if s < 3]) > len(clusters) * 0.7:
        size_distribution_score = 0.8

    overall_quality = (
        retrieval_score * 0.4 + coherence_score * 0.4 + size_distribution_score * 0.2
    )
    return min(1.0, max(0.0, overall_quality))


def generate_clustering_recommendations(
    clusters, strategy, matched_docs: int, requested_docs: int
) -> dict[str, Any]:
    recommendations = {
        "quality_threshold_met": (
            matched_docs / requested_docs >= 0.9 if requested_docs > 0 else False
        ),
        "suggestions": [],
    }

    retrieval_rate = matched_docs / requested_docs if requested_docs > 0 else 0
    if retrieval_rate < 0.9:
        recommendations["suggestions"].append(
            f"Low document retrieval rate ({retrieval_rate:.1%}). Check document ID consistency."
        )

    if len(clusters) == 1 and requested_docs > 10:
        recommendations["suggestions"].append(
            "Single large cluster detected. Consider trying entity_based or topic_based strategy."
        )
        recommendations["alternative_strategies"] = ["entity_based", "topic_based"]

    if len(clusters) > requested_docs * 0.5:
        recommendations["suggestions"].append(
            "Many small clusters. Consider increasing min_cluster_size or trying mixed_features strategy."
        )

    coherence_scores = [c.coherence_score for c in clusters if c.coherence_score > 0]
    if coherence_scores and sum(coherence_scores) / len(coherence_scores) < 0.5:
        recommendations["suggestions"].append(
            "Low cluster coherence. Documents may be too diverse for meaningful clustering."
        )

    return recommendations


def build_enhanced_metadata(
    clusters, documents, strategy, processing_time, matched_docs, requested_docs
) -> dict[str, Any]:
    cluster_sizes = [len(cluster.documents) for cluster in clusters]
    coherence_scores = [
        cluster.coherence_score for cluster in clusters if cluster.coherence_score > 0
    ]

    metadata = {
        "strategy": strategy.value,
        "total_documents": len(documents),
        "clusters_created": len(clusters),
        "unclustered_documents": len(documents) - sum(cluster_sizes),
        "document_retrieval_rate": (
            matched_docs / requested_docs if requested_docs > 0 else 0
        ),
        "processing_time_ms": round(processing_time, 2),
        "strategy_performance": {
            "coherence_avg": (
                sum(coherence_scores) / len(coherence_scores) if coherence_scores else 0
            ),
            "coherence_std": (
                calculate_std(coherence_scores) if len(coherence_scores) > 1 else 0
            ),
            "size_distribution": cluster_sizes,
            "size_avg": (
                sum(cluster_sizes) / len(cluster_sizes) if cluster_sizes else 0
            ),
        },
        "clustering_quality": assess_overall_quality(
            clusters, matched_docs, requested_docs
        ),
        "recommendations": generate_clustering_recommendations(
            clusters, strategy, matched_docs, requested_docs
        ),
    }
    return metadata


def categorize_cluster_size(size: int) -> str:
    if size <= 2:
        return "small"
    elif size <= 5:
        return "medium"
    elif size <= 10:
        return "large"
    else:
        return "very_large"


def estimate_content_similarity(documents: list[Any]) -> float:
    if len(documents) < 2:
        return 1.0
    all_words: list[str] = []
    doc_word_sets: list[set[str]] = []
    for doc in documents[:5]:
        words: set[str] = set()
        title = getattr(doc, "source_title", None)
        if title:
            words.update(str(title).lower().split())
        text = getattr(doc, "text", None)
        if text:
            words.update(str(text)[:200].lower().split())
        doc_word_sets.append(words)
        all_words.extend(list(words))
    if not doc_word_sets:
        return 0.0
    total_overlap = 0.0
    comparisons = 0
    for i in range(len(doc_word_sets)):
        for j in range(i + 1, len(doc_word_sets)):
            overlap = len(doc_word_sets[i] & doc_word_sets[j])
            union = len(doc_word_sets[i] | doc_word_sets[j])
            if union > 0:
                total_overlap += overlap / union
            comparisons += 1
    return total_overlap / comparisons if comparisons > 0 else 0.0


def calculate_cluster_quality(
    cluster: Any, cluster_documents: list[Any]
) -> dict[str, Any]:
    quality_metrics = {
        "document_retrieval_rate": (
            len(cluster_documents) / len(cluster.documents) if cluster.documents else 0
        ),
        "coherence_score": cluster.coherence_score,
        "entity_diversity": len(cluster.shared_entities),
        "topic_diversity": len(cluster.shared_topics),
        "has_representative": bool(cluster.representative_doc_id),
        "cluster_size_category": categorize_cluster_size(len(cluster_documents)),
    }
    if len(cluster_documents) > 1:
        quality_metrics["content_similarity"] = estimate_content_similarity(
            cluster_documents
        )
    return quality_metrics
