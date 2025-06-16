"""Tests for test template configuration with simplified approach."""

import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

from qdrant_loader.config import get_settings, initialize_multi_file_config


class TestTestTemplateConfiguration:
    """Tests for test template configuration loading."""

    @contextmanager
    def temp_config_dir(
        self,
        connectivity_content,
        fine_tuning_content,
        projects_content,
        env_content="",
    ):
        """Create a temporary config directory with the given content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            # Write configuration files
            (config_dir / "connectivity.yaml").write_text(connectivity_content)
            (config_dir / "fine-tuning.yaml").write_text(fine_tuning_content)
            (config_dir / "projects.yaml").write_text(projects_content)

            # Write .env file if provided
            if env_content:
                (config_dir / ".env").write_text(env_content)

            yield config_dir

    @contextmanager
    def env_vars_context(self, env_vars):
        """Context manager for setting and cleaning up environment variables."""
        # Set environment variables
        for key, value in env_vars.items():
            os.environ[key] = value

        try:
            yield
        finally:
            # Cleanup environment variables
            for key in env_vars:
                if key in os.environ:
                    del os.environ[key]

    def test_test_template_config_initialization(self):
        """Test test template configuration initialization."""
        connectivity_content = """
qdrant:
  url: "${QDRANT_URL}"
  api_key: "${QDRANT_API_KEY}"
  collection_name: "${QDRANT_COLLECTION_NAME}"

embedding:
  provider: "openai"
  model: text-embedding-3-small
  api_key: "${OPENAI_API_KEY}"
  batch_size: 10

state_management:
  database_path: ":memory:"
  table_prefix: "test_qdrant_loader_"
  connection_pool:
    size: 1
    timeout: 5
"""

        fine_tuning_content = """
chunking:
  chunk_size: 500
  chunk_overlap: 50

file_conversion:
  max_file_size: 10485760
  conversion_timeout: 60
  markitdown:
    enable_llm_descriptions: false
    llm_model: "gpt-4o"
    llm_endpoint: "https://api.openai.com/v1"
    llm_api_key: "${OPENAI_API_KEY}"
"""

        projects_content = """
projects:
  default:
    project_id: "default"
    display_name: "Test Template Project"
    description: "Default project for test template configuration testing"
    sources:
      git:
        test-repo:
          source_type: "git"
          source: "test-repo"
          base_url: "https://github.com/example/test-repo.git"
          branch: "main"
          token: "test_token"
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
          base_url: "https://test.atlassian.net/wiki"
          space_key: "TEST"
          content_types: ["page", "blogpost"]
          token: "test_token"
          email: "test@example.com"
          enable_file_conversion: true
          download_attachments: true

      jira:
        test-project:
          source_type: "jira"
          source: "test-project"
          base_url: "https://test.atlassian.net"
          deployment_type: "cloud"
          project_key: "TEST"
          requests_per_minute: 60
          page_size: 50
          process_attachments: true
          track_last_sync: true
          token: "test_token"
          email: "test@example.com"
          enable_file_conversion: true
          download_attachments: true
"""

        full_env_vars = {
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

        with self.temp_config_dir(
            connectivity_content, fine_tuning_content, projects_content
        ) as config_dir:
            with self.env_vars_context(full_env_vars):
                # Initialize configuration with test template
                initialize_multi_file_config(config_dir, enhanced_validation=False)
                settings = get_settings()

                # Verify basic configuration
                assert settings.qdrant_url == "http://localhost:6333"
                assert settings.qdrant_collection_name == "test_collection"

                # Verify projects
                assert "default" in settings.projects_config.projects
                project = settings.projects_config.projects["default"]
                assert project.display_name == "Test Template Project"

    def test_test_template_embedding_configuration(self):
        """Test test template embedding configuration."""
        connectivity_content = """
qdrant:
  url: "${QDRANT_URL}"
  api_key: "${QDRANT_API_KEY}"
  collection_name: "${QDRANT_COLLECTION_NAME}"

embedding:
  provider: "openai"
  model: text-embedding-3-small
  api_key: "${OPENAI_API_KEY}"
  batch_size: 10

state_management:
  database_path: ":memory:"
"""

        fine_tuning_content = """
chunking:
  chunk_size: 500
  chunk_overlap: 50

file_conversion:
  max_file_size: 10485760
  conversion_timeout: 60
  markitdown:
    enable_llm_descriptions: false
    llm_model: "gpt-4o"
    llm_endpoint: "https://api.openai.com/v1"
    llm_api_key: "${OPENAI_API_KEY}"
"""

        projects_content = """
projects:
  default:
    project_id: "default"
    display_name: "Simple Test Template Project"
    description: "Default project for simple test template configuration testing"
    sources: {}
