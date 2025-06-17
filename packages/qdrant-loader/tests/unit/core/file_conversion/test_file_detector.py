"""
Extended unit tests for the file detector to improve coverage.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from qdrant_loader.core.file_conversion.file_detector import FileDetector


@pytest.fixture
def file_detector():
    """Create a file detector instance."""
    return FileDetector()


class TestFileDetectorInitialization:
    """Test file detector initialization."""

    def test_initialization(self, file_detector):
        """Test that file detector initializes correctly."""
        assert file_detector is not None
        assert hasattr(file_detector, "SUPPORTED_MIME_TYPES")
        assert hasattr(file_detector, "EXCLUDED_EXTENSIONS")
        assert len(file_detector.SUPPORTED_MIME_TYPES) > 0
        assert len(file_detector.EXCLUDED_EXTENSIONS) > 0

    def test_custom_mime_types_added(self, file_detector):
        """Test that custom MIME types are added during initialization."""
        # This tests the _add_custom_mime_types method indirectly
        import mimetypes

        # Check that some custom types were added
        docx_type, _ = mimetypes.guess_type("test.docx")
        assert (
            docx_type
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )


class TestFileTypeDetection:
    """Test file type detection functionality."""

    def test_detect_file_type_pdf(self, file_detector):
        """Test file type detection for PDF files."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"%PDF-1.4")  # PDF header

        try:
            mime_type, extension = file_detector.detect_file_type(str(temp_path))
            assert mime_type == "application/pdf"
            assert extension == ".pdf"
        finally:
            temp_path.unlink(missing_ok=True)

    def test_detect_file_type_docx(self, file_detector):
        """Test file type detection for DOCX files."""
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            # DOCX files are ZIP archives with specific structure
            temp_file.write(b"PK\x03\x04")  # ZIP header

        try:
            mime_type, extension = file_detector.detect_file_type(str(temp_path))
            # Should detect as DOCX based on extension
            assert (
                mime_type
                == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            assert extension == ".docx"
        finally:
            temp_path.unlink(missing_ok=True)

    def test_detect_file_type_nonexistent_file(self, file_detector):
        """Test file type detection for nonexistent file."""
        mime_type, extension = file_detector.detect_file_type(
            "/path/to/nonexistent/file.pdf"
        )
        # Should return None for MIME type but still extract extension
        assert mime_type is None
        assert extension == ".pdf"

    def test_detect_file_type_no_extension(self, file_detector):
        """Test file type detection for file without extension."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"Some content")

        try:
            mime_type, extension = file_detector.detect_file_type(str(temp_path))
            # Extension should be empty
            assert extension == ""
            # MIME type might be detected or None
            assert mime_type is None or isinstance(mime_type, str)
        finally:
            temp_path.unlink(missing_ok=True)


class TestMimeTypeDetection:
    """Test internal MIME type detection."""

    def test_detect_mime_type_existing_file(self, file_detector):
        """Test MIME type detection for existing file."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"This is a plain text file.")

        try:
            mime_type = file_detector._detect_mime_type(str(temp_path))
            assert mime_type == "text/plain"
        finally:
            temp_path.unlink(missing_ok=True)

    def test_detect_mime_type_nonexistent_file(self, file_detector):
        """Test MIME type detection for nonexistent file."""
        mime_type = file_detector._detect_mime_type("/path/to/nonexistent/file.pdf")
        assert mime_type is None

    def test_detect_mime_type_permission_error(self, file_detector):
        """Test MIME type detection with permission error."""
        with patch("os.path.exists") as mock_exists, patch("os.access") as mock_access:

            mock_exists.return_value = True
            mock_access.return_value = False  # No read permission

            mime_type = file_detector._detect_mime_type("/path/to/restricted/file.pdf")
            assert mime_type is None

    def test_detect_mime_type_os_error(self, file_detector):
        """Test MIME type detection with OS error."""
        with patch("os.path.exists") as mock_exists:
            mock_exists.side_effect = OSError("OS error")

            mime_type = file_detector._detect_mime_type("/path/to/file.pdf")
            assert mime_type is None


class TestSupportedForConversion:
    """Test supported file conversion checking."""

    def test_is_supported_for_conversion_pdf(self, file_detector):
        """Test checking if PDF file is supported for conversion."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"%PDF-1.4")

        try:
            assert file_detector.is_supported_for_conversion(str(temp_path)) is True
        finally:
            temp_path.unlink(missing_ok=True)

    def test_is_supported_for_conversion_docx(self, file_detector):
        """Test checking if DOCX file is supported for conversion."""
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"PK\x03\x04")  # ZIP header

        try:
            assert file_detector.is_supported_for_conversion(str(temp_path)) is True
        finally:
            temp_path.unlink(missing_ok=True)

    def test_is_supported_for_conversion_excluded_html(self, file_detector):
        """Test that HTML files are excluded from conversion."""
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"<html><body>Test</body></html>")

        try:
            assert file_detector.is_supported_for_conversion(str(temp_path)) is False
        finally:
            temp_path.unlink(missing_ok=True)

    def test_is_supported_for_conversion_excluded_markdown(self, file_detector):
        """Test that Markdown files are excluded from conversion."""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"# Test Markdown")

        try:
            assert file_detector.is_supported_for_conversion(str(temp_path)) is False
        finally:
            temp_path.unlink(missing_ok=True)

    def test_is_supported_for_conversion_excluded_json(self, file_detector):
        """Test that JSON files are excluded from conversion (handled by JSONChunkingStrategy)."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b'{"test": "data"}')

        try:
            assert file_detector.is_supported_for_conversion(str(temp_path)) is False
        finally:
            temp_path.unlink(missing_ok=True)

    def test_is_supported_for_conversion_unsupported_extension(self, file_detector):
        """Test that unsupported file types are not supported for conversion."""
        with tempfile.NamedTemporaryFile(suffix=".unknown", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"Unknown file content")

        try:
            result = file_detector.is_supported_for_conversion(str(temp_path))
            # Should be False since .unknown is not a supported extension
            assert result is False
        finally:
            temp_path.unlink(missing_ok=True)

    def test_is_supported_for_conversion_by_extension_fallback(self, file_detector):
        """Test that files are supported by extension fallback when MIME detection fails."""
        # Create a file with supported extension but no MIME type detection
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"Not a real PDF")  # Invalid PDF content

        try:
            # Mock MIME type detection to fail
            with patch.object(file_detector, "_detect_mime_type") as mock_detect:
                mock_detect.return_value = None

                result = file_detector.is_supported_for_conversion(str(temp_path))
                # Should still be True due to extension fallback
                assert result is True
        finally:
            temp_path.unlink(missing_ok=True)


