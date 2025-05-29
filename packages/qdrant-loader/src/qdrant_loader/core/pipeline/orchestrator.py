"""Main orchestrator for the ingestion pipeline."""

from qdrant_loader.config import Settings, SourcesConfig
from qdrant_loader.connectors.confluence import ConfluenceConnector
from qdrant_loader.connectors.git import GitConnector
from qdrant_loader.connectors.jira import JiraConnector
from qdrant_loader.connectors.localfile import LocalFileConnector
from qdrant_loader.connectors.publicdocs import PublicDocsConnector
from qdrant_loader.core.document import Document
from qdrant_loader.core.state.state_change_detector import StateChangeDetector
from qdrant_loader.core.state.state_manager import StateManager
from qdrant_loader.utils.logging import LoggingConfig

from .document_pipeline import DocumentPipeline
from .source_filter import SourceFilter
from .source_processor import SourceProcessor

logger = LoggingConfig.get_logger(__name__)


class PipelineComponents:
    """Container for pipeline components."""

    def __init__(
        self,
        document_pipeline: DocumentPipeline,
        source_processor: SourceProcessor,
        source_filter: SourceFilter,
        state_manager: StateManager,
    ):
        self.document_pipeline = document_pipeline
        self.source_processor = source_processor
        self.source_filter = source_filter
        self.state_manager = state_manager


class PipelineOrchestrator:
    """Main orchestrator for the ingestion pipeline."""

    def __init__(self, settings: Settings, components: PipelineComponents):
        self.settings = settings
        self.components = components

    async def process_documents(
        self,
        sources_config: SourcesConfig | None = None,
        source_type: str | None = None,
        source: str | None = None,
    ) -> list[Document]:
        """Main entry point for document processing.

        Args:
            sources_config: Sources configuration to use
            source_type: Filter by source type
            source: Filter by specific source name

        Returns:
            List of processed documents
        """
        logger.info("🚀 Starting document ingestion")

        try:
            # Use default sources config if none provided
            if not sources_config:
                sources_config = self.settings.sources_config

            # Filter sources based on type and name
            filtered_config = self.components.source_filter.filter_sources(
                sources_config, source_type, source
            )

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

            # Collect documents from all sources
            documents = await self._collect_documents_from_sources(filtered_config)

            if not documents:
                logger.info("✅ No documents found from sources")
                return []

            # Detect changes in documents
            documents = await self._detect_document_changes(documents, filtered_config)

            if not documents:
                logger.info("✅ No new or updated documents to process")
                return []

            # Process documents through the pipeline
            result = await self.components.document_pipeline.process_documents(
                documents
            )

            # Update document states for successfully processed documents
            await self._update_document_states(
                documents, result.successfully_processed_documents
            )

            logger.info(
                f"✅ Ingestion completed: {result.success_count} chunks processed successfully"
            )
            return documents

        except Exception as e:
            logger.error(f"❌ Pipeline orchestration failed: {e}", exc_info=True)
            raise

    async def _collect_documents_from_sources(
        self, filtered_config: SourcesConfig
    ) -> list[Document]:
        """Collect documents from all configured sources."""
        documents = []

        # Process each source type
        if filtered_config.confluence:
            confluence_docs = (
                await self.components.source_processor.process_source_type(
                    filtered_config.confluence, ConfluenceConnector, "Confluence"
                )
            )
            documents.extend(confluence_docs)

        if filtered_config.git:
            git_docs = await self.components.source_processor.process_source_type(
                filtered_config.git, GitConnector, "Git"
            )
            documents.extend(git_docs)

        if filtered_config.jira:
            jira_docs = await self.components.source_processor.process_source_type(
                filtered_config.jira, JiraConnector, "Jira"
            )
            documents.extend(jira_docs)

        if filtered_config.publicdocs:
            publicdocs_docs = (
                await self.components.source_processor.process_source_type(
                    filtered_config.publicdocs, PublicDocsConnector, "PublicDocs"
                )
            )
            documents.extend(publicdocs_docs)

        if filtered_config.localfile:
            localfile_docs = await self.components.source_processor.process_source_type(
                filtered_config.localfile, LocalFileConnector, "LocalFile"
            )
            documents.extend(localfile_docs)

        logger.info(f"📄 Collected {len(documents)} documents from all sources")
        return documents

    async def _detect_document_changes(
        self, documents: list[Document], filtered_config: SourcesConfig
    ) -> list[Document]:
        """Detect changes in documents and return only new/updated ones."""
        if not documents:
            return []

        logger.debug(f"Starting change detection for {len(documents)} documents")

        try:
            # Ensure state manager is initialized before use
            if not self.components.state_manager._initialized:
                logger.debug("Initializing state manager for change detection")
                await self.components.state_manager.initialize()

            async with StateChangeDetector(
                self.components.state_manager
            ) as change_detector:
                changes = await change_detector.detect_changes(
                    documents, filtered_config
                )

                logger.info(
                    f"🔍 Change detection: {len(changes['new'])} new, "
                    f"{len(changes['updated'])} updated, {len(changes['deleted'])} deleted"
                )

                # Return new and updated documents
                return changes["new"] + changes["updated"]

        except Exception as e:
            logger.error(f"Error during change detection: {e}", exc_info=True)
            raise

    async def _update_document_states(
        self, documents: list[Document], successfully_processed_doc_ids: set
    ):
        """Update document states for successfully processed documents."""
        successfully_processed_docs = [
            doc for doc in documents if doc.id in successfully_processed_doc_ids
        ]

        logger.debug(
            f"Updating document states for {len(successfully_processed_docs)} documents"
        )

        # Ensure state manager is initialized before use
        if not self.components.state_manager._initialized:
            logger.debug("Initializing state manager for document state updates")
            await self.components.state_manager.initialize()

        for doc in successfully_processed_docs:
            try:
                await self.components.state_manager.update_document_state(doc)
                logger.debug(f"Updated document state for {doc.id}")
            except Exception as e:
                logger.error(f"Failed to update document state for {doc.id}: {e}")
