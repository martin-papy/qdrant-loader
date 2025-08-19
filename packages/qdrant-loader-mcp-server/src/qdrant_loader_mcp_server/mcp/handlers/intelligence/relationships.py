from __future__ import annotations

import math
from typing import Any, Dict, List

from .utils import get_or_create_document_id


def _safe_score(d: Any) -> float:
    try:
        if isinstance(d, dict):
            return float(d.get("score") or d.get("similarity") or d.get("relevance") or 0.0)
        return float(
            getattr(d, "score", None) or getattr(d, "similarity", None) or getattr(d, "relevance", None) or 0.0
        )
    except Exception:
        return 0.0


def _display_title(d: Any) -> str:
    if isinstance(d, dict):
        return (d.get("title") or d.get("source_title") or str(d))[:100]
    return (getattr(d, "source_title", None) or getattr(d, "title", None) or str(d))[:100]


def process_analysis_results(analysis_results: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    relationships: List[Dict[str, Any]] = []
    summary_parts: List[str] = []
    total_analyzed = analysis_results.get("query_metadata", {}).get("document_count", 0)

    # Document clusters → similarity relationships
    if "document_clusters" in analysis_results:
        clusters = analysis_results["document_clusters"]
        summary_parts.append(f"{len(clusters)} document clusters found")

        for cluster in clusters:
            cluster_docs = cluster.get("documents", [])
            max_pairs: int = params.get("max_similarity_pairs_per_cluster", 50)
            try:
                sorted_docs = sorted(cluster_docs, key=_safe_score, reverse=True)
            except Exception:
                sorted_docs = list(cluster_docs)

            if max_pairs is None or max_pairs <= 0:
                continue

            max_docs = int((1 + math.isqrt(1 + 8 * max_pairs)) // 2)
            max_docs = max(2, max_docs)
            docs_for_pairs = sorted_docs[:max_docs]

            emitted_pairs = 0
            for i, doc1 in enumerate(docs_for_pairs):
                for doc2 in docs_for_pairs[i + 1 :]:
                    if emitted_pairs >= max_pairs:
                        break
                    relationships.append(
                        {
                            "document_1_id": get_or_create_document_id(doc1),
                            "document_2_id": get_or_create_document_id(doc2),
                            "document_1_title": _display_title(doc1),
                            "document_2_title": _display_title(doc2),
                            "relationship_type": "similarity",
                            "confidence_score": cluster.get("cohesion_score", 0.8),
                            "relationship_summary": f"Both documents belong to cluster: {cluster.get('theme', 'unnamed cluster')}",
                        }
                    )
                    emitted_pairs += 1

    # Conflicts → conflict relationships
    if "conflict_analysis" in analysis_results:
        conflicts = analysis_results["conflict_analysis"].get("conflicting_pairs", [])
        if conflicts:
            summary_parts.append(f"{len(conflicts)} conflicts detected")
            for conflict in conflicts:
                if isinstance(conflict, (list, tuple)) and len(conflict) >= 2:
                    doc1, doc2 = conflict[0], conflict[1]
                    conflict_info = conflict[2] if len(conflict) > 2 else {}
                    relationships.append(
                        {
                            "document_1_id": get_or_create_document_id(doc1),
                            "document_2_id": get_or_create_document_id(doc2),
                            "document_1_title": _display_title(doc1),
                            "document_2_title": _display_title(doc2),
                            "relationship_type": "conflict",
                            "confidence_score": conflict_info.get("severity", 0.5),
                            "relationship_summary": f"Conflict detected: {conflict_info.get('type', 'unknown conflict')}",
                        }
                    )

    # Complementary content → complementary relationships
    if "complementary_content" in analysis_results:
        complementary = analysis_results["complementary_content"]
        comp_count = 0
        for doc_id, complementary_content in complementary.items():
            if hasattr(complementary_content, "get_top_recommendations"):
                recommendations = complementary_content.get_top_recommendations()
            else:
                recommendations = complementary_content if isinstance(complementary_content, list) else []
            for rec in recommendations:
                if isinstance(rec, dict):
                    target_doc_id = rec.get("document_id", "Unknown")
                    score = rec.get("relevance_score", 0.5)
                    reason = rec.get("recommendation_reason", "complementary content")
                    relationships.append(
                        {
                            "document_1_id": doc_id,
                            "document_2_id": target_doc_id,
                            "document_1_title": str(doc_id)[:100],
                            "document_2_title": rec.get("title", str(target_doc_id))[:100],
                            "relationship_type": "complementary",
                            "confidence_score": score,
                            "relationship_summary": f"Complementary content: {reason}",
                        }
                    )
                    comp_count += 1
        if comp_count > 0:
            summary_parts.append(f"{comp_count} complementary relationships")

    # Citations and insights → summary only
    if "citation_network" in analysis_results:
        citation_net = analysis_results["citation_network"]
        if citation_net.get("edges", 0) > 0:
            summary_parts.append(f"{citation_net['edges']} citation relationships")

    if analysis_results.get("similarity_insights"):
        summary_parts.append("similarity patterns identified")

    summary_text = (
        f"Analyzed {total_analyzed} documents: {', '.join(summary_parts)}"
        if summary_parts
        else f"Analyzed {total_analyzed} documents with no significant relationships found"
    )

    return {
        "relationships": relationships,
        "total_analyzed": total_analyzed,
        "summary": summary_text,
    }


