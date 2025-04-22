"""
Tests for the base connector interface and functionality.
"""

from typing import Any, Dict, List
import pytest
from unittest.mock import MagicMock, patch

from qdrant_loader.connectors.base import BaseConnector


class TestBaseConnector:
    """Test suite for the BaseConnector class."""

    @pytest.fixture
    def mock_config(self):
        """Fixture providing a mock configuration."""
        return MagicMock()

    def test_interface_implementation(self, mock_config):
        """Test that the base connector implements all required methods."""

        # Create a concrete implementation of BaseConnector
        class TestConnector(BaseConnector):
            def __init__(self, config):
                super().__init__(config)
                self.config = config

            def connect(self) -> None:
                pass

            def disconnect(self) -> None:
                pass

            def fetch_documents(self) -> List[Dict[str, Any]]:
                return []

            def get_changes(self) -> List[Dict[str, Any]]:
                return []

            def get_documents(self) -> List[Dict[str, Any]]:
                return []

        # Instantiate the test connector
        connector = TestConnector(mock_config)

        # Verify all required methods exist
        assert hasattr(connector, "connect")
        assert hasattr(connector, "disconnect")
        assert hasattr(connector, "fetch_documents")
        assert hasattr(connector, "get_changes")
        assert hasattr(connector, "get_documents")

    def test_common_functionality(self, mock_config):
        """Test common functionality provided by the base connector."""

        class TestConnector(BaseConnector):
            def __init__(self, config):
                super().__init__(config)
                self.connected = False
                self.documents = []

            def connect(self) -> None:
                self.connected = True

            def disconnect(self) -> None:
                self.connected = False

            def fetch_documents(self) -> List[Dict[str, Any]]:
                return self.documents

            def get_changes(self) -> List[Dict[str, Any]]:
                return []

            def get_documents(self) -> List[Dict[str, Any]]:
                return self.documents

        # Test connection state management
        connector = TestConnector(mock_config)
        connector.connect()
        assert connector.connected is True
        connector.disconnect()
        assert connector.connected is False

        # Test document fetching
        test_docs = [{"id": "1", "content": "test"}]
        connector.documents = test_docs
        assert connector.fetch_documents() == test_docs
        assert connector.get_documents() == test_docs

    def test_error_handling(self, mock_config):
        """Test error handling in the base connector."""

        class TestConnector(BaseConnector):
            def __init__(self, config):
                super().__init__(config)

            def connect(self) -> None:
                raise ConnectionError("Failed to connect")

            def disconnect(self) -> None:
                raise ConnectionError("Failed to disconnect")

            def fetch_documents(self) -> List[Dict[str, Any]]:
                raise ValueError("Invalid documents")

            def get_changes(self) -> List[Dict[str, Any]]:
                raise RuntimeError("Failed to get changes")

            def get_documents(self) -> List[Dict[str, Any]]:
                raise RuntimeError("Failed to get documents")

        connector = TestConnector(mock_config)

        # Test error handling for each method
        with pytest.raises(ConnectionError):
            connector.connect()

        with pytest.raises(ConnectionError):
            connector.disconnect()

        with pytest.raises(ValueError):
            connector.fetch_documents()

        with pytest.raises(RuntimeError):
            connector.get_changes()

        with pytest.raises(RuntimeError):
            connector.get_documents()

    def test_event_handling(self, mock_config):
        """Test event handling in the base connector."""

        class TestConnector(BaseConnector):
            def __init__(self, config):
                super().__init__(config)
                self.events = []
                self.connected = False

            def connect(self) -> None:
                self.connected = True
                self.events.append("connected")

            def disconnect(self) -> None:
                self.connected = False
                self.events.append("disconnected")

            def fetch_documents(self) -> List[Dict[str, Any]]:
                self.events.append("fetch_documents")
                return []

            def get_changes(self) -> List[Dict[str, Any]]:
                self.events.append("get_changes")
                return []

            def get_documents(self) -> List[Dict[str, Any]]:
                self.events.append("get_documents")
                return []

        # Test event sequence
        connector = TestConnector(mock_config)
        connector.connect()
        connector.fetch_documents()
        connector.get_changes()
        connector.get_documents()
        connector.disconnect()

        expected_events = [
            "connected",
            "fetch_documents",
            "get_changes",
            "get_documents",
            "disconnected",
        ]
        assert connector.events == expected_events
