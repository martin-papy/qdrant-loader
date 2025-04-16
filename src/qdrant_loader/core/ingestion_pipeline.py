"""
Ingestion pipeline for processing documents.
"""

from datetime import UTC, datetime

import structlog
from pydantic import HttpUrl
from qdrant_client.http import models

from ..config import Settings, SourcesConfig
from ..connectors.confluence import ConfluenceConnector
from ..connectors.git import GitConnector
from ..connectors.jira import JiraConfig, JiraConnector
from ..connectors.public_docs import PublicDocsConnector
from .chunking_service import ChunkingService
from .document import Document
from .embedding_service import EmbeddingService
from .qdrant_manager import QdrantManager
from .state import DocumentState, StateManager

logger = structlog.get_logger()


class IngestionPipeline:
    """Pipeline for processing documents."""

    def __init__(self, settings: Settings):
        """Initialize the ingestion pipeline."""
        if settings is None:
            raise ValueError("Settings not available. Please check your environment variables.")

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

    async def process_documents(
        self,
        sources_config: SourcesConfig | None = None,
        source_type: str | None = None,
        source_name: str | None = None,
    ) -> list[Document]:
        """Process documents from all configured sources."""
        if not sources_config:
            sources_config = self.settings.sources_config

        if not sources_config:
            logger.warning("No sources configured")
            return []

        # Filter sources based on type and name
        filtered_config = self._filter_sources(sources_config, source_type, source_name)

        documents: list[Document] = []

        try:
            # Process Git repositories
            if filtered_config.git_repos:
                for name, config in filtered_config.git_repos.items():
                    connector = GitConnector(config)
                    git_docs = await connector.get_documents()
                    documents.extend(git_docs)

            # Process Confluence spaces
            if filtered_config.confluence:
                for name, config in filtered_config.confluence.items():
                    connector = ConfluenceConnector(config)
                    confluence_docs = await connector.get_documents()
                    documents.extend(confluence_docs)

            # Process Jira projects
            if filtered_config.jira:
                for name, config in filtered_config.jira.items():
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
                    connector = PublicDocsConnector(config)
                    public_docs = await connector.get_documentation()
                    documents.extend(public_docs)

            # Process all documents
            for doc in documents:
                try:
                    # Convert Document to DocumentState
                    doc_state = DocumentState(
                        source_type=doc.source_type,
                        source_name=doc.source,
                        document_id=doc.id,
                        last_updated=doc.last_updated or datetime.now(UTC),
                        last_ingested=datetime.now(UTC),
                        is_deleted=False,
                        created_at=datetime.now(UTC),
                        updated_at=datetime.now(UTC),
                    )
                    # Update document state
                    await self.state_manager.update_document_state(doc_state)

                    # Chunk document
                    try:
                        chunks = self.chunking_service.chunk_document(doc)
                    except Exception as e:
                        logger.error(f"Error chunking document {doc.id}: {e!s}")
                        raise

                    # Get embeddings
                    chunk_contents = [chunk.content for chunk in chunks]
                    embeddings = await self.embedding_service.get_embeddings(chunk_contents)

                    # Create PointStruct instances
                    points = []
                    for chunk, embedding in zip(chunks, embeddings, strict=False):
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
                        points.append(point)

                    # Update Qdrant
                    await self.qdrant_manager.upsert_points(points)

                except Exception as e:
                    logger.error(f"Error processing document {doc.id}: {e!s}")
                    raise

        except Exception as e:
            logger.error(f"Error in document processing pipeline: {e!s}")
            raise

        return documents

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
