"""Main orchestrator for the ingestion pipeline."""

import traceback
from collections.abc import AsyncIterator
from datetime import datetime

from qdrant_loader.config import Settings, SourcesConfig
from qdrant_loader.connectors.base import ConnectorConfigurationError
from qdrant_loader.connectors.factory import get_connector_instance
from qdrant_loader.core.document import Document
from qdrant_loader.core.project_manager import ProjectManager
from qdrant_loader.core.qdrant_manager import QdrantManager
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
        qdrant_manager: QdrantManager,
    ):
        self.document_pipeline = document_pipeline
        self.source_processor = source_processor
        self.source_filter = source_filter
        self.state_manager = state_manager
        self.qdrant_manager = qdrant_manager


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

    async def _stream_batches_from_sources(
        self,
        filtered_config: SourcesConfig,
        batch_size: int = 256,
        since: datetime | None = None,
        project_id: str | None = None,
        seen_uris: set[str] | None = None,
    ) -> AsyncIterator[list[Document]]:
        """Stream source documents in bounded micro-batches.

        This helper collects documents from each source type and yields
        batches of a fixed size, keeping memory usage bounded.
        """
        batch: list[Document] = []

        # Note: previous implementation contained vestigial async inner
        # helpers `_flush_batch` and `_append_document` which attempted to
        # yield from inside non-generator contexts. These were dead code
        # and confusing. Batching is handled inline in `_process_source_type`.

        async def _process_source_type(source_type_name: str, source_configs):
            if not source_configs:
                return

            async for (
                document
            ) in self.components.source_processor.stream_source_documents(
                source_configs,
                get_connector_instance,
                source_type_name,
                since=since,
            ):
                # Inject project metadata when running with project context
                if project_id and self.project_manager:
                    try:
                        document.metadata = (
                            self.project_manager.inject_project_metadata(
                                project_id, document.metadata
                            )
                        )
                    except Exception:
                        # Don't let metadata injection break streaming; log and continue
                        logger.debug(
                            "Project metadata injection failed for document",
                            document_id=document.id,
                            project_id=project_id,
                        )

                # Track seen URIs for potential post-stream reconciliation
                if seen_uris is not None:
                    try:
                        uri = f"{document.source_type}:{document.source}:{document.url.rstrip('/') }"
                        seen_uris.add(uri)
                    except Exception:
                        pass

                batch.append(document)
                if len(batch) >= batch_size:
                    yield batch.copy()
                    batch.clear()

        if filtered_config.confluence:
            async for yielded_batch in _process_source_type(
                "Confluence", filtered_config.confluence
            ):
                yield yielded_batch

        if filtered_config.git:
            async for yielded_batch in _process_source_type("Git", filtered_config.git):
                yield yielded_batch

        if filtered_config.jira:
            async for yielded_batch in _process_source_type(
                "Jira", filtered_config.jira
            ):
                yield yielded_batch

        if filtered_config.publicdocs:
            async for yielded_batch in _process_source_type(
                "PublicDocs", filtered_config.publicdocs
            ):
                yield yielded_batch

        if filtered_config.localfile:
            async for yielded_batch in _process_source_type(
                "LocalFile", filtered_config.localfile
            ):
                yield yielded_batch

        if batch:
            yield batch

    async def process_documents(
        self,
        sources_config: SourcesConfig | None = None,
        source_type: str | None = None,
        source: str | None = None,
        project_id: str | None = None,
        force: bool = False,
        since: datetime | None = None,
    ) -> list[Document]:
        """Main entry point for document processing.

        Args:
            sources_config: Sources configuration to use (for backward compatibility)
            source_type: Filter by source type
            source: Filter by specific source name
            project_id: Process documents for a specific project
            force: Force processing of all documents, bypassing change detection
            since: Only stream documents updated after this timestamp (connector-level
                filtering). Connectors that do not yet support time-based filtering will
                fall back to full fetch with hash-based change detection.

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
                return await self._process_all_projects(
                    source_type, source, force, since
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

            # Stream documents in bounded micro-batches and process each batch
            total_documents = 0
            processed_documents: list[Document] = []
            aggregated_result = PipelineResult()
            batch_count = 0

            if not force and not self.components.state_manager._initialized:
                logger.debug("Initializing state manager for change detection")
                await self.components.state_manager.initialize()

            change_detector = None
            if not force:
                change_detector = await StateChangeDetector(
                    self.components.state_manager
                ).__aenter__()

            seen_uris: set[str] = set()
            try:
                # Prefer calling the new signature but fall back to the
                # legacy 3-arg signature for backwards compatibility / tests.
                try:
                    stream_iter = self._stream_batches_from_sources(
                        filtered_config,
                        256,
                        since,
                        project_id=current_project_id,
                        seen_uris=seen_uris,
                    )
                except TypeError:
                    # Callable likely expects the old signature
                    stream_iter = self._stream_batches_from_sources(
                        filtered_config, 256, since
                    )

                async for batch in stream_iter:
                    total_documents += len(batch)
                    batch_count += 1

                    if not force and change_detector is not None:
                        batch = await change_detector.classify_batch(
                            batch, filtered_config, current_project_id
                        )

                    if not batch:
                        continue

                    batch_result = (
                        await self.components.document_pipeline.process_batch(batch)
                    )
                    aggregated_result.success_count += batch_result.success_count
                    aggregated_result.error_count += batch_result.failure_count
                    aggregated_result.errors.extend(batch_result.errors)
                    aggregated_result.successfully_processed_documents.update(
                        batch_result.successfully_processed_documents
                    )
                    aggregated_result.failed_document_ids.update(
                        batch_result.failed_document_ids
                    )

                    if batch_result.successfully_processed_documents:
                        await self._update_document_states(
                            batch,
                            batch_result.successfully_processed_documents,
                            current_project_id,
                        )
                        processed_documents.extend(
                            [
                                doc
                                for doc in batch
                                if doc.id
                                in batch_result.successfully_processed_documents
                            ]
                        )

                if total_documents == 0 and not force:
                    logger.warning(
                        "⚠️ EMPTY SNAPSHOT in non-force mode. About to enter change detection "
                        "which may classify existing corpus as deleted if source API returned partial/null results. "
                        "This is a known risk (WS-3: add explicit snapshot_is_complete signal or per-source enable_deletion_detection). "
                        "Proceeding carefully."
                    )

                if total_documents == 0 and force:
                    logger.info("✅ No documents found from sources")
                    return []

                if not force and not processed_documents:
                    self.last_pipeline_result = aggregated_result
                    if aggregated_result.error_count > 0:
                        logger.error(
                            "No documents were successfully processed",
                            error_count=aggregated_result.error_count,
                        )
                    else:
                        logger.info("No new or updated documents to process")
                    return []

                    # Deletion detection / reconciliation note:
                    # Streaming classification only detects new/updated documents
                    # per-batch. Full deletion detection (documents present in the
                    # state DB but absent from the current snapshot across all
                    # batches) requires a post-stream reconciliation (WS-3).
                    # For now we only log that reconciliation is possible and
                    # record the set of seen URIs; implementors can enable a
                    # reconciliation pass that compares previous state URIs to
                    # `seen_uris` and call `_process_deleted_documents`.
                    if not force:
                        logger.debug(
                            "Post-stream reconciliation not enabled. Seen URIs collected for potential WS-3 reconciliation",
                            seen_count=len(seen_uris),
                        )

                self.last_pipeline_result = aggregated_result
                logger.info(
                    f"✅ Ingestion completed: {aggregated_result.success_count} chunks processed successfully"
                )
                return processed_documents
            finally:
                if change_detector is not None:
                    await change_detector.__aexit__(None, None, None)

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
        since: datetime | None = None,
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
                    since=since,
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

    async def _collect_documents_from_sources(
        self, filtered_config: SourcesConfig, project_id: str | None = None
    ) -> list[Document]:
        """Collect documents from all configured sources."""
        documents = []

        # Process each source type with project context
        if filtered_config.confluence:
            confluence_docs = (
                await self.components.source_processor.process_source_type(
                    filtered_config.confluence, get_connector_instance, "Confluence"
                )
            )
            documents.extend(confluence_docs)

        if filtered_config.git:
            git_docs = await self.components.source_processor.process_source_type(
                filtered_config.git, get_connector_instance, "Git"
            )
            documents.extend(git_docs)

        if filtered_config.jira:
            jira_docs = await self.components.source_processor.process_source_type(
                filtered_config.jira, get_connector_instance, "Jira"
            )
            documents.extend(jira_docs)

        if filtered_config.publicdocs:
            publicdocs_docs = (
                await self.components.source_processor.process_source_type(
                    filtered_config.publicdocs, get_connector_instance, "PublicDocs"
                )
            )
            documents.extend(publicdocs_docs)

        if filtered_config.localfile:
            localfile_docs = await self.components.source_processor.process_source_type(
                filtered_config.localfile, get_connector_instance, "LocalFile"
            )
            documents.extend(localfile_docs)

        # Inject project metadata into documents if project context is available
        if project_id and self.project_manager:
            for document in documents:
                enhanced_metadata = self.project_manager.inject_project_metadata(
                    project_id, document.metadata
                )
                document.metadata = enhanced_metadata

        logger.info(f"📄 Collected {len(documents)} documents from all sources")
        return documents

    async def _detect_document_changes(
        self,
        documents: list[Document],
        filtered_config: SourcesConfig,
        project_id: str | None = None,
    ) -> list[Document]:
        """Detect changes in documents and return only new/updated ones."""

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

            new_documents = list(changes.get("new") or [])
            updated_documents = list(changes.get("updated") or [])
            deleted_documents = list(changes.get("deleted") or [])

            logger.info(
                f"🔍 Change detection: {len(new_documents)} new, "
                f"{len(updated_documents)} updated, "
                f"{len(deleted_documents)} deleted"
            )

            if deleted_documents:
                await self._process_deleted_documents(
                    deleted_documents,
                    project_id,
                )

            documents_to_process = new_documents + updated_documents

            if not documents_to_process and deleted_documents:
                logger.info(
                    "No new or updated documents to process, "
                    "but deleted documents were handled"
                )

            return documents_to_process

        except Exception as e:
            logger.error(
                f"Error during change detection: {sanitize_exception_message(e)}",
                error_type=type(e).__name__,
            )
            raise

    async def _process_deleted_documents(
        self,
        deleted_documents: list[Document],
        project_id: str | None = None,
    ) -> None:
        """Process deleted documents by updating state and removing points from Qdrant."""
        if not deleted_documents:
            return

        logger.info(f"Processing {len(deleted_documents)} deleted documents")

        if not self.components.state_manager._initialized:
            logger.debug("Initializing state manager for deleted document processing")
            await self.components.state_manager.initialize()

        # Use an atomic operation that marks state and deletes points together.
        try:
            deleted_ids = (
                await self.components.state_manager.mark_documents_deleted_atomic(
                    deleted_documents, self.components.qdrant_manager, project_id
                )
            )
            if deleted_ids:
                logger.info(
                    f"Deleted {len(deleted_ids)} document points from Qdrant and updated state"
                )
        except Exception as e:
            logger.error(
                f"Failed to process deleted documents atomically: {sanitize_exception_message(e)}",
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
