"""Upsert worker for upserting embedded chunks to Qdrant."""

import asyncio
from collections import Counter
from collections.abc import AsyncIterator
from typing import Any

from qdrant_client.http import models

from qdrant_loader.core.monitoring import prometheus_metrics
from qdrant_loader.core.qdrant_manager import QdrantManager
from qdrant_loader.utils.logging import LoggingConfig

from .base_worker import BaseWorker

logger = LoggingConfig.get_logger(__name__)


class PipelineResult:
    """Result of pipeline processing."""

    def __init__(self):
        self.success_count: int = 0
        self.error_count: int = 0
        self.successfully_processed_documents: set[str] = set()
        self.failed_document_ids: set[str] = set()
        self.errors: list[str] = []


class UpsertWorker(BaseWorker):
    """Handles upserting embedded chunks to Qdrant."""

    def __init__(
        self,
        qdrant_manager: QdrantManager,
        batch_size: int,
        max_workers: int = 4,
        queue_size: int = 1000,
        shutdown_event: asyncio.Event | None = None,
    ):
        super().__init__(max_workers, queue_size)
        self.qdrant_manager = qdrant_manager
        self.batch_size = batch_size
        self.shutdown_event = shutdown_event or asyncio.Event()

    async def process(
        self, batch: list[tuple[Any, list[float]]]
    ) -> tuple[int, int, set[str], list[str]]:
        """Process a batch of embedded chunks.

        Args:
            batch: List of (chunk, embedding) tuples

        Returns:
            Tuple of (success_count, error_count, successful_doc_ids, errors)
        """
        if not batch:
            return 0, 0, set(), []

        success_count = 0
        error_count = 0
        successful_doc_ids = set()
        errors = []

        try:
            with prometheus_metrics.UPSERT_DURATION.time():
                # Separate deleted and non-deleted chunks
                deleted_chunks = []
                non_deleted_chunks = []

                for chunk, embedding in batch:
                    if chunk.metadata.get("is_deleted", False):
                        deleted_chunks.append(chunk)
                    else:
                        non_deleted_chunks.append((chunk, embedding))

                # Handle non-deleted chunks (upsert)
                if non_deleted_chunks:
                    points = [
                        models.PointStruct(
                            id=chunk.id,
                            vector=embedding,
                            payload={
                                "content": chunk.content,
                                "contextual_content": chunk.contextual_content,
                            "metadata": {
                                    k: v
                                    for k, v in chunk.metadata.items()
                                    if k != "parent_document"
                                },
                                "source": chunk.source,
                                "source_type": chunk.source_type,
                                "created_at": chunk.created_at.isoformat(),
                                "updated_at": (
                                    getattr(
                                        chunk, "updated_at", chunk.created_at
                                    ).isoformat()
                                    if hasattr(chunk, "updated_at")
                                    else chunk.created_at.isoformat()
                                ),
                                "title": getattr(
                                    chunk, "title", chunk.metadata.get("title", "")
                                ),
                                "url": getattr(chunk, "url", chunk.metadata.get("url", "")),
                                "document_id": chunk.metadata.get(
                                    "parent_document_id", chunk.id
                                ),
                            },
                        )
                        for chunk, embedding in non_deleted_chunks
                    ]

                    await self.qdrant_manager.upsert_points(points)
                    success_count += len(points)
                    successful_doc_ids.update(
                        chunk.metadata["parent_document"].id for chunk, _ in non_deleted_chunks
                    )

                # Handle deleted chunks (delete)
                if deleted_chunks:
                    document_ids = list(set(chunk.metadata["parent_document"].id for chunk in deleted_chunks))
                    await self.qdrant_manager.delete_points_by_document_id(document_ids)
                    success_count += len(deleted_chunks)
                    successful_doc_ids.update(
                        chunk.metadata["parent_document"].id for chunk in deleted_chunks
                    )

                prometheus_metrics.INGESTED_DOCUMENTS.inc(success_count)

        except Exception as e:
            for chunk, _ in batch:
                logger.error(f"Upsert failed for chunk {chunk.id}: {e}")
                # Mark parent document as failed
                parent_doc = chunk.metadata.get("parent_document")
                if parent_doc:
                    successful_doc_ids.discard(parent_doc.id)  # Remove if it was added
                errors.append(f"Upsert failed for chunk {chunk.id}: {e}")
            error_count = len(batch)

        return success_count, error_count, successful_doc_ids, errors

    async def process_embedded_chunks(
        self, embedded_chunks: AsyncIterator[tuple[Any, list[float]]]
    ) -> PipelineResult:
        """Upsert embedded chunks to Qdrant.

        Args:
            embedded_chunks: AsyncIterator of (chunk, embedding) tuples

        Returns:
            PipelineResult with processing statistics
        """
        logger.debug("UpsertWorker started")
        result = PipelineResult()
        batch = []
        seen_chunk_ids: set[str] = set()

        try:
            async for chunk_embedding in embedded_chunks:
                if self.shutdown_event.is_set():
                    logger.debug("UpsertWorker exiting due to shutdown")
                    break

                batch.append(chunk_embedding)

                # Process batch when it reaches the desired size
                if len(batch) >= self.batch_size:
                    batch_chunk_id_list = [str(chunk.id) for chunk, _ in batch]
                    batch_chunk_ids = set(batch_chunk_id_list)
                    batch_chunk_id_counts = Counter(batch_chunk_id_list)
                    success_count, error_count, successful_doc_ids, errors = (
                        await self.process(batch)
                    )

                    if success_count > 0:
                        same_batch_duplicates = {
                            chunk_id
                            for chunk_id, count in batch_chunk_id_counts.items()
                            if count > 1
                        }
                        cross_batch_duplicates = batch_chunk_ids & seen_chunk_ids
                        duplicate_chunk_ids = (
                            cross_batch_duplicates | same_batch_duplicates
                        )
                        new_chunk_ids = batch_chunk_ids - seen_chunk_ids

                        if duplicate_chunk_ids:
                            same_batch_duplicate_occurrences = sum(
                                count - 1
                                for count in batch_chunk_id_counts.values()
                                if count > 1
                            )
                            logger.warning(
                                "Detected chunk ID collisions during upsert; existing points will be overwritten",
                                duplicate_count=len(duplicate_chunk_ids),
                                same_batch_duplicate_count=len(same_batch_duplicates),
                                same_batch_duplicate_occurrences=same_batch_duplicate_occurrences,
                                cross_batch_duplicate_count=len(cross_batch_duplicates),
                            )
                            errors.append(
                                "Detected duplicate chunk IDs during upsert: "
                                f"{len(cross_batch_duplicates)} cross-batch IDs and "
                                f"{same_batch_duplicate_occurrences} same-batch duplicate occurrences "
                                f"across {len(same_batch_duplicates)} IDs"
                            )

                        seen_chunk_ids.update(batch_chunk_ids)
                        result.success_count += len(new_chunk_ids)

                    result.error_count += error_count
                    result.successfully_processed_documents.update(successful_doc_ids)
                    result.errors.extend(errors)
                    batch = []

            # Process any remaining chunks in the final batch
            if batch and not self.shutdown_event.is_set():
                batch_chunk_id_list = [str(chunk.id) for chunk, _ in batch]
                batch_chunk_ids = set(batch_chunk_id_list)
                batch_chunk_id_counts = Counter(batch_chunk_id_list)
                success_count, error_count, successful_doc_ids, errors = (
                    await self.process(batch)
                )

                if success_count > 0:
                    same_batch_duplicates = {
                        chunk_id
                        for chunk_id, count in batch_chunk_id_counts.items()
                        if count > 1
                    }
                    cross_batch_duplicates = batch_chunk_ids & seen_chunk_ids
                    duplicate_chunk_ids = cross_batch_duplicates | same_batch_duplicates
                    new_chunk_ids = batch_chunk_ids - seen_chunk_ids

                    if duplicate_chunk_ids:
                        same_batch_duplicate_occurrences = sum(
                            count - 1
                            for count in batch_chunk_id_counts.values()
                            if count > 1
                        )
                        logger.warning(
                            "Detected chunk ID collisions during upsert; existing points will be overwritten",
                            duplicate_count=len(duplicate_chunk_ids),
                            same_batch_duplicate_count=len(same_batch_duplicates),
                            same_batch_duplicate_occurrences=same_batch_duplicate_occurrences,
                            cross_batch_duplicate_count=len(cross_batch_duplicates),
                        )
                        errors.append(
                            "Detected duplicate chunk IDs during upsert: "
                            f"{len(cross_batch_duplicates)} cross-batch IDs and "
                            f"{same_batch_duplicate_occurrences} same-batch duplicate occurrences "
                            f"across {len(same_batch_duplicates)} IDs"
                        )

                    seen_chunk_ids.update(batch_chunk_ids)
                    result.success_count += len(new_chunk_ids)

                result.error_count += error_count
                result.successfully_processed_documents.update(successful_doc_ids)
                result.errors.extend(errors)

        except asyncio.CancelledError:
            logger.debug("UpsertWorker cancelled")
            raise
        finally:
            logger.debug("UpsertWorker exited")

        return result
