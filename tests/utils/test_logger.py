import os
import pytest
import logging
from unittest.mock import patch, MagicMock
from qdrant_loader.utils.logger import setup_logging, get_logger
import structlog

@pytest.fixture
def mock_env():
    with patch.dict(os.environ, {
        "LOG_LEVEL": "INFO",
        "LOG_FORMAT": "json"
    }):
        yield

def test_setup_logging_defaults(mock_env):
    """Test logging setup with default values."""
    with patch('logging.basicConfig') as mock_basic_config, \
         patch('structlog.configure') as mock_configure:
        
        setup_logging()
        
        # Verify logging was configured
        mock_basic_config.assert_called_once_with(level=logging.INFO)
        # Verify structlog was configured
        mock_configure.assert_called_once()

def test_setup_logging_custom_values():
    """Test logging setup with custom values."""
    with patch('logging.basicConfig') as mock_basic_config, \
         patch('structlog.configure') as mock_configure:
        
        setup_logging(log_level="DEBUG", log_format="console")
        
        # Verify logging was configured
        mock_basic_config.assert_called_once_with(level=logging.DEBUG)
        # Verify structlog was configured
        mock_configure.assert_called_once()

def test_setup_logging_invalid_level():
    """Test logging setup with invalid log level."""
    with pytest.raises(ValueError, match="Invalid log level: INVALID"):
        setup_logging(log_level="INVALID")

def test_get_logger():
    """Test getting a logger instance."""
    with patch('structlog.get_logger') as mock_get_logger:
        logger = get_logger("test_logger")
        mock_get_logger.assert_called_once_with("test_logger")
        assert logger == mock_get_logger.return_value

def test_logger_integration():
    """Test actual logging functionality."""
    # Create a mock logger before setting up
    mock_logger = MagicMock(spec=structlog.stdlib.BoundLogger)
    
    with patch('structlog.stdlib.LoggerFactory') as mock_factory, \
         patch('structlog.stdlib.BoundLogger') as mock_bound_logger:
        
        # Configure the mock factory to return our mock logger
        mock_factory.return_value.return_value = mock_logger
        mock_bound_logger.return_value = mock_logger
        
        # Set up logging and get logger
        setup_logging(log_level="DEBUG", log_format="json")
        logger = get_logger("test")
        
        # Test logging at different levels
        logger.info("test message", key="value")
        logger.error("error message", error="test error")
        logger.debug("debug message", data={"test": "data"})
        
        # Verify log calls
        assert mock_logger.info.called
        assert mock_logger.error.called
        assert mock_logger.debug.called 