"""Embedding worker for processing chunks into embeddings."""

import asyncio
import gc
from collections.abc import AsyncIterator
from typing import Any

import psutil

from qdrant_loader.core.embedding.embedding_service import EmbeddingService
from qdrant_loader.core.monitoring import prometheus_metrics
from qdrant_loader.utils.logging import LoggingConfig

from .base_worker import BaseWorker

logger = LoggingConfig.get_logger(__name__)


class EmbeddingWorker(BaseWorker):
    """Handles chunk embedding with batching."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        max_workers: int = 4,
        queue_size: int = 1000,
        shutdown_event: asyncio.Event | None = None,
    ):
        super().__init__(max_workers, queue_size)
        self.embedding_service = embedding_service
        self.shutdown_event = shutdown_event or asyncio.Event()

    async def process(
        self, chunks: list[Any]
    ) -> list[tuple[Any, list[float] | None]]:
        """Process a batch of chunks into embeddings.

        The result is aligned 1:1 with ``chunks``: a chunk whose embedding
        came back empty (invalid content was skipped by ``get_embeddings``)
        is still included, paired with ``None``, so callers can account for
        every chunk's fate instead of the failure silently disappearing.

        Args:
            chunks: List of chunks to embed

        Returns:
            List of (chunk, embedding) tuples; embedding is None on failure.
        """
        if not chunks:
            return []

        try:
            logger.debug(f"EmbeddingWorker processing batch of {len(chunks)} items")

            # Monitor memory usage
            memory_percent = psutil.virtual_memory().percent
            if memory_percent > 85:
                logger.warning(
                    f"High memory usage detected: {memory_percent}%. Running garbage collection..."
                )
                gc.collect()

            with prometheus_metrics.EMBEDDING_DURATION.time():
                # Add timeout to prevent hanging and check for shutdown
                embeddings = await asyncio.wait_for(
                    self.embedding_service.get_embeddings([c.content for c in chunks]),
                    timeout=300.0,  # Increased to 5 minute timeout for large batches
                )

                # Check for shutdown before returning
                if self.shutdown_event.is_set():
                    logger.debug("EmbeddingWorker skipping result due to shutdown")
                    return []

                result: list[tuple[Any, list[float] | None]] = [
                    (chunk, emb if emb else None)
                    for chunk, emb in zip(chunks, embeddings, strict=False)
                ]
                skipped = sum(1 for _, emb in result if emb is None)
                if skipped:
                    logger.warning(
                        f"Skipped {skipped} chunk(s) with empty embeddings, they will not be upserted"
                    )
                logger.debug(f"EmbeddingWorker completed batch of {len(chunks)} items")

                # Cleanup after large batches
                if len(chunks) > 50:
                    gc.collect()

                return result

        except TimeoutError:
            logger.error(
                f"EmbeddingWorker timed out processing batch of {len(chunks)} items"
            )
            raise
        except Exception as e:
            logger.error(f"EmbeddingWorker error processing batch: {e}")
            raise

    async def _process_batch_guarded(
        self, batch: list[Any], batch_index: int
    ) -> list[tuple[Any, list[float] | None]]:
        """Run process() for a batch under the shared concurrency semaphore.

        Bounds how many embedding batches run concurrently to ``max_workers``
        so that ``max_embed_workers`` actually governs concurrency, instead of
        every batch running to completion before the next one starts.

        If the whole batch raises (timeout, service error), every chunk in it
        is still returned, paired with ``None``, instead of being dropped —
        otherwise those chunks vanish from accounting entirely and their
        parent documents can end up looking untouched rather than failed.
        """
        async with self.semaphore:
            try:
                logger.debug(
                    f"🔄 Processing embedding batch {batch_index} "
                    f"with {len(batch)} chunks..."
                )
                return await self.process(batch)
            except Exception as e:
                logger.error(f"EmbeddingWorker batch processing failed: {e}")
                for chunk in batch:
                    logger.error(f"Embedding failed for chunk {chunk.id}: {e}")
                return [(chunk, None) for chunk in batch]

    async def process_chunks(
        self, chunks: AsyncIterator[Any]
    ) -> AsyncIterator[tuple[Any, list[float] | None]]:
        """Process chunks into embeddings.

        Batches are dispatched concurrently, but the number of batches
        dispatched-and-not-yet-yielded is capped at ``max_workers``: once that
        many are in flight, the oldest is awaited before a new one is created.
        This bounds memory use (not just execution concurrency) when chunks
        arrive far faster than embedding calls complete, while still yielding
        results in submission order. Every dispatched chunk is yielded exactly
        once, paired with ``None`` if it failed to embed, so downstream stages
        can account for it instead of it silently vanishing.

        Args:
            chunks: AsyncIterator of chunks to process

        Yields:
            (chunk, embedding) tuples; embedding is None on failure.
        """
        logger.debug("EmbeddingWorker started")
        logger.info(
            f"🔄 Starting embedding generation (max_workers={self.max_workers})..."
        )
        batch_size = self.embedding_service.batch_size
        batch: list[Any] = []
        pending: list[asyncio.Task] = []
        batch_index = 0
        total_processed = 0
        total_failed = 0

        async def drain_oldest() -> list[tuple[Any, list[float] | None]]:
            nonlocal total_processed, total_failed
            results = await pending.pop(0)
            if not results:
                return []

            succeeded = sum(1 for _, embedding in results if embedding is not None)
            failed = len(results) - succeeded
            total_processed += succeeded
            total_failed += failed
            logger.info(
                f"🔗 Generated embeddings: {succeeded} items in batch"
                + (f" ({failed} failed)" if failed else "")
                + f", {total_processed} total processed"
            )
            return results

        def dispatch(batch_to_dispatch: list[Any]) -> None:
            nonlocal batch_index
            batch_index += 1
            pending.append(
                asyncio.create_task(
                    self._process_batch_guarded(batch_to_dispatch, batch_index)
                )
            )

        try:
            async for chunk in chunks:
                if self.shutdown_event.is_set():
                    logger.debug("EmbeddingWorker exiting due to shutdown")
                    break

                batch.append(chunk)

                # Dispatch batch when it reaches the desired size
                if len(batch) >= batch_size:
                    batch_to_submit = batch
                    batch = []

                    # Keep at most max_workers batches in flight so memory
                    # use stays bounded, not just execution concurrency.
                    if len(pending) >= self.max_workers:
                        for result in await drain_oldest():
                            yield result

                    dispatch(batch_to_submit)

            # Dispatch any remaining chunks in the final batch
            if batch and not self.shutdown_event.is_set():
                dispatch(batch)

            while pending:
                for result in await drain_oldest():
                    yield result

            logger.info(
                f"✅ Embedding completed: {total_processed} chunks processed, "
                f"{total_failed} failed"
            )

        except asyncio.CancelledError:
            logger.debug("EmbeddingWorker cancelled")
            for task in pending:
                if not task.done():
                    task.cancel()
            raise
        finally:
            logger.debug("EmbeddingWorker exited")
