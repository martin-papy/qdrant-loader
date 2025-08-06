"""Response formatters for MCP server."""

from typing import Any

from ..search.components.search_result_models import HybridSearchResult


class MCPFormatters:
    """Response formatters for MCP server."""

    @staticmethod
    def format_search_result(result: HybridSearchResult) -> str:
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
    def format_attachment_search_result(result: HybridSearchResult) -> str:
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
        organized_results: dict[str, list[HybridSearchResult]]
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
    def create_structured_search_results(results: list[HybridSearchResult]) -> list[dict[str, Any]]:
        """Create structured results matching Qdrant document structure."""
        return [
            {
                # 🔥 ROOT LEVEL FIELDS (matching Qdrant structure)
                "score": result.score,
                "document_id": result.document_id or "",
                "title": result.get_display_title(),
                "content": result.text,
                "source_type": result.source_type,
                "source": result.repo_name or "",
                "url": result.source_url or "",
                "created_at": result.created_at or "",
                "updated_at": result.last_modified or "",
                
                # 🔥 NESTED METADATA (matching Qdrant structure)
                "metadata": {
                    # Project information
                    "project_id": result.project_id or "",
                    "project_name": result.project_name or "",
                    "project_description": result.project_description or "",
                    "collection_name": result.collection_name or "",
                    
                    # File information (from rich Qdrant metadata)
                    "file_path": result.file_path or "",
                    "file_name": result.original_filename or "",
                    "file_type": result.original_file_type or "",
                    "file_size": result.file_size,
                    
                    # Content analysis (from rich Qdrant metadata)
                    "word_count": result.word_count,
                    "char_count": result.char_count,
                    "estimated_read_time": result.estimated_read_time,
                    
                    # Chunking information (from rich Qdrant metadata)
                    "chunk_index": result.chunk_index,
                    "total_chunks": result.total_chunks,
                    "chunk_info": f"Chunk {result.chunk_index + 1}/{result.total_chunks}" if result.chunk_index is not None and result.total_chunks is not None else None,
                    "chunking_strategy": result.chunking_strategy or "",
                    
                    # Enhanced context and analysis
                    "hierarchy_context": result.get_hierarchy_info(),
                    "content_analysis": result.get_content_info(),
                    "semantic_analysis": result.get_semantic_info(),
                    "section_context": result.get_section_context(),
                    "attachment_info": result.get_attachment_info(),
                }
            }
            for result in results
        ]

    @staticmethod
    def create_lightweight_hierarchy_results(
        filtered_results: list[HybridSearchResult], 
        organized_results: dict[str, list[HybridSearchResult]] = None,
        query: str = ""
    ) -> dict[str, Any]:
        """Return minimal hierarchy data for fast navigation."""
        
        # Create hierarchy index with minimal data (up to 20 hierarchy nodes)
        hierarchy_index = []
        for result in filtered_results[:20]:
            hierarchy_index.append({
                "document_id": result.document_id,
                "title": result.source_title or "Untitled",
                "score": result.score,
                "hierarchy_info": {
                    "depth": MCPFormatters._extract_synthetic_depth(result),
                    "parent_id": MCPFormatters._extract_synthetic_parent_id(result),
                    "parent_title": MCPFormatters._extract_synthetic_parent_title(result),
                    "breadcrumb": MCPFormatters._extract_synthetic_breadcrumb(result),
                    "has_children": MCPFormatters._extract_has_children(result),
                    "source_type": result.source_type
                },
                "navigation_hints": {
                    "group": MCPFormatters._get_group_key(result),
                    "siblings_count": MCPFormatters._count_siblings(result, filtered_results),
                    "children_count": MCPFormatters._extract_children_count(result, filtered_results)
                }
            })
        
        # Create clean hierarchy groups
        hierarchy_groups = []
        if organized_results:
            for group_key, results in organized_results.items():
                hierarchy_groups.append({
                    "group_key": group_key,
                    "group_name": MCPFormatters._generate_clean_group_name(group_key, results),
                    "document_ids": [r.document_id for r in results],
                    "depth_range": [
                        min(getattr(r, 'depth', 0) or 0 for r in results),
                        max(getattr(r, 'depth', 0) or 0 for r in results)
                    ],
                    "total_documents": len(results)
                })

        return {
            "hierarchy_index": hierarchy_index,
            "hierarchy_groups": hierarchy_groups,
            "total_found": len(filtered_results),
            "query_metadata": {
                "search_query": query,
                "source_types_found": list(set(r.source_type for r in filtered_results))
            }
        }

    @staticmethod
    def _generate_clean_group_name(group_key: str, results: list) -> str:
        """Generate clear, short group names."""
        # Remove chunk/content prefixes from group names
        if group_key.startswith("Exists, limited clarity"):
            return "Technical Documentation"
        if group_key.startswith("Immediately begin compiling"):
            return "Product Management"
        if group_key.startswith("Purpose and Scope"):
            return "Project Overview"
        
        # Use first meaningful part of breadcrumb
        if " > " in group_key:
            return group_key.split(" > ")[0]
        
        # Truncate long names and add context
        if len(group_key) > 50:
            source_type = results[0].source_type if results else "unknown"
            return f"{group_key[:47]}... ({source_type.title()})"
        
        return group_key

    @staticmethod
    def _get_group_key(result) -> str:
        """Generate a stable group key for hierarchy organization."""
        # Try synthetic breadcrumb first
        synthetic_breadcrumb = MCPFormatters._extract_synthetic_breadcrumb(result)
        if synthetic_breadcrumb:
            if result.source_type == "confluence":
                return synthetic_breadcrumb
            elif result.source_type == "localfile":
                # Use root folder from breadcrumb
                return synthetic_breadcrumb.split(" > ")[0] if " > " in synthetic_breadcrumb else synthetic_breadcrumb
        
        # Fallback to file path for localfiles
        if result.source_type == "localfile" and result.file_path:
            path_parts = [p for p in result.file_path.split('/') if p and p != '.']
            return path_parts[0] if path_parts else "Root"
            
        # Fallback to title
        return result.source_title or "Uncategorized"

    @staticmethod
    def _count_siblings(result, all_results: list) -> int:
        """Count sibling documents at the same hierarchy level."""
        target_depth = MCPFormatters._extract_synthetic_depth(result)
        target_parent = MCPFormatters._extract_synthetic_parent_title(result)
        target_group = MCPFormatters._get_group_key(result)
        
        siblings = 0
        for other_result in all_results:
            other_depth = MCPFormatters._extract_synthetic_depth(other_result) 
            other_parent = MCPFormatters._extract_synthetic_parent_title(other_result)
            other_group = MCPFormatters._get_group_key(other_result)
            
            # Count as siblings if same depth and same parent/group
            if (other_depth == target_depth and 
                (other_parent == target_parent or other_group == target_group) and 
                other_result.document_id != result.document_id):
                siblings += 1
                
        return siblings

    @staticmethod
    def _extract_synthetic_depth(result) -> int:
        """Extract or synthesize depth information from available data."""
        # Try native hierarchy first
        if hasattr(result, 'depth') and result.depth is not None:
            return result.depth
            
        # For localfiles, use folder depth
        if result.source_type == "localfile" and result.file_path:
            path_parts = [p for p in result.file_path.split('/') if p and p != '.']
            return max(0, len(path_parts) - 1)  # Exclude filename
            
        # For confluence with section context
        if result.source_type == "confluence":
            section_context = getattr(result, 'section_context', '')
            if section_context and '[H' in section_context:
                # Extract header level from section context like "[H2]"
                try:
                    header_level = int(section_context.split('[H')[1][0])
                    return header_level - 1  # H1=0, H2=1, etc.
                except (IndexError, ValueError):
                    pass
                    
        return 0

    @staticmethod
    def _extract_synthetic_parent_id(result) -> str | None:
        """Extract or synthesize parent ID from available data."""
        # For chunked documents, use base document ID if different chunk
        try:
            chunk_index = getattr(result, 'chunk_index', 0)
            if isinstance(chunk_index, int) and chunk_index > 0:
                # Generate a parent ID for chunk 0 of the same document
                document_id = getattr(result, 'document_id', None)
                if document_id and isinstance(document_id, str):
                    base_id = document_id.split('-')[0]
                    return f"{base_id}-chunk-0" if base_id else None
        except (TypeError, AttributeError):
            pass
            
        return None

    @staticmethod
    def _extract_synthetic_parent_title(result) -> str | None:
        """Extract or synthesize parent title from available data."""
        try:
            # For localfiles, use parent folder name
            source_type = getattr(result, 'source_type', '')
            if source_type == "localfile":
                file_path = getattr(result, 'file_path', '')
                if file_path and isinstance(file_path, str):
                    path_parts = [p for p in file_path.split('/') if p and p != '.']
                    if len(path_parts) > 1:
                        return path_parts[-2]  # Parent folder
                        
            # For chunked documents, use the base document title
            chunk_index = getattr(result, 'chunk_index', 0)
            if isinstance(chunk_index, int) and chunk_index > 0:
                title = getattr(result, 'source_title', '') or ""
                if isinstance(title, str) and "(Chunk " in title:
                    return title.split("(Chunk ")[0].strip()
        except (TypeError, AttributeError):
            pass
                
        return None

    @staticmethod
    def _extract_synthetic_breadcrumb(result) -> str | None:
        """Extract or synthesize breadcrumb from available data."""
        # Try native breadcrumb first
        if hasattr(result, 'breadcrumb_text') and getattr(result, 'breadcrumb_text'):
            return result.breadcrumb_text
            
        # For localfiles, create breadcrumb from file path
        if result.source_type == "localfile" and result.file_path:
            path_parts = [p for p in result.file_path.split('/') if p and p != '.']
            if len(path_parts) > 1:
                return " > ".join(path_parts[:-1])  # Exclude filename
                
        # For confluence with section context, create from section info
        if result.source_type == "confluence":
            section_context = getattr(result, 'section_context', '')
            if section_context:
                # Extract section title from context like "[H2] Functions - Beta release"
                if ']' in section_context:
                    section_title = section_context.split(']', 1)[1].strip()
                    if section_title and '(#' in section_title:
                        section_title = section_title.split('(#')[0].strip()
                    return section_title
                    
        return None

    @staticmethod
    def _extract_has_children(result) -> bool:
        """Extract or synthesize has_children information."""
        try:
            # Try native hierarchy first
            if hasattr(result, 'has_children') and callable(getattr(result, 'has_children')):
                return result.has_children()
                
            # For chunked documents, check if this is not the last chunk
            chunk_index = getattr(result, 'chunk_index', 0)
            total_chunks = getattr(result, 'total_chunks', 1)
            if isinstance(chunk_index, int) and isinstance(total_chunks, int):
                return chunk_index < (total_chunks - 1)
        except (TypeError, AttributeError):
            pass
            
        return False

    @staticmethod
    def _extract_children_count(result, all_results: list) -> int:
        """Extract or synthesize children count from available data."""
        try:
            # Try native children count first
            children_count = getattr(result, 'children_count', None)
            if children_count is not None and isinstance(children_count, int):
                return children_count
                
            # For chunked documents, count remaining chunks in same document
            chunk_index = getattr(result, 'chunk_index', 0)
            total_chunks = getattr(result, 'total_chunks', 1)
            if isinstance(chunk_index, int) and isinstance(total_chunks, int):
                return max(0, total_chunks - chunk_index - 1)
                
            # For localfiles, count files in subdirectories (rough estimate)
            source_type = getattr(result, 'source_type', '')
            file_path = getattr(result, 'file_path', '')
            if (source_type == "localfile" and 
                file_path and isinstance(file_path, str) and 
                all_results):
                base_path = "/".join(file_path.split('/')[:-1])  # Remove filename
                children = 0
                for other in all_results:
                    other_source_type = getattr(other, 'source_type', '')
                    other_file_path = getattr(other, 'file_path', '')
                    if (other_source_type == "localfile" and 
                        other_file_path and isinstance(other_file_path, str) and
                        other_file_path.startswith(base_path + "/") and
                        other_file_path != file_path):
                        children += 1
                return min(children, 10)  # Cap to reasonable number
        except (TypeError, AttributeError):
            pass
            
        return 0

    @staticmethod
    def create_structured_hierarchy_results(
        filtered_results: list[HybridSearchResult], 
        organize_by_hierarchy: bool,
        organized_results: dict[str, list[HybridSearchResult]] = None
    ) -> dict[str, Any]:
        """Legacy method - replaced by create_lightweight_hierarchy_results."""
        # For backward compatibility during transition, delegate to lightweight version
        return MCPFormatters.create_lightweight_hierarchy_results(
            filtered_results, organized_results
        )

    @staticmethod
    def create_structured_attachment_results(
        filtered_results: list[HybridSearchResult], 
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