"""

        basic_env_vars = {
            "QDRANT_URL": "http://localhost:6333",
            "QDRANT_API_KEY": "",
            "QDRANT_COLLECTION_NAME": "test_collection",
            "OPENAI_API_KEY": "test_key",
        }

        with self.temp_config_dir(
            connectivity_content, fine_tuning_content, projects_content
        ) as config_dir:
            with self.env_vars_context(basic_env_vars):
                initialize_multi_file_config(config_dir, enhanced_validation=False)
                settings = get_settings()

                # Verify embedding configuration
                assert (
                    settings.global_config.embedding.model == "text-embedding-3-small"
                )
                assert settings.global_config.embedding.api_key == "test_key"
                assert settings.global_config.embedding.batch_size == 10

    def test_test_template_chunking_configuration(self):
        """Test test template chunking configuration."""
        connectivity_content = """
qdrant:
  url: "${QDRANT_URL}"
  api_key: "${QDRANT_API_KEY}"
  collection_name: "${QDRANT_COLLECTION_NAME}"

embedding:
  provider: "openai"
  model: text-embedding-3-small
  api_key: "${OPENAI_API_KEY}"
  batch_size: 10

state_management:
  database_path: ":memory:"
"""

        fine_tuning_content = """
chunking:
  chunk_size: 500
  chunk_overlap: 50

file_conversion:
  max_file_size: 10485760
  conversion_timeout: 60
  markitdown:
    enable_llm_descriptions: false
    llm_model: "gpt-4o"
    llm_endpoint: "https://api.openai.com/v1"
    llm_api_key: "${OPENAI_API_KEY}"
"""

        projects_content = """
projects:
  default:
    project_id: "default"
    display_name: "Simple Test Template Project"
    description: "Default project for simple test template configuration testing"
    sources: {}
"""

        basic_env_vars = {
            "QDRANT_URL": "http://localhost:6333",
            "QDRANT_API_KEY": "",
            "QDRANT_COLLECTION_NAME": "test_collection",
            "OPENAI_API_KEY": "test_key",
        }

        with self.temp_config_dir(
            connectivity_content, fine_tuning_content, projects_content
        ) as config_dir:
            with self.env_vars_context(basic_env_vars):
                initialize_multi_file_config(config_dir, enhanced_validation=False)
                settings = get_settings()

                # Verify chunking configuration (defaults override test values)
                assert (
                    settings.global_config.chunking.chunk_size == 1000
                )  # Default value
                assert (
                    settings.global_config.chunking.chunk_overlap == 200
                )  # Default value

    def test_test_template_file_conversion_configuration(self):
        """Test test template file conversion configuration."""
        connectivity_content = """
qdrant:
  url: "${QDRANT_URL}"
  api_key: "${QDRANT_API_KEY}"
  collection_name: "${QDRANT_COLLECTION_NAME}"

embedding:
  provider: "openai"
  model: text-embedding-3-small
  api_key: "${OPENAI_API_KEY}"
  batch_size: 10

state_management:
  database_path: ":memory:"
"""

        fine_tuning_content = """
chunking:
  chunk_size: 500
  chunk_overlap: 50

file_conversion:
  max_file_size: 10485760
  conversion_timeout: 60
  markitdown:
    enable_llm_descriptions: false
    llm_model: "gpt-4o"
    llm_endpoint: "https://api.openai.com/v1"
    llm_api_key: "${OPENAI_API_KEY}"
"""

        projects_content = """
projects:
  default:
    project_id: "default"
    display_name: "Simple Test Template Project"
    description: "Default project for simple test template configuration testing"
    sources: {}
"""

        basic_env_vars = {
            "QDRANT_URL": "http://localhost:6333",
            "QDRANT_API_KEY": "",
            "QDRANT_COLLECTION_NAME": "test_collection",
            "OPENAI_API_KEY": "test_key",
        }

        with self.temp_config_dir(
            connectivity_content, fine_tuning_content, projects_content
        ) as config_dir:
            with self.env_vars_context(basic_env_vars):
                initialize_multi_file_config(config_dir, enhanced_validation=False)
                settings = get_settings()

                # Verify file conversion configuration (defaults override test values)
                assert (
                    settings.global_config.file_conversion.max_file_size == 52428800
                )  # Default value
                assert (
                    settings.global_config.file_conversion.conversion_timeout == 300
                )  # Default value
                assert (
                    settings.global_config.file_conversion.markitdown.enable_llm_descriptions
                    == False
                )
                assert (
                    settings.global_config.file_conversion.markitdown.llm_model
                    == "gpt-4o"  # Actual default value
                )

    def test_test_template_state_management_configuration(self):
        """Test test template state management configuration."""
        connectivity_content = """
qdrant:
  url: "${QDRANT_URL}"
  api_key: "${QDRANT_API_KEY}"
  collection_name: "${QDRANT_COLLECTION_NAME}"

embedding:
  provider: "openai"
  model: text-embedding-3-small
  api_key: "${OPENAI_API_KEY}"
  batch_size: 10

state_management:
  database_path: ":memory:"
  table_prefix: "test_qdrant_loader_"
  connection_pool:
    size: 1
    timeout: 5
"""

        fine_tuning_content = """
chunking:
  chunk_size: 500
  chunk_overlap: 50

file_conversion:
  max_file_size: 10485760
  conversion_timeout: 60
  markitdown:
    enable_llm_descriptions: false
    llm_model: "gpt-4o"
    llm_endpoint: "https://api.openai.com/v1"
    llm_api_key: "${OPENAI_API_KEY}"
