"""Document processing pipeline that coordinates chunking, embedding, and upserting."""

import asyncio
from typing import List

from qdrant_loader.core.document import Document
from qdrant_loader.utils.logging import LoggingConfig

from .workers import ChunkingWorker, EmbeddingWorker, UpsertWorker
from .workers.upsert_worker import PipelineResult

logger = LoggingConfig.get_logger(__name__)


class DocumentPipeline:
    """Handles the chunking -> embedding -> upsert pipeline."""

    def __init__(
        self,
        chunking_worker: ChunkingWorker,
        embedding_worker: EmbeddingWorker,
        upsert_worker: UpsertWorker,
    ):
        self.chunking_worker = chunking_worker
        self.embedding_worker = embedding_worker
        self.upsert_worker = upsert_worker

    async def process_documents(self, documents: List[Document]) -> PipelineResult:
        """Process documents through the pipeline.

        Args:
            documents: List of documents to process

        Returns:
            PipelineResult with processing statistics
        """
        logger.info(
            f"Starting document pipeline processing for {len(documents)} documents"
        )

        try:
            # Step 1: Chunk documents
            logger.debug("Starting chunking phase")
            chunks_iter = self.chunking_worker.process_documents(documents)

            # Step 2: Generate embeddings
            logger.debug("Starting embedding phase")
            embedded_chunks_iter = self.embedding_worker.process_chunks(chunks_iter)

            # Step 3: Upsert to Qdrant
            logger.debug("Starting upsert phase")
            result = await self.upsert_worker.process_embedded_chunks(
                embedded_chunks_iter
            )

            logger.info(
                f"Document pipeline completed. Success: {result.success_count}, "
                f"Errors: {result.error_count}, "
                f"Successfully processed documents: {len(result.successfully_processed_documents)}"
            )

            return result

        except Exception as e:
            logger.error(f"Document pipeline failed: {e}", exc_info=True)
            # Return a result with error information
            result = PipelineResult()
            result.error_count = len(documents)
            result.errors = [f"Pipeline failed: {e}"]
            return result
