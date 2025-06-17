"""Tests for search models."""

from qdrant_loader_mcp_server.search.models import SearchResult


class TestSearchResult:
    """Test SearchResult model methods."""

    def test_get_display_title_with_breadcrumb(self):
        """Test display title with breadcrumb for Confluence documents."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="API Documentation",
            breadcrumb_text="Developer Guide > API > Documentation",
        )

        display_title = result.get_display_title()
        assert (
            display_title == "API Documentation (Developer Guide > API > Documentation)"
        )

    def test_get_display_title_without_breadcrumb(self):
        """Test display title without breadcrumb."""
        result = SearchResult(
            score=0.8, text="Test content", source_type="git", source_title="config.py"
        )

        display_title = result.get_display_title()
        assert display_title == "config.py"

    def test_get_display_title_non_confluence(self):
        """Test display title for non-Confluence sources."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="git",
            source_title="README.md",
            breadcrumb_text="Some breadcrumb",  # Should be ignored for non-Confluence
        )

        display_title = result.get_display_title()
        assert display_title == "README.md"

    def test_get_hierarchy_info_with_context(self):
        """Test hierarchy info extraction."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="API Documentation",
            hierarchy_context="Path: Developer Guide > API | Depth: 2 | Children: 3",
        )

        hierarchy_info = result.get_hierarchy_info()
        assert hierarchy_info == "Path: Developer Guide > API | Depth: 2 | Children: 3"

    def test_get_hierarchy_info_non_confluence(self):
        """Test hierarchy info for non-Confluence sources."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="git",
            source_title="config.py",
            hierarchy_context="Some context",
        )

        hierarchy_info = result.get_hierarchy_info()
        assert hierarchy_info is None

    def test_get_hierarchy_info_no_context(self):
        """Test hierarchy info when no context is available."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="API Documentation",
        )

        hierarchy_info = result.get_hierarchy_info()
        assert hierarchy_info is None

    def test_is_root_document_true(self):
        """Test root document detection when parent_id is None."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="Root Document",
            parent_id=None,
        )

        assert result.is_root_document() is True

    def test_is_root_document_false(self):
        """Test root document detection when parent_id exists."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="Child Document",
            parent_id="parent-123",
        )

        assert result.is_root_document() is False

    def test_has_children_true(self):
        """Test children detection when children_count > 0."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="Parent Document",
            children_count=3,
        )

        assert result.has_children() is True

    def test_has_children_false_zero(self):
        """Test children detection when children_count is 0."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="Leaf Document",
            children_count=0,
        )

        assert result.has_children() is False

    def test_has_children_false_none(self):
        """Test children detection when children_count is None."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="Document",
            children_count=None,
        )

        assert result.has_children() is False

    def test_get_attachment_info_with_context(self):
        """Test attachment info extraction."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="requirements.pdf",
            is_attachment=True,
            attachment_context="File: requirements.pdf | Size: 2.0 MB | Type: application/pdf",
        )

        attachment_info = result.get_attachment_info()
        assert (
            attachment_info
            == "File: requirements.pdf | Size: 2.0 MB | Type: application/pdf"
        )

    def test_get_attachment_info_not_attachment(self):
        """Test attachment info for non-attachment documents."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="Regular Document",
            is_attachment=False,
            attachment_context="Some context",
        )

        attachment_info = result.get_attachment_info()
        assert attachment_info is None

    def test_get_attachment_info_no_context(self):
        """Test attachment info when no context is available."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="attachment.pdf",
            is_attachment=True,
            attachment_context=None,
        )

        attachment_info = result.get_attachment_info()
        assert attachment_info is None

    def test_is_file_attachment_true(self):
        """Test file attachment detection when is_attachment is True."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="document.pdf",
            is_attachment=True,
        )

        assert result.is_file_attachment() is True

    def test_is_file_attachment_false(self):
        """Test file attachment detection when is_attachment is False."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="Regular Document",
            is_attachment=False,
        )

        assert result.is_file_attachment() is False

    def test_get_file_type_from_mime_type(self):
        """Test file type extraction from MIME type."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="document.pdf",
            mime_type="application/pdf",
        )

        file_type = result.get_file_type()
        assert file_type == "application/pdf"

    def test_get_file_type_from_filename_extension(self):
        """Test file type extraction from filename extension."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="document.pdf",
            original_filename="requirements.pdf",
            mime_type=None,
        )

        file_type = result.get_file_type()
        assert file_type == "pdf"

    def test_get_file_type_from_filename_various_extensions(self):
        """Test file type extraction for various file extensions."""
        test_cases = [
            ("document.docx", "docx"),
            ("spreadsheet.xlsx", "xlsx"),
            ("presentation.pptx", "pptx"),
            ("image.jpg", "jpg"),
            ("image.png", "png"),
            ("archive.zip", "zip"),
            ("text.txt", "txt"),
            ("data.json", "json"),
            ("style.css", "css"),
            ("script.js", "js"),
        ]

        for filename, expected_type in test_cases:
            result = SearchResult(
                score=0.8,
                text="Test content",
                source_type="confluence",
                source_title=filename,
                original_filename=filename,
                mime_type=None,
            )

            file_type = result.get_file_type()
            assert file_type == expected_type, f"Failed for {filename}"

    def test_get_file_type_no_extension(self):
        """Test file type extraction when filename has no extension."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="document",
            original_filename="document",
            mime_type=None,
        )

        file_type = result.get_file_type()
        assert file_type is None

    def test_get_file_type_hidden_file(self):
        """Test file type extraction for hidden files (starting with dot)."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="git",
            source_title=".gitignore",
            original_filename=".gitignore",
            mime_type=None,
        )

        file_type = result.get_file_type()
        assert file_type is None  # No extension after the dot

    def test_get_file_type_multiple_dots(self):
        """Test file type extraction for files with multiple dots."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="backup.tar.gz",
            original_filename="backup.tar.gz",
            mime_type=None,
        )

        file_type = result.get_file_type()
        assert file_type == "gz"  # Should get the last extension

    def test_get_file_type_case_insensitive(self):
        """Test file type extraction is case insensitive."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="DOCUMENT.PDF",
            original_filename="DOCUMENT.PDF",
            mime_type=None,
        )

        file_type = result.get_file_type()
        assert file_type == "pdf"  # Should be lowercase

    def test_get_file_type_no_filename_no_mime(self):
        """Test file type extraction when both filename and MIME type are None."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="Document",
            original_filename=None,
            mime_type=None,
        )

        file_type = result.get_file_type()
        assert file_type is None

    def test_search_result_model_validation(self):
        """Test SearchResult model validation with all fields."""
        result = SearchResult(
            score=0.95,
            text="Complete test content with all fields",
            source_type="confluence",
            source_title="Complete Document",
            source_url="https://docs.company.com/complete",
            file_path="/path/to/file.txt",
            repo_name="test-repo",
            parent_id="parent-456",
            parent_title="Parent Document",
            breadcrumb_text="Root > Parent > Complete",
            depth=2,
            children_count=5,
            hierarchy_context="Path: Root > Parent | Depth: 2 | Children: 5",
            is_attachment=True,
            parent_document_id="doc-789",
            parent_document_title="Main Document",
            attachment_id="att-123",
            original_filename="complete.pdf",
            file_size=1048576,
            mime_type="application/pdf",
            attachment_author="test.user@company.com",
            attachment_context="File: complete.pdf | Size: 1.0 MB | Type: application/pdf",
        )

        # Verify all fields are set correctly
        assert result.score == 0.95
        assert result.text == "Complete test content with all fields"
        assert result.source_type == "confluence"
        assert result.source_title == "Complete Document"
        assert result.source_url == "https://docs.company.com/complete"
        assert result.file_path == "/path/to/file.txt"
        assert result.repo_name == "test-repo"
        assert result.parent_id == "parent-456"
        assert result.parent_title == "Parent Document"
        assert result.breadcrumb_text == "Root > Parent > Complete"
        assert result.depth == 2
        assert result.children_count == 5
        assert (
            result.hierarchy_context == "Path: Root > Parent | Depth: 2 | Children: 5"
        )
        assert result.is_attachment is True
        assert result.parent_document_id == "doc-789"
        assert result.parent_document_title == "Main Document"
        assert result.attachment_id == "att-123"
        assert result.original_filename == "complete.pdf"
        assert result.file_size == 1048576
        assert result.mime_type == "application/pdf"
        assert result.attachment_author == "test.user@company.com"
        assert (
            result.attachment_context
            == "File: complete.pdf | Size: 1.0 MB | Type: application/pdf"
        )

    def test_search_result_minimal_fields(self):
        """Test SearchResult with only required fields."""
        result = SearchResult(
            score=0.5,
            text="Minimal content",
            source_type="git",
            source_title="minimal.py",
        )

        # Verify required fields
        assert result.score == 0.5
        assert result.text == "Minimal content"
        assert result.source_type == "git"
        assert result.source_title == "minimal.py"

        # Verify optional fields have default values
        assert result.source_url is None
        assert result.file_path is None
        assert result.repo_name is None
        assert result.parent_id is None
        assert result.parent_title is None
        assert result.breadcrumb_text is None
        assert result.depth is None
        assert result.children_count is None
        assert result.hierarchy_context is None
        assert result.is_attachment is False
        assert result.parent_document_id is None
        assert result.parent_document_title is None
        assert result.attachment_id is None
        assert result.original_filename is None
        assert result.file_size is None
        assert result.mime_type is None
        assert result.attachment_author is None
        assert result.attachment_context is None
