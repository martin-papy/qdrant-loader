"""Tests for EmbeddingWorker."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from qdrant_loader.core.pipeline.workers.embedding_worker import EmbeddingWorker


class TestEmbeddingWorker:
    """Test cases for EmbeddingWorker."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_embedding_service = Mock()
        self.mock_embedding_service.batch_size = 10
        self.mock_shutdown_event = Mock(spec=asyncio.Event)
        self.mock_shutdown_event.is_set.return_value = False

        self.embedding_worker = EmbeddingWorker(
            embedding_service=self.mock_embedding_service,
            max_workers=4,
            queue_size=1000,
            shutdown_event=self.mock_shutdown_event,
        )

    def test_embedding_worker_initialization(self):
        """Test EmbeddingWorker initialization."""
        assert self.embedding_worker.embedding_service == self.mock_embedding_service
        assert self.embedding_worker.max_workers == 4
        assert self.embedding_worker.queue_size == 1000
        assert self.embedding_worker.shutdown_event == self.mock_shutdown_event

    def test_embedding_worker_initialization_default_shutdown_event(self):
        """Test EmbeddingWorker initialization with default shutdown event."""
        worker = EmbeddingWorker(
            embedding_service=self.mock_embedding_service,
            max_workers=2,
            queue_size=500,
        )

        assert worker.embedding_service == self.mock_embedding_service
        assert worker.max_workers == 2
        assert worker.queue_size == 500
        assert worker.shutdown_event is not None
        assert isinstance(worker.shutdown_event, asyncio.Event)

    @pytest.mark.asyncio
    async def test_process_empty_chunks(self):
        """Test processing empty chunks list."""
        result = await self.embedding_worker.process([])
        assert result == []

    @pytest.mark.asyncio
    async def test_process_success(self):
        """Test successful chunk processing."""
        # Setup mock chunks
        mock_chunk1 = Mock()
        mock_chunk1.content = "Test content 1"
        mock_chunk1.id = "chunk1"

        mock_chunk2 = Mock()
        mock_chunk2.content = "Test content 2"
        mock_chunk2.id = "chunk2"

        chunks = [mock_chunk1, mock_chunk2]

        # Setup mock embeddings
        mock_embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        self.mock_embedding_service.get_embeddings = AsyncMock(
            return_value=mock_embeddings
        )

        with patch(
            "qdrant_loader.core.pipeline.workers.embedding_worker.prometheus_metrics"
        ):
            result = await self.embedding_worker.process(chunks)

        # Verify result
        assert len(result) == 2
        assert result[0] == (mock_chunk1, [0.1, 0.2, 0.3])
        assert result[1] == (mock_chunk2, [0.4, 0.5, 0.6])

        # Verify embedding service was called correctly
        self.mock_embedding_service.get_embeddings.assert_called_once_with(
            ["Test content 1", "Test content 2"]
        )

    @pytest.mark.asyncio
    async def test_process_partial_empty_embeddings(self):
        """A chunk with an empty embedding is kept in the result, paired with None."""
        mock_chunk1 = Mock()
        mock_chunk1.content = "Test content 1"
        mock_chunk1.id = "chunk1"

        mock_chunk2 = Mock()
        mock_chunk2.content = "Test content 2"
        mock_chunk2.id = "chunk2"

        chunks = [mock_chunk1, mock_chunk2]

        # Second chunk's content was invalid, so get_embeddings returns []
        # for it instead of raising.
        self.mock_embedding_service.get_embeddings = AsyncMock(
            return_value=[[0.1, 0.2, 0.3], []]
        )

        with patch(
            "qdrant_loader.core.pipeline.workers.embedding_worker.prometheus_metrics"
        ):
            result = await self.embedding_worker.process(chunks)

        # Both chunks are present, not just the successful one, so callers
        # can tell the second one failed instead of it silently disappearing.
        assert len(result) == 2
        assert result[0] == (mock_chunk1, [0.1, 0.2, 0.3])
        assert result[1] == (mock_chunk2, None)

    @pytest.mark.asyncio
    async def test_process_with_shutdown_during_processing(self):
        """Test processing with shutdown event set during processing."""
        mock_chunk = Mock()
        mock_chunk.content = "Test content"
        mock_chunk.id = "chunk1"
        chunks = [mock_chunk]

        # Setup embedding service to return embeddings
        mock_embeddings = [[0.1, 0.2, 0.3]]
        self.mock_embedding_service.get_embeddings = AsyncMock(
            return_value=mock_embeddings
        )

        # Set shutdown event after embedding service call
        async def set_shutdown_after_call(*args, **kwargs):
            self.mock_shutdown_event.is_set.return_value = True
            return mock_embeddings

        self.mock_embedding_service.get_embeddings.side_effect = set_shutdown_after_call

        with patch(
            "qdrant_loader.core.pipeline.workers.embedding_worker.prometheus_metrics"
        ):
            result = await self.embedding_worker.process(chunks)

        # Should return empty list due to shutdown
        assert result == []

    @pytest.mark.asyncio
    async def test_process_timeout_error(self):
        """Test processing with timeout error."""
        mock_chunk = Mock()
        mock_chunk.content = "Test content"
        mock_chunk.id = "chunk1"
        chunks = [mock_chunk]

        # Setup embedding service to timeout
        self.mock_embedding_service.get_embeddings = AsyncMock(
            side_effect=TimeoutError()
        )

        with patch(
            "qdrant_loader.core.pipeline.workers.embedding_worker.prometheus_metrics"
        ):
            with pytest.raises(asyncio.TimeoutError):
                await self.embedding_worker.process(chunks)

    @pytest.mark.asyncio
    async def test_process_general_exception(self):
        """Test processing with general exception."""
        mock_chunk = Mock()
        mock_chunk.content = "Test content"
        mock_chunk.id = "chunk1"
        chunks = [mock_chunk]

        # Setup embedding service to raise exception
        self.mock_embedding_service.get_embeddings = AsyncMock(
            side_effect=Exception("Embedding service error")
        )

        with patch(
            "qdrant_loader.core.pipeline.workers.embedding_worker.prometheus_metrics"
        ):
            with pytest.raises(Exception, match="Embedding service error"):
                await self.embedding_worker.process(chunks)

    @pytest.mark.asyncio
    async def test_process_chunks_success(self):
        """Test successful chunk processing through async iterator."""
        # Setup mock chunks
        mock_chunk1 = Mock()
        mock_chunk1.content = "Test content 1"
        mock_chunk1.id = "chunk1"

        mock_chunk2 = Mock()
        mock_chunk2.content = "Test content 2"
        mock_chunk2.id = "chunk2"

        # Create async iterator
        async def chunk_iterator():
            yield mock_chunk1
            yield mock_chunk2

        # Setup mock embeddings
        mock_embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        self.mock_embedding_service.get_embeddings = AsyncMock(
            return_value=mock_embeddings
        )

        # Set batch size to 2 to process both chunks in one batch
        self.mock_embedding_service.batch_size = 2

        with patch(
            "qdrant_loader.core.pipeline.workers.embedding_worker.prometheus_metrics"
        ):
            results = []
            async for result in self.embedding_worker.process_chunks(chunk_iterator()):
                results.append(result)

        # Verify results
        assert len(results) == 2
        assert results[0] == (mock_chunk1, [0.1, 0.2, 0.3])
        assert results[1] == (mock_chunk2, [0.4, 0.5, 0.6])

    @pytest.mark.asyncio
    async def test_process_chunks_with_batching(self):
        """Test chunk processing with multiple batches."""
        # Setup mock chunks
        chunks = []
        for i in range(5):
            mock_chunk = Mock()
            mock_chunk.content = f"Test content {i}"
            mock_chunk.id = f"chunk{i}"
            chunks.append(mock_chunk)

        # Create async iterator
        async def chunk_iterator():
            for chunk in chunks:
                yield chunk

        # Setup mock embeddings for different batch sizes
        def get_embeddings_side_effect(contents):
            return [[0.1 * i, 0.2 * i, 0.3 * i] for i in range(len(contents))]

        self.mock_embedding_service.get_embeddings = AsyncMock(
            side_effect=get_embeddings_side_effect
        )

        # Set batch size to 2 to force multiple batches
        self.mock_embedding_service.batch_size = 2

        with patch(
            "qdrant_loader.core.pipeline.workers.embedding_worker.prometheus_metrics"
        ):
            results = []
            async for result in self.embedding_worker.process_chunks(chunk_iterator()):
                results.append(result)

        # Verify results - should have 5 results from 3 batches (2+2+1)
        assert len(results) == 5

        # Verify embedding service was called 3 times (for 3 batches)
        assert self.mock_embedding_service.get_embeddings.call_count == 3

    @pytest.mark.asyncio
    async def test_process_chunks_with_shutdown_during_iteration(self):
        """Shutdown mid-stream: a batch still in flight when shutdown lands is
        dropped (its document stays unfinished and is retried on the next run),
        and chunks arriving after shutdown are never dispatched.

        Under the concurrent dispatch model the first chunk's batch is created
        before shutdown but *executes* after the flag is set, so process()'s
        shutdown check discards its result. The completed-before-shutdown case
        (results still yielded) is covered by
        test_process_chunks_shutdown_drains_dispatched_batches.
        """
        # Setup mock chunks
        mock_chunk1 = Mock()
        mock_chunk1.content = "Test content 1"
        mock_chunk1.id = "chunk1"

        mock_chunk2 = Mock()
        mock_chunk2.content = "Test content 2"
        mock_chunk2.id = "chunk2"

        # Create async iterator that sets shutdown after first chunk
        async def chunk_iterator():
            yield mock_chunk1
            self.mock_shutdown_event.is_set.return_value = True
            yield mock_chunk2

        # Setup mock embeddings
        mock_embeddings = [[0.1, 0.2, 0.3]]
        self.mock_embedding_service.get_embeddings = AsyncMock(
            return_value=mock_embeddings
        )

        # Set batch size to 1 to process chunks individually
        self.mock_embedding_service.batch_size = 1

        with patch(
            "qdrant_loader.core.pipeline.workers.embedding_worker.prometheus_metrics"
        ):
            results = []
            async for result in self.embedding_worker.process_chunks(chunk_iterator()):
                results.append(result)

        # The in-flight batch was discarded at the shutdown check: nothing is
        # yielded, so the parent document is left unfinished for a later retry.
        assert results == []
        # chunk1 was dispatched (and embedded) before the drop; chunk2 never was.
        self.mock_embedding_service.get_embeddings.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_chunks_with_batch_processing_exception(self):
        """Test chunk processing with exception during batch processing."""
        # Setup mock chunks
        mock_chunk1 = Mock()
        mock_chunk1.content = "Test content 1"
        mock_chunk1.id = "chunk1"

        mock_chunk2 = Mock()
        mock_chunk2.content = "Test content 2"
        mock_chunk2.id = "chunk2"

        # Create async iterator
        async def chunk_iterator():
            yield mock_chunk1
            yield mock_chunk2

        # Setup embedding service to raise exception
        self.mock_embedding_service.get_embeddings = AsyncMock(
            side_effect=Exception("Batch processing error")
        )

        # Set batch size to 1 to process chunks individually
        self.mock_embedding_service.batch_size = 1

        with patch(
            "qdrant_loader.core.pipeline.workers.embedding_worker.prometheus_metrics"
        ):
            with patch(
                "qdrant_loader.core.pipeline.workers.embedding_worker.logger"
            ) as mock_logger:
                results = []
                async for result in self.embedding_worker.process_chunks(
                    chunk_iterator()
                ):
                    results.append(result)

                # Failed chunks are still surfaced (paired with None) so
                # their parent documents can be accounted for downstream,
                # instead of silently vanishing.
                assert len(results) == 2
                assert results == [(mock_chunk1, None), (mock_chunk2, None)]

                # Verify error logging
                assert mock_logger.error.call_count >= 2  # One for each chunk

    @pytest.mark.asyncio
    async def test_process_chunks_with_final_batch_exception(self):
        """Test chunk processing with exception in final batch."""
        # Setup mock chunks
        mock_chunk1 = Mock()
        mock_chunk1.content = "Test content 1"
        mock_chunk1.id = "chunk1"

        mock_chunk2 = Mock()
        mock_chunk2.content = "Test content 2"
        mock_chunk2.id = "chunk2"

        # Create async iterator
        async def chunk_iterator():
            yield mock_chunk1
            yield mock_chunk2

        # Setup embedding service to work for first call, fail for second
        call_count = 0

        def get_embeddings_side_effect(contents):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [[0.1, 0.2, 0.3]]
            else:
                raise Exception("Final batch error")

        self.mock_embedding_service.get_embeddings = AsyncMock(
            side_effect=get_embeddings_side_effect
        )

        # Set batch size to 1 to process chunks individually
        self.mock_embedding_service.batch_size = 1

        with patch(
            "qdrant_loader.core.pipeline.workers.embedding_worker.prometheus_metrics"
        ):
            with patch(
                "qdrant_loader.core.pipeline.workers.embedding_worker.logger"
            ) as mock_logger:
                results = []
                async for result in self.embedding_worker.process_chunks(
                    chunk_iterator()
                ):
                    results.append(result)

                # First chunk succeeds; second is still surfaced, paired
                # with None, instead of disappearing from accounting.
                assert len(results) == 2
                assert results[0] == (mock_chunk1, [0.1, 0.2, 0.3])
                assert results[1] == (mock_chunk2, None)

                # Verify error logging for second chunk
                mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_process_chunks_cancelled_error(self):
        """Test chunk processing with cancellation."""
        # Setup mock chunks
        mock_chunk = Mock()
        mock_chunk.content = "Test content"
        mock_chunk.id = "chunk1"

        # Create async iterator
        async def chunk_iterator():
            yield mock_chunk

        # Setup embedding service to raise CancelledError
        self.mock_embedding_service.get_embeddings = AsyncMock(
            side_effect=asyncio.CancelledError()
        )

        # Set batch size to 1
        self.mock_embedding_service.batch_size = 1

        with patch(
            "qdrant_loader.core.pipeline.workers.embedding_worker.prometheus_metrics"
        ):
            with pytest.raises(asyncio.CancelledError):
                results = []
                async for result in self.embedding_worker.process_chunks(
                    chunk_iterator()
                ):
                    results.append(result)

    @pytest.mark.asyncio
    async def test_process_chunks_empty_iterator(self):
        """Test chunk processing with empty iterator."""

        # Create empty async iterator
        async def empty_iterator():
            # Empty async generator - loop never executes but makes it a generator
            for _ in []:
                yield

        with patch(
            "qdrant_loader.core.pipeline.workers.embedding_worker.prometheus_metrics"
        ):
            results = []
            async for result in self.embedding_worker.process_chunks(empty_iterator()):
                results.append(result)

        # Should get no results
        assert len(results) == 0

        # Verify embedding service was not called
        self.mock_embedding_service.get_embeddings.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_chunks_bounds_concurrent_batches_to_max_workers(self):
        """No more than max_workers embedding batches should be in flight at once.

        Regression guard for the dispatch loop: batches used to be created
        eagerly with no cap, so max_embed_workers only throttled execution,
        not how many batches (and their chunk data) piled up in memory.
        """
        worker = EmbeddingWorker(
            embedding_service=self.mock_embedding_service,
            max_workers=2,
            queue_size=1000,
            shutdown_event=self.mock_shutdown_event,
        )
        self.mock_embedding_service.batch_size = 1

        chunks = []
        for i in range(6):
            chunk = Mock()
            chunk.content = f"Test content {i}"
            chunk.id = f"chunk{i}"
            chunks.append(chunk)

        async def chunk_iterator():
            for chunk in chunks:
                yield chunk

        in_flight = 0
        max_in_flight = 0
        lock = asyncio.Lock()

        async def get_embeddings_side_effect(contents):
            nonlocal in_flight, max_in_flight
            async with lock:
                in_flight += 1
                max_in_flight = max(max_in_flight, in_flight)
            await asyncio.sleep(0.01)
            async with lock:
                in_flight -= 1
            return [[0.1, 0.2, 0.3] for _ in contents]

        self.mock_embedding_service.get_embeddings = AsyncMock(
            side_effect=get_embeddings_side_effect
        )

        with patch(
            "qdrant_loader.core.pipeline.workers.embedding_worker.prometheus_metrics"
        ):
            results = []
            async for result in worker.process_chunks(chunk_iterator()):
                results.append(result)

        # All chunks still get processed, in submission order...
        assert len(results) == 6
        assert [chunk.id for chunk, _ in results] == [c.id for c in chunks]
        # ...but concurrency never exceeded max_workers, and genuine
        # concurrency (>1) did happen, ruling out an accidental fully
        # sequential implementation.
        assert max_in_flight == 2

    @pytest.mark.asyncio
    async def test_process_chunks_cancellation_cancels_in_flight_batches(self):
        """Cancelling the consumer must cancel dispatched-but-unfinished batch tasks.

        Guards the `except CancelledError: for task in pending: task.cancel()`
        cleanup: without it, in-flight embedding calls (up to the 300s timeout)
        keep running after the pipeline is torn down.
        """
        worker = EmbeddingWorker(
            embedding_service=self.mock_embedding_service,
            max_workers=2,
            queue_size=1000,
            shutdown_event=self.mock_shutdown_event,
        )
        self.mock_embedding_service.batch_size = 1

        hold = asyncio.Event()
        started: list = []
        cancelled: list = []

        async def blocking_get_embeddings(contents):
            started.append(contents)
            try:
                await hold.wait()
            except asyncio.CancelledError:
                cancelled.append(contents)
                raise
            return [[0.1, 0.2, 0.3] for _ in contents]

        self.mock_embedding_service.get_embeddings = AsyncMock(
            side_effect=blocking_get_embeddings
        )

        chunks = []
        for i in range(3):
            chunk = Mock()
            chunk.content = f"content {i}"
            chunk.id = f"chunk{i}"
            chunks.append(chunk)

        async def chunk_iterator():
            for chunk in chunks:
                yield chunk

        async def consume():
            with patch(
                "qdrant_loader.core.pipeline.workers.embedding_worker.prometheus_metrics"
            ):
                async for _ in worker.process_chunks(chunk_iterator()):
                    pass

        consumer = asyncio.create_task(consume())
        try:
            # Wait until both batch tasks are genuinely in flight.
            while len(started) < 2:
                await asyncio.sleep(0.01)

            consumer.cancel()
            with pytest.raises(asyncio.CancelledError):
                await consumer

            # Give cancellation a tick to propagate into the batch tasks.
            await asyncio.sleep(0.05)
            assert len(cancelled) == 2, (
                f"expected both in-flight batches cancelled, got {len(cancelled)}: "
                f"{cancelled}"
            )
        finally:
            hold.set()  # unblock any leaked task so the loop can close cleanly
            await asyncio.sleep(0)

    @pytest.mark.asyncio
    async def test_process_chunks_mixed_failures_conserve_all_chunks(self):
        """With concurrent batches where some fail outright, every dispatched
        chunk is yielded exactly once, in submission order, with None pairing
        for the failed ones — even when later batches finish first."""
        worker = EmbeddingWorker(
            embedding_service=self.mock_embedding_service,
            max_workers=3,
            queue_size=1000,
            shutdown_event=self.mock_shutdown_event,
        )
        self.mock_embedding_service.batch_size = 1

        async def flaky_get_embeddings(contents):
            idx = int(contents[0].rsplit(" ", 1)[1])
            # Stagger so completion order is roughly reversed vs submission.
            await asyncio.sleep(0.03 - idx * 0.004)
            if idx % 2 == 0:
                raise Exception(f"embedding service down for batch {idx}")
            return [[float(idx), 0.2, 0.3] for _ in contents]

        self.mock_embedding_service.get_embeddings = AsyncMock(
            side_effect=flaky_get_embeddings
        )

        chunks = []
        for i in range(6):
            chunk = Mock()
            chunk.content = f"content {i}"
            chunk.id = f"chunk{i}"
            chunks.append(chunk)

        async def chunk_iterator():
            for chunk in chunks:
                yield chunk

        with patch(
            "qdrant_loader.core.pipeline.workers.embedding_worker.prometheus_metrics"
        ):
            results = []
            async for result in worker.process_chunks(chunk_iterator()):
                results.append(result)

        # Conservation: all 6 yielded exactly once, in submission order.
        assert [chunk.id for chunk, _ in results] == [c.id for c in chunks]
        # Even-indexed batches failed -> None; odd-indexed succeeded.
        assert [emb is None for _, emb in results] == [
            True, False, True, False, True, False,
        ]

    @pytest.mark.asyncio
    async def test_process_chunks_shutdown_drains_dispatched_batches(self):
        """Batches dispatched (and completed) before shutdown are still yielded;
        chunks arriving after shutdown are never dispatched."""
        shutdown_event = asyncio.Event()
        worker = EmbeddingWorker(
            embedding_service=self.mock_embedding_service,
            max_workers=2,
            queue_size=1000,
            shutdown_event=shutdown_event,
        )
        self.mock_embedding_service.batch_size = 1

        completed = 0

        async def fast_get_embeddings(contents):
            nonlocal completed
            result = [[0.1, 0.2, 0.3] for _ in contents]
            completed += 1
            return result

        self.mock_embedding_service.get_embeddings = AsyncMock(
            side_effect=fast_get_embeddings
        )

        chunks = []
        for i in range(3):
            chunk = Mock()
            chunk.content = f"content {i}"
            chunk.id = f"chunk{i}"
            chunks.append(chunk)

        async def chunk_iterator():
            yield chunks[0]
            yield chunks[1]
            # Let both dispatched batches finish before signalling shutdown,
            # then produce one more chunk that must NOT be dispatched.
            while completed < 2:
                await asyncio.sleep(0.01)
            shutdown_event.set()
            yield chunks[2]

        with patch(
            "qdrant_loader.core.pipeline.workers.embedding_worker.prometheus_metrics"
        ):
            results = []
            async for result in worker.process_chunks(chunk_iterator()):
                results.append(result)

        # The two pre-shutdown chunks were drained and yielded...
        assert [chunk.id for chunk, _ in results] == ["chunk0", "chunk1"]
        # ...and the post-shutdown chunk never reached the embedding service.
        assert self.mock_embedding_service.get_embeddings.call_count == 2
