"""Unit tests for SharePoint integration in SourcesConfig and SourceFilter."""

import pytest
from unittest.mock import patch

from qdrant_loader.config.sources import SourcesConfig
from qdrant_loader.config.types import SourceType
from qdrant_loader.core.pipeline.source_filter import SourceFilter
from qdrant_loader.connectors.sharepoint.config import (
    SharePointConfig,
    SharePointAuthMethod,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sharepoint_config_dict():
    """Create SharePoint config as dict (as loaded from YAML).

    Note: source and source_type are injected by SourcesConfig._convert_source_configs
    based on the source name (dict key) and parent field name (e.g., 'sharepoint').
    """
    return {
        "source": "test-site",
        "source_type": "sharepoint",
        "base_url": "https://company.sharepoint.com",
        "site_url": "https://company.sharepoint.com/sites/test-site",
        "relative_url": "/sites/test-site",
        "auth_method": "client_credentials",
        "tenant_id": "12345678-1234-1234-1234-123456789012",
        "client_id": "client-app-id",
        "client_secret": "client-secret-value",
        "document_libraries": ["Documents"],
        "file_types": ["pdf", "docx"],
    }


@pytest.fixture
def multiple_sharepoint_configs():
    """Create multiple SharePoint configs."""
    return {
        "site-a": {
            "source": "site-a",
            "source_type": "sharepoint",
            "base_url": "https://companya.sharepoint.com",
            "site_url": "https://companya.sharepoint.com/sites/site-a",
            "relative_url": "/sites/site-a",
            "tenant_id": "12345678-1234-1234-1234-123456789012",
            "client_id": "client-a",
            "client_secret": "secret-a",
        },
        "site-b": {
            "source": "site-b",
            "source_type": "sharepoint",
            "base_url": "https://companyb.sharepoint.com",
            "site_url": "https://companyb.sharepoint.com/sites/site-b",
            "relative_url": "/sites/site-b",
            "tenant_id": "12345678-1234-1234-1234-123456789013",
            "client_id": "client-b",
            "client_secret": "secret-b",
        },
    }


@pytest.fixture
def mixed_sources_config(sharepoint_config_dict):
    """Create SourcesConfig with multiple source types including SharePoint."""
    return SourcesConfig(
        git={
            "main-repo": {
                "source": "main-repo",
                "source_type": "git",
                "base_url": "https://github.com/org/repo.git",
                "branch": "main",
                "token": "test-token",
            }
        },
        sharepoint={
            "company-site": {
                **sharepoint_config_dict,
                "source": "company-site",  # Override source name
            },
        },
    )


# =============================================================================
# SourcesConfig Tests
# =============================================================================


class TestSourcesConfigSharePoint:
    """Test SharePoint in SourcesConfig."""

    def test_sources_config_accepts_sharepoint(self, sharepoint_config_dict):
        """Test that SourcesConfig accepts sharepoint sources."""
        config = SourcesConfig(sharepoint={"test-site": sharepoint_config_dict})

        assert "test-site" in config.sharepoint
        assert isinstance(config.sharepoint["test-site"], SharePointConfig)

    def test_sources_config_sharepoint_empty(self):
        """Test SourcesConfig with empty sharepoint."""
        config = SourcesConfig(sharepoint={})

        assert config.sharepoint == {}

    def test_sources_config_sharepoint_default(self):
        """Test SourcesConfig default sharepoint is empty dict."""
        config = SourcesConfig()

        assert config.sharepoint == {}

    def test_sources_config_multiple_sharepoint_sites(self, multiple_sharepoint_configs):
        """Test SourcesConfig with multiple SharePoint sites."""
        config = SourcesConfig(sharepoint=multiple_sharepoint_configs)

        assert len(config.sharepoint) == 2
        assert "site-a" in config.sharepoint
        assert "site-b" in config.sharepoint

    def test_sources_config_validates_sharepoint_config(self):
        """Test that invalid SharePoint config raises validation error."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SourcesConfig(
                sharepoint={
                    "invalid-site": {
                        "base_url": "https://company.sharepoint.com",
                        # Missing required fields
                    }
                }
            )

    def test_sources_config_to_dict_includes_sharepoint(self, sharepoint_config_dict):
        """Test to_dict includes sharepoint sources."""
        config = SourcesConfig(sharepoint={"test-site": sharepoint_config_dict})

        result = config.to_dict()

        assert SourceType.SHAREPOINT in result
        assert "test-site" in result[SourceType.SHAREPOINT]

    def test_sources_config_get_source_config_sharepoint(self, sharepoint_config_dict):
        """Test get_source_config returns SharePoint config."""
        config = SourcesConfig(sharepoint={"test-site": sharepoint_config_dict})

        source = config.get_source_config("sharepoint", "test-site")

        assert source is not None
        assert isinstance(source, SharePointConfig)
        assert source.source == "test-site"


# =============================================================================
# SourceFilter Tests
# =============================================================================


class TestSourceFilterSharePoint:
    """Test SharePoint in SourceFilter."""

    def test_filter_by_sharepoint_type(self, sharepoint_config_dict):
        """Test filtering by sharepoint source type."""
        sources_config = SourcesConfig(
            sharepoint={"test-site": sharepoint_config_dict},
            git={
                "repo": {
                    "source": "repo",
                    "source_type": "git",
                    "base_url": "https://github.com/org/repo.git",
                    "branch": "main",
                    "token": "test-token",
                }
            },
        )

        filter = SourceFilter()
        result = filter.filter_sources(sources_config, source_type="sharepoint")

        assert len(result.sharepoint) == 1
        assert "test-site" in result.sharepoint
        assert len(result.git) == 0

    def test_filter_by_specific_sharepoint_source(self, multiple_sharepoint_configs):
        """Test filtering by specific SharePoint source name."""
        sources_config = SourcesConfig(sharepoint=multiple_sharepoint_configs)

        filter = SourceFilter()
        result = filter.filter_sources(
            sources_config, source_type="sharepoint", source="site-a"
        )

        assert len(result.sharepoint) == 1
        assert "site-a" in result.sharepoint
        assert "site-b" not in result.sharepoint

    def test_filter_no_type_includes_sharepoint(self, mixed_sources_config):
        """Test that filtering without type includes SharePoint sources."""
        filter = SourceFilter()
        result = filter.filter_sources(mixed_sources_config, source_type=None)

        # Should return original config with all sources
        assert result == mixed_sources_config
        assert len(result.sharepoint) == 1
        assert len(result.git) == 1

    def test_filter_by_name_across_types(self, mixed_sources_config):
        """Test filtering by name across all source types."""
        filter = SourceFilter()
        result = filter.filter_sources(
            mixed_sources_config, source_type=None, source="company-site"
        )

        assert len(result.sharepoint) == 1
        assert len(result.git) == 0  # main-repo doesn't match

    def test_filter_sharepoint_no_match(self, sharepoint_config_dict):
        """Test filtering SharePoint with no matching source."""
        sources_config = SourcesConfig(sharepoint={"test-site": sharepoint_config_dict})

        filter = SourceFilter()
        result = filter.filter_sources(
            sources_config, source_type="sharepoint", source="nonexistent"
        )

        assert len(result.sharepoint) == 0

    def test_filter_other_type_excludes_sharepoint(self, mixed_sources_config):
        """Test that filtering by other type excludes SharePoint."""
        filter = SourceFilter()
        result = filter.filter_sources(mixed_sources_config, source_type="git")

        assert len(result.git) == 1
        assert len(result.sharepoint) == 0


# =============================================================================
# SourceType Enum Tests
# =============================================================================


class TestSourceTypeSharePoint:
    """Test SharePoint in SourceType enum."""

    def test_sharepoint_in_source_type(self):
        """Test SHAREPOINT is in SourceType enum."""
        assert hasattr(SourceType, "SHAREPOINT")
        assert SourceType.SHAREPOINT.value == "sharepoint"

    def test_sharepoint_enum_comparison(self):
        """Test SourceType.SHAREPOINT comparison."""
        assert SourceType.SHAREPOINT == "sharepoint"
        assert SourceType.SHAREPOINT != SourceType.GIT


# =============================================================================
# Integration Tests
# =============================================================================


class TestSharePointSourcesIntegration:
    """Integration tests for SharePoint sources configuration."""

    def test_full_sources_config_with_all_types(self, sharepoint_config_dict):
        """Test SourcesConfig with all source types including SharePoint."""
        config = SourcesConfig(
            publicdocs={
                "docs": {
                    "source": "docs",
                    "source_type": "publicdocs",
                    "base_url": "https://docs.example.com",
                    "version": "1.0",
                    "content_type": "html",
                }
            },
            git={
                "repo": {
                    "source": "repo",
                    "source_type": "git",
                    "base_url": "https://github.com/org/repo.git",
                    "branch": "main",
                    "token": "test-token",
                }
            },
            confluence={},
            jira={},
            localfile={},
            sharepoint={
                "site": {
                    **sharepoint_config_dict,
                    "source": "site",
                }
            },
        )

        assert len(config.publicdocs) == 1
        assert len(config.git) == 1
        assert len(config.sharepoint) == 1
        assert len(config.confluence) == 0
        assert len(config.jira) == 0
        assert len(config.localfile) == 0

    def test_sources_config_converts_dict_to_sharepoint_config(
        self, sharepoint_config_dict
    ):
        """Test that dict configs are converted to SharePointConfig objects."""
        # Override source to match the dict key
        test_config = {**sharepoint_config_dict, "source": "test"}
        config = SourcesConfig(sharepoint={"test": test_config})

        sp_config = config.sharepoint["test"]

        # Verify it's a SharePointConfig instance
        assert isinstance(sp_config, SharePointConfig)

        # Verify fields are correctly set
        assert sp_config.source == "test"
        assert sp_config.source_type == "sharepoint"
        assert str(sp_config.base_url).rstrip("/") == "https://company.sharepoint.com"
        assert sp_config.relative_url == "/sites/test-site"
        assert sp_config.auth_method == SharePointAuthMethod.CLIENT_CREDENTIALS
        assert sp_config.tenant_id == "12345678-1234-1234-1234-123456789012"
        assert sp_config.document_libraries == ["Documents"]
        assert sp_config.file_types == ["pdf", "docx"]
