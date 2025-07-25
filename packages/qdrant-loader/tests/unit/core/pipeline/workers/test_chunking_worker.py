"""Tests for ChunkingWorker module."""

import asyncio
import concurrent.futures
from unittest.mock import Mock, call, patch

import pytest
from qdrant_loader.core.chunking.chunking_service import ChunkingService
from qdrant_loader.core.document import Document
from qdrant_loader.core.pipeline.workers.chunking_worker import ChunkingWorker


class TestChunkingWorker:
    """Test ChunkingWorker functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.chunking_service = Mock(spec=ChunkingService)
        self.chunk_executor = Mock(spec=concurrent.futures.ThreadPoolExecutor)
        self.shutdown_event = asyncio.Event()

        self.worker = ChunkingWorker(
            chunking_service=self.chunking_service,
            chunk_executor=self.chunk_executor,
            max_workers=5,
            queue_size=100,
            shutdown_event=self.shutdown_event,
        )

    def create_test_document(
        self, doc_id="test_doc", content="Test content", content_type="text", url=None
    ):
        """Helper method to create test documents with all required fields."""
        if url is None:
            url = f"https://example.com/{doc_id}.txt"

        return Document(
            url=url,
            content=content,
            content_type=content_type,
            title=f"Test Document {doc_id}",
            source_type="test",
            source="test_source",
            metadata={},
        )

    def test_chunking_worker_initialization(self):
        """Test ChunkingWorker initialization."""
        assert self.worker.chunking_service == self.chunking_service
        assert self.worker.chunk_executor == self.chunk_executor
        assert self.worker.shutdown_event == self.shutdown_event
        assert self.worker.max_workers == 5
        assert self.worker.queue_size == 100

    def test_chunking_worker_initialization_default_shutdown_event(self):
        """Test ChunkingWorker initialization with default shutdown event."""
        worker = ChunkingWorker(
            chunking_service=self.chunking_service,
            chunk_executor=self.chunk_executor,
        )

        assert isinstance(worker.shutdown_event, asyncio.Event)
        assert worker.max_workers == 10  # Default value
        assert worker.queue_size == 1000  # Default value

    @pytest.mark.asyncio
    async def test_process_document_success(self):
        """Test successful document processing."""
        # Setup test document
        document = self.create_test_document(
            doc_id="test_doc",
            content="Test content for chunking",
            url="https://example.com/test.txt",
        )

        # Setup mock chunks
        mock_chunk1 = Mock()
        mock_chunk1.metadata = {}
        mock_chunk2 = Mock()
        mock_chunk2.metadata = {}
        mock_chunks = [mock_chunk1, mock_chunk2]

        # Setup chunking service mock
        self.chunking_service.chunk_document.return_value = mock_chunks

        with patch("asyncio.get_running_loop") as mock_get_loop:
            mock_loop = Mock()
            mock_get_loop.return_value = mock_loop

            # Mock the executor call
            future = asyncio.Future()
            future.set_result(mock_chunks)
            mock_loop.run_in_executor.return_value = future

            with patch(
                "qdrant_loader.core.pipeline.workers.chunking_worker.prometheus_metrics"
            ) as mock_metrics:
                with patch("psutil.cpu_percent", return_value=50.0):
                    with patch("psutil.virtual_memory") as mock_memory:
                        mock_memory.return_value.percent = 60.0

                        # Execute
                        result = await self.worker.process(document)

                        # Verify
                        assert result == mock_chunks

                        # Verify metrics were updated
                        mock_metrics.CPU_USAGE.set.assert_called_once_with(50.0)
                        mock_metrics.MEMORY_USAGE.set.assert_called_once_with(60.0)

                        # Verify executor was called
                        mock_loop.run_in_executor.assert_called_once_with(
                            self.chunk_executor,
                            self.chunking_service.chunk_document,
                            document,
                        )

                        # Verify parent document was added to chunk metadata
                        assert mock_chunk1.metadata["parent_document"] == document
                        assert mock_chunk2.metadata["parent_document"] == document

    @pytest.mark.asyncio
    async def test_process_document_shutdown_before_processing(self):
        """Test document processing when shutdown is signaled before processing."""
        document = self.create_test_document()

        # Set shutdown event
        self.shutdown_event.set()

        # Execute
        result = await self.worker.process(document)

        # Verify
        assert result == []

        # Verify chunking service was not called
        self.chunking_service.chunk_document.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_document_metadata_assignment(self):
        """Test that parent document is properly assigned to chunk metadata."""
        document = self.create_test_document()

        # Setup mock chunks with proper metadata
        mock_chunk1 = Mock()
        mock_chunk1.metadata = {}
        mock_chunk2 = Mock()
        mock_chunk2.metadata = {}
        mock_chunks = [mock_chunk1, mock_chunk2]

        with patch("asyncio.get_running_loop") as mock_get_loop:
            mock_loop = Mock()
            mock_get_loop.return_value = mock_loop

            # Mock the executor call
            future = asyncio.Future()
            future.set_result(mock_chunks)
            mock_loop.run_in_executor.return_value = future

            with patch(
                "qdrant_loader.core.pipeline.workers.chunking_worker.prometheus_metrics"
            ):
                with patch("psutil.cpu_percent", return_value=50.0):
                    with patch("psutil.virtual_memory") as mock_memory:
                        mock_memory.return_value.percent = 60.0

                        # Execute first to get chunks
                        result = await self.worker.process(document)

                        # Verify chunks were processed and metadata was added
                        assert result == mock_chunks
                        assert mock_chunk1.metadata["parent_document"] == document
                        assert mock_chunk2.metadata["parent_document"] == document

    @pytest.mark.asyncio
    async def test_process_document_timeout_error(self):
        """Test document processing with timeout error."""
        document = self.create_test_document()

        with patch("asyncio.get_running_loop") as mock_get_loop:
            mock_loop = Mock()
            mock_get_loop.return_value = mock_loop

            # Mock timeout
            future = asyncio.Future()
            future.set_exception(TimeoutError())
            mock_loop.run_in_executor.return_value = future

            with patch(
                "qdrant_loader.core.pipeline.workers.chunking_worker.prometheus_metrics"
            ):
                with patch("psutil.cpu_percent", return_value=50.0):
                    with patch("psutil.virtual_memory") as mock_memory:
                        mock_memory.return_value.percent = 60.0

                        # Execute and verify exception
                        with pytest.raises(TimeoutError):
                            await self.worker.process(document)

    @pytest.mark.asyncio
    async def test_process_document_cancelled_error(self):
        """Test document processing with cancelled error."""
        document = self.create_test_document()

        with patch("asyncio.get_running_loop") as mock_get_loop:
            mock_loop = Mock()
            mock_get_loop.return_value = mock_loop

            # Mock cancellation
            future = asyncio.Future()
            future.set_exception(asyncio.CancelledError())
            mock_loop.run_in_executor.return_value = future

            with patch(
                "qdrant_loader.core.pipeline.workers.chunking_worker.prometheus_metrics"
            ):
                with patch("psutil.cpu_percent", return_value=50.0):
                    with patch("psutil.virtual_memory") as mock_memory:
                        mock_memory.return_value.percent = 60.0

                        # Execute and verify exception
                        with pytest.raises(asyncio.CancelledError):
                            await self.worker.process(document)

    @pytest.mark.asyncio
    async def test_process_document_general_exception(self):
        """Test document processing with general exception."""
        document = self.create_test_document()

        with patch("asyncio.get_running_loop") as mock_get_loop:
            mock_loop = Mock()
            mock_get_loop.return_value = mock_loop

            # Mock general exception
            future = asyncio.Future()
            future.set_exception(Exception("Chunking failed"))
            mock_loop.run_in_executor.return_value = future

            with patch(
                "qdrant_loader.core.pipeline.workers.chunking_worker.prometheus_metrics"
            ):
                with patch("psutil.cpu_percent", return_value=50.0):
                    with patch("psutil.virtual_memory") as mock_memory:
                        mock_memory.return_value.percent = 60.0

                        # Execute and verify exception
                        with pytest.raises(Exception, match="Chunking failed"):
                            await self.worker.process(document)

    @pytest.mark.asyncio
    async def test_process_documents_success(self):
        """Test successful processing of multiple documents."""
        # Setup test documents
        doc1 = self.create_test_document(doc_id="doc1", content="Content 1")
        doc2 = self.create_test_document(doc_id="doc2", content="Content 2")
        documents = [doc1, doc2]

        # Setup mock chunks
        chunks1 = [Mock(), Mock()]
        chunks2 = [Mock()]

        # Mock the process method instead of process_with_semaphore
        with patch.object(self.worker, "process") as mock_process:
            mock_process.side_effect = [chunks1, chunks2]

            # Execute
            result_chunks = []
            async for chunk in self.worker.process_documents(documents):
                result_chunks.append(chunk)

            # Verify
            expected_chunks = chunks1 + chunks2
            assert result_chunks == expected_chunks

            # Verify process was called for each document
            assert mock_process.call_count == 2
            mock_process.assert_has_calls([call(doc1), call(doc2)], any_order=True)

    @pytest.mark.asyncio
    async def test_process_documents_with_exceptions(self):
        """Test processing documents with some exceptions."""
        # Setup test documents
        doc1 = self.create_test_document(doc_id="doc1", content="Content 1")
        doc2 = self.create_test_document(doc_id="doc2", content="Content 2")
        documents = [doc1, doc2]

        # Setup mock results - one success, one exception
        chunks1 = [Mock(), Mock()]
        exception = Exception("Processing failed")

        # Mock the process method instead of process_with_semaphore
        with patch.object(self.worker, "process") as mock_process:
            mock_process.side_effect = [chunks1, exception]

            # Execute
            result_chunks = []
            async for chunk in self.worker.process_documents(documents):
                result_chunks.append(chunk)

            # Verify - should only get chunks from successful processing
            assert result_chunks == chunks1

    @pytest.mark.asyncio
    async def test_process_documents_empty_results(self):
        """Test processing documents with empty results."""
        # Setup test documents
        doc1 = self.create_test_document(doc_id="doc1", content="Content 1")
        documents = [doc1]

        # Mock the process method to return empty list
        with patch.object(self.worker, "process") as mock_process:
            mock_process.return_value = []

            # Execute
            result_chunks = []
            async for chunk in self.worker.process_documents(documents):
                result_chunks.append(chunk)

            # Verify - should get no chunks
            assert result_chunks == []

    @pytest.mark.asyncio
    async def test_process_documents_shutdown_during_processing(self):
        """Test processing documents when shutdown is signaled during processing."""
        # Setup test documents
        doc1 = self.create_test_document(doc_id="doc1", content="Content 1")
        documents = [doc1]

        # Setup mock chunks
        chunks1 = [Mock(), Mock()]

        # Mock the process method
        with patch.object(self.worker, "process") as mock_process:
            mock_process.return_value = chunks1

            # Set shutdown event
            self.shutdown_event.set()

            # Execute
            result_chunks = []
            async for chunk in self.worker.process_documents(documents):
                result_chunks.append(chunk)

            # Verify - should get no chunks due to shutdown
            assert result_chunks == []

    @pytest.mark.asyncio
    async def test_process_documents_cancelled_error(self):
        """Test processing documents with cancelled error."""
        # Setup test documents
        doc1 = self.create_test_document(doc_id="doc1", content="Content 1")
        documents = [doc1]

        # Mock the process method to raise CancelledError
        with patch.object(self.worker, "process") as mock_process:
            mock_process.side_effect = asyncio.CancelledError()

            # Execute - CancelledError should be caught and handled
            result_chunks = []
            try:
                async for chunk in self.worker.process_documents(documents):
                    result_chunks.append(chunk)
            except asyncio.CancelledError:
                # This is expected behavior - CancelledError propagates up
                pass

            # Verify - should get no chunks due to CancelledError
            assert result_chunks == []

    def test_calculate_adaptive_timeout_very_small_file(self):
        """Test adaptive timeout calculation for very small files."""
        document = self.create_test_document(content="x" * 500)  # 500 bytes

        timeout = self.worker._calculate_adaptive_timeout(document)

        # Should be base timeout for very small files (updated to match new implementation)
        assert timeout >= 30.0
        assert timeout <= 60.0  # With size factor

    def test_calculate_adaptive_timeout_small_file(self):
        """Test adaptive timeout calculation for small files."""
        document = self.create_test_document(content="x" * 5000)  # 5KB

        timeout = self.worker._calculate_adaptive_timeout(document)

        # Should be base timeout for small files (updated to match new implementation)
        assert timeout >= 60.0
        assert timeout <= 120.0  # With size factor

    def test_calculate_adaptive_timeout_medium_file(self):
        """Test adaptive timeout calculation for medium files."""
        document = self.create_test_document(content="x" * 30000)  # 30KB

        timeout = self.worker._calculate_adaptive_timeout(document)

        # Should be base timeout for medium files (updated to match new implementation)
        assert timeout >= 120.0
        assert timeout <= 300.0  # With size factor

    def test_calculate_adaptive_timeout_large_file(self):
        """Test adaptive timeout calculation for large files."""
        document = self.create_test_document(content="x" * 75000)  # 75KB

        timeout = self.worker._calculate_adaptive_timeout(document)

        # Should be base timeout for large files (updated to match new implementation)
        assert timeout >= 240.0
        assert timeout <= 600.0  # Capped at maximum

    def test_calculate_adaptive_timeout_very_large_file(self):
        """Test adaptive timeout calculation for very large files."""
        document = self.create_test_document(content="x" * 200000)  # 200KB

        timeout = self.worker._calculate_adaptive_timeout(document)

        # Should be base timeout for very large files, capped at maximum (updated to match new implementation)
        assert timeout >= 360.0
        assert timeout <= 600.0  # Capped at maximum

    def test_calculate_adaptive_timeout_html_file(self):
        """Test adaptive timeout calculation for HTML files."""
        document = self.create_test_document(
            content="x" * 30000, content_type="html"
        )  # 30KB

        timeout = self.worker._calculate_adaptive_timeout(document)

        # HTML files should get 50% more time
        text_document = self.create_test_document(
            content="x" * 30000, content_type="text"
        )  # Same size
        text_timeout = self.worker._calculate_adaptive_timeout(text_document)

        # HTML timeout should be higher than text timeout
        assert timeout > text_timeout

    def test_calculate_adaptive_timeout_non_html_content_type(self):
        """Test adaptive timeout calculation with non-HTML content type."""
        document = self.create_test_document(
            content="x" * 30000, content_type="markdown"
        )  # 30KB

        timeout = self.worker._calculate_adaptive_timeout(document)

        # Should work with any content type (non-HTML doesn't get extra time) - updated to match new implementation
        assert timeout >= 120.0
        assert timeout <= 600.0

    def test_calculate_adaptive_timeout_maximum_cap(self):
        """Test that adaptive timeout is capped at maximum."""
        document = self.create_test_document(
            content="x" * 1000000, content_type="html"
        )  # 1MB - very large

        timeout = self.worker._calculate_adaptive_timeout(document)

        # Should be capped at 600 seconds (10 minutes) - updated to match new implementation
        assert timeout == 600.0

    def test_calculate_adaptive_timeout_size_factor_scaling(self):
        """Test that size factor scales correctly."""
        # Test different sizes to verify scaling
        sizes = [1000, 10000, 50000, 100000, 200000]
        timeouts = []

        for size in sizes:
            document = self.create_test_document(
                doc_id=f"test_doc_{size}",
                content="x" * size,
                url=f"https://example.com/file_{size}.txt",
            )
            timeout = self.worker._calculate_adaptive_timeout(document)
            timeouts.append(timeout)

        # Timeouts should generally increase with size (until cap)
        for i in range(len(timeouts) - 1):
            # Allow for some variation due to different base timeouts
            # but overall trend should be increasing
            if timeouts[i + 1] < 600.0:  # Not at cap (updated to match new max)
                assert timeouts[i + 1] >= timeouts[i] * 0.8  # Allow some variation
