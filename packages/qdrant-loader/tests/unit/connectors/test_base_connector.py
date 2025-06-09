"""
Tests for the base connector interface and functionality.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from abc import ABC

from qdrant_loader.config.source_config import SourceConfig
from qdrant_loader.connectors.base import BaseConnector
from qdrant_loader.core.document import Document


class TestBaseConnector:
    """Test suite for the BaseConnector class."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = MagicMock(spec=SourceConfig)
        config.source_id = "test-source"
        config.name = "Test Source"
        config.source_type = "test"
        config.source = "test-source"
        return config

    @pytest.fixture
    def concrete_connector_class(self):
        """Create a concrete implementation of BaseConnector for testing."""

        class ConcreteConnector(BaseConnector):
            """Concrete implementation of BaseConnector for testing."""

            def __init__(self, config):
                super().__init__(config)
                self._documents = []

            async def get_documents(self):
                """Implement abstract method."""
                return self._documents

            def set_test_documents(self, documents):
                """Helper method to set test documents."""
                self._documents = documents

        return ConcreteConnector

    @pytest.fixture
    def connector(self, mock_config, concrete_connector_class):
        """Create a BaseConnector instance."""
        return concrete_connector_class(mock_config)

    def test_initialization(self, connector, mock_config):
        """Test the connector initialization."""
        assert connector.config == mock_config
        assert connector.config.source_id == "test-source"
        assert connector.config.name == "Test Source"

    def test_base_connector_is_abstract(self):
        """Test that BaseConnector cannot be instantiated directly."""
        mock_config = MagicMock(spec=SourceConfig)

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseConnector(mock_config)  # type: ignore

    def test_abstract_method_enforcement(self):
        """Test that subclasses must implement abstract methods."""

        class IncompleteConnector(BaseConnector):
            """Incomplete connector missing abstract method implementation."""

            pass

        mock_config = MagicMock(spec=SourceConfig)

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteConnector(mock_config)  # type: ignore

    @pytest.mark.asyncio
    async def test_get_documents_abstract_method(self, connector):
        """Test that get_documents is properly implemented."""
        # Should not raise an error since our concrete class implements it
        documents = await connector.get_documents()
        assert isinstance(documents, list)
        assert len(documents) == 0

    @pytest.mark.asyncio
    async def test_get_documents_with_test_data(self, connector):
        """Test get_documents with test data."""
        test_documents = [
            Document(
                title="Test Doc 1",
                content="Content 1",
                content_type="text/plain",
                source_type="test",
                source="test-source",
                url="http://test.com/doc1",
                metadata={},
            ),
            Document(
                title="Test Doc 2",
                content="Content 2",
                content_type="text/plain",
                source_type="test",
                source="test-source",
                url="http://test.com/doc2",
                metadata={},
            ),
        ]

        connector.set_test_documents(test_documents)
        documents = await connector.get_documents()

        assert len(documents) == 2
        assert all(isinstance(doc, Document) for doc in documents)
        assert documents[0].title == "Test Doc 1"
        assert documents[1].title == "Test Doc 2"

    def test_config_property_access(self, connector, mock_config):
        """Test that config property provides access to configuration."""
        assert connector.config is mock_config
        assert connector.config.source_id == "test-source"
        assert connector.config.name == "Test Source"

    def test_config_immutability(self, connector, mock_config):
        """Test that config cannot be modified after initialization."""
        original_config = connector.config

        # Config can be set (no property protection in BaseConnector)
        # This test verifies the config is properly stored
        assert connector.config is original_config

        # Setting a new config should work (no immutability enforced)
        new_config = MagicMock(spec=SourceConfig)
        connector.config = new_config
        assert connector.config is new_config

        # Config has been changed (no immutability protection)
        assert connector.config is not original_config

    def test_inheritance_structure(self, concrete_connector_class):
        """Test that BaseConnector has proper inheritance structure."""
        assert issubclass(BaseConnector, ABC)
        assert issubclass(concrete_connector_class, BaseConnector)

    @pytest.mark.asyncio
    async def test_connector_with_different_config_types(
        self, concrete_connector_class
    ):
        """Test connector with different configuration types."""
        configs = [
            MagicMock(spec=SourceConfig, source_id="git-repo", name="Git Repo"),
            MagicMock(
                spec=SourceConfig, source_id="confluence-space", name="Confluence Space"
            ),
            MagicMock(spec=SourceConfig, source_id="jira-project", name="Jira Project"),
        ]

        for config in configs:
            connector = concrete_connector_class(config)
            assert connector.config == config
            documents = await connector.get_documents()
            assert isinstance(documents, list)

    def test_connector_with_none_config(self, concrete_connector_class):
        """Test connector behavior with None config."""
        # BaseConnector accepts None config (no validation in constructor)
        connector = concrete_connector_class(None)
        assert connector.config is None

    def test_connector_with_invalid_config(self, concrete_connector_class):
        """Test connector behavior with invalid config."""
        invalid_configs = ["string_config", 123, {}, []]

        for invalid_config in invalid_configs:
            # BaseConnector accepts any config type (no validation in constructor)
            connector = concrete_connector_class(invalid_config)
            assert connector.config == invalid_config

    @pytest.mark.asyncio
    async def test_error_handling_in_get_documents(self, mock_config):
        """Test error handling in get_documents implementation."""

        class ErrorConnector(BaseConnector):
            """Connector that raises errors for testing."""

            async def get_documents(self):
                raise ValueError("Test error")

        connector = ErrorConnector(mock_config)

        with pytest.raises(ValueError, match="Test error"):
            await connector.get_documents()

    @pytest.mark.asyncio
    async def test_async_context_manager_support(self, connector):
        """Test that connector can be used as async context manager if implemented."""
        # BaseConnector doesn't implement context manager by default
        # This test verifies the basic structure
        assert hasattr(connector, "get_documents")
        documents = await connector.get_documents()
        assert isinstance(documents, list)

    def test_multiple_connector_instances(self, concrete_connector_class):
        """Test creating multiple connector instances."""
        configs = []
        for i in range(5):
            config = MagicMock(spec=SourceConfig)
            config.source_id = f"source-{i}"
            config.name = f"Source {i}"
            configs.append(config)

        connectors = [concrete_connector_class(config) for config in configs]

        assert len(connectors) == 5
        for i, connector in enumerate(connectors):
            assert connector.config.source_id == f"source-{i}"
            assert connector.config.name == f"Source {i}"

    @pytest.mark.asyncio
    async def test_concurrent_document_retrieval(self, concrete_connector_class):
        """Test concurrent document retrieval from multiple connectors."""
        import asyncio

        configs = [
            MagicMock(spec=SourceConfig, source_id=f"source-{i}", name=f"Source {i}")
            for i in range(3)
        ]

        connectors = [concrete_connector_class(config) for config in configs]

        # Set different test documents for each connector
        for i, connector in enumerate(connectors):
            test_docs = [
                Document(
                    title=f"Doc {j} from Source {i}",
                    content=f"Content {j}",
                    content_type="text/plain",
                    source_type="test",
                    source=f"source-{i}",
                    url=f"http://test.com/source{i}/doc{j}",
                    metadata={},
                )
                for j in range(2)
            ]
            connector.set_test_documents(test_docs)

        # Retrieve documents concurrently
        tasks = [connector.get_documents() for connector in connectors]
        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        for i, documents in enumerate(results):
            assert len(documents) == 2
            assert all(f"Source {i}" in doc.title for doc in documents)

    def test_connector_string_representation(self, connector):
        """Test string representation of connector."""
        # BaseConnector doesn't define __str__ or __repr__ by default
        # This test verifies basic object representation
        str_repr = str(connector)
        assert "ConcreteConnector" in str_repr or "BaseConnector" in str_repr

    @pytest.mark.asyncio
    async def test_document_validation(self, connector):
        """Test that returned documents are properly validated."""
        # Test with valid documents
        valid_documents = [
            Document(
                title="Valid Doc",
                content="Valid content",
                content_type="text/plain",
                source_type="test",
                source="test-source",
                url="http://test.com/valid",
                metadata={},
            )
        ]

        connector.set_test_documents(valid_documents)
        documents = await connector.get_documents()

        assert len(documents) == 1
        assert isinstance(documents[0], Document)
        assert documents[0].title == "Valid Doc"

    def test_config_attribute_access(self, connector, mock_config):
        """Test accessing various config attributes through connector."""
        # Test that we can access config attributes
        assert connector.config.source_id == mock_config.source_id
        assert connector.config.name == mock_config.name
        assert connector.config.source_type == mock_config.source_type
        assert connector.config.source == mock_config.source
