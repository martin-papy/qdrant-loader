"""Tests for MCP handler filter and formatting methods."""

from unittest.mock import Mock

import pytest
from qdrant_loader_mcp_server.search.models import SearchResult


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
    result2.hierarchy_context = "Path: Developer Guide > API Reference | Depth: 1"
    result2.is_attachment = False
    result2.file_size = None  # Non-attachments don't have file size
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

    # Confluence attachment (PDF)
    result3 = Mock(spec=SearchResult)
    result3.source_type = "confluence"
    result3.source_title = "Attachment: requirements.pdf"
    result3.text = "Project requirements specification"
    result3.score = 0.82
    result3.depth = None
    result3.parent_title = None
    result3.parent_id = None
    result3.children_count = 0
    result3.breadcrumb_text = None
    result3.hierarchy_context = None
    result3.is_attachment = True
    result3.file_size = 2048000  # 2MB
    result3.attachment_author = "project.manager@company.com"
    result3.parent_document_title = "Project Planning"
    result3.original_filename = "requirements.pdf"
    result3.attachment_context = (
        "File: requirements.pdf | Size: 2.0 MB | Type: application/pdf"
    )
    result3.source_url = "https://docs.company.com/attachments/req.pdf"
    result3.file_path = None
    result3.repo_name = None
    result3.is_root_document.return_value = False
    result3.has_children.return_value = False
    result3.get_file_type.return_value = "pdf"
    results.append(result3)

    # Git repository result (non-Confluence)
    result4 = Mock(spec=SearchResult)
    result4.source_type = "git"
    result4.source_title = "config.py"
    result4.text = "Configuration file for the application"
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
    result4.file_path = "/src/config.py"
    result4.repo_name = "my-project"
    result4.is_root_document.return_value = False
    result4.has_children.return_value = False
    result4.get_file_type.return_value = None
    results.append(result4)

    return results


class TestHierarchyFilters:
    """Test hierarchy filtering methods."""

    def test_apply_hierarchy_filters_depth(self, mcp_handler, mock_search_results):
        """Test filtering by depth."""
        hierarchy_filter = {"depth": 0}
        filtered = mcp_handler._apply_hierarchy_filters(
            mock_search_results, hierarchy_filter
        )

        # Should only return the root document (depth 0)
        assert len(filtered) == 1
        assert filtered[0].source_title == "Developer Guide"
        assert filtered[0].depth == 0

    def test_apply_hierarchy_filters_parent_title(
        self, mcp_handler, mock_search_results
    ):
        """Test filtering by parent title."""
        hierarchy_filter = {"parent_title": "Developer Guide"}
        filtered = mcp_handler._apply_hierarchy_filters(
            mock_search_results, hierarchy_filter
        )

        # Should only return documents with "Developer Guide" as parent
        assert len(filtered) == 1
        assert filtered[0].source_title == "API Reference"
        assert filtered[0].parent_title == "Developer Guide"

    def test_apply_hierarchy_filters_root_only(self, mcp_handler, mock_search_results):
        """Test filtering for root documents only."""
        hierarchy_filter = {"root_only": True}
        filtered = mcp_handler._apply_hierarchy_filters(
            mock_search_results, hierarchy_filter
        )

        # Should only return root documents
        assert len(filtered) == 1
        assert filtered[0].source_title == "Developer Guide"
        assert filtered[0].is_root_document() is True

    def test_apply_hierarchy_filters_has_children_true(
        self, mcp_handler, mock_search_results
    ):
        """Test filtering for documents with children."""
        hierarchy_filter = {"has_children": True}
        filtered = mcp_handler._apply_hierarchy_filters(
            mock_search_results, hierarchy_filter
        )

        # Should only return documents that have children
        assert len(filtered) == 1
        assert filtered[0].source_title == "Developer Guide"
        assert filtered[0].has_children() is True

    def test_apply_hierarchy_filters_has_children_false(
        self, mcp_handler, mock_search_results
    ):
        """Test filtering for documents without children."""
        hierarchy_filter = {"has_children": False}
        filtered = mcp_handler._apply_hierarchy_filters(
            mock_search_results, hierarchy_filter
        )

        # Should only return Confluence documents that don't have children
        # (API Reference and the attachment, but attachment should be excluded by other logic)
        assert len(filtered) == 2  # API Reference + attachment (both have no children)
        confluence_non_children = [r for r in filtered if not r.has_children()]
        assert len(confluence_non_children) == 2

    def test_apply_hierarchy_filters_non_confluence_excluded(
        self, mcp_handler, mock_search_results
    ):
        """Test that non-Confluence results are excluded."""
        hierarchy_filter = {}
        filtered = mcp_handler._apply_hierarchy_filters(
            mock_search_results, hierarchy_filter
        )

        # Should exclude Git results, only include Confluence
        confluence_results = [r for r in filtered if r.source_type == "confluence"]
        git_results = [r for r in filtered if r.source_type == "git"]

        assert len(confluence_results) == 3  # All Confluence results
        assert len(git_results) == 0  # No Git results

    def test_organize_by_hierarchy(self, mcp_handler, mock_search_results):
        """Test organizing results by hierarchy."""
        confluence_results = [
            r for r in mock_search_results if r.source_type == "confluence"
        ]
        organized = mcp_handler._organize_by_hierarchy(confluence_results)

        # Should group by root title
        assert "Developer Guide" in organized
        assert len(organized["Developer Guide"]) == 2  # Root + child

        # Results should be sorted by depth and title
        dev_guide_results = organized["Developer Guide"]
        assert dev_guide_results[0].depth == 0  # Root first
        assert dev_guide_results[1].depth == 1  # Child second

    def test_format_hierarchical_results(self, mcp_handler, mock_search_results):
        """Test formatting hierarchical results."""
        confluence_results = [
            r
            for r in mock_search_results
            if r.source_type == "confluence" and not r.is_attachment
        ]
        organized = mcp_handler._organize_by_hierarchy(confluence_results)
        formatted = mcp_handler._format_hierarchical_results(organized)

        # Should contain hierarchy indicators
        assert "📁" in formatted
        assert "📄" in formatted
        assert "Developer Guide" in formatted
        assert "API Reference" in formatted
        assert "Score:" in formatted


