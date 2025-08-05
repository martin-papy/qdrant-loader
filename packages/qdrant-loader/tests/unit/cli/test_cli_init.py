"""Tests for the CLI __init__.py module with lazy imports."""

import pytest
from unittest.mock import patch, MagicMock

# Import the module to test its lazy import functionality
import qdrant_loader.cli as cli_module


class TestLazyImports:
    """Test cases for the lazy import system in CLI module."""

    def test_get_settings_lazy_import(self):
        """Test lazy import of get_settings."""
        with patch('qdrant_loader.config.get_settings') as mock_get_settings:
            mock_function = MagicMock()
            mock_get_settings.return_value = mock_function
            
            # Access the lazy import
            result = cli_module.get_settings
            
            # Verify the function was imported and returned
            assert result == mock_get_settings

    def test_async_ingestion_pipeline_lazy_import(self):
        """Test lazy import of AsyncIngestionPipeline."""
        with patch('qdrant_loader.core.async_ingestion_pipeline.AsyncIngestionPipeline') as mock_pipeline:
            mock_class = MagicMock()
            mock_pipeline.return_value = mock_class
            
            # Access the lazy import
            result = cli_module.AsyncIngestionPipeline
            
            # Verify the class was imported and returned
            assert result == mock_pipeline

    def test_init_collection_lazy_import(self):
        """Test lazy import of init_collection."""
        with patch('qdrant_loader.core.init_collection.init_collection') as mock_init_collection:
            mock_function = MagicMock()
            mock_init_collection.return_value = mock_function
            
            # Access the lazy import
            result = cli_module.init_collection
            
            # Verify the function was imported and returned
            assert result == mock_init_collection

    def test_logger_lazy_import(self):
        """Test lazy import of logger."""
        with patch('qdrant_loader.utils.logging.LoggingConfig') as mock_logging_config:
            mock_logger = MagicMock()
            mock_logging_config.get_logger.return_value = mock_logger
            
            # Access the lazy import
            result = cli_module.logger
            
            # Verify the logger was created and returned
            assert result == mock_logger
            mock_logging_config.get_logger.assert_called_once_with('qdrant_loader.cli')

    def test_invalid_attribute_raises_attribute_error(self):
        """Test that accessing invalid attributes raises AttributeError."""
        with pytest.raises(AttributeError) as exc_info:
            # Try to access a non-existent attribute
            _ = cli_module.nonexistent_attribute
        
        error_message = str(exc_info.value)
        assert "module 'qdrant_loader.cli' has no attribute 'nonexistent_attribute'" in error_message

    def test_multiple_accesses_of_same_attribute(self):
        """Test that multiple accesses of the same attribute work correctly."""
        with patch('qdrant_loader.config.get_settings') as mock_get_settings:
            mock_function = MagicMock()
            mock_get_settings.return_value = mock_function
            
            # Access the same attribute multiple times
            result1 = cli_module.get_settings
            result2 = cli_module.get_settings
            
            # Both should return the same imported function
            assert result1 == mock_get_settings
            assert result2 == mock_get_settings
            assert result1 == result2

    def test_all_exports_are_accessible(self):
        """Test that all items in __all__ are accessible via lazy imports."""
        # Get the __all__ list from the module
        all_exports = cli_module.__all__
        expected_exports = ["AsyncIngestionPipeline", "init_collection", "get_settings", "logger"]
        
        # Verify __all__ contains expected exports
        assert set(all_exports) == set(expected_exports)
        
        # Verify each export can be accessed
        with (
            patch('qdrant_loader.config.get_settings') as mock_get_settings,
            patch('qdrant_loader.core.async_ingestion_pipeline.AsyncIngestionPipeline') as mock_pipeline,
            patch('qdrant_loader.core.init_collection.init_collection') as mock_init_collection,
            patch('qdrant_loader.utils.logging.LoggingConfig') as mock_logging_config
        ):
            mock_logging_config.get_logger.return_value = MagicMock()
            
            for export_name in all_exports:
                # Should not raise AttributeError
                result = getattr(cli_module, export_name)
                assert result is not None

    def test_getattr_with_different_attribute_names(self):
        """Test __getattr__ method with various attribute name types."""
        # Test with valid names (should work)
        valid_names = ["get_settings", "AsyncIngestionPipeline", "init_collection", "logger"]
        
        for name in valid_names:
            try:
                # This should not raise an exception for valid names
                _ = getattr(cli_module, name)
            except AttributeError:
                pytest.fail(f"Valid attribute '{name}' raised AttributeError")
        
        # Test with invalid names (should raise AttributeError)
        invalid_names = ["", "invalid", "123invalid", "_private", "__dunder__"]
        
        for name in invalid_names:
            with pytest.raises(AttributeError):
                _ = getattr(cli_module, name)

    def test_lazy_import_attribute_error_path(self):
        """Test that accessing invalid attributes follows the correct error path."""
        # Test the else clause in __getattr__ which raises AttributeError
        with pytest.raises(AttributeError, match="module 'qdrant_loader.cli' has no attribute 'invalid_attribute'"):
            _ = getattr(cli_module, 'invalid_attribute')

    def test_module_has_expected_structure(self):
        """Test that the module has the expected structure."""
        # Check that the module has __getattr__ function
        assert hasattr(cli_module, '__getattr__')
        assert callable(getattr(cli_module, '__getattr__'))
        
        # Check that __all__ is defined
        assert hasattr(cli_module, '__all__')
        assert isinstance(cli_module.__all__, list)
        
        # Check that __all__ is not empty
        assert len(cli_module.__all__) > 0

    def test_lazy_import_consistent_behavior(self):
        """Test that lazy imports behave consistently."""
        # This test ensures that multiple calls to the same lazy import return the same object
        # This is the expected behavior since Python caches imports
        
        with patch('qdrant_loader.config.get_settings') as mock_get_settings:
            mock_function = MagicMock(name="get_settings_function")
            mock_get_settings.return_value = mock_function
            
            # First access - should trigger import
            result1 = cli_module.get_settings
            
            # Second access - should return the same imported object
            result2 = cli_module.get_settings
            
            # Both should return the same imported function (due to Python's import caching)
            assert result1 == mock_get_settings
            assert result2 == mock_get_settings
            assert result1 == result2