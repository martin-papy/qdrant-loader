"""Document processing pipeline that coordinates chunking, embedding, and upserting."""

import asyncio
import time
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

    async def process_documents(self, documents: list[Document]) -> PipelineResult:
        """Process documents through the pipeline.

        Args:
            documents: List of documents to process

        Returns:
            PipelineResult with processing statistics
        """
        logger.info(f"⚙️ Processing {len(documents)} documents through pipeline")
        start_time = time.time()

        try:
            # Step 1: Chunk documents
            logger.info("🔄 Starting chunking phase...")
            chunking_start = time.time()
            chunks_iter = self.chunking_worker.process_documents(documents)

            # Step 2: Generate embeddings
            logger.info("🔄 Chunking completed, transitioning to embedding phase...")
            chunking_duration = time.time() - chunking_start
            logger.info(f"⏱️ Chunking phase took {chunking_duration:.2f} seconds")

            embedding_start = time.time()
            embedded_chunks_iter = self.embedding_worker.process_chunks(chunks_iter)

            # Step 3: Upsert to Qdrant
            logger.info("🔄 Embedding phase ready, starting upsert phase...")

            # Add timeout for the entire pipeline to prevent indefinite hanging
            try:
                result = await asyncio.wait_for(
                    self.upsert_worker.process_embedded_chunks(embedded_chunks_iter),
                    timeout=3600.0,  # 1 hour timeout for the entire pipeline
                )
            except asyncio.TimeoutError:
                logger.error("❌ Pipeline timed out after 1 hour")
                result = PipelineResult()
                result.error_count = len(documents)
                result.errors = ["Pipeline timed out after 1 hour"]
                return result

            total_duration = time.time() - start_time
            embedding_duration = time.time() - embedding_start

            logger.info(
                f"⏱️ Embedding + Upsert phase took {embedding_duration:.2f} seconds"
            )
            logger.info(f"⏱️ Total pipeline duration: {total_duration:.2f} seconds")
            logger.info(
                f"✅ Pipeline completed: {result.success_count} chunks processed, "
                f"{result.error_count} errors"
            )

            return result

        except Exception as e:
            total_duration = time.time() - start_time
            logger.error(
                f"❌ Document pipeline failed after {total_duration:.2f} seconds: {e}",
                exc_info=True,
            )
            # Return a result with error information
            result = PipelineResult()
            result.error_count = len(documents)
            result.errors = [f"Pipeline failed: {e}"]
            return result