class TestAttachmentFilters:
    """Test attachment filtering methods."""

    def test_apply_attachment_filters_attachments_only(
        self, mcp_handler, mock_search_results
    ):
        """Test filtering for attachments only."""
        attachment_filter = {"attachments_only": True}
        filtered = mcp_handler._apply_attachment_filters(
            mock_search_results, attachment_filter
        )

        # Should only return attachment results
        assert len(filtered) == 1
        assert filtered[0].is_attachment is True
        assert filtered[0].original_filename == "requirements.pdf"

    def test_apply_attachment_filters_parent_document_title(
        self, mcp_handler, mock_search_results
    ):
        """Test filtering by parent document title."""
        attachment_filter = {"parent_document_title": "Project Planning"}
        filtered = mcp_handler._apply_attachment_filters(
            mock_search_results, attachment_filter
        )

        # Should only return attachments with matching parent document
        assert len(filtered) == 1
        assert filtered[0].parent_document_title == "Project Planning"

    def test_apply_attachment_filters_file_type(self, mcp_handler, mock_search_results):
        """Test filtering by file type."""
        attachment_filter = {"file_type": "pdf"}
        filtered = mcp_handler._apply_attachment_filters(
            mock_search_results, attachment_filter
        )

        # Should only return PDF files
        assert len(filtered) == 1
        assert filtered[0].get_file_type() == "pdf"

    def test_apply_attachment_filters_file_size_min(
        self, mcp_handler, mock_search_results
    ):
        """Test filtering by minimum file size."""
        attachment_filter = {"file_size_min": 1048576}  # 1MB
        filtered = mcp_handler._apply_attachment_filters(
            mock_search_results, attachment_filter
        )

        # Should return documents with file_size >= 1MB OR file_size=None
        # The logic is: if file_size exists AND is less than min, exclude it
        # So None file_size documents pass through
        assert (
            len(filtered) == 3
        )  # 2 non-attachments (None file_size) + 1 attachment (2MB)
        attachment_results = [r for r in filtered if r.is_attachment]
        assert len(attachment_results) == 1
        assert attachment_results[0].file_size >= 1048576

    def test_apply_attachment_filters_file_size_max(
        self, mcp_handler, mock_search_results
    ):
        """Test filtering by maximum file size."""
        attachment_filter = {"file_size_max": 1048576}  # 1MB
        filtered = mcp_handler._apply_attachment_filters(
            mock_search_results, attachment_filter
        )

        # Should return documents with file_size <= 1MB OR file_size=None
        # The logic is: if file_size exists AND is greater than max, exclude it
        # So None file_size documents pass through, but our 2MB attachment is excluded
        assert (
            len(filtered) == 2
        )  # 2 non-attachments (None file_size), attachment excluded

    def test_apply_attachment_filters_author(self, mcp_handler, mock_search_results):
        """Test filtering by author."""
        attachment_filter = {"author": "project.manager@company.com"}
        filtered = mcp_handler._apply_attachment_filters(
            mock_search_results, attachment_filter
        )

        # Should only return files by that author
        assert len(filtered) == 1
        assert filtered[0].attachment_author == "project.manager@company.com"

    def test_apply_attachment_filters_non_confluence_excluded(
        self, mcp_handler, mock_search_results
    ):
        """Test that non-Confluence results are excluded."""
        attachment_filter = {}
        filtered = mcp_handler._apply_attachment_filters(
            mock_search_results, attachment_filter
        )

        # Should exclude Git results, only include Confluence
        confluence_results = [r for r in filtered if r.source_type == "confluence"]
        git_results = [r for r in filtered if r.source_type == "git"]

        assert len(confluence_results) == 3  # All Confluence results
        assert len(git_results) == 0  # No Git results

    def test_format_attachment_search_result(self, mcp_handler, mock_search_results):
        """Test formatting attachment search results."""
        attachment_result = next(r for r in mock_search_results if r.is_attachment)
        formatted = mcp_handler._format_attachment_search_result(attachment_result)

        # Should contain attachment indicators and information
        assert "📎" in formatted
        assert "requirements.pdf" in formatted
        assert "Score:" in formatted
        assert "Project Planning" in formatted
        assert "📄 Attached to:" in formatted

    def test_format_attachment_search_result_non_attachment(
        self, mcp_handler, mock_search_results
    ):
        """Test formatting non-attachment search results."""
        non_attachment_result = next(
            r
            for r in mock_search_results
            if not r.is_attachment and r.source_type == "confluence"
        )
        formatted = mcp_handler._format_attachment_search_result(non_attachment_result)

        # Should contain attachment indicator (even for non-attachments in this method)
        assert "📎 Attachment" in formatted
        # Should contain hierarchy information for Confluence documents
        assert "🏗️" in formatted
        assert "⬇️ Children:" in formatted
        assert "Score:" in formatted
        # The breadcrumb_text is empty string, so no "📍 Path:" will be shown
        # But hierarchy_context should be present
