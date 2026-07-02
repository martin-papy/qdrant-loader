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
        self.processed_document_count: int = 0
        self.failed_document_count: int = 0
        self.total_size_bytes: int = 0


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

    def _handle_duplicate_chunk_ids(
        self,
        batch: list[tuple[Any, list[float]]],
        batch_chunk_id_counts: Counter,
        duplicate_chunk_ids: set[str],
        same_batch_duplicates: set[str],
        cross_batch_duplicates: set[str],
        new_chunk_ids: set[str],
        result: PipelineResult,
        errors: list[str],
    ) -> None:
        """Log/record duplicate chunk IDs and their error-count impact.

        Whether a duplicate-affected document ends up in
        ``successfully_processed_documents`` or ``failed_document_ids`` is
        decided by the per-document completion tracking in
        ``process_embedded_chunks`` (via ``note_chunk_outcome``), not here.
        """
        if not duplicate_chunk_ids:
            return

        duplicate_doc_ids = set()
        for chunk, _ in batch:
            if str(chunk.id) in duplicate_chunk_ids:
                parent_doc = chunk.metadata.get("parent_document")
                if parent_doc:
                    duplicate_doc_ids.add(parent_doc.id)

        same_batch_duplicate_occurrences = sum(
            count - 1 for count in batch_chunk_id_counts.values() if count > 1
        )
        total_duplicate_impact = len(duplicate_doc_ids)
        duplicate_chunk_attempts = len(batch) - len(new_chunk_ids)

        logger.warning(
            "Detected chunk ID collisions during upsert; existing points will be overwritten",
            duplicate_count=len(duplicate_chunk_ids),
            same_batch_duplicate_count=len(same_batch_duplicates),
            same_batch_duplicate_occurrences=same_batch_duplicate_occurrences,
            cross_batch_duplicate_count=len(cross_batch_duplicates),
            affected_documents=total_duplicate_impact,
        )
        errors.append(
            "Detected duplicate chunk IDs during upsert: "
            f"{len(cross_batch_duplicates)} cross-batch IDs and "
            f"{same_batch_duplicate_occurrences} same-batch duplicate occurrences "
            f"across {len(same_batch_duplicates)} IDs affecting {total_duplicate_impact} document(s): "
            f"{sorted(duplicate_doc_ids)}"
        )
        result.error_count += duplicate_chunk_attempts

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
                # QdrantManager.build_point_vector owns the dense / dense+sparse
                # decision and has its own dense-only fallback on encode failure,
                # so no defensive wrapper is needed here.
                points = [
                    models.PointStruct(
                        id=chunk.id,
                        vector=self.qdrant_manager.build_point_vector(
                            embedding, chunk.content
                        ),
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
                    for chunk, embedding in batch
                ]

                await self.qdrant_manager.upsert_points(points)
                prometheus_metrics.INGESTED_DOCUMENTS.inc(len(points))
                success_count = len(points)

                # Mark parent documents as successfully processed
                for chunk, _ in batch:
                    parent_doc = chunk.metadata.get("parent_document")
                    if parent_doc:
                        successful_doc_ids.add(parent_doc.id)

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

    def _reserve_chunk_ids(
        self, batch: list[tuple[Any, list[float]]], seen_chunk_ids: set[str]
    ) -> dict[str, Any]:
        """Compute duplicate-chunk-id bookkeeping for a batch and reserve its new IDs.

        This runs synchronously (no ``await``) at batch-formation time, before
        the batch is handed off for concurrent upserting. That ordering is
        what keeps duplicate detection correct once batches are processed
        concurrently: reservations happen strictly in submission order, so two
        in-flight batches can never both believe the same chunk id is new.
        """
        batch_chunk_id_list = [str(chunk.id) for chunk, _ in batch]
        batch_chunk_ids = set(batch_chunk_id_list)
        batch_chunk_id_counts = Counter(batch_chunk_id_list)
        same_batch_duplicates = {
            chunk_id for chunk_id, count in batch_chunk_id_counts.items() if count > 1
        }
        cross_batch_duplicates = batch_chunk_ids & seen_chunk_ids
        duplicate_chunk_ids = cross_batch_duplicates | same_batch_duplicates
        new_chunk_ids = batch_chunk_ids - seen_chunk_ids - same_batch_duplicates

        # Reserve now so the next batch's cross-batch check sees it, regardless
        # of how long this batch's upsert takes to actually complete.
        seen_chunk_ids.update(new_chunk_ids)

        return {
            "batch_chunk_id_counts": batch_chunk_id_counts,
            "same_batch_duplicates": same_batch_duplicates,
            "cross_batch_duplicates": cross_batch_duplicates,
            "duplicate_chunk_ids": duplicate_chunk_ids,
            "new_chunk_ids": new_chunk_ids,
        }

    @staticmethod
    def _note_chunk_outcome(
        chunk: Any,
        failed: bool,
        result: PipelineResult,
        doc_totals: dict[str, int],
        doc_seen: dict[str, int],
        doc_failed: dict[str, bool],
    ) -> None:
        """Record one chunk's fate and finalize its document once complete.

        A document is only added to ``successfully_processed_documents`` once
        *every* chunk chunking produced for it has been accounted for (via
        ``parent_document_total_chunks``) with none failed — a document isn't
        "done" just because the first batch containing one of its chunks
        happened to succeed. If any chunk failed (embedding failure, upsert
        failure, or duplicate-id collision), the document lands in
        ``failed_document_ids`` instead so a later incremental run retries it.
        """
        parent_doc = chunk.metadata.get("parent_document")
        if not parent_doc:
            return

        doc_id = parent_doc.id
        total = chunk.metadata.get("parent_document_total_chunks") or 1
        doc_totals.setdefault(doc_id, total)

        seen = doc_seen.get(doc_id, 0) + 1
        doc_seen[doc_id] = seen
        if failed:
            doc_failed[doc_id] = True

        if seen >= doc_totals[doc_id]:
            if doc_failed.get(doc_id):
                result.failed_document_ids.add(doc_id)
                result.successfully_processed_documents.discard(doc_id)
            else:
                result.successfully_processed_documents.add(doc_id)

    def _merge_batch_outcome(
        self,
        batch: list[tuple[Any, list[float]]],
        dedup: dict[str, Any],
        outcome: tuple[int, int, set[str], list[str]],
        result: PipelineResult,
        seen_chunk_ids: set[str],
        doc_totals: dict[str, int],
        doc_seen: dict[str, int],
        doc_failed: dict[str, bool],
    ) -> None:
        """Fold one batch's process() outcome into the running PipelineResult."""
        success_count, error_count, successful_doc_ids, errors = outcome

        if success_count > 0:
            if dedup["duplicate_chunk_ids"]:
                self._handle_duplicate_chunk_ids(
                    batch=batch,
                    batch_chunk_id_counts=dedup["batch_chunk_id_counts"],
                    duplicate_chunk_ids=dedup["duplicate_chunk_ids"],
                    same_batch_duplicates=dedup["same_batch_duplicates"],
                    cross_batch_duplicates=dedup["cross_batch_duplicates"],
                    new_chunk_ids=dedup["new_chunk_ids"],
                    result=result,
                    errors=errors,
                )
            result.success_count += len(dedup["new_chunk_ids"])
        else:
            # Nothing was actually written; release the reservation so a
            # later batch with the same id isn't wrongly treated as a dup.
            seen_chunk_ids.difference_update(dedup["new_chunk_ids"])

        result.error_count += error_count
        result.errors.extend(errors)

        for chunk, _ in batch:
            chunk_failed = success_count == 0 or str(chunk.id) in dedup[
                "duplicate_chunk_ids"
            ]
            self._note_chunk_outcome(
                chunk, chunk_failed, result, doc_totals, doc_seen, doc_failed
            )

    async def process_embedded_chunks(
        self, embedded_chunks: AsyncIterator[tuple[Any, list[float] | None]]
    ) -> PipelineResult:
        """Upsert embedded chunks to Qdrant.

        The number of batches dispatched-and-not-yet-merged is capped at
        ``max_workers``: once that many are in flight, the oldest is awaited
        before a new one is created. This bounds memory use (not just upsert
        concurrency) when embeddings arrive far faster than Qdrant upserts
        complete, while still merging outcomes in submission order. A chunk
        arriving with ``embedding is None`` (embedding failed upstream) is
        never sent to Qdrant, but is still accounted for so its parent
        document doesn't get marked successful with pieces missing.

        Args:
            embedded_chunks: AsyncIterator of (chunk, embedding) tuples

        Returns:
            PipelineResult with processing statistics
        """
        logger.debug("UpsertWorker started")
        logger.info(f"🔄 Starting upsert processing (max_workers={self.max_workers})...")
        result = PipelineResult()
        seen_chunk_ids: set[str] = set()
        doc_totals: dict[str, int] = {}
        doc_seen: dict[str, int] = {}
        doc_failed: dict[str, bool] = {}
        batch: list[tuple[Any, list[float]]] = []
        pending: list[
            tuple[asyncio.Task, list[tuple[Any, list[float]]], dict[str, Any]]
        ] = []

        async def drain_oldest() -> None:
            task, task_batch, dedup = pending.pop(0)
            outcome = await task
            self._merge_batch_outcome(
                task_batch,
                dedup,
                outcome,
                result,
                seen_chunk_ids,
                doc_totals,
                doc_seen,
                doc_failed,
            )

        def dispatch(batch_to_dispatch: list[tuple[Any, list[float]]]) -> None:
            dedup = self._reserve_chunk_ids(batch_to_dispatch, seen_chunk_ids)
            task = asyncio.create_task(self.process_with_semaphore(batch_to_dispatch))
            pending.append((task, batch_to_dispatch, dedup))

        try:
            async for chunk, embedding in embedded_chunks:
                if self.shutdown_event.is_set():
                    logger.debug("UpsertWorker exiting due to shutdown")
                    break

                if embedding is None:
                    result.error_count += 1
                    result.errors.append(
                        f"Embedding failed for chunk {chunk.id}, skipped upsert"
                    )
                    self._note_chunk_outcome(
                        chunk, True, result, doc_totals, doc_seen, doc_failed
                    )
                    continue

                batch.append((chunk, embedding))

                # Dispatch batch when it reaches the desired size
                if len(batch) >= self.batch_size:
                    batch_to_submit = batch
                    batch = []

                    # Keep at most max_workers batches in flight so memory
                    # use stays bounded, not just upsert concurrency.
                    if len(pending) >= self.max_workers:
                        await drain_oldest()

                    dispatch(batch_to_submit)

            # Dispatch any remaining chunks in the final batch
            if batch and not self.shutdown_event.is_set():
                dispatch(batch)

            while pending:
                await drain_oldest()

        except asyncio.CancelledError:
            logger.debug("UpsertWorker cancelled")
            for task, _, _ in pending:
                if not task.done():
                    task.cancel()
            raise
        finally:
            logger.debug("UpsertWorker exited")

        return result
