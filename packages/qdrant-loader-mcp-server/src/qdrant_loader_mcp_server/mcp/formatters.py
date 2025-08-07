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
    def create_lightweight_similar_documents_results(
        similar_docs: list[dict[str, Any]], 
        target_query: str = "",
        comparison_query: str = ""
    ) -> dict[str, Any]:
        """Return minimal similar documents data for fast navigation."""
        
        # Create similarity index with minimal data
        similarity_index = []
        for doc_info in similar_docs:
            document = doc_info.get("document", {})
            
            # Handle both HybridSearchResult objects and dict formats
            if hasattr(document, 'document_id'):
                doc_id = document.document_id
                title = document.source_title or "Untitled"
                source_type = document.source_type
                text_length = len(document.text) if document.text else 0
            else:
                # Fallback for dict format
                doc_id = document.get("document_id") or doc_info.get("document_id")
                title = document.get("source_title", "Untitled") 
                source_type = document.get("source_type", "unknown")
                text_length = len(document.get("text", ""))
            
            similarity_index.append({
                "document_id": doc_id,
                "title": title,
                "similarity_score": doc_info.get("similarity_score", 0),
                "similarity_info": {
                    "metric_scores": doc_info.get("metric_scores", {}),
                    "similarity_reasons": doc_info.get("similarity_reasons", []),
                    "source_type": source_type
                },
                "navigation_hints": {
                    "can_expand": True,
                    "has_content": text_length > 0,
                    "content_length": text_length,
                    "expand_tool": "search"  # Tool to get full document content
                }
            })
        
        # Extract similarity metrics used
        metrics_used = []
        if similar_docs:
            first_doc_metrics = similar_docs[0].get("metric_scores", {})
            metrics_used = list(first_doc_metrics.keys())
        
        return {
            "similarity_index": similarity_index,
            "query_info": {
                "target_query": target_query,
                "comparison_query": comparison_query,
                "total_found": len(similarity_index),
                "metrics_used": metrics_used
            },
            "navigation": {
                "supports_lazy_loading": True,
                "expand_document_tool": "search",  # Tool to get full document content
                "sort_order": "similarity_desc",
                "max_displayed": len(similarity_index)
            }
        }

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
    def create_lightweight_conflict_results(
        conflicts: dict[str, Any], 
        query: str = "",
        documents: list = None
    ) -> dict[str, Any]:
        """Create lightweight conflict results for fast navigation and lazy loading."""
        
        conflicting_pairs = conflicts.get("conflicting_pairs", [])
        
        # Create conflict index with comprehensive information
        conflict_index = []
        involved_document_ids = set()
        
        for i, (doc1_id, doc2_id, conflict_info) in enumerate(conflicting_pairs):
            conflict_id = f"conf_{i+1:03d}"
            
            # Extract document titles from IDs or use the IDs themselves
            title_1 = doc1_id.split(":", 1)[-1] if ":" in doc1_id else doc1_id
            title_2 = doc2_id.split(":", 1)[-1] if ":" in doc2_id else doc2_id
            
            # Extract conflicting statements from structured indicators
            conflicting_statements = []
            structured_indicators = conflict_info.get("structured_indicators", [])
            
            for indicator in structured_indicators:
                if isinstance(indicator, dict) and "doc1_snippet" in indicator and "doc2_snippet" in indicator:
                    conflicting_statements.append({
                        "from_doc1": indicator["doc1_snippet"],
                        "from_doc2": indicator["doc2_snippet"]
                    })
            
            # If no structured indicators, try to extract from basic indicators
            if not conflicting_statements and conflict_info.get("indicators"):
                # Fallback: create generic conflicting statements
                indicators = conflict_info.get("indicators", [])
                if indicators:
                    conflicting_statements.append({
                        "from_doc1": f"Document contains: {indicators[0] if indicators else 'conflicting information'}",
                        "from_doc2": f"Document contains: {indicators[1] if len(indicators) > 1 else 'different information'}"
                    })
            
            # Create rich conflict entry with comprehensive information
            conflict_entry = {
                "conflict_id": conflict_id,
                "document_1_id": doc1_id,
                "document_2_id": doc2_id,
                "conflict_type": conflict_info.get("type", "unknown"),
                "confidence_score": round(conflict_info.get("confidence", 0.0), 3),
                "title_1": title_1[:100] + "..." if len(title_1) > 100 else title_1,
                "title_2": title_2[:100] + "..." if len(title_2) > 100 else title_2,
                "summary": conflict_info.get("description", "Potential conflict detected"),
                "detailed_description": conflict_info.get("description", "Documents contain contradictory or inconsistent information"),
                "resolution_suggestion": MCPFormatters._generate_conflict_resolution_suggestion(conflict_info),
                "conflict_indicators": conflict_info.get("indicators", []),
                "conflicting_statements": conflicting_statements,
                "analysis_tier": conflict_info.get("analysis_tier", "unknown"),
                "tier_score": round(conflict_info.get("tier_score", 0.0), 3),
                "affected_sections": MCPFormatters._extract_affected_sections(conflict_info)
            }
            
            conflict_index.append(conflict_entry)
            involved_document_ids.add(doc1_id)
            involved_document_ids.add(doc2_id)
        
        # Create document index for involved documents
        document_index = []
        if documents:
            # Create a lookup for document details
            doc_lookup = {}
            for doc in documents:
                doc_id = doc.document_id or f"{doc.source_type}:{doc.source_title}"
                doc_lookup[doc_id] = doc
            
            # Build document index for involved documents
            for doc_id in involved_document_ids:
                if doc_id in doc_lookup:
                    doc = doc_lookup[doc_id]
                    document_index.append({
                        "document_id": doc_id,
                        "title": doc.source_title or "Untitled",
                        "source_type": doc.source_type,
                        "text_length": len(doc.text) if doc.text else 0,
                        "conflict_count": sum(1 for conflict in conflict_index 
                                             if conflict["document_1_id"] == doc_id or conflict["document_2_id"] == doc_id),
                        "last_modified": doc.last_modified if hasattr(doc, 'last_modified') else None
                    })
                else:
                    # Fallback for documents not in the lookup
                    document_index.append({
                        "document_id": doc_id,
                        "title": doc_id.split(":", 1)[-1] if ":" in doc_id else doc_id,
                        "source_type": doc_id.split(":", 1)[0] if ":" in doc_id else "unknown",
                        "text_length": 0,
                        "conflict_count": sum(1 for conflict in conflict_index 
                                             if conflict["document_1_id"] == doc_id or conflict["document_2_id"] == doc_id),
                        "last_modified": None
                    })
        
        # Create conflict summary
        conflict_types = {}
        for conflict in conflict_index:
            conflict_type = conflict["conflict_type"]
            conflict_types[conflict_type] = conflict_types.get(conflict_type, 0) + 1
        
        conflict_summary = {
            "total_documents_analyzed": conflicts.get("query_metadata", {}).get("document_count", 0),
            "documents_with_conflicts": len(involved_document_ids),
            "total_conflicts_found": len(conflict_index),
            "conflict_types": conflict_types,
            "highest_confidence_score": max([c["confidence_score"] for c in conflict_index], default=0.0)
        }
        
        # Analysis metadata
        analysis_metadata = conflicts.get("query_metadata", {})
        analysis_metadata.update({
            "analysis_strategy": "tiered_analysis",
            "response_type": "lightweight"
        })
        
        # Convert conflict_index to the expected schema format
        conflicts_detected = []
        for conflict in conflict_index:
            # Find document details for the conflicting documents
            doc1_info = next((doc for doc in document_index if doc["document_id"] == conflict["document_1_id"]), None)
            doc2_info = next((doc for doc in document_index if doc["document_id"] == conflict["document_2_id"]), None)
            
            conflicts_detected.append({
                "conflict_id": conflict["conflict_id"],
                "document_1": {
                    "title": doc1_info["title"] if doc1_info else conflict["title_1"],
                    "content_preview": "",  # Can be populated if needed
                    "source_type": doc1_info["source_type"] if doc1_info else "unknown",
                    "document_id": conflict["document_1_id"]  # Add this for expand_document compatibility
                },
                "document_2": {
                    "title": doc2_info["title"] if doc2_info else conflict["title_2"],
                    "content_preview": "",  # Can be populated if needed
                    "source_type": doc2_info["source_type"] if doc2_info else "unknown",
                    "document_id": conflict["document_2_id"]  # Add this for expand_document compatibility
                },
                "conflict_type": conflict["conflict_type"],
                "conflict_score": conflict["confidence_score"],
                "conflict_description": conflict["summary"],
                "conflicting_statements": MCPFormatters._extract_conflicting_statements(conflict_info),
                "analysis_tier": conflict["analysis_tier"]  # Keep our enhancement
            })
        
        # Update conflict summary to match expected format
        updated_conflict_summary = {
            "total_documents_analyzed": conflict_summary["total_documents_analyzed"],
            "conflicts_found": conflict_summary["total_conflicts_found"],
            "conflict_types": list(conflict_summary["conflict_types"].keys()),
            "highest_conflict_score": conflict_summary["highest_confidence_score"]
        }
        
        return {
            "conflicts_detected": conflicts_detected,
            "conflict_summary": updated_conflict_summary,
            "analysis_metadata": analysis_metadata,
            "document_index": document_index,  # Keep for our enhancement
            "navigation": {
                "total_conflicts": len(conflict_index),
                "max_displayed": len(conflict_index),
                "can_expand_documents": True,
                "expand_tool": "expand_document"
            }
        }

    @staticmethod
    def _extract_conflicting_statements(conflict_info: dict[str, Any]) -> list[dict[str, str]]:
        """Extract actual conflicting statements from structured conflict data."""
        statements = []
        
        # Check if we have new structured indicators
        structured_indicators = conflict_info.get("structured_indicators", [])
        
        if structured_indicators:
            # Use the new structured data with actual text snippets
            for indicator in structured_indicators[:3]:  # Limit to 3 for brevity
                doc1_snippet = indicator.get("doc1_snippet", "[Content not available]")
                doc2_snippet = indicator.get("doc2_snippet", "[Content not available]")
                
                statements.append({
                    "from_doc1": doc1_snippet,
                    "from_doc2": doc2_snippet
                })
        else:
            # Fallback to old format (summary only)
            indicators = conflict_info.get("indicators", [])
            for indicator in indicators[:3]:
                statements.append({
                    "from_doc1": indicator,
                    "from_doc2": indicator
                })
        
        return statements

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
    def create_lightweight_cluster_results(
        clustering_results: dict[str, Any], 
        query: str = ""
    ) -> dict[str, Any]:
        """Create lightweight cluster results for lazy loading following hierarchy_search pattern."""
        
        clusters = clustering_results.get("clusters", [])
        metadata = clustering_results.get("clustering_metadata", {})
        
        # Create cluster index with minimal data (limit documents per cluster for performance)
        cluster_index = []
        total_documents_shown = 0
        max_docs_per_cluster = 5  # Show only first 5 documents per cluster initially
        
        for cluster in clusters:
            cluster_documents = cluster.get("documents", [])
            
            # Create lightweight document entries (only first few per cluster)
            lightweight_docs = []
            for doc in cluster_documents[:max_docs_per_cluster]:
                doc_id = None
                title = "Untitled"
                source_type = "unknown"
                
                if hasattr(doc, 'document_id'):
                    doc_id = doc.document_id
                    title = doc.source_title or doc.get_display_title()
                    source_type = doc.source_type
                elif hasattr(doc, 'source_title'):
                    doc_id = f"{doc.source_type}:{doc.source_title}"
                    title = doc.source_title
                    source_type = doc.source_type
                elif isinstance(doc, dict):
                    doc_id = doc.get("document_id", "")
                    title = (doc.get("title") or doc.get("source_title") or 
                            doc.get("parent_document_title") or "Untitled")
                    source_type = doc.get("source_type", "unknown")
                
                lightweight_docs.append({
                    "document_id": doc_id,
                    "title": title,
                    "source_type": source_type,
                    "cluster_relevance": 1.0
                })
                total_documents_shown += 1
            
            # Build cluster info
            cluster_info = {
                "cluster_id": cluster.get("id", f"cluster_{len(cluster_index)}"),
                "cluster_name": cluster.get("name", f"Cluster {len(cluster_index) + 1}"),
                "cluster_theme": cluster.get("cluster_summary", "Mixed documents"),
                "document_count": len(cluster_documents),
                "documents_shown": len(lightweight_docs),
                "coherence_score": cluster.get("coherence_score", 0.0),
                "representative_doc_id": cluster.get("representative_doc_id"),
                "cluster_strategy": cluster.get("cluster_strategy", metadata.get("strategy", "mixed_features")),
                "quality_metrics": cluster.get("quality_metrics", {}),
                "documents": lightweight_docs,
                "cluster_metadata": {
                    "shared_entities": cluster.get("shared_entities", [])[:5],  # Limit to first 5
                    "shared_topics": cluster.get("centroid_topics", [])[:5],   # Limit to first 5
                    "cluster_keywords": cluster.get("cluster_keywords", [])[:5]
                }
            }
            cluster_index.append(cluster_info)
        
        # Create enhanced clustering metadata
        enhanced_metadata = {
            "strategy": metadata.get("strategy", "mixed_features"),
            "total_documents": metadata.get("total_documents", 0),
            "clusters_created": metadata.get("clusters_created", len(clusters)),
            "unclustered_documents": metadata.get("unclustered_documents", 0),
            "document_retrieval_rate": metadata.get("document_retrieval_rate", 1.0),
            "clustering_quality": metadata.get("clustering_quality", 0.0),
            "processing_time_ms": metadata.get("processing_time_ms", 0),
            "strategy_performance": metadata.get("strategy_performance", {}),
            "recommendations": metadata.get("recommendations", {}),
            "query_metadata": {
                "search_query": query,
                "documents_shown": total_documents_shown,
                "max_docs_per_cluster": max_docs_per_cluster,
                "lazy_loading_enabled": True
            }
        }
        
        return {
            "cluster_index": cluster_index,
            "clustering_metadata": enhanced_metadata,
            "expansion_info": {
                "cluster_expansion_available": True,
                "document_expansion_available": True,
                "expansion_instructions": "Use expand_document tool with document_id or expand_cluster with cluster_id for full content"
            }
        }

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
    def create_lightweight_complementary_results(
        complementary_recommendations: list[dict[str, Any]],
        target_document: 'HybridSearchResult' = None,
        context_documents_analyzed: int = 0,
        target_query: str = ""
    ) -> dict[str, Any]:
        """Create lightweight complementary content results for lazy loading."""
        
        # Create complementary index with minimal data
        complementary_index = []
        for result in complementary_recommendations:
            document = result.get("document")
            if document:
                complementary_index.append({
                    "document_id": document.document_id,
                    "title": document.source_title or "Untitled",
                    "complementary_score": result.get("relevance_score", 0.0),
                    "complementary_reason": result.get("recommendation_reason", ""),
                    "relationship_type": result.get("strategy", "related"),
                    "source_type": document.source_type or "",
                    "basic_metadata": {
                        "project_id": document.project_id or "",
                        "created_at": document.created_at or "",
                        "source_url": document.source_url or ""
                    }
                    # NO content_preview - use expand_document for full content
                })
        
        # Target document info
        target_info = {
            "title": target_query,  # Fallback to query
            "content_preview": "",
            "source_type": ""
        }
        
        if target_document:
            target_info = {
                "document_id": target_document.document_id,
                "title": target_document.source_title or target_query,
                "source_type": target_document.source_type or ""
            }
        
        # Calculate summary statistics
        scores = [item.get("complementary_score", 0.0) for item in complementary_index]
        relationship_types = [item.get("relationship_type", "related") for item in complementary_index]
        
        return {
            "complementary_index": complementary_index,
            "target_document": target_info,
            "complementary_summary": {
                "total_analyzed": context_documents_analyzed,
                "complementary_found": len(complementary_index),
                "highest_score": max(scores, default=0.0),
                "relationship_types": list(set(relationship_types))
            },
            "lazy_loading_enabled": True,
            "expand_document_hint": "Use expand_document tool with document_id for full content"
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

    @staticmethod
    def create_lightweight_attachment_results(
        filtered_results: list[HybridSearchResult], 
        attachment_filter: dict[str, Any],
        query: str = ""
    ) -> dict[str, Any]:
        """Return minimal attachment data for fast navigation and lazy loading."""
        
        # Create attachment index with minimal data (limit to 20 for performance)
        attachment_index = []
        for result in filtered_results[:20]:
            attachment_index.append({
                "document_id": result.document_id,
                "title": result.source_title or "Untitled",
                "score": result.score,
                "attachment_info": {
                    "filename": MCPFormatters._extract_safe_filename(result),
                    "file_type": MCPFormatters._extract_file_type_minimal(result),
                    "file_size": result.file_size if result.file_size and result.file_size > 0 else None,
                    "source_type": result.source_type
                },
                "navigation_hints": {
                    "parent_document": result.parent_document_title or result.parent_title,
                    "project_context": result.project_name or result.project_id,
                    "content_preview": result.text[:100] + "..." if result.text else None
                }
            })
        
        # Create attachment groups for better organization
        attachment_groups = MCPFormatters._organize_attachments_by_type(filtered_results)
        
        return {
            "attachment_index": attachment_index,
            "attachment_groups": attachment_groups,
            "total_found": len(filtered_results),
            "query_metadata": {
                "search_query": query,
                "source_types_found": list(set(r.source_type for r in filtered_results)),
                "filters_applied": attachment_filter
            }
        }

    @staticmethod
    def _extract_safe_filename(result: HybridSearchResult) -> str:
        """Fast filename extraction with minimal processing."""
        # Quick priority check - avoid expensive validation
        if result.original_filename and len(result.original_filename) < 200:
            return result.original_filename
        
        if result.file_path:
            import os
            return os.path.basename(result.file_path)
        
        # Fallback to source title but clean it
        title = result.source_title or "untitled"
        # Quick clean - remove obvious chunk indicators
        if "(Chunk " in title:
            title = title.split("(Chunk ")[0].strip()
        
        return title[:100]  # Truncate for safety

    @staticmethod
    def _extract_file_type_minimal(result: HybridSearchResult) -> str:
        """Fast file type detection - minimal processing."""
        # Priority order with early returns for performance
        if result.mime_type:
            return result.mime_type.split('/')[-1]  # Get extension from MIME
        
        # Try multiple filename sources for extension extraction
        filename_candidates = [
            result.original_filename,
            result.source_title,
            result.file_path.split('/')[-1] if result.file_path else None
        ]
        
        for filename in filename_candidates:
            if filename and '.' in filename:
                ext = filename.split('.')[-1].lower().strip()
                # Valid file extensions and common document types
                if len(ext) <= 5 and ext.isalnum():
                    return ext
        
        return "unknown"

    @staticmethod
    def _organize_attachments_by_type(results: list[HybridSearchResult]) -> list[dict]:
        """Organize attachments into logical groups for navigation."""
        from collections import defaultdict
        
        type_groups = defaultdict(list)
        
        for result in results:
            # Group by file type first
            file_type = MCPFormatters._extract_file_type_minimal(result)
            group_key = MCPFormatters._get_attachment_group_key(file_type, result.source_type)
            type_groups[group_key].append(result.document_id)
        
        # Convert to structured format
        groups = []
        for group_key, doc_ids in type_groups.items():
            if len(doc_ids) >= 1:  # Include all groups, even single files
                groups.append({
                    "group_key": group_key,
                    "group_name": MCPFormatters._generate_friendly_group_name(group_key),
                    "document_ids": doc_ids,
                    "file_count": len(doc_ids)
                })
        
        # Sort by file count (most common types first)
        return sorted(groups, key=lambda g: g["file_count"], reverse=True)

    @staticmethod
    def _get_attachment_group_key(file_type: str, source_type: str) -> str:
        """Generate logical grouping keys for attachments."""
        # Map to broader categories for better UX
        document_types = {"pdf", "doc", "docx", "txt", "md"}
        spreadsheet_types = {"xls", "xlsx", "csv"}
        image_types = {"png", "jpg", "jpeg", "gif", "svg"}
        
        if file_type in document_types:
            return f"documents_{source_type}"
        elif file_type in spreadsheet_types:
            return f"spreadsheets_{source_type}"
        elif file_type in image_types:
            return f"images_{source_type}"
        else:
            return f"other_{source_type}"

    @staticmethod
    def _generate_friendly_group_name(group_key: str) -> str:
        """Generate user-friendly group names."""
        # Parse the group key format: "type_source"
        if "_" in group_key:
            file_category, source_type = group_key.split("_", 1)
            
            # Capitalize and format
            category_map = {
                "documents": "Documents",
                "spreadsheets": "Spreadsheets", 
                "images": "Images",
                "other": "Other Files"
            }
            
            source_map = {
                "confluence": "Confluence",
                "localfile": "Local Files",
                "git": "Git Repository",
                "jira": "Jira"
            }
            
            category = category_map.get(file_category, file_category.title())
            source = source_map.get(source_type, source_type.title())
            
            return f"{category} ({source})"
        
        return group_key.title()

    @staticmethod
    def _generate_conflict_resolution_suggestion(conflict_info: dict) -> str:
        """Generate a resolution suggestion based on conflict type and information."""
        conflict_type = conflict_info.get("type", "unknown")
        
        if conflict_type == "version_conflict":
            return "Review documents for version consistency and update outdated information"
        elif conflict_type == "contradictory_guidance":
            return "Reconcile contradictory guidance by consulting authoritative sources or stakeholders"
        elif conflict_type == "procedural_conflict":
            return "Establish a single, authoritative procedure and deprecate conflicting processes"
        elif conflict_type == "requirement_conflict":
            return "Clarify requirements with stakeholders and update documentation to resolve ambiguity"
        elif conflict_type == "implementation_conflict":
            return "Review implementation approaches and standardize on the preferred solution"
        else:
            return "Review conflicting information and establish a single source of truth"

    @staticmethod
    def _extract_affected_sections(conflict_info: dict) -> list:
        """Extract affected sections from conflict information."""
        affected_sections = []
        
        # Try to identify sections from structured indicators
        structured_indicators = conflict_info.get("structured_indicators", [])
        for indicator in structured_indicators:
            if isinstance(indicator, dict):
                # Look for section keywords in the snippets
                doc1_snippet = indicator.get("doc1_snippet", "")
                doc2_snippet = indicator.get("doc2_snippet", "")
                
                sections = set()
                for snippet in [doc1_snippet, doc2_snippet]:
                    # Common section patterns
                    if "introduction" in snippet.lower():
                        sections.add("Introduction")
                    elif "requirement" in snippet.lower():
                        sections.add("Requirements")
                    elif "procedure" in snippet.lower() or "process" in snippet.lower():
                        sections.add("Procedures")
                    elif "implementation" in snippet.lower():
                        sections.add("Implementation")
                    elif "configuration" in snippet.lower() or "config" in snippet.lower():
                        sections.add("Configuration")
                    elif "guideline" in snippet.lower() or "guide" in snippet.lower():
                        sections.add("Guidelines")
                
                affected_sections.extend(list(sections))
        
        # Remove duplicates and return
        return list(set(affected_sections)) if affected_sections else ["Content"] 