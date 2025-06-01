"""Tests for test template configuration with simplified approach."""

import os
import tempfile
from pathlib import Path

import pytest

from qdrant_loader.config import get_settings, initialize_config


class TestTestTemplateConfiguration:
    """Tests for test template configuration loading."""

    @pytest.fixture
    def test_template_config_content(self):
        """Test template configuration content."""
        return """
global:
  qdrant:
    url: "${QDRANT_URL}"
    api_key: "${QDRANT_API_KEY}"
    collection_name: "${QDRANT_COLLECTION_NAME}"
    
  chunking:
    chunk_size: 500
    chunk_overlap: 50
    
  embedding:
    model: text-embedding-3-small
    api_key: "${OPENAI_API_KEY}"
    batch_size: 10
    
  state_management:
    database_path: ":memory:"
    table_prefix: "test_qdrant_loader_"
    connection_pool:
      size: 1
      timeout: 5
  
  file_conversion:
    max_file_size: 10485760
    conversion_timeout: 60
    markitdown:
      enable_llm_descriptions: false
      llm_model: "gpt-4o"
      llm_endpoint: "https://api.openai.com/v1"
      llm_api_key: "${OPENAI_API_KEY}"

projects:
  default:
    display_name: "Test Template Project"
    description: "Default project for test template configuration testing"
    sources:
      git:
        test-repo:
          source_type: "git"
          source: "test-repo"
          base_url: "${REPO_URL}"
          branch: "main"
          token: "${REPO_TOKEN}"
          include_paths: ["/", "docs/**/*", "src/main/**/*", "README.md"]
          exclude_paths: ["src/test/**/*"]
          file_types: ["*.md","*.java"]
          max_file_size: 1048576
          depth: 1
          enable_file_conversion: true

      confluence:
        test-space:
          source_type: "confluence"
          source: "test-space"
          base_url: "${CONFLUENCE_URL}"
          space_key: "${CONFLUENCE_SPACE_KEY}"
          content_types: ["page", "blogpost"]
          token: "${CONFLUENCE_TOKEN}"
          email: "${CONFLUENCE_EMAIL}"
          enable_file_conversion: true
          download_attachments: true

      jira:
        test-project:
          source_type: "jira"
          source: "test-project"
          base_url: "${JIRA_URL}"
          deployment_type: "cloud"
          project_key: "${JIRA_PROJECT_KEY}"
          requests_per_minute: 60
          page_size: 50
          process_attachments: true
          track_last_sync: true
          token: "${JIRA_TOKEN}"
          email: "${JIRA_EMAIL}"
          enable_file_conversion: true
          download_attachments: true
"""

    @pytest.fixture
    def temp_config_file(self, test_template_config_content):
        """Create a temporary config file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(test_template_config_content)
            temp_path = Path(f.name)

        yield temp_path

        # Cleanup
        if temp_path.exists():
            temp_path.unlink()

    def test_test_template_config_initialization(self, temp_config_file):
        """Test test template configuration initialization."""
        # Set required environment variables for the test template
        env_vars = {
            "QDRANT_URL": "http://localhost:6333",
            "QDRANT_API_KEY": "",
            "QDRANT_COLLECTION_NAME": "test_collection",
            "OPENAI_API_KEY": "test_key",
            "REPO_URL": "https://github.com/example/test-repo.git",
            "REPO_TOKEN": "test_token",
            "CONFLUENCE_URL": "https://test.atlassian.net/wiki",
            "CONFLUENCE_SPACE_KEY": "TEST",
            "CONFLUENCE_TOKEN": "test_token",
            "CONFLUENCE_EMAIL": "test@example.com",
            "JIRA_URL": "https://test.atlassian.net",
            "JIRA_PROJECT_KEY": "TEST",
            "JIRA_TOKEN": "test_token",
            "JIRA_EMAIL": "test@example.com",
        }

        # Set environment variables
        for key, value in env_vars.items():
            os.environ[key] = value

        try:
            # Initialize configuration with test template
            initialize_config(temp_config_file, skip_validation=True)
            settings = get_settings()

            # Test basic configuration access
            assert settings.qdrant_url == "http://localhost:6333"
            assert settings.qdrant_collection_name == "test_collection"
            assert settings.state_db_path == ":memory:"

        finally:
            # Cleanup environment variables
            for key in env_vars:
                if key in os.environ:
                    del os.environ[key]

    def test_test_template_embedding_configuration(
        self, simple_test_template_config_content
    ):
        """Test test template embedding configuration."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(simple_test_template_config_content)
            temp_config_file = Path(f.name)

        os.environ["OPENAI_API_KEY"] = "test_embedding_key"
        os.environ["QDRANT_URL"] = "http://localhost:6333"
        os.environ["QDRANT_COLLECTION_NAME"] = "test_embedding"

        try:
            initialize_config(temp_config_file, skip_validation=True)
            settings = get_settings()

            # Test embedding configuration (smaller values for tests)
            assert settings.global_config.embedding.model == "text-embedding-3-small"
            assert (
                settings.global_config.embedding.batch_size == 10
            )  # Smaller for tests
            assert settings.global_config.embedding.api_key == "test_embedding_key"

        finally:
            for key in ["OPENAI_API_KEY", "QDRANT_URL", "QDRANT_COLLECTION_NAME"]:
                if key in os.environ:
                    del os.environ[key]
            if temp_config_file.exists():
                temp_config_file.unlink()

    def test_test_template_chunking_configuration(
        self, simple_test_template_config_content
    ):
        """Test test template chunking configuration."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(simple_test_template_config_content)
            temp_config_file = Path(f.name)

        os.environ["OPENAI_API_KEY"] = "test_key"
        os.environ["QDRANT_URL"] = "http://localhost:6333"
        os.environ["QDRANT_COLLECTION_NAME"] = "test_chunking"

        try:
            initialize_config(temp_config_file, skip_validation=True)
            settings = get_settings()

            # Test chunking configuration (smaller values for tests)
            assert (
                settings.global_config.chunking.chunk_size == 500
            )  # Smaller for tests
            assert (
                settings.global_config.chunking.chunk_overlap == 50
            )  # Smaller for tests

        finally:
            for key in ["OPENAI_API_KEY", "QDRANT_URL", "QDRANT_COLLECTION_NAME"]:
                if key in os.environ:
                    del os.environ[key]
            if temp_config_file.exists():
                temp_config_file.unlink()

    def test_test_template_file_conversion_configuration(
        self, simple_test_template_config_content
    ):
        """Test test template file conversion configuration."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(simple_test_template_config_content)
            temp_config_file = Path(f.name)

        os.environ["OPENAI_API_KEY"] = "test_conversion_key"
        os.environ["QDRANT_URL"] = "http://localhost:6333"
        os.environ["QDRANT_COLLECTION_NAME"] = "test_conversion"

        try:
            initialize_config(temp_config_file, skip_validation=True)
            settings = get_settings()

            # Test file conversion configuration (smaller limits for tests)
            assert (
                settings.global_config.file_conversion.max_file_size == 10485760
            )  # 10MB for tests
            assert (
                settings.global_config.file_conversion.conversion_timeout == 60
            )  # Shorter for tests
            assert (
                settings.global_config.file_conversion.markitdown.enable_llm_descriptions
                is False
            )  # Disabled for tests
            assert (
                settings.global_config.file_conversion.markitdown.llm_api_key
                == "test_conversion_key"
            )

        finally:
            for key in ["OPENAI_API_KEY", "QDRANT_URL", "QDRANT_COLLECTION_NAME"]:
                if key in os.environ:
                    del os.environ[key]
            if temp_config_file.exists():
                temp_config_file.unlink()

    def test_test_template_state_management_configuration(
        self, simple_test_template_config_content
    ):
        """Test test template state management configuration."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(simple_test_template_config_content)
            temp_config_file = Path(f.name)

        os.environ["OPENAI_API_KEY"] = "test_key"
        os.environ["QDRANT_URL"] = "http://localhost:6333"
        os.environ["QDRANT_COLLECTION_NAME"] = "test_state"

        try:
            initialize_config(temp_config_file, skip_validation=True)
            settings = get_settings()

            # Test state management configuration (test-specific values)
            assert (
                settings.global_config.state_management.database_path == ":memory:"
            )  # In-memory for tests
            assert (
                settings.global_config.state_management.table_prefix
                == "test_qdrant_loader_"
            )  # Test prefix

            # Test connection pool configuration (smaller values for tests)
            connection_pool = settings.global_config.state_management.connection_pool
            assert connection_pool["size"] == 1  # Single connection for tests
            assert connection_pool["timeout"] == 5  # Shorter timeout for tests

        finally:
            for key in ["OPENAI_API_KEY", "QDRANT_URL", "QDRANT_COLLECTION_NAME"]:
                if key in os.environ:
                    del os.environ[key]
            if temp_config_file.exists():
                temp_config_file.unlink()

    def test_test_template_sources_configuration(self, temp_config_file):
        """Test test template sources configuration."""
        # Set all required environment variables
        env_vars = {
            "QDRANT_URL": "http://localhost:6333",
            "QDRANT_COLLECTION_NAME": "test_sources",
            "OPENAI_API_KEY": "test_key",
            "REPO_URL": "https://github.com/example/test-repo.git",
            "REPO_TOKEN": "test_repo_token",
            "CONFLUENCE_URL": "https://test.atlassian.net/wiki",
            "CONFLUENCE_SPACE_KEY": "TEST",
            "CONFLUENCE_TOKEN": "test_confluence_token",
            "CONFLUENCE_EMAIL": "test@example.com",
            "JIRA_URL": "https://test.atlassian.net",
            "JIRA_PROJECT_KEY": "TEST",
            "JIRA_TOKEN": "test_jira_token",
            "JIRA_EMAIL": "test@example.com",
        }

        for key, value in env_vars.items():
            os.environ[key] = value

        try:
            initialize_config(temp_config_file, skip_validation=True)
            settings = get_settings()

            # Test sources configuration
            default_project = settings.projects_config.projects.get("default")
            assert default_project is not None
            sources = default_project.sources

            # Test Git source
            assert "git" in sources.to_dict()
            git_sources = sources.to_dict()["git"]
            assert "test-repo" in git_sources

            # Test Confluence source
            assert "confluence" in sources.to_dict()
            confluence_sources = sources.to_dict()["confluence"]
            assert "test-space" in confluence_sources

            # Test Jira source
            assert "jira" in sources.to_dict()
            jira_sources = sources.to_dict()["jira"]
            assert "test-project" in jira_sources

        finally:
            # Cleanup environment variables
            for key in env_vars:
                if key in os.environ:
                    del os.environ[key]

    def test_test_template_variable_substitution(
        self, simple_test_template_config_content
    ):
        """Test that test template variables are properly substituted."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(simple_test_template_config_content)
            temp_config_file = Path(f.name)

        # Set environment variables with specific test values
        test_env_vars = {
            "QDRANT_URL": "http://test-qdrant:6333",
            "QDRANT_COLLECTION_NAME": "custom_test_collection",
            "OPENAI_API_KEY": "custom_test_api_key",
        }

        for key, value in test_env_vars.items():
            os.environ[key] = value

        try:
            initialize_config(temp_config_file, skip_validation=True)
            settings = get_settings()

            # Verify variable substitution worked
            assert settings.qdrant_url == "http://test-qdrant:6333"
            assert settings.qdrant_collection_name == "custom_test_collection"
            assert settings.global_config.embedding.api_key == "custom_test_api_key"

        finally:
            for key in test_env_vars:
                if key in os.environ:
                    del os.environ[key]
            if temp_config_file.exists():
                temp_config_file.unlink()

    @pytest.fixture
    def simple_test_template_config_content(self):
        """Simple test template configuration content without sources."""
        return """
global:
  qdrant:
    url: "${QDRANT_URL}"
    api_key: "${QDRANT_API_KEY}"
    collection_name: "${QDRANT_COLLECTION_NAME}"
    
  chunking:
    chunk_size: 500
    chunk_overlap: 50
    
  embedding:
    model: text-embedding-3-small
    api_key: "${OPENAI_API_KEY}"
    batch_size: 10
    
  state_management:
    database_path: ":memory:"
    table_prefix: "test_qdrant_loader_"
    connection_pool:
      size: 1
      timeout: 5
  
  file_conversion:
    max_file_size: 10485760
    conversion_timeout: 60
    markitdown:
      enable_llm_descriptions: false
      llm_model: "gpt-4o"
      llm_endpoint: "https://api.openai.com/v1"
      llm_api_key: "${OPENAI_API_KEY}"

projects:
  default:
    display_name: "Simple Test Template Project"
    description: "Default project for simple test template configuration testing"
    sources: {}
"""
