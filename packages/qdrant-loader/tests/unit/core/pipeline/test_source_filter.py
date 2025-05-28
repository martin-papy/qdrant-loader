"""Tests for SourceFilter."""


from qdrant_loader.config import SourcesConfig
from qdrant_loader.core.pipeline.source_filter import SourceFilter


class TestSourceFilter:
    """Test cases for SourceFilter."""

    def test_no_filters_returns_original(self):
        """Test that no filters returns the original config."""
        filter_obj = SourceFilter()
        original_config = SourcesConfig()

        result = filter_obj.filter_sources(original_config)

        assert result == original_config

    def test_filter_by_source_type_git(self):
        """Test filtering by git source type."""
        filter_obj = SourceFilter()
        config = SourcesConfig()

        result = filter_obj.filter_sources(config, source_type="git")

        # Should return a new SourcesConfig with empty collections
        assert isinstance(result, SourcesConfig)
        assert len(result.git) == 0
        assert len(result.confluence) == 0

    def test_filter_by_source_type_case_insensitive(self):
        """Test that source type filtering is case insensitive."""
        filter_obj = SourceFilter()
        config = SourcesConfig()

        result = filter_obj.filter_sources(config, source_type="GIT")

        assert isinstance(result, SourcesConfig)
        assert len(result.git) == 0

    def test_filter_nonexistent_source_type(self):
        """Test filtering by nonexistent source type returns empty config."""
        filter_obj = SourceFilter()
        config = SourcesConfig()

        result = filter_obj.filter_sources(config, source_type="nonexistent")

        assert isinstance(result, SourcesConfig)
        assert len(result.git) == 0
        assert len(result.confluence) == 0
        assert len(result.jira) == 0
        assert len(result.publicdocs) == 0
        assert len(result.localfile) == 0
