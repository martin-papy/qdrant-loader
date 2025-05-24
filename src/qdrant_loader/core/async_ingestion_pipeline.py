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
import sys

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

        # Shutdown coordination
        self._shutdown_event = asyncio.Event()
        self._active_tasks = set()
        self._cleanup_done = False

        # Register cleanup handlers
        atexit.register(self._cleanup)
        signal.signal(signal.SIGINT, self._handle_sigint)
        signal.signal(signal.SIGTERM, self._handle_sigterm)

        # Only start metrics server if explicitly enabled
        if enable_metrics:
            prometheus_metrics.start_metrics_server()

    def _cleanup(self):
        """Clean up resources."""
        if self._cleanup_done:
            return

        try:
            logger.info("Cleaning up resources...")

            # Set shutdown event
            if hasattr(self, "_shutdown_event") and not self._shutdown_event.is_set():
                # We can't await in a sync function, so we'll use a different approach
                try:
                    loop = asyncio.get_running_loop()
                    loop.call_soon_threadsafe(self._shutdown_event.set)
                except RuntimeError:
                    # No running loop, create one briefly
                    try:
                        asyncio.run(self._async_cleanup())
                    except Exception as e:
                        logger.error(f"Error in async cleanup: {e}")

            # Shutdown thread pool executor
            if hasattr(self, "chunk_executor") and self.chunk_executor:
                logger.debug("Shutting down chunk executor")
                self.chunk_executor.shutdown(wait=True)

            # Save metrics
            if hasattr(self, "monitor"):
                self.monitor.save_metrics()

            # Stop metrics server
            try:
                prometheus_metrics.stop_metrics_server()
            except Exception as e:
                logger.warning(f"Error stopping metrics server: {e}")

            self._cleanup_done = True
            logger.info("Cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    async def _async_cleanup(self):
        """Async cleanup helper."""
        self._shutdown_event.set()

        # Cancel all active tasks
        if self._active_tasks:
            logger.info(f"Cancelling {len(self._active_tasks)} active tasks")
            for task in self._active_tasks:
                if not task.done():
                    task.cancel()

            # Wait for tasks to complete with timeout
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._active_tasks, return_exceptions=True), timeout=10.0
                )
            except asyncio.TimeoutError:
                logger.warning("Some tasks did not complete within timeout")

    def _handle_sigint(self, signum, frame):
        """Handle SIGINT signal."""
        # Prevent multiple signal handling
        if self._shutdown_event.is_set():
            logger.warning("Multiple SIGINT received, forcing immediate exit")
            self._force_immediate_exit()
            return

        logger.info("Received SIGINT, initiating shutdown...")
        self._shutdown_event.set()

        # Try to schedule graceful shutdown
        try:
            loop = asyncio.get_running_loop()
            # Cancel all running tasks immediately
            loop.call_soon_threadsafe(self._cancel_all_tasks)
            # Schedule force shutdown
            loop.call_later(3.0, self._force_immediate_exit)
        except RuntimeError:
            # No running loop, do immediate cleanup and exit
            logger.warning("No event loop found, forcing immediate exit")
            self._cleanup()
            self._force_immediate_exit()

    def _handle_sigterm(self, signum, frame):
        """Handle SIGTERM signal."""
        if self._shutdown_event.is_set():
            logger.warning("Multiple SIGTERM received, forcing immediate exit")
            self._force_immediate_exit()
            return

        logger.info("Received SIGTERM, initiating shutdown...")
        self._shutdown_event.set()

        try:
            loop = asyncio.get_running_loop()
            loop.call_soon_threadsafe(self._cancel_all_tasks)
            loop.call_later(3.0, self._force_immediate_exit)
        except RuntimeError:
            self._cleanup()
            self._force_immediate_exit()

    def _cancel_all_tasks(self):
        """Cancel all active tasks immediately."""
        try:
            logger.warning("Cancelling all active tasks")

            # Cancel all tracked tasks
            if hasattr(self, "_active_tasks") and self._active_tasks:
                for task in list(self._active_tasks):
                    if not task.done():
                        task.cancel()

            # Cancel all running tasks in the current loop
            try:
                loop = asyncio.get_running_loop()
                for task in asyncio.all_tasks(loop):
                    if not task.done() and task != asyncio.current_task():
                        task.cancel()
            except RuntimeError:
                pass

        except Exception as e:
            logger.error(f"Error cancelling tasks: {e}")

    def _force_immediate_exit(self):
        """Force immediate exit."""
        try:
            logger.error("Force exit initiated")
            self._cleanup()
        except Exception as e:
            logger.error(f"Error during force cleanup: {e}")
        finally:
            # Force exit regardless of cleanup success
            import os

            os._exit(1)

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

            # Check for shutdown before processing sources
            if self._shutdown_event.is_set():
                logger.info("Shutdown requested, skipping source processing")
                return []

            # Process each source type
            if filtered_config.confluence and not self._shutdown_event.is_set():
                logger.info("Starting to process Confluence sources")
                confluence_docs = await self._process_source_type(
                    filtered_config.confluence, ConfluenceConnector, "Confluence"
                )
                logger.info(
                    f"Completed processing Confluence sources, got {len(confluence_docs)} documents"
                )
                documents.extend(confluence_docs)

            if filtered_config.git and not self._shutdown_event.is_set():
                logger.info("Starting to process Git sources")
                git_docs = await self._process_source_type(filtered_config.git, GitConnector, "Git")
                logger.info(f"Completed processing Git sources, got {len(git_docs)} documents")
                documents.extend(git_docs)

            if filtered_config.jira and not self._shutdown_event.is_set():
                logger.info("Starting to process Jira sources")
                jira_docs = await self._process_source_type(
                    filtered_config.jira, JiraConnector, "Jira"
                )
                logger.info(f"Completed processing Jira sources, got {len(jira_docs)} documents")
                documents.extend(jira_docs)

            if filtered_config.publicdocs and not self._shutdown_event.is_set():
                logger.info("Starting to process PublicDocs sources")
                publicdocs_docs = await self._process_source_type(
                    filtered_config.publicdocs, PublicDocsConnector, "PublicDocs"
                )
                logger.info(
                    f"Completed processing PublicDocs sources, got {len(publicdocs_docs)} documents"
                )
                documents.extend(publicdocs_docs)

            if filtered_config.localfile and not self._shutdown_event.is_set():
                logger.info("Starting to process LocalFile sources")
                localfile_docs = await self._process_source_type(
                    filtered_config.localfile, LocalFileConnector, "LocalFile"
                )
                logger.info(
                    f"Completed processing LocalFile sources, got {len(localfile_docs)} documents"
                )
                documents.extend(localfile_docs)

            logger.info(f"Completed processing all sources, total documents: {len(documents)}")

            # Check for shutdown before change detection
            if self._shutdown_event.is_set():
                logger.info("Shutdown requested, skipping change detection and processing")
                return documents

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

            # Check for shutdown before pipeline processing
            if self._shutdown_event.is_set():
                logger.info("Shutdown requested, skipping pipeline processing")
                return documents

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

                if documents and not self._shutdown_event.is_set():
                    success_count, error_count = await self.process_documents_pipeline(documents)

                    # Update document states immediately after successful processing
                    if not self._shutdown_event.is_set():
                        logger.debug(
                            f"Updating document states for {len(documents)} processed documents"
                        )
                        for doc in documents:
                            try:
                                await self.state_manager.update_document_state(doc)
                                logger.debug(f"Updated document state for {doc.id}")
                            except Exception as e:
                                logger.error(f"Failed to update document state for {doc.id}: {e}")

                # Update batch metrics
                self.monitor.end_batch("document_batch", success_count, error_count, [])

                if deleted_documents and not self._shutdown_event.is_set():
                    logger.info(f"Processing {len(deleted_documents)} deleted documents")
                    # Process deleted documents
                    for doc in deleted_documents:
                        if self._shutdown_event.is_set():
                            logger.info("Shutdown requested, stopping deleted document processing")
                            break
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
            if not self._shutdown_event.is_set():
                self.monitor.save_metrics()
                logger.info("Metrics saved successfully")

            return documents

        except (asyncio.CancelledError, KeyboardInterrupt):
            logger.warning("Process interrupted, initiating shutdown...")
            self._shutdown_event.set()
            # Save metrics even on interruption
            try:
                self.monitor.save_metrics()
                logger.info("Metrics saved after interruption")
            except Exception as e:
                logger.error(f"Error saving metrics after interruption: {e}")
            # Don't re-raise, just return empty list to allow graceful exit
            return []
        except Exception as e:
            logger.error(
                "Failed to process documents",
                error=str(e),
                error_type=type(e).__name__,
                error_class=e.__class__.__name__,
            )
            # Save metrics even on failure
            try:
                self.monitor.save_metrics()
                logger.info("Metrics saved after failure")
            except Exception as save_error:
                logger.error(f"Error saving metrics after failure: {save_error}")
            raise
        finally:
            self.monitor.end_operation(
                "ingestion_process", success=not self._shutdown_event.is_set()
            )

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

        async def chunker_worker(doc):
            logger.debug(f"[DIAG] chunker_worker started for doc {doc.id}")
            try:
                # Check for shutdown signal
                if self._shutdown_event.is_set():
                    logger.debug(f"[DIAG] chunker_worker {doc.id} exiting due to shutdown")
                    return

                prometheus_metrics.CPU_USAGE.set(psutil.cpu_percent())
                prometheus_metrics.MEMORY_USAGE.set(psutil.virtual_memory().percent)
                prometheus_metrics.CHUNK_QUEUE_SIZE.set(chunk_queue.qsize())
                # Run chunking in a thread pool for true parallelism
                with prometheus_metrics.CHUNKING_DURATION.time():
                    # Add timeout to prevent hanging on chunking
                    chunks = await asyncio.wait_for(
                        asyncio.get_running_loop().run_in_executor(
                            self.chunk_executor, self.chunking_service.chunk_document, doc
                        ),
                        timeout=30.0,  # 30 second timeout for chunking
                    )

                    # Check for shutdown before putting chunks in queue
                    if self._shutdown_event.is_set():
                        logger.debug(
                            f"[DIAG] chunker_worker {doc.id} exiting due to shutdown after chunking"
                        )
                        return

                    for chunk in chunks:
                        # Add document reference to chunk for later state tracking
                        chunk.metadata["parent_document"] = doc
                        await chunk_queue.put(chunk)
                    logger.debug(f"Chunked doc {doc.id} into {len(chunks)} chunks")
            except asyncio.CancelledError:
                logger.debug(f"[DIAG] chunker_worker {doc.id} cancelled")
                raise
            except asyncio.TimeoutError:
                logger.error(f"Chunking timed out for doc {doc.id}")
                errors.append(f"Chunking timed out for doc {doc.id}")
            except Exception as e:
                logger.error(f"Chunking failed for doc {doc.id}: {e}")
                errors.append(f"Chunking failed for doc {doc.id}: {e}")
            logger.debug(f"[DIAG] chunker_worker exiting for doc {doc.id}")

        async def chunker():
            logger.debug(f"[DIAG] chunker started")
            try:
                tasks = [chunker_worker(doc) for doc in documents]
                await asyncio.gather(*tasks)

                # Check for shutdown before putting sentinels
                if not self._shutdown_event.is_set():
                    logger.info(
                        f"[DIAG] chunker finished, putting {self.max_embed_workers} sentinels into chunk_queue"
                    )
                    for _ in range(self.max_embed_workers):
                        await chunk_queue.put(None)
                    logger.debug(f"[DIAG] chunker put all sentinels into chunk_queue")
                else:
                    logger.debug(
                        f"[DIAG] chunker exiting due to shutdown, putting emergency sentinels"
                    )
                    for _ in range(self.max_embed_workers):
                        try:
                            chunk_queue.put_nowait(None)
                        except asyncio.QueueFull:
                            pass
            except asyncio.CancelledError:
                logger.debug(f"[DIAG] chunker cancelled")
                # Put emergency sentinels to unblock embedders
                for _ in range(self.max_embed_workers):
                    try:
                        chunk_queue.put_nowait(None)
                    except asyncio.QueueFull:
                        pass
                raise

        async def embedder_worker(worker_id):
            logger.debug(f"[DIAG] embedder_worker {worker_id} started")
            batch_size = self.embedding_service.batch_size
            try:
                while not self._shutdown_event.is_set():
                    batch = []
                    sentinel_received = False

                    # Collect batch items with timeout to check shutdown
                    for _ in range(batch_size):
                        try:
                            chunk = await asyncio.wait_for(chunk_queue.get(), timeout=1.0)
                            if chunk is None:
                                logger.debug(
                                    f"[DIAG] embedder_worker {worker_id} received sentinel"
                                )
                                sentinel_received = True
                                break
                            batch.append(chunk)
                        except asyncio.TimeoutError:
                            # Check shutdown and continue if no shutdown
                            if self._shutdown_event.is_set():
                                logger.debug(
                                    f"[DIAG] embedder_worker {worker_id} exiting due to shutdown"
                                )
                                return
                            break  # Exit batch collection loop, process what we have

                    # If no items in batch and sentinel received, exit
                    if not batch and sentinel_received:
                        logger.debug(f"[DIAG] embedder_worker {worker_id} exiting (no batch)")
                        break

                    # Process any remaining items in batch
                    if batch:
                        try:
                            logger.debug(
                                f"[DIAG] embedder_worker {worker_id} processing batch of {len(batch)} items"
                            )
                            with prometheus_metrics.EMBEDDING_DURATION.time():
                                # Add timeout to prevent hanging and check for shutdown
                                embeddings = await asyncio.wait_for(
                                    self.embedding_service.get_embeddings(
                                        [c.content for c in batch]
                                    ),
                                    timeout=120.0,  # 2 minute timeout
                                )

                                # Check for shutdown before putting in queue
                                if not self._shutdown_event.is_set():
                                    for chunk, embedding in zip(batch, embeddings):
                                        await embed_queue.put((chunk, embedding))
                                else:
                                    logger.debug(
                                        f"[DIAG] embedder_worker {worker_id} skipping queue put due to shutdown"
                                    )

                            logger.debug(
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
                        logger.debug(
                            f"[DIAG] embedder_worker {worker_id} exiting after processing final batch"
                        )
                        break
            except asyncio.CancelledError:
                logger.debug(f"[DIAG] embedder_worker {worker_id} cancelled")
                raise
            finally:
                logger.debug(f"[DIAG] embedder_worker {worker_id} exited")

        async def upserter_worker(worker_id):
            nonlocal success_count, error_count
            logger.debug(f"[DIAG] upserter_worker {worker_id} started")
            batch_size = self.upsert_batch_size
            batch = []
            try:
                while not self._shutdown_event.is_set():
                    try:
                        item = await asyncio.wait_for(embed_queue.get(), timeout=1.0)
                        if item is None:
                            logger.debug(
                                f"[DIAG] upserter_worker {worker_id} received sentinel, breaking"
                            )
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
                            except Exception as e:
                                for chunk, _ in batch:
                                    logger.error(f"Upsert failed for chunk {chunk.id}: {e}")
                                    errors.append(f"Upsert failed for chunk {chunk.id}: {e}")
                                error_count += len(batch)
                            batch = []
                    except asyncio.TimeoutError:
                        # Check shutdown and continue if no shutdown
                        if self._shutdown_event.is_set():
                            logger.debug(
                                f"[DIAG] upserter_worker {worker_id} exiting due to shutdown"
                            )
                            break
                        continue
            except asyncio.CancelledError:
                logger.debug(f"[DIAG] upserter_worker {worker_id} cancelled")
                raise
            finally:
                logger.debug(f"[DIAG] upserter_worker {worker_id} exited")

        # Create and start tasks
        logger.debug(f"[DIAG] Creating chunker task")
        chunker_task = asyncio.create_task(chunker())
        all_tasks.append(chunker_task)
        self._active_tasks.add(chunker_task)

        logger.debug(f"[DIAG] Creating {self.max_embed_workers} embedder_tasks")
        embedder_tasks = [
            asyncio.create_task(embedder_worker(i)) for i in range(self.max_embed_workers)
        ]
        all_tasks.extend(embedder_tasks)
        self._active_tasks.update(embedder_tasks)

        logger.debug(f"[DIAG] Creating {self.max_upsert_workers} upserter_tasks")
        upserter_tasks = [
            asyncio.create_task(upserter_worker(i)) for i in range(self.max_upsert_workers)
        ]
        all_tasks.extend(upserter_tasks)
        self._active_tasks.update(upserter_tasks)

        async def emergency_shutdown():
            """Emergency shutdown procedure."""
            logger.warning("[DIAG] Emergency shutdown initiated")
            self._shutdown_event.set()

            # Put emergency sentinels to unblock workers
            try:
                for _ in range(self.max_embed_workers):
                    try:
                        chunk_queue.put_nowait(None)
                    except asyncio.QueueFull:
                        pass

                for _ in range(self.max_upsert_workers):
                    try:
                        embed_queue.put_nowait(None)
                    except asyncio.QueueFull:
                        pass
            except Exception as e:
                logger.error(f"Error putting emergency sentinels: {e}")

            # Cancel all tasks
            for task in all_tasks:
                if not task.done():
                    task.cancel()

            # Wait for tasks to complete with timeout
            try:
                await asyncio.wait_for(
                    asyncio.gather(*all_tasks, return_exceptions=True), timeout=5.0
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "[DIAG] Some tasks did not complete within emergency shutdown timeout"
                )

        try:
            # Wait for chunker to complete
            logger.debug(f"[DIAG] Awaiting chunker_task")
            await chunker_task

            # Wait for embedders to complete
            logger.debug(f"[DIAG] Awaiting embedder_tasks")
            await asyncio.gather(*embedder_tasks)

            # Signal upserters to finish
            if not self._shutdown_event.is_set():
                logger.debug(
                    f"[DIAG] embedder_tasks completed, putting {self.max_upsert_workers} sentinels into embed_queue"
                )
                for _ in range(self.max_upsert_workers):
                    await embed_queue.put(None)
                logger.debug(f"[DIAG] embedder put all sentinels into embed_queue")

            # Wait for upserters to complete
            logger.debug(f"[DIAG] Awaiting upserter_tasks")
            await asyncio.gather(*upserter_tasks)
            logger.debug(f"[DIAG] upserter_tasks completed")

        except (asyncio.CancelledError, KeyboardInterrupt):
            logger.warning(
                "[DIAG] Received cancellation or SIGINT, initiating emergency shutdown..."
            )
            await emergency_shutdown()
            # Don't re-raise, return current counts to allow graceful exit
            return success_count, error_count
        except Exception as e:
            logger.error(f"[DIAG] Unexpected error in pipeline: {e}")
            await emergency_shutdown()
            raise
        finally:
            # Remove tasks from active set
            self._active_tasks.discard(chunker_task)
            for task in embedder_tasks:
                self._active_tasks.discard(task)
            for task in upserter_tasks:
                self._active_tasks.discard(task)

            # Ensure all tasks are completed
            pending = [t for t in all_tasks if not t.done()]
            if pending:
                logger.debug(f"[DIAG] Awaiting {len(pending)} pending tasks in finally block")
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*pending, return_exceptions=True), timeout=3.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("[DIAG] Some tasks did not complete within final timeout")

            # Properly shutdown the ThreadPoolExecutor to free resources
            if hasattr(self, "chunk_executor") and self.chunk_executor:
                logger.debug("[DIAG] Shutting down chunk executor")
                self.chunk_executor.shutdown(wait=False)  # Don't wait to avoid hanging

        logger.info(f"Pipeline completed: {success_count} success, {error_count} errors")
        logger.debug("[DIAG] Active threads at pipeline end:")
        for t in threading.enumerate():
            logger.debug(
                f"[DIAG] Thread: {t.name}, Daemon: {t.daemon}, Alive: {t.is_alive()}, Ident: {t.ident}"
            )
        logger.debug("[DIAG] Active asyncio tasks at pipeline end:")
        for task in asyncio.all_tasks():
            logger.debug(f"[DIAG] Task: {task}")
        return success_count, error_count

    def cleanup(self):
        """Clean up resources to prevent hanging threads."""
        if self._cleanup_done:
            return

        logger.debug("[DIAG] Starting pipeline cleanup")

        try:
            # Set shutdown event
            if hasattr(self, "_shutdown_event"):
                try:
                    loop = asyncio.get_running_loop()
                    if not self._shutdown_event.is_set():
                        loop.call_soon_threadsafe(self._shutdown_event.set)
                except RuntimeError:
                    pass  # No running loop

            # Cancel active tasks
            if hasattr(self, "_active_tasks") and self._active_tasks:
                logger.debug(f"[DIAG] Cancelling {len(self._active_tasks)} active tasks")
                for task in list(self._active_tasks):
                    if not task.done():
                        task.cancel()

            # Shutdown thread pool executor
            if hasattr(self, "chunk_executor") and self.chunk_executor:
                logger.debug("[DIAG] Shutting down chunk executor")
                self.chunk_executor.shutdown(wait=False)  # Don't wait to avoid hanging

            # Stop metrics server if it was started
            try:
                prometheus_metrics.stop_metrics_server()
            except Exception as e:
                logger.warning(f"[DIAG] Error stopping metrics server: {e}")

            self._cleanup_done = True
            logger.debug("[DIAG] Pipeline cleanup completed")
        except Exception as e:
            logger.error(f"[DIAG] Error during cleanup: {e}")

    def __del__(self):
        """Destructor to ensure cleanup on object deletion."""
        try:
            if hasattr(self, "_cleanup_done"):
                self.cleanup()
        except Exception as e:
            logger.warning(f"[DIAG] Error in destructor cleanup: {e}")
