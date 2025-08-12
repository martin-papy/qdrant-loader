"""Test FileFormatter duplicate level fix."""

import logging
from unittest.mock import Mock

from qdrant_loader.utils.logging import FileFormatter


class TestFileFormatterDuplicateFix:
    """Test fixing duplicate log levels in FileFormatter output."""

    def test_file_formatter_no_duplicate_debug_level(self):
        """Test that FileFormatter doesn't add duplicate DEBUG levels."""
        formatter = FileFormatter()

        # Create a mock log record
        record = Mock()
        record.levelname = "DEBUG"
        record.levelno = logging.DEBUG

        # Mock the formatTime method
        formatter.formatTime = Mock(return_value="2025-06-18 15:53:57")

        # Simulate message already formatted by CustomConsoleRenderer with level
        record.getMessage.return_value = "15:53:57 [DEBUG] Document content length: 372"

        # Format the record
        result = formatter.format(record)

        # Should not contain duplicate levels
        assert "[DEBUG] [DEBUG]" not in result
        # Should contain the timestamp and single level
        assert "2025-06-18 15:53:57 | [DEBUG] Document content length: 372" == result

    def test_file_formatter_no_duplicate_warning_level(self):
        """Test that FileFormatter doesn't add duplicate WARNING levels."""
        formatter = FileFormatter()

        record = Mock()
        record.levelname = "WARNING"
        record.levelno = logging.WARNING
        formatter.formatTime = Mock(return_value="2025-06-18 15:53:57")

        # Message already has WARNING level
        record.getMessage.return_value = "15:53:57 [WARNING] File conversion failed"

        result = formatter.format(record)

        assert "[WARNING] [WARNING]" not in result
        assert "2025-06-18 15:53:57 | [WARNING] File conversion failed" == result

    def test_file_formatter_adds_level_when_missing(self):
        """Test that FileFormatter adds level when it's missing."""
        formatter = FileFormatter()

        record = Mock()
        record.levelname = "ERROR"
        record.levelno = logging.ERROR
        formatter.formatTime = Mock(return_value="2025-06-18 15:53:57")

        # Message without level tag
        record.getMessage.return_value = "15:53:57 Conversion failed unexpectedly"

        result = formatter.format(record)

        # Should add the level tag
        assert "2025-06-18 15:53:57 | [ERROR] Conversion failed unexpectedly" == result

    def test_file_formatter_info_level_no_duplicate(self):
        """Test that FileFormatter handles INFO level correctly."""
        formatter = FileFormatter()

        record = Mock()
        record.levelname = "INFO"
        record.levelno = logging.INFO
        formatter.formatTime = Mock(return_value="2025-06-18 15:53:57")

        # INFO message with timestamp
        record.getMessage.return_value = "15:53:57 Starting file conversion"

        result = formatter.format(record)

        # INFO level should not have level tag added (clean format)
        assert "2025-06-18 15:53:57 | Starting file conversion" == result
        assert "[INFO]" not in result

    def test_file_formatter_strips_ansi_codes(self):
        """Test that FileFormatter strips ANSI color codes."""
        formatter = FileFormatter()

        record = Mock()
        record.levelname = "DEBUG"
        record.levelno = logging.DEBUG
        formatter.formatTime = Mock(return_value="2025-06-18 15:53:57")

        # Message with ANSI color codes
        record.getMessage.return_value = (
            "\033[90m15:53:57\033[0m \033[96m[DEBUG]\033[0m Document processing"
        )

        result = formatter.format(record)

        # Should strip ANSI codes and not duplicate level
        assert "\033[" not in result
        assert "[DEBUG] [DEBUG]" not in result
        assert "2025-06-18 15:53:57 | [DEBUG] Document processing" == result
