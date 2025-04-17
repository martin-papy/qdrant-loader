"""
Ingestion pipeline for processing documents.
"""

from datetime import UTC, datetime
import uuid

from pydantic import HttpUrl
from qdrant_client.http import models

from ..config import Settings, SourcesConfig
from ..connectors.confluence import ConfluenceConnector
from ..connectors.git import GitConnector
from ..connectors.jira import JiraConfig, JiraConnector
from ..connectors.public_docs import PublicDocsConnector
from ..utils.logging import LoggingConfig
from .chunking_service import ChunkingService
from .document import Document
from .embedding_service import EmbeddingService
from .qdrant_manager import QdrantManager
from .state import DocumentState, StateManager

logger = LoggingConfig.get_logger(__name__)


class IngestionPipeline:
    """Pipeline for processing documents."""

    def __init__(self, settings: Settings):
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
        self.qdrant_manager = QdrantManager(settings)
        self.state_manager = StateManager(self.config.state_management)
        self.logger = LoggingConfig.get_logger(__name__)

    async def process_documents(
        self,
        sources_config: SourcesConfig | None = None,
        source_type: str | None = None,
        source_name: str | None = None,
    ) -> list[Document]:
        """Process documents from all configured sources."""
        if not sources_config:
            sources_config = self.settings.sources_config
            self.logger.error("No sources configured")
            return []

        # Filter sources based on type and name
        filtered_config = self._filter_sources(sources_config, source_type, source_name)

        documents: list[Document] = []

        try:
            # Process Git repositories
            if filtered_config.git_repos:
                for name, config in filtered_config.git_repos.items():
                    self.logger.info(f"Configuring Git repository: {name}")
                    try:
                        with GitConnector(config) as connector:
                            git_docs = await connector.get_documents()
                            documents.extend(git_docs)
                    except Exception as e:
                        self.logger.error(
                            f"Failed to process Git repository {name}",
                            error=str(e),
                            error_type=type(e).__name__,
                            error_class=e.__class__.__name__,
                        )
                        raise

            # Process Confluence spaces
            if filtered_config.confluence:
                for name, config in filtered_config.confluence.items():
                    self.logger.debug(f"Configuring Confluence space: {name}")
                    connector = ConfluenceConnector(config)
                    confluence_docs = await connector.get_documents()
                    documents.extend(confluence_docs)

            # Process Jira projects
            if filtered_config.jira:
                for name, config in filtered_config.jira.items():
                    self.logger.debug(f"Configuring Jira project: {name}")
                    # Convert JiraProjectConfig to JiraConfig
                    jira_config = JiraConfig(
                        base_url=HttpUrl(config.base_url),
                        project_key=config.project_key,
                        requests_per_minute=config.requests_per_minute,
                        page_size=config.page_size,
                        process_attachments=config.process_attachments,
                        track_last_sync=config.track_last_sync,
                        api_token=config.token,
                        email=config.email,
                    )
                    connector = JiraConnector(jira_config)
                    jira_docs = await connector.get_documents()
                    documents.extend(jira_docs)

            # Process public documentation
            if filtered_config.public_docs:
                for name, config in filtered_config.public_docs.items():
                    self.logger.debug(f"Configuring public documentation: {name}")
                    connector = PublicDocsConnector(config)
                    public_docs = await connector.get_documentation()
                    documents.extend(public_docs)

            self.logger.debug(f"Found {len(documents)} documents to process", documents=documents)
            # Process all documents
            for doc in documents:
                try:
                    # Convert Document to DocumentState
                    now = datetime.now(UTC)
                    doc_state = DocumentState(
                        source_type=doc.source_type or "unknown",
                        source_name=doc.source or "unknown",
                        document_id=doc.id or str(uuid.uuid4()),
                        last_updated=doc.last_updated if doc.last_updated is not None else now,
                        last_ingested=now,
                        is_deleted=False,
                        created_at=now,
                        updated_at=now,
                    )
                    self.logger.debug(f"Document state created: {doc_state}")
                    # Update document state
                    await self.state_manager.update_document_state(doc_state)

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
                            },
                        )
                        self.logger.debug(f"Point created: {point}")
                        points.append(point)

                    # Update Qdrant
                    await self.qdrant_manager.upsert_points(points)

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
        source_name: str | None = None,
    ) -> SourcesConfig:
        """Filter sources based on type and name."""
        if not source_type:
            return sources_config

        filtered = SourcesConfig()

        if source_type == "git":
            if source_name:
                if source_name in sources_config.git_repos:
                    filtered.git_repos = {source_name: sources_config.git_repos[source_name]}
            else:
                filtered.git_repos = sources_config.git_repos

        elif source_type == "confluence":
            if source_name:
                if source_name in sources_config.confluence:
                    filtered.confluence = {source_name: sources_config.confluence[source_name]}
            else:
                filtered.confluence = sources_config.confluence

        elif source_type == "jira":
            if source_name:
                if source_name in sources_config.jira:
                    filtered.jira = {source_name: sources_config.jira[source_name]}
            else:
                filtered.jira = sources_config.jira

        elif source_type == "public-docs":
            if source_name:
                if source_name in sources_config.public_docs:
                    filtered.public_docs = {source_name: sources_config.public_docs[source_name]}
            else:
                filtered.public_docs = sources_config.public_docs

        return filtered
