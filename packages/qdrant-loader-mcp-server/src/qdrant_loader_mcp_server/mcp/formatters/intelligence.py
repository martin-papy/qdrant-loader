"""
Intelligence Result Formatters - Analysis and Insights Formatting.

This module handles formatting of intelligence analysis results including
relationship analysis, similarity detection, conflict analysis, and
complementary content discovery.
"""

from typing import Any
from ...search.components.search_result_models import HybridSearchResult


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

        clusters = analysis.get("document_clusters", [])
        if clusters:
            formatted += "\n🗂️ **Document Clusters:**\n"
            for i, cluster in enumerate(clusters[:3], 1):  # Show first 3 clusters
                formatted += (
                    f"• Cluster {i}: {len(cluster.get('documents', []))} documents\n"
                )

        conflicts = analysis.get("conflict_analysis", {}).get("conflicting_pairs", [])
        if conflicts:
            formatted += f"\n⚠️ **Conflicts Detected:** {len(conflicts)} conflicting document pairs\n"

        return formatted

    @staticmethod
    def format_similar_documents(similar_docs: list[dict[str, Any]]) -> str:
        """Format similar documents results for display."""
        if not similar_docs:
            return "🔍 **Similar Documents**\n\nNo similar documents found."

        formatted = f"🔍 **Similar Documents** ({len(similar_docs)} found)\n\n"

        for i, doc_info in enumerate(similar_docs[:5], 1):  # Show top 5
            score = doc_info.get("similarity_score", 0)
            document = doc_info.get("document", {})
            reasons = doc_info.get("similarity_reasons", [])

            formatted += f"**{i}. Similarity Score: {score:.3f}**\n"
            if hasattr(document, "source_title"):
                formatted += f"• Title: {document.source_title}\n"
            if reasons:
                formatted += f"• Reasons: {', '.join(reasons)}\n"
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
            return "✅ **Conflict Analysis**\n\nNo conflicts detected between documents."

        formatted = f"⚠️ **Conflict Analysis** ({len(conflict_list)} conflicts found)\n\n"

        for i, conflict in enumerate(conflict_list[:3], 1):  # Show top 3 conflicts
            # Handle tuple format (doc1, doc2, metadata) or dict format
            if isinstance(conflict, tuple) and len(conflict) == 3:
                doc1_name, doc2_name, metadata = conflict
                conflict_type = metadata.get("type", "unknown")
                severity = metadata.get("severity", "unknown")
                doc1_title = doc1_name
                doc2_title = doc2_name
            else:
                # Dict format
                doc1 = conflict.get("document_1", {})
                doc2 = conflict.get("document_2", {})
                doc1_title = doc1.get('title', 'Unknown') if isinstance(doc1, dict) else str(doc1)
                doc2_title = doc2.get('title', 'Unknown') if isinstance(doc2, dict) else str(doc2)
                severity = conflict.get("severity", "unknown")
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
                for key, suggestion in list(suggestions.items())[:2]:  # Show top 2 suggestions
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

        formatted = f"🔗 **Complementary Content** ({len(complementary)} recommendations)\n\n"

        for i, content in enumerate(complementary[:5], 1):  # Show top 5
            document = content.get("document", {})
            relevance = content.get("relevance_score", 0)
            reason = content.get("recommendation_reason", "")

            formatted += f"**{i}. Complementary Score: {relevance:.3f}**\n"
            
            if hasattr(document, "source_title"):
                formatted += f"• Title: {document.source_title}\n"
            elif isinstance(document, dict):
                formatted += f"• Title: {document.get('source_title', 'Unknown')}\n"
            else:
                formatted += f"• Title: Sample Document\n"
                
            if reason:
                formatted += f"• Why Complementary: {reason}\n"
                
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

        formatted = f"🗂️ **Document Clustering Results**\n\n"

        for i, cluster in enumerate(cluster_list[:5], 1):  # Show first 5 clusters
            documents = cluster.get("documents", [])
            coherence = cluster.get("coherence_score", 0)
            centroid_topics = cluster.get("centroid_topics", [])
            shared_entities = cluster.get("shared_entities", [])
            cluster_summary = cluster.get("cluster_summary", "")

            cluster_id = cluster.get("id", f"cluster_{i}")
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
        avg_coherence = sum(cluster.get("coherence_score", 0) for cluster in cluster_list) / len(cluster_list)
        
        formatted += f"📊 **Summary:**\n"
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