class TestSupportedFormats:
    """Test supported format constants and methods."""

    def test_supported_mime_types_not_empty(self, file_detector):
        """Test that supported MIME types list is not empty."""
        assert len(file_detector.SUPPORTED_MIME_TYPES) > 0

    def test_excluded_extensions_not_empty(self, file_detector):
        """Test that excluded extensions list is not empty."""
        assert len(file_detector.EXCLUDED_EXTENSIONS) > 0

    def test_supported_mime_types_include_common_formats(self, file_detector):
        """Test that supported MIME types include common formats."""
        common_types = [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ]

        for mime_type in common_types:
            assert mime_type in file_detector.SUPPORTED_MIME_TYPES

    def test_excluded_extensions_include_common_formats(self, file_detector):
        """Test that excluded extensions include common formats."""
        common_excluded = [".html", ".htm", ".md", ".markdown", ".txt", ".json"]

        for extension in common_excluded:
            assert extension in file_detector.EXCLUDED_EXTENSIONS

    def test_get_supported_extensions_class_method(self, file_detector):
        """Test the get_supported_extensions class method."""
        extensions = FileDetector.get_supported_extensions()
        assert isinstance(extensions, set)
        assert len(extensions) > 0
        assert ".pdf" in extensions  # Extensions include the dot
        assert ".docx" in extensions

    def test_get_supported_mime_types_class_method(self, file_detector):
        """Test the get_supported_mime_types class method."""
        mime_types = FileDetector.get_supported_mime_types()
        assert isinstance(mime_types, set)
        assert len(mime_types) > 0
        assert "application/pdf" in mime_types


class TestErrorHandling:
    """Test error handling in file detection."""

    def test_detect_file_type_exception_handling(self, file_detector):
        """Test that detect_file_type handles exceptions gracefully."""
        # Test with a scenario that actually causes an exception in the method
        with patch.object(file_detector, "_detect_mime_type") as mock_detect:
            mock_detect.side_effect = Exception("Detection error")

            # This should trigger the exception handling in detect_file_type
            mime_type, extension = file_detector.detect_file_type("/some/path.pdf")
            # When any exception occurs, the method returns (None, None)
            assert mime_type is None
            assert extension is None

    def test_is_supported_for_conversion_exception_handling(self, file_detector):
        """Test that is_supported_for_conversion handles exceptions gracefully."""
        # Test with a scenario where detect_file_type fails completely
        with patch.object(file_detector, "detect_file_type") as mock_detect:
            mock_detect.return_value = (None, None)  # Simulate complete failure

            # Should return False when detection completely fails
            result = file_detector.is_supported_for_conversion("/path/to/document.pdf")
            assert result is False


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_file_path(self, file_detector):
        """Test handling of empty file path."""
        mime_type, extension = file_detector.detect_file_type("")
        # Should handle gracefully - empty path has empty extension
        assert mime_type is None
        assert extension == ""

    def test_very_long_file_path(self, file_detector):
        """Test handling of very long file path."""
        long_path = "/very/long/path/" + "a" * 1000 + ".pdf"
        mime_type, extension = file_detector.detect_file_type(long_path)
        # Should handle gracefully and detect extension
        assert extension == ".pdf"

    def test_file_path_with_special_characters(self, file_detector):
        """Test handling of file path with special characters."""
        special_path = "/path/with spaces/and-dashes/file (1).pdf"
        mime_type, extension = file_detector.detect_file_type(special_path)
        # Should detect extension correctly
        assert extension == ".pdf"

    def test_file_path_with_unicode(self, file_detector):
        """Test handling of file path with Unicode characters."""
        unicode_path = "/path/with/unicode/文档.pdf"
        mime_type, extension = file_detector.detect_file_type(unicode_path)
        # Should detect extension correctly
        assert extension == ".pdf"

    def test_file_with_multiple_extensions(self, file_detector):
        """Test handling of file with multiple extensions."""
        multi_ext_path = "/path/to/file.tar.gz"
        mime_type, extension = file_detector.detect_file_type(multi_ext_path)
        # Should get the last extension
        assert extension == ".gz"

    def test_hidden_file_with_extension(self, file_detector):
        """Test handling of hidden file with extension."""
        hidden_path = "/path/to/.hidden.pdf"
        mime_type, extension = file_detector.detect_file_type(hidden_path)
        # Should detect extension correctly
        assert extension == ".pdf"

    def test_case_insensitive_extension(self, file_detector):
        """Test that extension detection is case insensitive."""
        upper_path = "/path/to/document.PDF"
        mime_type, extension = file_detector.detect_file_type(upper_path)
        # Should normalize to lowercase
        assert extension == ".pdf"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
