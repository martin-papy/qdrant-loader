"""Tests for automatic source_type and source field injection."""

import tempfile
from pathlib import Path

from qdrant_loader.config import get_settings, initialize_multi_file_config


class TestAutomaticFieldInjection:
    """Tests for automatic injection of source_type and source fields."""

    def test_automatic_field_injection_publicdocs(self):
        """Test that source_type and source are automatically injected for PublicDocs sources."""
        # Create multi-file configuration structure
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            # Create connectivity.yaml
            connectivity_content = """
qdrant:
  url: "http://localhost:6333"
  collection_name: "test_injection"

embedding:
  provider: "openai"
  model: "text-embedding-3-small"
  api_key: "test_key"

state_management:
  database_path: "/tmp/test.db"
"""
            (config_dir / "connectivity.yaml").write_text(connectivity_content)

            # Create fine-tuning.yaml
            fine_tuning_content = """
chunking:
  chunk_size: 1000
  chunk_overlap: 200
"""
            (config_dir / "fine-tuning.yaml").write_text(fine_tuning_content)

            # Create projects.yaml
            projects_content = """
projects:
  test-project:
    project_id: "test-project"
    display_name: "Test Project"
    description: "Test project for field injection"
    sources:
      publicdocs:
        example-docs:
          base_url: "https://example.com/docs"
          version: "1.0"
"""
            (config_dir / "projects.yaml").write_text(projects_content)

            # Initialize configuration
            initialize_multi_file_config(config_dir, enhanced_validation=False)
            settings = get_settings()

            # Get the project and its sources
            project = settings.projects_config.projects["test-project"]
            publicdocs_sources = project.sources.publicdocs

            # Verify the source exists
            assert "example-docs" in publicdocs_sources

            # Get the source configuration
            source_config = publicdocs_sources["example-docs"]

            # Verify that source_type and source were automatically injected
            assert source_config.source_type == "publicdocs"
            assert source_config.source == "example-docs"
            assert str(source_config.base_url) == "https://example.com/docs"
            assert source_config.version == "1.0"

    def test_automatic_field_injection_git(self):
        """Test that source_type and source are automatically injected for Git sources."""
        # Create multi-file configuration structure
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            # Create connectivity.yaml
            connectivity_content = """
qdrant:
  url: "http://localhost:6333"
  collection_name: "test_injection_git"

embedding:
  provider: "openai"
  model: "text-embedding-3-small"
  api_key: "test_key"

state_management:
  database_path: "/tmp/test.db"
"""
            (config_dir / "connectivity.yaml").write_text(connectivity_content)

            # Create fine-tuning.yaml
            fine_tuning_content = """
chunking:
  chunk_size: 1000
  chunk_overlap: 200
"""
            (config_dir / "fine-tuning.yaml").write_text(fine_tuning_content)

            # Create projects.yaml
            projects_content = """
projects:
  test-project:
    project_id: "test-project"
    display_name: "Test Project"
    description: "Test project for Git field injection"
    sources:
      git:
        my-repo:
          base_url: "https://github.com/example/repo.git"
          branch: "main"
          token: "test_token"
          file_types: ["*.md", "*.txt"]
"""
            (config_dir / "projects.yaml").write_text(projects_content)

            # Initialize configuration
            initialize_multi_file_config(config_dir, enhanced_validation=False)
            settings = get_settings()

            # Get the project and its sources
            project = settings.projects_config.projects["test-project"]
            git_sources = project.sources.git

            # Verify the source exists
            assert "my-repo" in git_sources

            # Get the source configuration
            source_config = git_sources["my-repo"]

            # Verify that source_type and source were automatically injected
            assert source_config.source_type == "git"
            assert source_config.source == "my-repo"
            assert str(source_config.base_url) == "https://github.com/example/repo.git"
            assert source_config.branch == "main"

    def test_multiple_source_types(self):
        """Test automatic field injection works for multiple source types."""
        # Create multi-file configuration structure
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            # Create connectivity.yaml
            connectivity_content = """
qdrant:
  url: "http://localhost:6333"
  collection_name: "test_multiple_sources"

embedding:
  provider: "openai"
  model: "text-embedding-3-small"
  api_key: "test_key"

state_management:
  database_path: "/tmp/test.db"
"""
            (config_dir / "connectivity.yaml").write_text(connectivity_content)

            # Create fine-tuning.yaml
            fine_tuning_content = """
chunking:
  chunk_size: 1000
  chunk_overlap: 200
"""
            (config_dir / "fine-tuning.yaml").write_text(fine_tuning_content)

            # Create projects.yaml
            projects_content = """
projects:
  test-project:
    project_id: "test-project"
    display_name: "Test Project"
    description: "Test project for multiple source types"
    sources:
      git:
        repo1:
          base_url: "https://github.com/example/repo1.git"
          branch: "main"
          token: "test_token1"
          file_types: ["*.md", "*.txt"]
        repo2:
          base_url: "https://github.com/example/repo2.git"
          branch: "develop"
          token: "test_token2"
          file_types: ["*.md", "*.txt"]
      publicdocs:
        docs1:
          base_url: "https://example.com/docs1"
          version: "1.0"
        docs2:
          base_url: "https://example.com/docs2"
          version: "2.0"
"""
            (config_dir / "projects.yaml").write_text(projects_content)

            # Initialize configuration
            initialize_multi_file_config(config_dir, enhanced_validation=False)
            settings = get_settings()

            # Get the project and its sources
            project = settings.projects_config.projects["test-project"]

            # Test Git sources
            git_sources = project.sources.git
            assert "repo1" in git_sources
            assert "repo2" in git_sources

            repo1_config = git_sources["repo1"]
            assert repo1_config.source_type == "git"
            assert repo1_config.source == "repo1"

            repo2_config = git_sources["repo2"]
            assert repo2_config.source_type == "git"
            assert repo2_config.source == "repo2"

            # Test PublicDocs sources
            publicdocs_sources = project.sources.publicdocs
            assert "docs1" in publicdocs_sources
            assert "docs2" in publicdocs_sources

            docs1_config = publicdocs_sources["docs1"]
            assert docs1_config.source_type == "publicdocs"
            assert docs1_config.source == "docs1"

            docs2_config = publicdocs_sources["docs2"]
            assert docs2_config.source_type == "publicdocs"
            assert docs2_config.source == "docs2"
