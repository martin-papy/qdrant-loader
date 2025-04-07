import pytest
from unittest.mock import patch, MagicMock
import git
from qdrant_loader.connectors.git.metadata_extractor import GitMetadataExtractor

@pytest.fixture
def metadata_extractor():
    """Create a GitMetadataExtractor instance."""
    return GitMetadataExtractor()

@pytest.fixture
def mock_repo():
    """Create a mock Git repository."""
    repo = MagicMock(spec=git.Repo)
    repo.git = MagicMock()
    repo.git.show = MagicMock(return_value="test content")
    repo.git.log = MagicMock(return_value="1234567890")
    repo.working_dir = "/tmp/test"
    repo.remotes = MagicMock()
    repo.remotes.origin = MagicMock()
    repo.remotes.origin.url = "https://github.com/test/repo.git"
    repo.description = "Test repository"
    return repo

def test_extract_file_metadata(metadata_extractor):
    """Test file metadata extraction."""
    file_path = "test.md"
    content = "This is a test file\nwith multiple lines\nand some words"
    
    metadata = metadata_extractor._extract_file_metadata(file_path, content)
    
    assert metadata["file_type"] == ".md"
    assert metadata["file_name"] == "test.md"
    assert metadata["line_count"] == 3
    assert metadata["word_count"] == 11
    assert metadata["file_encoding"] == "utf-8"

def test_extract_repo_metadata(metadata_extractor, mock_repo):
    """Test repository metadata extraction."""
    with patch('git.Repo', return_value=mock_repo):
        metadata = metadata_extractor._extract_repo_metadata("test.md")
        
        assert "repository_name" in metadata
        assert "repository_description" in metadata
        assert "repository_owner" in metadata
        assert "repository_url" in metadata
        assert "repository_language" in metadata
        assert metadata["repository_name"] == "repo"
        assert metadata["repository_description"] == "Test repository"
        assert metadata["repository_owner"] == "test"
        assert metadata["repository_url"] == "https://github.com/test/repo.git"

def test_extract_git_metadata(metadata_extractor, mock_repo):
    """Test Git metadata extraction."""
    with patch('git.Repo', return_value=mock_repo):
        metadata = metadata_extractor._extract_git_metadata("test.md")
        
        assert "last_commit_date" in metadata
        assert "last_commit_author" in metadata
        assert "last_commit_message" in metadata

def test_extract_structure_metadata(metadata_extractor):
    """Test content structure metadata extraction."""
    content = """# Heading 1
## Heading 2
```python
print("code block")
```
![image](test.png)
[link](test.md)
"""
    
    metadata = metadata_extractor._extract_structure_metadata(content)
    
    assert "has_toc" in metadata
    assert "heading_levels" in metadata
    assert "sections_count" in metadata
    assert metadata["heading_levels"] == [1, 2]
    assert metadata["sections_count"] == 2

def test_detect_encoding(metadata_extractor):
    """Test encoding detection."""
    content = "Test content with UTF-8 characters: é, ñ, ü"
    
    encoding = metadata_extractor._detect_encoding(content)
    assert encoding == "utf-8"

def test_detect_language(metadata_extractor):
    """Test language detection."""
    # Test Python file
    assert metadata_extractor._detect_language("test.py") == "Python"
    
    # Test Markdown file
    assert metadata_extractor._detect_language("test.md") == "Markdown"
    
    # Test unknown file type
    assert metadata_extractor._detect_language("test.xyz") == "Unknown"

def test_extract_all_metadata(metadata_extractor, mock_repo):
    """Test complete metadata extraction."""
    with patch('git.Repo', return_value=mock_repo):
        file_path = "test.md"
        content = """# Test
```python
print("test")
```
"""
        
        metadata = metadata_extractor.extract_all_metadata(file_path, content)
        
        # Check that all metadata categories are present
        assert "file_type" in metadata
        assert "file_name" in metadata
        assert "line_count" in metadata
        assert "word_count" in metadata
        assert "file_encoding" in metadata
        assert "repository_name" in metadata
        assert "repository_description" in metadata
        assert "last_commit_date" in metadata
        assert "has_toc" in metadata
        assert "heading_levels" in metadata
        assert metadata["heading_levels"] == [1]
        assert metadata["file_type"] == ".md"
        assert metadata["repository_name"] == "repo" 