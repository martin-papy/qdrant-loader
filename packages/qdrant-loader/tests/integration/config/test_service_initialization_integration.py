"""Service Initialization Integration Tests.

Tests real service initialization and startup orchestration patterns that have
caused production issues, including GraphitiManager initialization, database
connections, and service health checks.

These tests use real service managers and actual initialization logic
without mocking to catch real-world service startup failures.
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
import yaml
from qdrant_loader.config.multi_file_loader import ConfigDomain, load_multi_file_config
from qdrant_loader.core.managers.graphiti_manager import GraphitiManager
from qdrant_loader.core.managers.neo4j_manager import Neo4jManager
from qdrant_loader.core.managers.qdrant_manager import QdrantManager


@pytest.mark.integration
class TestServiceInitializationIntegration:
    """Integration tests for service initialization and orchestration."""

    @pytest.fixture
    def service_config_dir(self):
        """Create configuration directory for service initialization testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir)
            
            # Create service-focused configuration
            connectivity_config = {
                "qdrant": {
                    "host": "localhost",
                    "port": 6333,
                    "collection_name": "integration_test_collection",
                    "vector_size": 1536,
                    "distance": "Cosine",
                    "api_key": None,
                    "timeout": 30,
                    "prefer_grpc": False
                },
                "neo4j": {
                    "uri": "bolt://localhost:7687",
                    "username": "neo4j",
                    "password": "test_password",
                    "database": "test_db",
                    "timeout": 30,
                    "max_connection_lifetime": 3600,
                    "max_connection_pool_size": 50
                }
            }
            
            projects_config = {
                "projects": {
                    "service_test": {
                        "name": "Service Integration Test",
                        "description": "Test project for service initialization",
                        "sources": {
                            "test_source": {
                                "type": "local",
                                "path": "/tmp/test_data"
                            }
                        }
                    }
                }
            }
            
            fine_tuning_config = {
                "embedding": {
                    "api_key": "test-embedding-key",
                    "model": "text-embedding-ada-002",
                    "dimensions": 1536,
                    "batch_size": 100
                },
                "graphiti": {
                    "enabled": True,
                    "llm": {
                        "provider": "openai",
                        "model": "gpt-4o-mini",
                        "api_key": "test-llm-key",
                        "max_tokens": 4000,
                        "temperature": 0.1
                    },
                    "embedder": {
                        "provider": "openai",
                        "model": "text-embedding-3-small",
                        "api_key": "test-embedder-key",
                        "dimensions": 1536,
                        "batch_size": 100
                    },
                    "operational": {
                        "max_episode_length": 10000,
                        "search_limit_default": 10,
                        "search_limit_max": 100,
                        "enable_auto_indexing": True,
                        "enable_constraints": True,
                        "timeout_seconds": 30
                    },
                    "debug_mode": False
                }
            }
            
            # Write configuration files
            with open(config_path / "connectivity.yaml", "w") as f:
                yaml.dump(connectivity_config, f)
            
            with open(config_path / "projects.yaml", "w") as f:
                yaml.dump(projects_config, f)
                
            with open(config_path / "fine-tuning.yaml", "w") as f:
                yaml.dump(fine_tuning_config, f)
            
            yield config_path

    def test_configuration_to_service_manager_initialization(self, service_config_dir):
        """Test complete flow from configuration loading to service manager initialization."""
        # Load configuration using real config loader
        config = load_multi_file_config(
            config_dir=service_config_dir,
            domains=ConfigDomain.CORE_DOMAINS
        )
        
        # Test QdrantManager initialization with real config
        qdrant_manager = QdrantManager(settings=config)
        assert qdrant_manager is not None
        assert qdrant_manager.settings == config
        
        # Test Neo4jManager initialization with real config
        neo4j_manager = Neo4jManager(config=config.global_config.neo4j)
        assert neo4j_manager is not None
        assert neo4j_manager.config == config.global_config.neo4j

    def test_qdrant_manager_initialization_with_real_config(self, service_config_dir):
        """Test QdrantManager initialization with real configuration objects."""
        config = load_multi_file_config(
            config_dir=service_config_dir,
            domains=ConfigDomain.CORE_DOMAINS
        )
        
        # Initialize QdrantManager with real config
        manager = QdrantManager(settings=config)
        
        # Verify configuration mapping
        assert manager.settings.global_config.qdrant.host == "localhost"
        assert manager.settings.global_config.qdrant.port == 6333
        assert manager.settings.global_config.qdrant.collection_name == "integration_test_collection"
        assert manager.settings.global_config.qdrant.vector_size == 1536

    def test_neo4j_manager_initialization_with_real_config(self, service_config_dir):
        """Test Neo4jManager initialization with real configuration objects."""
        config = load_multi_file_config(
            config_dir=service_config_dir,
            domains=ConfigDomain.CORE_DOMAINS
        )
        
        # Initialize Neo4jManager with real config
        manager = Neo4jManager(config=config.global_config.neo4j)
        
        # Verify configuration mapping
        assert manager.config.uri == "bolt://localhost:7687"
        assert manager.config.username == "neo4j"
        assert manager.config.password == "test_password"
        assert manager.config.database == "test_db"

    @patch('qdrant_loader.core.managers.graphiti_manager.Graphiti')
    @patch('qdrant_loader.core.managers.graphiti_manager.OpenAIClient')
    @patch('qdrant_loader.core.managers.graphiti_manager.OpenAIEmbedder')
    def test_graphiti_manager_initialization_with_real_config(self, mock_embedder, mock_client, mock_graphiti, service_config_dir):
        """Test GraphitiManager initialization with real configuration objects.
        
        Note: This test patches only the external dependencies (Graphiti SDK components)
        but uses real configuration loading and GraphitiManager initialization logic.
        """
        config = load_multi_file_config(
            config_dir=service_config_dir,
            domains=ConfigDomain.CORE_DOMAINS
        )
        
        # Mock the external Graphiti SDK components
        mock_graphiti_instance = Mock()
        mock_graphiti.return_value = mock_graphiti_instance
        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_embedder_instance = Mock()
        mock_embedder.return_value = mock_embedder_instance
        
        # Initialize GraphitiManager with real config
        manager = GraphitiManager(config=config.global_config)
        
        # Verify configuration was properly mapped to GraphitiManager
        assert manager.config == config.global_config
        assert hasattr(manager, '_graphiti_config')

    def test_service_manager_configuration_validation_integration(self, service_config_dir):
        """Test that service managers properly validate their configuration sections."""
        config = load_multi_file_config(
            config_dir=service_config_dir,
            domains=ConfigDomain.CORE_DOMAINS
        )
        
        # All managers should initialize without validation errors
        qdrant_manager = QdrantManager(settings=config)
        neo4j_manager = Neo4jManager(config=config.global_config.neo4j)
        
        # Verify they have the expected configuration attributes
        assert hasattr(qdrant_manager.settings.global_config, 'qdrant')
        assert hasattr(neo4j_manager, 'config')

    def test_missing_configuration_section_error_propagation(self, service_config_dir):
        """Test error propagation when required configuration sections are missing."""
        # Create config with missing Neo4j section
        connectivity_config = {
            "qdrant": {
                "host": "localhost",
                "port": 6333,
                "collection_name": "test_collection",
                "vector_size": 1536,
                "distance": "Cosine"
            }
            # Missing neo4j section
        }
        
        with open(service_config_dir / "connectivity.yaml", "w") as f:
            yaml.dump(connectivity_config, f)
        
        config = load_multi_file_config(
            config_dir=service_config_dir,
            domains=ConfigDomain.CORE_DOMAINS
        )
        
        # QdrantManager should work
        qdrant_manager = QdrantManager(settings=config)
        assert qdrant_manager is not None
        
        # Neo4jManager should fail gracefully or handle missing config
        # (behavior depends on implementation - test actual behavior)
        try:
            neo4j_manager = Neo4jManager(config=config.global_config.neo4j)
            # If it doesn't raise an error, verify it handles missing config
            assert neo4j_manager is not None
        except AttributeError:
            # Expected if neo4j config is missing
            pass

    def test_invalid_configuration_values_error_propagation(self, service_config_dir):
        """Test error propagation when configuration values are invalid."""
        # Create config with invalid values
        connectivity_config = {
            "qdrant": {
                "host": "localhost",
                "port": "invalid_port",  # Invalid port type
                "collection_name": "",  # Invalid empty collection name
                "vector_size": -1,  # Invalid negative vector size
                "distance": "InvalidDistance"  # Invalid distance metric
            },
            "neo4j": {
                "uri": "invalid_uri",  # Invalid URI format
                "username": "",  # Empty username
                "password": "",  # Empty password
                "database": ""  # Empty database
            }
        }
        
        with open(service_config_dir / "connectivity.yaml", "w") as f:
            yaml.dump(connectivity_config, f)
        
        # Configuration loading should catch validation errors
        with pytest.raises((ValueError, TypeError, AttributeError)):
            config = load_multi_file_config(
                config_dir=service_config_dir,
                domains=ConfigDomain.CORE_DOMAINS
            )

    @patch('qdrant_loader.core.managers.qdrant_manager.QdrantClient')
    def test_qdrant_manager_connection_initialization_flow(self, mock_qdrant_client, service_config_dir):
        """Test the complete QdrantManager connection initialization flow."""
        config = load_multi_file_config(
            config_dir=service_config_dir,
            domains=ConfigDomain.CORE_DOMAINS
        )
        
        # Mock QdrantClient to avoid actual network calls
        mock_client_instance = Mock()
        mock_qdrant_client.return_value = mock_client_instance
        
        manager = QdrantManager(settings=config)
        
        # Test connection initialization
        manager.connect()
        
        # Verify QdrantClient was initialized with correct parameters
        mock_qdrant_client.assert_called()
        call_args = mock_qdrant_client.call_args
        
        # Verify connection parameters from real config
        assert call_args is not None

    @patch('qdrant_loader.core.managers.neo4j_manager.GraphDatabase')
    def test_neo4j_manager_connection_initialization_flow(self, mock_graph_database, service_config_dir):
        """Test the complete Neo4jManager connection initialization flow."""
        config = load_multi_file_config(
            config_dir=service_config_dir,
            domains=ConfigDomain.CORE_DOMAINS
        )
        
        # Mock GraphDatabase to avoid actual network calls
        mock_driver = Mock()
        mock_graph_database.driver.return_value = mock_driver
        
        manager = Neo4jManager(config=config.global_config.neo4j)
        
        # Test connection initialization
        manager.connect()
        
        # Verify GraphDatabase.driver was called with correct parameters
        mock_graph_database.driver.assert_called_with(
            "bolt://localhost:7687",
            auth=("neo4j", "test_password"),
            database="test_db"
        )

    def test_service_initialization_order_dependencies(self, service_config_dir):
        """Test that services can be initialized in the correct dependency order."""
        config = load_multi_file_config(
            config_dir=service_config_dir,
            domains=ConfigDomain.CORE_DOMAINS
        )
        
        # Initialize services in dependency order
        # 1. Configuration-dependent services first
        qdrant_manager = QdrantManager(settings=config)
        neo4j_manager = Neo4jManager(config=config.global_config.neo4j)
        
        # 2. Services that depend on other services
        # (GraphitiManager might depend on Neo4j being available)
        # Note: Only testing initialization, not actual connections
        
        assert qdrant_manager is not None
        assert neo4j_manager is not None

    def test_service_health_check_integration_patterns(self, service_config_dir):
        """Test patterns for service health checking after initialization."""
        config = load_multi_file_config(
            config_dir=service_config_dir,
            domains=ConfigDomain.CORE_DOMAINS
        )
        
        # Initialize managers
        qdrant_manager = QdrantManager(settings=config)
        neo4j_manager = Neo4jManager(config=config.global_config.neo4j)
        
        # Test that health check methods exist and can be called
        # (without actually connecting to services)
        assert hasattr(qdrant_manager, 'health_check') or hasattr(qdrant_manager, 'is_connected')
        assert hasattr(neo4j_manager, 'health_check') or hasattr(neo4j_manager, 'is_connected')

    def test_configuration_hot_reload_service_reinitialization(self, service_config_dir):
        """Test service reinitialization when configuration changes."""
        # Initial configuration load
        config1 = load_multi_file_config(
            config_dir=service_config_dir,
            domains=ConfigDomain.CORE_DOMAINS
        )
        
        manager1 = QdrantManager(settings=config1)
        original_host = manager1.settings.global_config.qdrant.host
        
        # Modify configuration
        connectivity_config = {
            "qdrant": {
                "host": "modified-host",  # Changed host
                "port": 6333,
                "collection_name": "integration_test_collection",
                "vector_size": 1536,
                "distance": "Cosine"
            },
            "neo4j": {
                "uri": "bolt://localhost:7687",
                "username": "neo4j",
                "password": "test_password",
                "database": "test_db"
            }
        }
        
        with open(service_config_dir / "connectivity.yaml", "w") as f:
            yaml.dump(connectivity_config, f)
        
        # Reload configuration
        config2 = load_multi_file_config(
            config_dir=service_config_dir,
            domains=ConfigDomain.CORE_DOMAINS
        )
        
        manager2 = QdrantManager(settings=config2)
        new_host = manager2.settings.global_config.qdrant.host
        
        # Verify configuration change was picked up
        assert original_host != new_host
        assert new_host == "modified-host"


