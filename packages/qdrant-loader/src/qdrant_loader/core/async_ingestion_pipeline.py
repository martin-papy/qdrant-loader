"""Refactored async ingestion pipeline using the new modular architecture."""

from pathlib import Path

from qdrant_loader.config import Settings, SourcesConfig
from qdrant_loader.core.document import Document
from qdrant_loader.core.monitoring import prometheus_metrics
from qdrant_loader.core.monitoring.ingestion_metrics import IngestionMonitor
from qdrant_loader.core.qdrant_manager import QdrantManager
from qdrant_loader.core.state.state_manager import StateManager
from qdrant_loader.core.project_manager import ProjectManager
from qdrant_loader.utils.logging import LoggingConfig

from .pipeline import (
    PipelineComponentsFactory,
    PipelineConfig,
    PipelineOrchestrator,
    ResourceManager,
)

logger = LoggingConfig.get_logger(__name__)


class AsyncIngestionPipeline:
    """Refactored async ingestion pipeline using modular architecture.

    This class maintains backward compatibility with the original interface
    while using the new modular pipeline architecture internally.
    """

    def __init__(
        self,
        settings: Settings,
        qdrant_manager: QdrantManager,
        state_manager: StateManager | None = None,
        embedding_cache=None,  # Placeholder for future cache (maintained for compatibility)
        max_chunk_workers: int = 10,
        max_embed_workers: int = 4,
        max_upsert_workers: int = 4,
        queue_size: int = 1000,
        upsert_batch_size: int | None = None,
        enable_metrics: bool = False,
        metrics_dir: Path | None = None,  # New parameter for workspace support
    ):
        """Initialize the async ingestion pipeline.

        Args:
            settings: Application settings
            qdrant_manager: QdrantManager instance
            state_manager: Optional state manager
            embedding_cache: Placeholder for future cache (unused)
            max_chunk_workers: Maximum number of chunking workers
            max_embed_workers: Maximum number of embedding workers
            max_upsert_workers: Maximum number of upsert workers
            queue_size: Queue size for workers
            upsert_batch_size: Batch size for upserts
            enable_metrics: Whether to enable metrics server
            metrics_dir: Custom metrics directory (for workspace support)
        """
        self.settings = settings
        self.qdrant_manager = qdrant_manager
        self.embedding_cache = embedding_cache  # Maintained for compatibility

        # Validate global configuration
        if not settings.global_config:
            raise ValueError(
                "Global configuration not available. Please check your configuration file."
            )

        # Create pipeline configuration
        self.pipeline_config = PipelineConfig(
            max_chunk_workers=max_chunk_workers,
            max_embed_workers=max_embed_workers,
            max_upsert_workers=max_upsert_workers,
            queue_size=queue_size,
            upsert_batch_size=upsert_batch_size,
            enable_metrics=enable_metrics,
        )

        # Create resource manager
        self.resource_manager = ResourceManager()
        self.resource_manager.register_signal_handlers()

        # Create state manager if not provided
        self.state_manager = state_manager or StateManager(
            settings.global_config.state_management
        )

        # Initialize project manager for multi-project support
        if not settings.global_config.qdrant:
            raise ValueError(
                "Qdrant configuration is required for project manager initialization"
            )

        self.project_manager = ProjectManager(
            projects_config=settings.projects_config,
            global_collection_name=settings.global_config.qdrant.collection_name,
        )

        # Create pipeline components using factory
        factory = PipelineComponentsFactory()
        self.components = factory.create_components(
            settings=settings,
            config=self.pipeline_config,
            qdrant_manager=qdrant_manager,
            state_manager=self.state_manager,
            resource_manager=self.resource_manager,
        )

        # Create orchestrator with project manager support
        self.orchestrator = PipelineOrchestrator(
            settings, self.components, self.project_manager
        )

        # Initialize performance monitor with custom or default metrics directory
        if metrics_dir:
            # Use provided metrics directory (workspace mode)
            final_metrics_dir = metrics_dir
        else:
            # Use default metrics directory
            final_metrics_dir = Path.cwd() / "metrics"

        final_metrics_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initializing metrics directory at {final_metrics_dir}")
        self.monitor = IngestionMonitor(str(final_metrics_dir.absolute()))

        # Start metrics server if enabled
        if enable_metrics:
            prometheus_metrics.start_metrics_server()

        logger.info("AsyncIngestionPipeline initialized with new modular architecture")

        # Track cleanup state to prevent duplicate cleanup
        self._cleanup_performed = False

    async def initialize(self):
        """Initialize the pipeline (maintained for compatibility)."""
        logger.debug("Pipeline initialization called")

        # Initialize state manager first
        if not self.state_manager._initialized:
            logger.debug("Initializing state manager")
            await self.state_manager.initialize()

        # Initialize project manager
        if not self.project_manager._initialized:
            logger.debug("Initializing project manager")
            if self.state_manager._session_factory:
                async with self.state_manager._session_factory() as session:
                    await self.project_manager.initialize(session)

    async def process_documents(
        self,
        sources_config: SourcesConfig | None = None,
        source_type: str | None = None,
        source: str | None = None,
        project_id: str | None = None,
    ) -> list[Document]:
        """Process documents from all configured sources.

        Args:
            sources_config: Sources configuration to use (deprecated, use project_id instead)
            source_type: Filter by source type
            source: Filter by specific source name
            project_id: Process documents for a specific project

        Returns:
            List of processed documents
        """
        # Ensure the pipeline is initialized
        await self.initialize()

        # Reset metrics for new run
        self.monitor.clear_metrics()

        self.monitor.start_operation(
            "ingestion_process",
            metadata={
                "source_type": source_type,
                "source": source,
                "project_id": project_id,
            },
        )

        try:
            logger.debug("Starting document processing with new pipeline architecture")

            # Use the orchestrator to process documents with project support
            documents = await self.orchestrator.process_documents(
                sources_config=sources_config,
                source_type=source_type,
                source=source,
                project_id=project_id,
            )

            # Update metrics (maintained for compatibility)
            if documents:
                self.monitor.start_batch(
                    "document_batch",
                    batch_size=len(documents),
                    metadata={
                        "source_type": source_type,
                        "source": source,
                        "project_id": project_id,
                    },
                )
                # Note: Success/error counts are handled internally by the new architecture
                self.monitor.end_batch("document_batch", len(documents), 0, [])

            self.monitor.end_operation("ingestion_process")

            logger.debug(
                f"Document processing completed. Processed {len(documents)} documents"
            )
            return documents

        except Exception as e:
            logger.error(f"Document processing failed: {e}", exc_info=True)
            self.monitor.end_operation("ingestion_process", error=str(e))
            raise

    async def cleanup(self):
        """Clean up resources."""
        if self._cleanup_performed:
            return

        logger.info("Cleaning up pipeline resources")
        self._cleanup_performed = True

        try:
            # Save metrics
            if hasattr(self, "monitor"):
                self.monitor.save_metrics()

            # Stop metrics server
            try:
                prometheus_metrics.stop_metrics_server()
            except Exception as e:
                logger.warning(f"Error stopping metrics server: {e}")

            # Use resource manager for cleanup
            if hasattr(self, "resource_manager"):
                await self.resource_manager.cleanup()

            logger.info("Pipeline cleanup completed")
        except Exception as e:
            logger.error(f"Error during pipeline cleanup: {e}")

    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            # Can't await in __del__, so use the sync cleanup method
            self._sync_cleanup()
        except Exception as e:
            logger.error(f"Error in destructor cleanup: {e}")

    def _sync_cleanup(self):
        """Synchronous cleanup for destructor and signal handlers."""
        if self._cleanup_performed:
            return

        logger.info("Cleaning up pipeline resources (sync)")
        self._cleanup_performed = True

        # Save metrics
        try:
            if hasattr(self, "monitor"):
                self.monitor.save_metrics()
        except Exception as e:
            logger.error(f"Error saving metrics: {e}")

        # Stop metrics server
        try:
            prometheus_metrics.stop_metrics_server()
        except Exception as e:
            logger.error(f"Error stopping metrics server: {e}")

        # Use resource manager sync cleanup
        try:
            if hasattr(self, "resource_manager"):
                self.resource_manager._cleanup()
        except Exception as e:
            logger.error(f"Error in resource manager cleanup: {e}")

        logger.info("Pipeline cleanup completed (sync)")

    # Backward compatibility properties
    @property
    def _shutdown_event(self):
        """Backward compatibility property for shutdown event."""
        return self.resource_manager.shutdown_event

    @property
    def _active_tasks(self):
        """Backward compatibility property for active tasks."""
        return self.resource_manager.active_tasks

    @property
    def _cleanup_done(self):
        """Backward compatibility property for cleanup status."""
        return self.resource_manager.cleanup_done

    # Legacy methods maintained for compatibility
    def _cleanup(self):
        """Legacy cleanup method (redirects to sync cleanup)."""
        self._sync_cleanup()

    async def _async_cleanup(self):
        """Legacy async cleanup method (redirects to resource manager)."""
        await self.resource_manager.cleanup()

    def _handle_sigint(self, signum, frame):
        """Legacy signal handler (redirects to resource manager)."""
        self.resource_manager._handle_sigint(signum, frame)

    def _handle_sigterm(self, signum, frame):
        """Legacy signal handler (redirects to resource manager)."""
        self.resource_manager._handle_sigterm(signum, frame)

    def _cancel_all_tasks(self):
        """Legacy task cancellation (redirects to resource manager)."""
        self.resource_manager._cancel_all_tasks()

    def _force_immediate_exit(self):
        """Legacy force exit (redirects to resource manager)."""
        self.resource_manager._force_immediate_exit()
