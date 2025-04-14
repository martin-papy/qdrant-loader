"""
Tests for Git directory structure handling.
"""
import pytest
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def normalize_path(path: str) -> str:
    """Normalize a path for consistent comparison."""
    return path.strip("/").replace("\\", "/")

@pytest.mark.integration
@pytest.mark.asyncio
async def test_nested_directory_handling(session_git_connector, is_github_actions):
    """Test handling of nested directories."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")
    with session_git_connector:
        logger.debug("Starting test_nested_directory_handling")
        # Get all documents
        docs = await session_git_connector.get_documents()
        assert len(docs) > 0
        
        logger.debug(f"Found {len(docs)} total documents")
        # Log each document's path
        for doc in docs:
            logger.debug(f"Document found: {doc.metadata.get('file_path', 'unknown')}")
        
        # Ensure we have documents
        assert len(docs) > 0, "No documents were found"
        
        # Get all unique directories
        directories = {normalize_path(doc.metadata["file_directory"]) for doc in docs}
        
        # Print directories for debugging
        logger.debug(f"Found directories: {directories}")
        
        # Log all document paths and metadata for debugging
        for doc in docs:
            logger.debug(f"Document path: {doc.metadata.get('file_path', 'unknown')}")
            logger.debug(f"Document directory: {doc.metadata.get('file_directory', 'unknown')}")
            logger.debug(f"Document metadata: {doc.metadata}")
        
        # Log specific directory checks
        docs_dirs = [dir for dir in directories if dir.startswith("docs")]
        src_dirs = [dir for dir in directories if dir.startswith("src")]
        logger.debug(f"Docs directories found: {docs_dirs}")
        logger.debug(f"Src directories found: {src_dirs}")
        
        # Verify we have documents from nested directories
        assert any(dir.startswith("docs") for dir in directories), "No documents found in docs directory"
        assert any(dir.startswith("src") for dir in directories), "No documents found in src directory"

@pytest.mark.integration
def test_root_directory_handling(session_git_connector, is_github_actions):
    """Test handling of root directory files."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")
    with session_git_connector:
        logger.debug("Starting test_root_directory_handling")
        # Get all documents
        docs = list(session_git_connector.get_documents())
        
        logger.debug(f"Found {len(docs)} total documents")
        # Log each document's path
        for doc in docs:
            logger.debug(f"Document found: {doc.metadata.get('file_path', 'unknown')}")
        
        # Ensure we have documents
        assert len(docs) > 0, "No documents were found"
        
        # Get all unique directories
        directories = {normalize_path(doc.metadata["file_directory"]) for doc in docs}
        
        # Print directories for debugging
        logger.debug(f"Found directories: {directories}")
        
        # Log root directory check
        root_docs = [dir for dir in directories if dir == ""]
        logger.debug(f"Root directory documents found: {root_docs}")
        
        # Verify we have documents from root directory (like README.md)
        assert any(dir == "" for dir in directories), "No documents found in root directory"

@pytest.mark.integration
def test_directory_exclusion(session_git_connector, is_github_actions):
    """Test directory exclusion functionality."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")
    with session_git_connector:
        logger.debug("Starting test_directory_exclusion")
        # Get all documents
        docs = list(session_git_connector.get_documents())
        
        logger.debug(f"Found {len(docs)} total documents")
        # Log each document's path
        for doc in docs:
            logger.debug(f"Document found: {doc.metadata.get('file_path', 'unknown')}")
        
        # Ensure we have documents
        assert len(docs) > 0, "No documents were found"
        
        # Get all unique directories
        directories = {normalize_path(doc.metadata["file_directory"]) for doc in docs}
        
        # Print directories for debugging
        logger.debug(f"Found directories: {directories}")
        
        # Log test directory check
        test_dirs = [dir for dir in directories if dir.startswith("tests")]
        logger.debug(f"Test directories found (should be empty): {test_dirs}")
        
        # Verify no documents from excluded directories
        assert not any(dir.startswith("tests") for dir in directories), "Found documents in excluded tests directory"

@pytest.mark.integration
def test_directory_inclusion(session_git_connector, is_github_actions):
    """Test directory inclusion functionality."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")
    with session_git_connector:
        logger.debug("Starting test_directory_inclusion")
        # Get all documents
        docs = list(session_git_connector.get_documents())
        
        logger.debug(f"Found {len(docs)} total documents")
        # Log each document's path
        for doc in docs:
            logger.debug(f"Document found: {doc.metadata.get('file_path', 'unknown')}")
        
        # Ensure we have documents
        assert len(docs) > 0, "No documents were found"
        
        # Get all unique directories
        directories = {normalize_path(doc.metadata["file_directory"]) for doc in docs}
        
        # Print directories for debugging
        logger.debug(f"Found directories: {directories}")
        
        # Log specific directory checks
        has_root = any(dir == "" for dir in directories)  # For README.md
        has_docs = any(dir.startswith("docs") for dir in directories)
        has_src = any(dir.startswith("src") for dir in directories)
        
        logger.debug(f"Has root documents: {has_root}")
        logger.debug(f"Has docs documents: {has_docs}")
        logger.debug(f"Has src documents: {has_src}")
        
        # Verify we have documents from included directories
        assert has_root or has_docs or has_src, "No documents found in any of the included directories"

@pytest.mark.integration
def test_directory_pattern_matching(session_git_connector, is_github_actions):
    """Test directory pattern matching."""
    if is_github_actions:
        pytest.skip("Skipping test in GitHub Actions environment")
    with session_git_connector:
        logger.debug("Starting test_directory_pattern_matching")
        # Get all documents
        docs = list(session_git_connector.get_documents())
        
        logger.debug(f"Found {len(docs)} total documents")
        # Log each document's path
        for doc in docs:
            logger.debug(f"Document found: {doc.metadata.get('file_path', 'unknown')}")
        
        # Ensure we have documents
        assert len(docs) > 0, "No documents were found"
        
        # Get all unique directories
        directories = {normalize_path(doc.metadata["file_directory"]) for doc in docs}
        
        # Print directories for debugging
        logger.debug(f"Found directories: {directories}")
        
        # Log all document paths and metadata for debugging
        for doc in docs:
            logger.debug(f"Document path: {doc.metadata.get('file_path', 'unknown')}")
            logger.debug(f"Document directory: {doc.metadata.get('file_directory', 'unknown')}")
            logger.debug(f"Document metadata: {doc.metadata}")
        
        # Log specific directory checks
        has_root = any(dir == "" for dir in directories)  # For README.md
        has_docs = any(dir.startswith("docs") for dir in directories)
        has_src = any(dir.startswith("src") for dir in directories)
        has_tests = any(dir.startswith("tests") for dir in directories)
        
        logger.debug(f"Has root documents: {has_root}")
        logger.debug(f"Has docs documents: {has_docs}")
        logger.debug(f"Has src documents: {has_src}")
        logger.debug(f"Has tests documents: {has_tests}")
        
        # Verify pattern matching works for both inclusion and exclusion
        assert has_root or has_docs or has_src, "No documents found in any of the included directories"
        assert not has_tests, "Found documents in excluded tests directory" 