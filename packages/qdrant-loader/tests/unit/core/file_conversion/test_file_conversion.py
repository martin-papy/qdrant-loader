"""Tests for file conversion infrastructure."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from qdrant_loader.core.file_conversion import (
    ConnectorFileConversionConfig,
    ConversionTimeoutError,
    FileAccessError,
    FileConversionConfig,
    FileConversionError,
    FileConverter,
    FileDetector,
    FileSizeExceededError,
    MarkItDownConfig,
    MarkItDownError,
    UnsupportedFileTypeError,
)


class TestFileDetector:
    """Test cases for FileDetector class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.detector = FileDetector()

    def test_is_supported_for_conversion_pdf(self):
        """Test PDF file detection."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(b"fake pdf content")
            tmp_file.flush()

            try:
                assert self.detector.is_supported_for_conversion(tmp_file.name)
            finally:
                os.unlink(tmp_file.name)

    def test_is_supported_for_conversion_office_docs(self):
        """Test Office document detection."""
        test_files = [
            ("document.docx", True),
            ("document.doc", True),
            ("spreadsheet.xlsx", True),
            ("spreadsheet.xls", True),
            ("presentation.pptx", True),
            ("presentation.ppt", True),
        ]

        for filename, expected in test_files:
            with tempfile.NamedTemporaryFile(
                suffix=Path(filename).suffix, delete=False
            ) as tmp_file:
                tmp_file.write(b"fake content")
                tmp_file.flush()

                try:
                    result = self.detector.is_supported_for_conversion(tmp_file.name)
                    assert result == expected, f"Failed for {filename}"
                finally:
                    os.unlink(tmp_file.name)

    def test_is_supported_for_conversion_excluded_types(self):
        """Test that excluded file types return False."""
        excluded_files = [
            "document.txt",
            "document.md",
            "document.html",
            "document.htm",
        ]

        for filename in excluded_files:
            with tempfile.NamedTemporaryFile(
                suffix=Path(filename).suffix, delete=False
            ) as tmp_file:
                tmp_file.write(b"fake content")
                tmp_file.flush()

                try:
                    assert not self.detector.is_supported_for_conversion(
                        tmp_file.name
                    ), f"Should exclude {filename}"
                finally:
                    os.unlink(tmp_file.name)

    def test_detect_file_type(self):
        """Test file type detection."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(b"fake pdf content")
            tmp_file.flush()

            try:
                mime_type, extension = self.detector.detect_file_type(tmp_file.name)
                assert mime_type == "application/pdf"
                assert extension == ".pdf"
            finally:
                os.unlink(tmp_file.name)

    def test_get_file_type_info(self):
        """Test comprehensive file type information."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(b"fake pdf content")
            tmp_file.flush()

            try:
                info = self.detector.get_file_type_info(tmp_file.name)

                assert info["file_path"] == tmp_file.name
                assert info["mime_type"] == "application/pdf"
                assert info["file_extension"] == ".pdf"
                assert info["file_size"] > 0
                assert info["is_supported"] is True
                assert info["normalized_type"] == "pdf"
                assert info["is_excluded"] is False
            finally:
                os.unlink(tmp_file.name)

    @patch("mimetypes.guess_type")
    def test_detect_file_type_mime_fallback(self, mock_guess_type):
        """Test MIME type detection fallback."""
        mock_guess_type.return_value = ("application/pdf", None)

        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(b"fake content")
            tmp_file.flush()

            try:
                mime_type, extension = self.detector.detect_file_type(tmp_file.name)
                assert mime_type == "application/pdf"
                mock_guess_type.assert_called_once_with(tmp_file.name)
            finally:
                os.unlink(tmp_file.name)


class TestFileConversionConfig:
    """Test cases for FileConversionConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = FileConversionConfig()

        assert config.max_file_size == 52428800  # 50MB in bytes
        assert config.conversion_timeout == 300
        assert config.markitdown is not None
        assert isinstance(config.markitdown, MarkItDownConfig)

    def test_custom_config(self):
        """Test custom configuration values."""
        markitdown_config = MarkItDownConfig(
            enable_llm_descriptions=True,
            llm_model="gpt-4",
            llm_endpoint="https://api.openai.com/v1",
        )

        config = FileConversionConfig(
            max_file_size=104857600,  # 100MB
            conversion_timeout=600,
            markitdown=markitdown_config,
        )

        assert config.max_file_size == 104857600
        assert config.conversion_timeout == 600
        assert config.markitdown.enable_llm_descriptions is True
        assert config.markitdown.llm_model == "gpt-4"

    def test_get_max_file_size_mb(self):
        """Test file size conversion to MB."""
        config = FileConversionConfig(max_file_size=52428800)  # 50MB
        assert config.get_max_file_size_mb() == 50.0

    def test_is_file_size_allowed(self):
        """Test file size validation."""
        config = FileConversionConfig(max_file_size=1024)  # 1KB

        assert config.is_file_size_allowed(512) is True  # 512 bytes
        assert config.is_file_size_allowed(1024) is True  # Exactly 1KB
        assert config.is_file_size_allowed(2048) is False  # 2KB


