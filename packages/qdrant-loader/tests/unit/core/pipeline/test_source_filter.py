"""Tests for SourceFilter."""

from unittest.mock import MagicMock

import pytest
from qdrant_loader.config import SourcesConfig
from qdrant_loader.config.source_config import SourceConfig
from qdrant_loader.core.pipeline.source_filter import SourceFilter


class TestSourceFilter:
    """Test cases for SourceFilter."""

    @pytest.fixture
    def sample_sources_config(self):
        """Create a sample SourcesConfig with multiple source types."""
        config = SourcesConfig()

        # Add Git sources
        git_source1 = MagicMock(spec=SourceConfig)
        git_source1.source_type = "git"
        git_source1.source = "repo1"
        git_source1.name = "repo1"

        git_source2 = MagicMock(spec=SourceConfig)
        git_source2.source_type = "git"
        git_source2.source = "repo2"
        git_source2.name = "repo2"

        config.git = {"repo1": git_source1, "repo2": git_source2}

        # Add Confluence sources
        confluence_source = MagicMock(spec=SourceConfig)
        confluence_source.source_type = "confluence"
        confluence_source.source = "space1"
        confluence_source.name = "space1"

        config.confluence = {"space1": confluence_source}

        # Add Jira sources
        jira_source = MagicMock(spec=SourceConfig)
        jira_source.source_type = "jira"
        jira_source.source = "project1"
        jira_source.name = "project1"

        config.jira = {"project1": jira_source}

        # Add LocalFile sources
        localfile_source = MagicMock(spec=SourceConfig)
        localfile_source.source_type = "localfile"
        localfile_source.source = "docs"
        localfile_source.name = "docs"

        config.localfile = {"docs": localfile_source}

        return config

    def test_no_filters_returns_original(self, sample_sources_config):
        """Test that no filters returns the original config."""
        filter_obj = SourceFilter()

        result = filter_obj.filter_sources(sample_sources_config)

        assert result == sample_sources_config
        assert len(result.git) == 2
        assert len(result.confluence) == 1
        assert len(result.jira) == 1
        assert len(result.localfile) == 1

    def test_filter_by_source_type_git(self, sample_sources_config):
        """Test filtering by git source type."""
        filter_obj = SourceFilter()

        result = filter_obj.filter_sources(sample_sources_config, source_type="git")

        # Should return a new SourcesConfig with only git sources
        assert isinstance(result, SourcesConfig)
        assert len(result.git) == 2
        assert len(result.confluence) == 0
        assert len(result.jira) == 0
        assert len(result.localfile) == 0
        assert len(result.publicdocs) == 0

    def test_filter_by_source_type_confluence(self, sample_sources_config):
        """Test filtering by confluence source type."""
        filter_obj = SourceFilter()

        result = filter_obj.filter_sources(
            sample_sources_config, source_type="confluence"
        )

        assert isinstance(result, SourcesConfig)
        assert len(result.git) == 0
        assert len(result.confluence) == 1
        assert len(result.jira) == 0
        assert len(result.localfile) == 0
        assert len(result.publicdocs) == 0

    def test_filter_by_source_type_case_insensitive(self, sample_sources_config):
        """Test that source type filtering is case insensitive."""
        filter_obj = SourceFilter()

        result = filter_obj.filter_sources(sample_sources_config, source_type="GIT")

        assert isinstance(result, SourcesConfig)
        assert len(result.git) == 2
        assert len(result.confluence) == 0

    def test_filter_by_source_type_mixed_case(self, sample_sources_config):
        """Test filtering with mixed case source type."""
        filter_obj = SourceFilter()

        result = filter_obj.filter_sources(
            sample_sources_config, source_type="ConFluEnCe"
        )

        assert isinstance(result, SourcesConfig)
        assert len(result.git) == 0
        assert len(result.confluence) == 1

    def test_filter_nonexistent_source_type(self, sample_sources_config):
        """Test filtering by nonexistent source type returns empty config."""
        filter_obj = SourceFilter()

        result = filter_obj.filter_sources(
            sample_sources_config, source_type="nonexistent"
        )

        assert isinstance(result, SourcesConfig)
        assert len(result.git) == 0
        assert len(result.confluence) == 0
        assert len(result.jira) == 0
        assert len(result.publicdocs) == 0
        assert len(result.localfile) == 0

    def test_filter_by_source_name(self, sample_sources_config):
        """Test filtering by specific source name."""
        filter_obj = SourceFilter()

        result = filter_obj.filter_sources(sample_sources_config, source="repo1")

        assert isinstance(result, SourcesConfig)
        assert len(result.git) == 1
        assert "repo1" in result.git
        assert "repo2" not in result.git
        assert len(result.confluence) == 0

    def test_filter_by_source_name_case_sensitive(self, sample_sources_config):
        """Test that source name filtering is case sensitive."""
        filter_obj = SourceFilter()

        result = filter_obj.filter_sources(sample_sources_config, source="REPO1")

        # Should return empty since source names are case sensitive
        assert isinstance(result, SourcesConfig)
        assert len(result.git) == 0

    def test_filter_by_source_name_nonexistent(self, sample_sources_config):
        """Test filtering by nonexistent source name."""
        filter_obj = SourceFilter()

        result = filter_obj.filter_sources(sample_sources_config, source="nonexistent")

        assert isinstance(result, SourcesConfig)
        assert len(result.git) == 0
        assert len(result.confluence) == 0
        assert len(result.jira) == 0
        assert len(result.localfile) == 0

    def test_filter_by_both_source_type_and_name(self, sample_sources_config):
        """Test filtering by both source type and source name."""
        filter_obj = SourceFilter()

        result = filter_obj.filter_sources(
            sample_sources_config, source_type="git", source="repo1"
        )

        assert isinstance(result, SourcesConfig)
        assert len(result.git) == 1
        assert "repo1" in result.git
        assert len(result.confluence) == 0

    def test_filter_by_conflicting_type_and_name(self, sample_sources_config):
        """Test filtering with conflicting source type and name."""
        filter_obj = SourceFilter()

        # Try to filter for confluence type but git source name
        result = filter_obj.filter_sources(
            sample_sources_config, source_type="confluence", source="repo1"
        )

        # Should return empty since repo1 is not a confluence source
        assert isinstance(result, SourcesConfig)
        assert len(result.git) == 0
        assert len(result.confluence) == 0

    def test_filter_empty_sources_config(self):
        """Test filtering an empty SourcesConfig."""
        filter_obj = SourceFilter()
        empty_config = SourcesConfig()

        result = filter_obj.filter_sources(empty_config, source_type="git")

        assert isinstance(result, SourcesConfig)
        assert len(result.git) == 0
        assert len(result.confluence) == 0

    def test_filter_preserves_source_objects(self, sample_sources_config):
        """Test that filtering preserves the actual source objects."""
        filter_obj = SourceFilter()

        result = filter_obj.filter_sources(sample_sources_config, source_type="git")

        # Check that the actual source objects are preserved
        assert result.git["repo1"] is sample_sources_config.git["repo1"]
        assert result.git["repo2"] is sample_sources_config.git["repo2"]

    def test_filter_creates_new_config_instance(self, sample_sources_config):
        """Test that filtering creates a new SourcesConfig instance."""
        filter_obj = SourceFilter()

        result = filter_obj.filter_sources(sample_sources_config, source_type="git")

        # Should be a different instance
        assert result is not sample_sources_config
        assert isinstance(result, SourcesConfig)

    def test_filter_multiple_source_types_sequentially(self, sample_sources_config):
        """Test applying multiple filters sequentially."""
        filter_obj = SourceFilter()

        # First filter by git
        git_result = filter_obj.filter_sources(sample_sources_config, source_type="git")
        assert len(git_result.git) == 2

        # Then filter the result by specific source name
        final_result = filter_obj.filter_sources(git_result, source="repo1")
        assert len(final_result.git) == 1
        assert "repo1" in final_result.git

    def test_filter_with_none_values(self, sample_sources_config):
        """Test filtering with None values for parameters."""
        filter_obj = SourceFilter()

        result = filter_obj.filter_sources(
            sample_sources_config, source_type=None, source=None
        )

        # Should return original config when filters are None
        assert result == sample_sources_config

    def test_filter_with_empty_string_values(self, sample_sources_config):
        """Test filtering with empty string values for parameters."""
        filter_obj = SourceFilter()

        result = filter_obj.filter_sources(
            sample_sources_config, source_type="", source=""
        )

        # Should return original config for empty string filters (same as None)
        assert result == sample_sources_config
        assert len(result.git) == 2
        assert len(result.confluence) == 1

    def test_filter_all_source_types(self, sample_sources_config):
        """Test filtering each source type individually."""
        filter_obj = SourceFilter()

        source_types = ["git", "confluence", "jira", "localfile", "publicdocs"]
        expected_counts = [2, 1, 1, 1, 0]  # Expected count for each type

        for source_type, expected_count in zip(source_types, expected_counts, strict=False):
            result = filter_obj.filter_sources(
                sample_sources_config, source_type=source_type
            )
            actual_count = len(getattr(result, source_type))
            assert (
                actual_count == expected_count
            ), f"Failed for {source_type}: expected {expected_count}, got {actual_count}"

    def test_filter_performance_with_large_config(self):
        """Test filtering performance with a large number of sources."""
        filter_obj = SourceFilter()
        large_config = SourcesConfig()

        # Create a large number of git sources
        git_sources = {}
        for i in range(1000):
            source = MagicMock(spec=SourceConfig)
            source.source_type = "git"
            source.source = f"repo{i}"
            source.name = f"repo{i}"
            git_sources[f"repo{i}"] = source

        large_config.git = git_sources

        # Filter should complete quickly
        result = filter_obj.filter_sources(large_config, source_type="git")
        assert len(result.git) == 1000

        # Filter by specific name should also be quick
        result = filter_obj.filter_sources(large_config, source="repo500")
        assert len(result.git) == 1
        assert "repo500" in result.git
