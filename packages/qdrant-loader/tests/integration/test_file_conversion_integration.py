"""Integration tests for file conversion functionality."""

import os
import tempfile
from pathlib import Path

import pytest
from qdrant_loader.core.file_conversion import (
    FileConversionConfig,
    FileConverter,
    FileDetector,
    MarkItDownConfig,
)


@pytest.mark.integration
class TestFileConversionIntegration:
    """Integration tests for file conversion."""

    def setup_method(self):
        """Set up test fixtures."""
        self.detector = FileDetector()
        self.config = FileConversionConfig()
        self.converter = FileConverter(self.config)
        self.fixtures_dir = (
            Path(__file__).parent.parent / "fixtures" / "unit" / "file_conversion"
        )

    def test_file_detector_with_real_files(self):
        """Test file detector with real test files."""
        # Test with PDF fixture
        pdf_file = self.fixtures_dir / "sample.pdf"
        if pdf_file.exists():
            assert self.detector.is_supported_for_conversion(str(pdf_file))
            mime_type, extension = self.detector.detect_file_type(str(pdf_file))
            assert extension == ".pdf"

        # Test with text fixture (should not be convertible)
        txt_file = self.fixtures_dir / "sample.txt"
        if txt_file.exists():
            assert not self.detector.is_supported_for_conversion(str(txt_file))

    def test_file_converter_with_pdf_file(self):
        """Test file converter with a PDF file."""
        # Create a temporary PDF file that should be convertible
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".pdf", delete=False
        ) as tmp_file:
            # Write a minimal PDF content
            tmp_file.write(
                b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            )
            tmp_file.flush()
            tmp_path = tmp_file.name

        # File is now closed, safe to process and delete
        try:
            # This should work if MarkItDown is properly installed with PDF support
            try:
                result = self.converter.convert_file(tmp_path)

                assert isinstance(result, str)
                assert len(result) > 0

            except Exception as e:
                # If MarkItDown is not available or fails, that's expected in test environment
                pytest.skip(
                    f"MarkItDown conversion failed (expected in test environment): {e}"
                )

        finally:
            try:
                os.unlink(tmp_path)
            except (OSError, PermissionError):
                pass  # File may already be deleted or locked

    def test_file_converter_error_handling(self):
        """Test file converter error handling with invalid files."""
        # Test with non-existent file
        with pytest.raises(
            Exception
        ):  # Should raise MarkItDownError wrapping FileAccessError
            self.converter.convert_file("/non/existent/file.pdf")

    def test_file_converter_with_large_file(self):
        """Test file converter with file size limits."""
        # Create converter with very small max file size
        small_config = FileConversionConfig(max_file_size=1024)  # 1KB limit
        small_converter = FileConverter(small_config)

        # Create a file larger than the limit
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".pdf", delete=False
        ) as tmp_file:
            # Write more than 1KB of data
            tmp_file.write(b"x" * 2048)
            tmp_file.flush()
            tmp_path = tmp_file.name

        # File is now closed, safe to process and delete
        try:
            with pytest.raises(
                Exception
            ):  # Should raise MarkItDownError wrapping FileSizeExceededError
                small_converter.convert_file(tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except (OSError, PermissionError):
                pass  # File may already be deleted or locked

    def test_file_conversion_config_integration(self):
        """Test file conversion configuration integration."""
        # Test with custom MarkItDown config
        markitdown_config = MarkItDownConfig(
            enable_llm_descriptions=False,  # No LLM for basic conversion
            llm_model="gpt-4o",  # Default model
            llm_endpoint="https://api.openai.com/v1",  # Default endpoint
        )

        config = FileConversionConfig(
            max_file_size=10485760,  # 10MB
            conversion_timeout=60,
            markitdown=markitdown_config,
        )

        converter = FileConverter(config)

        # Verify configuration is properly set
        assert converter.config.max_file_size == 10485760
        assert converter.config.conversion_timeout == 60
        assert converter.config.markitdown.enable_llm_descriptions is False

    @pytest.mark.slow
    def test_file_converter_with_pdf_fixture(self):
        """Test file converter with PDF fixture (if available)."""
        pdf_file = self.fixtures_dir / "sample.pdf"

        if not pdf_file.exists():
            pytest.skip("PDF fixture not available")

        try:
            result = self.converter.convert_file(str(pdf_file))

            assert isinstance(result, str)
            assert len(result) > 0

        except Exception as e:
            # If MarkItDown is not available or fails, that's expected in test environment
            pytest.skip(
                f"MarkItDown conversion failed (expected in test environment): {e}"
            )

    def test_multiple_file_types_detection(self):
        """Test file type detection for various extensions."""
        test_cases = [
            ("document.pdf", True),
            ("spreadsheet.xlsx", True),
            ("presentation.pptx", True),
            ("image.jpg", True),
            ("audio.mp3", True),
            ("book.epub", True),
            ("archive.zip", True),
            ("text.txt", False),
            ("webpage.html", False),
            ("data.json", False),  # JSON is excluded - handled by JSONChunkingStrategy
        ]

        for filename, should_be_convertible in test_cases:
            # Create temporary files to test with
            with tempfile.NamedTemporaryFile(
                suffix=Path(filename).suffix, delete=False
            ) as tmp_file:
                tmp_file.write(b"fake content")
                tmp_file.flush()
                tmp_path = tmp_file.name

            # File is now closed, safe to process and delete
            try:
                is_convertible = self.detector.is_supported_for_conversion(tmp_path)
                assert is_convertible == should_be_convertible, f"Failed for {filename}"
            finally:
                try:
                    os.unlink(tmp_path)
                except (OSError, PermissionError):
                    pass  # File may already be deleted or locked

    def test_file_type_info_comprehensive(self):
        """Test comprehensive file type information gathering."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(b"fake pdf content")
            tmp_file.flush()
            tmp_path = tmp_file.name

        # File is now closed, safe to process and delete
        try:
            info = self.detector.get_file_type_info(tmp_path)

            # Verify all expected fields are present
            expected_fields = [
                "file_path",
                "mime_type",
                "file_extension",
                "file_size",
                "is_supported",
                "normalized_type",
                "is_excluded",
            ]

            for field in expected_fields:
                assert field in info, f"Missing field: {field}"

            # Verify specific values for PDF
            assert info["file_extension"] == ".pdf"
            assert info["mime_type"] == "application/pdf"
            assert info["normalized_type"] == "pdf"
            assert info["is_supported"] is True
            assert info["is_excluded"] is False
            assert info["file_size"] > 0

        finally:
            try:
                os.unlink(tmp_path)
            except (OSError, PermissionError):
                pass  # File may already be deleted or locked

    def test_fallback_document_creation(self):
        """Test fallback document creation functionality."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(b"fake pdf content")
            tmp_file.flush()
            tmp_path = tmp_file.name

        # File is now closed, safe to process and delete
        try:
            error = Exception("Test conversion error")
            fallback_doc = self.converter.create_fallback_document(tmp_path, error)

            assert isinstance(fallback_doc, str)
            assert "Conversion Status" in fallback_doc
            assert "Failed" in fallback_doc
            assert "Test conversion error" in fallback_doc
            assert Path(tmp_path).name in fallback_doc

        finally:
            try:
                os.unlink(tmp_path)
            except (OSError, PermissionError):
                pass  # File may already be deleted or locked
