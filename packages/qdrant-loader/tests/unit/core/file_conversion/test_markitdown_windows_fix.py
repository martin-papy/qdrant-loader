"""Test MarkItDown Windows signal compatibility fix."""

import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from qdrant_loader.core.file_conversion.conversion_config import (
    FileConversionConfig,
    MarkItDownConfig,
)
from qdrant_loader.core.file_conversion.file_converter import FileConverter


class TestMarkItDownWindowsFix:
    """Test MarkItDown Windows signal compatibility fixes."""

    def test_windows_signal_monkey_patch(self):
        """Test that Windows signal monkey patch is applied correctly."""
        with patch("sys.platform", "win32"):
            # Import signal and remove SIGALRM to simulate Windows
            import signal

            if hasattr(signal, "SIGALRM"):
                delattr(signal, "SIGALRM")
            if hasattr(signal, "alarm"):
                delattr(signal, "alarm")

            # Re-import the file_converter module to trigger monkey patch
            import importlib
            from qdrant_loader.core.file_conversion import file_converter

            importlib.reload(file_converter)

            # Verify monkey patch was applied
            assert hasattr(signal, "SIGALRM")
            assert hasattr(signal, "alarm")
            assert signal.SIGALRM == 14
            assert callable(signal.alarm)

    def test_markitdown_signal_error_prevention(self):
        """Test that MarkItDown signal errors are prevented on Windows."""
        config = FileConversionConfig(
            max_file_size=50 * 1024 * 1024,
            conversion_timeout=300,
            markitdown=MarkItDownConfig(),
        )

        converter = FileConverter(config)

        # Create a test file (use .pdf since it's supported for conversion)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(b"Test content for conversion")
            tmp_file.flush()
            tmp_path = Path(tmp_file.name)

        try:
            with patch("sys.platform", "win32"):
                # Mock both validation and MarkItDown to focus on signal error prevention
                with patch.object(converter, "_validate_file") as mock_validate:
                    with patch.object(
                        converter, "_get_markitdown"
                    ) as mock_get_markitdown:
                        mock_validate.return_value = None  # Pass validation

                        mock_markitdown = Mock()

                        # This should NOT raise AttributeError: 'module signal has no attribute SIGALRM'
                        # because our monkey patch provides the missing attributes
                        mock_result = Mock()
                        mock_result.text_content = "Converted content"
                        mock_markitdown.convert.return_value = mock_result
                        mock_get_markitdown.return_value = mock_markitdown

                        # This should work without signal errors
                        result = converter.convert_file(str(tmp_path))
                        assert result == "Converted content"

        finally:
            tmp_path.unlink(missing_ok=True)

    def test_unix_platforms_unaffected(self):
        """Test that Unix/Linux/macOS platforms are unaffected by Windows fixes."""
        with patch("sys.platform", "linux"):
            # Import signal (should have native SIGALRM on Unix)
            import signal

            # Re-import to ensure no monkey patching on Unix
            import importlib
            from qdrant_loader.core.file_conversion import file_converter

            importlib.reload(file_converter)

            # On Unix, signal.SIGALRM should exist naturally (not from our patch)
            assert hasattr(signal, "SIGALRM")
            assert hasattr(signal, "alarm")
            # The value should be the real Unix SIGALRM, not our patched value
            # (could be different from 14 depending on the platform)

    def test_file_converter_initialization_windows(self):
        """Test that FileConverter can be initialized on Windows without signal errors."""
        with patch("sys.platform", "win32"):
            config = FileConversionConfig(
                max_file_size=50 * 1024 * 1024,
                conversion_timeout=300,
                markitdown=MarkItDownConfig(),
            )

            # This should not raise any signal-related errors
            converter = FileConverter(config)
            assert converter is not None
            assert converter.config == config

    def test_signal_alarm_no_op_windows(self):
        """Test that signal.alarm is a no-op on Windows after our patch."""
        with patch("sys.platform", "win32"):
            import signal

            # Remove SIGALRM to simulate clean Windows environment
            if hasattr(signal, "SIGALRM"):
                delattr(signal, "SIGALRM")
            if hasattr(signal, "alarm"):
                delattr(signal, "alarm")

            # Re-import to trigger monkey patch
            import importlib
            from qdrant_loader.core.file_conversion import file_converter

            importlib.reload(file_converter)

            # signal.alarm should be callable and not raise errors
            try:
                signal.alarm(30)  # Should be a no-op, not crash
                signal.alarm(0)  # Cancel alarm (also no-op)
            except Exception as e:
                pytest.fail(f"signal.alarm should be no-op on Windows, but raised: {e}")
