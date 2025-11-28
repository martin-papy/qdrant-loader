"""Tests for the DocumentPipeline class."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from qdrant_loader.core.document import Document
from qdrant_loader.core.pipeline.document_pipeline import DocumentPipeline
from qdrant_loader.core.pipeline.workers.upsert_worker import PipelineResult


class TestDocumentPipeline:
    """Test cases for DocumentPipeline."""

    @pytest.fixture
    def mock_workers(self):
        """Create mock workers for testing."""
        chunking_worker = MagicMock()
        embedding_worker = MagicMock()
        upsert_worker = MagicMock()

        return chunking_worker, embedding_worker, upsert_worker

    @pytest.fixture
    def sample_documents(self):
        """Create sample documents for testing."""
        return [
            Document(
                content="This is test document 1",
                url="http://example.com/doc1",
                content_type="md",
                source_type="test",
                source="test_source",
                title="Test Document 1",
                metadata={"source": "test"},
            ),
            Document(
                content="This is test document 2",
                url="http://example.com/doc2",
                content_type="md",
                source_type="test",
                source="test_source",
                title="Test Document 2",
                metadata={"source": "test"},
            ),
        ]

    @pytest.fixture
    def document_pipeline(self, mock_workers):
        """Create a DocumentPipeline instance with mock workers."""
        chunking_worker, embedding_worker, upsert_worker = mock_workers
        return DocumentPipeline(chunking_worker, embedding_worker, upsert_worker)

    def test_initialization(self, mock_workers):
        """Test DocumentPipeline initialization."""
        chunking_worker, embedding_worker, upsert_worker = mock_workers

        pipeline = DocumentPipeline(chunking_worker, embedding_worker, upsert_worker)

        assert pipeline.chunking_worker == chunking_worker
        assert pipeline.embedding_worker == embedding_worker
        assert pipeline.upsert_worker == upsert_worker

    @pytest.mark.asyncio
    async def test_process_documents_success(
        self, document_pipeline, mock_workers, sample_documents
    ):
        """Test successful document processing."""
        chunking_worker, embedding_worker, upsert_worker = mock_workers

        # Mock the processing chain
        chunks_iter = AsyncMock()
        embedded_chunks_iter = AsyncMock()

        chunking_worker.process_documents.return_value = chunks_iter
        embedding_worker.process_chunks.return_value = embedded_chunks_iter

        # Mock successful pipeline result
        expected_result = PipelineResult()
        expected_result.success_count = 5
        expected_result.error_count = 0
        expected_result.errors = []

        upsert_worker.process_embedded_chunks = AsyncMock(return_value=expected_result)

        # Process documents
        result = await document_pipeline.process_documents(sample_documents)

        # Verify the chain was called correctly
        chunking_worker.process_documents.assert_called_once_with(sample_documents)
        embedding_worker.process_chunks.assert_called_once_with(chunks_iter)
        upsert_worker.process_embedded_chunks.assert_called_once_with(
            embedded_chunks_iter
        )

        # Verify result
        assert result == expected_result
        assert result.success_count == 5
        assert result.error_count == 0

    @pytest.mark.asyncio
    async def test_process_documents_with_errors(
        self, document_pipeline, mock_workers, sample_documents
    ):
        """Test document processing with some errors."""
        chunking_worker, embedding_worker, upsert_worker = mock_workers

        # Mock the processing chain
        chunks_iter = AsyncMock()
        embedded_chunks_iter = AsyncMock()

        chunking_worker.process_documents.return_value = chunks_iter
        embedding_worker.process_chunks.return_value = embedded_chunks_iter

        # Mock pipeline result with errors
        expected_result = PipelineResult()
        expected_result.success_count = 3
        expected_result.error_count = 2
        expected_result.errors = ["Error 1", "Error 2"]

        upsert_worker.process_embedded_chunks = AsyncMock(return_value=expected_result)

        # Process documents
        result = await document_pipeline.process_documents(sample_documents)

        # Verify result includes errors
        assert result.success_count == 3
        assert result.error_count == 2
        assert len(result.errors) == 2

    @pytest.mark.asyncio
    async def test_process_documents_timeout(
        self, document_pipeline, mock_workers, sample_documents
    ):
        """Test document processing with timeout."""
        chunking_worker, embedding_worker, upsert_worker = mock_workers

        # Mock the processing chain
        chunks_iter = AsyncMock()
        embedded_chunks_iter = AsyncMock()

        chunking_worker.process_documents.return_value = chunks_iter
        embedding_worker.process_chunks.return_value = embedded_chunks_iter

        # Mock upsert worker to raise TimeoutError
        async def slow_upsert(*args, **kwargs):
            await asyncio.sleep(10)  # This will be interrupted by timeout

        upsert_worker.process_embedded_chunks = AsyncMock(side_effect=slow_upsert)

        # Mock asyncio.wait_for to raise TimeoutError
        with patch("asyncio.wait_for", side_effect=TimeoutError("Timeout")):
            result = await document_pipeline.process_documents(sample_documents)

        # Verify timeout handling
        assert result.error_count == len(sample_documents)
        assert "Pipeline timed out after 1 hour" in result.errors

    @pytest.mark.asyncio
    async def test_process_documents_exception_in_pipeline(
        self, document_pipeline, mock_workers, sample_documents
    ):
        """Test document processing with exception in the pipeline."""
        chunking_worker, embedding_worker, upsert_worker = mock_workers

        # Mock chunking worker to raise an exception
        chunking_worker.process_documents.side_effect = Exception("Chunking failed")

        # Process documents
        result = await document_pipeline.process_documents(sample_documents)

        # Verify error handling
        assert result.error_count == len(sample_documents)
        assert len(result.errors) == 1
        assert "Pipeline failed: Chunking failed" in result.errors[0]

    @pytest.mark.asyncio
    async def test_process_documents_exception_in_embedding(
        self, document_pipeline, mock_workers, sample_documents
    ):
        """Test document processing with exception in embedding phase."""
        chunking_worker, embedding_worker, upsert_worker = mock_workers

        # Mock chunking to succeed but embedding to fail
        chunks_iter = AsyncMock()
        chunking_worker.process_documents.return_value = chunks_iter
        embedding_worker.process_chunks.side_effect = Exception("Embedding failed")

        # Process documents
        result = await document_pipeline.process_documents(sample_documents)

        # Verify error handling
        assert result.error_count == len(sample_documents)
        assert "Pipeline failed: Embedding failed" in result.errors[0]

    @pytest.mark.asyncio
    async def test_process_documents_exception_in_upsert(
        self, document_pipeline, mock_workers, sample_documents
    ):
        """Test document processing with exception in upsert phase."""
        chunking_worker, embedding_worker, upsert_worker = mock_workers

        # Mock chunking and embedding to succeed but upsert to fail
        chunks_iter = AsyncMock()
        embedded_chunks_iter = AsyncMock()

        chunking_worker.process_documents.return_value = chunks_iter
        embedding_worker.process_chunks.return_value = embedded_chunks_iter
        upsert_worker.process_embedded_chunks = AsyncMock(
            side_effect=Exception("Upsert failed")
        )

        # Process documents
        result = await document_pipeline.process_documents(sample_documents)

        # Verify error handling
        assert result.error_count == len(sample_documents)
        assert "Pipeline failed: Upsert failed" in result.errors[0]

    @pytest.mark.asyncio
    async def test_process_empty_documents_list(self, document_pipeline, mock_workers):
        """Test processing an empty list of documents."""
        chunking_worker, embedding_worker, upsert_worker = mock_workers

        # Mock the processing chain
        chunks_iter = AsyncMock()
        embedded_chunks_iter = AsyncMock()

        chunking_worker.process_documents.return_value = chunks_iter
        embedding_worker.process_chunks.return_value = embedded_chunks_iter

        # Mock empty result
        expected_result = PipelineResult()
        expected_result.success_count = 0
        expected_result.error_count = 0
        expected_result.errors = []

        upsert_worker.process_embedded_chunks = AsyncMock(return_value=expected_result)

        # Process empty list
        result = await document_pipeline.process_documents([])

        # Verify the chain was called
        chunking_worker.process_documents.assert_called_once_with([])

        # Verify result
        assert result.success_count == 0
        assert result.error_count == 0

    @pytest.mark.asyncio
    @patch("qdrant_loader.core.pipeline.document_pipeline.logger")
    async def test_logging_during_processing(
        self, mock_logger, document_pipeline, mock_workers, sample_documents
    ):
        """Test that appropriate logging occurs during processing."""
        chunking_worker, embedding_worker, upsert_worker = mock_workers

        # Mock the processing chain
        chunks_iter = AsyncMock()
        embedded_chunks_iter = AsyncMock()

        chunking_worker.process_documents.return_value = chunks_iter
        embedding_worker.process_chunks.return_value = embedded_chunks_iter

        # Mock successful result
        expected_result = PipelineResult()
        expected_result.success_count = 2
        expected_result.error_count = 0

        upsert_worker.process_embedded_chunks = AsyncMock(return_value=expected_result)

        # Process documents
        await document_pipeline.process_documents(sample_documents)

        # Verify logging calls
        assert mock_logger.info.call_count >= 5  # Start, phases, completion logs

        # Check specific log messages
        log_messages = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any(
            "Processing 2 documents through pipeline" in msg for msg in log_messages
        )
        assert any("Starting chunking phase" in msg for msg in log_messages)
        assert any(
            "Chunking completed, transitioning to embedding phase" in msg
            for msg in log_messages
        )
        assert any(
            "Embedding phase ready, starting upsert phase" in msg
            for msg in log_messages
        )
        assert any("Pipeline completed" in msg for msg in log_messages)

    @pytest.mark.asyncio
    @patch("qdrant_loader.core.pipeline.document_pipeline.logger")
    async def test_error_logging(
        self, mock_logger, document_pipeline, mock_workers, sample_documents
    ):
        """Test that errors are logged appropriately."""
        chunking_worker, embedding_worker, upsert_worker = mock_workers

        # Mock chunking worker to raise an exception
        error_message = "Test chunking error"
        chunking_worker.process_documents.side_effect = Exception(error_message)

        # Process documents
        await document_pipeline.process_documents(sample_documents)

        # Verify error logging
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args[0][0]
        assert error_message in error_call
        assert "Document pipeline failed" in error_call

    @pytest.mark.asyncio
    @patch("qdrant_loader.core.pipeline.document_pipeline.logger")
    async def test_timing_and_completion_logging(
        self, mock_logger, document_pipeline, mock_workers, sample_documents
    ):
        """Test that timing and completion information is logged."""
        chunking_worker, embedding_worker, upsert_worker = mock_workers

        # Mock the processing chain
        chunks_iter = AsyncMock()
        embedded_chunks_iter = AsyncMock()

        chunking_worker.process_documents.return_value = chunks_iter
        embedding_worker.process_chunks.return_value = embedded_chunks_iter

        # Mock successful result
        expected_result = PipelineResult()
        expected_result.success_count = 5
        expected_result.error_count = 2

        upsert_worker.process_embedded_chunks = AsyncMock(return_value=expected_result)

        # Process documents
        await document_pipeline.process_documents(sample_documents)

        # Verify timing and completion logs
        log_messages = [call[0][0] for call in mock_logger.info.call_args_list]

        # Check that timing information is logged (should contain timing info)
        assert any(
            "Chunking phase took" in msg and "seconds" in msg for msg in log_messages
        )
        assert any(
            "Embedding + Upsert phase took" in msg and "seconds" in msg
            for msg in log_messages
        )
        assert any(
            "Total pipeline duration:" in msg and "seconds" in msg
            for msg in log_messages
        )

        # Check completion logging with specific counts
        assert any("5 chunks processed, 2 errors" in msg for msg in log_messages)

    @pytest.mark.asyncio
    async def test_process_documents_with_single_document(
        self, document_pipeline, mock_workers
    ):
        """Test processing a single document."""
        chunking_worker, embedding_worker, upsert_worker = mock_workers

        single_doc = [
            Document(
                content="Single test document",
                url="http://example.com/single",
                content_type="md",
                source_type="test",
                source="test_source",
                title="Single Document",
                metadata={"source": "test"},
            )
        ]

        # Mock the processing chain
        chunks_iter = AsyncMock()
        embedded_chunks_iter = AsyncMock()

        chunking_worker.process_documents.return_value = chunks_iter
        embedding_worker.process_chunks.return_value = embedded_chunks_iter

        # Mock successful result for single document
        expected_result = PipelineResult()
        expected_result.success_count = 1
        expected_result.error_count = 0

        upsert_worker.process_embedded_chunks = AsyncMock(return_value=expected_result)

        # Process single document
        result = await document_pipeline.process_documents(single_doc)

        # Verify result
        assert result.success_count == 1
        assert result.error_count == 0

    @pytest.mark.asyncio
    async def test_worker_interaction_order(
        self, document_pipeline, mock_workers, sample_documents
    ):
        """Test that workers are called in the correct order."""
        chunking_worker, embedding_worker, upsert_worker = mock_workers

        call_order = []

        def track_chunking_call(*args, **kwargs):
            call_order.append("chunking")
            return AsyncMock()

        def track_embedding_call(*args, **kwargs):
            call_order.append("embedding")
            return AsyncMock()

        async def track_upsert_call(*args, **kwargs):
            call_order.append("upsert")
            result = PipelineResult()
            result.success_count = 2
            result.error_count = 0
            return result

        chunking_worker.process_documents.side_effect = track_chunking_call
        embedding_worker.process_chunks.side_effect = track_embedding_call
        upsert_worker.process_embedded_chunks.side_effect = track_upsert_call

        # Process documents
        await document_pipeline.process_documents(sample_documents)

        # Verify call order
        assert call_order == ["chunking", "embedding", "upsert"]
