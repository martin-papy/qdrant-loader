"""Test environment variable substitution in projects.yaml configuration."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from qdrant_loader.config.multi_file_loader import MultiFileConfigLoader


class TestProjectsEnvironmentSubstitution:
    """Test environment variable substitution in projects configuration."""

    def test_repo_url_substitution_before_validation(self):
        """Test that REPO_URL is properly substituted BEFORE validation in projects.yaml."""
        # Test environment variables
        test_env_vars = {
            "QDRANT_URL": "http://test-qdrant:6333",
            "QDRANT_COLLECTION_NAME": "test_collection", 
            "QDRANT_API_KEY": "",
            "OPENAI_API_KEY": "test-openai-key",
            "REPO_URL": "https://github.com/test/repo.git",  # The key variable being tested
            "EMBEDDING_PROVIDER": "openai",
            "EMBEDDING_ENDPOINT": "https://api.openai.com/v1",
            "EMBEDDING_MODEL": "text-embedding-3-small",
            "EMBEDDING_TOKENIZER": "cl100k_base",
            "EMBEDDING_VECTOR_SIZE": "1536",
            "EMBEDDING_API_KEY": "test-openai-key",
        }

        # Set environment variables for the test
        original_env = {}
        for key, value in test_env_vars.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                config_dir = Path(temp_dir)
                
                # Create minimal connectivity.yaml
                connectivity_config = {
                    "qdrant": {
                        "url": "${QDRANT_URL}",
                        "collection_name": "${QDRANT_COLLECTION_NAME}",
                        "api_key": "${QDRANT_API_KEY}",
                    },
                    "embedding": {
                        "provider": "${EMBEDDING_PROVIDER}",
                        "endpoint": "${EMBEDDING_ENDPOINT}",
                        "model": "${EMBEDDING_MODEL}",
                        "tokenizer": "${EMBEDDING_TOKENIZER}",
                        "vector_size": "${EMBEDDING_VECTOR_SIZE}",
                        "api_key": "${EMBEDDING_API_KEY}",
                    }
                }
                
                # Create projects.yaml with REPO_URL that needs substitution BEFORE validation
                projects_config = {
                    "projects": {
                        "test_project": {
                            "project_id": "test-project",
                            "display_name": "Test Project",
                            "description": "Test project for environment variable substitution",
                            "sources": {
                                "git": {
                                    "test_repo": {
                                        "base_url": "${REPO_URL}",  # This MUST be substituted before URL validation
                                        "branch": "main",
                                        "include_paths": ["*.py", "*.yaml"],
                                        "exclude_paths": ["__pycache__", "*.pyc"],
                                        "file_types": ["*.py", "*.yaml"],
                                        "max_file_size": 1048576,
                                        "token": ""
                                    }
                                }
                            }
                        }
                    }
                }

                # Write configuration files
                with open(config_dir / "connectivity.yaml", "w") as f:
                    yaml.dump(connectivity_config, f)
                    
                with open(config_dir / "projects.yaml", "w") as f:
                    yaml.dump(projects_config, f)

                # Load configuration using MultiFileConfigLoader
                loader = MultiFileConfigLoader(enhanced_validation=True)
                
                # This should work WITHOUT validation errors now that env vars are substituted BEFORE validation
                parsed_config = loader.load_config(
                    config_dir=config_dir,
                    domains={"connectivity", "projects"}
                )

                # Verify that REPO_URL was properly substituted
                assert parsed_config is not None
                
                # Check that the substitution worked in the parsed config
                project_config = parsed_config.projects_config.projects.get("test_project")
                assert project_config is not None, "test_project not found in parsed config"
                
                git_sources = project_config.sources.git
                test_repo = git_sources.get("test_repo")
                assert test_repo is not None, "test_repo not found in git sources"
                
                # The base_url should now be the actual URL, not the environment variable pattern
                actual_base_url = test_repo.base_url
                # Convert Pydantic URL to string for comparison
                actual_base_url_str = str(actual_base_url)
                assert actual_base_url_str == "https://github.com/test/repo.git", (
                    f"Expected REPO_URL to be substituted with 'https://github.com/test/repo.git', "
                    f"but got: {actual_base_url_str}"
                )
                
                # Verify other substitutions also worked
                qdrant_config = parsed_config.global_config.qdrant
                assert qdrant_config.url == "http://test-qdrant:6333"
                assert qdrant_config.collection_name == "test_collection"

        finally:
            # Restore original environment
            for key, original_value in original_env.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value

    def test_missing_env_var_substitution(self):
        """Test behavior when environment variable is not set."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            
            # Create projects.yaml with undefined environment variable
            projects_config = {
                "projects": {
                    "test_project": {
                        "project_id": "test-project",
                        "display_name": "Test Project", 
                        "description": "Test project",
                        "sources": {
                            "git": {
                                "test_repo": {
                                    "base_url": "${UNDEFINED_REPO_URL}",  # This var doesn't exist
                                    "branch": "main",
                                    "include_paths": ["*.py"],
                                    "file_types": ["*.py"],
                                    "max_file_size": 1048576,
                                    "token": ""
                                }
                            }
                        }
                    }
                }
            }

            with open(config_dir / "projects.yaml", "w") as f:
                yaml.dump(projects_config, f)

            loader = MultiFileConfigLoader(enhanced_validation=True)
            
            # This should now fail at validation stage with a clearer error about the unsubstituted variable
            with pytest.raises(Exception) as exc_info:
                loader.load_config(
                    config_dir=config_dir,
                    domains={"projects"}
                )
            
            # The error should mention the unsubstituted environment variable
            error_str = str(exc_info.value)
            assert "${UNDEFINED_REPO_URL}" in error_str or "UNDEFINED_REPO_URL" in error_str

    def test_env_var_with_default_values(self):
        """Test environment variable substitution with default values."""
        # Don't set REPO_URL, so default should be used
        test_env_vars = {
            "QDRANT_URL": "http://test-qdrant:6333",
            "QDRANT_COLLECTION_NAME": "test_collection",
            "QDRANT_API_KEY": "",
            "OPENAI_API_KEY": "test-openai-key",
            "EMBEDDING_PROVIDER": "openai",
            "EMBEDDING_ENDPOINT": "https://api.openai.com/v1", 
            "EMBEDDING_MODEL": "text-embedding-3-small",
            "EMBEDDING_TOKENIZER": "cl100k_base",
            "EMBEDDING_VECTOR_SIZE": "1536",
            "EMBEDDING_API_KEY": "test-openai-key",
        }

        # Set environment variables (but NOT REPO_URL)
        original_env = {}
        for key, value in test_env_vars.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        # Ensure REPO_URL is not set
        original_repo_url = os.environ.get("REPO_URL")
        if "REPO_URL" in os.environ:
            del os.environ["REPO_URL"]

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                config_dir = Path(temp_dir)
                
                # Create connectivity.yaml
                connectivity_config = {
                    "qdrant": {
                        "url": "${QDRANT_URL}",
                        "collection_name": "${QDRANT_COLLECTION_NAME}",
                        "api_key": "${QDRANT_API_KEY}",
                    },
                    "embedding": {
                        "provider": "${EMBEDDING_PROVIDER}",
                        "endpoint": "${EMBEDDING_ENDPOINT}",
                        "model": "${EMBEDDING_MODEL}",
                        "tokenizer": "${EMBEDDING_TOKENIZER}",
                        "vector_size": "${EMBEDDING_VECTOR_SIZE}",
                        "api_key": "${EMBEDDING_API_KEY}",
                    }
                }
                
                # Create projects.yaml with default value syntax
                projects_config = {
                    "projects": {
                        "test_project": {
                            "project_id": "test-project",
                            "display_name": "Test Project",
                            "description": "Test project",
                            "sources": {
                                "git": {
                                    "test_repo": {
                                        "base_url": "${REPO_URL:-https://github.com/default/repo.git}",  # Default value
                                        "branch": "main",
                                        "include_paths": ["*.py"],
                                        "file_types": ["*.py"],
                                        "max_file_size": 1048576,
                                        "token": ""
                                    }
                                }
                            }
                        }
                    }
                }

                with open(config_dir / "connectivity.yaml", "w") as f:
                    yaml.dump(connectivity_config, f)
                    
                with open(config_dir / "projects.yaml", "w") as f:
                    yaml.dump(projects_config, f)

                loader = MultiFileConfigLoader(enhanced_validation=True)
                parsed_config = loader.load_config(
                    config_dir=config_dir,
                    domains={"connectivity", "projects"}
                )

                # Verify that default value was used
                project_config = parsed_config.projects_config.projects.get("test_project")
                assert project_config is not None, "test_project not found in parsed config"
                
                git_sources = project_config.sources.git
                test_repo = git_sources.get("test_repo")
                assert test_repo is not None, "test_repo not found in git sources"
                actual_base_url = test_repo.base_url
                # Convert Pydantic URL to string for comparison
                actual_base_url_str = str(actual_base_url)
                
                assert actual_base_url_str == "https://github.com/default/repo.git", (
                    f"Expected default value to be used, but got: {actual_base_url}"
                )

        finally:
            # Restore original environment
            for key, original_value in original_env.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value
            
            if original_repo_url is not None:
                os.environ["REPO_URL"] = original_repo_url 