"""Integration tests for PublicDocs connector with real configuration."""

import os
import warnings
from pathlib import Path

import pytest
import yaml
from bs4 import XMLParsedAsHTMLWarning

from qdrant_loader.config.types import SourceType
from qdrant_loader.connectors.publicdocs.config import PublicDocsSourceConfig
from qdrant_loader.connectors.publicdocs.connector import PublicDocsConnector

# Suppress XMLParsedAsHTMLWarning
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


class TestPublicDocsIntegration:
    """Integration tests for PublicDocs connector."""

    @pytest.fixture
    def publicdocs_config(self):
        """Get the PublicDocs configuration from test config file."""
        # Load the test configuration directly from the file
        config_path = Path("tests/config.test.yaml")
        
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)
        
        # Get the publicdocs sources
        publicdocs_sources = config_data.get("sources", {}).get("publicdocs", {})
        
        # Use the first publicdocs source
        source_name = next(iter(publicdocs_sources.keys()), None)
        if not source_name:
            pytest.skip("No PublicDocs source configured in test settings")
        
        # Get the source configuration
        config_dict = publicdocs_sources[source_name]
        
        # Add required fields
        config_dict["source"] = source_name
        config_dict["source_type"] = SourceType.PUBLICDOCS
        
        # Create the configuration object
        return PublicDocsSourceConfig.model_validate(config_dict)

    @pytest.mark.asyncio
    async def test_document_crawling(self, publicdocs_config):
        """Test document crawling with real configuration."""
        # Create the connector with the real configuration
        async with PublicDocsConnector(publicdocs_config) as connector:
            # Get the documents from the real source
            documents = await connector.get_documents()
            
            # Verify that we got at least one document
            assert len(documents) > 0
            
            # Verify the document metadata
            for doc in documents:
                assert doc.metadata["version"] == publicdocs_config.version
                assert doc.source_type == publicdocs_config.source_type
                assert doc.source == publicdocs_config.source
                assert doc.url is not None
                assert doc.content is not None
                assert doc.title is not None

    @pytest.mark.asyncio
    async def test_content_extraction(self, publicdocs_config, test_data_dir):
        """Test content extraction with a real HTML document."""
        # Use the sample document from the fixtures
        sample_doc_path = os.path.join(
            test_data_dir, "unit", "publicdocs", "sample_document.html"
        )
        
        with open(sample_doc_path, "r") as f:
            html_content = f.read()
        
        # Create a modified configuration with a selector that matches the sample document
        modified_config = publicdocs_config.model_copy(deep=True)
        modified_config.selectors.content = ".body"
        
        # Create the connector with the modified configuration
        connector = PublicDocsConnector(modified_config)
        
        # Extract content from the HTML
        content = connector._extract_content(html_content)
        
        # Verify the extracted content
        assert content is not None
        assert len(content) > 0
        
        # Check for specific content in the sample document
        assert "Test Document" in content
        assert "This is a sample document for testing purposes." in content
        assert "def example_function():" in content
        assert "return \"Hello, World!\"" in content

    @pytest.mark.asyncio
    async def test_url_filtering(self, publicdocs_config):
        """Test URL filtering based on configuration."""
        # Create the connector with the real configuration
        connector = PublicDocsConnector(publicdocs_config)
        
        # Test URLs that should be processed
        base_url = str(publicdocs_config.base_url)
        should_process = connector._should_process_url(base_url)
        
        # The base URL should always be processed
        assert should_process is True
        
        # Test URLs that should be excluded based on exclude_paths
        for exclude_path in publicdocs_config.exclude_paths:
            # Create a test URL that matches the exclude pattern
            if "*" in exclude_path:
                # Replace * with "test" for a concrete URL
                test_path = exclude_path.replace("*", "test")
            else:
                test_path = exclude_path
            
            test_url = f"{base_url}{test_path}"
            should_process = connector._should_process_url(test_url)
            
            # This URL should be excluded
            assert should_process is False