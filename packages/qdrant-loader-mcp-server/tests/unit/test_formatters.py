"""
Comprehensive tests for MCPFormatters class.

Tests for all formatting methods including:
- Basic search result formatting
- Hierarchical result formatting  
- Analysis result formatting (relationship, conflict, similarity, clustering)
- Lightweight result creation for lazy loading
- Structured result creation for MCP compliance
- Helper methods and edge cases
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime
from typing import Any, Dict, List

from qdrant_loader_mcp_server.mcp.formatters import MCPFormatters
from qdrant_loader_mcp_server.search.components.search_result_models import HybridSearchResult


class TestMCPFormatters:
    """Test suite for MCPFormatters class."""

    @pytest.fixture
    def sample_search_result(self):
        """Create a sample HybridSearchResult for testing."""
        result = Mock(spec=HybridSearchResult)
        result.score = 0.85
        result.text = "This is sample content for testing the formatter functionality."
        result.source_type = "confluence"
        result.source_title = "Sample Document"
        result.source_url = "https://docs.example.com/sample"
        result.file_path = "/path/to/file.md"
        result.repo_name = "test-repo"
        result.project_id = "proj-123"
        result.project_name = "Test Project"
        result.project_description = "A test project"
        result.collection_name = "test_collection"
        result.document_id = "doc-456"
        result.created_at = "2024-01-01T00:00:00Z"
        result.last_modified = "2024-01-02T00:00:00Z"
        result.breadcrumb_text = "Home > Docs > Sample"
        result.hierarchy_context = "Depth: 1 | Parent: Docs"
        result.is_attachment = False
        result.original_filename = "sample-doc.md"
        result.attachment_context = None
        result.parent_document_title = None
        result.parent_title = "Docs"
        result.children_count = 3
        result.depth = 1
        result.file_size = None
        result.word_count = 45
        result.char_count = 256
        result.estimated_read_time = 1
        result.chunk_index = 0
        result.total_chunks = 2
        result.chunking_strategy = "semantic"
        result.mime_type = "text/markdown"
        result.original_file_type = "md"
        
        # Mock methods
        result.get_project_info.return_value = "Test Project (proj-123)"
        result.has_children.return_value = True
        result.get_display_title.return_value = "Sample Document"
        result.get_hierarchy_info.return_value = "Depth: 1 | Parent: Docs"
        result.get_content_info.return_value = "Word count: 45, Read time: 1 min"
        result.get_semantic_info.return_value = "Semantic analysis available"
        result.get_section_context.return_value = "[H2] Introduction"
        result.get_attachment_info.return_value = None
        
        return result

    @pytest.fixture
    def sample_attachment_result(self):
        """Create a sample attachment result for testing."""
        result = Mock(spec=HybridSearchResult)
        result.score = 0.92
        result.text = "Content from a PDF attachment about technical specifications."
        result.source_type = "confluence"
        result.source_title = "technical-spec.pdf"
        result.source_url = "https://docs.example.com/attachments/123"
        result.file_path = "/attachments/technical-spec.pdf"
        result.repo_name = None
        result.project_id = "proj-123"
        result.document_id = "att-789"
        result.breadcrumb_text = "Home > Docs > Attachments"
        result.is_attachment = True
        result.original_filename = "technical-spec.pdf"
        result.attachment_context = "Technical documentation attachment"
        result.parent_document_title = "Technical Documentation"
        result.parent_title = None
        result.children_count = 0
        result.depth = None
        result.file_size = 1024000
        result.word_count = 200
        result.char_count = 1500
        result.estimated_read_time = 2
        result.chunk_index = None
        result.total_chunks = None
        result.chunking_strategy = None
        result.project_name = "Test Project"
        result.project_description = "A test project"
        result.collection_name = "test_collection"
        result.created_at = "2024-01-01T00:00:00Z"
        result.last_modified = "2024-01-02T00:00:00Z"
        result.mime_type = "application/pdf"
        result.original_file_type = "pdf"
        result.file_type = "pdf"
        
        # Mock methods
        result.get_project_info.return_value = "Test Project (proj-123)"
        result.has_children.return_value = False
        result.get_display_title.return_value = "technical-spec.pdf"
        result.get_attachment_info.return_value = "PDF, 1024000 bytes"
        
        return result

    @pytest.fixture
    def sample_localfile_result(self):
        """Create a sample local file result for testing."""
        result = Mock(spec=HybridSearchResult)
        result.score = 0.78
        result.text = "Content from a local markdown file in the repository."
        result.source_type = "localfile"
        result.source_title = "README.md"
        result.source_url = None
        result.file_path = "docs/api/README.md"
        result.repo_name = "main-repo"
        result.project_id = "proj-456"
        result.document_id = "local-123"
        result.breadcrumb_text = None
        result.is_attachment = False
        result.original_filename = "README.md"
        result.parent_title = None
        result.children_count = 0
        result.depth = 2
        result.file_size = 2048
        
        # Mock methods
        result.get_project_info.return_value = None
        result.has_children.return_value = False
        result.get_display_title.return_value = "README.md"
        
        return result

    @pytest.fixture
    def sample_git_result(self):
        """Create a sample git repository result for testing."""
        result = Mock(spec=HybridSearchResult)
        result.score = 0.65
        result.text = "Code content from a git repository file."
        result.source_type = "git"
        result.source_title = "main.py"
        result.source_url = "https://github.com/example/repo/blob/main/src/main.py"
        result.file_path = "src/main.py"
        result.repo_name = "example/repo"
        result.project_id = None
        result.document_id = "git-321"
        result.is_attachment = False
        result.children_count = 0
        
        # Mock methods
        result.get_project_info.return_value = None
        result.has_children.return_value = False
        result.get_display_title.return_value = "main.py"
        
        return result

    def test_format_search_result_basic(self, sample_search_result):
        """Test basic search result formatting."""
        formatted = MCPFormatters.format_search_result(sample_search_result)
        
        # Check core components
        assert f"Score: {sample_search_result.score}" in formatted
        assert f"Text: {sample_search_result.text}" in formatted
        assert f"Source: {sample_search_result.source_type}" in formatted
        assert sample_search_result.source_title in formatted
        
        # Check project info
        assert "🏗️ Test Project (proj-123)" in formatted
        
        # Check hierarchy context
        assert "📍 Path: Home > Docs > Sample" in formatted
        assert "🏗️ Depth: 1 | Parent: Docs" in formatted
        
        # Check URL and file info
        assert sample_search_result.source_url in formatted
        assert f"File: {sample_search_result.file_path}" in formatted
        assert f"Repo: {sample_search_result.repo_name}" in formatted
        
        # Check parent and children info
        assert "⬆️ Parent: Docs" in formatted
        assert "⬇️ Children: 3" in formatted

    def test_format_search_result_attachment(self, sample_attachment_result):
        """Test search result formatting for attachments."""
        formatted = MCPFormatters.format_search_result(sample_attachment_result)
        
        # Check attachment-specific formatting
        assert "📎 Attachment: technical-spec.pdf" in formatted
        assert "📋 Technical documentation attachment" in formatted
        assert "📄 Attached to: Technical Documentation" in formatted
        
        # Should not show parent info for attachments
        assert "⬆️ Parent:" not in formatted

    def test_format_search_result_minimal(self):
        """Test search result formatting with minimal data."""
        result = Mock(spec=HybridSearchResult)
        result.score = 0.5
        result.text = "Minimal content"
        result.source_type = "unknown"
        result.source_title = None
        result.source_url = None
        result.file_path = None
        result.repo_name = None
        result.breadcrumb_text = None
        result.hierarchy_context = None
        result.is_attachment = False
        result.original_filename = None
        result.attachment_context = None
        result.parent_document_title = None
        result.parent_title = None
        
        # Mock methods to return None/False
        result.get_project_info.return_value = None
        result.has_children.return_value = False
        
        formatted = MCPFormatters.format_search_result(result)
        
        # Should handle None values gracefully
        assert "Score: 0.5" in formatted
        assert "Text: Minimal content" in formatted
        assert "Source: unknown" in formatted
        assert "🏗️" not in formatted  # No project info
        assert "📍" not in formatted  # No breadcrumb
        assert "⬆️" not in formatted  # No parent
        assert "⬇️" not in formatted  # No children

    def test_format_attachment_search_result(self, sample_attachment_result):
        """Test dedicated attachment search result formatting."""
        formatted = MCPFormatters.format_attachment_search_result(sample_attachment_result)
        
        # Should always show attachment info
        assert "📎 Attachment: technical-spec.pdf" in formatted
        assert "📋 Technical documentation attachment" in formatted
        assert "📄 Attached to: Technical Documentation" in formatted
        
        # Check basic components
        assert f"Score: {sample_attachment_result.score}" in formatted
        assert sample_attachment_result.text in formatted

    def test_format_attachment_search_result_non_attachment(self, sample_search_result):
        """Test attachment formatter with non-attachment result."""
        formatted = MCPFormatters.format_attachment_search_result(sample_search_result)
        
        # Should still show attachment marker (this is the expected behavior)
        assert "📎 Attachment" in formatted
        assert sample_search_result.source_title in formatted

    def test_format_hierarchical_results_empty(self):
        """Test hierarchical results formatting with empty results."""
        organized_results = {}
        formatted = MCPFormatters.format_hierarchical_results(organized_results)
        
        assert "Found 0 results organized by hierarchy" in formatted

    def test_format_hierarchical_results_single_group(self, sample_search_result):
        """Test hierarchical results formatting with single group."""
        organized_results = {
            "Test Group": [sample_search_result]
        }
        formatted = MCPFormatters.format_hierarchical_results(organized_results)
        
        assert "Found 1 results organized by hierarchy" in formatted
        assert "📁 **Test Group** (1 results)" in formatted
        assert sample_search_result.source_title in formatted
        assert f"Score: {sample_search_result.score:.3f}" in formatted
        assert sample_search_result.source_url in formatted

    def test_format_hierarchical_results_multiple_groups(self, sample_search_result, sample_attachment_result):
        """Test hierarchical results formatting with multiple groups."""
        organized_results = {
            "Documents": [sample_search_result],
            "Attachments": [sample_attachment_result]
        }
        formatted = MCPFormatters.format_hierarchical_results(organized_results)
        
        assert "Found 2 results organized by hierarchy" in formatted
        assert "📁 **Documents** (1 results)" in formatted
        assert "📁 **Attachments** (1 results)" in formatted

    def test_format_relationship_analysis_error(self):
        """Test relationship analysis formatting with error."""
        analysis = {"error": "Failed to analyze relationships"}
        formatted = MCPFormatters.format_relationship_analysis(analysis)
        
        assert "❌ Error: Failed to analyze relationships" in formatted

    def test_format_relationship_analysis_success(self):
        """Test relationship analysis formatting with successful analysis."""
        analysis = {
            "summary": {
                "total_documents": 15,
                "clusters_found": 3,
                "citation_relationships": 8,
                "conflicts_detected": 2
            },
            "query_metadata": {
                "original_query": "test analysis",
                "document_count": 15
            },
            "document_clusters": [
                {"documents": [{"title": "Doc1"}, {"title": "Doc2"}]},
                {"documents": [{"title": "Doc3"}]},
                {"documents": [{"title": "Doc4"}, {"title": "Doc5"}, {"title": "Doc6"}]}
            ],
            "conflict_analysis": {
                "conflicting_pairs": [
                    ("doc1", "doc2", {"type": "version_conflict"}),
                    ("doc3", "doc4", {"type": "contradictory_guidance"})
                ]
            }
        }
        
        formatted = MCPFormatters.format_relationship_analysis(analysis)
        
        # Check summary section
        assert "🔍 **Document Relationship Analysis**" in formatted
        assert "Total Documents: 15" in formatted
        assert "Clusters Found: 3" in formatted
        assert "Citation Relationships: 8" in formatted
        assert "Conflicts Detected: 2" in formatted
        
        # Check query information
        assert "Original Query: test analysis" in formatted
        assert "Documents Analyzed: 15" in formatted
        
        # Check clusters section
        assert "🗂️ **Document Clusters:**" in formatted
        assert "Cluster 1: 2 documents" in formatted
        assert "Cluster 2: 1 documents" in formatted
        assert "Cluster 3: 3 documents" in formatted
        
        # Check conflicts section
        assert "⚠️ **Conflicts Detected:** 2 conflicting document pairs" in formatted

    def test_format_similar_documents_empty(self):
        """Test similar documents formatting with empty results."""
        formatted = MCPFormatters.format_similar_documents([])
        
        assert "🔍 **Similar Documents**" in formatted
        assert "No similar documents found." in formatted

    def test_format_similar_documents_with_results(self, sample_search_result):
        """Test similar documents formatting with results."""
        similar_docs = [
            {
                "similarity_score": 0.95,
                "document": sample_search_result,
                "similarity_reasons": ["topic_overlap", "entity_overlap"]
            },
            {
                "similarity_score": 0.87,
                "document": sample_search_result,
                "similarity_reasons": ["semantic_similarity"]
            }
        ]
        
        formatted = MCPFormatters.format_similar_documents(similar_docs)
        
        assert "🔍 **Similar Documents** (2 found)" in formatted
        assert "**1. Similarity Score: 0.950**" in formatted
        assert "**2. Similarity Score: 0.870**" in formatted
        assert "• Title: Sample Document" in formatted
        assert "• Reasons: topic_overlap, entity_overlap" in formatted
        assert "• Reasons: semantic_similarity" in formatted

    def test_format_conflict_analysis_no_conflicts(self):
        """Test conflict analysis formatting with no conflicts."""
        conflicts = {"conflicting_pairs": []}
        formatted = MCPFormatters.format_conflict_analysis(conflicts)
        
        assert "✅ **Conflict Analysis**" in formatted
        assert "No conflicts detected between documents." in formatted

    def test_format_conflict_analysis_with_conflicts(self):
        """Test conflict analysis formatting with conflicts."""
        conflicts = {
            "conflicting_pairs": [
                ("doc1", "doc2", {"type": "version_conflict"}),
                ("doc3", "doc4", {"type": "contradictory_guidance"})
            ],
            "resolution_suggestions": {
                "suggestion1": "Review version consistency",
                "suggestion2": "Reconcile contradictory guidance",
                "suggestion3": "Update documentation"
            }
        }
        
        formatted = MCPFormatters.format_conflict_analysis(conflicts)
        
        assert "⚠️ **Conflict Analysis** (2 conflicts found)" in formatted
        assert "**1. Conflict Type: version_conflict**" in formatted
        assert "**2. Conflict Type: contradictory_guidance**" in formatted
        assert "• Document 1: doc1" in formatted
        assert "• Document 2: doc2" in formatted
        assert "💡 **Resolution Suggestions:**" in formatted
        assert "• Review version consistency" in formatted

    def test_format_complementary_content_empty(self):
        """Test complementary content formatting with empty results."""
        formatted = MCPFormatters.format_complementary_content([])
        
        assert "🔍 **Complementary Content**" in formatted
        assert "No complementary content found." in formatted

    def test_format_complementary_content_with_results(self, sample_search_result):
        """Test complementary content formatting with results."""
        complementary = [
            {
                "document": sample_search_result,
                "relevance_score": 0.92,
                "recommendation_reason": "Related technical content"
            },
            {
                "document": sample_search_result,
                "relevance_score": 0.85,
                "recommendation_reason": "Similar topic coverage"
            }
        ]
        
        formatted = MCPFormatters.format_complementary_content(complementary)
        
        assert "🔗 **Complementary Content** (2 recommendations)" in formatted
        assert "**1. Complementary Score: 0.920**" in formatted
        assert "**2. Complementary Score: 0.850**" in formatted
        assert "• Title: Sample Document" in formatted
        assert "• Why Complementary: Related technical content" in formatted
        assert "• Why Complementary: Similar topic coverage" in formatted

    def test_format_document_clusters_empty(self):
        """Test document clustering formatting with empty results."""
        clusters = {
            "clusters": [],
            "clustering_metadata": {
                "message": "Insufficient documents for clustering"
            }
        }
        
        formatted = MCPFormatters.format_document_clusters(clusters)
        
        assert "🗂️ **Document Clustering**" in formatted
        assert "Insufficient documents for clustering" in formatted

    def test_format_document_clusters_with_results(self):
        """Test document clustering formatting with results."""
        clusters = {
            "clusters": [
                {
                    "id": "cluster_1",
                    "coherence_score": 0.85,
                    "centroid_topics": ["API", "documentation", "REST"],
                    "shared_entities": ["service", "endpoint", "authentication"],
                    "cluster_summary": "API documentation cluster",
                    "documents": [{"title": "API Guide"}, {"title": "REST Reference"}]
                },
                {
                    "id": "cluster_2", 
                    "coherence_score": 0.78,
                    "centroid_topics": ["deployment", "configuration"],
                    "shared_entities": ["server", "config"],
                    "cluster_summary": "Deployment guides",
                    "documents": [{"title": "Deploy Guide"}]
                }
            ],
            "clustering_metadata": {
                "strategy": "mixed_features",
                "total_clusters": 2,
                "total_documents": 3,
                "original_query": "technical documentation"
            }
        }
        
        formatted = MCPFormatters.format_document_clusters(clusters)
        
        assert "🗂️ **Document Clustering Results**" in formatted
        assert "Strategy: mixed_features" in formatted
        assert "Total Clusters: 2" in formatted
        assert "Total Documents: 3" in formatted
        assert "Original Query: technical documentation" in formatted
        
        assert "**Cluster 1 (ID: cluster_1)**" in formatted
        assert "• Documents: 2" in formatted
        assert "• Coherence Score: 0.850" in formatted
        assert "• Key Topics: API, documentation, REST" in formatted
        assert "• Shared Entities: service, endpoint, authentication" in formatted
        assert "• Summary: API documentation cluster" in formatted
        
        assert "**Cluster 2 (ID: cluster_2)**" in formatted
        assert "• Documents: 1" in formatted

    def test_create_structured_search_results(self, sample_search_result, sample_attachment_result):
        """Test creating structured search results."""
        results = [sample_search_result, sample_attachment_result]
        structured = MCPFormatters.create_structured_search_results(results)
        
        assert len(structured) == 2
        
        # Check first result structure
        first_result = structured[0]
        assert first_result["score"] == sample_search_result.score
        assert first_result["document_id"] == sample_search_result.document_id
        assert first_result["title"] == sample_search_result.get_display_title()
        assert first_result["content"] == sample_search_result.text
        assert first_result["source_type"] == sample_search_result.source_type
        
        # Check metadata structure
        metadata = first_result["metadata"]
        assert metadata["project_id"] == sample_search_result.project_id
        assert metadata["file_path"] == sample_search_result.file_path
        assert metadata["word_count"] == sample_search_result.word_count
        assert metadata["chunk_index"] == sample_search_result.chunk_index
        assert metadata["total_chunks"] == sample_search_result.total_chunks

    def test_create_lightweight_similar_documents_results(self, sample_search_result):
        """Test creating lightweight similar documents results."""
        similar_docs = [
            {
                "document": sample_search_result,
                "similarity_score": 0.95,
                "metric_scores": {"topic": 0.9, "entity": 0.8},
                "similarity_reasons": ["topic_overlap"]
            }
        ]
        
        lightweight = MCPFormatters.create_lightweight_similar_documents_results(
            similar_docs, "target query", "comparison query"
        )
        
        assert "similarity_index" in lightweight
        assert "query_info" in lightweight
        assert "navigation" in lightweight
        
        # Check similarity index
        similarity_index = lightweight["similarity_index"]
        assert len(similarity_index) == 1
        
        doc_entry = similarity_index[0]
        assert doc_entry["document_id"] == sample_search_result.document_id
        assert doc_entry["title"] == sample_search_result.source_title
        assert doc_entry["similarity_score"] == 0.95
        assert doc_entry["similarity_info"]["metric_scores"]["topic"] == 0.9
        assert doc_entry["navigation_hints"]["can_expand"] is True

    def test_create_lightweight_conflict_results(self, sample_search_result, sample_attachment_result):
        """Test creating lightweight conflict results."""
        conflicts = {
            "conflicting_pairs": [
                (
                    "doc1:title1", 
                    "doc2:title2", 
                    {
                        "type": "version_conflict",
                        "confidence": 0.85,
                        "description": "Version information conflicts",
                        "indicators": ["v1.0", "v2.0"],
                        "structured_indicators": [
                            {
                                "doc1_snippet": "Version 1.0 is current",
                                "doc2_snippet": "Version 2.0 is latest"
                            }
                        ]
                    }
                )
            ],
            "query_metadata": {
                "document_count": 10
            }
        }
        
        documents = [sample_search_result, sample_attachment_result]
        lightweight = MCPFormatters.create_lightweight_conflict_results(
            conflicts, "test query", documents
        )
        
        assert "conflicts_detected" in lightweight
        assert "conflict_summary" in lightweight
        assert "analysis_metadata" in lightweight
        assert "navigation" in lightweight
        
        # Check conflicts detected
        conflicts_detected = lightweight["conflicts_detected"]
        assert len(conflicts_detected) == 1
        
        conflict = conflicts_detected[0]
        assert conflict["conflict_type"] == "version_conflict"
        assert conflict["conflict_score"] == 0.85
        assert conflict["conflict_description"] == "Version information conflicts"
        assert len(conflict["conflicting_statements"]) > 0

    def test_create_lightweight_cluster_results(self, sample_search_result):
        """Test creating lightweight cluster results."""
        clustering_results = {
            "clusters": [
                {
                    "id": "cluster_1",
                    "name": "Documentation Cluster",
                    "cluster_summary": "Technical documentation",
                    "coherence_score": 0.85,
                    "documents": [sample_search_result],
                    "shared_entities": ["API", "documentation"],
                    "centroid_topics": ["technical", "guide"]
                }
            ],
            "clustering_metadata": {
                "strategy": "mixed_features",
                "total_documents": 5,
                "clusters_created": 1
            }
        }
        
        lightweight = MCPFormatters.create_lightweight_cluster_results(
            clustering_results, "test query"
        )
        
        assert "cluster_index" in lightweight
        assert "clustering_metadata" in lightweight
        assert "expansion_info" in lightweight
        
        # Check cluster index
        cluster_index = lightweight["cluster_index"]
        assert len(cluster_index) == 1
        
        cluster = cluster_index[0]
        assert cluster["cluster_id"] == "cluster_1"
        assert cluster["cluster_name"] == "Documentation Cluster"
        assert cluster["document_count"] == 1
        assert cluster["coherence_score"] == 0.85
        assert len(cluster["documents"]) == 1

    def test_create_lightweight_hierarchy_results(self, sample_search_result, sample_localfile_result):
        """Test creating lightweight hierarchy results."""
        filtered_results = [sample_search_result, sample_localfile_result]
        organized_results = {
            "Docs": [sample_search_result],
            "Local Files": [sample_localfile_result]
        }
        
        lightweight = MCPFormatters.create_lightweight_hierarchy_results(
            filtered_results, organized_results, "test query"
        )
        
        assert "hierarchy_index" in lightweight
        assert "hierarchy_groups" in lightweight
        assert "total_found" in lightweight
        assert "query_metadata" in lightweight
        
        # Check hierarchy index
        hierarchy_index = lightweight["hierarchy_index"]
        assert len(hierarchy_index) == 2
        
        # Check hierarchy groups
        hierarchy_groups = lightweight["hierarchy_groups"]
        assert len(hierarchy_groups) == 2

    def test_create_lightweight_attachment_results(self, sample_attachment_result):
        """Test creating lightweight attachment results."""
        filtered_results = [sample_attachment_result]
        attachment_filter = {"attachments_only": True}
        
        lightweight = MCPFormatters.create_lightweight_attachment_results(
            filtered_results, attachment_filter, "test query"
        )
        
        assert "attachment_index" in lightweight
        assert "attachment_groups" in lightweight
        assert "total_found" in lightweight
        assert "query_metadata" in lightweight
        
        # Check attachment index
        attachment_index = lightweight["attachment_index"]
        assert len(attachment_index) == 1
        
        attachment = attachment_index[0]
        assert attachment["document_id"] == sample_attachment_result.document_id
        assert attachment["title"] == sample_attachment_result.source_title
        assert attachment["attachment_info"]["filename"] == "technical-spec.pdf"
        assert attachment["attachment_info"]["file_type"] == "pdf"

    def test_create_lightweight_complementary_results(self, sample_search_result):
        """Test creating lightweight complementary results."""
        complementary_recommendations = [
            {
                "document": sample_search_result,
                "relevance_score": 0.92,
                "recommendation_reason": "Related content",
                "strategy": "topic_similarity"
            }
        ]
        
        lightweight = MCPFormatters.create_lightweight_complementary_results(
            complementary_recommendations, sample_search_result, 5, "test query"
        )
        
        assert "complementary_index" in lightweight
        assert "target_document" in lightweight
        assert "complementary_summary" in lightweight
        assert "lazy_loading_enabled" in lightweight
        
        # Check complementary index
        complementary_index = lightweight["complementary_index"]
        assert len(complementary_index) == 1
        
        comp = complementary_index[0]
        assert comp["document_id"] == sample_search_result.document_id
        assert comp["complementary_score"] == 0.92
        assert comp["complementary_reason"] == "Related content"
        assert comp["relationship_type"] == "topic_similarity"

    def test_create_structured_attachment_results(self, sample_attachment_result):
        """Test creating structured attachment results."""
        filtered_results = [sample_attachment_result]
        attachment_filter = {"attachments_only": True}
        
        structured = MCPFormatters.create_structured_attachment_results(
            filtered_results, attachment_filter, True
        )
        
        assert "results" in structured
        assert "total_found" in structured
        assert "attachment_summary" in structured
        
        # Check results structure
        results = structured["results"]
        assert len(results) == 1
        
        result = results[0]
        assert result["score"] == sample_attachment_result.score
        assert result["title"] == sample_attachment_result.source_title
        assert result["attachment_info"]["filename"] == "technical-spec.pdf"
        assert result["attachment_info"]["file_type"] == "pdf" or result["attachment_info"]["file_type"] == "unknown"
        assert result["attachment_info"]["file_size"] == 1024000

    def test_helper_methods(self, sample_search_result):
        """Test various helper methods."""
        # Test _extract_safe_filename
        filename = MCPFormatters._extract_safe_filename(sample_search_result)
        assert filename == "sample-doc.md"  # Uses original_filename first
        
        # Test _extract_file_type_minimal  
        file_type = MCPFormatters._extract_file_type_minimal(sample_search_result)
        assert file_type == "markdown"  # From mime_type text/markdown
        
        # Test _generate_conflict_resolution_suggestion
        conflict_info = {"type": "version_conflict"}
        suggestion = MCPFormatters._generate_conflict_resolution_suggestion(conflict_info)
        assert "version consistency" in suggestion
        
        # Test _get_group_key
        group_key = MCPFormatters._get_group_key(sample_search_result)
        assert group_key is not None

    def test_edge_cases_and_none_handling(self):
        """Test edge cases and None value handling."""
        # Test with completely empty result
        empty_result = Mock(spec=HybridSearchResult)
        for attr in ['score', 'text', 'source_type', 'source_title', 'source_url', 
                     'file_path', 'repo_name', 'breadcrumb_text', 'hierarchy_context',
                     'is_attachment', 'original_filename', 'attachment_context',
                     'parent_document_title', 'parent_title']:
            setattr(empty_result, attr, None)
        
        empty_result.get_project_info.return_value = None
        empty_result.has_children.return_value = False
        
        # Should not crash
        formatted = MCPFormatters.format_search_result(empty_result)
        assert "Score: None" in formatted
        assert "Text: None" in formatted
        
        # Test with empty organized results
        formatted = MCPFormatters.format_hierarchical_results({})
        assert "Found 0 results" in formatted
        
        # Test with None values in lightweight results
        lightweight = MCPFormatters.create_lightweight_similar_documents_results([], "", "")
        assert lightweight["similarity_index"] == []
        assert lightweight["query_info"]["total_found"] == 0

    def test_large_data_truncation(self):
        """Test that large data is properly truncated for performance."""
        # Test with many results - should be limited
        large_results = []
        for i in range(30):
            result = Mock(spec=HybridSearchResult)
            result.document_id = f"doc-{i}"
            result.source_title = f"Document {i}"
            result.score = 0.5
            result.source_type = "confluence"
            result.original_filename = f"doc{i}.pdf"
            result.file_path = f"/path/doc{i}.pdf"
            result.mime_type = "application/pdf"
            result.file_size = 1000
            result.project_name = None
            result.project_id = None
            result.text = f"Sample content for document {i} used in testing large data truncation functionality."
            result.parent_document_title = None
            result.parent_title = None
            large_results.append(result)
        
        # Test hierarchy results limiting
        lightweight = MCPFormatters.create_lightweight_hierarchy_results(large_results, {}, "test")
        assert len(lightweight["hierarchy_index"]) <= 20  # Should be limited
        
        # Test attachment results limiting  
        lightweight = MCPFormatters.create_lightweight_attachment_results(large_results, {}, "test")
        assert len(lightweight["attachment_index"]) <= 20  # Should be limited

    def test_error_recovery(self):
        """Test error recovery in formatters."""
        # Test with malformed conflict data
        bad_conflicts = {
            "conflicting_pairs": [
                # Missing required fields
                ("doc1", "doc2", {})
            ]
        }
        
        lightweight = MCPFormatters.create_lightweight_conflict_results(bad_conflicts, "test", [])
        # Should not crash and should handle missing fields gracefully
        assert "conflicts_detected" in lightweight
        assert len(lightweight["conflicts_detected"]) == 1