class TestMarkItDownConfig:
    """Test cases for MarkItDownConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = MarkItDownConfig()

        assert config.enable_llm_descriptions is False
        assert config.llm_model == "gpt-4o"
        assert config.llm_endpoint == "https://api.openai.com/v1"

    def test_custom_config(self):
        """Test custom configuration values."""
        config = MarkItDownConfig(
            enable_llm_descriptions=True,
            llm_model="gpt-4",
            llm_endpoint="https://custom.api.com/v1",
        )

        assert config.enable_llm_descriptions is True
        assert config.llm_model == "gpt-4"
        assert config.llm_endpoint == "https://custom.api.com/v1"


class TestConnectorFileConversionConfig:
    """Test cases for ConnectorFileConversionConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ConnectorFileConversionConfig()

        assert config.enable_file_conversion is False
        assert config.download_attachments is None

    def test_custom_config(self):
        """Test custom configuration values."""
        config = ConnectorFileConversionConfig(
            enable_file_conversion=True, download_attachments=True
        )

        assert config.enable_file_conversion is True
        assert config.download_attachments is True

    def test_should_download_attachments(self):
        """Test attachment download logic."""
        # Default case
        config = ConnectorFileConversionConfig()
        assert config.should_download_attachments() is False

        # Explicitly enabled
        config = ConnectorFileConversionConfig(download_attachments=True)
        assert config.should_download_attachments() is True

        # Explicitly disabled
        config = ConnectorFileConversionConfig(download_attachments=False)
        assert config.should_download_attachments() is False


