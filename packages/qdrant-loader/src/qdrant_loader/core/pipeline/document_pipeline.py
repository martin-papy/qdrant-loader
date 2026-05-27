"""Document processing pipeline that coordinates chunking, embedding, and upserting."""

import asyncio
import time
from dataclasses import dataclass

from qdrant_loader.core.document import Document
from qdrant_loader.utils.logging import LoggingConfig

from .workers import ChunkingWorker, EmbeddingWorker, UpsertWorker
from .workers.upsert_worker import PipelineResult

logger = LoggingConfig.get_logger(__name__)


@dataclass
class BatchResult:
    """Result of processing a bounded batch of documents."""

    success_count: int = 0
    failure_count: int = 0
    skipped_count: int = 0
    successfully_processed_documents: set[str] | None = None
    failed_document_ids: set[str] | None = None
    errors: list[str] | None = None

    def __post_init__(self) -> None:
        if self.successfully_processed_documents is None:
            self.successfully_processed_documents = set()
        if self.failed_document_ids is None:
            self.failed_document_ids = set()
        if self.errors is None:
            self.errors = []


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

    async def process_batch(self, batch: list[Document]) -> BatchResult:
        """Process a bounded batch of documents through the pipeline.

        Args:
            batch: List of documents to process (bounded size, typically 256)

        Returns:
            BatchResult with processing statistics.
        """
        logger.info(f"⚙️ Processing batch of {len(batch)} documents through pipeline")
        start_time = time.time()

        try:
            logger.debug("🔄 Starting chunking phase for batch...")
            chunking_start = time.time()
            chunks_iter = self.chunking_worker.process_documents(batch)

            logger.debug("🔄 Chunking completed, transitioning to embedding phase...")
            chunking_duration = time.time() - chunking_start
            logger.debug(f"⏱️ Chunking phase took {chunking_duration:.2f} seconds")

            embedding_start = time.time()
            embedded_chunks_iter = self.embedding_worker.process_chunks(chunks_iter)

            logger.debug("🔄 Embedding phase ready, starting upsert phase...")

            try:
                pipeline_result = await asyncio.wait_for(
                    self.upsert_worker.process_embedded_chunks(embedded_chunks_iter),
                    timeout=600.0,  # 10 minute timeout per batch
                )
            except TimeoutError:
                logger.error("❌ Batch processing timed out after 10 minutes")
                return BatchResult(
                    failure_count=len(batch),
                    errors=["Batch processing timed out after 10 minutes"],
                )

            total_duration = time.time() - start_time
            embedding_duration = time.time() - embedding_start

            logger.debug(
                f"⏱️ Embedding + Upsert phase took {embedding_duration:.2f} seconds"
            )
            logger.info(
                f"✅ Batch processing completed: {pipeline_result.success_count} chunks, "
                f"{pipeline_result.error_count} errors in {total_duration:.2f}s"
            )

            return BatchResult(
                success_count=pipeline_result.success_count,
                failure_count=pipeline_result.error_count,
                skipped_count=0,
                successfully_processed_documents=pipeline_result.successfully_processed_documents,
                failed_document_ids=pipeline_result.failed_document_ids,
                errors=pipeline_result.errors,
            )

        except Exception as e:
            total_duration = time.time() - start_time
            logger.error(
                f"❌ Batch processing failed after {total_duration:.2f} seconds: {e}",
                exc_info=True,
            )
            return BatchResult(
                failure_count=len(batch),
                errors=[f"Batch processing failed: {e}"],
            )

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
            logger.info("🔄 Starting chunking phase...")
            chunking_start = time.time()
            chunks_iter = self.chunking_worker.process_documents(documents)

            logger.info("🔄 Chunking completed, transitioning to embedding phase...")
            chunking_duration = time.time() - chunking_start
            logger.info(f"⏱️ Chunking phase took {chunking_duration:.2f} seconds")

            embedding_start = time.time()
            embedded_chunks_iter = self.embedding_worker.process_chunks(chunks_iter)

            logger.info("🔄 Embedding phase ready, starting upsert phase...")

            try:
                result = await asyncio.wait_for(
                    self.upsert_worker.process_embedded_chunks(embedded_chunks_iter),
                    timeout=3600.0,  # 1 hour timeout for the entire pipeline
                )
            except TimeoutError:
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
            result = PipelineResult()
            result.error_count = len(documents)
            result.errors = [f"Pipeline failed: {e}"]
            return result