"""Enhanced comprehensive tests for Git metadata extractor to achieve 80%+ coverage."""

import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import git
import pytest
from pydantic import HttpUrl

from qdrant_loader.config.types import SourceType
from qdrant_loader.connectors.git.config import GitRepoConfig
from qdrant_loader.connectors.git.metadata_extractor import GitMetadataExtractor


class TestGitMetadataExtractorEnhanced:
    """Enhanced comprehensive tests for GitMetadataExtractor class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def base_config(self, temp_dir):
        """Create a base configuration for testing."""
        return GitRepoConfig(
            base_url=HttpUrl("https://github.com/test/repo.git"),
            branch="main",
            file_types=["*.md", "*.txt"],
            token="test_token",
            source="test_source",
            source_type=SourceType.GIT,
            temp_dir=temp_dir,
        )

    @pytest.fixture
    def gitlab_config(self, temp_dir):
        """Create a GitLab configuration for testing."""
        return GitRepoConfig(
            base_url=HttpUrl("https://gitlab.example.com/group/project.git"),
            branch="develop",
            file_types=["*.md"],
            token="gitlab_token",
            source="gitlab_source",
            source_type=SourceType.GIT,
            temp_dir=temp_dir,
        )

    @pytest.fixture
    def azure_config(self, temp_dir):
        """Create an Azure DevOps configuration for testing."""
        return GitRepoConfig(
            base_url=HttpUrl("https://dev.azure.com/org/project/_git/repo"),
            branch="feature/test",
            file_types=["*.md"],
            token="azure_token",
            source="azure_source",
            source_type=SourceType.GIT,
            temp_dir=temp_dir,
        )

    def test_initialization(self, base_config):
        """Test GitMetadataExtractor initialization."""
        extractor = GitMetadataExtractor(base_config)
        
        assert extractor.config is base_config
        assert extractor.logger is not None

    def test_extract_file_metadata_complex_content(self, base_config):
        """Test file metadata extraction with complex content."""
        extractor = GitMetadataExtractor(base_config)
        
        # Complex markdown with multiple features
        content = """# Main Title

## Introduction
This is a complex document with various features.

### Code Examples

```python
def complex_function(x, y):
    \"\"\"A complex function.\"\"\"
    return x + y
```

```javascript
const arr = [1, 2, 3];
console.log(arr);
```

### Images and Links

