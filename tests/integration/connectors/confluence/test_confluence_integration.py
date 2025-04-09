"""
Tests for the Confluence integration.
"""
import os
from datetime import datetime
from pathlib import Path
import pytest
from qdrant_loader.connectors.confluence import ConfluenceConnector
from qdrant_loader.config import ConfluenceSpaceConfig, Settings, initialize_config
from qdrant_loader.core.document import Document
from dotenv import load_dotenv
import yaml
from unittest.mock import patch, MagicMock
import requests
from requests.auth import HTTPBasicAuth
import logging

# Configure logging for tests
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

# Load test environment variables
load_dotenv(Path(__file__).parent.parent.parent / ".env.test")

@pytest.fixture(scope="session")
def test_settings():
    """Load test settings from environment variables and config file."""
    try:
        # Log environment variables (excluding sensitive data)
        env_vars = {
            'CONFLUENCE_URL': os.getenv('CONFLUENCE_URL'),
            'CONFLUENCE_SPACE_KEY': os.getenv('CONFLUENCE_SPACE_KEY'),
            'CONFLUENCE_EMAIL': os.getenv('CONFLUENCE_EMAIL'),
            'CONFLUENCE_TOKEN': 'REDACTED' if os.getenv('CONFLUENCE_TOKEN') else None
        }
        logger.debug("Environment variables: %s", env_vars)

        # Load settings from YAML
        config_path = Path(__file__).parent.parent.parent.parent / "config.test.yaml"
        logger.debug("Loading config from: %s", config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found at {config_path}")
            
        try:
            with open(config_path) as f:
                config_data = yaml.safe_load(f)
                logger.debug("Loaded YAML data: %s", {k: '...' for k in config_data.keys()})
        except yaml.YAMLError as e:
            logger.error("Failed to parse YAML file: %s", e)
            raise
            
        try:
            initialize_config(config_path)
            settings = Settings.from_yaml(config_path)
            logger.debug("Successfully initialized settings")
            return settings
        except Exception as e:
            logger.error("Failed to initialize settings: %s", e)
            raise
            
    except Exception as e:
        logger.error("Failed to load test settings: %s", e)
        raise

@pytest.fixture(scope="function")
def confluence_config(test_settings):
    """Create a ConfluenceConfig instance with test settings."""
    # Get the first Confluence space config from the test settings
    space_key = next(iter(test_settings.sources_config.confluence.keys()))
    return test_settings.sources_config.confluence[space_key]

@pytest.fixture(scope="function")
def confluence_connector(confluence_config):
    """Create a ConfluenceConnector instance for testing."""
    return ConfluenceConnector(confluence_config)

@pytest.mark.integration
def test_connector_initialization(confluence_config):
    """Test that the connector initializes correctly with real configuration."""
    connector = ConfluenceConnector(confluence_config)
    assert connector.config == confluence_config
    assert connector.base_url == confluence_config.url
    assert connector.token == os.getenv("CONFLUENCE_TOKEN")
    assert connector.email == os.getenv("CONFLUENCE_EMAIL")
    assert connector.session.auth.username == os.getenv("CONFLUENCE_EMAIL")
    assert connector.session.auth.password == os.getenv("CONFLUENCE_TOKEN")

@pytest.mark.integration
def test_missing_token_environment_variable(confluence_config):
    """Test that the connector raises an error when CONFLUENCE_TOKEN is missing."""
    with pytest.raises(ValueError, match="CONFLUENCE_TOKEN environment variable is not set"):
        with pytest.MonkeyPatch.context() as mp:
            mp.delenv("CONFLUENCE_TOKEN", raising=False)
            ConfluenceConnector(confluence_config)

@pytest.mark.integration
def test_missing_email_environment_variable(confluence_config):
    """Test that the connector raises an error when CONFLUENCE_EMAIL is missing."""
    with pytest.raises(ValueError, match="CONFLUENCE_EMAIL environment variable is not set"):
        with pytest.MonkeyPatch.context() as mp:
            mp.delenv("CONFLUENCE_EMAIL", raising=False)
            ConfluenceConnector(confluence_config)

@pytest.mark.integration
def test_make_request(confluence_connector):
    """Test that the connector makes authenticated requests correctly."""
    # Test with a simple endpoint that should always exist
    response = confluence_connector._make_request("GET", "space")
    assert isinstance(response, dict)
    assert "results" in response

@pytest.mark.integration
def test_get_space_content(confluence_connector):
    """Test fetching content from a real Confluence space."""
    response = confluence_connector._get_space_content()
    assert isinstance(response, dict)
    assert "results" in response
    
    # Verify the response structure
    if response["results"]:
        content = response["results"][0]
        assert "id" in content
        assert "type" in content
        assert "title" in content
        assert "body" in content
        assert "space" in content
        assert "version" in content

@pytest.mark.integration
def test_should_process_content(confluence_connector):
    """Test content filtering based on labels with real content."""
    # Get some real content from the space
    response = confluence_connector._get_space_content()
    if not response["results"]:
        pytest.skip("No content available in the test space")
    
    content = response["results"][0]
    
    # Test with original config
    should_process = confluence_connector._should_process_content(content)
    assert isinstance(should_process, bool)
    
    # Test with modified config (no label requirements)
    confluence_connector.config.include_labels = []
    confluence_connector.config.exclude_labels = []
    assert confluence_connector._should_process_content(content) is True

@pytest.mark.integration
def test_get_documents(confluence_connector):
    """Test fetching and processing documents from real Confluence space."""
    # Get only one page of content
    response = confluence_connector._get_space_content(limit=1)
    assert isinstance(response, dict)
    assert "results" in response
    
    if not response["results"]:
        pytest.skip("No documents found in the test space")
    
    # Process the first document
    content = response["results"][0]
    if confluence_connector._should_process_content(content):
        doc = confluence_connector._process_content(content)
        assert isinstance(doc, Document)
        assert doc.content  # Should have content
        assert doc.metadata["id"]  # Should have an ID
        assert doc.metadata["title"]  # Should have a title
        assert doc.metadata["space"]  # Should have a space key
        assert doc.metadata["version"]  # Should have a version number
        assert "labels" in doc.metadata  # Should have labels (even if empty)
        assert doc.source == f"{confluence_connector.base_url}/spaces/{doc.metadata['space']}/pages/{doc.metadata['id']}"  # Should have correct source URL
        assert doc.source_type == "confluence"  # Should have correct source type

@pytest.mark.integration
def test_error_handling(confluence_config):
    """Test error handling with invalid Confluence configuration."""
    invalid_config = ConfluenceSpaceConfig(
        url="https://invalid.atlassian.net/wiki",
        space_key="INVALID",
        content_types=confluence_config.content_types,
        include_labels=confluence_config.include_labels,
        exclude_labels=confluence_config.exclude_labels,
        token=confluence_config.token,
        email=confluence_config.email
    )
    
    with pytest.raises(Exception):
        connector = ConfluenceConnector(invalid_config)
        connector.get_documents()

@pytest.mark.integration
def test_pagination(confluence_connector):
    """Test pagination with real Confluence API."""
    # Test with very small page sizes to verify pagination
    page_size_1 = 1
    page_size_2 = 2

    # Get documents with page size 1
    documents_1 = []
    response = confluence_connector._get_space_content(start=0, limit=page_size_1)
    results = response.get("results", [])
    if not results:
        pytest.skip("No documents found in the test space")
    for content in results:
        if confluence_connector._should_process_content(content):
            doc = confluence_connector._process_content(content)
            if doc:
                documents_1.append(doc)

    # Get documents with page size 2
    documents_2 = []
    response = confluence_connector._get_space_content(start=0, limit=page_size_2)
    results = response.get("results", [])
    if not results:
        pytest.skip("No documents found in the test space")
    for content in results:
        if confluence_connector._should_process_content(content):
            doc = confluence_connector._process_content(content)
            if doc:
                documents_2.append(doc)

    # Get document IDs from both batches
    doc_ids_1 = [doc.metadata["id"] for doc in documents_1]
    doc_ids_2 = [doc.metadata["id"] for doc in documents_2]

    # Compare the first document ID from each batch
    # They should be the same since we're starting from the same position
    assert doc_ids_1[0] == doc_ids_2[0], "First document ID should be the same regardless of page size"

@pytest.mark.integration
def test_content_processing(confluence_connector):
    """Test processing of real Confluence content."""
    # Get some real content
    response = confluence_connector._get_space_content()
    if not response["results"]:
        pytest.skip("No content available in the test space")
    
    content = response["results"][0]
    document = confluence_connector._process_content(content)
    
    # Verify document structure
    assert isinstance(document, Document)
    assert document.content  # Should have content
    assert document.metadata["id"] == content["id"]
    assert document.metadata["title"] == content["title"]
    assert document.metadata["space"] == content["space"]["key"]
    assert document.metadata["version"] == content["version"]["number"]
    assert isinstance(document.metadata["labels"], list)
    assert document.source_type == "confluence" 