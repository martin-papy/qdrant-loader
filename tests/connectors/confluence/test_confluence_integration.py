import pytest
from unittest.mock import Mock, patch
import os
import responses
import json
from datetime import datetime
from qdrant_loader.connectors.confluence import ConfluenceConnector
from qdrant_loader.config import ConfluenceConfig
from qdrant_loader.core.document import Document

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
def mock_confluence_responses():
    """Fixture to set up mock Confluence API responses."""
    with responses.RequestsMock() as rsps:
        def request_callback(request):
            params = request.params
            content_types = params.get("type", "").split(",")
            
            # Base content
            all_content = [
                {
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
                    },
                    "history": {
                        "createdBy": {
                            "displayName": "Test User"
                        },
                        "createdDate": "2024-03-06T12:00:00Z"
                    },
                    "space": {
                        "name": "Test Space",
                        "type": "global"
                    },
                    "extensions": {
                        "position": {
                            "parentId": "123455",
                            "position": 1
                        }
                    }
                },
                {
                    "id": "123457",
                    "type": "blogpost",
                    "title": "Test Blog",
                    "body": {
                        "storage": {
                            "value": "<p>Blog content</p>"
                        }
                    },
                    "version": {
                        "number": 1,
                        "when": "2024-03-07T13:00:00Z"
                    },
                    "metadata": {
                        "labels": {
                            "results": [
                                {"name": "documentation"},
                                {"name": "blog"}
                            ]
                        }
                    },
                    "history": {
                        "createdBy": {
                            "displayName": "Blog Author"
                        },
                        "createdDate": "2024-03-07T13:00:00Z"
                    },
                    "space": {
                        "name": "Test Space",
                        "type": "global"
                    }
                }
            ]
            
            # Filter content based on content types
            filtered_content = [
                content for content in all_content
                if content["type"] in content_types
            ]
            
            return (200, {"Content-Type": "application/json"}, json.dumps({"results": filtered_content}))
        
        # Add the callback for content endpoint
        rsps.add_callback(
            responses.GET,
            "https://example.atlassian.net/wiki/rest/api/content",
            callback=request_callback,
            content_type="application/json",
        )
        
        yield rsps

@pytest.mark.integration
def test_get_documents_integration(mock_config, mock_env_vars, mock_confluence_responses):
    """Test fetching documents from Confluence with realistic API responses."""
    connector = ConfluenceConnector(mock_config)
    documents = connector.get_documents()
    
    assert len(documents) == 2
    
    # Verify first document (page)
    page = documents[0]
    assert isinstance(page, Document)
    assert page.content == "<p>Test content</p>"
    assert page.metadata["id"] == "123456"
    assert page.metadata["type"] == "page"
    assert page.metadata["title"] == "Test Page"
    assert page.metadata["space_key"] == "TEST"
    assert page.metadata["version"] == 1
    assert page.metadata["last_modified"] == "2024-03-07T12:00:00Z"
    assert page.metadata["labels"] == ["documentation", "test"]
    assert page.metadata["author"] == "Test User"
    assert page.metadata["created_date"] == "2024-03-06T12:00:00Z"
    assert page.metadata["space_name"] == "Test Space"
    assert page.metadata["space_type"] == "global"
    assert page.metadata["parent_id"] == "123455"
    assert page.metadata["position"] == 1
    
    # Verify second document (blogpost)
    blog = documents[1]
    assert isinstance(blog, Document)
    assert blog.content == "<p>Blog content</p>"
    assert blog.metadata["id"] == "123457"
    assert blog.metadata["type"] == "blogpost"
    assert blog.metadata["title"] == "Test Blog"
    assert blog.metadata["labels"] == ["documentation", "blog"]
    assert blog.metadata["author"] == "Blog Author"
    assert "parent_id" not in blog.metadata
    assert "position" not in blog.metadata

@pytest.mark.integration
def test_label_filtering_integration(mock_config, mock_env_vars, mock_confluence_responses):
    """Test content filtering based on labels in a realistic scenario."""
    # Update config to only include content with 'blog' label
    mock_config.include_labels = ["blog"]
    
    connector = ConfluenceConnector(mock_config)
    documents = connector.get_documents()
    
    assert len(documents) == 1
    assert documents[0].metadata["id"] == "123457"
    assert "blog" in documents[0].metadata["labels"]

@pytest.mark.integration
def test_content_type_filtering_integration(mock_config, mock_env_vars, mock_confluence_responses):
    """Test content filtering based on content types in a realistic scenario."""
    # Update config to only include pages
    mock_config.content_types = ["page"]
    
    connector = ConfluenceConnector(mock_config)
    documents = connector.get_documents()
    
    assert len(documents) == 1
    assert documents[0].metadata["type"] == "page"
    assert documents[0].metadata["id"] == "123456"

@pytest.mark.integration
@responses.activate
def test_error_handling_integration(mock_config, mock_env_vars):
    """Test error handling in a realistic scenario."""
    # Mock a server error response
    responses.add(
        responses.GET,
        "https://example.atlassian.net/wiki/rest/api/content",
        json={"message": "Internal Server Error"},
        status=500
    )
    
    connector = ConfluenceConnector(mock_config)
    with pytest.raises(Exception) as exc_info:
        connector.get_documents()
    assert "500" in str(exc_info.value)

@pytest.mark.integration
@responses.activate
def test_pagination_integration(mock_config, mock_env_vars):
    """Test pagination handling in a realistic scenario."""
    def request_callback(request):
        params = request.params
        start = int(params.get("start", "0"))
        
        if start == 0:
            response = {
                "results": [{
                    "id": "1",
                    "type": "page",
                    "title": "Page 1",
                    "body": {"storage": {"value": "Content 1"}},
                    "version": {"number": 1, "when": "2024-03-07T12:00:00Z"},
                    "metadata": {"labels": {"results": [{"name": "documentation"}]}},
                    "history": {
                        "createdBy": {"displayName": "Test User"},
                        "createdDate": "2024-03-07T12:00:00Z"
                    },
                    "space": {"name": "Test Space", "type": "global"}
                }],
                "size": 1,
                "_links": {"next": "/rest/api/content?start=1"}
            }
        else:
            response = {
                "results": [{
                    "id": "2",
                    "type": "page",
                    "title": "Page 2",
                    "body": {"storage": {"value": "Content 2"}},
                    "version": {"number": 1, "when": "2024-03-07T12:00:00Z"},
                    "metadata": {"labels": {"results": [{"name": "documentation"}]}},
                    "history": {
                        "createdBy": {"displayName": "Test User"},
                        "createdDate": "2024-03-07T12:00:00Z"
                    },
                    "space": {"name": "Test Space", "type": "global"}
                }],
                "size": 1
            }
        
        return (200, {"Content-Type": "application/json"}, json.dumps(response))
    
    # Add the callback for content endpoint
    responses.add_callback(
        responses.GET,
        "https://example.atlassian.net/wiki/rest/api/content",
        callback=request_callback,
        content_type="application/json",
    )
    
    connector = ConfluenceConnector(mock_config)
    documents = connector.get_documents()
    
    assert len(documents) == 2
    assert documents[0].metadata["id"] == "1"
    assert documents[1].metadata["id"] == "2" 