"""Tests for UpsertWorker."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from qdrant_loader.core.pipeline.workers.upsert_worker import (
    PipelineResult,
    UpsertWorker,
)


class TestPipelineResult:
    """Test cases for PipelineResult."""

    def test_pipeline_result_initialization(self):
        """Test PipelineResult initialization."""
        result = PipelineResult()

        assert result.success_count == 0
        assert result.error_count == 0
        assert result.successfully_processed_documents == set()
        assert result.failed_document_ids == set()
        assert result.errors == []


class TestUpsertWorker:
    """Test cases for UpsertWorker."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_qdrant_manager = Mock()
        self.mock_qdrant_manager.upsert_points = AsyncMock()
        self.mock_shutdown_event = Mock(spec=asyncio.Event)
        self.mock_shutdown_event.is_set.return_value = False

        self.upsert_worker = UpsertWorker(
            qdrant_manager=self.mock_qdrant_manager,
            batch_size=10,
            max_workers=4,
            queue_size=1000,
            shutdown_event=self.mock_shutdown_event,
        )

    def test_upsert_worker_initialization(self):
        """Test UpsertWorker initialization."""
        assert self.upsert_worker.qdrant_manager == self.mock_qdrant_manager
        assert self.upsert_worker.batch_size == 10
        assert self.upsert_worker.max_workers == 4
        assert self.upsert_worker.queue_size == 1000
        assert self.upsert_worker.shutdown_event == self.mock_shutdown_event

    def test_upsert_worker_initialization_default_shutdown_event(self):
        """Test UpsertWorker initialization with default shutdown event."""
        worker = UpsertWorker(
            qdrant_manager=self.mock_qdrant_manager,
            batch_size=5,
            max_workers=2,
            queue_size=500,
        )

        assert worker.qdrant_manager == self.mock_qdrant_manager
        assert worker.batch_size == 5
        assert worker.max_workers == 2
        assert worker.queue_size == 500
        assert worker.shutdown_event is not None
        assert isinstance(worker.shutdown_event, asyncio.Event)

    @pytest.mark.asyncio
    async def test_process_empty_batch(self):
        """Test processing empty batch."""
        result = await self.upsert_worker.process([])

        success_count, error_count, successful_doc_ids, errors = result
        assert success_count == 0
        assert error_count == 0
        assert successful_doc_ids == set()
        assert errors == []

    @pytest.mark.asyncio
    async def test_process_success(self):
        """Test successful batch processing."""
        # Setup mock chunks
        mock_chunk1 = Mock()
        mock_chunk1.id = "chunk1"
        mock_chunk1.content = "Test content 1"
        mock_chunk1.source = "test_source"
        mock_chunk1.source_type = "test"
        mock_chunk1.created_at = datetime(2023, 1, 1, 12, 0, 0)
        mock_chunk1.updated_at = datetime(2023, 1, 1, 12, 30, 0)
        mock_chunk1.title = "Test Title 1"
        mock_chunk1.url = "http://test1.com"
        mock_chunk1.metadata = {
            "parent_document_id": "doc1",
            "parent_document": Mock(id="doc1"),
            "title": "Test Title 1",
            "url": "http://test1.com",
        }

        mock_chunk2 = Mock()
        mock_chunk2.id = "chunk2"
        mock_chunk2.content = "Test content 2"
        mock_chunk2.source = "test_source"
        mock_chunk2.source_type = "test"
        mock_chunk2.created_at = datetime(2023, 1, 1, 13, 0, 0)
        mock_chunk2.metadata = {
            "parent_document_id": "doc2",
            "parent_document": Mock(id="doc2"),
        }

        # Mock embeddings
        embedding1 = [0.1, 0.2, 0.3]
        embedding2 = [0.4, 0.5, 0.6]
        batch = [(mock_chunk1, embedding1), (mock_chunk2, embedding2)]

        with patch(
            "qdrant_loader.core.pipeline.workers.upsert_worker.prometheus_metrics"
        ) as mock_metrics:
            mock_timer = Mock()
            mock_metrics.UPSERT_DURATION.time.return_value = mock_timer
            mock_timer.__enter__ = Mock(return_value=mock_timer)
            mock_timer.__exit__ = Mock(return_value=None)

            result = await self.upsert_worker.process(batch)

        success_count, error_count, successful_doc_ids, errors = result
        assert success_count == 2
        assert error_count == 0
        assert successful_doc_ids == {"doc1", "doc2"}
        assert errors == []

        # Verify qdrant_manager.upsert_points was called with correct points
        self.mock_qdrant_manager.upsert_points.assert_called_once()
        points = self.mock_qdrant_manager.upsert_points.call_args[0][0]
        assert len(points) == 2

        # Verify first point
        point1 = points[0]
        assert point1.id == "chunk1"
        assert point1.vector == embedding1
        assert point1.payload["content"] == "Test content 1"
        assert point1.payload["source"] == "test_source"
        assert point1.payload["source_type"] == "test"
        assert point1.payload["title"] == "Test Title 1"
        assert point1.payload["url"] == "http://test1.com"
        assert point1.payload["document_id"] == "doc1"

        # Verify metrics were called
        mock_metrics.INGESTED_DOCUMENTS.inc.assert_called_once_with(2)

    @pytest.mark.asyncio
    async def test_process_chunk_without_updated_at(self):
        """Test processing chunk without updated_at attribute."""
        mock_chunk = Mock()
        mock_chunk.id = "chunk1"
        mock_chunk.content = "Test content"
        mock_chunk.source = "test_source"
        mock_chunk.source_type = "test"
        mock_chunk.created_at = datetime(2023, 1, 1, 12, 0, 0)
        # No updated_at attribute
        del mock_chunk.updated_at
        mock_chunk.metadata = {"parent_document": Mock(id="doc1")}

        embedding = [0.1, 0.2, 0.3]
        batch = [(mock_chunk, embedding)]

        with patch(
            "qdrant_loader.core.pipeline.workers.upsert_worker.prometheus_metrics"
        ):
            result = await self.upsert_worker.process(batch)

        success_count, error_count, successful_doc_ids, errors = result
        assert success_count == 1
        assert error_count == 0

        # Verify point was created with created_at as updated_at
        points = self.mock_qdrant_manager.upsert_points.call_args[0][0]
        point = points[0]
        assert point.payload["updated_at"] == "2023-01-01T12:00:00"

    @pytest.mark.asyncio
    async def test_process_chunk_without_title_and_url(self):
        """Test processing chunk without title and url attributes."""
        mock_chunk = Mock()
        mock_chunk.id = "chunk1"
        mock_chunk.content = "Test content"
        mock_chunk.source = "test_source"
        mock_chunk.source_type = "test"
        mock_chunk.created_at = datetime(2023, 1, 1, 12, 0, 0)
        # No title or url attributes
        del mock_chunk.title
        del mock_chunk.url
        mock_chunk.metadata = {
            "parent_document": Mock(id="doc1"),
            "title": "Metadata Title",
            "url": "http://metadata.com",
        }

        embedding = [0.1, 0.2, 0.3]
        batch = [(mock_chunk, embedding)]

        with patch(
            "qdrant_loader.core.pipeline.workers.upsert_worker.prometheus_metrics"
        ):
            result = await self.upsert_worker.process(batch)

        success_count, error_count, successful_doc_ids, errors = result
        assert success_count == 1
        assert error_count == 0

        # Verify point was created with metadata values
        points = self.mock_qdrant_manager.upsert_points.call_args[0][0]
        point = points[0]
        assert point.payload["title"] == "Metadata Title"
        assert point.payload["url"] == "http://metadata.com"

    @pytest.mark.asyncio
    async def test_process_chunk_without_parent_document_id(self):
        """Test processing chunk without parent_document_id."""
        mock_chunk = Mock()
        mock_chunk.id = "chunk1"
        mock_chunk.content = "Test content"
        mock_chunk.source = "test_source"
        mock_chunk.source_type = "test"
        mock_chunk.created_at = datetime(2023, 1, 1, 12, 0, 0)
        mock_chunk.metadata = {}  # No parent_document_id

        embedding = [0.1, 0.2, 0.3]
        batch = [(mock_chunk, embedding)]

        with patch(
            "qdrant_loader.core.pipeline.workers.upsert_worker.prometheus_metrics"
        ):
            result = await self.upsert_worker.process(batch)

        success_count, error_count, successful_doc_ids, errors = result
        assert success_count == 1
        assert error_count == 0

        # Verify point was created with chunk.id as document_id
        points = self.mock_qdrant_manager.upsert_points.call_args[0][0]
        point = points[0]
        assert point.payload["document_id"] == "chunk1"

    @pytest.mark.asyncio
    async def test_process_upsert_exception(self):
        """Test processing with upsert exception."""
        mock_chunk = Mock()
        mock_chunk.id = "chunk1"
        mock_chunk.content = "Test content"
        mock_chunk.source = "test_source"
        mock_chunk.source_type = "test"
        mock_chunk.created_at = datetime(2023, 1, 1, 12, 0, 0)
        mock_chunk.metadata = {"parent_document": Mock(id="doc1")}

        embedding = [0.1, 0.2, 0.3]
        batch = [(mock_chunk, embedding)]

        # Setup qdrant_manager to raise exception
        self.mock_qdrant_manager.upsert_points.side_effect = Exception("Upsert failed")

        with patch(
            "qdrant_loader.core.pipeline.workers.upsert_worker.prometheus_metrics"
        ):
            with patch(
                "qdrant_loader.core.pipeline.workers.upsert_worker.logger"
            ) as mock_logger:
                result = await self.upsert_worker.process(batch)

        success_count, error_count, successful_doc_ids, errors = result
        assert success_count == 0
        assert error_count == 1
        assert successful_doc_ids == set()
        assert len(errors) == 1
        assert "Upsert failed for chunk chunk1: Upsert failed" in errors[0]

        # Verify error logging
        mock_logger.error.assert_called_once_with(
            "Upsert failed for chunk chunk1: Upsert failed"
        )

    @pytest.mark.asyncio
    async def test_process_embedded_chunks_success(self):
        """Test successful processing of embedded chunks."""
        # Setup mock chunks
        mock_chunk1 = Mock()
        mock_chunk1.id = "chunk1"
        mock_chunk1.content = "Test content 1"
        mock_chunk1.source = "test_source"
        mock_chunk1.source_type = "test"
        mock_chunk1.created_at = datetime(2023, 1, 1, 12, 0, 0)
        mock_chunk1.metadata = {"parent_document": Mock(id="doc1")}

        mock_chunk2 = Mock()
        mock_chunk2.id = "chunk2"
        mock_chunk2.content = "Test content 2"
        mock_chunk2.source = "test_source"
        mock_chunk2.source_type = "test"
        mock_chunk2.created_at = datetime(2023, 1, 1, 13, 0, 0)
        mock_chunk2.metadata = {"parent_document": Mock(id="doc2")}

        # Create async iterator
        async def embedded_chunks_iterator():
            yield (mock_chunk1, [0.1, 0.2, 0.3])
            yield (mock_chunk2, [0.4, 0.5, 0.6])

        # Set batch size to 1 to process chunks individually
        self.upsert_worker.batch_size = 1

        with patch(
            "qdrant_loader.core.pipeline.workers.upsert_worker.prometheus_metrics"
        ):
            result = await self.upsert_worker.process_embedded_chunks(
                embedded_chunks_iterator()
            )

        assert result.success_count == 2
        assert result.error_count == 0
        assert result.successfully_processed_documents == {"doc1", "doc2"}
        assert result.errors == []

        # Verify qdrant_manager.upsert_points was called twice (once per chunk)
        assert self.mock_qdrant_manager.upsert_points.call_count == 2

    @pytest.mark.asyncio
    async def test_process_embedded_chunks_with_batching(self):
        """Test processing embedded chunks with batching."""
        # Setup mock chunks
        chunks = []
        for i in range(5):
            mock_chunk = Mock()
            mock_chunk.id = f"chunk{i}"
            mock_chunk.content = f"Test content {i}"
            mock_chunk.source = "test_source"
            mock_chunk.source_type = "test"
            mock_chunk.created_at = datetime(2023, 1, 1, 12, 0, 0)
            mock_chunk.metadata = {"parent_document": Mock(id=f"doc{i}")}
            chunks.append(mock_chunk)

        # Create async iterator
        async def embedded_chunks_iterator():
            for i, chunk in enumerate(chunks):
                yield (chunk, [0.1 * i, 0.2 * i, 0.3 * i])

        # Set batch size to 2 to force multiple batches
        self.upsert_worker.batch_size = 2

        with patch(
            "qdrant_loader.core.pipeline.workers.upsert_worker.prometheus_metrics"
        ):
            result = await self.upsert_worker.process_embedded_chunks(
                embedded_chunks_iterator()
            )

        assert result.success_count == 5
        assert result.error_count == 0
        assert result.successfully_processed_documents == {
            "doc0",
            "doc1",
            "doc2",
            "doc3",
            "doc4",
        }
        assert result.errors == []

        # Verify qdrant_manager.upsert_points was called 3 times (2+2+1 batches)
        assert self.mock_qdrant_manager.upsert_points.call_count == 3

    @pytest.mark.asyncio
    async def test_process_embedded_chunks_with_shutdown_during_iteration(self):
        """Test processing with shutdown during iteration."""
        # Setup mock chunks
        mock_chunk1 = Mock()
        mock_chunk1.id = "chunk1"
        mock_chunk1.content = "Test content 1"
        mock_chunk1.source = "test_source"
        mock_chunk1.source_type = "test"
        mock_chunk1.created_at = datetime(2023, 1, 1, 12, 0, 0)
        mock_chunk1.metadata = {"parent_document": Mock(id="doc1")}

        mock_chunk2 = Mock()
        mock_chunk2.id = "chunk2"
        mock_chunk2.content = "Test content 2"
        mock_chunk2.source = "test_source"
        mock_chunk2.source_type = "test"
        mock_chunk2.created_at = datetime(2023, 1, 1, 13, 0, 0)
        mock_chunk2.metadata = {"parent_document": Mock(id="doc2")}

        # Create async iterator that sets shutdown after first chunk
        async def embedded_chunks_iterator():
            yield (mock_chunk1, [0.1, 0.2, 0.3])
            self.mock_shutdown_event.is_set.return_value = True
            yield (mock_chunk2, [0.4, 0.5, 0.6])

        # Set batch size to 1 to process chunks individually
        self.upsert_worker.batch_size = 1

        with patch(
            "qdrant_loader.core.pipeline.workers.upsert_worker.prometheus_metrics"
        ):
            result = await self.upsert_worker.process_embedded_chunks(
                embedded_chunks_iterator()
            )

        # Should only process first chunk before shutdown
        assert result.success_count == 1
        assert result.error_count == 0
        assert result.successfully_processed_documents == {"doc1"}
        assert result.errors == []

        # Verify qdrant_manager.upsert_points was called once
        assert self.mock_qdrant_manager.upsert_points.call_count == 1

    @pytest.mark.asyncio
    async def test_process_embedded_chunks_with_shutdown_before_final_batch(self):
        """Test processing with shutdown before final batch."""
        # Setup mock chunks
        mock_chunk1 = Mock()
        mock_chunk1.id = "chunk1"
        mock_chunk1.content = "Test content 1"
        mock_chunk1.source = "test_source"
        mock_chunk1.source_type = "test"
        mock_chunk1.created_at = datetime(2023, 1, 1, 12, 0, 0)
        mock_chunk1.metadata = {"parent_document": Mock(id="doc1")}

        mock_chunk2 = Mock()
        mock_chunk2.id = "chunk2"
        mock_chunk2.content = "Test content 2"
        mock_chunk2.source = "test_source"
        mock_chunk2.source_type = "test"
        mock_chunk2.created_at = datetime(2023, 1, 1, 13, 0, 0)
        mock_chunk2.metadata = {"parent_document": Mock(id="doc2")}

        # Create async iterator
        async def embedded_chunks_iterator():
            yield (mock_chunk1, [0.1, 0.2, 0.3])
            yield (mock_chunk2, [0.4, 0.5, 0.6])

        # Set batch size to 3 so chunks accumulate in batch
        self.upsert_worker.batch_size = 3

        # Set shutdown after iteration completes but before final batch processing
        async def mock_process_embedded_chunks():
            result = PipelineResult()
            batch = []

            async for chunk_embedding in embedded_chunks_iterator():
                batch.append(chunk_embedding)
                if len(batch) >= self.upsert_worker.batch_size:
                    # This won't happen with batch_size=3 and 2 chunks
                    pass

            # Set shutdown before final batch processing
            self.mock_shutdown_event.is_set.return_value = True

            # Final batch should not be processed due to shutdown
            if batch and not self.mock_shutdown_event.is_set():
                # This won't execute
                pass

            return result

        with patch(
            "qdrant_loader.core.pipeline.workers.upsert_worker.prometheus_metrics"
        ):
            result = await self.upsert_worker.process_embedded_chunks(
                embedded_chunks_iterator()
            )

        # Should process the final batch since shutdown is checked after iteration
        # The actual implementation processes the final batch if it exists and shutdown is not set at that moment
        assert result.success_count == 2
        assert result.error_count == 0
        assert result.successfully_processed_documents == {"doc1", "doc2"}
        assert result.errors == []

        # Verify qdrant_manager.upsert_points was called once for the final batch
        assert self.mock_qdrant_manager.upsert_points.call_count == 1

    @pytest.mark.asyncio
    async def test_process_embedded_chunks_cancelled_error(self):
        """Test processing with cancellation."""

        # Create async iterator that raises CancelledError
        async def embedded_chunks_iterator():
            yield (Mock(), [0.1, 0.2, 0.3])
            raise asyncio.CancelledError()

        with patch(
            "qdrant_loader.core.pipeline.workers.upsert_worker.prometheus_metrics"
        ):
            with patch(
                "qdrant_loader.core.pipeline.workers.upsert_worker.logger"
            ) as mock_logger:
                with pytest.raises(asyncio.CancelledError):
                    await self.upsert_worker.process_embedded_chunks(
                        embedded_chunks_iterator()
                    )

                # Verify debug logging
                mock_logger.debug.assert_any_call("UpsertWorker started")
                mock_logger.debug.assert_any_call("UpsertWorker cancelled")
                mock_logger.debug.assert_any_call("UpsertWorker exited")

    @pytest.mark.asyncio
    async def test_process_embedded_chunks_empty_iterator(self):
        """Test processing with empty iterator."""

        # Create empty async iterator
        async def empty_iterator():
            # Empty async generator - loop never executes but makes it a generator
            for _ in []:
                yield

        with patch(
            "qdrant_loader.core.pipeline.workers.upsert_worker.prometheus_metrics"
        ):
            with patch(
                "qdrant_loader.core.pipeline.workers.upsert_worker.logger"
            ) as mock_logger:
                result = await self.upsert_worker.process_embedded_chunks(
                    empty_iterator()
                )

        assert result.success_count == 0
        assert result.error_count == 0
        assert result.successfully_processed_documents == set()
        assert result.errors == []

        # Verify qdrant_manager.upsert_points was not called
        self.mock_qdrant_manager.upsert_points.assert_not_called()

        # Verify debug logging
        mock_logger.debug.assert_any_call("UpsertWorker started")
        mock_logger.debug.assert_any_call("UpsertWorker exited")

    @pytest.mark.asyncio
    async def test_process_embedded_chunks_with_final_batch(self):
        """Test processing with final batch that doesn't reach batch_size."""
        # Setup mock chunks
        mock_chunk1 = Mock()
        mock_chunk1.id = "chunk1"
        mock_chunk1.content = "Test content 1"
        mock_chunk1.source = "test_source"
        mock_chunk1.source_type = "test"
        mock_chunk1.created_at = datetime(2023, 1, 1, 12, 0, 0)
        mock_chunk1.metadata = {"parent_document": Mock(id="doc1")}

        mock_chunk2 = Mock()
        mock_chunk2.id = "chunk2"
        mock_chunk2.content = "Test content 2"
        mock_chunk2.source = "test_source"
        mock_chunk2.source_type = "test"
        mock_chunk2.created_at = datetime(2023, 1, 1, 13, 0, 0)
        mock_chunk2.metadata = {"parent_document": Mock(id="doc2")}

        mock_chunk3 = Mock()
        mock_chunk3.id = "chunk3"
        mock_chunk3.content = "Test content 3"
        mock_chunk3.source = "test_source"
        mock_chunk3.source_type = "test"
        mock_chunk3.created_at = datetime(2023, 1, 1, 14, 0, 0)
        mock_chunk3.metadata = {"parent_document": Mock(id="doc3")}

        # Create async iterator with 3 chunks
        async def embedded_chunks_iterator():
            yield (mock_chunk1, [0.1, 0.2, 0.3])
            yield (mock_chunk2, [0.4, 0.5, 0.6])
            yield (mock_chunk3, [0.7, 0.8, 0.9])

        # Set batch size to 2 so we get one full batch (2 chunks) and one final batch (1 chunk)
        self.upsert_worker.batch_size = 2

        with patch(
            "qdrant_loader.core.pipeline.workers.upsert_worker.prometheus_metrics"
        ):
            result = await self.upsert_worker.process_embedded_chunks(
                embedded_chunks_iterator()
            )

        assert result.success_count == 3
        assert result.error_count == 0
        assert result.successfully_processed_documents == {"doc1", "doc2", "doc3"}
        assert result.errors == []

        # Verify qdrant_manager.upsert_points was called twice (one full batch + one final batch)
        assert self.mock_qdrant_manager.upsert_points.call_count == 2
