import asyncio
from collections.abc import Mapping
from typing import List, Tuple, Optional, Type
from qdrant_client.http import models
import concurrent.futures
import psutil
import threading
from pathlib import Path
import signal
import atexit

from qdrant_loader.utils.logging import LoggingConfig
from qdrant_loader.config.source_config import SourceConfig
from qdrant_loader.config.state import IngestionStatus
from qdrant_loader.config.types import SourceType
from qdrant_loader.connectors.base import BaseConnector
from qdrant_loader.core.state.state_change_detector import StateChangeDetector
from qdrant_loader.core.monitoring.ingestion_metrics import IngestionMonitor, BatchMetrics

from .document import Document
from .chunking.chunking_service import ChunkingService
from .embedding.embedding_service import EmbeddingService
from .qdrant_manager import QdrantManager
from .state.state_manager import StateManager
from ..config import Settings, SourcesConfig
from ..connectors.confluence import ConfluenceConnector
from ..connectors.git import GitConnector
from ..connectors.jira import JiraConnector
from ..connectors.publicdocs import PublicDocsConnector
from ..connectors.localfile import LocalFileConnector
from .monitoring import prometheus_metrics

logger = LoggingConfig.get_logger(__name__)


class AsyncIngestionPipeline:
    """Blazing fast async ingestion pipeline using pipeline parallelism."""

    def __init__(
        self,
        settings: Settings,
        qdrant_manager: QdrantManager,
        state_manager: Optional[StateManager] = None,
        embedding_cache=None,  # Placeholder for future cache
        max_chunk_workers: int = 2,
        max_embed_workers: int = 4,
        max_upsert_workers: int = 4,
        queue_size: int = 1000,
        upsert_batch_size: Optional[int] = None,
        enable_metrics: bool = False,  # Add flag to control metrics server
    ):
        self.settings = settings
        self.config = settings.global_config
        if not self.config:
            raise ValueError(
                "Global configuration not available. Please check your configuration file."
            )

        # Initialize services
        self.chunking_service = ChunkingService(config=self.config, settings=self.settings)
        self.embedding_service = EmbeddingService(settings)
        self.qdrant_manager = qdrant_manager
        self.state_manager = state_manager or StateManager(self.config.state_management)
        self.embedding_cache = embedding_cache
        self.max_chunk_workers = max_chunk_workers
        self.max_embed_workers = max_embed_workers
        self.max_upsert_workers = max_upsert_workers
        self.queue_size = queue_size
        self.upsert_batch_size = (
            int(upsert_batch_size)
            if upsert_batch_size is not None
            else self.embedding_service.batch_size
        )
        self.chunk_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_chunk_workers
        )

        # Initialize performance monitor with absolute path
        metrics_dir = Path.cwd() / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initializing metrics directory at {metrics_dir}")
        self.monitor = IngestionMonitor(str(metrics_dir.absolute()))

        # Register cleanup handlers
        atexit.register(self._cleanup)
        signal.signal(signal.SIGINT, self._handle_sigint)
        signal.signal(signal.SIGTERM, self._handle_sigterm)

        # Only start metrics server if explicitly enabled
        if enable_metrics:
            prometheus_metrics.start_metrics_server()

    def _cleanup(self):
        """Clean up resources."""
        try:
            logger.info("Cleaning up resources...")
            if hasattr(self, "chunk_executor") and self.chunk_executor:
                self.chunk_executor.shutdown(wait=True)
            self.monitor.save_metrics()
            logger.info("Cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    def _handle_sigint(self, signum, frame):
        """Handle SIGINT signal."""
        logger.info("Received SIGINT, cleaning up...")
        self._cleanup()
        raise KeyboardInterrupt()

    def _handle_sigterm(self, signum, frame):
        """Handle SIGTERM signal."""
        logger.info("Received SIGTERM, cleaning up...")
        self._cleanup()
        raise SystemExit(0)

    async def initialize(self):
        """Initialize the pipeline services."""
        await self.state_manager.initialize()

    async def process_documents(
        self,
        sources_config: SourcesConfig | None = None,
        source_type: str | None = None,
        source: str | None = None,
    ) -> list[Document]:
        """Process documents from all configured sources."""
        # Ensure the pipeline is initialized
        await self.initialize()

        # Reset metrics for new run
        self.monitor.clear_metrics()

        self.monitor.start_operation(
            "ingestion_process", metadata={"source_type": source_type, "source": source}
        )

        try:
            if not sources_config:
                sources_config = self.settings.sources_config

            # Filter sources based on type and name
            filtered_config = self._filter_sources(sources_config, source_type, source)

            # Check if filtered config is empty
            if source_type and not any(
                [
                    filtered_config.git,
                    filtered_config.confluence,
                    filtered_config.jira,
                    filtered_config.publicdocs,
                    filtered_config.localfile,
                ]
            ):
                raise ValueError(f"No sources found for type '{source_type}'")

            documents: list[Document] = []
            deleted_documents: list[Document] = []

            # Process each source type
            if filtered_config.confluence:
                logger.info("Starting to process Confluence sources")
                confluence_docs = await self._process_source_type(
                    filtered_config.confluence, ConfluenceConnector, "Confluence"
                )
                logger.info(
                    f"Completed processing Confluence sources, got {len(confluence_docs)} documents"
                )
                documents.extend(confluence_docs)

            if filtered_config.git:
                logger.info("Starting to process Git sources")
                git_docs = await self._process_source_type(filtered_config.git, GitConnector, "Git")
                logger.info(f"Completed processing Git sources, got {len(git_docs)} documents")
                documents.extend(git_docs)

            if filtered_config.jira:
                logger.info("Starting to process Jira sources")
                jira_docs = await self._process_source_type(
                    filtered_config.jira, JiraConnector, "Jira"
                )
                logger.info(f"Completed processing Jira sources, got {len(jira_docs)} documents")
                documents.extend(jira_docs)

            if filtered_config.publicdocs:
                logger.info("Starting to process PublicDocs sources")
                publicdocs_docs = await self._process_source_type(
                    filtered_config.publicdocs, PublicDocsConnector, "PublicDocs"
                )
                logger.info(
                    f"Completed processing PublicDocs sources, got {len(publicdocs_docs)} documents"
                )
                documents.extend(publicdocs_docs)

            if filtered_config.localfile:
                logger.info("Starting to process LocalFile sources")
                localfile_docs = await self._process_source_type(
                    filtered_config.localfile, LocalFileConnector, "LocalFile"
                )
                logger.info(
                    f"Completed processing LocalFile sources, got {len(localfile_docs)} documents"
                )
                documents.extend(localfile_docs)

            logger.info(f"Completed processing all sources, total documents: {len(documents)}")

            # Detect changes in documents
            if documents:
                logger.debug(f"Starting change detection for {len(documents)} documents")
                try:
                    logger.debug("Initializing StateChangeDetector...")
                    async with StateChangeDetector(self.state_manager) as change_detector:
                        logger.debug("StateChangeDetector initialized, detecting changes...")
                        changes = await change_detector.detect_changes(documents, filtered_config)
                        logger.info(
                            f"Change detection completed. New: {len(changes['new'])}, Updated: {len(changes['updated'])}, Deleted: {len(changes['deleted'])}"
                        )
                        documents = changes["new"] + changes["updated"]
                        deleted_documents = changes["deleted"]
                        logger.debug(
                            f"After change detection: {len(documents)} documents to process, {len(deleted_documents)} documents to delete"
                        )
                except Exception as e:
                    logger.error(f"Error during change detection: {str(e)}", exc_info=True)
                    raise

            if documents or deleted_documents:
                logger.info(
                    f"Processing {len(documents)} documents and {len(deleted_documents)} deleted documents"
                )
                self.monitor.start_batch(
                    "document_batch",
                    batch_size=len(documents),
                    metadata={"source_type": source_type, "source": source},
                )

                # Process documents using the async pipeline
                success_count = 0
                error_count = 0

                if documents:
                    success_count, error_count = await self.process_documents_pipeline(documents)

                # Update batch metrics
                self.monitor.end_batch("document_batch", success_count, error_count, [])

                if deleted_documents:
                    logger.info(f"Processing {len(deleted_documents)} deleted documents")
                    # Process deleted documents
                    for doc in deleted_documents:
                        try:
                            # Delete points from Qdrant
                            await self.qdrant_manager.delete_points_by_document_id([doc.id])
                            # Mark document as deleted in state manager
                            await self.state_manager.mark_document_deleted(
                                doc.source_type, doc.source, doc.id
                            )
                            logger.debug(f"Successfully processed deleted document {doc.id}")
                        except Exception as e:
                            logger.error(f"Error processing deleted document {doc.id}: {e!s}")
                            raise
            else:
                logger.info("No new, updated or deleted documents to process.")

            # Save metrics
            self.monitor.save_metrics()
            logger.info("Metrics saved successfully")

            return documents

        except Exception as e:
            logger.error(
                "Failed to process documents",
                error=str(e),
                error_type=type(e).__name__,
                error_class=e.__class__.__name__,
            )
            # Save metrics even on failure
            self.monitor.save_metrics()
            logger.info("Metrics saved after failure")
            raise
        finally:
            self.monitor.end_operation("ingestion_process", success=True)

    async def _process_source_type(
        self,
        source_configs: Mapping[str, SourceConfig],
        connector_class: Type[BaseConnector],
        source_type: str,
    ) -> list[Document]:
        """Process documents from a specific source type."""
        documents: list[Document] = []
        logger.debug(f"Initializing documents list for {source_type}")

        for name, config in source_configs.items():
            logger.info(f"Configuring {source_type} source: {name}")
            try:
                self.monitor.start_operation(
                    f"source_{name}", metadata={"source_type": source_type, "source": name}
                )

                try:
                    logger.debug(f"Creating connector for {source_type} source: {name}")
                    connector = connector_class(config)
                    logger.debug(
                        f"Connector created, getting documents from {source_type} source: {config.source}"
                    )
                    async with connector:
                        source_docs = await connector.get_documents()
                        logger.debug(
                            f"Got {len(source_docs)} documents from {source_type} source: {config.source}"
                        )
                        documents.extend(source_docs)
                        logger.debug(f"Documents list length after extend: {len(documents)}")
                        logger.debug(
                            f"Updating last ingestion state for {source_type} source: {config.source}"
                        )
                        await self.state_manager.update_last_ingestion(
                            config.source_type,
                            config.source,
                            IngestionStatus.SUCCESS,
                            document_count=len(source_docs),
                        )
                        logger.debug(
                            f"Successfully updated last ingestion state for {source_type} source: {config.source}"
                        )
                        logger.debug(f"Completed processing {source_type} source: {name}")
                        self.monitor.end_operation(f"source_{name}", success=True)
                except Exception as e:
                    logger.error(
                        f"Failed to process {source_type} source {name}",
                        error=str(e),
                        error_type=type(e).__name__,
                        error_class=e.__class__.__name__,
                    )
                    logger.info(
                        f"Updating last ingestion state to FAILED for {source_type} source: {config.source}"
                    )
                    await self.state_manager.update_last_ingestion(
                        config.source_type,
                        config.source,
                        IngestionStatus.FAILED,
                        error_message=str(e),
                    )
                    logger.debug(
                        f"Successfully updated last ingestion state to FAILED for {source_type} source: {config.source}"
                    )
                    self.monitor.end_operation(f"source_{name}", success=False, error=str(e))
                    raise

            except Exception as e:
                logger.error(
                    f"Failed to process {source_type} source {name}",
                    error=str(e),
                    error_type=type(e).__name__,
                    error_class=e.__class__.__name__,
                )
                raise

        logger.debug(f"Final documents list length: {len(documents)}")
        logger.debug(f"Final documents list type: {type(documents)}")
        logger.info(
            f"Completed processing {source_type} sources, total documents: {len(documents)}"
        )
        return documents

    def _filter_sources(
        self,
        sources_config: SourcesConfig,
        source_type: str | None = None,
        source: str | None = None,
    ) -> SourcesConfig:
        """Filter sources based on type and name."""
        if not source_type:
            return sources_config

        filtered = SourcesConfig()

        if source_type == SourceType.GIT:
            if source:
                if source in sources_config.git:
                    filtered.git = {source: sources_config.git[source]}
            else:
                filtered.git = sources_config.git

        elif source_type == SourceType.CONFLUENCE:
            if source:
                if source in sources_config.confluence:
                    filtered.confluence = {source: sources_config.confluence[source]}
            else:
                filtered.confluence = sources_config.confluence

        elif source_type == SourceType.JIRA:
            if source:
                if source in sources_config.jira:
                    filtered.jira = {source: sources_config.jira[source]}
            else:
                filtered.jira = sources_config.jira

        elif source_type == SourceType.PUBLICDOCS:
            if source:
                if source in sources_config.publicdocs:
                    filtered.publicdocs = {source: sources_config.publicdocs[source]}
            else:
                filtered.publicdocs = sources_config.publicdocs

        elif source_type == SourceType.LOCALFILE:
            if source:
                if source in sources_config.localfile:
                    filtered.localfile = {source: sources_config.localfile[source]}
            else:
                filtered.localfile = sources_config.localfile

        return filtered

    async def process_documents_pipeline(self, documents: List[Document]) -> Tuple[int, int]:
        """
        Process documents using a parallel async pipeline:
        - Chunking -> Embedding -> Upsert
        Returns: (success_count, error_count)
        """
        logger.debug(f"[DIAG] Starting process_documents_pipeline with {len(documents)} documents")
        chunk_queue = asyncio.Queue(self.queue_size)
        embed_queue = asyncio.Queue(self.queue_size)
        upsert_queue = asyncio.Queue(self.queue_size)
        errors = []
        success_count = 0
        error_count = 0
        all_tasks = []
        processed_documents = set()  # Track successfully processed documents

        async def chunker_worker(doc):
            logger.debug(f"[DIAG] chunker_worker started for doc {doc.id}")
            try:
                prometheus_metrics.CPU_USAGE.set(psutil.cpu_percent())
                prometheus_metrics.MEMORY_USAGE.set(psutil.virtual_memory().percent)
                prometheus_metrics.CHUNK_QUEUE_SIZE.set(chunk_queue.qsize())
                # Run chunking in a thread pool for true parallelism
                with prometheus_metrics.CHUNKING_DURATION.time():
                    chunks = await asyncio.get_running_loop().run_in_executor(
                        self.chunk_executor, self.chunking_service.chunk_document, doc
                    )
                    for chunk in chunks:
                        # Add document reference to chunk for later state tracking
                        chunk.metadata["parent_document"] = doc
                        await chunk_queue.put(chunk)
                    logger.debug(f"Chunked doc {doc.id} into {len(chunks)} chunks")
            except Exception as e:
                logger.error(f"Chunking failed for doc {doc.id}: {e}")
                errors.append(f"Chunking failed for doc {doc.id}: {e}")
            logger.debug(f"[DIAG] chunker_worker exiting for doc {doc.id}")

        async def chunker():
            logger.debug(f"[DIAG] chunker started")
            tasks = [chunker_worker(doc) for doc in documents]
            await asyncio.gather(*tasks)
            logger.info(
                f"[DIAG] chunker finished, putting {self.max_embed_workers} sentinels into chunk_queue"
            )
            for _ in range(self.max_embed_workers):
                await chunk_queue.put(None)
            logger.debug(f"[DIAG] chunker put all sentinels into chunk_queue")

        async def embedder_worker(worker_id):
            logger.debug(f"[DIAG] embedder_worker {worker_id} started")
            batch_size = self.embedding_service.batch_size
            while True:
                batch = []
                sentinel_received = False

                # Collect batch items
                for _ in range(batch_size):
                    chunk = await chunk_queue.get()
                    if chunk is None:
                        logger.debug(f"[DIAG] embedder_worker {worker_id} received sentinel")
                        sentinel_received = True
                        break
                    batch.append(chunk)

                # If no items in batch and sentinel received, exit
                if not batch and sentinel_received:
                    logger.debug(f"[DIAG] embedder_worker {worker_id} exiting (no batch)")
                    break

                # Process any remaining items in batch
                if batch:
                    try:
                        logger.info(
                            f"[DIAG] embedder_worker {worker_id} processing batch of {len(batch)} items"
                        )
                        with prometheus_metrics.EMBEDDING_DURATION.time():
                            # Add timeout to prevent hanging
                            embeddings = await asyncio.wait_for(
                                self.embedding_service.get_embeddings([c.content for c in batch]),
                                timeout=120.0,  # 2 minute timeout
                            )
                            for chunk, embedding in zip(batch, embeddings):
                                await embed_queue.put((chunk, embedding))
                        logger.info(
                            f"[DIAG] embedder_worker {worker_id} completed batch of {len(batch)} items"
                        )
                    except asyncio.TimeoutError:
                        logger.error(
                            f"[DIAG] embedder_worker {worker_id} timed out processing batch"
                        )
                        for chunk in batch:
                            logger.error(f"Embedding timed out for chunk {chunk.id}")
                            errors.append(f"Embedding timed out for chunk {chunk.id}")
                    except Exception as e:
                        logger.error(
                            f"[DIAG] embedder_worker {worker_id} error processing batch: {e}"
                        )
                        for chunk in batch:
                            logger.error(f"Embedding failed for chunk {chunk.id}: {e}")
                            errors.append(f"Embedding failed for chunk {chunk.id}: {e}")

                # If sentinel received, exit after processing batch
                if sentinel_received:
                    logger.info(
                        f"[DIAG] embedder_worker {worker_id} exiting after processing final batch"
                    )
                    break

            logger.debug(f"[DIAG] embedder_worker {worker_id} exited")

        async def upserter_worker(worker_id):
            nonlocal success_count, error_count, processed_documents
            logger.debug(f"[DIAG] upserter_worker {worker_id} started")
            batch_size = self.upsert_batch_size
            batch = []
            while True:
                item = await embed_queue.get()
                if item is None:
                    logger.debug(f"[DIAG] upserter_worker {worker_id} received sentinel, breaking")
                    # Upsert any remaining items in the batch before exiting
                    if batch:
                        try:
                            with prometheus_metrics.UPSERT_DURATION.time():
                                points = [
                                    models.PointStruct(
                                        id=chunk.id,
                                        vector=embedding,
                                        payload={
                                            "content": chunk.content,
                                            "metadata": {
                                                k: v
                                                for k, v in chunk.metadata.items()
                                                if k != "parent_document"
                                            },
                                            "source": chunk.source,
                                            "source_type": chunk.source_type,
                                            "created_at": chunk.created_at.isoformat(),
                                            "document_id": chunk.metadata.get(
                                                "parent_document_id", chunk.id
                                            ),
                                        },
                                    )
                                    for chunk, embedding in batch
                                ]
                                await self.qdrant_manager.upsert_points(points)
                                prometheus_metrics.INGESTED_DOCUMENTS.inc(len(points))
                                success_count += len(points)

                                # Update document states for successfully processed chunks
                                for chunk, _ in batch:
                                    if "parent_document" in chunk.metadata:
                                        parent_doc = chunk.metadata["parent_document"]
                                        processed_documents.add(parent_doc.id)
                        except Exception as e:
                            for chunk, _ in batch:
                                logger.error(f"Upsert failed for chunk {chunk.id}: {e}")
                                errors.append(f"Upsert failed for chunk {chunk.id}: {e}")
                            error_count += len(batch)
                        batch = []
                    break
                batch.append(item)
                if len(batch) >= batch_size:
                    try:
                        with prometheus_metrics.UPSERT_DURATION.time():
                            points = [
                                models.PointStruct(
                                    id=chunk.id,
                                    vector=embedding,
                                    payload={
                                        "content": chunk.content,
                                        "metadata": {
                                            k: v
                                            for k, v in chunk.metadata.items()
                                            if k != "parent_document"
                                        },
                                        "source": chunk.source,
                                        "source_type": chunk.source_type,
                                        "created_at": chunk.created_at.isoformat(),
                                        "document_id": chunk.metadata.get(
                                            "parent_document_id", chunk.id
                                        ),
                                    },
                                )
                                for chunk, embedding in batch
                            ]
                            await self.qdrant_manager.upsert_points(points)
                            prometheus_metrics.INGESTED_DOCUMENTS.inc(len(points))
                            success_count += len(points)

                            # Update document states for successfully processed chunks
                            for chunk, _ in batch:
                                if "parent_document" in chunk.metadata:
                                    parent_doc = chunk.metadata["parent_document"]
                                    processed_documents.add(parent_doc.id)
                    except Exception as e:
                        for chunk, _ in batch:
                            logger.error(f"Upsert failed for chunk {chunk.id}: {e}")
                            errors.append(f"Upsert failed for chunk {chunk.id}: {e}")
                        error_count += len(batch)
                    batch = []
            logger.debug(f"[DIAG] upserter_worker {worker_id} exited")

        # Create and start tasks
        logger.debug(f"[DIAG] Creating chunker_tasks")
        chunker_tasks = [asyncio.create_task(chunker_worker(doc)) for doc in documents]
        all_tasks.extend(chunker_tasks)
        logger.debug(f"[DIAG] Creating {self.max_embed_workers} embedder_tasks")
        embedder_tasks = [
            asyncio.create_task(embedder_worker(i)) for i in range(self.max_embed_workers)
        ]
        all_tasks.extend(embedder_tasks)
        logger.debug(f"[DIAG] Creating {self.max_upsert_workers} upserter_tasks")
        upserter_tasks = [
            asyncio.create_task(upserter_worker(i)) for i in range(self.max_upsert_workers)
        ]
        all_tasks.extend(upserter_tasks)

        async def shutdown():
            logger.debug("[DIAG] Shutdown: putting sentinels in all queues to unblock workers")
            for _ in range(self.max_embed_workers):
                await chunk_queue.put(None)
            for _ in range(self.max_upsert_workers):
                await embed_queue.put(None)
            # Await all tasks
            logger.debug("[DIAG] Shutdown: awaiting all worker tasks")
            await asyncio.gather(*all_tasks, return_exceptions=True)
            logger.debug("[DIAG] Shutdown: all worker tasks completed")

        try:
            logger.debug(f"[DIAG] Awaiting chunker_tasks")
            await asyncio.gather(*chunker_tasks)
            logger.info(
                f"[DIAG] chunker finished, putting {self.max_embed_workers} sentinels into chunk_queue"
            )
            for _ in range(self.max_embed_workers):
                await chunk_queue.put(None)
            logger.debug(f"[DIAG] chunker put all sentinels into chunk_queue")

            logger.debug(f"[DIAG] Awaiting embedder_tasks")
            await asyncio.gather(*embedder_tasks)
            logger.info(
                f"[DIAG] embedder_tasks completed, putting {self.max_upsert_workers} sentinels into embed_queue"
            )
            for _ in range(self.max_upsert_workers):
                await embed_queue.put(None)
            logger.debug(f"[DIAG] embedder put all sentinels into embed_queue")

            logger.debug(f"[DIAG] Awaiting upserter_tasks")
            await asyncio.gather(*upserter_tasks)
            logger.debug(f"[DIAG] upserter_tasks completed")
        except (asyncio.CancelledError, KeyboardInterrupt):
            logger.debug("[DIAG] Received cancellation or SIGINT, shutting down pipeline...")
            await shutdown()
        finally:
            # Ensure all tasks are awaited before returning
            pending = [t for t in all_tasks if not t.done()]
            if pending:
                logger.debug(f"[DIAG] Awaiting {len(pending)} pending tasks in finally block")
                await asyncio.gather(*pending, return_exceptions=True)
            # Properly shutdown the ThreadPoolExecutor to free resources
            self.chunk_executor.shutdown(wait=True)

        # Update document states for successfully processed documents
        logger.debug(
            f"Updating document states for {len(processed_documents)} successfully processed documents"
        )
        for doc in documents:
            if doc.id in processed_documents:
                try:
                    await self.state_manager.update_document_state(doc)
                    logger.debug(f"Updated document state for {doc.id}")
                except Exception as e:
                    logger.error(f"Failed to update document state for {doc.id}: {e}")

        logger.info(f"Pipeline completed: {success_count} success, {error_count} errors")
        logger.debug("[DIAG] Active threads at pipeline end:")
        for t in threading.enumerate():
            logger.info(
                f"[DIAG] Thread: {t.name}, Daemon: {t.daemon}, Alive: {t.is_alive()}, Ident: {t.ident}"
            )
        logger.debug("[DIAG] Active asyncio tasks at pipeline end:")
        for task in asyncio.all_tasks():
            logger.debug(f"[DIAG] Task: {task}")
        return success_count, error_count

    def cleanup(self):
        """Clean up resources to prevent hanging threads."""
        logger.debug("[DIAG] Starting pipeline cleanup")

        # Shutdown thread pool executor
        if hasattr(self, "chunk_executor") and self.chunk_executor:
            logger.debug("[DIAG] Shutting down chunk executor")
            self.chunk_executor.shutdown(wait=True)

        # Stop metrics server if it was started
        try:
            prometheus_metrics.stop_metrics_server()
        except Exception as e:
            logger.warning(f"[DIAG] Error stopping metrics server: {e}")

        logger.debug("[DIAG] Pipeline cleanup completed")

    def __del__(self):
        """Destructor to ensure cleanup on object deletion."""
        try:
            self.cleanup()
        except Exception as e:
            logger.warning(f"[DIAG] Error in destructor cleanup: {e}")
