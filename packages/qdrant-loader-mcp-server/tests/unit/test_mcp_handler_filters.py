"""Tests for MCP handler filter and formatting methods."""

from unittest.mock import Mock

import pytest
from qdrant_loader_mcp_server.search.models import SearchResult
from qdrant_loader_mcp_server.mcp.search_handler import SearchHandler
from qdrant_loader_mcp_server.mcp.formatters import MCPFormatters
from qdrant_loader_mcp_server.mcp.protocol import MCPProtocol


@pytest.fixture
def mock_search_results():
    """Create mock search results for testing filters."""
    results = []

    # Confluence root document with children
    result1 = Mock(spec=SearchResult)
    result1.source_type = "confluence"
    result1.source_title = "Developer Guide"
    result1.text = "Complete developer documentation"
    result1.score = 0.95
    result1.depth = 0
    result1.parent_title = None
    result1.parent_id = None
    result1.children_count = 5
    result1.breadcrumb_text = ""
    result1.hierarchy_context = "Depth: 0 | Children: 5"
    result1.is_attachment = False
    result1.file_size = None  # Non-attachments don't have file size
    result1.attachment_author = None
    result1.parent_document_title = None
    result1.original_filename = None
    result1.attachment_context = None
    result1.source_url = "https://docs.company.com/dev-guide"
    result1.file_path = None
    result1.repo_name = None
    result1.is_root_document.return_value = True
    result1.has_children.return_value = True
    result1.get_file_type.return_value = None
    results.append(result1)

    # Confluence child document
    result2 = Mock(spec=SearchResult)
    result2.source_type = "confluence"
    result2.source_title = "API Reference"
    result2.text = "API documentation and examples"
    result2.score = 0.88
    result2.depth = 1
    result2.parent_title = "Developer Guide"
    result2.parent_id = "dev-guide-123"
    result2.children_count = 0
    result2.breadcrumb_text = "Developer Guide > API Reference"
    result2.hierarchy_context = "Depth: 1 | Parent: Developer Guide"
    result2.is_attachment = False
    result2.file_size = None
    result2.attachment_author = None
    result2.parent_document_title = None
    result2.original_filename = None
    result2.attachment_context = None
    result2.source_url = "https://docs.company.com/api-ref"
    result2.file_path = None
    result2.repo_name = None
    result2.is_root_document.return_value = False
    result2.has_children.return_value = False
    result2.get_file_type.return_value = None
    results.append(result2)

    # PDF attachment on Confluence document
    result3 = Mock(spec=SearchResult)
    result3.source_type = "confluence"
    result3.source_title = "project-requirements.pdf"
    result3.text = "Project requirements and specifications document"
    result3.score = 0.82
    result3.depth = None
    result3.parent_title = None
    result3.parent_id = None
    result3.children_count = 0
    result3.breadcrumb_text = "Developer Guide > Project Planning"
    result3.hierarchy_context = None
    result3.is_attachment = True
    result3.file_size = 2097152  # 2MB
    result3.attachment_author = "project.manager@company.com"
    result3.parent_document_title = "Project Planning"
    result3.original_filename = "project-requirements.pdf"
    result3.attachment_context = "Requirements document for project planning phase"
    result3.source_url = "https://docs.company.com/attachments/project-req.pdf"
    result3.file_path = "/attachments/project-requirements.pdf"
    result3.repo_name = None
    result3.is_root_document.return_value = False
    result3.has_children.return_value = False
    result3.get_file_type.return_value = "pdf"
    results.append(result3)

    # Git result (non-Confluence)
    result4 = Mock(spec=SearchResult)
    result4.source_type = "git"
    result4.source_title = "README.md"
    result4.text = "Project readme file"
    result4.score = 0.75
    result4.depth = None
    result4.parent_title = None
    result4.parent_id = None
    result4.children_count = 0
    result4.breadcrumb_text = None
    result4.hierarchy_context = None
    result4.is_attachment = False
    result4.file_size = None
    result4.attachment_author = None
    result4.parent_document_title = None
    result4.original_filename = None
    result4.attachment_context = None
    result4.source_url = None
    result4.file_path = "README.md"
    result4.repo_name = "my-project"
    result4.is_root_document.return_value = False
    result4.has_children.return_value = False
    result4.get_file_type.return_value = None
    results.append(result4)

    return results


@pytest.fixture
def search_handler():
    """Create a SearchHandler instance for testing."""
    mock_search_engine = Mock()
    mock_query_processor = Mock()
    mock_protocol = Mock(spec=MCPProtocol)
    return SearchHandler(mock_search_engine, mock_query_processor, mock_protocol)


