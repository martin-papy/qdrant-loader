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
        self.monitor = PerformanceMonitor(metrics_dir)

        # Configure batch sizes and timeouts
        self.embedding_batch_size = 32  # Number of texts to embed at once
        self.upsert_batch_size = 50     # Number of points to upsert at once
        self.max_workers = 4            # Number of parallel workers
        self.timeout = 30               # Timeout in seconds for operations

    async def initialize(self):
        """Initialize the pipeline services."""
        await self.state_manager.initialize()

    async def _process_document_batch(self, documents: List[Document]) -> Tuple[int, int, List[str]]:
        """Process a batch of documents in parallel.

        Args:
            documents: List of documents to process

        Returns:
            Tuple of (success_count, error_count, errors)
        """
        success_count = 0
        error_count = 0
        errors: List[str] = []

        # Process documents in parallel with semaphore to limit concurrency
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def process_with_semaphore(doc: Document) -> None:
            async with semaphore:
                try:
                    await self._process_single_document(doc)
                    nonlocal success_count
                    success_count += 1
                except Exception as e:
                    nonlocal error_count, errors
                    error_count += 1
                    errors.append(f"Error processing document {doc.id}: {str(e)}")
                    raise

        # Create tasks with semaphore
        tasks = [process_with_semaphore(doc) for doc in documents]
        
        # Wait for all tasks to complete
        await asyncio.gather(*tasks, return_exceptions=True)

        return success_count, error_count, errors

    async def _process_single_document(self, doc: Document) -> None:
        """Process a single document.

        Args:
            doc: Document to process
        """
        # Start document processing operation
        doc_op_id = await self.monitor.start_operation(
            'document_processing',
            metadata={'document_id': doc.id, 'source_type': doc.source_type}
        )

        try:
            # Update document state
            updated_state = await self.state_manager.update_document_state(doc)
            self.logger.debug(
                "Document state updated",
                doc_id=updated_state.document_id,
                content_hash=updated_state.content_hash,
                updated_at=updated_state.updated_at,
            )

            # Chunk document
            chunks = self.chunking_service.chunk_document(doc)

            # Process chunks in batches
            for i in range(0, len(chunks), self.embedding_batch_size):
                batch_chunks = chunks[i:i + self.embedding_batch_size]
                chunk_contents = [chunk.content for chunk in batch_chunks]
                
                # Get embeddings for batch
                embeddings = await self.embedding_service.get_embeddings(chunk_contents)

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
                    await self.qdrant_manager.upsert_points(batch_points)

            await self.monitor.end_operation(doc_op_id, success=True)

        except Exception as e:
            self.logger.error(f"Error processing document {doc.id}: {e!s}")
            await self.monitor.end_operation(doc_op_id, success=False, error=str(e))
            raise

    async def process_documents(
        self,
        sources_config: SourcesConfig | None = None,
        source_type: str | None = None,
        source: str | None = None,
    ) -> list[Document]:
        """Process documents from all configured sources."""
        # Start overall ingestion operation
        ingestion_op_id = await self.monitor.start_operation(
            'document_processing',
            metadata={'source_type': source_type, 'source': source}
        )

        try:
            # Ensure state manager is initialized
            await self.initialize()

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
                confluence_docs = await self._process_source_type(
                    filtered_config.confluence, ConfluenceConnector, "Confluence"
                )
                documents.extend(confluence_docs)

            if filtered_config.git:
                git_docs = await self._process_source_type(
                    filtered_config.git, GitConnector, "Git"
                )
                documents.extend(git_docs)

            if filtered_config.jira:
                jira_docs = await self._process_source_type(
                    filtered_config.jira, JiraConnector, "Jira"
                )
                documents.extend(jira_docs)

            if filtered_config.publicdocs:
                publicdocs_docs = await self._process_source_type(
                    filtered_config.publicdocs, PublicDocsConnector, "PublicDocs"
                )
                documents.extend(publicdocs_docs)

            # Detect changes in documents
            if documents:
                async with StateChangeDetector(self.state_manager) as change_detector:
                    changes = await change_detector.detect_changes(documents, filtered_config)
                    documents = changes["new"] + changes["updated"]
                    deleted_documents = changes["deleted"]

            if documents or deleted_documents:
                # Start batch processing
                batch_id = await self.monitor.start_batch(
                    'document_batch',
                    batch_size=len(documents),
                    metadata={'source_type': source_type, 'source': source}
                )

                # Process documents in parallel batches
                success_count = 0
                error_count = 0
                errors: List[str] = []

                # Split documents into batches for parallel processing
                batch_size = 10  # Process 10 documents at a time
                for i in range(0, len(documents), batch_size):
                    batch = documents[i:i + batch_size]
                    batch_success, batch_error_count, batch_errors = await self._process_document_batch(batch)
                    success_count += batch_success
                    error_count += batch_error_count
                    errors.extend(batch_errors)

                # End batch processing
                await self.monitor.end_batch(batch_id, success_count, error_count, errors)

                if deleted_documents:
                    # Process deleted documents
                    for doc in deleted_documents:
                        try:
                            # Delete points from Qdrant
                            await self.qdrant_manager.delete_points_by_document_id(doc.id)
                            # Mark document as deleted in state manager
                            await self.state_manager.mark_document_deleted(
                                doc.source_type, doc.source, doc.id
                            )
                            self.logger.info(
                                f"Successfully processed deleted document {doc.id}"
                            )
                        except Exception as e:
                            self.logger.error(
                                f"Error processing deleted document {doc.id}: {e!s}"
                            )
                            raise
            else:
                self.logger.info("No new, updated or deleted documents to process.")

            # End overall ingestion operation
            await self.monitor.end_operation(ingestion_op_id, success=True)

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
            await self.monitor.end_operation(ingestion_op_id, success=False, error=str(e))
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
        """Process documents from a specific source type.

        Args:
            source_configs: Dictionary of source configurations
            connector_class: The connector class to use
            source_type: Name of the source type for logging
        """
        documents: list[Document] = []

        for name, config in source_configs.items():
            self.logger.info(f"Configuring {source_type} source: {name}")
            try:
                # Start source processing operation
                source_op_id = await self.monitor.start_operation(
                    'source_processing',
                    metadata={'source_type': source_type, 'source': name}
                )

                try:
                    connector = connector_class(config)  # Instantiate first
                    async with connector:  # Then use as context manager
                        self.logger.info(
                            f"Getting documents from {source_type} source: {config.source}"
                        )
                        source_docs = await connector.get_documents()
                        documents.extend(source_docs)
                        await self.state_manager.update_last_ingestion(
                            config.source_type,
                            config.source,
                            IngestionStatus.SUCCESS,
                            document_count=len(source_docs),
                        )
                    await self.monitor.end_operation(source_op_id, success=True)
                except Exception as e:
                    self.logger.error(
                        f"Failed to process {source_type} source {name}",
                        error=str(e),
                        error_type=type(e).__name__,
                        error_class=e.__class__.__name__,
                    )
                    await self.state_manager.update_last_ingestion(
                        config.source_type,
                        config.source,
                        IngestionStatus.FAILED,
                        error_message=str(e),
                    )
                    await self.monitor.end_operation(source_op_id, success=False, error=str(e))
                    raise

            except Exception as e:
                self.logger.error(
                    f"Failed to process {source_type} source {name}",
                    error=str(e),
                    error_type=type(e).__name__,
                    error_class=e.__class__.__name__,
                )
                raise

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
