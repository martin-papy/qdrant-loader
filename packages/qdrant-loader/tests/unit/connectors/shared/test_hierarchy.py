"""Unit tests for hierarchy tracking utilities.

POC1-010: Tests for the hierarchy module implementing the Unstructured.io pattern.
"""

from qdrant_loader.connectors.shared.hierarchy import (
    HierarchyMetadata,
    build_hierarchy_from_ancestors,
    build_hierarchy_from_jira,
    build_hierarchy_from_markdown_sections,
    build_hierarchy_from_path,
    merge_hierarchy_metadata,
)


class TestHierarchyMetadata:
    """Tests for HierarchyMetadata dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        hierarchy = HierarchyMetadata(
            parent_id="parent-123",
            depth=2,
            breadcrumb=["Root", "Parent", "Current"],
            breadcrumb_text="Root > Parent > Current",
        )

        result = hierarchy.to_dict()

        assert result == {
            "parent_id": "parent-123",
            "depth": 2,
            "breadcrumb": ["Root", "Parent", "Current"],
            "breadcrumb_text": "Root > Parent > Current",
        }

    def test_to_dict_with_none_parent(self):
        """Test conversion when parent_id is None (root element)."""
        hierarchy = HierarchyMetadata(
            parent_id=None,
            depth=0,
            breadcrumb=["Root"],
            breadcrumb_text="Root",
        )

        result = hierarchy.to_dict()

        assert result["parent_id"] is None
        assert result["depth"] == 0


class TestBuildHierarchyFromPath:
    """Tests for build_hierarchy_from_path function (Git, LocalFile, PublicDocs)."""

    def test_simple_path(self):
        """Test with a simple file path."""
        result = build_hierarchy_from_path("docs/api/reference.md")

        assert result.depth == 3
        assert result.breadcrumb == ["docs", "api", "reference.md"]
        assert result.breadcrumb_text == "docs > api > reference.md"
        assert result.parent_id == "docs/api"

    def test_path_with_root_name(self):
        """Test with a root name (repository name)."""
        result = build_hierarchy_from_path(
            "docs/api/reference.md", root_name="my-repo"
        )

        assert result.depth == 4
        assert result.breadcrumb == ["my-repo", "docs", "api", "reference.md"]
        assert result.breadcrumb_text == "my-repo > docs > api > reference.md"
        assert result.parent_id == "my-repo/docs/api"

    def test_single_file(self):
        """Test with a single file (no directories)."""
        result = build_hierarchy_from_path("README.md")

        assert result.depth == 1
        assert result.breadcrumb == ["README.md"]
        assert result.breadcrumb_text == "README.md"
        assert result.parent_id is None

    def test_single_file_with_root(self):
        """Test single file with root name."""
        result = build_hierarchy_from_path("README.md", root_name="project")

        assert result.depth == 2
        assert result.breadcrumb == ["project", "README.md"]
        assert result.parent_id == "project"

    def test_deep_path(self):
        """Test with a deeply nested path."""
        result = build_hierarchy_from_path(
            "src/core/chunking/strategy/markdown/splitters/base.py"
        )

        assert result.depth == 7
        assert len(result.breadcrumb) == 7
        assert result.breadcrumb[-1] == "base.py"
        assert result.parent_id == "src/core/chunking/strategy/markdown/splitters"

    def test_windows_path(self):
        """Test with backslash separator (Windows paths)."""
        result = build_hierarchy_from_path(
            "docs\\api\\reference.md", separator="\\"
        )

        assert result.depth == 3
        assert result.breadcrumb == ["docs", "api", "reference.md"]

    def test_empty_segments_filtered(self):
        """Test that empty path segments are filtered out."""
        result = build_hierarchy_from_path("docs//api///reference.md")

        assert result.depth == 3
        assert "" not in result.breadcrumb


class TestBuildHierarchyFromAncestors:
    """Tests for build_hierarchy_from_ancestors function (Confluence)."""

    def test_with_ancestors_and_space(self):
        """Test with Confluence ancestors and space name."""
        ancestors = [
            {"id": "1", "title": "Documentation"},
            {"id": "2", "title": "API Reference"},
        ]

        result = build_hierarchy_from_ancestors(
            ancestors, space_name="DEV", current_title="Auth API"
        )

        assert result.depth == 4
        assert result.breadcrumb == ["DEV", "Documentation", "API Reference", "Auth API"]
        assert result.breadcrumb_text == "DEV > Documentation > API Reference > Auth API"
        assert result.parent_id == "2"

    def test_without_space_name(self):
        """Test without space name."""
        ancestors = [{"id": "1", "title": "Parent"}]

        result = build_hierarchy_from_ancestors(
            ancestors, current_title="Current Page"
        )

        assert result.depth == 2
        assert result.breadcrumb == ["Parent", "Current Page"]
        assert result.parent_id == "1"

    def test_empty_ancestors(self):
        """Test with no ancestors (root page)."""
        result = build_hierarchy_from_ancestors(
            [], space_name="TEAM", current_title="Home"
        )

        assert result.depth == 2
        assert result.breadcrumb == ["TEAM", "Home"]
        assert result.parent_id is None

    def test_ancestors_with_name_key(self):
        """Test ancestors using 'name' instead of 'title'."""
        ancestors = [{"id": "1", "name": "Parent Section"}]

        result = build_hierarchy_from_ancestors(ancestors, current_title="Child")

        assert result.breadcrumb == ["Parent Section", "Child"]

    def test_only_space_name(self):
        """Test with only space name (root of space)."""
        result = build_hierarchy_from_ancestors([], space_name="DOCS")

        assert result.depth == 1
        assert result.breadcrumb == ["DOCS"]


class TestBuildHierarchyFromJira:
    """Tests for build_hierarchy_from_jira function."""

    def test_epic_hierarchy(self):
        """Test Epic (top-level under project)."""
        result = build_hierarchy_from_jira(
            issue_type="Epic",
            project_key="PROJ",
            issue_key="PROJ-50",
        )

        assert result.depth == 2
        assert result.breadcrumb == ["PROJ", "PROJ-50"]
        assert result.parent_id == "PROJ"

    def test_story_with_epic(self):
        """Test Story linked to Epic."""
        result = build_hierarchy_from_jira(
            issue_type="Story",
            epic_key="PROJ-50",
            project_key="PROJ",
            issue_key="PROJ-100",
        )

        assert result.depth == 3
        assert result.breadcrumb == ["PROJ", "PROJ-50", "PROJ-100"]
        assert result.parent_id == "PROJ-50"

    def test_subtask(self):
        """Test Sub-task with parent and epic."""
        result = build_hierarchy_from_jira(
            issue_type="Sub-task",
            parent_key="PROJ-100",
            epic_key="PROJ-50",
            project_key="PROJ",
            issue_key="PROJ-101",
        )

        assert result.depth == 4
        assert result.breadcrumb == ["PROJ", "PROJ-50", "PROJ-100", "PROJ-101"]
        assert result.parent_id == "PROJ-100"

    def test_task_without_epic(self):
        """Test Task without Epic."""
        result = build_hierarchy_from_jira(
            issue_type="Task",
            project_key="PROJ",
            issue_key="PROJ-200",
        )

        assert result.depth == 2
        assert result.breadcrumb == ["PROJ", "PROJ-200"]
        # No epic, so parent is None (task is under project but not hierarchically)
        assert result.parent_id is None

    def test_bug_with_epic(self):
        """Test Bug linked to Epic."""
        result = build_hierarchy_from_jira(
            issue_type="Bug",
            epic_key="PROJ-10",
            project_key="PROJ",
            issue_key="PROJ-300",
        )

        assert result.depth == 3
        assert result.parent_id == "PROJ-10"


class TestBuildHierarchyFromMarkdownSections:
    """Tests for build_hierarchy_from_markdown_sections function."""

    def test_basic_section(self):
        """Test basic section hierarchy."""
        result = build_hierarchy_from_markdown_sections(
            section_path=["Installation"],
            section_level=1,
            document_title="Getting Started",
        )

        assert result.depth == 2  # 1 for doc title + 1 for section level
        assert result.breadcrumb == ["Getting Started", "Installation"]
        assert result.breadcrumb_text == "Getting Started > Installation"

    def test_nested_section(self):
        """Test nested section with path."""
        result = build_hierarchy_from_markdown_sections(
            section_path=["Installation", "Prerequisites"],
            section_level=2,
            document_title="Guide",
        )

        assert result.depth == 3
        assert result.breadcrumb == ["Guide", "Installation", "Prerequisites"]

    def test_without_document_title(self):
        """Test section without document title."""
        result = build_hierarchy_from_markdown_sections(
            section_path=["Overview"],
            section_level=1,
        )

        assert result.depth == 1
        assert result.breadcrumb == ["Overview"]
        assert result.breadcrumb_text == "Overview"

    def test_with_parent_section_id(self):
        """Test with explicit parent section ID."""
        result = build_hierarchy_from_markdown_sections(
            section_path=["API", "Methods"],
            section_level=2,
            document_id="doc-123",
            document_title="Reference",
            parent_section_id="doc-123_chunk_0",
        )

        assert result.parent_id == "doc-123_chunk_0"
        assert result.depth == 3

    def test_empty_path(self):
        """Test with empty section path (preamble/content before headers)."""
        result = build_hierarchy_from_markdown_sections(
            section_path=[],
            section_level=0,
            document_title="README",
        )

        assert result.depth == 1
        assert result.breadcrumb == ["README"]


class TestMergeHierarchyMetadata:
    """Tests for merge_hierarchy_metadata function."""

    def test_merge_into_empty_metadata(self):
        """Test merging into empty metadata."""
        base = {}
        hierarchy = HierarchyMetadata(
            parent_id="parent-1",
            depth=2,
            breadcrumb=["A", "B"],
            breadcrumb_text="A > B",
        )

        result = merge_hierarchy_metadata(base, hierarchy)

        assert result["parent_id"] == "parent-1"
        assert result["depth"] == 2
        assert result["breadcrumb"] == ["A", "B"]
        assert result["breadcrumb_text"] == "A > B"

    def test_merge_preserves_existing(self):
        """Test that merge preserves existing metadata."""
        base = {
            "title": "My Document",
            "source": "git",
            "custom_field": "value",
        }
        hierarchy = HierarchyMetadata(
            parent_id="parent-1",
            depth=1,
            breadcrumb=["Doc"],
            breadcrumb_text="Doc",
        )

        result = merge_hierarchy_metadata(base, hierarchy)

        assert result["title"] == "My Document"
        assert result["source"] == "git"
        assert result["custom_field"] == "value"
        assert result["parent_id"] == "parent-1"

    def test_merge_does_not_modify_original(self):
        """Test that original metadata is not modified."""
        base = {"existing": "value"}
        hierarchy = HierarchyMetadata(
            parent_id="p1",
            depth=1,
            breadcrumb=["X"],
            breadcrumb_text="X",
        )

        result = merge_hierarchy_metadata(base, hierarchy)

        assert "parent_id" not in base
        assert result is not base


class TestIntegrationScenarios:
    """Integration tests for real-world scenarios."""

    def test_git_repository_file(self):
        """Test hierarchy for a file in a Git repository."""
        hierarchy = build_hierarchy_from_path(
            "packages/qdrant-loader/src/qdrant_loader/core/document.py",
            root_name="qdrant-loader",
        )

        assert hierarchy.depth == 7
        assert hierarchy.breadcrumb[0] == "qdrant-loader"
        assert hierarchy.breadcrumb[-1] == "document.py"
        assert "core" in hierarchy.breadcrumb

    def test_confluence_page_hierarchy(self):
        """Test hierarchy for a Confluence page."""
        ancestors = [
            {"id": "100", "title": "Engineering"},
            {"id": "200", "title": "Backend"},
            {"id": "300", "title": "API Documentation"},
        ]

        hierarchy = build_hierarchy_from_ancestors(
            ancestors,
            space_name="TECH",
            current_title="Authentication Guide",
        )

        assert hierarchy.depth == 5
        assert hierarchy.breadcrumb_text == (
            "TECH > Engineering > Backend > API Documentation > Authentication Guide"
        )
        assert hierarchy.parent_id == "300"

    def test_jira_subtask_hierarchy(self):
        """Test hierarchy for a JIRA sub-task."""
        hierarchy = build_hierarchy_from_jira(
            issue_type="Sub-task",
            parent_key="PROJ-100",
            epic_key="PROJ-50",
            project_key="PROJ",
            issue_key="PROJ-101",
        )

        # Full path: PROJ -> PROJ-50 (epic) -> PROJ-100 (parent) -> PROJ-101
        assert hierarchy.depth == 4
        assert hierarchy.breadcrumb == ["PROJ", "PROJ-50", "PROJ-100", "PROJ-101"]

    def test_markdown_document_sections(self):
        """Test hierarchy for markdown document sections."""
        # Simulate chunking a document with multiple levels
        chunks = [
            {"path": [], "level": 1, "title": "Introduction"},
            {"path": ["Introduction"], "level": 2, "title": "Overview"},
            {"path": ["Introduction"], "level": 2, "title": "Goals"},
            {"path": [], "level": 1, "title": "Implementation"},
            {"path": ["Implementation"], "level": 2, "title": "Architecture"},
            {"path": ["Implementation", "Architecture"], "level": 3, "title": "Components"},
        ]

        hierarchies = []
        for chunk in chunks:
            h = build_hierarchy_from_markdown_sections(
                section_path=chunk["path"] + [chunk["title"]],
                section_level=chunk["level"],
                document_title="Design Doc",
            )
            hierarchies.append(h)

        # Verify structure
        assert hierarchies[0].breadcrumb_text == "Design Doc > Introduction"
        assert hierarchies[1].breadcrumb_text == "Design Doc > Introduction > Overview"
        assert hierarchies[5].breadcrumb_text == (
            "Design Doc > Implementation > Architecture > Components"
        )
        assert hierarchies[5].depth == 4
