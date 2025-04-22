"""
Ingestion pipeline for processing documents.
"""

from collections.abc import Mapping
from qdrant_client.http import models
from tqdm import tqdm
from typing import Type

from qdrant_loader.config.source_config import SourceConfig
from qdrant_loader.config.state import IngestionStatus
from qdrant_loader.config.types import SourceType
from qdrant_loader.connectors.base import BaseConnector
from qdrant_loader.core.state.state_change_detector import StateChangeDetector

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

        try:
            self.logger.info("Collecting documents from sources")
            # Process Git repositories
            if filtered_config.git:
                documents.extend(
                    await self._process_source_type(filtered_config.git, GitConnector, "Git")
                )

            # Process Confluence spaces
            if filtered_config.confluence:
                documents.extend(
                    await self._process_source_type(
                        filtered_config.confluence, ConfluenceConnector, "Confluence"
                    )
                )

            # Process Jira projects
            if filtered_config.jira:
                documents.extend(
                    await self._process_source_type(filtered_config.jira, JiraConnector, "Jira")
                )

            # Process public documentation
            if filtered_config.publicdocs:
                documents.extend(
                    await self._process_source_type(
                        filtered_config.publicdocs, PublicDocsConnector, "Public Documentation"
                    )
                )

            self.logger.debug(f"Found {len(documents)} documents to process")
            for doc in documents:
                self.logger.debug(
                    "Document details",
                    id=doc.id,
                    title=doc.title,
                    content_length=len(doc.content) if doc.content else 0,
                    metadata=doc.metadata,
                    source_type=doc.source_type,
                    source=doc.source,
                    url=doc.url,
                )

            # Filter documents based on state changes
            async with StateChangeDetector(self.state_manager) as detector:
                filtered_documents = await detector.detect_changes(documents, filtered_config)

            documents = filtered_documents["new"] + filtered_documents["updated"]

            deleted_documents = filtered_documents["deleted"]

            if documents or deleted_documents:
                # Process all valid documents
                total_steps = (
                    len(documents) * 4
                )  # 4 steps per document: state update, chunking, embedding, upserting
                with tqdm(total=total_steps, desc="Processing documents", unit="step") as pbar:
                    for doc in documents:
                        try:
                            # Update document state
                            updated_state = await self.state_manager.update_document_state(doc)
                            self.logger.debug(
                                "Document state updated",
                                doc_id=updated_state.document_id,
                                content_hash=updated_state.content_hash,
                                updated_at=updated_state.updated_at,
                            )
                            pbar.update(1)
                            pbar.set_postfix({"step": "state update", "doc": doc.id})

                            # Chunk document
                            try:
                                chunks = self.chunking_service.chunk_document(doc)
                            except Exception as e:
                                self.logger.error(f"Error chunking document {doc.id}: {e!s}")
                                raise
                            pbar.update(1)
                            pbar.set_postfix({"step": "chunking", "doc": doc.id})

                            # Get embeddings
                            chunk_contents = [chunk.content for chunk in chunks]
                            embeddings = await self.embedding_service.get_embeddings(chunk_contents)
                            pbar.update(1)
                            pbar.set_postfix({"step": "embedding", "doc": doc.id})

                            # Create PointStruct instances
                            points = []
                            for chunk, embedding in zip(chunks, embeddings, strict=False):
                                self.logger.debug(f"Creating point for chunk {chunk.id}")
                                self.logger.debug(
                                    f"Chunk content length: {len(chunk.content) if chunk.content else 0}"
                                )
                                self.logger.debug(f"Chunk metadata: {chunk.metadata}")
                                self.logger.debug(f"Chunk source: {chunk.source}")
                                self.logger.debug(f"Chunk source_type: {chunk.source_type}")
                                self.logger.debug(f"Chunk created_at: {chunk.created_at}")
                                self.logger.debug(
                                    f"Embedding length: {len(embedding) if embedding else 0}"
                                )

                                point = models.PointStruct(
                                    id=chunk.id,
                                    vector=embedding,
                                    payload={
                                        "content": chunk.content,
                                        "metadata": chunk.metadata,
                                        "source": chunk.source,
                                        "source_type": chunk.source_type,
                                        "created_at": chunk.created_at.isoformat(),
                                        "document_id": doc.id,  # Add reference to parent document
                                    },
                                )
                                self.logger.debug("Point created")
                                points.append(point)

                            # Update Qdrant
                            await self.qdrant_manager.upsert_points(points)
                            self.logger.debug(
                                f"Successfully processed document {doc.id}",
                                points_count=len(points),
                            )
                            pbar.update(1)
                            pbar.set_postfix({"step": "upserting", "doc": doc.id})

                        except Exception as e:
                            self.logger.error(f"Error processing document {doc.id}: {e!s}")
                            raise
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

            return documents

        except Exception as e:
            self.logger.error(
                "Failed to process documents",
                error=str(e),
                error_type=type(e).__name__,
                error_class=e.__class__.__name__,
            )
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
