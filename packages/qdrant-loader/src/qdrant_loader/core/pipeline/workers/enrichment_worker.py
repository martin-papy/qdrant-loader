"""Enrichment worker for processing documents through the enricher pipeline.

POC2-005: Integration of the pluggable enricher pipeline into the document
processing workflow.
"""

import asyncio
from collections.abc import AsyncIterator

from qdrant_loader.core.document import Document
from qdrant_loader.core.enrichers import EnricherPipeline, PipelineResult
from qdrant_loader.utils.logging import LoggingConfig

from .base_worker import BaseWorker

logger = LoggingConfig.get_logger(__name__)


class EnrichmentWorker(BaseWorker):
    """Handles document enrichment with the pluggable enricher pipeline.

    This worker integrates the enricher pipeline into the document processing
    flow, running before chunking to extract document-level metadata that
    will be inherited by chunks.

    Enrichment is optional and graceful - if enrichment fails for a document,
    the document is still passed through to chunking with its original metadata.
    """

    def __init__(
        self,
        enricher_pipeline: EnricherPipeline,
        max_workers: int = 5,
        queue_size: int = 100,
        shutdown_event: asyncio.Event | None = None,
    ):
        """Initialize the enrichment worker.

        Args:
            enricher_pipeline: Configured enricher pipeline to use
            max_workers: Maximum concurrent enrichment tasks
            queue_size: Queue size for documents
            shutdown_event: Optional shutdown signal
        """
        super().__init__(max_workers, queue_size)
        self.enricher_pipeline = enricher_pipeline
        self.shutdown_event = shutdown_event or asyncio.Event()

    async def process(self, document: Document) -> Document:
        """Process a single document through the enricher pipeline.

        Args:
            document: The document to enrich

        Returns:
            Document with enriched metadata (or original if enrichment fails)
        """
        logger.debug(f"Enrichment worker started for doc {document.id}")

        try:
            # Check for shutdown signal
            if self.shutdown_event.is_set():
                logger.debug(f"Enrichment worker {document.id} exiting due to shutdown")
                return document

            # Run enrichment pipeline
            result: PipelineResult = await self.enricher_pipeline.enrich(document)

            if result.success:
                # Merge enriched metadata into document metadata
                enriched_metadata = result.merged_metadata
                document.metadata.update(enriched_metadata)

                # Log enrichment stats
                successful = result.get_successful_enrichers()
                skipped = result.get_skipped_enrichers()
                failed = result.get_failed_enrichers()

                logger.debug(
                    f"Enriched doc {document.id}: "
                    f"{len(successful)} successful, "
                    f"{len(skipped)} skipped, "
                    f"{len(failed)} failed"
                )
            else:
                # Log warning but don't fail - document passes through with original metadata
                logger.warning(
                    f"Enrichment failed for doc {document.id}: {result.errors}"
                )

            return document

        except asyncio.CancelledError:
            logger.debug(f"Enrichment worker {document.id} cancelled")
            raise
        except Exception as e:
            # Log error but return original document - enrichment is optional
            logger.warning(
                f"Enrichment error for doc {document.url}: {e}. "
                f"Document will continue with original metadata."
            )
            return document

    async def process_documents(
        self, documents: list[Document]
    ) -> AsyncIterator[Document]:
        """Process documents through the enricher pipeline.

        Args:
            documents: List of documents to enrich

        Yields:
            Documents with enriched metadata
        """
        if not documents:
            return

        logger.debug("EnrichmentWorker started")
        logger.info(f"🔄 Enriching {len(documents)} documents...")

        try:
            # Process documents with controlled concurrency
            semaphore = asyncio.Semaphore(self.max_workers)

            async def enrich_document(doc: Document, doc_index: int) -> Document:
                """Enrich a single document with controlled concurrency."""
                try:
                    async with semaphore:
                        if self.shutdown_event.is_set():
                            logger.debug(
                                f"EnrichmentWorker exiting due to shutdown (doc {doc_index})"
                            )
                            return doc

                        return await self.process(doc)

                except Exception as e:
                    logger.warning(
                        f"Enrichment failed for document {doc_index + 1}/{len(documents)} "
                        f"({doc.id}): {e}"
                    )
                    return doc  # Return original document on failure

            # Create tasks for all documents
            tasks = [enrich_document(doc, i) for i, doc in enumerate(documents)]

            # Process tasks as they complete and yield documents
            completed = 0
            enriched_count = 0

            for coro in asyncio.as_completed(tasks):
                if self.shutdown_event.is_set():
                    logger.debug("EnrichmentWorker exiting due to shutdown")
                    break

                try:
                    enriched_doc = await coro
                    completed += 1

                    # Check if document was actually enriched (has new metadata)
                    if "keywords" in enriched_doc.metadata or "entities" in enriched_doc.metadata:
                        enriched_count += 1

                    yield enriched_doc

                    # Log progress every 10 documents or at completion
                    if completed % 10 == 0 or completed == len(documents):
                        logger.info(
                            f"🔄 Enrichment progress: {completed}/{len(documents)} documents, "
                            f"{enriched_count} enriched"
                        )

                except Exception as e:
                    logger.error(f"Error processing enrichment task: {e}")
                    completed += 1

            logger.info(
                f"✅ Enrichment completed: {completed}/{len(documents)} documents processed, "
                f"{enriched_count} enriched"
            )

        except asyncio.CancelledError:
            logger.debug("EnrichmentWorker cancelled")
            raise
        finally:
            logger.debug("EnrichmentWorker exited")

    async def enrich_batch(self, documents: list[Document]) -> list[Document]:
        """Enrich a batch of documents and return them as a list.

        This is a convenience method that collects all enriched documents
        instead of yielding them one by one.

        Args:
            documents: List of documents to enrich

        Returns:
            List of enriched documents
        """
        enriched_docs = []
        async for doc in self.process_documents(documents):
            enriched_docs.append(doc)
        return enriched_docs

    async def shutdown(self):
        """Shutdown the enrichment worker."""
        logger.debug("Shutting down EnrichmentWorker")
        self.shutdown_event.set()

        # Shutdown the enricher pipeline
        await self.enricher_pipeline.shutdown()