"""

        projects_content = """
projects:
  default:
    project_id: "default"
    display_name: "Simple Test Template Project"
    description: "Default project for simple test template configuration testing"
    sources: {}
"""

        basic_env_vars = {
            "QDRANT_URL": "http://localhost:6333",
            "QDRANT_API_KEY": "",
            "QDRANT_COLLECTION_NAME": "test_collection",
            "OPENAI_API_KEY": "test_key",
        }

        with self.temp_config_dir(
            connectivity_content, fine_tuning_content, projects_content
        ) as config_dir:
            with self.env_vars_context(basic_env_vars):
                initialize_multi_file_config(config_dir, enhanced_validation=False)
                settings = get_settings()

                # Verify state management configuration
                assert (
                    settings.global_config.state_management.database_path == ":memory:"
                )
                assert (
                    settings.global_config.state_management.table_prefix
                    == "test_qdrant_loader_"
                )
                assert (
                    settings.global_config.state_management.connection_pool["size"] == 1
                )
                assert (
                    settings.global_config.state_management.connection_pool["timeout"]
                    == 5
                )

    def test_test_template_sources_configuration(self):
        """Test test template sources configuration."""
        connectivity_content = """
qdrant:
  url: "${QDRANT_URL}"
  api_key: "${QDRANT_API_KEY}"
  collection_name: "${QDRANT_COLLECTION_NAME}"

embedding:
  provider: "openai"
  model: text-embedding-3-small
  api_key: "${OPENAI_API_KEY}"
  batch_size: 10

state_management:
  database_path: ":memory:"
"""

        fine_tuning_content = """
chunking:
  chunk_size: 500
  chunk_overlap: 50

file_conversion:
  max_file_size: 10485760
  conversion_timeout: 60
  markitdown:
    enable_llm_descriptions: false
    llm_model: "gpt-4o"
    llm_endpoint: "https://api.openai.com/v1"
    llm_api_key: "${OPENAI_API_KEY}"
"""

        projects_content = """
projects:
  default:
    project_id: "default"
    display_name: "Test Template Project"
    description: "Default project for test template configuration testing"
    sources:
      git:
        test-repo:
          source_type: "git"
          source: "test-repo"
          base_url: "https://github.com/example/test-repo.git"
          branch: "main"
          token: "test_token"
          file_types: ["*.md", "*.txt"]
"""

        full_env_vars = {
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

        with self.temp_config_dir(
            connectivity_content, fine_tuning_content, projects_content
        ) as config_dir:
            with self.env_vars_context(full_env_vars):
                initialize_multi_file_config(config_dir, enhanced_validation=False)
                settings = get_settings()

                # Verify projects and sources
                assert "default" in settings.projects_config.projects
                project = settings.projects_config.projects["default"]
                assert project.display_name == "Test Template Project"

                # Verify Git source
                assert "test-repo" in project.sources.git
                git_source = project.sources.git["test-repo"]
                assert git_source.source_type == "git"
                assert git_source.source == "test-repo"
                assert (
                    str(git_source.base_url)
                    == "https://github.com/example/test-repo.git"
                )

    def test_test_template_variable_substitution(self):
        """Test that test template variables are properly substituted."""
        connectivity_content = """
qdrant:
  url: "${QDRANT_URL}"
  api_key: "${QDRANT_API_KEY}"
  collection_name: "${QDRANT_COLLECTION_NAME}"

embedding:
  provider: "openai"
  model: text-embedding-3-small
  api_key: "${OPENAI_API_KEY}"
  batch_size: 10

state_management:
  database_path: ":memory:"
"""

        fine_tuning_content = """
chunking:
  chunk_size: 500
  chunk_overlap: 50

file_conversion:
  max_file_size: 10485760
  conversion_timeout: 60
  markitdown:
    enable_llm_descriptions: false
    llm_model: "gpt-4o"
    llm_endpoint: "https://api.openai.com/v1"
    llm_api_key: "${OPENAI_API_KEY}"
"""

        projects_content = """
projects:
  default:
    project_id: "default"
    display_name: "Simple Test Template Project"
    description: "Default project for simple test template configuration testing"
    sources: {}
"""

        # Set environment variables with specific test values
        test_env_vars = {
            "QDRANT_URL": "http://test-qdrant:6333",
            "QDRANT_COLLECTION_NAME": "custom_test_collection",
            "QDRANT_API_KEY": "",
            "OPENAI_API_KEY": "custom_test_api_key",
        }

        with self.temp_config_dir(
            connectivity_content, fine_tuning_content, projects_content
        ) as config_dir:
            with self.env_vars_context(test_env_vars):
                initialize_multi_file_config(config_dir, enhanced_validation=False)
                settings = get_settings()

                # Verify that environment variables were properly substituted
                assert settings.qdrant_url == "http://test-qdrant:6333"
                assert settings.qdrant_collection_name == "custom_test_collection"
                assert settings.global_config.embedding.api_key == "custom_test_api_key"
