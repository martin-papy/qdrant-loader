from __future__ import annotations

import math
from typing import Any

from .utils import get_or_create_document_id


def _safe_score(d: Any) -> float:
    try:
        if isinstance(d, dict):
            return float(
                d.get("score") or d.get("similarity") or d.get("relevance") or 0.0
            )
        return float(
            getattr(d, "score", None)
            or getattr(d, "similarity", None)
            or getattr(d, "relevance", None)
            or 0.0
        )
    except Exception:
        return 0.0


def _display_title(d: Any) -> str:
    if isinstance(d, dict):
        return (d.get("title") or d.get("source_title") or str(d))[:100]
    return (getattr(d, "source_title", None) or getattr(d, "title", None) or str(d))[
        :100
    ]


def process_analysis_results(
    analysis_results: dict[str, Any], params: dict[str, Any]
) -> dict[str, Any]:
    relationships: list[dict[str, Any]] = []
    summary_parts: list[str] = []
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

            # Validate inputs and clamp quadratic-based doc count
            try:
                max_pairs_val = int(max_pairs) if max_pairs is not None else 0
            except Exception:
                max_pairs_val = 0
            if max_pairs_val < 0:
                max_pairs_val = 0

            if not sorted_docs:
                docs_for_pairs = []
            else:
                # Guard isqrt by ensuring non-negative discriminant
                discriminant = 1 + 8 * max_pairs_val
                if discriminant < 0:
                    discriminant = 0
                root = math.isqrt(discriminant)
                max_docs = int((1 + root) // 2)
                # Clamp to [2, len(sorted_docs)] where possible
                max_docs = max(2, max_docs)
                max_docs = min(len(sorted_docs), max_docs)
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
                if isinstance(conflict, list | tuple) and len(conflict) >= 2:
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
        # Build a lightweight documents lookup for title resolution
        docs_lookup: dict[str, Any] = {}
        try:
            # From clusters if available
            for cluster in analysis_results.get("document_clusters", []) or []:
                for d in cluster.get("documents", []) or []:
                    if isinstance(d, dict):
                        doc_key = d.get("document_id") or get_or_create_document_id(d)
                        if doc_key:
                            docs_lookup[str(doc_key)] = d
                        # Also try a composite key commonly used elsewhere
                        st = d.get("source_type", "unknown")
                        tt = d.get("source_title", d.get("title", "unknown"))
                        docs_lookup.setdefault(f"{st}:{tt}", d)
        except Exception:
            pass
        for doc_id, complementary_content in complementary.items():
            if hasattr(complementary_content, "get_top_recommendations"):
                recommendations = complementary_content.get_top_recommendations()
            else:
                recommendations = (
                    complementary_content
                    if isinstance(complementary_content, list)
                    else []
                )
            for rec in recommendations:
                if isinstance(rec, dict):
                    target_doc_id = rec.get("document_id", "Unknown")
                    score = rec.get("relevance_score", 0.5)
                    reason = rec.get("recommendation_reason", "complementary content")
                    # Resolve titles consistently using _display_title with lookups
                    source_doc_obj = docs_lookup.get(str(doc_id))
                    document_1_title = (
                        _display_title(source_doc_obj)
                        if source_doc_obj is not None
                        else str(doc_id)
                    )[:100]
                    target_doc_obj = rec.get("document") or docs_lookup.get(
                        str(target_doc_id)
                    )
                    fallback_title = rec.get("title", str(target_doc_id))
                    document_2_title = (
                        _display_title(target_doc_obj)
                        if target_doc_obj is not None
                        else fallback_title
                    )[:100]
                    relationships.append(
                        {
                            "document_1_id": doc_id,
                            "document_2_id": target_doc_id,
                            "document_1_title": document_1_title,
                            "document_2_title": document_2_title,
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
