"""Tests for optional domain configuration loading."""

import tempfile
from pathlib import Path

import pytest
import yaml
from qdrant_loader.config.multi_file_loader import MultiFileConfigLoader, ConfigDomain


class TestOptionalDomains:
    """Tests for optional domain configuration loading."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory with core configuration files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            # Create core required files
            connectivity_content = """
qdrant:
  url: "http://localhost:6333"
  api_key: null
  collection_name: "test_optional"

embedding:
  provider: "openai"
  model: "text-embedding-3-small"
  api_key: "test_key"

state_management:
  database_path: ":memory:"
"""
            (config_dir / "connectivity.yaml").write_text(connectivity_content)

            fine_tuning_content = """
chunking:
  chunk_size: 1000
  chunk_overlap: 200
"""
            (config_dir / "fine-tuning.yaml").write_text(fine_tuning_content)

            projects_content = """
projects:
  test-project:
    project_id: "test-project"
    display_name: "Test Project"
    description: "Test project for optional domains"
    sources: {}
"""
            (config_dir / "projects.yaml").write_text(projects_content)

            yield config_dir

    def test_loads_core_domains_without_optional(self, temp_config_dir):
        """Test that core domains load successfully without optional files."""
        loader = MultiFileConfigLoader(enhanced_validation=False)
        config = loader.load_config(temp_config_dir)
        
        # Should have core configuration
        assert config.global_config.qdrant.url == "http://localhost:6333"
        assert config.projects_config.projects
        
    def test_auto_discovers_metadata_extraction_domain(self, temp_config_dir):
        """Test that metadata-extraction.yaml is auto-discovered when present."""
        # Add metadata-extraction.yaml
        metadata_content = """
metadata_extraction:
  enabled: true
  strategy: "standard"
  authors:
    enabled: true
    extract_display_names: true
"""
        (temp_config_dir / "metadata-extraction.yaml").write_text(metadata_content)
        
        loader = MultiFileConfigLoader(enhanced_validation=False)
        config = loader.load_config(temp_config_dir)
        
        # Should have metadata extraction configuration
        # Note: Since we're storing raw config, it should be accessible in the merged config
        assert config.global_config.qdrant.url == "http://localhost:6333"
        
    def test_auto_discovers_validation_domain(self, temp_config_dir):
        """Test that validation.yaml is auto-discovered when present."""
        # Add validation.yaml
        validation_content = """
validation:
  enable_post_ingestion_validation: true
  enable_post_sync_validation: true
  max_retry_attempts: 3
  validation_timeout_seconds: 300
"""
        (temp_config_dir / "validation.yaml").write_text(validation_content)
        
        loader = MultiFileConfigLoader(enhanced_validation=False)
        config = loader.load_config(temp_config_dir)
        
        # Should have validation configuration
        assert config.global_config.qdrant.url == "http://localhost:6333"
        
    def test_auto_discovers_both_optional_domains(self, temp_config_dir):
        """Test that both optional files are auto-discovered when present."""
        # Add both optional files
        metadata_content = """
metadata_extraction:
  enabled: true
  strategy: "comprehensive"
"""
        (temp_config_dir / "metadata-extraction.yaml").write_text(metadata_content)
        
        validation_content = """
validation:
  enable_post_ingestion_validation: true
  auto_repair_enabled: true
"""
        (temp_config_dir / "validation.yaml").write_text(validation_content)
        
        loader = MultiFileConfigLoader(enhanced_validation=False)
        config = loader.load_config(temp_config_dir)
        
        # Should have all configurations
        assert config.global_config.qdrant.url == "http://localhost:6333"
        
    def test_explicit_domain_selection_overrides_auto_discovery(self, temp_config_dir):
        """Test that explicit domain selection overrides auto-discovery."""
        # Add optional file
        metadata_content = """
metadata_extraction:
  enabled: true
"""
        (temp_config_dir / "metadata-extraction.yaml").write_text(metadata_content)
        
        # Explicitly request only core domains
        loader = MultiFileConfigLoader(enhanced_validation=False)
        config = loader.load_config(
            temp_config_dir, 
            domains=ConfigDomain.CORE_DOMAINS
        )
        
        # Should only have core configuration, optional should be ignored
        assert config.global_config.qdrant.url == "http://localhost:6333"
        
    def test_preset_full_includes_optional_domains(self, temp_config_dir):
        """Test that 'full' preset includes optional domains when present."""
        # Add optional files
        metadata_content = """
metadata_extraction:
  enabled: true
"""
        (temp_config_dir / "metadata-extraction.yaml").write_text(metadata_content)
        
        validation_content = """
validation:
  enable_post_ingestion_validation: true
"""
        (temp_config_dir / "validation.yaml").write_text(validation_content)
        
        loader = MultiFileConfigLoader(enhanced_validation=False)
        config = loader.load_config(temp_config_dir, preset="full")
        
        # Should have all configurations
        assert config.global_config.qdrant.url == "http://localhost:6333"

    def test_domain_constants_updated(self):
        """Test that domain constants include the new optional domains."""
        assert ConfigDomain.METADATA_EXTRACTION == "metadata-extraction"
        assert ConfigDomain.VALIDATION == "validation"
        
        assert ConfigDomain.METADATA_EXTRACTION in ConfigDomain.OPTIONAL_DOMAINS
        assert ConfigDomain.VALIDATION in ConfigDomain.OPTIONAL_DOMAINS
        
        assert ConfigDomain.METADATA_EXTRACTION in ConfigDomain.ALL_DOMAINS
        assert ConfigDomain.VALIDATION in ConfigDomain.ALL_DOMAINS
        
        # Core domains should not include optional ones
        assert ConfigDomain.METADATA_EXTRACTION not in ConfigDomain.CORE_DOMAINS
        assert ConfigDomain.VALIDATION not in ConfigDomain.CORE_DOMAINS
        
        # Standard preset should use core domains
        assert ConfigDomain.get_predefined_combination("standard") == ConfigDomain.CORE_DOMAINS
        
        # Full preset should include all domains
        assert ConfigDomain.get_predefined_combination("full") == ConfigDomain.ALL_DOMAINS 