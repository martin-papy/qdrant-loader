import pytest
from unittest.mock import patch, MagicMock
import git
from qdrant_loader.connectors.git.metadata_extractor import GitMetadataExtractor
from qdrant_loader.config import GitRepoConfig
from datetime import datetime

@pytest.fixture
def git_config():
    """Create a GitRepoConfig instance for testing."""
    return GitRepoConfig(
        url="https://github.com/test/repo.git",
        branch="main",
        file_types=[".md", ".py"],  # Add some file types to pass validation
        temp_dir="/tmp/test"  # Add temp_dir to match mock_repo.working_dir
    )

@pytest.fixture
def metadata_extractor(git_config):
    """Create a GitMetadataExtractor instance."""
    return GitMetadataExtractor(git_config)

@pytest.fixture
def mock_repo():
    """Create a mock Git repository."""
    mock_repo = MagicMock(spec=git.Repo)
    
    # Mock commit
    mock_commit = MagicMock()
    mock_commit.committed_datetime = datetime(2024, 1, 1, 12, 0, 0)
    mock_commit.author.name = "Test Author"
    mock_commit.message = "Test commit message"
    
    # Mock iter_commits to return our mock commit
    def mock_iter_commits(*args, **kwargs):
        return [mock_commit]
    mock_repo.iter_commits = MagicMock(side_effect=mock_iter_commits)
    
    # Mock working_dir
    mock_repo.working_dir = "/tmp/test"  # Match the temp_dir in git_config
    
    # Mock config_reader
    mock_config = MagicMock()
    mock_config.has_section.return_value = True
    
    # Create a dictionary to store config values
    config_values = {
        ('github', 'description'): 'Test repository',
        ('github', 'language'): 'Python',
        ('core', 'description'): 'Test repository'  # Add fallback value
    }
    
    def mock_get_value(section, key, default=None):
        return config_values.get((section, key), default)
    
    mock_config.get_value = MagicMock(side_effect=mock_get_value)
    mock_repo.config_reader.return_value = mock_config
    
    # Mock bare property
    mock_repo.bare = False
    
    # Mock head commit
    mock_repo.head.commit = mock_commit
    
    return mock_repo

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
        assert metadata["repository_language"] == "Python"
        assert metadata["repository_owner"] == "test"
        assert metadata["repository_url"] == "https://github.com/test/repo.git"

def test_extract_git_metadata(metadata_extractor, mock_repo):
    """Test Git metadata extraction."""
    with patch('git.Repo', return_value=mock_repo):
        metadata = metadata_extractor._extract_git_metadata("test.md")
        
        assert "last_commit_date" in metadata
        assert "last_commit_author" in metadata
        assert "last_commit_message" in metadata
        assert metadata["last_commit_date"] == "2024-01-01T12:00:00"
        assert metadata["last_commit_author"] == "Test Author"
        assert metadata["last_commit_message"] == "Test commit message"
        mock_repo.iter_commits.assert_called()

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
        assert "last_commit_author" in metadata
        assert "last_commit_message" in metadata
        
        # Verify specific values
        assert metadata["repository_description"] == "Test repository"
        assert metadata["last_commit_date"] == "2024-01-01T12:00:00"
        assert metadata["last_commit_author"] == "Test Author"
        assert metadata["last_commit_message"] == "Test commit message" 