@pytest.fixture 
def formatters():
    """Create a MCPFormatters instance for testing."""
    return MCPFormatters()


class TestHierarchyFilters:
    """Test hierarchy filtering functionality."""

    def test_apply_hierarchy_filters_depth(self, search_handler, mock_search_results):
        """Test filtering by depth."""
        hierarchy_filter = {"depth": 0}
        filtered = search_handler._apply_hierarchy_filters(
            mock_search_results, hierarchy_filter
        )
        
        # Should only return the root document (depth=0)
        assert len(filtered) == 1
        assert filtered[0].depth == 0
        assert filtered[0].source_title == "Developer Guide"

    def test_apply_hierarchy_filters_parent_title(
        self, search_handler, mock_search_results
    ):
        """Test filtering by parent title."""
        hierarchy_filter = {"parent_title": "Developer Guide"}
        filtered = search_handler._apply_hierarchy_filters(
            mock_search_results, hierarchy_filter
        )
        
        # Should only return documents with "Developer Guide" as parent
        assert len(filtered) == 1
        assert filtered[0].parent_title == "Developer Guide"
        assert filtered[0].source_title == "API Reference"

    def test_apply_hierarchy_filters_root_only(self, search_handler, mock_search_results):
        """Test filtering for root documents only."""
        hierarchy_filter = {"root_only": True}
        filtered = search_handler._apply_hierarchy_filters(
            mock_search_results, hierarchy_filter
        )
        
        # Should only return root documents
        assert len(filtered) == 1
        assert filtered[0].is_root_document() is True
        assert filtered[0].source_title == "Developer Guide"

    def test_apply_hierarchy_filters_has_children_true(
        self, search_handler, mock_search_results
    ):
        """Test filtering for documents with children."""
        hierarchy_filter = {"has_children": True}
        filtered = search_handler._apply_hierarchy_filters(
            mock_search_results, hierarchy_filter
        )
        
        # Should only return documents with children
        assert len(filtered) == 1
        assert filtered[0].has_children() is True
        assert filtered[0].source_title == "Developer Guide"

    def test_apply_hierarchy_filters_has_children_false(
        self, search_handler, mock_search_results
    ):
        """Test filtering for documents without children."""
        hierarchy_filter = {"has_children": False}
        filtered = search_handler._apply_hierarchy_filters(
            mock_search_results, hierarchy_filter
        )
        
        # Should return documents without children (includes attachments)
        assert len(filtered) == 2
        titles = [r.source_title for r in filtered]
        assert "API Reference" in titles
        assert "project-requirements.pdf" in titles

    def test_apply_hierarchy_filters_non_confluence_excluded(
        self, search_handler, mock_search_results
    ):
        """Test that non-Confluence results are excluded."""
        hierarchy_filter = {}
        filtered = search_handler._apply_hierarchy_filters(
            mock_search_results, hierarchy_filter
        )
        
        # Should exclude the git result but include all Confluence results
        confluence_titles = [r.source_title for r in filtered]
        assert "README.md" not in confluence_titles
        assert all(r.source_type == "confluence" for r in filtered)
        # Should have 3 Confluence results (including attachment)
        assert len(filtered) == 3

    def test_organize_by_hierarchy(self, search_handler, mock_search_results):
        """Test organizing results by hierarchy."""
        confluence_results = [
            r for r in mock_search_results if r.source_type == "confluence"
        ]
        organized = search_handler._organize_by_hierarchy(confluence_results)
        
        # Should have one group: "Developer Guide" (attachment uses breadcrumb root)
        assert len(organized) == 1
        assert "Developer Guide" in organized
        
        # Developer Guide group should have all 3 documents
        dev_guide_group = organized["Developer Guide"]
        assert len(dev_guide_group) == 3
        titles = [r.source_title for r in dev_guide_group]
        assert "Developer Guide" in titles
        assert "API Reference" in titles
        assert "project-requirements.pdf" in titles

    def test_format_hierarchical_results(self, formatters, search_handler, mock_search_results):
        """Test formatting hierarchical results."""
        confluence_results = [
            r
            for r in mock_search_results
            if r.source_type == "confluence" and not r.is_attachment
        ]
        organized = search_handler._organize_by_hierarchy(confluence_results)
        formatted = formatters.format_hierarchical_results(organized)
        
        # Should contain the organized structure
        assert "Developer Guide" in formatted
        assert "API Reference" in formatted
        assert "results organized by hierarchy" in formatted


