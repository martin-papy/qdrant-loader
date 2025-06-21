"""Document processing pipeline that coordinates chunking, embedding, and upserting."""

import asyncio
import time

from qdrant_loader.core.document import Document
from qdrant_loader.utils.logging import LoggingConfig

from .workers import (
    ChunkingWorker,
    EmbeddingWorker,
    EntityExtractionWorker,
    UpsertWorker,
)
from .workers.upsert_worker import PipelineResult

logger = LoggingConfig.get_logger(__name__)


class DocumentPipeline:
    """Handles the chunking -> embedding -> upsert pipeline with optional entity extraction."""

    def __init__(
        self,
        chunking_worker: ChunkingWorker,
        embedding_worker: EmbeddingWorker,
        upsert_worker: UpsertWorker,
        entity_extraction_worker: EntityExtractionWorker | None = None,
    ):
        self.chunking_worker = chunking_worker
        self.embedding_worker = embedding_worker
        self.upsert_worker = upsert_worker
        self.entity_extraction_worker = entity_extraction_worker

    async def process_documents(self, documents: list[Document]) -> PipelineResult:
        """Process documents through the pipeline.

        Args:
            documents: List of documents to process

        Returns:
            PipelineResult with processing statistics
        """
        logger.info(f"Processing {len(documents)} documents through pipeline")
        start_time = time.time()

        try:
            # Step 1: Chunk documents
            logger.info("Starting chunking phase...")
            chunking_start = time.time()
            chunks_iter = self.chunking_worker.process_documents(documents)

            # Step 2: Generate embeddings
            logger.info("Chunking completed, transitioning to embedding phase...")
            chunking_duration = time.time() - chunking_start
            logger.info(f"Chunking phase took {chunking_duration:.2f} seconds")

            embedding_start = time.time()
            embedded_chunks_iter = self.embedding_worker.process_chunks(chunks_iter)

            # Step 3: Entity extraction (parallel with embedding if enabled)
            if self.entity_extraction_worker:
                logger.info(
                    "Starting entity extraction phase (parallel with embedding)..."
                )
                entity_extraction_start = time.time()

                # Run entity extraction in parallel with embedding/upsert
                entity_extraction_task = asyncio.create_task(
                    self._process_entity_extraction(documents),
                    name="entity_extraction_task",
                )

            # Step 4: Upsert to Qdrant
            logger.info("Embedding phase ready, starting upsert phase...")

            # Add timeout for the entire pipeline to prevent indefinite hanging
            try:
                result = await asyncio.wait_for(
                    self.upsert_worker.process_embedded_chunks(embedded_chunks_iter),
                    timeout=3600.0,  # 1 hour timeout for the entire pipeline
                )
            except TimeoutError:
                logger.error("Pipeline timed out after 1 hour")
                result = PipelineResult()
                result.error_count = len(documents)
                result.errors = ["Pipeline timed out after 1 hour"]
                return result

            # Wait for entity extraction to complete if it was started
            if self.entity_extraction_worker:
                try:
                    await asyncio.wait_for(
                        entity_extraction_task, timeout=300.0
                    )  # 5 minute timeout for entity extraction
                    entity_extraction_duration = time.time() - entity_extraction_start
                    logger.info(
                        f"Entity extraction phase took {entity_extraction_duration:.2f} seconds"
                    )
                except TimeoutError:
                    logger.warning("Entity extraction timed out after 5 minutes")
                    entity_extraction_task.cancel()
                except Exception as e:
                    logger.error(f"Entity extraction failed: {e}")

            total_duration = time.time() - start_time
            embedding_duration = time.time() - embedding_start

            logger.info(
                f"Embedding + Upsert phase took {embedding_duration:.2f} seconds"
            )
            logger.info(f"Total pipeline duration: {total_duration:.2f} seconds")
            logger.info(
                f"Pipeline completed: {result.success_count} chunks processed, "
                f"{result.error_count} errors"
            )

            return result

        except Exception as e:
            total_duration = time.time() - start_time
            logger.error(
                f"Document pipeline failed after {total_duration:.2f} seconds: {e}",
                exc_info=True,
            )
            # Return a result with error information
            result = PipelineResult()
            result.error_count = len(documents)
            result.errors = [f"Pipeline failed: {e}"]
            return result

    async def _process_entity_extraction(self, documents: list[Document]) -> None:
        """Process entity extraction for documents.

        Args:
            documents: List of documents to extract entities from
        """
        if not self.entity_extraction_worker:
            return

        try:
            logger.debug("Starting entity extraction processing")
            entity_count = 0
            relationship_count = 0

            async for result in self.entity_extraction_worker.process_documents(
                documents
            ):
                entity_count += len(result.entities)
                relationship_count += len(result.relationships)

                # Log extraction results for debugging
                if result.entities or result.relationships:
                    logger.debug(
                        f"Extracted {len(result.entities)} entities and "
                        f"{len(result.relationships)} relationships from document"
                    )

            logger.info(
                f"Entity extraction completed: {entity_count} total entities, "
                f"{relationship_count} total relationships extracted"
            )

        except asyncio.CancelledError:
            logger.warning("Entity extraction was cancelled")
            # Don't re-raise CancelledError, let the main pipeline continue
        except Exception as e:
            logger.error(f"Entity extraction processing failed: {e}", exc_info=True)
            raise
