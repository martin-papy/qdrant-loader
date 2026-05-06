"""Main orchestrator for the ingestion pipeline."""

import asyncio
import os
import traceback

import psutil
from qdrant_loader.config import Settings, SourcesConfig
from qdrant_loader.connectors.base import ConnectorConfigurationError
from qdrant_loader.connectors.factory import get_connector_instance
from qdrant_loader.core.document import Document
from qdrant_loader.core.project_manager import ProjectManager
from qdrant_loader.core.state.state_change_detector import StateChangeDetector
from qdrant_loader.core.state.state_manager import StateManager
from qdrant_loader.utils.logging import LoggingConfig
from qdrant_loader.utils.sensitive import sanitize_exception_message

from .document_pipeline import DocumentPipeline
from .source_filter import SourceFilter
from .source_processor import SourceProcessor
from .workers.upsert_worker import PipelineResult

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

    def __init__(
        self,
        settings: Settings,
        components: PipelineComponents,
        project_manager: ProjectManager | None = None,
    ):
        self.settings = settings
        self.components = components
        self.project_manager = project_manager
        self.last_pipeline_result = None

    async def process_documents(
        self,
        sources_config: SourcesConfig | None = None,
        source_type: str | None = None,
        source: str | None = None,
        project_id: str | None = None,
        force: bool = False,
    ) -> list[Document]:
        """Main entry point for document processing.

        Args:
            sources_config: Sources configuration to use (for backward compatibility)
            source_type: Filter by source type
            source: Filter by specific source name
            project_id: Process documents for a specific project
            force: Force processing of all documents, bypassing change detection

        Returns:
            List of processed documents
        """
        logger.info("🚀 Starting document ingestion")
        self.last_pipeline_result = None

        try:
            # Determine sources configuration to use
            if sources_config:
                # Use provided sources config (backward compatibility)
                logger.debug("Using provided sources configuration")
                filtered_config = self.components.source_filter.filter_sources(
                    sources_config, source_type, source
                )
                current_project_id = None
            elif project_id:
                # Use project-specific sources configuration
                if not self.project_manager:
                    raise ValueError(
                        "Project manager not available for project-specific processing"
                    )

                project_context = self.project_manager.get_project_context(project_id)
                if (
                    not project_context
                    or not project_context.config
                    or not project_context.config.sources
                ):
                    raise ValueError(
                        f"Project '{project_id}' not found or has no configuration"
                    )

                logger.debug(f"Using project configuration for project: {project_id}")
                project_sources_config = project_context.config.sources
                filtered_config = self.components.source_filter.filter_sources(
                    project_sources_config, source_type, source
                )
                current_project_id = project_id
            else:
                # Process all projects
                if not self.project_manager:
                    raise ValueError(
                        "Project manager not available and no sources configuration provided"
                    )

                logger.debug("Processing all projects")
                return await self._process_all_projects(source_type, source, force)

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
            await self._stream_and_process_sources(
                filtered_config,
                current_project_id,
                force=force,
            )

            logger.info("✅ Streaming ingestion completed")
            return []

        except Exception as e:
            logger.error(
                f"❌ Pipeline orchestration failed: {sanitize_exception_message(e)}",
                error_type=type(e).__name__,
                sanitized_traceback=sanitize_exception_message(traceback.format_exc()),
            )
            raise

    async def _process_all_projects(
        self,
        source_type: str | None = None,
        source: str | None = None,
        force: bool = False,
    ) -> list[Document]:
        """Process documents from all configured projects."""
        if not self.project_manager:
            raise ValueError("Project manager not available")

        all_documents = []
        aggregated_result = PipelineResult()
        failed_projects: list[str] = []
        project_ids = self.project_manager.list_project_ids()

        logger.info(f"Processing {len(project_ids)} projects")

        for project_id in project_ids:
            try:
                logger.debug(f"Processing project: {project_id}")
                project_documents = await self.process_documents(
                    project_id=project_id,
                    source_type=source_type,
                    source=source,
                    force=force,
                )
                project_result = self.last_pipeline_result
                all_documents.extend(project_documents)

                if project_result is not None:
                    aggregated_result.success_count += project_result.success_count
                    aggregated_result.error_count += project_result.error_count
                    aggregated_result.successfully_processed_documents.update(
                        project_result.successfully_processed_documents
                    )
                    aggregated_result.failed_document_ids.update(
                        project_result.failed_document_ids
                    )
                    aggregated_result.errors.extend(project_result.errors)

                logger.debug(
                    f"Processed {len(project_documents)} documents from project: {project_id}"
                )
            except ConnectorConfigurationError as e:
                logger.error(
                    f"Configuration error in project {project_id}: "
                    f"{sanitize_exception_message(e)}. "
                    "Skipping this project — check connector settings.",
                    error_type=type(e).__name__,
                    sanitized_traceback=sanitize_exception_message(
                        traceback.format_exc()
                    ),
                )
                aggregated_result.errors.append(
                    f"Configuration error in project {project_id}: "
                    f"{sanitize_exception_message(e)}"
                )
                failed_projects.append(project_id)
                continue
            except Exception as e:
                safe_error = sanitize_exception_message(e)
                sanitized_traceback = sanitize_exception_message(traceback.format_exc())
                aggregated_result.error_count += 1
                aggregated_result.errors.append(
                    "project_id="
                    f"{project_id}; "
                    "error_type="
                    f"{type(e).__name__}; "
                    "message="
                    f"{safe_error}; "
                    "traceback="
                    f"{sanitized_traceback}"
                )
                logger.error(
                    f"Failed to process project {project_id}: {safe_error}",
                    error_type=type(e).__name__,
                    sanitized_traceback=sanitized_traceback,
                )
                failed_projects.append(project_id)
                # Continue processing other projects
                continue

        self.last_pipeline_result = aggregated_result

        total_count = len(project_ids)
        failed_count = len(failed_projects)
        success_count = total_count - failed_count
        if failed_count > 0:
            logger.warning(
                f"Completed processing projects: {success_count}/{total_count} succeeded, "
                f"{failed_count} failed. Check errors above for details.",
                total_projects=total_count,
                successful_projects=success_count,
                failed_projects=failed_count,
            )
        else:
            logger.info(
                f"Completed processing all projects: {len(all_documents)} total documents"
            )
        return all_documents

    async def _detect_document_changes(
        self,
        documents: list[Document],
        filtered_config: SourcesConfig,
        project_id: str | None = None,
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
            logger.error(
                f"Error during change detection: {sanitize_exception_message(e)}",
                error_type=type(e).__name__,
            )
            raise

    async def _update_document_states(
        self,
        documents: list[Document],
        successfully_processed_doc_ids: set,
        project_id: str | None = None,
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
                await self.components.state_manager.update_document_state(
                    doc, project_id
                )
                logger.debug(f"Updated document state for {doc.id}")
            except Exception as e:
                logger.error(
                    f"Failed to update document state for {doc.id}: {sanitize_exception_message(e)}",
                    error_type=type(e).__name__,
                )

    async def _stream_and_process_sources(
        self,
        filtered_config: SourcesConfig,
        project_id: str | None = None,
        force: bool = False,
    ):
        batch_size = self.settings.global_config.embedding.batch_size or 100
        first_batch_size = 32

        state_manager = self.components.state_manager
        pipeline = self.components.document_pipeline

        if not state_manager._initialized:
            await state_manager.initialize()
        
        async with StateChangeDetector(state_manager) as change_detector:
            sources = await self.components.source_processor.get_sources(filtered_config)
            tasks = [
                asyncio.create_task(
                    self._ingest_single_source(
                        source,
                        pipeline,
                        change_detector,
                        batch_size,
                        first_batch_size,
                        force,
                        project_id,
                    )
                )
                for source in sources
            ]
            await asyncio.gather(*tasks)
        
    async def _ingest_single_source(
        self,
        connector,
        pipeline,
        change_detector,
        batch_size,
        first_batch_size,
        force,
        project_id,
    ):
        batch = []
        started = False

        async for doc in connector.stream_documents():

            batch.append(doc)

            # 🚀 early flush để đạt <2s
            if not started and len(batch) >= first_batch_size:
                await self._handle_batch(batch, pipeline, change_detector, force, project_id)
                batch.clear()
                started = True

            elif len(batch) >= batch_size:
                self.log_memory()
                await self._handle_batch(batch, pipeline, change_detector, force, project_id)
                batch.clear()

        # flush cuối
        if batch:
            await self._handle_batch(batch, pipeline, change_detector, force, project_id)
    
    async def _handle_batch(
        self,
        batch,
        pipeline,
        change_detector,
        force,
        project_id,
    ):
        try:
            if force:
                to_process = batch
            else:
                new_docs, updated_docs, deleted_ids = await change_detector.classify_batch(batch)

                to_process = new_docs + updated_docs

                if deleted_ids:
                    await pipeline.delete_batch(deleted_ids)

            if not to_process:
                return

            result = await pipeline.process_batch(to_process)

            # 🔥 update state ngay sau mỗi batch
            await self._update_document_states(
                to_process,
                result.successfully_processed_documents,
                project_id,
            )

        except Exception as e:
            logger.exception("Batch processing failed", error=str(e))
    
    # function to test memory usage at any point in the pipeline
    def log_memory():
        process = psutil.Process(os.getpid())
        mem = process.memory_info().rss / 1024 / 1024
        logger.info(f"🧠 Memory usage: {mem:.2f} MB")

