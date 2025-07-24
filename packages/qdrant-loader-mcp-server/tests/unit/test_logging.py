"""Tests for logging utilities."""

import logging
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from qdrant_loader_mcp_server.utils.logging import (
    ApplicationFilter,
    CleanFormatter,
    LoggingConfig,
    QdrantVersionFilter,
)


def test_qdrant_version_filter():
    """Test QdrantVersionFilter filters version check warnings."""
    filter_instance = QdrantVersionFilter()

    # Test that version check warnings are filtered out
    record = MagicMock()
    record.msg = "Failed to obtain server version"
    assert filter_instance.filter(record) is False

    # Test that other messages pass through
    record.msg = "Some other message"
    assert filter_instance.filter(record) is True


def test_application_filter():
    """Test ApplicationFilter only shows application logs."""
    filter_instance = ApplicationFilter()

    # Test application logs pass through
    test_cases = [
        ("mcp_server.test", True),
        ("src.main", True),
        ("uvicorn", True),
        ("fastapi", True),
        ("__main__", True),
        ("asyncio", True),
        ("main", True),
        ("qdrant_loader_mcp_server", True),
        ("external.library", False),
        ("some.other.module", False),
    ]

    # Use a simple class instead of MagicMock to avoid async confusion
    class TestRecord:
        def __init__(self, name):
            self.name = name

    for name, expected in test_cases:
        record = TestRecord(name)
        assert filter_instance.filter(record) is expected


def test_clean_formatter():
    """Test CleanFormatter removes ANSI color codes."""
    formatter = CleanFormatter()

    # Create a mock record
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Test message with \x1b[31mcolor\x1b[0m codes",
        args=(),
        exc_info=None,
    )

    # Format the record
    formatted = formatter.format(record)

    # Verify ANSI codes are removed
    assert "\x1b[31m" not in formatted
    assert "\x1b[0m" not in formatted
    assert "Test message with color codes" in formatted


def test_logging_config_setup_basic():
    """Test basic logging configuration setup."""
    # Reset logging config
    LoggingConfig._initialized = False

    # Test basic setup
    LoggingConfig.setup(level="DEBUG", format="console")

    assert LoggingConfig._initialized is True
    assert LoggingConfig._current_config == ("DEBUG", "console", None, True)


def test_logging_config_setup_with_file():
    """Test logging configuration with file output."""
    LoggingConfig._initialized = False

    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        try:
            LoggingConfig.setup(level="INFO", format="json", file=tmp_file.name)

            assert LoggingConfig._initialized is True
            assert LoggingConfig._current_config == (
                "INFO",
                "json",
                tmp_file.name,
                True,
            )
        finally:
            os.unlink(tmp_file.name)


def test_logging_config_setup_with_env_variables():
    """Test logging configuration with environment variables."""
    LoggingConfig._initialized = False

    with tempfile.TemporaryDirectory() as tmp_dir:
        log_file = os.path.join(tmp_dir, "test.log")

        with patch.dict(
            os.environ,
            {
                "MCP_LOG_LEVEL": "WARNING",
                "MCP_LOG_FILE": log_file,
                "MCP_DISABLE_CONSOLE_LOGGING": "false",
            },
        ):
            LoggingConfig.setup()

            assert LoggingConfig._initialized is True
            # Check that log file was created
            assert os.path.exists(log_file)


def test_logging_config_setup_disabled_console():
    """Test logging configuration with disabled console logging."""
    LoggingConfig._initialized = False

    with patch.dict(os.environ, {"MCP_DISABLE_CONSOLE_LOGGING": "true"}):
        LoggingConfig.setup(level="INFO")

        assert LoggingConfig._initialized is True


def test_logging_config_setup_invalid_level():
    """Test logging configuration with invalid level."""
    LoggingConfig._initialized = False

    with pytest.raises(ValueError, match="Invalid log level"):
        LoggingConfig.setup(level="INVALID_LEVEL")


def test_logging_config_get_logger():
    """Test getting logger instances."""
    LoggingConfig._initialized = False

    # Test getting logger initializes config if not already done
    logger = LoggingConfig.get_logger("test")

    assert LoggingConfig._initialized is True
    assert logger is not None
    assert hasattr(logger, "info")
    assert hasattr(logger, "debug")
    assert hasattr(logger, "error")


def test_logging_config_get_logger_with_name():
    """Test getting logger with specific name."""
    LoggingConfig._initialized = False
    LoggingConfig.setup()

    logger = LoggingConfig.get_logger("custom.logger")
    assert logger is not None


def test_logging_config_get_logger_without_name():
    """Test getting logger without name."""
    LoggingConfig._initialized = False
    LoggingConfig.setup()

    logger = LoggingConfig.get_logger()
    assert logger is not None


def test_logging_config_suppress_qdrant_warnings():
    """Test suppressing Qdrant warnings."""
    LoggingConfig._initialized = False

    with patch("logging.getLogger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        LoggingConfig.setup(suppress_qdrant_warnings=True)

        # Verify filter was added to qdrant_client logger
        mock_get_logger.assert_any_call("qdrant_client")
        mock_logger.addFilter.assert_called()


def test_logging_config_no_suppress_qdrant_warnings():
    """Test not suppressing Qdrant warnings."""
    LoggingConfig._initialized = False

    with patch("logging.getLogger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        LoggingConfig.setup(suppress_qdrant_warnings=False)

        # Verify qdrant_client logger was not accessed for filtering
        calls = [call[0][0] for call in mock_get_logger.call_args_list if call[0]]
        assert "qdrant_client" not in calls


def test_logging_config_json_format():
    """Test JSON format configuration."""
    LoggingConfig._initialized = False

    with patch("structlog.configure") as mock_configure:
        LoggingConfig.setup(format="json")

        # Verify structlog was configured
        mock_configure.assert_called_once()


def test_logging_config_console_format():
    """Test console format configuration."""
    LoggingConfig._initialized = False

    with patch("structlog.configure") as mock_configure:
        LoggingConfig.setup(format="console")

        # Verify structlog was configured
        mock_configure.assert_called_once()


def test_logging_config_reset_and_reconfigure():
    """Test that logging can be reset and reconfigured."""
    LoggingConfig._initialized = False

    # First configuration
    LoggingConfig.setup(level="INFO", format="console")
    assert LoggingConfig._current_config is not None
    assert LoggingConfig._current_config[0] == "INFO"

    # Second configuration should override
    LoggingConfig.setup(level="DEBUG", format="json")
    assert LoggingConfig._current_config is not None
    assert LoggingConfig._current_config[0] == "DEBUG"
    assert LoggingConfig._current_config[1] == "json"
