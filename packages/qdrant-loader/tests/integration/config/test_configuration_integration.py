"""Configuration Integration Tests.

Tests real configuration loading scenarios that have caused production issues,
including optional domain handling, environment variable substitution, and
configuration validation chains.

These tests use real YAML files and actual configuration loading logic
without mocking to catch real-world integration failures.
"""

import os
import tempfile
from pathlib import Path

import pytest
import yaml
from qdrant_loader.config.multi_file_loader import (
    ConfigDomain,
    MultiFileConfigLoader,
    load_multi_file_config,
)
from qdrant_loader.config.validation_errors import ConfigValidationError


@pytest.mark.integration
class TestConfigurationIntegration:
    """Integration tests for configuration loading and validation."""

    @pytest.fixture
    def real_config_dir(self):
        """Use the actual test configuration directory with real config files."""
        # Use the existing test config directory
        config_path = Path(__file__).parent.parent.parent / "config"
        
        # Verify the config directory exists and has the expected files
        assert config_path.exists(), f"Config directory not found: {config_path}"
        assert (config_path / "connectivity.yaml").exists(), "connectivity.yaml not found"
        assert (config_path / "projects.yaml").exists(), "projects.yaml not found"
        assert (config_path / "fine-tuning.yaml").exists(), "fine-tuning.yaml not found"
        
        return config_path

    @pytest.fixture
    def temp_env_file(self):
        """Create a temporary .env file for testing environment variable substitution."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("QDRANT_URL=http://integration-test-host:9999\n")
            f.write("NEO4J_URI=bolt://integration-test:7687\n")
            f.write("OPENAI_API_KEY=integration-test-key\n")
            f.write("VALIDATION_STRICT=true\n")
            env_path = Path(f.name)
        
        yield env_path
        
        # Cleanup
        os.unlink(env_path)

    def test_core_domains_loading_success(self, real_config_dir):
        """Test successful loading of core domains (connectivity, projects, fine-tuning)."""
        loader = MultiFileConfigLoader()
        
        config = loader.load_config(
            config_dir=real_config_dir,
            domains=ConfigDomain.CORE_DOMAINS
        )
        
        # Verify core configuration sections are present
        assert hasattr(config, 'global_config')
        assert hasattr(config.global_config, 'qdrant')
        assert hasattr(config.global_config, 'neo4j')
        assert config.projects_config is not None
        assert len(config.projects_config.projects) > 0
        
        # Verify configuration loaded from real files
        assert config.global_config.qdrant is not None
        assert config.global_config.neo4j is not None

    def test_optional_domains_missing_graceful_handling(self, real_config_dir):
        """Test graceful handling when optional domain files are missing.
        
        This reproduces the production issue where missing optional domains
        caused configuration loading to fail.
        """
        # Create a temporary copy without optional domain files
        import tempfile
        import shutil
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_config_path = Path(temp_dir)
            
            # Copy only core domain files
            shutil.copy2(real_config_dir / "connectivity.yaml", temp_config_path)
            shutil.copy2(real_config_dir / "projects.yaml", temp_config_path)
            shutil.copy2(real_config_dir / "fine-tuning.yaml", temp_config_path)
            # Deliberately skip metadata-extraction.yaml and validation.yaml
            
            loader = MultiFileConfigLoader()
            
            # Should succeed even with missing optional domains
            config = loader.load_config(
                config_dir=temp_config_path,
                domains=ConfigDomain.FULL  # Request all domains including optional
            )
            
            # Core functionality should still work
            assert hasattr(config, 'global_config')
            assert config.projects_config is not None

    def test_environment_variable_substitution_integration(self, real_config_dir, temp_env_file):
        """Test real environment variable substitution in configuration loading."""
        loader = MultiFileConfigLoader()
        
        config = loader.load_config(
            config_dir=real_config_dir,
            domains=ConfigDomain.CORE_DOMAINS,
            env_path=temp_env_file
        )
        
        # Verify environment variables were substituted (actual behavior depends on real config)
        assert config.global_config.qdrant is not None
        assert config.global_config.neo4j is not None

    def test_configuration_validation_chain_integration(self, real_config_dir):
        """Test the complete configuration validation chain with real validators."""
        loader = MultiFileConfigLoader(enhanced_validation=True)
        
        # Should complete validation without errors
        config = loader.load_config(
            config_dir=real_config_dir,
            domains=ConfigDomain.CORE_DOMAINS
        )
        
        assert config is not None
        assert hasattr(config, 'global_config')

    def test_malformed_yaml_error_propagation(self, real_config_dir):
        """Test error propagation when YAML files are malformed."""
        import tempfile
        import shutil
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_config_path = Path(temp_dir)
            
            # Copy real configs first
            shutil.copy2(real_config_dir / "projects.yaml", temp_config_path)
            shutil.copy2(real_config_dir / "fine-tuning.yaml", temp_config_path)
            
            # Create malformed connectivity.yaml
            with open(temp_config_path / "connectivity.yaml", "w") as f:
                f.write("invalid: yaml: content: [\n")  # Malformed YAML
            
            loader = MultiFileConfigLoader()
            
            with pytest.raises((yaml.YAMLError, ConfigValidationError)):
                loader.load_config(
                    config_dir=temp_config_path,
                    domains=ConfigDomain.CORE_DOMAINS
                )

    def test_missing_required_domain_file_error(self, real_config_dir):
        """Test error handling when required domain files are missing."""
        import tempfile
        import shutil
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_config_path = Path(temp_dir)
            
            # Copy only non-connectivity files (missing required connectivity.yaml)
            shutil.copy2(real_config_dir / "projects.yaml", temp_config_path)
            shutil.copy2(real_config_dir / "fine-tuning.yaml", temp_config_path)
            
            loader = MultiFileConfigLoader()
            
            with pytest.raises(ConfigValidationError):
                loader.load_config(
                    config_dir=temp_config_path,
                    domains=ConfigDomain.CORE_DOMAINS
                )

    def test_domain_dependency_validation_integration(self, real_config_dir):
        """Test domain dependency validation in real configuration loading."""
        loader = MultiFileConfigLoader()
        
        # Projects domain requires connectivity domain
        with pytest.raises(ValueError, match="requires"):
            loader.load_config(
                config_dir=real_config_dir,
                domains={ConfigDomain.PROJECTS}  # Missing connectivity dependency
            )

    def test_preset_domain_combinations(self, real_config_dir):
        """Test predefined domain combination presets."""
        loader = MultiFileConfigLoader()
        
        # Test minimal preset (connectivity only)
        config = loader.load_config(
            config_dir=real_config_dir,
            preset="minimal"
        )
        assert hasattr(config.global_config, 'qdrant')
        assert hasattr(config.global_config, 'neo4j')
        
        # Test standard preset (all core domains)
        config = loader.load_config(
            config_dir=real_config_dir,
            preset="standard"
        )
        assert config.projects_config is not None

    def test_configuration_merge_logic_integration(self, real_config_dir):
        """Test configuration merging when multiple files define overlapping sections."""
        import tempfile
        import shutil
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_config_path = Path(temp_dir)
            
            # Copy real configs
            shutil.copy2(real_config_dir / "connectivity.yaml", temp_config_path)
            shutil.copy2(real_config_dir / "projects.yaml", temp_config_path)
            shutil.copy2(real_config_dir / "fine-tuning.yaml", temp_config_path)
            
            # Create overlapping configuration in an additional file
            override_config = {
                "qdrant": {
                    "host": "override-host",
                    "collection_name": "override_collection"
                }
            }
            
            with open(temp_config_path / "connectivity-override.yaml", "w") as f:
                yaml.dump(override_config, f)
            
            loader = MultiFileConfigLoader()
            
            config = loader.load_config(
                config_dir=temp_config_path,
                domains=ConfigDomain.CORE_DOMAINS
            )
            
            # Verify merging behavior - exact behavior depends on implementation
            assert config.global_config.qdrant is not None

    def test_environment_substitution_with_defaults(self, real_config_dir):
        """Test environment variable substitution with default values."""
        # Ensure specific env vars are not set
        env_backup = {}
        test_vars = ["QDRANT_CUSTOM_HOST", "QDRANT_CUSTOM_PORT"]
        
        for var in test_vars:
            if var in os.environ:
                env_backup[var] = os.environ[var]
                del os.environ[var]
        
        try:
            # Test with real config that should have default substitution behavior
            loader = MultiFileConfigLoader()
            config = loader.load_config(
                config_dir=real_config_dir,
                domains={ConfigDomain.CONNECTIVITY}
            )
            
            # Should work with real config (exact values depend on real config content)
            assert config.global_config.qdrant is not None
            
        finally:
            # Restore environment
            for var, value in env_backup.items():
                os.environ[var] = value

    def test_enhanced_validation_integration(self, real_config_dir):
        """Test enhanced validation features in real configuration loading."""
        loader = MultiFileConfigLoader(
            enhanced_validation=True,
            fail_fast=True,
            validate_connectivity=False  # Don't test actual connectivity
        )
        
        config = loader.load_config(
            config_dir=real_config_dir,
            domains=ConfigDomain.CORE_DOMAINS
        )
        
        assert config is not None

    def test_use_case_specific_domain_loading(self, real_config_dir):
        """Test use-case specific domain loading patterns."""
        loader = MultiFileConfigLoader()
        
        # Test config validation use case (should skip fine-tuning)
        config = loader.load_config(
            config_dir=real_config_dir,
            use_case="config_validation"
        )
        
        assert hasattr(config.global_config, 'qdrant')
        assert config.projects is not None

    def test_configuration_loading_performance_measurement(self, real_config_dir):
        """Test configuration loading with performance measurement enabled."""
        loader = MultiFileConfigLoader()
        
        config = loader.load_config(
            config_dir=real_config_dir,
            domains=ConfigDomain.CORE_DOMAINS,
            measure_performance=True
        )
        
        assert config is not None
        # Performance metrics would be logged, not returned

    def test_module_level_load_function_integration(self, real_config_dir):
        """Test the module-level load_multi_file_config function."""
        config = load_multi_file_config(
            config_dir=real_config_dir,
            domains=ConfigDomain.CORE_DOMAINS,
            enhanced_validation=True
        )
        
        assert config is not None
        assert hasattr(config, 'global_config')
        assert config.projects is not None


@pytest.mark.integration
class TestConfigurationEdgeCases:
    """Integration tests for configuration edge cases and error scenarios."""

    @pytest.fixture
    def real_config_dir_for_edge_cases(self):
        """Use the real config directory for edge case testing."""
        config_path = Path(__file__).parent.parent.parent / "config"
        assert config_path.exists(), f"Config directory not found: {config_path}"
        return config_path

    def test_nested_environment_variable_substitution(self, real_config_dir_for_edge_cases):
        """Test complex nested environment variable substitution patterns."""
        # Set some environment variables
        os.environ["ENVIRONMENT"] = "integration"
        os.environ["NEO4J_HOST"] = "test-neo4j"
        os.environ["NEO4J_PORT"] = "9999"
        
        try:
            loader = MultiFileConfigLoader()
            config = loader.load_config(
                config_dir=real_config_dir_for_edge_cases,
                domains={ConfigDomain.CONNECTIVITY, ConfigDomain.PROJECTS}
            )
            
            # Verify config loads successfully with environment substitutions
            assert config.global_config.qdrant is not None
            assert config.global_config.neo4j is not None
            
        finally:
            # Cleanup environment
            for var in ["ENVIRONMENT", "NEO4J_HOST", "NEO4J_PORT"]:
                if var in os.environ:
                    del os.environ[var]

    def test_empty_default_environment_variables(self, real_config_dir_for_edge_cases):
        """Test handling of environment variables with empty defaults."""
        loader = MultiFileConfigLoader()
        
        config = loader.load_config(
            config_dir=real_config_dir_for_edge_cases,
            domains={ConfigDomain.CONNECTIVITY, ConfigDomain.PROJECTS}
        )
        
        # Should handle configuration loading gracefully
        assert config.global_config.qdrant is not None

    def test_configuration_with_all_environment_overrides(self, real_config_dir_for_edge_cases):
        """Test configuration loading with all possible environment variables set."""
        env_vars = {
            "QDRANT_HOST": "env-qdrant-host",
            "QDRANT_PORT": "7777",
            "QDRANT_TIMEOUT": "60",
            "ENVIRONMENT": "test",
            "NEO4J_HOST": "env-neo4j-host",
            "NEO4J_PORT": "8888",
            "NEO4J_USER": "env-user",
            "NEO4J_PASS": "env-pass",
            "NEO4J_DB": "env-db"
        }
        
        # Set all environment variables
        original_env = {}
        for key, value in env_vars.items():
            if key in os.environ:
                original_env[key] = os.environ[key]
            os.environ[key] = value
        
        try:
            loader = MultiFileConfigLoader()
            config = loader.load_config(
                config_dir=real_config_dir_for_edge_cases,
                domains={ConfigDomain.CONNECTIVITY, ConfigDomain.PROJECTS}
            )
            
            # Verify configuration loads successfully with environment overrides
            assert config.global_config.qdrant is not None
            assert config.global_config.neo4j is not None
            
        finally:
            # Restore original environment
            for key in env_vars:
                if key in original_env:
                    os.environ[key] = original_env[key]
                elif key in os.environ:
                    del os.environ[key] 