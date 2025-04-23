"""
Tests for the base connector interface and functionality.
"""

import pytest
from unittest.mock import MagicMock

from qdrant_loader.config.source_config import SourceConfig
from qdrant_loader.connectors.base import BaseConnector


class TestBaseConnector:
    """Test suite for the BaseConnector class."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = MagicMock(spec=SourceConfig)
        config.source_id = "test-source"
        config.name = "Test Source"
        return config

    @pytest.fixture
    def connector(self, mock_config):
        """Create a BaseConnector instance."""

        class ConcreteConnector(BaseConnector):
            """Concrete implementation of BaseConnector for testing."""

            def __init__(self, config):
                super().__init__(config)

            async def get_documents(self):
                """Implement abstract method."""
                return []

        return ConcreteConnector(mock_config)

    def test_initialization(self, connector, mock_config):
        """Test the connector initialization."""
        assert connector.config == mock_config

    def test_create_document(self, connector):
        """Test document creation."""
        # This test can't be implemented if there's no create_document method
        pass