class TestAttachmentFilters:
    """Test attachment filtering functionality."""

    def test_apply_attachment_filters_attachments_only(
        self, search_handler, mock_search_results
    ):
        """Test filtering for attachments only."""
        attachment_filter = {"attachments_only": True}
        filtered = search_handler._apply_attachment_filters(
            mock_search_results, attachment_filter
        )
        
        # Should only return attachments
        assert len(filtered) == 1
        assert filtered[0].is_attachment is True
        assert filtered[0].source_title == "project-requirements.pdf"

    def test_apply_attachment_filters_parent_document_title(
        self, search_handler, mock_search_results
    ):
        """Test filtering by parent document title."""
        attachment_filter = {"parent_document_title": "Project Planning"}
        filtered = search_handler._apply_attachment_filters(
            mock_search_results, attachment_filter
        )
        
        # Should only return attachments with matching parent document
        assert len(filtered) == 1
        assert filtered[0].parent_document_title == "Project Planning"
        assert filtered[0].source_title == "project-requirements.pdf"

    def test_apply_attachment_filters_file_type(self, search_handler, mock_search_results):
        """Test filtering by file type."""
        attachment_filter = {"file_type": "pdf"}
        filtered = search_handler._apply_attachment_filters(
            mock_search_results, attachment_filter
        )
        
        # Should only return PDF files
        assert len(filtered) == 1
        assert filtered[0].get_file_type() == "pdf"
        assert filtered[0].source_title == "project-requirements.pdf"

    def test_apply_attachment_filters_file_size_min(
        self, search_handler, mock_search_results
    ):
        """Test filtering by minimum file size."""
        attachment_filter = {"file_size_min": 1048576}  # 1MB
        filtered = search_handler._apply_attachment_filters(
            mock_search_results, attachment_filter
        )
        
        # Should return files >= 1MB AND files with no size (non-attachments)
        # Non-attachments have file_size=None which passes the filter
        assert len(filtered) == 3
        # Should include the attachment (2MB) and the 2 non-attachments (None file_size)
        attachment_results = [r for r in filtered if r.is_attachment]
        assert len(attachment_results) == 1
        assert attachment_results[0].file_size >= 1048576

    def test_apply_attachment_filters_file_size_max(
        self, search_handler, mock_search_results
    ):
        """Test filtering by maximum file size."""
        attachment_filter = {"file_size_max": 1048576}  # 1MB
        filtered = search_handler._apply_attachment_filters(
            mock_search_results, attachment_filter
        )
        
        # Should return files <= 1MB AND files with no size (non-attachments)
        # The 2MB attachment should be excluded, but non-attachments (None) pass through
        assert len(filtered) == 2
        # Should only include the 2 non-attachments (file_size=None)
        attachment_results = [r for r in filtered if r.is_attachment]
        assert len(attachment_results) == 0

    def test_apply_attachment_filters_author(self, search_handler, mock_search_results):
        """Test filtering by author."""
        attachment_filter = {"author": "project.manager@company.com"}
        filtered = search_handler._apply_attachment_filters(
            mock_search_results, attachment_filter
        )
        
        # Should only return attachments by the specified author
        assert len(filtered) == 1
        assert filtered[0].attachment_author == "project.manager@company.com"
        assert filtered[0].source_title == "project-requirements.pdf"

    def test_apply_attachment_filters_non_confluence_excluded(
        self, search_handler, mock_search_results
    ):
        """Test that non-Confluence results are excluded."""
        attachment_filter = {}
        filtered = search_handler._apply_attachment_filters(
            mock_search_results, attachment_filter
        )
        
        # Should exclude the git result
        confluence_titles = [r.source_title for r in filtered]
        assert "README.md" not in confluence_titles
        assert all(r.source_type == "confluence" for r in filtered)

    def test_format_attachment_search_result(self, formatters, mock_search_results):
        """Test formatting attachment search results."""
        attachment_result = next(r for r in mock_search_results if r.is_attachment)
        formatted = formatters.format_attachment_search_result(attachment_result)
        
        # Should contain attachment-specific information
        assert "📎 Attachment" in formatted
        assert "project-requirements.pdf" in formatted
        assert "Attached to: Project Planning" in formatted
        assert "Score:" in formatted

    def test_format_attachment_search_result_non_attachment(
        self, formatters, mock_search_results
    ):
        """Test formatting non-attachment search results."""
        non_attachment_result = next(
            r
            for r in mock_search_results
            if not r.is_attachment and r.source_type == "confluence"
        )
        formatted = formatters.format_attachment_search_result(non_attachment_result)
        
        # Should still format properly but without attachment info
        assert "📎 Attachment" in formatted  # This is added by the formatter
        assert "Developer Guide" in formatted or "API Reference" in formatted
        assert "Score:" in formatted
