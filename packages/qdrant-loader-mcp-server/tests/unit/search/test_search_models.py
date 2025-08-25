"""Tests for search models."""

from qdrant_loader_mcp_server.search.components.search_result_models import (
    create_hybrid_search_result,
)
from qdrant_loader_mcp_server.search.models import SearchResult


class TestSearchResult:
    """Test HybridSearchResult model methods."""

    def test_get_display_title_with_breadcrumb(self):
        """Test display title with breadcrumb for Confluence documents."""
        result = create_hybrid_search_result(
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
        result = create_hybrid_search_result(
            score=0.8, text="Test content", source_type="git", source_title="config.py"
        )

        display_title = result.get_display_title()
        assert display_title == "config.py"

    def test_get_display_title_non_confluence(self):
        """Test display title for non-Confluence sources."""
        result = create_hybrid_search_result(
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
        result = create_hybrid_search_result(
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
        result = create_hybrid_search_result(
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
        result = create_hybrid_search_result(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="API Documentation",
        )

        hierarchy_info = result.get_hierarchy_info()
        assert hierarchy_info is None

    def test_is_root_document_true(self):
        """Test root document detection when parent_id is None."""
        result = create_hybrid_search_result(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="Root Document",
            parent_id=None,
        )

        assert result.is_root_document() is True

    def test_is_root_document_false(self):
        """Test root document detection when parent_id exists."""
        result = create_hybrid_search_result(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="Child Document",
            parent_id="parent-123",
        )

        assert result.is_root_document() is False

    def test_has_children_true(self):
        """Test children detection when children_count > 0."""
        result = create_hybrid_search_result(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="Parent Document",
            children_count=3,
        )

        assert result.has_children() is True

    def test_has_children_false_zero(self):
        """Test children detection when children_count is 0."""
        result = create_hybrid_search_result(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="Leaf Document",
            children_count=0,
        )

        assert result.has_children() is False

    def test_has_children_false_none(self):
        """Test children detection when children_count is None."""
        result = create_hybrid_search_result(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="Document",
            children_count=None,
        )

        assert result.has_children() is False

    def test_has_children_via_subsections(self):
        """Test children detection via subsections."""
        result = create_hybrid_search_result(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="Document",
            children_count=0,
            subsections=["Sub 1", "Sub 2"],
        )

        assert result.has_children() is True

    def test_is_root_document_with_both_parent_ids(self):
        """Test root document detection when both parent IDs exist."""
        result = create_hybrid_search_result(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="Child Document",
            parent_id="parent-123",
            parent_document_id="doc-456",
        )

        assert result.is_root_document() is False

    def test_is_root_document_localfile_windows_paths(self):
        """Windows-style path handling for localfile sources."""
        # Single file at repo root should be root document
        r1 = create_hybrid_search_result(
            score=0.8,
            text="Test content",
            source_type="localfile",
            source_title="README.md",
            file_path="C:\\\\repo\\\\README.md",
            repo_name="repo",
        )
        assert r1.is_root_document() is True

        # Nested file in subdirectory should not be root document
        r2 = create_hybrid_search_result(
            score=0.8,
            text="Test content",
            source_type="localfile",
            source_title="config.yaml",
            file_path="C:\\\\repo\\\\configs\\\\config.yaml",
            repo_name="repo",
        )
        assert r2.is_root_document() is False

        # UNC path with server/share and single file
        r3 = create_hybrid_search_result(
            score=0.8,
            text="Test content",
            source_type="localfile",
            source_title="guide.md",
            file_path="\\\\server\\share\\guide.md",
            repo_name=None,
        )
        assert r3.is_root_document() is True

        # UNC path with nested directories
        r4 = create_hybrid_search_result(
            score=0.8,
            text="Test content",
            source_type="localfile",
            source_title="doc.md",
            file_path="\\\\server\\share\\docs\\doc.md",
            repo_name=None,
        )
        assert r4.is_root_document() is False

    def test_get_attachment_info_with_context(self):
        """Test attachment info extraction."""
        result = create_hybrid_search_result(
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
        result = create_hybrid_search_result(
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
        result = create_hybrid_search_result(
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
        result = create_hybrid_search_result(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="document.pdf",
            is_attachment=True,
        )

        assert result.is_file_attachment() is True

    def test_is_file_attachment_false(self):
        """Test file attachment detection when is_attachment is False."""
        result = create_hybrid_search_result(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="Regular Document",
            is_attachment=False,
        )

        assert result.is_file_attachment() is False

    def test_get_file_type_from_mime_type(self):
        """Test file type extraction from MIME type."""
        result = create_hybrid_search_result(
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
        result = create_hybrid_search_result(
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
            result = create_hybrid_search_result(
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
        result = create_hybrid_search_result(
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
        result = create_hybrid_search_result(
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
        result = create_hybrid_search_result(
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
        result = create_hybrid_search_result(
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
        result = create_hybrid_search_result(
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
        """Test HybridSearchResult model validation with all fields."""
        result = create_hybrid_search_result(
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
        """Test HybridSearchResult with only required fields."""
        result = create_hybrid_search_result(
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


class TestSearchResultEnhancedFeatures:
    """Test enhanced features of SearchResult model."""

    def test_get_project_info_full(self):
        """Test project info with all fields."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="git",
            source_title="test.py",
            project_id="proj-123",
            project_name="Test Project",
            project_description="A test project",
            collection_name="test_collection",
        )

        project_info = result.get_project_info()
        assert (
            project_info
            == "Project: Test Project - A test project (Collection: test_collection)"
        )

    def test_get_project_info_minimal(self):
        """Test project info with minimal fields."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="git",
            source_title="test.py",
            project_id="proj-123",
        )

        project_info = result.get_project_info()
        assert project_info == "Project: proj-123"

    def test_get_project_info_none(self):
        """Test project info when no project_id."""
        result = SearchResult(
            score=0.8, text="Test content", source_type="git", source_title="test.py"
        )

        project_info = result.get_project_info()
        assert project_info is None

    def test_get_content_info_all_features(self):
        """Test content info with all content features."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="Rich Document",
            has_code_blocks=True,
            has_tables=True,
            has_images=True,
            has_links=True,
            word_count=500,
            estimated_read_time=3,
        )

        content_info = result.get_content_info()
        assert "Contains: Code, Tables, Images, Links" in content_info
        assert "500 words" in content_info
        assert "~3min read" in content_info

    def test_get_content_info_partial_features(self):
        """Test content info with some features."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="git",
            source_title="code.py",
            has_code_blocks=True,
            has_tables=False,
            word_count=200,
        )

        content_info = result.get_content_info()
        assert "Contains: Code" in content_info
        assert "200 words" in content_info
        assert "Tables" not in content_info

    def test_get_content_info_none(self):
        """Test content info when no content features."""
        result = SearchResult(
            score=0.8, text="Test content", source_type="git", source_title="simple.txt"
        )

        content_info = result.get_content_info()
        assert content_info is None

    def test_get_semantic_info_all_types(self):
        """Test semantic info with entities, topics, and phrases."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="Analysis Doc",
            entities=["Company A", "Product B", "Location C"],
            topics=[
                "machine learning",
                "data analysis",
                "visualization",
                "extra topic",
            ],
            key_phrases=["key phrase 1", "key phrase 2"],
        )

        semantic_info = result.get_semantic_info()
        assert "3 entities" in semantic_info
        assert (
            "Topics: machine learning, data analysis, visualization (+1 more)"
            in semantic_info
        )
        assert "2 key phrases" in semantic_info

    def test_get_semantic_info_dict_format(self):
        """Test semantic info with dict format topics."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="Analysis Doc",
            topics=[
                {"text": "machine learning", "confidence": 0.9},
                {"text": "data analysis", "confidence": 0.8},
                {"name": "visualization"},  # Different key structure
            ],
        )

        semantic_info = result.get_semantic_info()
        assert (
            "Topics: machine learning, data analysis, {'name': 'visualization'}"
            in semantic_info
        )

    def test_get_semantic_info_none(self):
        """Test semantic info when no semantic data."""
        result = SearchResult(
            score=0.8, text="Test content", source_type="git", source_title="simple.py"
        )

        semantic_info = result.get_semantic_info()
        assert semantic_info is None

    def test_get_navigation_info_full(self):
        """Test navigation info with all navigation context."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="Section 2",
            previous_section="Section 1",
            next_section="Section 3",
            sibling_sections=["Section 2a", "Section 2b"],
            subsections=["Subsection 1", "Subsection 2", "Subsection 3"],
        )

        navigation_info = result.get_navigation_info()
        assert "Previous: Section 1" in navigation_info
        assert "Next: Section 3" in navigation_info
        assert "2 siblings" in navigation_info
        assert "3 subsections" in navigation_info

    def test_get_navigation_info_partial(self):
        """Test navigation info with partial data."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="Last Section",
            previous_section="Previous Section",
            subsections=["Sub 1"],
        )

        navigation_info = result.get_navigation_info()
        assert "Previous: Previous Section" in navigation_info
        assert "1 subsections" in navigation_info
        assert "Next:" not in navigation_info

    def test_get_navigation_info_none(self):
        """Test navigation info when no navigation data."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="git",
            source_title="standalone.py",
        )

        navigation_info = result.get_navigation_info()
        assert navigation_info is None

    def test_belongs_to_project_true(self):
        """Test project membership check - positive case."""
        result = create_hybrid_search_result(
            score=0.8,
            text="Test content",
            source_type="git",
            source_title="test.py",
            project_id="proj-123",
        )

        assert result.belongs_to_project("proj-123") is True

    def test_belongs_to_project_false(self):
        """Test project membership check - negative case."""
        result = create_hybrid_search_result(
            score=0.8,
            text="Test content",
            source_type="git",
            source_title="test.py",
            project_id="proj-123",
        )

        assert result.belongs_to_project("proj-456") is False

    def test_belongs_to_project_no_project(self):
        """Test project membership check when no project_id."""
        result = create_hybrid_search_result(
            score=0.8, text="Test content", source_type="git", source_title="test.py"
        )

        assert result.belongs_to_project("proj-123") is False

    def test_belongs_to_any_project_true(self):
        """Test multiple project membership check - positive case."""
        result = create_hybrid_search_result(
            score=0.8,
            text="Test content",
            source_type="git",
            source_title="test.py",
            project_id="proj-123",
        )

        assert result.belongs_to_any_project(["proj-123", "proj-456"]) is True

    def test_belongs_to_any_project_false(self):
        """Test multiple project membership check - negative case."""
        result = create_hybrid_search_result(
            score=0.8,
            text="Test content",
            source_type="git",
            source_title="test.py",
            project_id="proj-789",
        )

        assert result.belongs_to_any_project(["proj-123", "proj-456"]) is False

    def test_belongs_to_any_project_no_project(self):
        """Test multiple project membership check when no project_id."""
        result = create_hybrid_search_result(
            score=0.8, text="Test content", source_type="git", source_title="test.py"
        )

        assert result.belongs_to_any_project(["proj-123", "proj-456"]) is False

    def test_is_code_content_code_blocks(self):
        """Test code content detection via code blocks."""
        result = create_hybrid_search_result(
            score=0.8,
            text="Test content",
            source_type="git",
            source_title="code.py",
            has_code_blocks=True,
        )

        assert result.is_code_content() is True

    def test_is_code_content_section_type(self):
        """Test code content detection via section type."""
        result = create_hybrid_search_result(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="Code Section",
            section_type="code",
        )

        assert result.is_code_content() is True

    def test_is_code_content_false(self):
        """Test code content detection - negative case."""
        result = create_hybrid_search_result(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="Documentation",
        )

        assert result.is_code_content() is False

    def test_is_documentation_confluence(self):
        """Test documentation detection for Confluence."""
        result = create_hybrid_search_result(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="User Guide",
        )

        assert result.is_documentation() is True

    def test_is_documentation_localfile(self):
        """Test documentation detection for local files."""
        result = create_hybrid_search_result(
            score=0.8,
            text="Test content",
            source_type="localfile",
            source_title="README.md",
        )

        assert result.is_documentation() is True

    def test_is_documentation_with_code(self):
        """Test documentation detection with code blocks."""
        result = create_hybrid_search_result(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="API Guide",
            has_code_blocks=True,
        )

        assert result.is_documentation() is False

    def test_is_documentation_false(self):
        """Test documentation detection - negative case."""
        result = create_hybrid_search_result(
            score=0.8, text="Test content", source_type="git", source_title="source.py"
        )

        assert result.is_documentation() is False

    def test_is_structured_data_tables(self):
        """Test structured data detection via tables."""
        result = create_hybrid_search_result(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="Data Report",
            has_tables=True,
        )

        assert result.is_structured_data() is True

    def test_is_structured_data_excel(self):
        """Test structured data detection via Excel sheet."""
        result = create_hybrid_search_result(
            score=0.8,
            text="Test content",
            source_type="localfile",
            source_title="data.xlsx",
            is_excel_sheet=True,
        )

        assert result.is_structured_data() is True

    def test_is_structured_data_false(self):
        """Test structured data detection - negative case."""
        result = create_hybrid_search_result(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="Plain Text",
        )

        assert result.is_structured_data() is False


class TestSearchResultMissingCoverage:
    """Test cases specifically targeting missing coverage lines."""

    def test_get_display_title_empty_source_with_filepath(self):
        """Test display title when source_title is empty but file_path exists."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="git",
            source_title="",
            file_path="/path/to/config.py",
        )

        display_title = result.get_display_title()
        assert display_title == "config.py"

    def test_get_display_title_empty_source_with_repo(self):
        """Test display title when source_title is empty but repo_name exists."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="git",
            source_title="",
            repo_name="my-repo",
        )

        display_title = result.get_display_title()
        assert display_title == "my-repo"

    def test_get_display_title_empty_fallback(self):
        """Test display title fallback to 'Untitled'."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="git",
            source_title="   ",  # Whitespace only
        )

        display_title = result.get_display_title()
        assert display_title == "Untitled"

    def test_get_hierarchy_info_non_confluence_returns_none(self):
        """Test hierarchy info for non-Confluence sources returns None."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="git",
            source_title="test.py",
            hierarchy_context="Some context",
        )

        hierarchy_info = result.get_hierarchy_info()
        assert hierarchy_info is None

    def test_get_hierarchy_info_confluence_with_all_parts(self):
        """Test hierarchy info with all components for Confluence."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="Document",
            hierarchy_context="Path: Root > Parent | Depth: 2",
            section_breadcrumb="Document > Section > Subsection",
            chunk_index=1,
            total_chunks=3,
        )

        hierarchy_info = result.get_hierarchy_info()
        assert "Path: Root > Parent | Depth: 2" in hierarchy_info
        assert "Section: Document > Section > Subsection" in hierarchy_info
        assert "Chunk: 2/3" in hierarchy_info

    def test_get_hierarchy_info_confluence_partial(self):
        """Test hierarchy info with only some components for Confluence."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="Document",
            hierarchy_context="Path: Root > Parent",
        )

        hierarchy_info = result.get_hierarchy_info()
        assert hierarchy_info == "Path: Root > Parent"

    def test_get_file_type_original_with_conversion(self):
        """Test file type with conversion information."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="localfile",
            source_title="data.xlsx",
            original_file_type="xlsx",
            is_converted=True,
            conversion_method="openpyxl",
        )

        file_type = result.get_file_type()
        assert file_type == "xlsx (converted via openpyxl)"

    def test_get_file_type_original_no_conversion(self):
        """Test file type with original_file_type but no conversion."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="localfile",
            source_title="document.pdf",
            original_file_type="pdf",
            is_converted=False,
        )

        file_type = result.get_file_type()
        assert file_type == "pdf"

    def test_get_file_type_from_mime_type(self):
        """Test file type extraction from MIME type."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="localfile",
            source_title="Document",
            mime_type="application/pdf",
        )

        file_type = result.get_file_type()
        assert file_type == "application/pdf"

    def test_get_file_type_from_filename_extension(self):
        """Test file type extraction from original filename."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="localfile",
            source_title="Document",
            original_filename="document.docx",
        )

        file_type = result.get_file_type()
        assert file_type == "docx"

    def test_get_file_type_filename_no_extension(self):
        """Test file type when filename has no extension."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="localfile",
            source_title="Document",
            original_filename="README",
        )

        file_type = result.get_file_type()
        assert file_type is None

    def test_belongs_to_project_exact_match(self):
        """Test exact project ID matching."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="git",
            source_title="test.py",
            project_id="proj-123",
        )

        assert result.belongs_to_project("proj-123") is True
        assert result.belongs_to_project("proj-456") is False

    def test_belongs_to_any_project_with_matching_id(self):
        """Test project membership in list with matching ID."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="git",
            source_title="test.py",
            project_id="proj-123",
        )

        assert result.belongs_to_any_project(["proj-123", "proj-456"]) is True
        assert result.belongs_to_any_project(["proj-789", "proj-456"]) is False

    def test_belongs_to_any_project_no_project_id(self):
        """Test project membership when result has no project_id."""
        result = SearchResult(
            score=0.8, text="Test content", source_type="git", source_title="test.py"
        )

        assert result.belongs_to_any_project(["proj-123", "proj-456"]) is False

    def test_is_code_content_via_has_code_blocks(self):
        """Test code content detection via has_code_blocks."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="Documentation",
            has_code_blocks=True,
        )

        assert result.is_code_content() is True

    def test_is_code_content_via_section_type(self):
        """Test code content detection via section_type."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="Code Section",
            section_type="code",
        )

        assert result.is_code_content() is True

    def test_is_documentation_confluence_source(self):
        """Test documentation detection for Confluence source."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="User Guide",
        )

        assert result.is_documentation() is True

    def test_is_documentation_localfile_source(self):
        """Test documentation detection for localfile source."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="localfile",
            source_title="README.md",
        )

        assert result.is_documentation() is True

    def test_is_documentation_with_code_blocks(self):
        """Test documentation detection fails when has_code_blocks is True."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="API Guide",
            has_code_blocks=True,
        )

        assert result.is_documentation() is False

    def test_is_structured_data_via_has_tables(self):
        """Test structured data detection via has_tables."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="Data Report",
            has_tables=True,
        )

        assert result.is_structured_data() is True

    def test_is_structured_data_via_is_excel_sheet(self):
        """Test structured data detection via is_excel_sheet."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="localfile",
            source_title="data.xlsx",
            is_excel_sheet=True,
        )

        assert result.is_structured_data() is True

    def test_get_section_context_full(self):
        """Test section context with all section information."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="API Guide",
            section_title="Authentication Methods",
            section_type="h2",
            section_level=2,
            section_anchor="auth-methods",
        )

        section_context = result.get_section_context()
        assert section_context == "[H2] Authentication Methods (#auth-methods)"

    def test_get_section_context_minimal(self):
        """Test section context with minimal information."""
        result = SearchResult(
            score=0.8,
            text="Test content",
            source_type="confluence",
            source_title="Guide",
            section_title="Overview",
        )

        section_context = result.get_section_context()
        assert section_context == "Overview"

    def test_get_section_context_none(self):
        """Test section context when no section title."""
        result = SearchResult(
            score=0.8, text="Test content", source_type="git", source_title="code.py"
        )

        section_context = result.get_section_context()
        assert section_context is None
