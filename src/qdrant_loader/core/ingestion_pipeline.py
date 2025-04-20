"""
Ingestion pipeline for processing documents.
"""

from qdrant_client.http import models

from qdrant_loader.config.state import IngestionStatus
from qdrant_loader.config.types import SourceType

from ..config import Settings, SourcesConfig
from ..connectors.confluence import ConfluenceConnector
from ..connectors.git import GitConnector
from ..connectors.jira import JiraConnector
from ..connectors.publicdocs import PublicDocsConnector
from ..utils.logging import LoggingConfig
from .chunking_service import ChunkingService
from .document import Document
from .embedding_service import EmbeddingService
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
            # Process Git repositories
            if filtered_config.git:
                for name, config in filtered_config.git.items():
                    self.logger.info(f"Configuring Git repository: {name}")
                    try:
                        async with GitConnector(config) as connector:
                            git_docs = await connector.get_documents()
                            documents.extend(git_docs)
                            await self.state_manager.update_last_ingestion(
                                config.source_type,
                                config.source,
                                IngestionStatus.SUCCESS,
                                document_count=len(git_docs),
                            )
                    except Exception as e:
                        self.logger.error(
                            f"Failed to process Git repository {name}",
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

            # Process Confluence spaces
            if filtered_config.confluence:
                for name, config in filtered_config.confluence.items():
                    self.logger.debug(f"Configuring Confluence space: {name}")
                    try:
                        async with ConfluenceConnector(config) as connector:
                            confluence_docs = await connector.get_documents()
                            documents.extend(confluence_docs)
                            await self.state_manager.update_last_ingestion(
                                config.source_type,
                                config.source,
                                IngestionStatus.SUCCESS,
                                document_count=len(confluence_docs),
                            )
                    except Exception as e:
                        self.logger.error(
                            f"Failed to process Confluence space {name}",
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

            # Process Jira projects
            if filtered_config.jira:
                for name, config in filtered_config.jira.items():
                    self.logger.debug(f"Configuring Jira project: {name}")
                    try:
                        async with JiraConnector(config) as connector:
                            jira_docs = await connector.get_documents()
                            documents.extend(jira_docs)
                            await self.state_manager.update_last_ingestion(
                                config.source_type,
                                config.source,
                                IngestionStatus.SUCCESS,
                                document_count=len(jira_docs),
                            )
                    except Exception as e:
                        self.logger.error(
                            f"Failed to process Jira project {name}",
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

            # Process public documentation
            if filtered_config.publicdocs:
                for name, config in filtered_config.publicdocs.items():
                    self.logger.debug(f"Configuring public documentation: {name}")
                    try:
                        async with PublicDocsConnector(config) as connector:
                            publicdocs = await connector.get_documentation()
                            documents.extend(publicdocs)
                            await self.state_manager.update_last_ingestion(
                                config.source_type,
                                config.source,
                                IngestionStatus.SUCCESS,
                                document_count=len(publicdocs),
                            )
                    except Exception as e:
                        self.logger.error(
                            f"Failed to process public documentation {name}",
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

            self.logger.info(f"Found {len(documents)} documents to process")
            self.logger.debug(f"Documents: {documents}")

            # TODO: This is where the filtering will happen. We need to determine what are the new documents, the updated ones, and then figure out the one that were deleted.

            # Process all valid documents
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

                    # Chunk document
                    try:
                        chunks = self.chunking_service.chunk_document(doc)
                    except Exception as e:
                        self.logger.error(f"Error chunking document {doc.id}: {e!s}")
                        raise

                    # Get embeddings
                    chunk_contents = [chunk.content for chunk in chunks]
                    embeddings = await self.embedding_service.get_embeddings(chunk_contents)

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
                        self.logger.debug(f"Embedding length: {len(embedding) if embedding else 0}")

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

                except Exception as e:
                    self.logger.error(f"Error processing document {doc.id}: {e!s}")
                    raise

            return documents

        except Exception as e:
            self.logger.error(
                "Failed to process documents",
                error=str(e),
                error_type=type(e).__name__,
                error_class=e.__class__.__name__,
            )
            raise

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
