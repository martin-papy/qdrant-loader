import pytest
from unittest.mock import Mock, patch
import os
from qdrant_loader.connectors.confluence import ConfluenceConnector
from qdrant_loader.config import ConfluenceConfig

@pytest.fixture
def mock_config():
    return ConfluenceConfig(
        url="https://example.atlassian.net/wiki",
        space_key="TEST",
        content_types=["page", "blogpost"],
        include_labels=["documentation"],
        exclude_labels=["draft"]
    )

@pytest.fixture
def mock_env_vars():
    with patch.dict(os.environ, {
        "CONFLUENCE_TOKEN": "test-token"
    }):
        yield

@pytest.fixture
def mock_content():
    return {
        "id": "123456",
        "type": "page",
        "title": "Test Page",
        "body": {
            "storage": {
                "value": "<p>Test content</p>"
            }
        },
        "version": {
            "number": 1,
            "when": "2024-03-07T12:00:00Z"
        },
        "metadata": {
            "labels": {
                "results": [
                    {"name": "documentation"},
                    {"name": "test"}
                ]
            }
        }
    }

def test_connector_initialization(mock_config, mock_env_vars):
    """Test that the connector initializes correctly with valid configuration."""
    connector = ConfluenceConnector(mock_config)
    assert connector.config == mock_config
    assert connector.base_url == "https://example.atlassian.net/wiki"
    assert connector.token == "test-token"
    assert connector.session.auth.username == ""
    assert connector.session.auth.password == "test-token"

def test_missing_token_environment_variable(mock_config):
    """Test that the connector raises an error when CONFLUENCE_TOKEN is missing."""
    with pytest.raises(ValueError, match="CONFLUENCE_TOKEN environment variable is not set"):
        ConfluenceConnector(mock_config)

@patch("requests.Session")
def test_make_request(mock_session, mock_config, mock_env_vars):
    """Test that the connector makes authenticated requests correctly."""
    # Setup mock response
    mock_response = Mock()
    mock_response.json.return_value = {"test": "data"}
    mock_response.raise_for_status.return_value = None
    
    # Create a mock session instance
    mock_session_instance = Mock()
    mock_session_instance.request.return_value = mock_response
    mock_session.return_value = mock_session_instance
    
    connector = ConfluenceConnector(mock_config)
    response = connector._make_request("GET", "test/endpoint")
    
    # Verify request was made with correct parameters
    mock_session_instance.request.assert_called_once_with(
        "GET",
        "https://example.atlassian.net/wiki/rest/api/test/endpoint",
        auth=connector.session.auth
    )
    assert response == {"test": "data"}

@patch("requests.Session")
def test_make_request_error_handling(mock_session, mock_config, mock_env_vars):
    """Test that the connector handles request errors correctly."""
    # Setup mock to raise an exception
    mock_session_instance = Mock()
    mock_session_instance.request.side_effect = Exception("Request failed")
    mock_session.return_value = mock_session_instance
    
    connector = ConfluenceConnector(mock_config)
    with pytest.raises(Exception, match="Request failed"):
        connector._make_request("GET", "test/endpoint")

@patch("requests.Session")
def test_get_space_content(mock_session, mock_config, mock_env_vars, mock_content):
    """Test fetching content from a Confluence space."""
    # Setup mock response
    mock_response = Mock()
    mock_response.json.return_value = {"results": [mock_content]}
    mock_response.raise_for_status.return_value = None
    
    # Create a mock session instance
    mock_session_instance = Mock()
    mock_session_instance.request.return_value = mock_response
    mock_session.return_value = mock_session_instance
    
    connector = ConfluenceConnector(mock_config)
    response = connector._get_space_content()
    
    # Verify request was made with correct parameters
    mock_session_instance.request.assert_called_once_with(
        "GET",
        "https://example.atlassian.net/wiki/rest/api/content",
        params={
            "spaceKey": "TEST",
            "expand": "body.storage,version,metadata.labels",
            "start": 0,
            "limit": 25,
            "type": "page,blogpost"
        },
        auth=connector.session.auth
    )
    assert response == {"results": [mock_content]}

def test_should_process_content(mock_config, mock_env_vars, mock_content):
    """Test content filtering based on labels."""
    connector = ConfluenceConnector(mock_config)
    
    # Test with matching include label
    assert connector._should_process_content(mock_content) is True
    
    # Test with exclude label
    mock_content_with_draft = mock_content.copy()
    mock_content_with_draft["metadata"] = {
        "labels": {
            "results": [
                {"name": "documentation"},
                {"name": "test"},
                {"name": "draft"}
            ]
        }
    }
    assert connector._should_process_content(mock_content_with_draft) is False
    
    # Test with no matching include label
    mock_content_no_docs = mock_content.copy()
    mock_content_no_docs["metadata"] = {
        "labels": {
            "results": [
                {"name": "test"}
            ]
        }
    }
    assert connector._should_process_content(mock_content_no_docs) is False
    
    # Test with no labels requirement
    connector.config.include_labels = []
    assert connector._should_process_content(mock_content_no_docs) is True

@patch("requests.Session")
def test_get_documents(mock_session, mock_config, mock_env_vars, mock_content):
    """Test fetching and processing documents from Confluence."""
    # Setup mock responses for pagination
    mock_responses = [
        {"results": [mock_content]},  # First page
        {"results": []}  # No more results
    ]
    
    # Create mock responses
    mock_response_objects = []
    for response in mock_responses:
        mock_response = Mock()
        mock_response.json.return_value = response
        mock_response.raise_for_status.return_value = None
        mock_response_objects.append(mock_response)
    
    # Create a mock session instance
    mock_session_instance = Mock()
    mock_session_instance.request.side_effect = mock_response_objects
    mock_session.return_value = mock_session_instance
    
    connector = ConfluenceConnector(mock_config)
    documents = connector.get_documents()
    
    assert len(documents) == 1
    document = documents[0]
    assert document.content == "<p>Test content</p>"
    assert document.metadata["id"] == "123456"
    assert document.metadata["title"] == "Test Page"
    assert document.metadata["space_key"] == "TEST"
    assert document.metadata["version"] == 1
    assert document.metadata["last_modified"] == "2024-03-07T12:00:00Z"
    assert document.metadata["labels"] == ["documentation", "test"] 