class TestFileConverter:
    """Test cases for FileConverter class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = FileConversionConfig()
        self.converter = FileConverter(self.config)

    def test_init_with_config(self):
        """Test FileConverter initialization with config."""
        assert self.converter.config == self.config
        assert self.converter._markitdown is None  # Lazy loading

    def test_get_markitdown_lazy_loading(self):
        """Test lazy loading of MarkItDown instance."""
        with patch("markitdown.MarkItDown") as mock_markitdown_class:
            mock_instance = Mock()
            mock_markitdown_class.return_value = mock_instance

            # First access should create the instance
            markitdown = self.converter._get_markitdown()
            assert markitdown == mock_instance
            mock_markitdown_class.assert_called_once()

            # Second access should return the same instance
            markitdown2 = self.converter._get_markitdown()
            assert markitdown2 == mock_instance
            assert mock_markitdown_class.call_count == 1

    def test_validate_file_size_valid(self):
        """Test file size validation with valid file."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            # Write small amount of data
            tmp_file.write(b"x" * 1024)  # 1KB
            tmp_file.flush()

            try:
                # Should not raise exception
                self.converter._validate_file(tmp_file.name)
            finally:
                os.unlink(tmp_file.name)

    def test_validate_file_size_too_large(self):
        """Test file size validation with oversized file."""
        # Create converter with small max file size
        config = FileConversionConfig(max_file_size=1024)  # 1KB
        converter = FileConverter(config)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            # Write 2KB of data
            tmp_file.write(b"x" * 2048)
            tmp_file.flush()

            try:
                with pytest.raises(FileSizeExceededError) as exc_info:
                    converter._validate_file(tmp_file.name)

                assert "exceeds maximum allowed size" in str(exc_info.value)
                assert exc_info.value.file_size == 2048
                assert exc_info.value.max_size == 1024
            finally:
                os.unlink(tmp_file.name)

    def test_validate_file_not_found(self):
        """Test file validation with non-existent file."""
        with pytest.raises(FileAccessError) as exc_info:
            self.converter._validate_file("/non/existent/file.pdf")

        assert "Cannot access file" in str(exc_info.value)
        assert "File does not exist" in str(exc_info.value)

    def test_validate_file_not_readable(self):
        """Test file validation with unreadable file."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(b"test content")
            tmp_file.flush()

            try:
                # Remove read permissions
                os.chmod(tmp_file.name, 0o000)

                with pytest.raises(FileAccessError) as exc_info:
                    self.converter._validate_file(tmp_file.name)

                assert "Cannot access file" in str(exc_info.value)
                assert "File is not readable" in str(exc_info.value)
            finally:
                # Restore permissions and delete
                os.chmod(tmp_file.name, 0o644)
                os.unlink(tmp_file.name)

    def test_validate_file_unsupported_type(self):
        """Test file validation with unsupported file type."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp_file:
            tmp_file.write(b"test content")
            tmp_file.flush()

            try:
                with pytest.raises(UnsupportedFileTypeError) as exc_info:
                    self.converter._validate_file(tmp_file.name)

                assert "is not supported for conversion" in str(exc_info.value)
            finally:
                os.unlink(tmp_file.name)

    def test_convert_file_success(self):
        """Test successful file conversion."""
        with patch("markitdown.MarkItDown") as mock_markitdown_class:
            # Setup mock
            mock_instance = Mock()
            mock_markitdown_class.return_value = mock_instance
            mock_result = Mock()
            mock_result.text_content = (
                "# Converted Content\n\nThis is the converted text."
            )
            mock_instance.convert.return_value = mock_result

            # Create test file
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
                tmp_file.write(b"fake pdf content")
                tmp_file.flush()

                try:
                    result = self.converter.convert_file(tmp_file.name)

                    assert (
                        result == "# Converted Content\n\nThis is the converted text."
                    )
                    mock_instance.convert.assert_called_once_with(tmp_file.name)
                finally:
                    os.unlink(tmp_file.name)

    def test_convert_file_markitdown_error(self):
        """Test file conversion with MarkItDown error."""
        with patch("markitdown.MarkItDown") as mock_markitdown_class:
            # Setup mock to raise exception
            mock_instance = Mock()
            mock_markitdown_class.return_value = mock_instance
            mock_instance.convert.side_effect = Exception(
                "MarkItDown conversion failed"
            )

            # Create test file
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
                tmp_file.write(b"fake pdf content")
                tmp_file.flush()

                try:
                    with pytest.raises(MarkItDownError) as exc_info:
                        self.converter.convert_file(tmp_file.name)

                    assert "MarkItDown conversion failed" in str(exc_info.value)
                    assert tmp_file.name in str(exc_info.value.file_path)
                finally:
                    os.unlink(tmp_file.name)

    def test_convert_file_not_found(self):
        """Test file conversion with non-existent file."""
        with pytest.raises(MarkItDownError) as exc_info:
            self.converter.convert_file("/non/existent/file.pdf")

        # The FileAccessError gets wrapped in MarkItDownError
        assert "MarkItDown conversion failed" in str(exc_info.value)

    def test_create_fallback_document(self):
        """Test fallback document creation."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(b"fake pdf content")
            tmp_file.flush()

            try:
                error_msg = Exception("Test conversion error")
                result = self.converter.create_fallback_document(
                    tmp_file.name, error_msg
                )

                assert isinstance(result, str)
                assert "Conversion Status" in result
                assert "Failed" in result
                assert "Test conversion error" in result
                assert Path(tmp_file.name).name in result
            finally:
                os.unlink(tmp_file.name)


class TestFileConversionExceptions:
    """Test cases for file conversion exceptions."""

    def test_file_conversion_error_base(self):
        """Test base FileConversionError exception."""
        error = FileConversionError("Test error", "/path/to/file.pdf", "pdf")

        assert str(error) == "Test error"
        assert error.file_path == "/path/to/file.pdf"
        assert error.file_type == "pdf"

    def test_unsupported_file_type_error(self):
        """Test UnsupportedFileTypeError exception."""
        error = UnsupportedFileTypeError("xyz", "/path/to/file.xyz")

        assert "File type 'xyz' is not supported for conversion" in str(error)
        assert error.file_path == "/path/to/file.xyz"
        assert error.file_type == "xyz"

    def test_file_size_exceeded_error(self):
        """Test FileSizeExceededError exception."""
        error = FileSizeExceededError(2048, 1024, "/path/to/file.pdf")

        assert "exceeds maximum allowed size" in str(error)
        assert "2048 bytes" in str(error)
        assert "1024 bytes" in str(error)
        assert error.file_path == "/path/to/file.pdf"
        assert error.file_size == 2048
        assert error.max_size == 1024

    def test_conversion_timeout_error(self):
        """Test ConversionTimeoutError exception."""
        error = ConversionTimeoutError(300, "/path/to/file.pdf")

        assert "timed out after 300 seconds" in str(error)
        assert error.file_path == "/path/to/file.pdf"
        assert error.timeout == 300

    def test_markitdown_error(self):
        """Test MarkItDownError exception."""
        original_error = Exception("Original error")
        error = MarkItDownError(original_error, "/path/to/file.pdf", "pdf")

        assert "MarkItDown conversion failed" in str(error)
        assert "Original error" in str(error)
        assert error.file_path == "/path/to/file.pdf"
        assert error.file_type == "pdf"
        assert error.original_error == original_error

    def test_file_access_error(self):
        """Test FileAccessError exception."""
        error = FileAccessError("/path/to/file.pdf")

        assert "Cannot access file: /path/to/file.pdf" in str(error)
        assert error.file_path == "/path/to/file.pdf"

    def test_file_access_error_with_original(self):
        """Test FileAccessError with original exception."""
        original_error = OSError("Permission denied")
        error = FileAccessError("/path/to/file.pdf", original_error)

        assert "Cannot access file: /path/to/file.pdf" in str(error)
        assert "Permission denied" in str(error)
        assert error.original_error == original_error
