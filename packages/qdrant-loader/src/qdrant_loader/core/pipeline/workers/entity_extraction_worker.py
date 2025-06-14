"""Entity extraction worker for processing documents through entity extraction pipeline."""

import asyncio
import time
from collections.abc import AsyncIterator
from typing import List, Optional, Any

from qdrant_loader.core.document import Document
from qdrant_loader.core.entity_extractor import EntityExtractor, ExtractionResult
from qdrant_loader.core.monitoring import prometheus_metrics
from qdrant_loader.utils.logging import LoggingConfig

from .base_worker import BaseWorker

logger = LoggingConfig.get_logger(__name__)


class EntityExtractionWorker(BaseWorker):
    """Handles entity extraction from documents with controlled concurrency."""

    def __init__(
        self,
        entity_extractor: EntityExtractor,
        max_workers: int = 5,
        queue_size: int = 1000,
        shutdown_event: Optional[asyncio.Event] = None,
    ):
        """Initialize the entity extraction worker.

        Args:
            entity_extractor: EntityExtractor instance for processing documents
            max_workers: Maximum number of concurrent extraction workers
            queue_size: Queue size for worker coordination
            shutdown_event: Event to signal shutdown
        """
        super().__init__(max_workers, queue_size)
        self.entity_extractor = entity_extractor
        self.shutdown_event = shutdown_event or asyncio.Event()

    async def process(self, document: Document) -> ExtractionResult:
        """Process a single document for entity extraction.

        Args:
            document: The document to extract entities from

        Returns:
            ExtractionResult containing extracted entities and relationships
        """
        logger.debug(f"Entity extraction worker started for doc {document.id}")

        try:
            # Check for shutdown signal
            if self.shutdown_event.is_set():
                logger.debug(
                    f"Entity extraction worker {document.id} exiting due to shutdown"
                )
                return ExtractionResult(source_text=document.content)

            # Extract entities from document content
            start_time = time.time()

            # Use the document URL as source description for better context
            source_description = f"Document: {document.url or document.id}"

            # Extract entities using the EntityExtractor
            result = await self.entity_extractor.extract_entities(
                text=document.content,
                source_description=source_description,
                reference_time=document.created_at,
            )

            # Add document metadata to the result
            result.metadata.update(
                {
                    "document_id": document.id,
                    "document_url": document.url,
                    "document_type": document.type,
                    "processing_time": time.time() - start_time,
                }
            )

            logger.debug(
                f"Entity extraction completed for doc {document.id}: "
                f"{len(result.entities)} entities, {len(result.relationships)} relationships"
            )

            return result

        except asyncio.CancelledError:
            logger.debug(f"Entity extraction worker {document.id} cancelled")
            raise
        except Exception as e:
            logger.error(f"Entity extraction failed for doc {document.url}: {e}")
            # Return empty result with error information
            return ExtractionResult(
                source_text=document.content,
                errors=[f"Entity extraction failed: {e}"],
                metadata={"document_id": document.id, "error": str(e)},
            )

    async def process_documents(
        self, documents: List[Document]
    ) -> AsyncIterator[ExtractionResult]:
        """Process documents for entity extraction.

        Args:
            documents: List of documents to process

        Yields:
            ExtractionResult objects from processed documents
        """
        logger.debug("EntityExtractionWorker started")
        logger.info(
            f"🔄 Processing {len(documents)} documents for entity extraction..."
        )

        try:
            # Process documents with controlled concurrency
            semaphore = asyncio.Semaphore(self.max_workers)

            async def process_and_yield(doc, doc_index):
                """Process a single document and return its extraction result."""
                try:
                    async with semaphore:
                        if self.shutdown_event.is_set():
                            logger.debug(
                                f"EntityExtractionWorker exiting due to shutdown (doc {doc_index})"
                            )
                            return None

                        logger.debug(
                            f"🔄 Extracting entities from document {doc_index + 1}/{len(documents)}: {doc.id}"
                        )

                        result = await self.process(doc)

                        if result.entities or result.relationships:
                            logger.debug(
                                f"✓ Document {doc_index + 1}/{len(documents)} extracted "
                                f"{len(result.entities)} entities, {len(result.relationships)} relationships"
                            )
                        else:
                            logger.debug(
                                f"⚠️ Document {doc_index + 1}/{len(documents)} extracted no entities"
                            )

                        return result

                except Exception as e:
                    logger.error(
                        f"❌ Entity extraction failed for document {doc_index + 1}/{len(documents)} ({doc.id}): {e}"
                    )
                    return ExtractionResult(
                        source_text=doc.content,
                        errors=[f"Processing failed: {e}"],
                        metadata={"document_id": doc.id, "error": str(e)},
                    )

            # Create tasks for all documents
            tasks = [process_and_yield(doc, i) for i, doc in enumerate(documents)]

            # Process tasks as they complete and yield results immediately
            entity_count = 0
            relationship_count = 0
            completed_docs = 0

            for coro in asyncio.as_completed(tasks):
                if self.shutdown_event.is_set():
                    logger.debug("EntityExtractionWorker exiting due to shutdown")
                    break

                try:
                    result = await coro
                    completed_docs += 1

                    if result:
                        entity_count += len(result.entities)
                        relationship_count += len(result.relationships)

                        if not self.shutdown_event.is_set():
                            yield result
                        else:
                            logger.debug(
                                "EntityExtractionWorker exiting due to shutdown"
                            )
                            return

                    # Log progress every 10 documents or at completion
                    if completed_docs % 10 == 0 or completed_docs == len(documents):
                        logger.info(
                            f"🔄 Entity extraction progress: {completed_docs}/{len(documents)} documents, "
                            f"{entity_count} entities, {relationship_count} relationships extracted"
                        )

                except Exception as e:
                    logger.error(f"❌ Error processing entity extraction task: {e}")
                    completed_docs += 1

            logger.info(
                f"✅ Entity extraction completed: {completed_docs}/{len(documents)} documents processed, "
                f"{entity_count} total entities, {relationship_count} total relationships"
            )

        except asyncio.CancelledError:
            logger.debug("EntityExtractionWorker cancelled")
            raise
        finally:
            logger.debug("EntityExtractionWorker exited")

    async def process_chunks(
        self, chunks_iter: AsyncIterator
    ) -> AsyncIterator[ExtractionResult]:
        """Process chunks for entity extraction (alternative interface for pipeline compatibility).

        Args:
            chunks_iter: Async iterator of chunks to process

        Yields:
            ExtractionResult objects from processed chunks
        """
        logger.debug("EntityExtractionWorker processing chunks")

        # Collect chunks and group by document
        document_chunks = {}
        chunk_count = 0

        async for chunk in chunks_iter:
            chunk_count += 1

            # Get parent document from chunk metadata
            parent_doc = chunk.metadata.get("parent_document")
            if not parent_doc:
                logger.warning(
                    f"Chunk {chunk.id} has no parent document, skipping entity extraction"
                )
                continue

            doc_id = parent_doc.id
            if doc_id not in document_chunks:
                document_chunks[doc_id] = {"document": parent_doc, "chunks": []}
            document_chunks[doc_id]["chunks"].append(chunk)

        logger.info(
            f"🔄 Processing {len(document_chunks)} documents from {chunk_count} chunks for entity extraction"
        )

        # Process documents for entity extraction
        documents = [doc_data["document"] for doc_data in document_chunks.values()]

        async for result in self.process_documents(documents):
            yield result
