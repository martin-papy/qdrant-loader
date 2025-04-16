"""
Tests for Git file type handling.
"""

import pytest


@pytest.mark.integration
def test_file_type_handling(cached_documents, is_github_actions):
    """Test handling of different file types."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")

    # Await the documents from the fixture
    docs = cached_documents

    # Test markdown files
    md_files = [doc for doc in docs if doc.metadata["file_name"].endswith(".md")]
    assert len(md_files) > 0, "Should find markdown files"

    # Test java files
    java_files = [doc for doc in docs if doc.metadata["file_name"].endswith(".java")]
    assert len(java_files) > 0, "Should find Java files"

    # Test no other file types
    other_files = [doc for doc in docs if not doc.metadata["file_name"].endswith((".md", ".java"))]
    assert len(other_files) == 0, "Should not process non-specified file types"
