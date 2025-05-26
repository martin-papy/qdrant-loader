"""Tests for the AsyncIngestionPipeline."""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from qdrant_loader.config import Settings, SourcesConfig
from qdrant_loader.core.async_ingestion_pipeline import AsyncIngestionPipeline
from qdrant_loader.core.qdrant_manager import QdrantManager
from qdrant_loader.core.state.state_manager import StateManager


class TestAsyncIngestionPipeline:
    """Test cases for the AsyncIngestionPipeline."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=Settings)
        settings.global_config = Mock()
        settings.global_config.state_management = Mock()
        settings.sources_config = SourcesConfig()
        return settings

    @pytest.fixture
    def mock_qdrant_manager(self):
        """Create mock QdrantManager."""
        return Mock(spec=QdrantManager)

    @pytest.fixture
    def mock_state_manager(self):
        """Create mock StateManager."""
        return Mock(spec=StateManager)

    def test_initialization_with_new_architecture(
        self, mock_settings, mock_qdrant_manager
    ):
        """Test that the pipeline initializes correctly with the new architecture."""
        with (
            patch(
                "qdrant_loader.core.async_ingestion_pipeline.PipelineComponentsFactory"
            ) as mock_factory,
            patch(
                "qdrant_loader.core.async_ingestion_pipeline.PipelineOrchestrator"
            ) as mock_orchestrator,
            patch(
                "qdrant_loader.core.async_ingestion_pipeline.ResourceManager"
            ) as mock_resource_manager,
            patch(
                "qdrant_loader.core.async_ingestion_pipeline.IngestionMonitor"
            ) as mock_monitor,
            patch("qdrant_loader.core.async_ingestion_pipeline.prometheus_metrics"),
        ):

            # Setup mocks
            mock_factory_instance = Mock()
            mock_factory.return_value = mock_factory_instance
            mock_components = Mock()
            mock_factory_instance.create_components.return_value = mock_components

            # Create pipeline
            pipeline = AsyncIngestionPipeline(
                settings=mock_settings,
                qdrant_manager=mock_qdrant_manager,
                max_chunk_workers=5,
                max_embed_workers=2,
                enable_metrics=True,
            )

            # Verify initialization
            assert pipeline.settings == mock_settings
            assert pipeline.qdrant_manager == mock_qdrant_manager
            assert pipeline.pipeline_config.max_chunk_workers == 5
            assert pipeline.pipeline_config.max_embed_workers == 2
            assert pipeline.pipeline_config.enable_metrics is True

            # Verify factory was called
            mock_factory_instance.create_components.assert_called_once()

            # Verify orchestrator was created
            mock_orchestrator.assert_called_once_with(mock_settings, mock_components)

    def test_backward_compatibility_interface(self, mock_settings, mock_qdrant_manager):
        """Test that the pipeline maintains backward compatibility."""
        with (
            patch(
                "qdrant_loader.core.async_ingestion_pipeline.PipelineComponentsFactory"
            ),
            patch("qdrant_loader.core.async_ingestion_pipeline.PipelineOrchestrator"),
            patch("qdrant_loader.core.async_ingestion_pipeline.ResourceManager"),
            patch("qdrant_loader.core.async_ingestion_pipeline.IngestionMonitor"),
            patch("qdrant_loader.core.async_ingestion_pipeline.prometheus_metrics"),
        ):

            # Create pipeline with legacy parameters
            pipeline = AsyncIngestionPipeline(
                settings=mock_settings,
                qdrant_manager=mock_qdrant_manager,
                embedding_cache="legacy_cache",  # Legacy parameter
                max_chunk_workers=10,
                max_embed_workers=4,
                max_upsert_workers=4,
                queue_size=1000,
                upsert_batch_size=100,
                enable_metrics=False,
            )

            # Verify legacy properties work
            assert pipeline.embedding_cache == "legacy_cache"
            assert hasattr(pipeline, "_shutdown_event")
            assert hasattr(pipeline, "_active_tasks")
            assert hasattr(pipeline, "_cleanup_done")

            # Verify legacy methods exist
            assert hasattr(pipeline, "_cleanup")
            assert hasattr(pipeline, "_handle_sigint")
            assert hasattr(pipeline, "_handle_sigterm")

    @pytest.mark.asyncio
    async def test_process_documents_uses_orchestrator(
        self, mock_settings, mock_qdrant_manager
    ):
        """Test that process_documents delegates to the orchestrator."""
        with (
            patch(
                "qdrant_loader.core.async_ingestion_pipeline.PipelineComponentsFactory"
            ),
            patch(
                "qdrant_loader.core.async_ingestion_pipeline.PipelineOrchestrator"
            ) as mock_orchestrator_class,
            patch("qdrant_loader.core.async_ingestion_pipeline.ResourceManager"),
            patch(
                "qdrant_loader.core.async_ingestion_pipeline.IngestionMonitor"
            ) as mock_monitor_class,
            patch("qdrant_loader.core.async_ingestion_pipeline.prometheus_metrics"),
        ):

            # Setup mocks
            mock_orchestrator = Mock()
            mock_orchestrator.process_documents = AsyncMock(return_value=[])
            mock_orchestrator_class.return_value = mock_orchestrator

            mock_monitor = Mock()
            mock_monitor.clear_metrics = Mock()
            mock_monitor.start_operation = Mock()
            mock_monitor.end_operation = Mock()
            mock_monitor_class.return_value = mock_monitor

            # Create pipeline
            pipeline = AsyncIngestionPipeline(
                settings=mock_settings, qdrant_manager=mock_qdrant_manager
            )

            # Call process_documents
            sources_config = SourcesConfig()
            result = await pipeline.process_documents(
                sources_config=sources_config, source_type="git", source="test_repo"
            )

            # Verify orchestrator was called
            mock_orchestrator.process_documents.assert_called_once_with(
                sources_config=sources_config, source_type="git", source="test_repo"
            )

            # Verify metrics were handled
            mock_monitor.clear_metrics.assert_called_once()
            mock_monitor.start_operation.assert_called_once()
            mock_monitor.end_operation.assert_called_once()

            assert result == []

    async def test_cleanup_delegates_to_resource_manager(
        self, mock_settings, mock_qdrant_manager
    ):
        """Test that cleanup delegates to the resource manager."""
        with (
            patch(
                "qdrant_loader.core.async_ingestion_pipeline.PipelineComponentsFactory"
            ),
            patch("qdrant_loader.core.async_ingestion_pipeline.PipelineOrchestrator"),
            patch(
                "qdrant_loader.core.async_ingestion_pipeline.ResourceManager"
            ) as mock_resource_manager_class,
            patch(
                "qdrant_loader.core.async_ingestion_pipeline.IngestionMonitor"
            ) as mock_monitor_class,
            patch(
                "qdrant_loader.core.async_ingestion_pipeline.prometheus_metrics"
            ) as mock_prometheus,
        ):

            # Setup mocks
            mock_resource_manager = Mock()
            mock_resource_manager.cleanup = AsyncMock()
            mock_resource_manager_class.return_value = mock_resource_manager

            mock_monitor = Mock()
            mock_monitor.save_metrics = Mock()
            mock_monitor_class.return_value = mock_monitor

            mock_prometheus.stop_metrics_server = Mock()

            # Create pipeline
            pipeline = AsyncIngestionPipeline(
                settings=mock_settings, qdrant_manager=mock_qdrant_manager
            )

            # Call cleanup
            await pipeline.cleanup()

            # Verify cleanup was handled
            mock_monitor.save_metrics.assert_called_once()
            mock_prometheus.stop_metrics_server.assert_called_once()

    def test_configuration_validation(self, mock_qdrant_manager):
        """Test that configuration validation works correctly."""
        # Test with invalid settings (no global_config)
        invalid_settings = Mock(spec=Settings)
        invalid_settings.global_config = None

        with pytest.raises(ValueError, match="Global configuration not available"):
            AsyncIngestionPipeline(
                settings=invalid_settings, qdrant_manager=mock_qdrant_manager
            )

    def test_pipeline_config_creation(self, mock_settings, mock_qdrant_manager):
        """Test that PipelineConfig is created correctly from parameters."""
        with (
            patch(
                "qdrant_loader.core.async_ingestion_pipeline.PipelineComponentsFactory"
            ),
            patch("qdrant_loader.core.async_ingestion_pipeline.PipelineOrchestrator"),
            patch("qdrant_loader.core.async_ingestion_pipeline.ResourceManager"),
            patch("qdrant_loader.core.async_ingestion_pipeline.IngestionMonitor"),
            patch("qdrant_loader.core.async_ingestion_pipeline.prometheus_metrics"),
        ):

            pipeline = AsyncIngestionPipeline(
                settings=mock_settings,
                qdrant_manager=mock_qdrant_manager,
                max_chunk_workers=15,
                max_embed_workers=8,
                max_upsert_workers=6,
                queue_size=2000,
                upsert_batch_size=200,
                enable_metrics=True,
            )

            config = pipeline.pipeline_config
            assert config.max_chunk_workers == 15
            assert config.max_embed_workers == 8
            assert config.max_upsert_workers == 6
            assert config.queue_size == 2000
            assert config.upsert_batch_size == 200
            assert config.enable_metrics is True
