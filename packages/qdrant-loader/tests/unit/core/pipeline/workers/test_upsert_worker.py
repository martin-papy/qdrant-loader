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


def _make_chunk(chunk_id: str, parent_doc=None, total_chunks: int | None = None):
    """Build a mock chunk with attributes UpsertWorker touches."""
    chunk = Mock()
    chunk.id = chunk_id
    chunk.context = f"Content {chunk_id}"
    chunk.source = "test_source"
    chunk.source_type = "test"
    chunk.created_at = datetime(2023, 1, 1, 12, 0, 0)
    metadata = {}
    if parent_doc is not None:
        metadata["parent_document"] = parent_doc
        if total_chunks is not None:
            metadata["parent_document_total_chunks"] = total_chunks
    chunk.metadata = metadata
    return chunk


class TestUpsertWorker:
    """Test cases for UpsertWorker."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_qdrant_manager = Mock()
        self.mock_qdrant_manager.upsert_points = AsyncMock()
        self.mock_qdrant_manager.build_point_vector = Mock(
            side_effect=lambda embedding, _text: embedding
        )
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

    @pytest.mark.asyncio
    async def test_process_embedded_chunks_counts_unique_ids_only(self):
        """Duplicate chunk IDs should overwrite points and be counted once."""
        # Two chunks intentionally share the same ID
        mock_chunk1 = Mock()
        mock_chunk1.id = "same-chunk-id"
        mock_chunk1.content = "Version 1"
        mock_chunk1.source = "test_source"
        mock_chunk1.source_type = "test"
        mock_chunk1.created_at = datetime(2023, 1, 1, 12, 0, 0)
        mock_chunk1.metadata = {"parent_document": Mock(id="doc1")}

        mock_chunk2 = Mock()
        mock_chunk2.id = "same-chunk-id"
        mock_chunk2.content = "Version 2"
        mock_chunk2.source = "test_source"
        mock_chunk2.source_type = "test"
        mock_chunk2.created_at = datetime(2023, 1, 1, 12, 5, 0)
        mock_chunk2.metadata = {"parent_document": Mock(id="doc2")}

        async def embedded_chunks_iterator():
            yield (mock_chunk1, [0.1, 0.2, 0.3])
            yield (mock_chunk2, [0.4, 0.5, 0.6])

        self.upsert_worker.batch_size = 1

        with (
            patch(
                "qdrant_loader.core.pipeline.workers.upsert_worker.prometheus_metrics"
            ),
            patch(
                "qdrant_loader.core.pipeline.workers.upsert_worker.logger"
            ) as mock_logger,
        ):
            result = await self.upsert_worker.process_embedded_chunks(
                embedded_chunks_iterator()
            )

        # Count unique IDs only: 2 processed attempts, 1 unique stored point ID
        # Second batch (doc2) has duplicate chunk ID with first batch (doc1) → doc2 is affected
        assert result.success_count == 1
        assert result.error_count == 1  # doc2 affected by cross-batch duplicate
        assert len(result.errors) == 1
        assert "duplicate chunk IDs" in result.errors[0]
        assert "affecting 1 document(s)" in result.errors[0]
        assert result.successfully_processed_documents == {"doc1"}
        assert result.failed_document_ids == {"doc2"}
        mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_process_embedded_chunks_detects_same_batch_duplicates(self):
        """Duplicate IDs inside a single batch should be reported and counted once."""
        mock_chunk1 = Mock()
        mock_chunk1.id = "same-chunk-id"
        mock_chunk1.content = "Version 1"
        mock_chunk1.source = "test_source"
        mock_chunk1.source_type = "test"
        mock_chunk1.created_at = datetime(2023, 1, 1, 12, 0, 0)
        mock_chunk1.metadata = {"parent_document": Mock(id="doc1")}

        mock_chunk2 = Mock()
        mock_chunk2.id = "same-chunk-id"
        mock_chunk2.content = "Version 2"
        mock_chunk2.source = "test_source"
        mock_chunk2.source_type = "test"
        mock_chunk2.created_at = datetime(2023, 1, 1, 12, 5, 0)
        mock_chunk2.metadata = {"parent_document": Mock(id="doc2")}

        async def embedded_chunks_iterator():
            yield (mock_chunk1, [0.1, 0.2, 0.3])
            yield (mock_chunk2, [0.4, 0.5, 0.6])

        # Keep both chunks in the same batch
        self.upsert_worker.batch_size = 2

        with (
            patch(
                "qdrant_loader.core.pipeline.workers.upsert_worker.prometheus_metrics"
            ),
            patch(
                "qdrant_loader.core.pipeline.workers.upsert_worker.logger"
            ) as mock_logger,
        ):
            result = await self.upsert_worker.process_embedded_chunks(
                embedded_chunks_iterator()
            )

        assert result.success_count == 0
        assert (
            result.error_count == 2
        )  # Both doc1 and doc2 affected by same-batch duplicates
        assert len(result.errors) == 1
        assert "same-batch duplicate occurrences" in result.errors[0]
        assert "affecting 2 document(s)" in result.errors[0]
        mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_process_embedded_chunks_removes_global_success_on_late_duplicate(
        self,
    ):
        """A document previously marked successful should be removed after a later duplicate."""
        mock_chunk1 = Mock()
        mock_chunk1.id = "same-chunk-id"
        mock_chunk1.content = "Version 1"
        mock_chunk1.source = "test_source"
        mock_chunk1.source_type = "test"
        mock_chunk1.created_at = datetime(2023, 1, 1, 12, 0, 0)
        mock_chunk1.metadata = {"parent_document": Mock(id="doc1")}

        mock_chunk2 = Mock()
        mock_chunk2.id = "same-chunk-id"
        mock_chunk2.content = "Version 2"
        mock_chunk2.source = "test_source"
        mock_chunk2.source_type = "test"
        mock_chunk2.created_at = datetime(2023, 1, 1, 12, 5, 0)
        mock_chunk2.metadata = {"parent_document": Mock(id="doc1")}

        async def embedded_chunks_iterator():
            yield (mock_chunk1, [0.1, 0.2, 0.3])
            yield (mock_chunk2, [0.4, 0.5, 0.6])

        # Force cross-batch duplicate handling.
        self.upsert_worker.batch_size = 1

        with (
            patch(
                "qdrant_loader.core.pipeline.workers.upsert_worker.prometheus_metrics"
            ),
            patch(
                "qdrant_loader.core.pipeline.workers.upsert_worker.logger"
            ) as mock_logger,
        ):
            result = await self.upsert_worker.process_embedded_chunks(
                embedded_chunks_iterator()
            )

        assert result.success_count == 1
        assert result.error_count == 1
        assert result.successfully_processed_documents == set()
        assert len(result.errors) == 1
        assert "duplicate chunk IDs" in result.errors[0]
        mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_process_embedded_chunks_skips_upsert_on_failed_embedding(self):
        """A (chunk, None) pair from a failed embedding must not reach Qdrant."""
        mock_chunk = Mock()
        mock_chunk.id = "chunk1"
        mock_chunk.metadata = {"parent_document": Mock(id="doc1")}

        async def embedded_chunks_iterator():
            yield (mock_chunk, None)

        with patch("qdrant_loader.core.pipeline.workers.upsert_worker.prometheus_metrics"):
            result = await self.upsert_worker.process_embedded_chunks(
                embedded_chunks_iterator()
            )

        # Nothing should ever be sent to Qdrant for a chunk that failed to embed.
        self.mock_qdrant_manager.upsert_points.assert_not_called()

        assert result.success_count == 0
        assert result.error_count == 1
        assert len(result.errors) == 1
        assert "Embedding failed for chunk chunk1" in result.errors[0]
        # The document must not look successful just because nothing "failed to upsert" —
        # it never had a chance to be upserted at all.
        assert result.successfully_processed_documents == set()
        assert result.failed_document_ids == {"doc1"}

    @pytest.mark.asyncio
    async def test_process_embedded_chunks_partial_document_failure_not_marked_successful(
        self,
    ):
        """A document is only 'successful' once every chunk it produced is accounted for."""
        parent_doc = Mock(id="doc1")

        # doc1 was chunked into 3 pieces; only 2 arrive with a real embedding.
        good_chunk_1 = Mock()
        good_chunk_1.id = "doc1-chunk-1"
        good_chunk_1.content = "Content 1"
        good_chunk_1.source = "test_source"
        good_chunk_1.source_type = "test"
        good_chunk_1.created_at = datetime(2023, 1, 1, 12, 0, 0)
        good_chunk_1.metadata = {
            "parent_document": parent_doc,
            "parent_document_total_chunks": 3,
        }

        good_chunk_2 = Mock()
        good_chunk_2.id = "doc1-chunk-2"
        good_chunk_2.content = "Content 2"
        good_chunk_2.source = "test_source"
        good_chunk_2.source_type = "test"
        good_chunk_2.created_at = datetime(2023, 1, 1, 12, 0, 0)
        good_chunk_2.metadata = {
            "parent_document": parent_doc,
            "parent_document_total_chunks": 3,
        }

        failed_chunk = Mock()
        failed_chunk.id = "doc1-chunk-3"
        failed_chunk.metadata = {
            "parent_document": parent_doc,
            "parent_document_total_chunks": 3,
        }

        async def embedded_chunks_iterator():
            yield (good_chunk_1, [0.1, 0.2, 0.3])
            yield (good_chunk_2, [0.4, 0.5, 0.6])
            yield (failed_chunk, None)  # embedding failed upstream

        self.upsert_worker.batch_size = 10  # keep the 2 good chunks in one batch

        with patch("qdrant_loader.core.pipeline.workers.upsert_worker.prometheus_metrics"):
            result = await self.upsert_worker.process_embedded_chunks(
                embedded_chunks_iterator()
            )

        # 2 of 3 chunks upserted fine...
        assert result.success_count == 2
        assert result.error_count == 1
        # ...but the document as a whole must NOT be marked successful, since
        # one of its three chunks never made it in. It should be retried.
        assert result.successfully_processed_documents == set()
        assert result.failed_document_ids == {"doc1"}

    @pytest.mark.asyncio
    async def test_process_embedded_chunks_bounds_concurrent_batches_to_max_workers(
        self,
    ):
        """No more than max_workers upsert batches should be in flight at once.

        Regression guard for the dispatch loop: batches used to be created
        eagerly with no cap, so max_upsert_workers only throttled execution,
        not how many batches (and their embeddings) piled up in memory.
        """
        worker = UpsertWorker(
            qdrant_manager=self.mock_qdrant_manager,
            batch_size=1,
            max_workers=2,
            queue_size=1000,
            shutdown_event=self.mock_shutdown_event,
        )

        chunks = []
        for i in range(6):
            chunk = Mock()
            chunk.id = f"chunk{i}"
            chunk.content = f"Test content {i}"
            chunk.source = "test_source"
            chunk.source_type = "test"
            chunk.created_at = datetime(2023, 1, 1, 12, 0, 0)
            chunk.metadata = {"parent_document": Mock(id=f"doc{i}")}
            chunks.append(chunk)

        async def embedded_chunks_iterator():
            for i, chunk in enumerate(chunks):
                yield (chunk, [0.1 * i, 0.2 * i, 0.3 * i])

        in_flight = 0
        max_in_flight = 0
        lock = asyncio.Lock()

        async def upsert_points_side_effect(points):
            nonlocal in_flight, max_in_flight
            async with lock:
                in_flight += 1
                max_in_flight = max(max_in_flight, in_flight)
            await asyncio.sleep(0.01)
            async with lock:
                in_flight -= 1

        self.mock_qdrant_manager.upsert_points = AsyncMock(
            side_effect=upsert_points_side_effect
        )

        with patch("qdrant_loader.core.pipeline.workers.upsert_worker.prometheus_metrics"):
            result = await worker.process_embedded_chunks(embedded_chunks_iterator())

        assert result.success_count == 6
        assert result.successfully_processed_documents == {
            f"doc{i}" for i in range(6)
        }
        # Concurrency never exceeded max_workers, and genuine concurrency
        # (>1) did happen, ruling out an accidental fully sequential
        # implementation.
        assert max_in_flight == 2

    @pytest.mark.asyncio
    async def test_process_embedded_chunks_releases_reservation_on_failed_batch(self):
        """A chunk ID from a batch where nothing was written must not poison a retry.

        _merge_batch_outcome releases seen_chunk_ids reservations when
        success_count == 0; otherwise the retried chunk would be miscounted
        as a cross-batch duplicate.
        """
        worker = UpsertWorker(
            qdrant_manager=self.mock_qdrant_manager,
            batch_size=1,
            max_workers=1,  # failed batch merges (and releases) before retry dispatch
            queue_size=1000,
            shutdown_event=self.mock_shutdown_event,
        )

        # Same chunk ID twice: first attempt fails at Qdrant, retry succeeds.
        attempt = _make_chunk("chunk-x")
        retry = _make_chunk("chunk-x")

        calls = 0

        async def upsert_side_effect(points):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise Exception("Qdrant write failed")

        self.mock_qdrant_manager.upsert_points = AsyncMock(
            side_effect=upsert_side_effect
        )

        async def embedded_chunks_iterator():
            yield (attempt, [0.1, 0.2, 0.3])
            yield (retry, [0.1, 0.2, 0.3])

        with patch(
            "qdrant_loader.core.pipeline.workers.upsert_worker.prometheus_metrics"
        ):
            result = await worker.process_embedded_chunks(embedded_chunks_iterator())

        # The retry counts as a genuine success, not a duplicate.
        assert result.success_count == 1
        # And no duplicate-collision error was recorded for the retried ID.
        assert not any("duplicate chunk ids" in e.lower() for e in result.errors)
        # The original failure is still accounted.
        assert any("Upsert failed for chunk chunk-x" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_process_embedded_chunks_reserves_ids_for_in_flight_batches(self):
        """Reservation is synchronized at dispatch: a batch dispatched while an
        earlier batch with the same chunk ID is still in flight must see it as
        a cross-batch duplicate and not double-count the chunk."""
        worker = UpsertWorker(
            qdrant_manager=self.mock_qdrant_manager,
            batch_size=1,
            max_workers=2,  # both single-chunk batches genuinely in flight together
            queue_size=1000,
            shutdown_event=self.mock_shutdown_event,
        )

        first = _make_chunk("chunk-x")
        second = _make_chunk("chunk-x")  # same ID, dispatched while first runs

        async def slow_upsert(points):
            await asyncio.sleep(0.05)  # keep the first batch in flight

        self.mock_qdrant_manager.upsert_points = AsyncMock(side_effect=slow_upsert)

        async def embedded_chunks_iterator():
            yield (first, [0.1, 0.2, 0.3])
            yield (second, [0.4, 0.5, 0.6])

        with patch(
            "qdrant_loader.core.pipeline.workers.upsert_worker.prometheus_metrics"
        ):
            result = await worker.process_embedded_chunks(embedded_chunks_iterator())

        # The ID is counted exactly once even though both writes happened.
        assert result.success_count == 1
        assert self.mock_qdrant_manager.upsert_points.call_count == 2
        # The collision was detected and surfaced.
        assert any("duplicate chunk ids" in e.lower() for e in result.errors)

    @pytest.mark.asyncio
    async def test_process_embedded_chunks_batch_failure_fails_docs_but_continues(self):
        """If a batch writes nothing, every parent doc in it lands in
        failed_document_ids, and later batches are unaffected."""
        worker = UpsertWorker(
            qdrant_manager=self.mock_qdrant_manager,
            batch_size=2,
            max_workers=1,
            queue_size=1000,
            shutdown_event=self.mock_shutdown_event,
        )

        doc1, doc2 = Mock(id="doc1"), Mock(id="doc2")
        batch1 = [_make_chunk(f"d1-c{i}", doc1, total_chunks=2) for i in (1, 2)]
        batch2 = [_make_chunk(f"d2-c{i}", doc2, total_chunks=2) for i in (1, 2)]

        calls = 0

        async def upsert_side_effect(points):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise Exception("Qdrant write failed")

        self.mock_qdrant_manager.upsert_points = AsyncMock(
            side_effect=upsert_side_effect
        )

        async def embedded_chunks_iterator():
            for chunk in (*batch1, *batch2):
                yield (chunk, [0.1, 0.2, 0.3])

        with patch(
            "qdrant_loader.core.pipeline.workers.upsert_worker.prometheus_metrics"
        ):
            result = await worker.process_embedded_chunks(embedded_chunks_iterator())

        assert result.failed_document_ids == {"doc1"}
        assert result.successfully_processed_documents == {"doc2"}
        assert result.success_count == 2  # only doc2's chunks were written
        assert result.error_count >= 1

    @pytest.mark.asyncio
    async def test_process_embedded_chunks_document_success_across_batches(self):
        """A doc whose chunks span several batches is marked successful only
        after ALL its chunks are accounted for — and does end up successful."""
        worker = UpsertWorker(
            qdrant_manager=self.mock_qdrant_manager,
            batch_size=2,
            max_workers=1,
            queue_size=1000,
            shutdown_event=self.mock_shutdown_event,
        )
        self.mock_qdrant_manager.upsert_points = AsyncMock()

        doc = Mock(id="doc1")
        chunks = [_make_chunk(f"d1-c{i}", doc, total_chunks=4) for i in range(4)]

        async def embedded_chunks_iterator():
            for chunk in chunks:
                yield (chunk, [0.1, 0.2, 0.3])

        with patch(
            "qdrant_loader.core.pipeline.workers.upsert_worker.prometheus_metrics"
        ):
            result = await worker.process_embedded_chunks(embedded_chunks_iterator())

        assert result.success_count == 4
        assert result.successfully_processed_documents == {"doc1"}
        assert result.failed_document_ids == set()



