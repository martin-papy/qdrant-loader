"""Factory for creating pipeline components."""

import concurrent.futures
from pathlib import Path

from qdrant_loader.config import Settings
from qdrant_loader.core.chunking.chunking_service import ChunkingService
from qdrant_loader.core.embedding.embedding_service import EmbeddingService
from qdrant_loader.core.monitoring.ingestion_metrics import IngestionMonitor
from qdrant_loader.core.qdrant_manager import QdrantManager
from qdrant_loader.core.state.state_manager import StateManager
from qdrant_loader.utils.logging import LoggingConfig

from .config import PipelineConfig
from .document_pipeline import DocumentPipeline
from .orchestrator import PipelineComponents
from .resource_manager import ResourceManager
from .source_filter import SourceFilter
from .source_processor import SourceProcessor
from .workers import ChunkingWorker, EmbeddingWorker, UpsertWorker

logger = LoggingConfig.get_logger(__name__)


class PipelineComponentsFactory:
    """Factory for creating pipeline components."""

    def create_components(
        self,
        settings: Settings,
        config: PipelineConfig,
        qdrant_manager: QdrantManager,
        state_manager: StateManager | None = None,
        resource_manager: ResourceManager | None = None,
    ) -> PipelineComponents:
        """Create all pipeline components.

        Args:
            settings: Application settings
            config: Pipeline configuration
            qdrant_manager: QdrantManager instance
            state_manager: Optional state manager (will create if not provided)
            resource_manager: Optional resource manager (will create if not provided)

        Returns:
            PipelineComponents with all initialized components
        """
        logger.debug("Creating pipeline components")

        # Create resource manager if not provided
        if not resource_manager:
            resource_manager = ResourceManager()
            resource_manager.register_signal_handlers()

        # Create state manager if not provided
        if not state_manager:
            state_manager = StateManager(settings.global_config.state_management)

        # Create core services
        chunking_service = ChunkingService(
            config=settings.global_config, settings=settings
        )
        embedding_service = EmbeddingService(settings)

        # Create thread pool executor for chunking
        chunk_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=config.max_chunk_workers
        )
        resource_manager.set_chunk_executor(chunk_executor)

        # Create performance monitor
        metrics_dir = Path.cwd() / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)
        IngestionMonitor(str(metrics_dir.absolute()))

        # Calculate upsert batch size
        upsert_batch_size = (
            int(config.upsert_batch_size)
            if config.upsert_batch_size is not None
            else embedding_service.batch_size
        )

        # Create workers
        chunking_worker = ChunkingWorker(
            chunking_service=chunking_service,
            chunk_executor=chunk_executor,
            max_workers=config.max_chunk_workers,
            queue_size=config.queue_size,
            shutdown_event=resource_manager.shutdown_event,
        )

        embedding_worker = EmbeddingWorker(
            embedding_service=embedding_service,
            max_workers=config.max_embed_workers,
            queue_size=config.queue_size,
            shutdown_event=resource_manager.shutdown_event,
        )

        upsert_worker = UpsertWorker(
            qdrant_manager=qdrant_manager,
            batch_size=upsert_batch_size,
            max_workers=config.max_upsert_workers,
            queue_size=config.queue_size,
            shutdown_event=resource_manager.shutdown_event,
        )

        # Create document pipeline
        document_pipeline = DocumentPipeline(
            chunking_worker=chunking_worker,
            embedding_worker=embedding_worker,
            upsert_worker=upsert_worker,
        )

        # Create source processor
        source_processor = SourceProcessor(
            shutdown_event=resource_manager.shutdown_event,
            file_conversion_config=(
                settings.global_config.file_conversion
                if settings.global_config
                else None
            ),
        )

        # Create source filter
        source_filter = SourceFilter()

        # Create components container
        components = PipelineComponents(
            document_pipeline=document_pipeline,
            source_processor=source_processor,
            source_filter=source_filter,
            state_manager=state_manager,
        )

        logger.debug("Pipeline components created successfully")
        return components
