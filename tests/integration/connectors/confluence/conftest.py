"""Test configuration for Confluence integration tests."""

import pytest
from pydantic import HttpUrl

from qdrant_loader.connectors.confluence import ConfluenceConnector
from qdrant_loader.connectors.confluence.config import ConfluenceSpaceConfig


@pytest.fixture
def confluence_config(test_settings):
    """Create a ConfluenceConfig instance from test settings."""
    confluence_settings = test_settings.sources_config.confluence["test-space"]
    return ConfluenceSpaceConfig(
        source_type=confluence_settings.source_type,
        source_name=confluence_settings.source_name,
        base_url=HttpUrl(confluence_settings.base_url),
        space_key=confluence_settings.space_key,
        content_types=confluence_settings.content_types,
        include_labels=confluence_settings.include_labels,
        exclude_labels=confluence_settings.exclude_labels,
        token=confluence_settings.token,
        email=confluence_settings.email,
    )


@pytest.fixture
def confluence_connector(confluence_config):
    """Create a ConfluenceConnector instance."""
    return ConfluenceConnector(confluence_config)
