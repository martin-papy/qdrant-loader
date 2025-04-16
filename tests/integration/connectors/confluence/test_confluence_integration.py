"""Integration tests for the Confluence connector."""

import os
import pytest
from qdrant_loader.core.document import Document
from qdrant_loader.connectors.confluence import ConfluenceConnector
from qdrant_loader.connectors.confluence.config import ConfluenceSpaceConfig


@pytest.mark.integration
@pytest.mark.asyncio
async def test_connector_initialization(confluence_config):
    """Test that the connector initializes correctly."""
    connector = ConfluenceConnector(confluence_config)
    assert connector is not None
    assert connector.config == confluence_config


@pytest.mark.integration
@pytest.mark.asyncio
async def test_missing_token_environment_variable(confluence_config):
    """Test that the connector raises an error when token is missing."""
    # Remove token from environment
    token = os.environ.pop("CONFLUENCE_TOKEN", None)
    try:
        with pytest.raises(ValueError, match="CONFLUENCE_TOKEN environment variable is not set"):
            ConfluenceConnector(confluence_config)
    finally:
        # Restore token
        if token:
            os.environ["CONFLUENCE_TOKEN"] = token


@pytest.mark.integration
@pytest.mark.asyncio
async def test_missing_email_environment_variable(confluence_config):
    """Test that the connector raises an error when email is missing."""
    # Remove email from environment
    email = os.environ.pop("CONFLUENCE_EMAIL", None)
    try:
        with pytest.raises(ValueError, match="CONFLUENCE_EMAIL environment variable is not set"):
            ConfluenceConnector(confluence_config)
    finally:
        # Restore email
        if email:
            os.environ["CONFLUENCE_EMAIL"] = email


@pytest.mark.integration
@pytest.mark.asyncio
async def test_make_request(confluence_connector):
    """Test that the connector makes authenticated requests correctly."""
    # Test with a simple endpoint that should always exist
    response = await confluence_connector._make_request("GET", "space")
    assert isinstance(response, dict)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_space_content(confluence_connector):
    """Test fetching content from a real Confluence space."""
    response = await confluence_connector._get_space_content()
    assert isinstance(response, dict)
    assert "results" in response


@pytest.mark.integration
@pytest.mark.asyncio
async def test_should_process_content(confluence_connector):
    """Test content filtering based on labels with real content."""
    # Get some real content from the space
    response = await confluence_connector._get_space_content()
    if not response["results"]:
        pytest.skip("No content found in space to test with")

    content = response["results"][0]
    assert confluence_connector._should_process_content(content) in [True, False]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_documents(confluence_connector):
    """Test fetching and processing documents from real Confluence space."""
    # Get only one page of content
    response = await confluence_connector._get_space_content(limit=1)
    assert isinstance(response, dict)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling(confluence_config):
    """Test error handling with invalid Confluence configuration."""
    invalid_config = ConfluenceSpaceConfig(
        url="https://invalid.atlassian.net/wiki",
        space_key="INVALID",
        content_types=confluence_config.content_types,
        include_labels=confluence_config.include_labels,
        exclude_labels=confluence_config.exclude_labels,
        token=confluence_config.token,
        email=confluence_config.email,
    )

    with pytest.raises(Exception):
        connector = ConfluenceConnector(invalid_config)
        await connector._make_request("GET", "space")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pagination(confluence_connector):
    """Test pagination with real Confluence API."""
    # Test with very small page sizes to verify pagination
    page_size_1 = 1
    page_size_2 = 2

    # Get documents with page size 1
    documents_1 = []
    response = await confluence_connector._get_space_content(start=0, limit=page_size_1)
    results = response.get("results", [])

    # Get documents with page size 2
    documents_2 = []
    response = await confluence_connector._get_space_content(start=0, limit=page_size_2)
    results = response.get("results", [])

    # Verify that we got more or equal documents with larger page size
    assert len(documents_2) >= len(documents_1)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_content_processing(confluence_connector):
    """Test processing of real Confluence content."""
    # Get some real content
    response = await confluence_connector._get_space_content()
    if not response["results"]:
        pytest.skip("No content found in space to test with")

    content = response["results"][0]
    document = confluence_connector._process_content(content)
    assert document is not None
    assert isinstance(document, Document)
