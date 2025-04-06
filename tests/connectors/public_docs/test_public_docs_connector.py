import pytest
from unittest.mock import Mock, patch
from bs4 import BeautifulSoup
from qdrant_loader.connectors.public_docs import PublicDocsConnector
from qdrant_loader.config import PublicDocsSourceConfig, SelectorsConfig

@pytest.fixture
def mock_config():
    return PublicDocsSourceConfig(
        base_url="https://docs.example.com",
        version="1.0",
        content_type="html",
        selectors=SelectorsConfig()
    )

@pytest.fixture
def mock_html():
    return """
    <html>
        <head><title>Test Page</title></head>
        <body>
            <nav>Navigation</nav>
            <article class="main-content">
                <h1>Main Content</h1>
                <p>This is the main content.</p>
                <pre><code>print("Hello World")</code></pre>
            </article>
            <footer>Footer</footer>
            <a href="/page1">Page 1</a>
            <a href="/page2">Page 2</a>
            <a href="https://external.com">External</a>
        </body>
    </html>
    """

def test_should_process_url(mock_config):
    connector = PublicDocsConnector(mock_config)
    
    # Test base URL
    assert connector._should_process_url("https://docs.example.com/page") is True
    
    # Test excluded path
    mock_config.exclude_paths = ["/page1"]
    assert connector._should_process_url("https://docs.example.com/page1") is False
    
    # Test path pattern
    mock_config.path_pattern = "/docs/{version}/.*"
    assert connector._should_process_url("https://docs.example.com/docs/1.0/page") is True
    assert connector._should_process_url("https://docs.example.com/other/page") is False
    
    # Test external URL
    assert connector._should_process_url("https://other.com/page") is False

def test_extract_links(mock_config, mock_html):
    connector = PublicDocsConnector(mock_config)
    links = connector._extract_links(mock_html, "https://docs.example.com")
    
    assert len(links) == 2
    assert "https://docs.example.com/page1" in links
    assert "https://docs.example.com/page2" in links
    assert "https://external.com" not in links

def test_extract_content(mock_config, mock_html):
    connector = PublicDocsConnector(mock_config)
    content = connector._extract_content(mock_html)
    
    assert "Main Content" in content
    assert "Navigation" not in content
    assert "Footer" not in content
    assert "```" in content
    assert "print(\"Hello World\")" in content

@patch("requests.Session")
def test_process_page(mock_session, mock_config, mock_html):
    # Setup mock response
    mock_response = Mock()
    mock_response.text = mock_html
    mock_response.raise_for_status.return_value = None
    mock_session.return_value.get.return_value = mock_response
    
    connector = PublicDocsConnector(mock_config)
    content = connector._process_page("https://docs.example.com/page")
    
    assert content is not None
    assert "Main Content" in content
    assert "Navigation" not in content
    assert len(connector.url_queue) == 2  # Two internal links were found

@patch("requests.Session")
def test_get_documentation(mock_session, mock_config):
    # Setup mock responses for a simple site structure
    mock_responses = {
        "https://docs.example.com": Mock(
            text="""
            <html>
                <body>
                    <article class="main-content">Home Page</article>
                    <a href="/page1">Page 1</a>
                </body>
            </html>
            """,
            raise_for_status=lambda: None
        ),
        "https://docs.example.com/page1": Mock(
            text="""
            <html>
                <body>
                    <article class="main-content">Page 1 Content</article>
                </body>
            </html>
            """,
            raise_for_status=lambda: None
        )
    }
    
    def mock_get(url, *args, **kwargs):
        return mock_responses[url]
    
    mock_session.return_value.get.side_effect = mock_get
    
    connector = PublicDocsConnector(mock_config)
    content = connector.get_documentation()
    
    assert len(content) == 2
    assert "Home Page" in content[0]
    assert "Page 1 Content" in content[1]
    assert len(connector.visited_urls) == 2 