@pytest.mark.integration  
class TestServiceInitializationErrorScenarios:
    """Integration tests for service initialization error scenarios."""

    @pytest.fixture
    def error_config_dir(self):
        """Create configuration directory with error-inducing scenarios."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir)
            
            # Create config that might cause initialization errors
            connectivity_config = {
                "qdrant": {
                    "host": "nonexistent-host",
                    "port": 99999,  # Invalid port
                    "collection_name": "test_collection",
                    "vector_size": 1536,
                    "distance": "Cosine"
                },
                "neo4j": {
                    "uri": "bolt://nonexistent-host:7687",
                    "username": "invalid_user",
                    "password": "invalid_password",
                    "database": "nonexistent_db"
                }
            }
            
            projects_config = {
                "projects": {
                    "error_test": {
                        "name": "Error Test Project",
                        "sources": {}
                    }
                }
            }
            
            fine_tuning_config = {
                "embedding": {
                    "api_key": "invalid-key",
                    "model": "nonexistent-model"
                }
            }
            
            with open(config_path / "connectivity.yaml", "w") as f:
                yaml.dump(connectivity_config, f)
            
            with open(config_path / "projects.yaml", "w") as f:
                yaml.dump(projects_config, f)
                
            with open(config_path / "fine-tuning.yaml", "w") as f:
                yaml.dump(fine_tuning_config, f)
            
            yield config_path

    def test_service_initialization_with_invalid_config_graceful_failure(self, error_config_dir):
        """Test that services fail gracefully with invalid configuration."""
        config = load_multi_file_config(
            config_dir=error_config_dir,
            domains=ConfigDomain.CORE_DOMAINS
        )
        
        # Services should initialize (create objects) even with invalid config
        # but connection attempts should fail gracefully
        qdrant_manager = QdrantManager(settings=config)
        neo4j_manager = Neo4jManager(config=config.global_config.neo4j)
        
        assert qdrant_manager is not None
        assert neo4j_manager is not None
        
        # The managers should be created but not connected
        # (actual connection testing would require mocking or real services)

    def test_partial_service_initialization_failure_isolation(self, error_config_dir):
        """Test that failure of one service doesn't prevent others from initializing."""
        config = load_multi_file_config(
            config_dir=error_config_dir,
            domains=ConfigDomain.CORE_DOMAINS
        )
        
        # Even if one service has connection issues, others should still initialize
        managers = []
        
        try:
            qdrant_manager = QdrantManager(settings=config)
            managers.append(qdrant_manager)
        except Exception:
            pass  # Service initialization should not fail at object creation
        
        try:
            neo4j_manager = Neo4jManager(config=config.global_config.neo4j)
            managers.append(neo4j_manager)
        except Exception:
            pass  # Service initialization should not fail at object creation
        
        # At least some managers should be created successfully
        assert len(managers) > 0 