"""Tests for openpyxl warning capture functionality."""

import warnings
from unittest.mock import Mock

from qdrant_loader.core.file_conversion.file_converter import capture_openpyxl_warnings


class TestWarningCapture:
    """Test openpyxl warning capture functionality."""

    def test_capture_openpyxl_data_validation_warning(self):
        """Test that Data Validation warnings are captured and logged."""
        mock_logger = Mock()
        file_path = "/test/file.xlsx"

        with capture_openpyxl_warnings(mock_logger, file_path):
            # Simulate an openpyxl Data Validation warning by calling the handler directly
            warnings.showwarning(
                "Data Validation extension is not supported and will be removed",
                UserWarning,
                "/path/to/openpyxl/worksheet/_reader.py",
                329,
            )

        # Verify the warning was logged through our system
        mock_logger.info.assert_any_call(
            "Excel feature not fully supported during conversion",
            file_path=file_path,
            feature_type="Data Validation",
            source="openpyxl",
        )

        # Verify summary was logged
        mock_logger.info.assert_any_call(
            "Excel conversion completed with unsupported features",
            file_path=file_path,
            total_warnings=1,
            warning_types=["Data Validation"],
            source="openpyxl",
        )

    def test_capture_openpyxl_conditional_formatting_warning(self):
        """Test that Conditional Formatting warnings are captured and logged."""
        mock_logger = Mock()
        file_path = "/test/file.xlsx"

        with capture_openpyxl_warnings(mock_logger, file_path):
            # Simulate an openpyxl Conditional Formatting warning
            warnings.showwarning(
                "Conditional Formatting extension is not supported and will be removed",
                UserWarning,
                "/path/to/openpyxl/worksheet/_reader.py",
                329,
            )

        # Verify the warning was logged through our system
        mock_logger.info.assert_any_call(
            "Excel feature not fully supported during conversion",
            file_path=file_path,
            feature_type="Conditional Formatting",
            source="openpyxl",
        )

    def test_capture_multiple_warnings(self):
        """Test that multiple warnings are captured and summarized correctly."""
        mock_logger = Mock()
        file_path = "/test/file.xlsx"

        with capture_openpyxl_warnings(mock_logger, file_path):
            # Simulate multiple openpyxl warnings
            warnings.showwarning(
                "Data Validation extension is not supported and will be removed",
                UserWarning,
                "/path/to/openpyxl/worksheet/_reader.py",
                329,
            )
            warnings.showwarning(
                "Conditional Formatting extension is not supported and will be removed",
                UserWarning,
                "/path/to/openpyxl/worksheet/_reader.py",
                329,
            )
            warnings.showwarning(
                "Data Validation extension is not supported and will be removed",
                UserWarning,
                "/path/to/openpyxl/worksheet/_reader.py",
                329,
            )

        # Verify individual warnings were logged
        assert mock_logger.info.call_count >= 3  # 3 individual + 1 summary

        # Verify summary includes both types and correct count
        summary_call = None
        for call in mock_logger.info.call_args_list:
            if "Excel conversion completed with unsupported features" in str(call):
                summary_call = call
                break

        assert summary_call is not None
        args, kwargs = summary_call
        assert kwargs["total_warnings"] == 3
        assert set(kwargs["warning_types"]) == {
            "Data Validation",
            "Conditional Formatting",
        }

    def test_non_openpyxl_warnings_not_captured(self):
        """Test that non-openpyxl warnings are not captured by our handler."""
        mock_logger = Mock()
        file_path = "/test/file.xlsx"

        original_handler = warnings.showwarning

        with capture_openpyxl_warnings(mock_logger, file_path):
            # Simulate a non-openpyxl warning
            warnings.showwarning(
                "Some other warning", UserWarning, "/path/to/other/module.py", 100
            )

        # Verify our logger was not called
        mock_logger.info.assert_not_called()

    def test_warning_handler_restoration(self):
        """Test that the original warning handler is properly restored."""
        mock_logger = Mock()
        file_path = "/test/file.xlsx"

        original_handler = warnings.showwarning

        with capture_openpyxl_warnings(mock_logger, file_path):
            # Inside the context, handler should be different
            assert warnings.showwarning != original_handler

        # After the context, handler should be restored
        assert warnings.showwarning == original_handler

    def test_no_warnings_no_summary(self):
        """Test that no summary is logged when no warnings are captured."""
        mock_logger = Mock()
        file_path = "/test/file.xlsx"

        with capture_openpyxl_warnings(mock_logger, file_path):
            # No warnings triggered
            pass

        # Verify no logging occurred
        mock_logger.info.assert_not_called()
