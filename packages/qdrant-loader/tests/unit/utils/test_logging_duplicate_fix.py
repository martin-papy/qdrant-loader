"""Test logging duplicate level fix."""

import logging
from unittest.mock import Mock, patch

import pytest
from qdrant_loader.utils.logging import CleanFormatter, CustomConsoleRenderer


class TestLoggingDuplicateFix:
    """Test fixing duplicate log levels in logging output."""

    def test_clean_formatter_with_custom_renderer_no_duplicate(self):
        """Test that CleanFormatter doesn't add duplicate levels when using custom renderer."""
        formatter = CleanFormatter(use_custom_renderer=True)

        # Create a mock log record
        record = Mock()
        record.levelname = "DEBUG"
        record.levelno = logging.DEBUG

        # Simulate message already formatted by CustomConsoleRenderer
        record.getMessage.return_value = "16:52:50 [DEBUG] Document content length: 372"

        # Format the record
        result = formatter.format(record)

        # Should return the message as-is without adding another [DEBUG]
        assert result == "16:52:50 [DEBUG] Document content length: 372"
        # Should NOT contain duplicate levels
        assert "[DEBUG] [DEBUG]" not in result

    def test_clean_formatter_without_custom_renderer_detects_existing_level(self):
        """Test that CleanFormatter detects existing level tags and doesn't duplicate them."""
        formatter = CleanFormatter(use_custom_renderer=False)

        # Create a mock log record
        record = Mock()
        record.levelname = "WARNING"
        record.levelno = logging.WARNING

        # Simulate message that already has a level tag
        record.getMessage.return_value = "16:52:50 [WARNING] File conversion failed"

        # Format the record
        result = formatter.format(record)

        # Should not add duplicate level
        assert result == "16:52:50 [WARNING] File conversion failed"
        assert "[WARNING] [WARNING]" not in result

    def test_clean_formatter_without_custom_renderer_adds_level_when_missing(self):
        """Test that CleanFormatter adds level when it's missing."""
        formatter = CleanFormatter(use_custom_renderer=False)

        # Create a mock log record
        record = Mock()
        record.levelname = "ERROR"
        record.levelno = logging.ERROR

        # Simulate message without level tag
        record.getMessage.return_value = "16:52:50 Conversion failed unexpectedly"

        # Format the record
        result = formatter.format(record)

        # Should add the level tag
        assert result == "16:52:50 [ERROR] Conversion failed unexpectedly"

    def test_custom_console_renderer_output_format(self):
        """Test that CustomConsoleRenderer produces the expected format."""
        renderer = CustomConsoleRenderer(
            colors=False
        )  # Disable colors for easier testing

        # Create mock event dict
        event_dict = {
            "event": "Document content length: 372",
            "timestamp": "16:52:50",
        }

        # Call renderer
        result = renderer(None, "debug", event_dict)

        # Should produce format: "HH:MM:SS [LEVEL] message"
        # Note: without colors, should be clean text
        assert "[DEBUG]" in result
        assert "16:52:50" in result
        assert "Document content length: 372" in result

    def test_clean_formatter_info_level_no_level_tag(self):
        """Test that CleanFormatter doesn't add level tags for INFO messages."""
        formatter = CleanFormatter(use_custom_renderer=False)

        # Create a mock log record for INFO level
        record = Mock()
        record.levelname = "INFO"
        record.levelno = logging.INFO

        # Simulate INFO message
        record.getMessage.return_value = "16:52:50 Starting file conversion"

        # Format the record
        result = formatter.format(record)

        # INFO level should not have level tag added
        assert result == "16:52:50 Starting file conversion"
        assert "[INFO]" not in result

    def test_multiple_level_patterns_detected(self):
        """Test that formatter correctly detects various level patterns."""
        formatter = CleanFormatter(use_custom_renderer=False)

        test_cases = [
            ("DEBUG", "16:52:50 [DEBUG] Test message", "16:52:50 [DEBUG] Test message"),
            (
                "WARNING",
                "16:52:50 [WARNING] Test message",
                "16:52:50 [WARNING] Test message",
            ),
            ("ERROR", "16:52:50 [ERROR] Test message", "16:52:50 [ERROR] Test message"),
            (
                "CRITICAL",
                "16:52:50 [CRITICAL] Test message",
                "16:52:50 [CRITICAL] Test message",
            ),
        ]

        for level_name, input_message, expected_output in test_cases:
            record = Mock()
            record.levelname = level_name
            record.levelno = getattr(logging, level_name)
            record.getMessage.return_value = input_message

            result = formatter.format(record)
            assert result == expected_output
            # Ensure no duplication
            assert f"[{level_name}] [{level_name}]" not in result

    def test_no_timestamp_level_detection(self):
        """Test level detection when there's no timestamp in the message."""
        formatter = CleanFormatter(use_custom_renderer=False)

        # Create a mock log record
        record = Mock()
        record.levelname = "DEBUG"
        record.levelno = logging.DEBUG

        # Message without timestamp but with level
        record.getMessage.return_value = "[DEBUG] Some debug message"

        # Format the record
        result = formatter.format(record)

        # Should not add duplicate level
        assert result == "[DEBUG] Some debug message"
        assert "[DEBUG] [DEBUG]" not in result
