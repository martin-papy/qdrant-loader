"""
Tests for Git directory structure handling.
"""

import pytest
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def log_with_timestamp(message: str):
    """Helper function to log messages with timestamps."""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")
    logger.debug(f"[{timestamp}] {message}")


@pytest.mark.integration
def test_nested_directory_handling(cached_documents, is_github_actions):
    """Test handling of nested directories."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")

    logger.debug("Starting test_nested_directory_handling")
    # Get all documents
    docs = cached_documents

    # Log metadata structure of first document for debugging
    if docs:
        logger.debug(f"First document metadata keys: {list(docs[0].metadata.keys())}")
        logger.debug(f"First document metadata: {docs[0].metadata}")

    # Test deeply nested directory files - files with multiple path segments
    nested_files = [doc for doc in docs if doc.metadata.get("file_directory", "").count("/") >= 2]
    assert len(nested_files) > 0, "Should find files in deeply nested directories"


@pytest.mark.integration
def test_root_directory_handling(cached_documents, is_github_actions):
    """Test handling of root directory files."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")

    logger.debug("Starting test_root_directory_handling")
    # Get all documents
    docs = cached_documents

    # Test root directory files
    root_files = [doc for doc in docs if not doc.metadata.get("file_directory", "")]
    assert len(root_files) > 0, "Should find files in root directory"


@pytest.mark.integration
def test_directory_exclusion(cached_documents, is_github_actions):
    """Test directory exclusion functionality."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")

    logger.debug("Starting test_directory_exclusion")
    # Get all documents
    docs = cached_documents

    # Test excluded directories - check if directory contains "src/test"
    excluded_files = [doc for doc in docs if "src/test" in doc.metadata.get("file_directory", "")]
    assert len(excluded_files) == 0, "Should not find files in directories containing 'src/test'"


@pytest.mark.integration
def test_directory_inclusion(cached_documents, is_github_actions):
    """Test directory inclusion functionality."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")

    logger.debug("Starting test_directory_inclusion")
    # Get all documents
    docs = cached_documents

    root_files = [doc for doc in docs if not doc.metadata.get("file_directory", "")]
    src_files = [doc for doc in docs if "src" in doc.metadata.get("file_directory", "")]
    docs_files = [doc for doc in docs if "docs" in doc.metadata.get("file_directory", "")]

    assert len(root_files) > 0, "Should find files in root directory"
    assert len(src_files) > 0, "Should find files in src directory"
    assert len(docs_files) > 0, "Should find files in docs directory"
