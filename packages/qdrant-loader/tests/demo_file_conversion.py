#!/usr/bin/env python3
"""
Demo script showing file conversion functionality.

This script demonstrates how to use the file conversion infrastructure
we've built for the qdrant-loader project.
"""

import tempfile
import os
from pathlib import Path

from qdrant_loader.core.file_conversion import (
    FileConverter,
    FileDetector,
    FileConversionConfig,
    MarkItDownConfig,
)


def demo_file_detection():
    """Demonstrate file type detection capabilities."""
    print("=== File Detection Demo ===")

    detector = FileDetector()

    # Test various file types
    test_files = [
        ("document.pdf", "PDF document"),
        ("spreadsheet.xlsx", "Excel spreadsheet"),
        ("presentation.pptx", "PowerPoint presentation"),
        ("image.jpg", "JPEG image"),
        ("audio.mp3", "MP3 audio"),
        ("book.epub", "EPUB book"),
        ("archive.zip", "ZIP archive"),
        ("data.json", "JSON data"),
        ("text.txt", "Plain text (excluded)"),
        ("webpage.html", "HTML page (excluded)"),
        ("document.md", "Markdown (excluded)"),
    ]

    for filename, description in test_files:
        # Create temporary file to test with
        with tempfile.NamedTemporaryFile(
            suffix=Path(filename).suffix, delete=False
        ) as tmp_file:
            tmp_file.write(b"fake content for testing")
            tmp_file.flush()

            try:
                is_supported = detector.is_supported_for_conversion(tmp_file.name)
                file_info = detector.get_file_type_info(tmp_file.name)

                status = "✅ Supported" if is_supported else "❌ Not supported"
                print(f"{filename:20} ({description:25}) - {status}")
                print(f"  MIME type: {file_info['mime_type']}")
                print(f"  Normalized type: {file_info['normalized_type']}")
                print(f"  Is excluded: {file_info['is_excluded']}")
                print()

            finally:
                os.unlink(tmp_file.name)


def demo_file_conversion():
    """Demonstrate file conversion capabilities."""
    print("=== File Conversion Demo ===")

    # Create configuration
    config = FileConversionConfig(
        max_file_size=1024 * 1024,  # 1MB limit for demo
        conversion_timeout=30,  # 30 seconds timeout
        markitdown=MarkItDownConfig(
            enable_llm_descriptions=False,  # No LLM for demo
            llm_model="gpt-4o",
            llm_endpoint="https://api.openai.com/v1",
        ),
    )

    converter = FileConverter(config)

    print(f"Configuration:")
    print(f"  Max file size: {config.get_max_file_size_mb():.1f} MB")
    print(f"  Timeout: {config.conversion_timeout} seconds")
    print(f"  LLM enabled: {config.markitdown.enable_llm_descriptions}")
    print()

    # Test with a simple text file (will be rejected as unsupported)
    print("Testing with text file (should be rejected):")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp_file:
        tmp_file.write("This is a test document.\n\nIt has multiple lines.")
        tmp_file.flush()

        try:
            result = converter.convert_file(tmp_file.name)
            print(f"✅ Conversion successful: {len(result)} characters")
        except Exception as e:
            print(f"❌ Conversion failed (expected): {e}")
        finally:
            os.unlink(tmp_file.name)

    print()

    # Test fallback document creation
    print("Testing fallback document creation:")
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        tmp_file.write(b"fake pdf content")
        tmp_file.flush()

        try:
            error = Exception("Simulated conversion error")
            fallback_doc = converter.create_fallback_document(tmp_file.name, error)

            print("✅ Fallback document created:")
            print("--- Fallback Document ---")
            print(
                fallback_doc[:300] + "..." if len(fallback_doc) > 300 else fallback_doc
            )
            print("--- End Fallback Document ---")

        finally:
            os.unlink(tmp_file.name)


def demo_configuration():
    """Demonstrate configuration options."""
    print("=== Configuration Demo ===")

    # Default configuration
    default_config = FileConversionConfig()
    print("Default configuration:")
    print(f"  Max file size: {default_config.get_max_file_size_mb():.1f} MB")
    print(f"  Timeout: {default_config.conversion_timeout} seconds")
    print(f"  LLM enabled: {default_config.markitdown.enable_llm_descriptions}")
    print()

    # Custom configuration
    custom_markitdown = MarkItDownConfig(
        enable_llm_descriptions=True,
        llm_model="gpt-4",
        llm_endpoint="https://custom.api.com/v1",
    )

    custom_config = FileConversionConfig(
        max_file_size=5 * 1024 * 1024,  # 5MB
        conversion_timeout=120,  # 2 minutes
        markitdown=custom_markitdown,
    )

    print("Custom configuration:")
    print(f"  Max file size: {custom_config.get_max_file_size_mb():.1f} MB")
    print(f"  Timeout: {custom_config.conversion_timeout} seconds")
    print(f"  LLM enabled: {custom_config.markitdown.enable_llm_descriptions}")
    print(f"  LLM model: {custom_config.markitdown.llm_model}")
    print(f"  LLM endpoint: {custom_config.markitdown.llm_endpoint}")
    print()

    # Test file size validation
    print("File size validation:")
    test_sizes = [
        1024,
        1024 * 1024,
        5 * 1024 * 1024,
        10 * 1024 * 1024,
    ]  # 1KB, 1MB, 5MB, 10MB

    for size in test_sizes:
        is_allowed = custom_config.is_file_size_allowed(size)
        size_mb = size / (1024 * 1024)
        status = "✅ Allowed" if is_allowed else "❌ Too large"
        print(f"  {size_mb:.1f} MB - {status}")


def main():
    """Run all demos."""
    print("File Conversion Infrastructure Demo")
    print("=" * 50)
    print()

    try:
        demo_file_detection()
        demo_configuration()
        demo_file_conversion()

        print("\n" + "=" * 50)
        print("Demo completed successfully!")
        print("\nNote: Some conversion tests may fail if MarkItDown dependencies")
        print("are not fully installed. This is expected in a test environment.")

    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
