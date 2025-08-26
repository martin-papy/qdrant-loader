"""
Intelligence Result Formatters - Analysis and Insights Formatting.

This module handles formatting of intelligence analysis results including
relationship analysis, similarity detection, conflict analysis, and
complementary content discovery.
"""

from typing import Any


class IntelligenceResultFormatters:
    """Handles intelligence analysis result formatting operations."""

    @staticmethod
    def format_relationship_analysis(analysis: dict[str, Any]) -> str:
        """Format document relationship analysis for display."""
        if "error" in analysis:
            return f"❌ Error: {analysis['error']}"

        summary = analysis.get("summary", {})
        formatted = f"""🔍 **Document Relationship Analysis**

📊 **Summary:**
• Total Documents: {summary.get('total_documents', 0)}
• Clusters Found: {summary.get('clusters_found', 0)}
• Citation Relationships: {summary.get('citation_relationships', 0)}
• Conflicts Detected: {summary.get('conflicts_detected', 0)}

🏷️ **Query Information:**
• Original Query: {analysis.get('query_metadata', {}).get('original_query', 'N/A')}
• Documents Analyzed: {analysis.get('query_metadata', {}).get('document_count', 0)}
"""

        # Accept multiple shapes for clusters
        clusters_candidate = None
        for key in (
            "document_clusters",
            "topic_clusters",
            "entity_clusters",
            "clusters",
        ):
            value = analysis.get(key)
            if value:
                clusters_candidate = value
                break

        cluster_list: list[Any] = []
        if isinstance(clusters_candidate, list):
            cluster_list = clusters_candidate
        elif isinstance(clusters_candidate, dict):
            # Some producers return a dict of clusters
            cluster_list = list(clusters_candidate.values())

        if cluster_list:
            formatted += "\n🗂️ **Document Clusters:**\n"
            for i, cluster in enumerate(cluster_list[:3], 1):  # Show first 3 clusters
                count = 0
                if isinstance(cluster, dict):
                    items = (
                        cluster.get("documents")
                        or cluster.get("items")
                        or cluster.get("members")
                    )
                    if isinstance(items, list):
                        count = len(items)
                    else:
                        try:
                            count = len(cluster)
                        except Exception:
                            count = 0
                else:
                    try:
                        count = len(cluster)  # type: ignore[arg-type]
                    except Exception:
                        count = 0

                formatted += f"• Cluster {i}: {count} documents\n"

        # Aggregate conflicts across possible locations/shapes
        conflict_lists: list[list[Any]] = []
        conflict_analysis = analysis.get("conflict_analysis", {}) or {}
        for key in ("conflicting_pairs", "conflicts"):
            lst = conflict_analysis.get(key)
            if isinstance(lst, list):
                conflict_lists.append(lst)

        for key in ("conflicts", "conflicting_pairs"):
            lst = analysis.get(key)
            if isinstance(lst, list):
                conflict_lists.append(lst)

        entity_relationships = analysis.get("entity_relationships", {}) or {}
        for key in ("conflicting_pairs", "conflicts"):
            lst = entity_relationships.get(key)
            if isinstance(lst, list):
                conflict_lists.append(lst)

        total_conflicts = sum(len(lst) for lst in conflict_lists)
        if total_conflicts:
            formatted += f"\n⚠️ **Conflicts Detected:** {total_conflicts} conflicting document pairs\n"

        return formatted

    @staticmethod
    def format_similar_documents(similar_docs: list[dict[str, Any]]) -> str:
        """Format similar documents results for display."""
        if not similar_docs:
            return "🔍 **Similar Documents**\n\nNo similar documents found."

        formatted = f"🔍 **Similar Documents** ({len(similar_docs)} found)\n\n"

        for i, doc_info in enumerate(similar_docs[:5], 1):  # Show top 5
            # Robust similarity score extraction
            score_value: Any = None
            for key in ("overall_similarity", "similarity_score"):
                if key in doc_info:
                    score_value = doc_info.get(key)
                    break
            if score_value is None:
                similarity_scores = doc_info.get("similarity_scores")
                if isinstance(similarity_scores, dict):
                    if "overall" in similarity_scores:
                        score_value = similarity_scores.get("overall")
                    else:
                        for v in similarity_scores.values():
                            if isinstance(v, int | float):
                                score_value = v
                                break
                elif isinstance(similarity_scores, list):
                    for v in similarity_scores:
                        if isinstance(v, int | float):
                            score_value = v
                            break
            try:
                score = float(score_value) if score_value is not None else 0.0
            except (TypeError, ValueError):
                score = 0.0

            document = doc_info.get("document", {})

            # Title extraction: document.source_title -> document.title -> top-level
            title_value = None
            if isinstance(document, dict):
                title_value = document.get("source_title") or document.get("title")
            else:
                title_value = getattr(document, "source_title", None) or getattr(
                    document, "title", None
                )
            if not title_value:
                title_value = doc_info.get("source_title") or doc_info.get("title")

            # Reasons extraction: prefer list but normalize strings
            reasons_value = (
                doc_info.get("similarity_reasons")
                or doc_info.get("reason")
                or doc_info.get("explanations")
                or doc_info.get("reasons")
            )
            reasons_list: list[str] = []
            if isinstance(reasons_value, list):
                reasons_list = [str(r) for r in reasons_value]
            elif isinstance(reasons_value, str):
                reasons_list = [reasons_value]

            formatted += f"**{i}. Similarity Score: {score:.3f}**\n"
            if title_value:
                formatted += f"• Title: {title_value}\n"
            if reasons_list:
                formatted += f"• Reasons: {', '.join(reasons_list)}\n"
            formatted += "\n"

        return formatted

    @staticmethod
    def format_conflict_analysis(conflicts: dict[str, Any]) -> str:
        """Format conflict analysis results for display."""
        # Handle both new format ("conflicts") and old format ("conflicting_pairs")
        conflict_list = conflicts.get("conflicts", [])
        conflicting_pairs = conflicts.get("conflicting_pairs", [])

        # Use whichever format is provided
        if conflicting_pairs:
            conflict_list = conflicting_pairs

        if not conflicts or not conflict_list:
            return (
                "✅ **Conflict Analysis**\n\nNo conflicts detected between documents."
            )

        formatted = (
            f"⚠️ **Conflict Analysis** ({len(conflict_list)} conflicts found)\n\n"
        )

        for i, conflict in enumerate(conflict_list[:3], 1):  # Show top 3 conflicts
            # Handle tuple format (doc1, doc2, metadata) or dict format
            if isinstance(conflict, tuple) and len(conflict) == 3:
                doc1_name, doc2_name, metadata = conflict
                conflict_type = metadata.get("type", "unknown")
                doc1_title = doc1_name
                doc2_title = doc2_name
            else:
                # Dict format
                doc1 = conflict.get("document_1", {})
                doc2 = conflict.get("document_2", {})
                doc1_title = (
                    doc1.get("title", "Unknown")
                    if isinstance(doc1, dict)
                    else str(doc1)
                )
                doc2_title = (
                    doc2.get("title", "Unknown")
                    if isinstance(doc2, dict)
                    else str(doc2)
                )
                # severity currently unused in formatted output
                conflict_type = conflict.get("conflict_type", "unknown")

            formatted += f"**{i}. Conflict Type: {conflict_type}**\n"
            formatted += f"• Document 1: {doc1_title}\n"
            formatted += f"• Document 2: {doc2_title}\n"

            # Only check for conflicting_statements in dict format
            if isinstance(conflict, dict) and "conflicting_statements" in conflict:
                statements = conflict["conflicting_statements"]
                if statements:
                    formatted += f"• Conflicting statements found: {len(statements)}\n"

            formatted += "\n"

        # Add resolution suggestions if available
        suggestions = conflicts.get("resolution_suggestions", {})
        if suggestions:
            formatted += "💡 **Resolution Suggestions:**\n"
            if isinstance(suggestions, dict):
                # Handle dict format
                for _key, suggestion in list(suggestions.items())[
                    :2
                ]:  # Show top 2 suggestions
                    formatted += f"• {suggestion}\n"
            else:
                # Handle list format
                for suggestion in suggestions[:2]:  # Show top 2 suggestions
                    formatted += f"• {suggestion}\n"

        return formatted

    @staticmethod
    def format_complementary_content(complementary: list[dict[str, Any]]) -> str:
        """Format complementary content results for display."""
        if not complementary:
            return "🔍 **Complementary Content**\n\nNo complementary content found."

        formatted = (
            f"🔗 **Complementary Content** ({len(complementary)} recommendations)\n\n"
        )

        for i, content in enumerate(complementary[:5], 1):  # Show top 5
            document = content.get("document", {})
            relevance = content.get("relevance_score", 0)

            # Flattened or nested title
            title_value = content.get("title") or content.get("source_title")
            if not title_value:
                if isinstance(document, dict):
                    title_value = document.get("source_title") or "Unknown"
                else:
                    title_value = getattr(document, "source_title", "Unknown")
            title_value = title_value or "Unknown"

            # Reasons and strategy
            reason = (
                content.get("reason") or content.get("recommendation_reason")
            ) or ""
            if not reason and isinstance(document, dict):
                reason = document.get("recommendation_reason", "") or document.get(
                    "reason", ""
                )
            elif not reason and document is not None:
                reason = getattr(document, "recommendation_reason", "") or getattr(
                    document, "reason", ""
                )
            strategy = content.get("strategy")

            formatted += f"**{i}. Complementary Score: {relevance:.3f}**\n"
            formatted += f"• Title: {title_value}\n"
            if reason:
                formatted += f"• Why Complementary: {reason}\n"
            if strategy:
                formatted += f"• Strategy: {strategy}\n"

            formatted += "\n"

        return formatted

    @staticmethod
    def format_document_clusters(clusters: dict[str, Any]) -> str:
        """Format document clustering results for display."""
        if not clusters or "clusters" not in clusters:
            return "🗂️ **Document Clustering**\n\nNo clusters found."

        cluster_list = clusters["clusters"]
        if not cluster_list:
            metadata = clusters.get("clustering_metadata", {})
            message = metadata.get("message", "No clusters found.")
            return f"🗂️ **Document Clustering**\n\n{message}"

        formatted = "🗂️ **Document Clustering Results**\n\n"

        for i, cluster in enumerate(cluster_list[:5], 1):  # Show first 5 clusters
            documents = cluster.get("documents", [])
            cluster_metadata = (
                cluster.get("cluster_metadata", {}) if isinstance(cluster, dict) else {}
            )
            coherence = (
                cluster_metadata.get(
                    "coherence_score", cluster.get("coherence_score", 0)
                )
                if isinstance(cluster, dict)
                else 0
            )
            centroid_topics = (
                cluster_metadata.get(
                    "centroid_topics", cluster.get("centroid_topics", [])
                )
                if isinstance(cluster, dict)
                else []
            )
            shared_entities = (
                cluster_metadata.get(
                    "shared_entities", cluster.get("shared_entities", [])
                )
                if isinstance(cluster, dict)
                else []
            )
            cluster_summary = cluster.get("cluster_summary", "")

            cluster_id = (
                cluster_metadata.get("id", cluster.get("id", f"cluster_{i}"))
                if isinstance(cluster, dict)
                else f"cluster_{i}"
            )
            formatted += f"**Cluster {i} (ID: {cluster_id})**\n"
            formatted += f"• Documents: {len(documents)}\n"
            formatted += f"• Coherence Score: {coherence:.3f}\n"

            if centroid_topics:
                formatted += f"• Key Topics: {', '.join(centroid_topics[:3])}\n"  # Show top 3 topics

            if shared_entities:
                formatted += f"• Shared Entities: {', '.join(shared_entities[:3])}\n"  # Show top 3 entities

            if cluster_summary:
                formatted += f"• Summary: {cluster_summary}\n"

            formatted += "\n"

        # Add summary statistics
        total_docs = sum(len(cluster.get("documents", [])) for cluster in cluster_list)
        cluster_count = len(cluster_list)

        # Compute average coherence using nested cluster_metadata when present;
        # if no per-cluster coherence is provided at all, fall back to overall_coherence.
        per_cluster_coherences: list[float] = []
        any_coherence_present = False
        for cluster in cluster_list:
            if not isinstance(cluster, dict):
                per_cluster_coherences.append(0.0)
                continue
            cluster_metadata = cluster.get("cluster_metadata", {}) or {}
            if "coherence_score" in cluster_metadata:
                any_coherence_present = True
                value = cluster_metadata.get("coherence_score")
            elif "coherence_score" in cluster:
                any_coherence_present = True
                value = cluster.get("coherence_score")
            else:
                value = 0.0
            try:
                per_cluster_coherences.append(float(value))
            except (TypeError, ValueError):
                per_cluster_coherences.append(0.0)

        if cluster_count > 0 and any_coherence_present:
            avg_coherence = sum(per_cluster_coherences) / cluster_count
        else:
            metadata = clusters.get("clustering_metadata", {})
            try:
                avg_coherence = float(metadata.get("overall_coherence", 0.0))
            except (TypeError, ValueError):
                avg_coherence = 0.0

        formatted += "📊 **Summary:**\n"
        formatted += f"• Total Clusters: {len(cluster_list)}\n"
        formatted += f"• Total Documents: {total_docs}\n"
        formatted += f"• Average Coherence Score: {avg_coherence:.3f}\n"

        metadata = clusters.get("clustering_metadata", {})
        strategy = metadata.get("strategy", "unknown")
        formatted += f"• Strategy: {strategy}\n"

        original_query = metadata.get("original_query")
        if original_query:
            formatted += f"• Original Query: {original_query}\n"

        return formatted