![Main diagram](./images/main.png)
![Secondary image](https://example.com/image.jpg)

[External link](https://example.com)
[Internal link](./docs/internal.md)
[Relative link](../README.md)

### Tables

| Column 1 | Column 2 |
|----------|----------|
| Data 1   | Data 2   |

> This is a blockquote with some content.

- List item 1
- List item 2
  - Nested item

1. Ordered item 1
2. Ordered item 2

---

Final paragraph with special characters: éñüñøß
"""

        # Test with different file paths and encodings
        test_cases = [
            ("/path/to/document.md", content),
            ("/nested/deep/folder/file.txt", content),
            ("simple.py", content),
        ]
        
        for file_path, test_content in test_cases:
            metadata = extractor._extract_file_metadata(file_path, test_content)
            
            assert metadata["file_type"] == os.path.splitext(file_path)[1]
            assert metadata["file_name"] == os.path.basename(file_path)
            assert metadata["file_encoding"] == "utf-8"
            assert metadata["line_count"] > 30
            assert metadata["word_count"] > 50
            assert metadata["file_size"] > 500
            assert metadata["has_code_blocks"] is True
            assert metadata["has_images"] is True
            assert metadata["has_links"] is True

    def test_extract_file_metadata_edge_cases(self, base_config):
        """Test file metadata extraction with edge cases."""
        extractor = GitMetadataExtractor(base_config)
        
        # Empty content
        metadata = extractor._extract_file_metadata("/test/empty.md", "")
        assert metadata["line_count"] == 0
        assert metadata["word_count"] == 0
        assert metadata["file_size"] == 0
        assert metadata["has_code_blocks"] is False
        assert metadata["has_images"] is False
        assert metadata["has_links"] is False
        
        # Single character content
        metadata = extractor._extract_file_metadata("/test/char.txt", "x")
        assert metadata["line_count"] == 1
        assert metadata["word_count"] == 1
        assert metadata["file_size"] == 1
        
        # Content with only whitespace
        metadata = extractor._extract_file_metadata("/test/whitespace.md", "   \n\n  \t  \n")
        assert metadata["line_count"] == 4
        assert metadata["word_count"] == 0

    def test_extract_file_metadata_encoding_detection(self, base_config):
        """Test encoding detection with various content types."""
        extractor = GitMetadataExtractor(base_config)
        
        # Test different encoding scenarios
        test_cases = [
            ("ASCII content", "utf-8"),
            ("Unicode content: éñüñøß 🌍", "utf-8"),
            ("Mixed content with numbers: 123 and symbols: !@#$%", "utf-8"),
        ]
        
        for content, expected_encoding in test_cases:
            detected = extractor._detect_encoding(content)
            assert detected == expected_encoding

    def test_extract_repo_metadata_github(self, base_config):
        """Test repository metadata extraction for GitHub."""
        # Mock repository
        mock_repo = MagicMock(spec=git.Repo)
        mock_repo.bare = False  # Ensure it's not a bare repository
        mock_config = MagicMock()
        mock_config.has_section.return_value = True
        mock_config.get_value.side_effect = lambda section, key, default: {
            ("github", "description"): "GitHub test repository",
            ("github", "language"): "Python",
        }.get((section, key), default)
        mock_repo.config_reader.return_value = mock_config
        
        with patch("git.Repo", return_value=mock_repo):
            extractor = GitMetadataExtractor(base_config)
            metadata = extractor._extract_repo_metadata("/test/file.md")
            
            assert metadata["repository_name"] == "repo"
            assert metadata["repository_owner"] == "test"
            assert metadata["repository_url"] == "https://github.com/test/repo.git"
            assert metadata["repository_description"] == "GitHub test repository"
            assert metadata["repository_language"] == "Python"

    def test_extract_repo_metadata_gitlab(self, gitlab_config):
        """Test repository metadata extraction for GitLab."""
        # Mock repository
        mock_repo = MagicMock(spec=git.Repo)
        mock_config = MagicMock()
        mock_config.has_section.return_value = False
        mock_repo.config_reader.return_value = mock_config
        
        with patch("git.Repo", return_value=mock_repo):
            extractor = GitMetadataExtractor(gitlab_config)
            metadata = extractor._extract_repo_metadata("/test/file.md")
            
            assert metadata["repository_name"] == "project"
            assert metadata["repository_owner"] == "group"
            assert metadata["repository_url"] == "https://gitlab.example.com/group/project.git"

    def test_extract_repo_metadata_azure_devops(self, azure_config):
        """Test repository metadata extraction for Azure DevOps."""
        # Mock repository
        mock_repo = MagicMock(spec=git.Repo)
        mock_config = MagicMock()
        mock_config.has_section.return_value = False
        mock_repo.config_reader.return_value = mock_config
        
        with patch("git.Repo", return_value=mock_repo):
            extractor = GitMetadataExtractor(azure_config)
            metadata = extractor._extract_repo_metadata("/test/file.md")
            
            assert metadata["repository_name"] == "repo"
            assert metadata["repository_owner"] == "org"
            assert metadata["repository_url"] == "https://dev.azure.com/org/project/_git/repo"

    def test_extract_repo_metadata_edge_cases(self, base_config):
        """Test repository metadata extraction edge cases."""
        extractor = GitMetadataExtractor(base_config)
        
        # Test with invalid Git repository
        with patch("git.Repo", side_effect=git.InvalidGitRepositoryError):
            metadata = extractor._extract_repo_metadata("/test/file.md")
            assert metadata == {}
        
        # Test with empty config - avoid mutating shared fixture by creating a copy
        local_config = GitRepoConfig(
            base_url=HttpUrl("https://example.com"),
            branch=base_config.branch,
            file_types=base_config.file_types,
            token=base_config.token,
            source=base_config.source,
            source_type=base_config.source_type,
            temp_dir=base_config.temp_dir,
        )
        extractor2 = GitMetadataExtractor(local_config)
        metadata = extractor2._extract_repo_metadata("/test/file.md")
        assert metadata == {}

    def test_extract_git_metadata_comprehensive(self, base_config):
        """Test comprehensive Git metadata extraction."""
        # Mock repository with multiple commits
        mock_repo = MagicMock(spec=git.Repo)
        
        # Mock commits
        commit1 = MagicMock()
        commit1.committed_datetime = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)
        commit1.author.name = "Alice Developer"
        commit1.message = "Initial commit\n\nAdded basic functionality"
        
        commit2 = MagicMock()
        commit2.committed_datetime = datetime(2024, 1, 10, 10, 0, 0, tzinfo=UTC)
        commit2.author.name = "Bob Developer"
        commit2.message = "Setup project structure"
        
        mock_repo.head.commit = commit1
        mock_repo.iter_commits.return_value = [commit1, commit2]
        
        with patch("git.Repo", return_value=mock_repo):
            extractor = GitMetadataExtractor(base_config)
            metadata = extractor._extract_git_metadata("/test/file.md")
            
            assert metadata["last_commit_date"] == "2024-01-15T14:30:00+00:00"
            assert metadata["last_commit_author"] == "Alice Developer"
            assert metadata["last_commit_message"] == "Initial commit"

    def test_extract_git_metadata_error_handling(self, base_config):
        """Test Git metadata extraction error handling."""
        extractor = GitMetadataExtractor(base_config)
        
        # Test various Git exceptions
        exceptions_to_test = [
            git.InvalidGitRepositoryError,
            git.GitCommandError("test", 1),
            git.NoSuchPathError,
            Exception("Generic error"),
        ]
        
        for exception in exceptions_to_test:
            with patch("git.Repo", side_effect=exception):
                metadata = extractor._extract_git_metadata("/test/file.md")
                assert metadata == {}

    def test_extract_structure_metadata_complex(self, base_config):
        """Test structure metadata extraction with complex documents."""
        extractor = GitMetadataExtractor(base_config)
        
        # Complex markdown structure
        content = """# Main Title

## Table of Contents
- [Introduction](#introduction)
- [Features](#features)
- [Usage](#usage)

## Introduction
Welcome to this document.

### Background
Some background information.

#### Historical Context
Even more detailed context.

## Features
List of features.

### Core Features
- Feature 1
- Feature 2

### Advanced Features
- Advanced feature 1

## Usage
How to use this.

### Quick Start
Getting started quickly.

### Advanced Usage
More complex usage patterns.

## Conclusion
Final thoughts.
"""
        
        metadata = extractor._extract_structure_metadata(content)
        
        assert metadata["has_toc"] is True
        assert metadata["sections_count"] == 12
        expected_levels = [1, 2, 2, 3, 4, 2, 3, 3, 2, 3, 3, 2]
        assert metadata["heading_levels"] == expected_levels

    def test_extract_structure_metadata_alternative_toc_formats(self, base_config):
        """Test structure metadata with different TOC formats."""
        extractor = GitMetadataExtractor(base_config)
        
        # Different TOC formats
        toc_formats = [
            "## Table of Contents",
            "## Contents",
            "# Table of Contents",
            "### Contents",
        ]
        
        for toc_format in toc_formats:
            content = f"""{toc_format}
- [Section 1](#section-1)
- [Section 2](#section-2)

# Section 1
Content here.

# Section 2
More content.
"""
            metadata = extractor._extract_structure_metadata(content)
            assert metadata["has_toc"] is True

    def test_extract_structure_metadata_no_headers(self, base_config):
        """Test structure metadata with content that has no headers."""
        extractor = GitMetadataExtractor(base_config)
        
        content = """This is just plain text content without any headers.
It has multiple paragraphs but no markdown headers.

Another paragraph here.

And a final paragraph.
"""
        
        metadata = extractor._extract_structure_metadata(content)
        
        assert metadata["has_toc"] is False
        assert metadata["sections_count"] == 0
        assert metadata["heading_levels"] == []

    def test_extract_structure_metadata_malformed_headers(self, base_config):
        """Test structure metadata with malformed headers."""
        extractor = GitMetadataExtractor(base_config)
        
        # Various malformed header scenarios
        content = """#No space after hash
 # Space before hash
# 

## Valid Header
#######Too many hashes
# Another valid header

Not a header: # hash in middle
"""
        
        metadata = extractor._extract_structure_metadata(content)
        
        # Should find the valid headers
        assert metadata["sections_count"] >= 1  # At least "Valid Header"
        assert 2 in metadata["heading_levels"]  # Level 2 for "Valid Header"

    def test_get_repo_description_from_config(self, base_config):
        """Test getting repository description from Git config."""
        extractor = GitMetadataExtractor(base_config)
        
        # Mock repository with config description
        mock_repo = MagicMock(spec=git.Repo)
        mock_config = MagicMock()
        mock_config.has_section.return_value = True
        mock_config.get_value.return_value = "Description from Git config"
        mock_repo.config_reader.return_value = mock_config
        
        description = extractor._get_repo_description(mock_repo, "/test/file.md")
        assert description == "Description from Git config"

    def test_get_repo_description_from_readme(self, base_config, temp_dir):
        """Test getting repository description from README files."""
        extractor = GitMetadataExtractor(base_config)
        
        # Create a mock repository with README
        readme_content = """# Test Repository

This is a test repository for demonstrating functionality.

It has multiple features and capabilities.

## Installation
Instructions here.
"""
        
        readme_path = os.path.join(temp_dir, "README.md")
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content)
        
        # Mock repository
        mock_repo = MagicMock(spec=git.Repo)
        mock_repo.working_dir = temp_dir
        mock_config = MagicMock()
        mock_config.has_section.return_value = False
        mock_repo.config_reader.return_value = mock_config
        
        description = extractor._get_repo_description(mock_repo, "/test/file.md")
        assert "This is a test repository for demonstrating functionality" in description

    def test_get_repo_description_fallback_scenarios(self, base_config, temp_dir):
        """Test repository description fallback scenarios."""
        extractor = GitMetadataExtractor(base_config)
        
        # Mock repository with no description sources
        mock_repo = MagicMock(spec=git.Repo)
        mock_repo.working_dir = temp_dir
        mock_config = MagicMock()
        mock_config.has_section.return_value = False
        mock_config.get_value.return_value = ""
        mock_repo.config_reader.return_value = mock_config
        
        description = extractor._get_repo_description(mock_repo, "/test/file.md")
        assert description == ""

    def test_detect_encoding_edge_cases(self, base_config):
        """Test encoding detection edge cases."""
        extractor = GitMetadataExtractor(base_config)
        
        # Test with different content types
        test_cases = [
            ("", "utf-8"),  # Empty string
            ("a", "utf-8"),  # Single character
            ("Hello World", "utf-8"),  # Simple ASCII
            ("日本語", "utf-8"),  # Japanese characters
            ("مرحبا", "utf-8"),  # Arabic characters
            ("🚀🌟💻", "utf-8"),  # Emojis
        ]
        
        for content, expected in test_cases:
            detected = extractor._detect_encoding(content)
            assert detected == expected

    def test_feature_detection_methods(self, base_config):
        """Test individual feature detection methods."""
        extractor = GitMetadataExtractor(base_config)
        
        # Test code block detection
        assert extractor._has_code_blocks("```python\nprint('hello')\n```") is True
        assert extractor._has_code_blocks("No code here") is False
        assert extractor._has_code_blocks("```\njust backticks\n```") is True
        assert extractor._has_code_blocks("`inline code`") is False
        
        # Test image detection
        assert extractor._has_images("![Alt text](image.png)") is True
        assert extractor._has_images("No images here") is False
        assert extractor._has_images("![](empty-alt.jpg)") is True
        assert extractor._has_images("![Multiple](img1.png) and ![more](img2.jpg)") is True
        
        # Test link detection
        assert extractor._has_links("[Link text](https://example.com)") is True
        assert extractor._has_links("No links here") is False
        assert extractor._has_links("[Empty]()")  is True
        assert extractor._has_links("[Multiple](link1.html) and [more](link2.html)") is True

    def test_get_heading_levels(self, base_config):
        """Test heading level extraction."""
        extractor = GitMetadataExtractor(base_config)
        
        content = """# Level 1
## Level 2
### Level 3
#### Level 4
##### Level 5
###### Level 6
## Another Level 2
# Another Level 1
"""
        
        levels = extractor._get_heading_levels(content)
        expected = [1, 2, 3, 4, 5, 6, 2, 1]
        assert levels == expected

    def test_extract_all_metadata_non_markdown_file(self, base_config):
        """Test metadata extraction for non-markdown files."""
        # Mock Git operations
        mock_repo = MagicMock(spec=git.Repo)
        mock_commit = MagicMock()
        mock_commit.committed_datetime = datetime(2024, 1, 1, tzinfo=UTC)
        mock_commit.author.name = "Test Author"
        mock_commit.message = "Test commit"
        mock_repo.head.commit = mock_commit
        mock_repo.iter_commits.return_value = [mock_commit]
        
        mock_config = MagicMock()
        mock_config.has_section.return_value = False
        mock_repo.config_reader.return_value = mock_config
        
        content = """
def hello_world():
    print("Hello, World!")
    
if __name__ == "__main__":
    hello_world()
"""
        
        with patch("git.Repo", return_value=mock_repo):
            extractor = GitMetadataExtractor(base_config)
            metadata = extractor.extract_all_metadata("/test/script.py", content)
            
            # Should have file and git metadata, but no structure metadata
            assert "file_type" in metadata
            assert "last_commit_author" in metadata
            assert "has_toc" not in metadata  # Structure metadata only for .md files
            assert "heading_levels" not in metadata
            assert "sections_count" not in metadata

    def test_extract_all_metadata_logging(self, base_config):
        """Test that extract_all_metadata logs appropriately."""
        with patch("git.Repo", side_effect=git.InvalidGitRepositoryError):
            with patch("qdrant_loader.connectors.git.metadata_extractor.logger") as mock_logger:
                extractor = GitMetadataExtractor(base_config)
                
                metadata = extractor.extract_all_metadata("/test/file.md", "# Test")
                
                # Verify logging calls were made
                mock_logger.debug.assert_called()
                
                # Should still return file metadata even if git fails
                assert "file_type" in metadata
                assert metadata["file_type"] == ".md"