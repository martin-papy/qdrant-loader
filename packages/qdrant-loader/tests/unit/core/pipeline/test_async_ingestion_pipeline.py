"""Tests for the AsyncIngestionPipeline."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from qdrant_loader.config import Settings
from qdrant_loader.core.async_ingestion_pipeline import AsyncIngestionPipeline
from qdrant_loader.core.document import Document
from qdrant_loader.core.qdrant_manager import QdrantManager
from qdrant_loader.core.state.state_manager import StateManager


class TestAsyncIngestionPipeline:
    """Test cases for the AsyncIngestionPipeline."""

    def _setup_path_mocks(self, mock_path):
        """Helper method to properly setup Path mocks."""
        mock_cwd_path = MagicMock()
        mock_metrics_dir = MagicMock()
        mock_cwd_path.__truediv__ = MagicMock(return_value=mock_metrics_dir)
        mock_path.cwd.return_value = mock_cwd_path
        mock_metrics_dir.mkdir = Mock()
        mock_metrics_dir.absolute.return_value = "/test/metrics"
        return mock_metrics_dir

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=Settings)
        settings.global_config = Mock()
        settings.global_config.state_management = Mock()
        settings.global_config.qdrant = Mock()
        settings.global_config.qdrant.collection_name = "test_collection"
        settings.projects_config = Mock()
        return settings

    @pytest.fixture
    def mock_qdrant_manager(self):
        """Create mock QdrantManager."""
        return Mock(spec=QdrantManager)

    @pytest.fixture
    def mock_state_manager(self):
        """Create mock StateManager."""
        return Mock(spec=StateManager)

    @pytest.fixture
    def sample_documents(self):
        """Create sample documents for testing."""
        return [
            Document(
                content="Test content 1",
                url="http://example.com/doc1",
                content_type="text/plain",
                source_type="test",
                source="test_source",
                title="Test Document 1",
                metadata={"source": "test"},
            ),
            Document(
                content="Test content 2",
                url="http://example.com/doc2",
                content_type="text/plain",
                source_type="test",
                source="test_source",
                title="Test Document 2",
                metadata={"source": "test"},
            ),
        ]

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
            patch("qdrant_loader.core.async_ingestion_pipeline.IngestionMonitor"),
            patch("qdrant_loader.core.async_ingestion_pipeline.prometheus_metrics"),
            patch("qdrant_loader.core.async_ingestion_pipeline.Path") as mock_path,
        ):

            # Setup mocks
            mock_factory_instance = Mock()
            mock_factory.return_value = mock_factory_instance
            mock_components = Mock()
            mock_factory_instance.create_components.return_value = mock_components

            mock_resource_manager_instance = Mock()
            mock_resource_manager.return_value = mock_resource_manager_instance

            mock_cwd_path = MagicMock()
            mock_metrics_dir = MagicMock()
            mock_cwd_path.__truediv__ = MagicMock(return_value=mock_metrics_dir)
            mock_path.cwd.return_value = mock_cwd_path
            mock_metrics_dir.mkdir = Mock()
            mock_metrics_dir.absolute.return_value = "/test/metrics"

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
            mock_orchestrator.assert_called_once()
            # Check that the orchestrator was called with settings, components, and project_manager
            call_args = mock_orchestrator.call_args
            assert len(call_args[0]) == 3  # settings, components, project_manager
            assert call_args[0][0] == mock_settings
            assert call_args[0][1] == mock_components
            # The third argument should be a ProjectManager instance

            # Verify resource manager setup
            mock_resource_manager_instance.register_signal_handlers.assert_called_once()

            # Verify metrics directory creation
            mock_metrics_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_initialization_with_state_manager(
        self, mock_settings, mock_qdrant_manager, mock_state_manager
    ):
        """Test initialization with provided state manager."""
        with (
            patch(
                "qdrant_loader.core.async_ingestion_pipeline.PipelineComponentsFactory"
            ) as mock_factory,
            patch("qdrant_loader.core.async_ingestion_pipeline.PipelineOrchestrator"),
            patch("qdrant_loader.core.async_ingestion_pipeline.ResourceManager"),
            patch("qdrant_loader.core.async_ingestion_pipeline.IngestionMonitor"),
            patch("qdrant_loader.core.async_ingestion_pipeline.prometheus_metrics"),
            patch("qdrant_loader.core.async_ingestion_pipeline.Path") as mock_path,
        ):
            mock_factory_instance = Mock()
            mock_factory.return_value = mock_factory_instance
            mock_factory_instance.create_components.return_value = Mock()

            # Setup Path mocks
            self._setup_path_mocks(mock_path)

            pipeline = AsyncIngestionPipeline(
                settings=mock_settings,
                qdrant_manager=mock_qdrant_manager,
                state_manager=mock_state_manager,
            )

            assert pipeline.state_manager == mock_state_manager

    def test_initialization_without_metrics(self, mock_settings, mock_qdrant_manager):
        """Test initialization without metrics enabled."""
        with (
            patch(
                "qdrant_loader.core.async_ingestion_pipeline.PipelineComponentsFactory"
            ) as mock_factory,
            patch("qdrant_loader.core.async_ingestion_pipeline.PipelineOrchestrator"),
            patch("qdrant_loader.core.async_ingestion_pipeline.ResourceManager"),
            patch("qdrant_loader.core.async_ingestion_pipeline.IngestionMonitor"),
            patch(
                "qdrant_loader.core.async_ingestion_pipeline.prometheus_metrics"
            ) as mock_prometheus,
            patch("qdrant_loader.core.async_ingestion_pipeline.Path") as mock_path,
        ):
            mock_factory_instance = Mock()
            mock_factory.return_value = mock_factory_instance
            mock_factory_instance.create_components.return_value = Mock()

            # Setup Path mocks
            self._setup_path_mocks(mock_path)

            AsyncIngestionPipeline(
                settings=mock_settings,
                qdrant_manager=mock_qdrant_manager,
                enable_metrics=False,
            )

            # Verify metrics server was not started
            mock_prometheus.start_metrics_server.assert_not_called()



    @pytest.mark.asyncio
    async def test_initialize_method(self, mock_settings, mock_qdrant_manager):
        """Test the initialize method (no-op in new architecture)."""
        with (
            patch(
                "qdrant_loader.core.async_ingestion_pipeline.PipelineComponentsFactory"
            ),
            patch("qdrant_loader.core.async_ingestion_pipeline.PipelineOrchestrator"),
            patch("qdrant_loader.core.async_ingestion_pipeline.ResourceManager"),
            patch("qdrant_loader.core.async_ingestion_pipeline.IngestionMonitor"),
            patch("qdrant_loader.core.async_ingestion_pipeline.prometheus_metrics"),
            patch("qdrant_loader.core.async_ingestion_pipeline.Path") as mock_path,
        ):
            # Setup Path mocks
            self._setup_path_mocks(mock_path)

            pipeline = AsyncIngestionPipeline(
                settings=mock_settings, qdrant_manager=mock_qdrant_manager
            )

            # Mock the state manager and project manager initialization
            pipeline.state_manager._initialized = True
            pipeline.project_manager._initialized = True

            # Should complete without error (no-op)
            await pipeline.initialize()

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
            patch("qdrant_loader.core.async_ingestion_pipeline.Path") as mock_path,
        ):
            # Setup Path mocks
            self._setup_path_mocks(mock_path)

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

            # Mock the state manager and project manager initialization
            pipeline.state_manager._initialized = True
            pipeline.project_manager._initialized = True

            # Call process_documents
            result = await pipeline.process_documents(
                source_type="git", source="test_repo"
            )

            # Verify orchestrator was called
            mock_orchestrator.process_documents.assert_called_once_with(
                sources_config=None,
                source_type="git",
                source="test_repo",
                project_id=None,
                force=False,
            )

            # Verify metrics were handled
            mock_monitor.clear_metrics.assert_called_once()
            mock_monitor.start_operation.assert_called_once()
            mock_monitor.end_operation.assert_called_once()

            assert result == []

    @pytest.mark.asyncio
    async def test_process_documents_with_documents(
        self, mock_settings, mock_qdrant_manager, sample_documents
    ):
        """Test process_documents when documents are returned."""
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
            patch("qdrant_loader.core.async_ingestion_pipeline.Path") as mock_path,
        ):
            # Setup Path mocks
            self._setup_path_mocks(mock_path)

            # Setup mocks
            mock_orchestrator = Mock()
            mock_orchestrator.process_documents = AsyncMock(
                return_value=sample_documents
            )
            mock_orchestrator_class.return_value = mock_orchestrator

            mock_monitor = Mock()
            mock_monitor.clear_metrics = Mock()
            mock_monitor.start_operation = Mock()
            mock_monitor.end_operation = Mock()
            mock_monitor.start_batch = Mock()
            mock_monitor.end_batch = Mock()
            mock_monitor_class.return_value = mock_monitor

            # Create pipeline
            pipeline = AsyncIngestionPipeline(
                settings=mock_settings, qdrant_manager=mock_qdrant_manager
            )

            # Mock the state manager and project manager initialization
            pipeline.state_manager._initialized = True
            pipeline.project_manager._initialized = True

            # Call process_documents
            result = await pipeline.process_documents(source_type="git")

            # Verify batch metrics were handled
            mock_monitor.start_batch.assert_called_once_with(
                "document_batch",
                batch_size=2,
                metadata={"source_type": "git", "source": None, "project_id": None, "force": False},
            )
            mock_monitor.end_batch.assert_called_once_with("document_batch", 2, 0, [])

            assert result == sample_documents

    @pytest.mark.asyncio
    async def test_process_documents_error_handling(
        self, mock_settings, mock_qdrant_manager
    ):
        """Test error handling in process_documents."""
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
            patch("qdrant_loader.core.async_ingestion_pipeline.Path") as mock_path,
        ):
            # Setup Path mocks
            self._setup_path_mocks(mock_path)

            # Setup mocks to raise an error
            mock_orchestrator = Mock()
            test_error = Exception("Test processing error")
            mock_orchestrator.process_documents = AsyncMock(side_effect=test_error)
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

            # Mock the state manager and project manager initialization
            pipeline.state_manager._initialized = True
            pipeline.project_manager._initialized = True

            # Call process_documents and expect error
            with pytest.raises(Exception, match="Test processing error"):
                await pipeline.process_documents()

            # Verify error was logged in metrics
            mock_monitor.end_operation.assert_called_once_with(
                "ingestion_process", error="Test processing error"
            )

    @pytest.mark.asyncio
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
            patch("qdrant_loader.core.async_ingestion_pipeline.Path"),
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
            # Note: stop_metrics_server may be called during initialization and cleanup
            assert mock_prometheus.stop_metrics_server.call_count >= 1
            mock_resource_manager.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_error_handling(self, mock_settings, mock_qdrant_manager):
        """Test error handling during cleanup."""
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
            patch("qdrant_loader.core.async_ingestion_pipeline.Path") as mock_path,
        ):
            # Setup Path mocks
            self._setup_path_mocks(mock_path)

            # Setup mocks with errors
            mock_resource_manager = Mock()
            mock_resource_manager.cleanup = AsyncMock(
                side_effect=Exception("Cleanup error")
            )
            mock_resource_manager_class.return_value = mock_resource_manager

            mock_monitor = Mock()
            mock_monitor.save_metrics = Mock()
            mock_monitor_class.return_value = mock_monitor

            mock_prometheus.stop_metrics_server = Mock(
                side_effect=Exception("Metrics error")
            )

            # Create pipeline
            pipeline = AsyncIngestionPipeline(
                settings=mock_settings, qdrant_manager=mock_qdrant_manager
            )

            # Cleanup should not raise errors even if components fail
            await pipeline.cleanup()

            # Verify attempts were made
            mock_monitor.save_metrics.assert_called_once()
            # stop_metrics_server might be called multiple times (init + cleanup), so just verify it was called
            assert mock_prometheus.stop_metrics_server.call_count >= 1
            mock_resource_manager.cleanup.assert_called_once()

    def test_destructor_cleanup(self, mock_settings, mock_qdrant_manager):
        """Test destructor calls sync cleanup."""
        with (
            patch(
                "qdrant_loader.core.async_ingestion_pipeline.PipelineComponentsFactory"
            ),
            patch("qdrant_loader.core.async_ingestion_pipeline.PipelineOrchestrator"),
            patch("qdrant_loader.core.async_ingestion_pipeline.ResourceManager"),
            patch("qdrant_loader.core.async_ingestion_pipeline.IngestionMonitor"),
            patch("qdrant_loader.core.async_ingestion_pipeline.prometheus_metrics"),
            patch("qdrant_loader.core.async_ingestion_pipeline.Path"),
        ):
            pipeline = AsyncIngestionPipeline(
                settings=mock_settings, qdrant_manager=mock_qdrant_manager
            )

            # Mock the sync cleanup method
            with patch.object(pipeline, "_sync_cleanup") as mock_sync_cleanup:
                # Trigger destructor
                pipeline.__del__()
                mock_sync_cleanup.assert_called_once()

    def test_sync_cleanup_method(self, mock_settings, mock_qdrant_manager):
        """Test the synchronous cleanup method."""
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
            patch("qdrant_loader.core.async_ingestion_pipeline.Path"),
        ):

            # Setup mocks
            mock_resource_manager = Mock()
            mock_resource_manager._cleanup = Mock()
            mock_resource_manager_class.return_value = mock_resource_manager

            mock_monitor = Mock()
            mock_monitor.save_metrics = Mock()
            mock_monitor_class.return_value = mock_monitor

            mock_prometheus.stop_metrics_server = Mock()

            # Create pipeline
            pipeline = AsyncIngestionPipeline(
                settings=mock_settings, qdrant_manager=mock_qdrant_manager
            )

            # Call sync cleanup
            pipeline._sync_cleanup()

            # Verify sync cleanup was handled
            mock_monitor.save_metrics.assert_called_once()
            # Note: stop_metrics_server may be called during initialization and cleanup
            assert mock_prometheus.stop_metrics_server.call_count >= 1
            mock_resource_manager._cleanup.assert_called_once()

    def test_sync_cleanup_error_handling(self, mock_settings, mock_qdrant_manager):
        """Test error handling in sync cleanup."""
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
            patch("qdrant_loader.core.async_ingestion_pipeline.Path"),
        ):

            # Setup mocks with errors
            mock_resource_manager = Mock()
            mock_resource_manager._cleanup = Mock(
                side_effect=Exception("Sync cleanup error")
            )
            mock_resource_manager_class.return_value = mock_resource_manager

            mock_monitor = Mock()
            mock_monitor.save_metrics = Mock(
                side_effect=Exception("Save metrics error")
            )
            mock_monitor_class.return_value = mock_monitor

            mock_prometheus.stop_metrics_server = Mock(
                side_effect=Exception("Stop metrics error")
            )

            # Create pipeline
            pipeline = AsyncIngestionPipeline(
                settings=mock_settings, qdrant_manager=mock_qdrant_manager
            )

            # Sync cleanup should not raise errors
            pipeline._sync_cleanup()

            # Verify attempts were made
            mock_monitor.save_metrics.assert_called_once()
            # Note: stop_metrics_server may not be called if save_metrics fails first
            mock_resource_manager._cleanup.assert_called_once()





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
            patch("qdrant_loader.core.async_ingestion_pipeline.Path"),
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

    def test_pipeline_config_defaults(self, mock_settings, mock_qdrant_manager):
        """Test pipeline config with default values."""
        with (
            patch(
                "qdrant_loader.core.async_ingestion_pipeline.PipelineComponentsFactory"
            ),
            patch("qdrant_loader.core.async_ingestion_pipeline.PipelineOrchestrator"),
            patch("qdrant_loader.core.async_ingestion_pipeline.ResourceManager"),
            patch("qdrant_loader.core.async_ingestion_pipeline.IngestionMonitor"),
            patch("qdrant_loader.core.async_ingestion_pipeline.prometheus_metrics"),
            patch("qdrant_loader.core.async_ingestion_pipeline.Path"),
        ):

            pipeline = AsyncIngestionPipeline(
                settings=mock_settings,
                qdrant_manager=mock_qdrant_manager,
            )

            config = pipeline.pipeline_config
            assert config.max_chunk_workers == 10  # Default
            assert config.max_embed_workers == 4  # Default
            assert config.max_upsert_workers == 4  # Default
            assert config.queue_size == 1000  # Default
            assert config.upsert_batch_size is None  # Default
            assert config.enable_metrics is False  # Default
