"""
Ingestion pipeline for processing documents.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, UTC
import logging
import structlog

from ..config import Settings, GlobalConfig, SourcesConfig
from ..connectors.git import GitConnector
from ..connectors.confluence import ConfluenceConnector
from ..connectors.jira import JiraConnector
from ..connectors.public_docs import PublicDocsConnector
from .chunking_service import ChunkingService
from .embedding_service import EmbeddingService
from .qdrant_manager import QdrantManager
from .document import Document
from .state import StateManager

logger = structlog.get_logger()

class IngestionPipeline:
    """Pipeline for processing documents."""

    def __init__(self, settings: Settings):
        """Initialize the ingestion pipeline."""
        if not settings:
            raise ValueError("Settings not available. Please check your environment variables.")

        self.settings = settings
        self.config = settings.global_config
        if not self.config:
            raise ValueError("Global configuration not available. Please check your configuration file.")

        # Initialize services
        self.chunking_service = ChunkingService(config=self.config, settings=self.settings)
        self.embedding_service = EmbeddingService(settings)
        self.qdrant_manager = QdrantManager(settings)
        self.state_manager = StateManager(settings.STATE_DB_PATH)

    async def process_documents(
        self,
        sources_config: Optional[SourcesConfig] = None,
        source_type: Optional[str] = None,
        source_name: Optional[str] = None
    ) -> List[Document]:
        """Process documents from all configured sources."""
        if not sources_config:
            sources_config = self.settings.sources_config

        if not sources_config:
            logger.warning("No sources configured")
            return []

        # Filter sources based on type and name
        filtered_config = self._filter_sources(sources_config, source_type, source_name)
        
        documents: List[Document] = []
        
        try:
            # Process Git repositories
            if filtered_config.git_repos:
                for name, config in filtered_config.git_repos.items():
                    connector = GitConnector(config)
                    git_docs = await connector.get_documentation()
                    documents.extend(git_docs)

            # Process Confluence spaces
            if filtered_config.confluence:
                for name, config in filtered_config.confluence.items():
                    connector = ConfluenceConnector(config)
                    confluence_docs = await connector.get_documentation()
                    documents.extend(confluence_docs)

            # Process Jira projects
            if filtered_config.jira:
                for name, config in filtered_config.jira.items():
                    connector = JiraConnector(config)
                    jira_docs = await connector.get_documentation()
                    documents.extend(jira_docs)

            # Process public documentation
            if filtered_config.public_docs:
                for name, config in filtered_config.public_docs.items():
                    connector = PublicDocsConnector(config)
                    public_docs = await connector.get_documentation()
                    documents.extend(public_docs)

            # Process all documents
            for doc in documents:
                # Update document state
                await self.state_manager.update_document_state(doc)

                # Chunk document
                chunks = self.chunking_service.chunk_document(doc)

                # Get embeddings
                embeddings = await self.embedding_service.get_embeddings(chunks)

                # Update Qdrant
                await self.qdrant_manager.upsert_points(chunks, embeddings)

            return documents

        except Exception as e:
            logger.error("Failed to process documents", error=str(e))
            raise

    def _filter_sources(
        self,
        sources_config: SourcesConfig,
        source_type: Optional[str] = None,
        source_name: Optional[str] = None
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