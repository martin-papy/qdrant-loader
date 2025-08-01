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
        """Test chunk processing with shutdown during iteration."""
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

        # Should only get result for first chunk before shutdown
        assert len(results) == 1
        assert results[0] == (mock_chunk1, [0.1, 0.2, 0.3])

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

                # Should get no results due to exceptions
                assert len(results) == 0

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

                # Should get result for first chunk only
                assert len(results) == 1
                assert results[0] == (mock_chunk1, [0.1, 0.2, 0.3])

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
            return
            # Note: yield is unreachable but kept for testing generator behavior

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
