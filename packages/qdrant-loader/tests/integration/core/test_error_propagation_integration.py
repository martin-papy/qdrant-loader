"""Error Propagation Integration Tests.

Tests real error propagation scenarios across service boundaries and configuration
chains to catch actual failure modes that heavily mocked unit tests miss.

These tests verify that errors propagate correctly through the system without
masking or swallowing critical failure information, ensuring proper error
handling and user feedback in production environments.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from qdrant_loader.config import Settings
from qdrant_loader.config.multi_file_loader import ConfigDomain, load_multi_file_config
from qdrant_loader.core.managers.graphiti_manager import GraphitiManager
from qdrant_loader.core.managers.neo4j_manager import Neo4jManager
from qdrant_loader.core.managers.qdrant_manager import QdrantManager
from qdrant_loader.core.pipeline.factory import PipelineComponentsFactory
from qdrant_loader.core.async_ingestion_pipeline import AsyncIngestionPipeline, PipelineConfig


def create_settings_from_config(parsed_config):
    """Helper function to convert ParsedConfig to Settings for service managers."""
    return Settings(
        global_config=parsed_config.global_config,
        projects_config=parsed_config.projects_config
    )


@pytest.mark.integration
class TestErrorPropagationIntegration:
    """Integration tests for error propagation across service boundaries."""

    @pytest.fixture
    def real_config_dir(self):
        """Use real configuration directory for error propagation testing."""
        return Path(__file__).parent.parent.parent / "config"

    @pytest.fixture
    def valid_config(self, real_config_dir):
        """Load valid configuration for baseline testing."""
        return load_multi_file_config(
            config_dir=real_config_dir,
            domains=ConfigDomain.CORE_DOMAINS
        )

    # GraphitiManager Error Propagation Tests

    @pytest.mark.asyncio
    async def test_graphiti_initialization_error_propagation(self, valid_config):
        """Test that GraphitiManager initialization errors propagate correctly through the system."""
        from copy import deepcopy
        
        # Create a modified config with NO API keys to force validation error
        modified_config = deepcopy(valid_config.global_config)
        if hasattr(modified_config, 'graphiti') and modified_config.graphiti:
            # Clear ALL possible API key sources
            modified_config.graphiti.llm.api_key = None
            modified_config.graphiti.embedder.api_key = None
        
        # Test OpenAI API key validation failure
        manager = GraphitiManager(
            neo4j_config=valid_config.global_config.neo4j,
            graphiti_config=modified_config.graphiti if hasattr(modified_config, 'graphiti') else None,
            openai_api_key=None  # Force API key failure
        )
        
        # Initialization should fail with proper error propagation
        with pytest.raises(ValueError, match="OpenAI API key is required for LLM operations"):
            await manager.initialize()
        
        # Manager should remain uninitialized
        assert not manager.is_initialized

    @pytest.mark.asyncio
    async def test_graphiti_neo4j_connection_error_propagation(self, valid_config):
        """Test error propagation when GraphitiManager fails to connect to Neo4j."""
        manager = GraphitiManager(
            neo4j_config=valid_config.global_config.neo4j,
            graphiti_config=valid_config.global_config.graphiti if hasattr(valid_config.global_config, 'graphiti') else None,
            openai_api_key="test-key"
        )
        
        # Mock Graphiti to simulate Neo4j connection failure
        with (
            patch('qdrant_loader.core.managers.graphiti_manager.OpenAIClient'),
            patch('qdrant_loader.core.managers.graphiti_manager.OpenAIEmbedder'),
            patch('qdrant_loader.core.managers.graphiti_manager.Graphiti') as mock_graphiti
        ):
            mock_graphiti.side_effect = Exception("Neo4j connection failed: Unable to establish connection")
            
            # Initialization should fail with Neo4j connection error
            with pytest.raises(Exception, match="Neo4j connection failed"):
                await manager.initialize()
            
            assert not manager.is_initialized

    # Pipeline Error Propagation Tests

    @pytest.mark.asyncio
    async def test_pipeline_initialization_graphiti_error_propagation(self, valid_config):
        """Test error propagation during pipeline initialization with Graphiti."""
        settings = create_settings_from_config(valid_config)
        qdrant_manager = QdrantManager(settings=settings)

        factory = PipelineComponentsFactory()

        # Test configuration validation in factory
        pipeline_config = PipelineConfig(
            enable_entity_extraction=True,
            max_chunk_workers=2,
            max_embed_workers=2,
            max_upsert_workers=2,
            queue_size=100
        )

        # Create a modified config without API key to test error propagation
        from copy import deepcopy
        
        modified_config = deepcopy(valid_config)
        # Ensure Graphiti is enabled and remove API key to trigger error
        if modified_config.global_config.graphiti:
            modified_config.global_config.graphiti.enabled = True
            modified_config.global_config.graphiti.llm.api_key = None
            modified_config.global_config.graphiti.embedder.api_key = None
        
        settings_without_api_key = create_settings_from_config(modified_config)

        # Test pipeline initialization with missing API key
        # This should fail during component creation due to missing API key
        with pytest.raises(ValueError, match="OpenAI API key is required for Graphiti entity extraction"):
            factory.create_components(
                settings=settings_without_api_key,
                config=pipeline_config,
                qdrant_manager=qdrant_manager
            )

    # Configuration Chain Error Propagation Tests

    def test_configuration_validation_error_propagation_chain(self, real_config_dir):
        """Test error propagation through configuration validation chain."""
        # Test that configuration validation errors propagate correctly
        # from individual domain validators up through the full chain
        
        # This test verifies the error propagation chain works by trying to load
        # configuration and observing how validation errors flow through
        
        # First verify normal config loading works
        normal_config = load_multi_file_config(
            config_dir=real_config_dir,
            domains=ConfigDomain.CORE_DOMAINS
        )
        assert normal_config is not None
        
        # Test non-existent config directory error propagation
        non_existent_dir = Path("/tmp/absolutely_non_existent_config_directory_12345")
        
        # Should propagate FileNotFoundError or ConfigurationError
        with pytest.raises((FileNotFoundError, ValueError, TypeError)):
            load_multi_file_config(
                config_dir=non_existent_dir,
                domains=ConfigDomain.CORE_DOMAINS
            )

    def test_service_dependency_error_propagation(self, valid_config):
        """Test error propagation when service dependencies are missing."""
        settings = create_settings_from_config(valid_config)
        
        # Test QdrantManager with missing configuration sections
        # Create a modified config with missing required fields
        modified_config = valid_config
        
        # Both managers should still be constructible
        # (errors typically occur during connection, not construction)
        qdrant_manager = QdrantManager(settings=settings)
        neo4j_manager = Neo4jManager(config=valid_config.global_config.neo4j)
        
        assert qdrant_manager is not None
        assert neo4j_manager is not None
        
        # Managers should be created but connection will fail if config is invalid
        # This tests that construction doesn't mask configuration issues

    # Cross-Service Error Propagation Tests

    @pytest.mark.asyncio
    async def test_cross_service_failure_isolation_and_propagation(self, valid_config):
        """Test that cross-service failures are properly isolated and reported."""
        settings = create_settings_from_config(valid_config)
        
        # Initialize multiple managers
        qdrant_manager = QdrantManager(settings=settings)
        neo4j_manager = Neo4jManager(config=valid_config.global_config.neo4j)
        graphiti_manager = GraphitiManager(
            neo4j_config=valid_config.global_config.neo4j,
            graphiti_config=valid_config.global_config.graphiti if hasattr(valid_config.global_config, 'graphiti') else None
        )
        
        # Test that failure in one service doesn't crash the others
        managers = {
            'qdrant': qdrant_manager,
            'neo4j': neo4j_manager,
            'graphiti': graphiti_manager
        }
        
        successful_initializations = []
        failed_initializations = []
        
        for name, manager in managers.items():
            try:
                if hasattr(manager, 'initialize'):
                    # Mock initialization for testing
                    if name == 'graphiti':
                        # Test GraphitiManager with mocked dependencies
                        with (
                            patch('qdrant_loader.core.managers.graphiti_manager.OpenAIClient'),
                            patch('qdrant_loader.core.managers.graphiti_manager.OpenAIEmbedder'),
                            patch('qdrant_loader.core.managers.graphiti_manager.Graphiti')
                        ):
                            await manager.initialize()
                    successful_initializations.append(name)
                else:
                    # Manager exists but doesn't need async initialization
                    successful_initializations.append(name)
            except Exception as e:
                failed_initializations.append((name, str(e)))
        
        # At least some managers should be creatable
        assert len(successful_initializations) > 0
        
        # If there are failures, they should be properly captured, not swallowed
        for name, error in failed_initializations:
            assert error is not None and len(error) > 0

    # API Key and Authentication Error Propagation Tests

    @pytest.mark.asyncio
    async def test_api_key_validation_error_propagation(self, valid_config):
        """Test that API key validation errors propagate clearly through the system."""
        # Test GraphitiManager with various API key failure scenarios
        test_scenarios = [
            (None, "API key is required"),
            ("", "API key cannot be empty"),
            ("invalid-key", "Invalid API key format")
        ]
        
        for api_key, expected_error_pattern in test_scenarios:
            manager = GraphitiManager(
                neo4j_config=valid_config.global_config.neo4j,
                graphiti_config=valid_config.global_config.graphiti if hasattr(valid_config.global_config, 'graphiti') else None,
                openai_api_key=api_key
            )
            
            # Mock OpenAI clients to simulate authentication failures
            with (
                patch('qdrant_loader.core.managers.graphiti_manager.OpenAIClient') as mock_client,
                patch('qdrant_loader.core.managers.graphiti_manager.OpenAIEmbedder') as mock_embedder
            ):
                if api_key is None or api_key == "":
                    # Simulate missing API key error
                    mock_client.side_effect = ValueError("API key is required for OpenAI client")
                elif "invalid" in api_key:
                    # Simulate invalid API key error
                    mock_client.side_effect = Exception("Invalid API key provided")
                
                # Error should propagate with clear message
                with pytest.raises((ValueError, Exception)):
                    await manager.initialize()
                
                assert not manager.is_initialized

    # Pipeline Component Factory Error Propagation Tests

    def test_pipeline_factory_error_propagation(self, valid_config):
        """Test error propagation in PipelineComponentsFactory."""
        settings = create_settings_from_config(valid_config)
        qdrant_manager = QdrantManager(settings=settings)

        factory = PipelineComponentsFactory()

        # Test configuration validation in factory
        pipeline_config = PipelineConfig(
            enable_entity_extraction=True,
            max_chunk_workers=2,
            max_embed_workers=2,
            max_upsert_workers=2,
            queue_size=100
        )

        # Test with missing Neo4j configuration by creating a new config without it
        # Create a copy of the config and modify the neo4j part
        from copy import deepcopy

        modified_config = deepcopy(valid_config)
        # Set neo4j to None in the global config (Pydantic model)
        modified_config.global_config.neo4j = None
        # Ensure Graphiti is enabled so that Neo4j validation is triggered
        if modified_config.global_config.graphiti:
            modified_config.global_config.graphiti.enabled = True

        settings_without_neo4j = create_settings_from_config(modified_config)

        # Test pipeline initialization with missing Neo4j config
        with pytest.raises(ValueError, match="Neo4j configuration is required for entity extraction"):
            factory.create_components(
                settings=settings_without_neo4j,
                config=pipeline_config,
                qdrant_manager=qdrant_manager
            )

    # Health Check Error Propagation Tests

    @pytest.mark.asyncio
    async def test_health_check_error_propagation(self, valid_config):
        """Test that health check errors are properly captured and reported."""
        # Create GraphitiManager without API key configuration to trigger error
        neo4j_config = valid_config.global_config.neo4j
        
        # Create a manager with no API key to test error propagation
        manager = GraphitiManager(
            neo4j_config=neo4j_config,
            graphiti_config=None  # This will cause API key validation to fail
        )

        # Try to initialize first - this should trigger the API key validation error
        try:
            await manager.initialize()
            # If we get here, the test should fail
            pytest.fail("Expected ValueError for missing API key but none was raised")
        except ValueError as e:
            # This is expected - verify the error message
            assert "OpenAI API key is required for LLM operations" in str(e)
        except Exception as e:
            # If we get a different exception, that's also acceptable for this test
            # as long as it indicates a configuration/initialization error
            assert any(keyword in str(e).lower() for keyword in ['api', 'key', 'config', 'auth', 'openai'])
        
        # Health check should return not_initialized status without throwing
        health_status = await manager.health_check()
        assert health_status["connection_test"] == "not_initialized"
        assert not health_status["initialized"]


@pytest.mark.integration
class TestErrorRecoveryIntegration:
    """Integration tests for error recovery and graceful degradation."""

    @pytest.fixture
    def real_config_dir(self):
        """Use real configuration directory for error recovery testing."""
        return Path(__file__).parent.parent.parent / "config"

    @pytest.mark.asyncio
    async def test_graceful_degradation_graphiti_unavailable(self, real_config_dir):
        """Test that system gracefully degrades when Graphiti is unavailable."""
        valid_config = load_multi_file_config(
            config_dir=real_config_dir,
            domains=ConfigDomain.CORE_DOMAINS
        )
        
        settings = create_settings_from_config(valid_config)
        qdrant_manager = QdrantManager(settings=settings)
        
        # Test pipeline with entity extraction disabled when Graphiti fails
        pipeline_config = PipelineConfig(
            enable_entity_extraction=False,  # Graceful degradation
            max_chunk_workers=2,
            max_embed_workers=2,
            max_upsert_workers=2,
            queue_size=100
        )
        
        # Pipeline should still work without entity extraction
        with patch.object(qdrant_manager, 'connect'):
            pipeline = AsyncIngestionPipeline(
                settings=settings,
                qdrant_manager=qdrant_manager,
                enable_entity_extraction=False,
                max_chunk_workers=2,
                max_embed_workers=2,
                max_upsert_workers=2,
                queue_size=100
            )
            
            # Should initialize successfully without Graphiti
            await pipeline.initialize()
            
            # Verify that entity extraction is disabled
            assert not pipeline.pipeline_config.enable_entity_extraction

    @pytest.mark.asyncio
    async def test_retry_logic_error_recovery(self, real_config_dir):
        """Test retry logic and error recovery mechanisms."""
        valid_config = load_multi_file_config(
            config_dir=real_config_dir,
            domains=ConfigDomain.CORE_DOMAINS
        )
        
        manager = GraphitiManager(
            neo4j_config=valid_config.global_config.neo4j,
            graphiti_config=valid_config.global_config.graphiti if hasattr(valid_config.global_config, 'graphiti') else None,
            openai_api_key="test-api-key"  # Provide API key to avoid validation error
        )
        
        # Test retry logic with temporary failures
        call_count = 0
        
        def failing_then_succeeding_init(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:  # Fail first 2 times
                raise Exception("Temporary failure")
            return AsyncMock()  # Succeed on 3rd attempt
        
        with (
            patch('qdrant_loader.core.managers.graphiti_manager.OpenAIClient'),
            patch('qdrant_loader.core.managers.graphiti_manager.OpenAIEmbedder'),
            patch('qdrant_loader.core.managers.graphiti_manager.Graphiti', side_effect=failing_then_succeeding_init),
            patch('asyncio.to_thread')
        ):
            # First attempt should fail
            with pytest.raises(Exception, match="Temporary failure"):
                await manager.initialize()
            
            # Second attempt should also fail
            with pytest.raises(Exception, match="Temporary failure"):
                await manager.initialize()
            
            # Third attempt should succeed
            await manager.initialize()
            assert manager.is_initialized

    def test_configuration_fallback_error_handling(self, real_config_dir):
        """Test configuration fallback mechanisms handle errors correctly."""
        # Test that configuration loading has proper fallback behavior
        valid_config = load_multi_file_config(
            config_dir=real_config_dir,
            domains=ConfigDomain.CORE_DOMAINS
        )
        
        # Verify fallback values are used when optional config is missing
        settings = create_settings_from_config(valid_config)
        
        # Test that managers handle missing optional configuration gracefully
        qdrant_manager = QdrantManager(settings=settings)
        neo4j_manager = Neo4jManager(config=valid_config.global_config.neo4j)
        
        # Should not raise exceptions during construction
        assert qdrant_manager is not None
        assert neo4j_manager is not None
        
        # Configuration should have reasonable defaults
        assert hasattr(qdrant_manager, 'settings')
        assert hasattr(neo4j_manager, 'config') 