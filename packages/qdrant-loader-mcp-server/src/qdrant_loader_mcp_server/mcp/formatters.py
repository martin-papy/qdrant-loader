"""Response formatters for MCP server."""

from typing import Any

from ..search.models import SearchResult


class MCPFormatters:
    """Response formatters for MCP server."""

    @staticmethod
    def format_search_result(result: SearchResult) -> str:
        """Format a search result for display."""
        formatted_result = f"Score: {result.score}\n"
        formatted_result += f"Text: {result.text}\n"
        formatted_result += f"Source: {result.source_type}"

        if result.source_title:
            formatted_result += f" - {result.source_title}"

        # Add project information if available
        project_info = result.get_project_info()
        if project_info:
            formatted_result += f"\n🏗️ {project_info}"

        # Add attachment information if this is a file attachment
        if result.is_attachment:
            formatted_result += "\n📎 Attachment"
            if result.original_filename:
                formatted_result += f": {result.original_filename}"
            if result.attachment_context:
                formatted_result += f"\n📋 {result.attachment_context}"
            if result.parent_document_title:
                formatted_result += f"\n📄 Attached to: {result.parent_document_title}"

        # Add hierarchy context for Confluence documents
        if result.source_type == "confluence" and result.breadcrumb_text:
            formatted_result += f"\n📍 Path: {result.breadcrumb_text}"

        if result.source_url:
            formatted_result += f" ({result.source_url})"

        if result.file_path:
            formatted_result += f"\nFile: {result.file_path}"

        if result.repo_name:
            formatted_result += f"\nRepo: {result.repo_name}"

        # Add hierarchy information for Confluence documents
        if result.source_type == "confluence" and result.hierarchy_context:
            formatted_result += f"\n🏗️ {result.hierarchy_context}"

        # Add parent information if available (for hierarchy, not attachments)
        if result.parent_title and not result.is_attachment:
            formatted_result += f"\n⬆️ Parent: {result.parent_title}"

        # Add children count if available
        if result.has_children():
            formatted_result += f"\n⬇️ Children: {result.children_count}"

        return formatted_result

    @staticmethod
    def format_attachment_search_result(result: SearchResult) -> str:
        """Format an attachment search result for display."""
        formatted_result = f"Score: {result.score}\n"
        formatted_result += f"Text: {result.text}\n"
        formatted_result += f"Source: {result.source_type}"

        if result.source_title:
            formatted_result += f" - {result.source_title}"

        # Add attachment information
        formatted_result += "\n📎 Attachment"
        if result.original_filename:
            formatted_result += f": {result.original_filename}"
        if result.attachment_context:
            formatted_result += f"\n📋 {result.attachment_context}"
        if result.parent_document_title:
            formatted_result += f"\n📄 Attached to: {result.parent_document_title}"

        # Add hierarchy context for Confluence documents
        if result.source_type == "confluence" and result.breadcrumb_text:
            formatted_result += f"\n📍 Path: {result.breadcrumb_text}"

        if result.source_url:
            formatted_result += f" ({result.source_url})"

        if result.file_path:
            formatted_result += f"\nFile: {result.file_path}"

        if result.repo_name:
            formatted_result += f"\nRepo: {result.repo_name}"

        # Add hierarchy information for Confluence documents
        if result.source_type == "confluence" and result.hierarchy_context:
            formatted_result += f"\n🏗️ {result.hierarchy_context}"

        # Add parent information if available (for hierarchy, not attachments)
        if result.parent_title and not result.is_attachment:
            formatted_result += f"\n⬆️ Parent: {result.parent_title}"

        # Add children count if available
        if result.has_children():
            formatted_result += f"\n⬇️ Children: {result.children_count}"

        return formatted_result

    @staticmethod
    def format_hierarchical_results(
        organized_results: dict[str, list[SearchResult]]
    ) -> str:
        """Format hierarchically organized results for display."""
        formatted_sections = []

        for root_title, results in organized_results.items():
            section = f"📁 **{root_title}** ({len(results)} results)\n"

            for result in results:
                indent = "  " * (result.depth or 0)
                section += f"{indent}📄 {result.source_title}"
                if result.hierarchy_context:
                    section += f" | {result.hierarchy_context}"
                section += f" (Score: {result.score:.3f})\n"

                # Add a snippet of the content
                content_snippet = (
                    result.text[:150] + "..." if len(result.text) > 150 else result.text
                )
                section += f"{indent}   {content_snippet}\n"

                if result.source_url:
                    section += f"{indent}   🔗 {result.source_url}\n"
                section += "\n"

            formatted_sections.append(section)

        return (
            f"Found {sum(len(results) for results in organized_results.values())} results organized by hierarchy:\n\n"
            + "\n".join(formatted_sections)
        )

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
                formatted += f"• Cluster {i}: {len(cluster.get('documents', []))} documents\n"

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
            if hasattr(document, 'source_title'):
                formatted += f"• Title: {document.source_title}\n"
            if reasons:
                formatted += f"• Reasons: {', '.join(reasons)}\n"
            formatted += "\n"

        return formatted

    @staticmethod
    def format_conflict_analysis(conflicts: dict[str, Any]) -> str:
        """Format conflict analysis results for display."""
        conflicting_pairs = conflicts.get("conflicting_pairs", [])
        
        if not conflicting_pairs:
            return "✅ **Conflict Analysis**\n\nNo conflicts detected between documents."

        formatted = f"⚠️ **Conflict Analysis** ({len(conflicting_pairs)} conflicts found)\n\n"
        
        for i, (doc1, doc2, conflict_info) in enumerate(conflicting_pairs[:5], 1):
            conflict_type = conflict_info.get("type", "unknown")
            formatted += f"**{i}. Conflict Type: {conflict_type}**\n"
            formatted += f"• Document 1: {doc1}\n"
            formatted += f"• Document 2: {doc2}\n\n"

        suggestions = conflicts.get("resolution_suggestions", {})
        if suggestions:
            formatted += "💡 **Resolution Suggestions:**\n"
            # Convert dict values to list and take first 3
            suggestion_list = list(suggestions.values())[:3]
            for suggestion in suggestion_list:
                formatted += f"• {suggestion}\n"

        return formatted

    @staticmethod
    def format_complementary_content(complementary: list[dict[str, Any]]) -> str:
        """Format complementary content results for display."""
        if not complementary:
            return "🔍 **Complementary Content**\n\nNo complementary content found."

        formatted = f"🔗 **Complementary Content** ({len(complementary)} recommendations)\n\n"
        
        for i, item in enumerate(complementary[:5], 1):  # Show top 5
            document = item.get("document", {})
            score = item.get("relevance_score", 0)  # Fixed: use correct key
            reason = item.get("recommendation_reason", "")  # Fixed: singular form
            
            formatted += f"**{i}. Complementary Score: {score:.3f}**\n"
            if hasattr(document, 'source_title'):
                formatted += f"• Title: {document.source_title}\n"
            if reason:
                formatted += f"• Why Complementary: {reason}\n"
            formatted += "\n"

        return formatted

    @staticmethod
    def format_document_clusters(clusters: dict[str, Any]) -> str:
        """Format document clustering results for display."""
        cluster_list = clusters.get("clusters", [])
        metadata = clusters.get("clustering_metadata", {})
        
        if not cluster_list:
            message = metadata.get("message", "No clusters could be formed.")
            return f"🗂️ **Document Clustering**\n\n{message}"

        formatted = f"""🗂️ **Document Clustering Results**

📊 **Clustering Summary:**
• Strategy: {metadata.get('strategy', 'unknown')}
• Total Clusters: {metadata.get('total_clusters', 0)}
• Total Documents: {metadata.get('total_documents', 0)}
• Original Query: {metadata.get('original_query', 'N/A')}

"""

        for i, cluster in enumerate(cluster_list[:5], 1):  # Show first 5 clusters
            formatted += f"**Cluster {i} (ID: {cluster.get('id', 'unknown')})**\n"
            formatted += f"• Documents: {len(cluster.get('documents', []))}\n"
            formatted += f"• Coherence Score: {cluster.get('coherence_score', 0):.3f}\n"
            
            topics = cluster.get('centroid_topics', [])
            if topics:
                formatted += f"• Key Topics: {', '.join(topics[:3])}\n"
            
            entities = cluster.get('shared_entities', [])
            if entities:
                formatted += f"• Shared Entities: {', '.join(entities[:3])}\n"
            
            summary = cluster.get('cluster_summary', '')
            if summary:
                formatted += f"• Summary: {summary}\n"
            
            formatted += "\n"

        return formatted

    @staticmethod
    def create_structured_search_results(results: list[SearchResult]) -> list[dict[str, Any]]:
        """Create structured results for MCP 2025-06-18 compliance."""
        return [
            {
                "score": result.score,
                "title": result.source_title or "Untitled",
                "content": result.text,
                "source_type": result.source_type,
                "metadata": {
                    "file_path": result.file_path or "",
                    "project_id": result.project_id or "",
                    "created_at": getattr(result, 'created_at', '') or "",
                    "last_modified": getattr(result, 'last_modified', '') or ""
                }
            }
            for result in results
        ]

    @staticmethod
    def create_structured_hierarchy_results(
        filtered_results: list[SearchResult], 
        organize_by_hierarchy: bool,
        organized_results: dict[str, list[SearchResult]] = None
    ) -> dict[str, Any]:
        """Create structured content for hierarchy search MCP compliance."""
        structured_results = []
        
        if organize_by_hierarchy and organized_results:
            # Flatten organized results for schema compliance
            for section, section_results in organized_results.items():
                for result in section_results:
                    structured_results.append({
                        "score": result.score,
                        "title": result.source_title or "Untitled", 
                        "content": result.text,
                        "hierarchy_path": getattr(result, 'hierarchy_path', section),
                        "parent_title": getattr(result, 'parent_title', '') or '',
                        "metadata": {
                            "space_key": getattr(result, 'space_key', '') or '',
                            "project_id": result.project_id or "",
                            "page_id": getattr(result, 'page_id', '') or '',
                            "hierarchy_level": getattr(result, 'depth', 0) or 0
                        }
                    })
        else:
            for result in filtered_results:
                structured_results.append({
                    "score": result.score,
                    "title": result.source_title or "Untitled",
                    "content": result.text,
                    "hierarchy_path": getattr(result, 'hierarchy_path', '') or '',
                    "parent_title": getattr(result, 'parent_title', '') or '',
                    "metadata": {
                        "space_key": getattr(result, 'space_key', '') or '',
                        "project_id": result.project_id or "",
                        "page_id": getattr(result, 'page_id', '') or '',
                        "hierarchy_level": getattr(result, 'depth', 0) or 0
                    }
                })

        return {
            "results": structured_results,
            "total_found": len(filtered_results),
            "hierarchy_organization": {
                "organized_by_hierarchy": organize_by_hierarchy,
                "hierarchy_groups": [
                    {"group_name": section, "document_count": len(results)}
                    for section, results in organized_results.items()
                ] if organize_by_hierarchy and organized_results else []
            }
        }

    @staticmethod
    def create_structured_attachment_results(
        filtered_results: list[SearchResult], 
        attachment_filter: dict[str, Any],
        include_parent_context: bool = True
    ) -> dict[str, Any]:
        """Create structured content for attachment search MCP compliance."""
        return {
            "results": [
                {
                    "score": result.score,
                    "title": result.source_title or "Untitled",
                    "content": result.text,
                    "attachment_info": {
                        "filename": getattr(result, 'file_name', result.source_title or "Untitled") or "Untitled",
                        "file_type": getattr(result, 'file_type', 'unknown') or 'unknown',
                        "file_size": getattr(result, 'file_size', 0) or 0,
                        "parent_document": (getattr(result, 'parent_document_title', '') or '') if include_parent_context else ""
                    },
                    "metadata": {
                        "file_path": result.file_path or "",
                        "project_id": result.project_id or "",
                        "upload_date": getattr(result, 'created_at', '') or "",
                        "author": getattr(result, 'author', '') or ""
                    }
                }
                for result in filtered_results
            ],
            "total_found": len(filtered_results),
            "attachment_summary": {
                "total_attachments": len(filtered_results),
                "file_types": list(set(getattr(result, 'file_type', 'unknown') for result in filtered_results)),
                "attachments_only": attachment_filter.get('attachments_only', False)
            }
        } 