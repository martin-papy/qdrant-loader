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
        if not conflicts or "conflicts" not in conflicts:
            return "⚠️ **Conflict Analysis**\n\nNo conflicts detected."

        conflict_list = conflicts["conflicts"]
        if not conflict_list:
            return "⚠️ **Conflict Analysis**\n\nNo conflicts detected."

        formatted = f"⚠️ **Conflict Analysis** ({len(conflict_list)} conflicts detected)\n\n"

        for i, conflict in enumerate(conflict_list[:3], 1):  # Show top 3 conflicts
            doc1 = conflict.get("document_1", {})
            doc2 = conflict.get("document_2", {})
            severity = conflict.get("severity", "unknown")
            conflict_type = conflict.get("conflict_type", "unknown")

            formatted += f"**{i}. {conflict_type.title()} Conflict (Severity: {severity.upper()})**\n"
            formatted += f"• Document 1: {doc1.get('title', 'Unknown')}\n"
            formatted += f"• Document 2: {doc2.get('title', 'Unknown')}\n"

            if "conflicting_statements" in conflict:
                statements = conflict["conflicting_statements"]
                if statements:
                    formatted += f"• Conflicting statements found: {len(statements)}\n"

            formatted += "\n"

        # Add resolution suggestions if available
        suggestions = conflicts.get("resolution_suggestions", [])
        if suggestions:
            formatted += "💡 **Resolution Suggestions:**\n"
            for suggestion in suggestions[:2]:  # Show top 2 suggestions
                formatted += f"• {suggestion}\n"

        return formatted

    @staticmethod
    def format_complementary_content(complementary: list[dict[str, Any]]) -> str:
        """Format complementary content results for display."""
        if not complementary:
            return "🔗 **Complementary Content**\n\nNo complementary content found."

        formatted = f"🔗 **Complementary Content** ({len(complementary)} recommendations)\n\n"

        for i, content in enumerate(complementary[:5], 1):  # Show top 5
            document = content.get("document", {})
            relationship = content.get("relationship_type", "related")
            relevance = content.get("relevance_score", 0)

            formatted += f"**{i}. {relationship.title()} Content (Relevance: {relevance:.3f})**\n"
            
            if hasattr(document, "source_title"):
                formatted += f"• Title: {document.source_title}\n"
            elif isinstance(document, dict):
                formatted += f"• Title: {document.get('source_title', 'Unknown')}\n"
                
            reasons = content.get("reasons", [])
            if reasons:
                formatted += f"• Why it's complementary: {', '.join(reasons)}\n"
                
            formatted += "\n"

        return formatted

    @staticmethod
    def format_document_clusters(clusters: dict[str, Any]) -> str:
        """Format document clustering results for display."""
        if not clusters or "clusters" not in clusters:
            return "🗂️ **Document Clusters**\n\nNo clusters found."

        cluster_list = clusters["clusters"]
        if not cluster_list:
            return "🗂️ **Document Clusters**\n\nNo clusters found."

        formatted = f"🗂️ **Document Clusters** ({len(cluster_list)} clusters found)\n\n"

        for i, cluster in enumerate(cluster_list[:5], 1):  # Show first 5 clusters
            documents = cluster.get("documents", [])
            themes = cluster.get("cluster_themes", [])
            coherence = cluster.get("coherence_score", 0)

            formatted += f"**{i}. Cluster {i} ({len(documents)} documents)**\n"
            formatted += f"• Coherence Score: {coherence:.3f}\n"
            
            if themes:
                formatted += f"• Themes: {', '.join(themes[:3])}\n"  # Show top 3 themes
                
            # Show first few document titles
            doc_titles = []
            for doc in documents[:3]:
                if hasattr(doc, "source_title"):
                    doc_titles.append(doc.source_title)
                elif isinstance(doc, dict):
                    doc_titles.append(doc.get("source_title", "Unknown"))
                    
            if doc_titles:
                formatted += f"• Documents: {', '.join(doc_titles)}\n"
                
            formatted += "\n"

        # Add summary statistics
        total_docs = sum(len(cluster.get("documents", [])) for cluster in cluster_list)
        avg_coherence = sum(cluster.get("coherence_score", 0) for cluster in cluster_list) / len(cluster_list)
        
        formatted += f"📊 **Summary:**\n"
        formatted += f"• Total Documents Clustered: {total_docs}\n"
        formatted += f"• Average Coherence Score: {avg_coherence:.3f}\n"
        
        strategy = clusters.get("query_metadata", {}).get("strategy", "unknown")
        formatted += f"• Clustering Strategy: {strategy}\n"

        return formatted
