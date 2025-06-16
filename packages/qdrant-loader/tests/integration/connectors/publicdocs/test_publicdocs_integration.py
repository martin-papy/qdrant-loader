"""Integration tests for PublicDocs connector with real configuration."""

import os
import warnings
from pathlib import Path

import pytest
from bs4 import XMLParsedAsHTMLWarning

from qdrant_loader.config import get_settings, initialize_multi_file_config
from qdrant_loader.config.types import SourceType
from qdrant_loader.connectors.publicdocs.config import PublicDocsSourceConfig
from qdrant_loader.connectors.publicdocs.connector import PublicDocsConnector

# Suppress XMLParsedAsHTMLWarning
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


class TestPublicDocsIntegration:
    """Integration tests for PublicDocs connector."""

    @pytest.fixture(scope="class")
    def test_settings(self):
        """Load test settings from configuration files."""
        config_dir = Path(__file__).parent.parent.parent.parent / "config"
        initialize_multi_file_config(config_dir, enhanced_validation=False)
        return get_settings()

    @pytest.fixture
    def publicdocs_config(self, test_settings):
        """Get the PublicDocs configuration from multi-file configuration."""
        try:
            # Look for publicdocs sources in the loaded configuration
            publicdocs_sources = None
            for (
                project_id,
                project_config,
            ) in test_settings.projects_config.projects.items():
                if hasattr(project_config, "sources") and project_config.sources:
                    project_sources = project_config.sources
                    if (
                        hasattr(project_sources, "publicdocs")
                        and project_sources.publicdocs
                    ):
                        publicdocs_sources = project_sources.publicdocs
                        break

            if not publicdocs_sources:
                # No PublicDocs sources found, create mock configuration
                mock_config = {
                    "source": "test-publicdocs",
                    "source_type": SourceType.PUBLICDOCS,
                    "base_url": "https://example.com/docs",
                    "version": "1.0",
                    "selectors": {"content": ".content", "title": "h1"},
                    "exclude_paths": ["/api/*", "/internal/*"],
                    "max_depth": 3,
                    "delay": 1.0,
                }
                return PublicDocsSourceConfig.model_validate(mock_config)

            # Use the first publicdocs source
            source_name = next(iter(publicdocs_sources.keys()), None)
            if not source_name:
                pytest.skip("No PublicDocs source configured in test settings")

            # Get the source configuration
            config_dict = publicdocs_sources[source_name].model_dump()

            # Add required fields
            config_dict["source"] = source_name
            config_dict["source_type"] = SourceType.PUBLICDOCS

            # Create the configuration object
            return PublicDocsSourceConfig.model_validate(config_dict)

        except Exception as e:
            # If anything fails, fall back to mock configuration
            print(f"Failed to load PublicDocs configuration: {e}")
            mock_config = {
                "source": "test-publicdocs",
                "source_type": SourceType.PUBLICDOCS,
                "base_url": "https://example.com/docs",
                "version": "1.0",
                "selectors": {"content": ".content", "title": "h1"},
                "exclude_paths": ["/api/*", "/internal/*"],
                "max_depth": 3,
                "delay": 1.0,
            }
            return PublicDocsSourceConfig.model_validate(mock_config)

    @pytest.mark.asyncio
    async def test_document_crawling(self, publicdocs_config):
        """Test document crawling with real configuration."""
        # Skip if using mock configuration (no real PublicDocs source available)
        if str(publicdocs_config.base_url) == "https://example.com/docs":
            pytest.skip(
                "Using mock PublicDocs configuration - no real source available"
            )

        # Create the connector with the real configuration
        connector = PublicDocsConnector(publicdocs_config)
        async with connector:
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

        with open(sample_doc_path) as f:
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
        assert 'return "Hello, World!"' in content

    @pytest.mark.asyncio
    async def test_url_filtering(self, publicdocs_config):
        """Test URL filtering based on configuration."""
        # Skip if using mock configuration (no real PublicDocs source available)
        if str(publicdocs_config.base_url) == "https://example.com/docs":
            pytest.skip(
                "Using mock PublicDocs configuration - no real source available"
            )

        # Create the connector with the real configuration
        connector = PublicDocsConnector(publicdocs_config)

        # Test URLs that should be processed
        base_url = str(publicdocs_config.base_url)
        should_process = connector._should_process_url(base_url)

        # The base URL should always be processed
        assert should_process

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
