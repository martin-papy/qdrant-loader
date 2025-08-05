"""Tests for the connectors base module."""

import pytest
from unittest.mock import Mock

from qdrant_loader.connectors.base import BaseConnector
from qdrant_loader.core.document import Document


class TestBaseConnector:
    """Test cases for BaseConnector."""

    def test_set_file_conversion_config_default_implementation(self):
        """Test the default set_file_conversion_config implementation - covers line 35."""
        # Create a concrete implementation of BaseConnector for testing
        class TestConnector(BaseConnector):
            def __init__(self, config=None):
                if config is None:
                    config = Mock()
                super().__init__(config)
            
            async def get_documents(self) -> list[Document]:
                return []  # Minimal implementation
        
        connector = TestConnector()
        
        # Call set_file_conversion_config - this should hit line 35 (the pass statement)
        file_conversion_config = Mock()
        
        # This should not raise any errors and should execute the pass statement
        result = connector.set_file_conversion_config(file_conversion_config)
        
        # The method should return None (implicit return from pass statement)
        assert result is None

    def test_abstract_method_signature(self):
        """Test that BaseConnector defines the abstract methods correctly."""
        # Verify that BaseConnector has the expected abstract methods
        assert hasattr(BaseConnector, 'get_documents')
        assert hasattr(BaseConnector, 'set_file_conversion_config')
        
        # Verify that set_file_conversion_config is not abstract (has default implementation)
        # We can test this by checking if it can be called on a concrete subclass
        class TestConnector(BaseConnector):
            def __init__(self, config=None):
                if config is None:
                    config = Mock()
                super().__init__(config)
            
            async def get_documents(self) -> list[Document]:
                return []
        
        connector = TestConnector()
        
        # Should be able to call set_file_conversion_config (covers line 35)
        connector.set_file_conversion_config(Mock())

    def test_base_connector_instantiation_fails(self):
        """Test that BaseConnector cannot be instantiated directly due to abstract methods."""
        with pytest.raises(TypeError):
            BaseConnector()

    def test_concrete_subclass_must_implement_get_documents(self):
        """Test that concrete subclasses must implement get_documents."""
        class IncompleteConnector(BaseConnector):
            def __init__(self, config=None):
                if config is None:
                    config = Mock()
                super().__init__(config)
            
            # Missing get_documents implementation
        
        with pytest.raises(TypeError):
            IncompleteConnector()

    def test_set_file_conversion_config_with_none_config(self):
        """Test set_file_conversion_config with None config - covers line 35."""
        class TestConnector(BaseConnector):
            def __init__(self, config=None):
                if config is None:
                    config = Mock()
                super().__init__(config)
            
            async def get_documents(self) -> list[Document]:
                return []
        
        connector = TestConnector()
        
        # Call with None config - should still execute line 35 without errors
        result = connector.set_file_conversion_config(None)
        assert result is None

    def test_set_file_conversion_config_multiple_calls(self):
        """Test multiple calls to set_file_conversion_config - covers line 35 multiple times."""
        class TestConnector(BaseConnector):
            def __init__(self, config=None):
                if config is None:
                    config = Mock()
                super().__init__(config)
            
            async def get_documents(self) -> list[Document]:
                return []
        
        connector = TestConnector()
        
        # Multiple calls should all execute line 35
        for i in range(3):
            file_config = Mock()
            file_config.test_value = i
            result = connector.set_file_conversion_config(file_config)
            assert result is None