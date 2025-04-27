"""
Ingestion pipeline for processing documents.
"""

from collections.abc import Mapping
from qdrant_client.http import models
from tqdm import tqdm
from typing import Type, List, Tuple
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, UTC

from qdrant_loader.config.source_config import SourceConfig
from qdrant_loader.config.state import IngestionStatus
from qdrant_loader.config.types import SourceType
from qdrant_loader.connectors.base import BaseConnector
from qdrant_loader.core.state.state_change_detector import StateChangeDetector
from qdrant_loader.core.monitoring.performance_monitor import PerformanceMonitor

from ..config import Settings, SourcesConfig
from ..connectors.confluence import ConfluenceConnector
from ..connectors.git import GitConnector
from ..connectors.jira import JiraConnector
from ..connectors.publicdocs import PublicDocsConnector
from ..utils.logging import LoggingConfig
from .chunking.chunking_service import ChunkingService
from .document import Document
from .embedding.embedding_service import EmbeddingService
from .qdrant_manager import QdrantManager
from .state.state_manager import StateManager

logger = LoggingConfig.get_logger(__name__)


class IngestionPipeline:
    """Pipeline for processing documents."""

    def __init__(self, settings: Settings, qdrant_manager: QdrantManager):
        """Initialize the ingestion pipeline."""

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
        self.state_manager = StateManager(self.config.state_management)
        self.logger = LoggingConfig.get_logger(__name__)

        # Initialize performance monitor with absolute path
        metrics_dir = Path.cwd() / 'metrics'
        metrics_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Initializing metrics directory at {metrics_dir}")
        self.monitor = PerformanceMonitor.get_monitor(metrics_dir)

        # Configure batch sizes and timeouts
        self.embedding_batch_size = 32  # Number of texts to embed at once
        self.upsert_batch_size = 50     # Number of points to upsert at once
        self.max_workers = 4            # Number of parallel workers
        self.timeout = 30               # Timeout in seconds for operations

    async def initialize(self):
        """Initialize the pipeline services."""
        await self.state_manager.initialize()
        # No need to initialize the monitor, it's already initialized in the current event loop

    async def _process_document_batch(self, documents: List[Document]) -> Tuple[int, int, List[str]]:
        """Process a batch of documents in parallel."""
        success_count = 0
        error_count = 0
        errors: List[str] = []

        self.logger.debug(f"Starting to process batch of {len(documents)} documents")

        # Process documents in parallel with semaphore to limit concurrency
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def process_with_semaphore(doc: Document) -> None:
            async with semaphore:
                try:
                    self.logger.debug(f"Processing document {doc.id} from {doc.source_type}")
                    await self._process_single_document(doc)
                    nonlocal success_count
                    success_count += 1
                    self.logger.debug(f"Successfully processed document {doc.id}")
                except Exception as e:
                    nonlocal error_count, errors
                    error_count += 1
                    error_msg = f"Error processing document {doc.id}: {str(e)}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
                    raise

        # Create tasks with semaphore
        tasks = [process_with_semaphore(doc) for doc in documents]
        
        # Wait for all tasks to complete
        await asyncio.gather(*tasks, return_exceptions=True)

        self.logger.info(f"Batch processing completed. Success: {success_count}, Errors: {error_count}")
        return success_count, error_count, errors

    async def _process_single_document(self, doc: Document) -> None:
        """Process a single document."""
        async with self.monitor.track_operation(
            'document_processing',
            metadata={'document_id': doc.id, 'source_type': doc.source_type}
        ) as doc_op_id:
            try:
                # Update document state
                self.logger.debug(f"Updating state for document {doc.id}")
                updated_state = await self.state_manager.update_document_state(doc)
                self.logger.debug(
                    "Document state updated",
                    doc_id=updated_state.document_id,
                    content_hash=updated_state.content_hash,
                    updated_at=updated_state.updated_at,
                )

                # Chunk document
                self.logger.debug(f"Chunking document {doc.id}")
                chunks = self.chunking_service.chunk_document(doc)
                self.logger.debug(f"Document {doc.id} split into {len(chunks)} chunks")

                # Process chunks in batches
                for i in range(0, len(chunks), self.embedding_batch_size):
                    batch_chunks = chunks[i:i + self.embedding_batch_size]
                    chunk_contents = [chunk.content for chunk in batch_chunks]
                    
                    # Get embeddings for batch
                    self.logger.debug(f"Getting embeddings for batch of {len(batch_chunks)} chunks from document {doc.id}")
                    embeddings = await self.embedding_service.get_embeddings(chunk_contents)
                    self.logger.debug(f"Successfully generated embeddings for {len(embeddings)} chunks from document {doc.id}")

                    # Create points for batch
                    points = []
                    for chunk, embedding in zip(batch_chunks, embeddings, strict=False):
                        point = models.PointStruct(
                            id=chunk.id,
                            vector=embedding,
                            payload={
                                "content": chunk.content,
                                "metadata": chunk.metadata,
                                "source": chunk.source,
                                "source_type": chunk.source_type,
                                "created_at": chunk.created_at.isoformat(),
                                "document_id": doc.id,
                            },
                        )
                        points.append(point)

                    # Upsert points in smaller batches
                    for j in range(0, len(points), self.upsert_batch_size):
                        batch_points = points[j:j + self.upsert_batch_size]
                        self.logger.debug(f"Upserting batch of {len(batch_points)} points from document {doc.id}")
                        await self.qdrant_manager.upsert_points(batch_points)
                        self.logger.debug(f"Successfully upserted {len(batch_points)} points from document {doc.id}")

            except Exception as e:
                error_msg = f"Error processing document {doc.id}: {str(e)}"
                self.logger.error(error_msg)
                raise

    async def process_documents(
        self,
        sources_config: SourcesConfig | None = None,
        source_type: str | None = None,
        source: str | None = None,
    ) -> list[Document]:
        """Process documents from all configured sources."""
        # Ensure the pipeline is initialized
        await self.initialize()
        
        async with self.monitor.track_operation(
            'document_processing',
            metadata={'source_type': source_type, 'source': source}
        ) as ingestion_op_id:
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
                    ]
                ):
                    raise ValueError(f"No sources found for type '{source_type}'")

                documents: list[Document] = []
                deleted_documents: list[Document] = []

                # Process each source type
                if filtered_config.confluence:
                    self.logger.info("Starting to process Confluence sources")
                    confluence_docs = await self._process_source_type(
                        filtered_config.confluence, ConfluenceConnector, "Confluence"
                    )
                    self.logger.info(f"Completed processing Confluence sources, got {len(confluence_docs)} documents")
                    documents.extend(confluence_docs)

                if filtered_config.git:
                    self.logger.info("Starting to process Git sources")
                    git_docs = await self._process_source_type(
                        filtered_config.git, GitConnector, "Git"
                    )
                    self.logger.info(f"Completed processing Git sources, got {len(git_docs)} documents")
                    documents.extend(git_docs)

                if filtered_config.jira:
                    self.logger.info("Starting to process Jira sources")
                    jira_docs = await self._process_source_type(
                        filtered_config.jira, JiraConnector, "Jira"
                    )
                    self.logger.info(f"Completed processing Jira sources, got {len(jira_docs)} documents")
                    documents.extend(jira_docs)

                if filtered_config.publicdocs:
                    self.logger.info("Starting to process PublicDocs sources")
                    publicdocs_docs = await self._process_source_type(
                        filtered_config.publicdocs, PublicDocsConnector, "PublicDocs"
                    )
                    self.logger.info(f"Completed processing PublicDocs sources, got {len(publicdocs_docs)} documents")
                    documents.extend(publicdocs_docs)

                self.logger.info(f"Completed processing all sources, total documents: {len(documents)}")

                # Detect changes in documents
                if documents:
                    self.logger.debug(f"Starting change detection for {len(documents)} documents")
                    try:
                        self.logger.debug("Initializing StateChangeDetector...")
                        async with StateChangeDetector(self.state_manager) as change_detector:
                            self.logger.debug("StateChangeDetector initialized, detecting changes...")
                            changes = await change_detector.detect_changes(documents, filtered_config)
                            self.logger.info(f"Change detection completed. New: {len(changes['new'])}, Updated: {len(changes['updated'])}, Deleted: {len(changes['deleted'])}")
                            documents = changes["new"] + changes["updated"]
                            deleted_documents = changes["deleted"]
                            self.logger.debug(f"After change detection: {len(documents)} documents to process, {len(deleted_documents)} documents to delete")
                    except Exception as e:
                        self.logger.error(f"Error during change detection: {str(e)}", exc_info=True)
                        raise

                if documents or deleted_documents:
                    self.logger.info(f"Processing {len(documents)} documents and {len(deleted_documents)} deleted documents")
                    async with self.monitor.track_batch(
                        'document_batch',
                        batch_size=len(documents),
                        metadata={'source_type': source_type, 'source': source}
                    ) as batch_id:
                        # Process documents in parallel batches
                        success_count = 0
                        error_count = 0
                        errors: List[str] = []

                        # Split documents into batches for parallel processing
                        batch_size = 5  # Process 5 documents at a time
                        for i in range(0, len(documents), batch_size):
                            batch = documents[i:i + batch_size]
                            self.logger.info(f"Processing batch {i//batch_size + 1} of {(len(documents) + batch_size - 1)//batch_size} with {len(batch)} documents")
                            batch_success, batch_error_count, batch_errors = await self._process_document_batch(batch)
                            success_count += batch_success
                            error_count += batch_error_count
                            errors.extend(batch_errors)
                            self.logger.info(f"Batch {i//batch_size + 1} completed. Success: {batch_success}, Errors: {batch_error_count}")

                        # Update batch metrics
                        await self.monitor.batch_tracker.end_batch(batch_id, success_count, error_count, errors)

                        if deleted_documents:
                            self.logger.info(f"Processing {len(deleted_documents)} deleted documents")
                            # Process deleted documents
                            for doc in deleted_documents:
                                try:
                                    # Delete points from Qdrant
                                    await self.qdrant_manager.delete_points_by_document_id(doc.id)
                                    # Mark document as deleted in state manager
                                    await self.state_manager.mark_document_deleted(
                                        doc.source_type, doc.source, doc.id
                                    )
                                    self.logger.debug(f"Successfully processed deleted document {doc.id}")
                                except Exception as e:
                                    self.logger.error(f"Error processing deleted document {doc.id}: {e!s}")
                                    raise
                else:
                    self.logger.info("No new, updated or deleted documents to process.")

                # Save metrics after all operations are completed
                metrics_filename = f"ingestion_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"
                await self.monitor.save_metrics(metrics_filename)
                self.logger.info(f"Metrics saved successfully to {metrics_filename}")

                return documents

            except Exception as e:
                self.logger.error(
                    "Failed to process documents",
                    error=str(e),
                    error_type=type(e).__name__,
                    error_class=e.__class__.__name__,
                )
                # Save metrics even on failure
                metrics_filename = f"ingestion_failed_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"
                await self.monitor.save_metrics(metrics_filename)
                self.logger.info(f"Metrics saved to {metrics_filename} after failure")
                raise

    async def _process_source_type(
        self,
        source_configs: Mapping[str, SourceConfig],
        connector_class: Type[BaseConnector],
        source_type: str,
    ) -> list[Document]:
        """Process documents from a specific source type."""
        documents: list[Document] = []
        self.logger.debug(f"Initializing documents list for {source_type}")

        for name, config in source_configs.items():
            self.logger.info(f"Configuring {source_type} source: {name}")
            try:
                async with self.monitor.track_operation(
                    'source_processing',
                    metadata={'source_type': source_type, 'source': name}
                ) as source_op_id:
                    try:
                        self.logger.debug(f"Creating connector for {source_type} source: {name}")
                        connector = connector_class(config)
                        self.logger.debug(f"Connector created, getting documents from {source_type} source: {config.source}")
                        async with connector:
                            source_docs = await connector.get_documents()
                            self.logger.debug(f"Got {len(source_docs)} documents from {source_type} source: {config.source}")
                            documents.extend(source_docs)
                            self.logger.debug(f"Documents list length after extend: {len(documents)}")
                            self.logger.debug(f"Updating last ingestion state for {source_type} source: {config.source}")
                            await self.state_manager.update_last_ingestion(
                                config.source_type,
                                config.source,
                                IngestionStatus.SUCCESS,
                                document_count=len(source_docs),
                            )
                            self.logger.debug(f"Successfully updated last ingestion state for {source_type} source: {config.source}")
                            self.logger.debug(f"Completed processing {source_type} source: {name}")
                    except Exception as e:
                        self.logger.error(
                            f"Failed to process {source_type} source {name}",
                            error=str(e),
                            error_type=type(e).__name__,
                            error_class=e.__class__.__name__,
                        )
                        self.logger.info(f"Updating last ingestion state to FAILED for {source_type} source: {config.source}")
                        await self.state_manager.update_last_ingestion(
                            config.source_type,
                            config.source,
                            IngestionStatus.FAILED,
                            error_message=str(e),
                        )
                        self.logger.debug(f"Successfully updated last ingestion state to FAILED for {source_type} source: {config.source}")
                        raise

            except Exception as e:
                self.logger.error(
                    f"Failed to process {source_type} source {name}",
                    error=str(e),
                    error_type=type(e).__name__,
                    error_class=e.__class__.__name__,
                )
                raise

        self.logger.debug(f"Final documents list length: {len(documents)}")
        self.logger.debug(f"Final documents list type: {type(documents)}")
        self.logger.info(f"Completed processing {source_type} sources, total documents: {len(documents)}")
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

        return filtered
