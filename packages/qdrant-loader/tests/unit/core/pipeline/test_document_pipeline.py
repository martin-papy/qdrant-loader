"""Comprehensive tests for DocumentPipeline."""

import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

from qdrant_loader.core.document import Document
from qdrant_loader.core.pipeline.document_pipeline import DocumentPipeline
from qdrant_loader.core.pipeline.workers.upsert_worker import PipelineResult


class TestDocumentPipeline:
    """Test suite for DocumentPipeline."""

    @pytest.fixture
    def sample_documents(self):
        """Create sample documents for testing."""
        return [
            Document(
                title="Test Document 1",
                content="This is test content 1 about AI and machine learning.",
                url="https://example.com/doc1",
                source="test-source-1",
                content_type="text/plain",
                source_type="web",
                metadata={},
                created_at=datetime.now(timezone.utc),
            ),
            Document(
                title="Test Document 2",
                content="This is test content 2 about data science.",
                url="https://example.com/doc2",
                source="test-source-2",
                content_type="text/plain",
                source_type="web",
                metadata={},
                created_at=datetime.now(timezone.utc),
            ),
        ]

    @pytest.fixture
    def mock_chunking_worker(self):
        """Create a mock ChunkingWorker with async generator."""
        worker = AsyncMock()

        async def process_documents(docs):
            for i, doc in enumerate(docs):
                yield f"chunk_{i}_from_{doc.title}"

        worker.process_documents = process_documents
        return worker

    @pytest.fixture
    def mock_embedding_worker(self):
        """Create a mock EmbeddingWorker with async generator."""
        worker = AsyncMock()

        async def process_chunks(chunks):
            async for chunk in chunks:
                yield (chunk, [0.1, 0.2, 0.3])  # Mock embedding

        worker.process_chunks = process_chunks
        return worker

    @pytest.fixture
    def mock_upsert_worker(self):
        """Create a mock UpsertWorker."""
        worker = AsyncMock()
        result = PipelineResult()
        result.success_count = 2
        result.error_count = 0
        result.successfully_processed_documents = {"doc1", "doc2"}
        result.errors = []
        worker.process_embedded_chunks.return_value = result
        return worker

    @pytest.fixture
    def mock_entity_extraction_worker(self):
        """Create a mock EntityExtractionWorker with async generator."""
        from qdrant_loader.core.entity_extractor import ExtractionResult
        from qdrant_loader.core.types import (
            ExtractedEntity,
            ExtractedRelationship,
            EntityType,
            RelationshipType,
        )

        worker = AsyncMock()

        async def process_documents(docs):
            for doc in docs:
                result = ExtractionResult(source_text=doc.content)
                result.entities = [
                    ExtractedEntity(
                        name="AI",
                        entity_type=EntityType.CONCEPT,
                        context=doc.content,
                        confidence=0.9,
                    )
                ]
                result.relationships = [
                    ExtractedRelationship(
                        source_entity="AI",
                        target_entity="machine learning",
                        relationship_type=RelationshipType.RELATED_TO,
                        context=doc.content,
                        confidence=0.8,
                    )
                ]
                yield result

        worker.process_documents = process_documents
        return worker

    @pytest.fixture
    def pipeline_without_entity_extraction(
        self, mock_chunking_worker, mock_embedding_worker, mock_upsert_worker
    ):
        """Create a DocumentPipeline without entity extraction."""
        return DocumentPipeline(
            chunking_worker=mock_chunking_worker,
            embedding_worker=mock_embedding_worker,
            upsert_worker=mock_upsert_worker,
        )

    @pytest.fixture
    def pipeline_with_entity_extraction(
        self,
        mock_chunking_worker,
        mock_embedding_worker,
        mock_upsert_worker,
        mock_entity_extraction_worker,
    ):
        """Create a DocumentPipeline with entity extraction."""
        return DocumentPipeline(
            chunking_worker=mock_chunking_worker,
            embedding_worker=mock_embedding_worker,
            upsert_worker=mock_upsert_worker,
            entity_extraction_worker=mock_entity_extraction_worker,
        )

    # Initialization Tests
    def test_pipeline_initialization_without_entity_extraction(
        self, mock_chunking_worker, mock_embedding_worker, mock_upsert_worker
    ):
        """Test pipeline initialization without entity extraction worker."""
        pipeline = DocumentPipeline(
            chunking_worker=mock_chunking_worker,
            embedding_worker=mock_embedding_worker,
            upsert_worker=mock_upsert_worker,
        )

        assert pipeline.chunking_worker == mock_chunking_worker
        assert pipeline.embedding_worker == mock_embedding_worker
        assert pipeline.upsert_worker == mock_upsert_worker
        assert pipeline.entity_extraction_worker is None

    def test_pipeline_initialization_with_entity_extraction(
        self,
        mock_chunking_worker,
        mock_embedding_worker,
        mock_upsert_worker,
        mock_entity_extraction_worker,
    ):
        """Test pipeline initialization with entity extraction worker."""
        pipeline = DocumentPipeline(
            chunking_worker=mock_chunking_worker,
            embedding_worker=mock_embedding_worker,
            upsert_worker=mock_upsert_worker,
            entity_extraction_worker=mock_entity_extraction_worker,
        )

        assert pipeline.chunking_worker == mock_chunking_worker
        assert pipeline.embedding_worker == mock_embedding_worker
        assert pipeline.upsert_worker == mock_upsert_worker
        assert pipeline.entity_extraction_worker == mock_entity_extraction_worker

    # Document Processing Tests
    @pytest.mark.asyncio
    async def test_process_documents_success_without_entity_extraction(
        self, pipeline_without_entity_extraction, sample_documents
    ):
        """Test successful document processing without entity extraction."""
        result = await pipeline_without_entity_extraction.process_documents(
            sample_documents
        )

        assert isinstance(result, PipelineResult)
        assert result.success_count == 2
        assert result.error_count == 0
        assert len(result.successfully_processed_documents) == 2
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_process_documents_success_with_entity_extraction(
        self, pipeline_with_entity_extraction, sample_documents
    ):
        """Test successful document processing with entity extraction."""
        result = await pipeline_with_entity_extraction.process_documents(
            sample_documents
        )

        assert isinstance(result, PipelineResult)
        assert result.success_count == 2
        assert result.error_count == 0
        assert len(result.successfully_processed_documents) == 2
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_process_empty_document_list(
        self, pipeline_without_entity_extraction
    ):
        """Test processing an empty list of documents."""
        result = await pipeline_without_entity_extraction.process_documents([])
        assert isinstance(result, PipelineResult)

    # Error Handling Tests
    @pytest.mark.asyncio
    async def test_chunking_worker_error(
        self, pipeline_without_entity_extraction, sample_documents
    ):
        """Test error handling when chunking worker fails."""

        async def failing_chunking_worker(docs):
            raise Exception("Chunking failed")
            yield  # Unreachable but makes it an async generator

        # Replace the worker's method directly
        pipeline_without_entity_extraction.chunking_worker.process_documents = (
            failing_chunking_worker
        )

        # Mock upsert worker to consume the iterator and trigger the exception
        async def consuming_upsert_worker(embedded_chunks_iter):
            result = PipelineResult()
            result.success_count = 0
            result.error_count = 0
            result.successfully_processed_documents = set()
            result.errors = []

            async for _ in embedded_chunks_iter:
                result.success_count += 1

            return result

        pipeline_without_entity_extraction.upsert_worker.process_embedded_chunks = (
            consuming_upsert_worker
        )

        result = await pipeline_without_entity_extraction.process_documents(
            sample_documents
        )

        assert isinstance(result, PipelineResult)
        assert result.error_count == len(sample_documents)
        assert len(result.errors) == 1
        assert "Pipeline failed:" in result.errors[0]

    @pytest.mark.asyncio
    async def test_embedding_worker_error(
        self, pipeline_without_entity_extraction, sample_documents
    ):
        """Test error handling when embedding worker fails."""

        async def failing_embedding_worker(chunks):
            raise Exception("Embedding failed")
            yield  # Unreachable but makes it an async generator

        # Replace the worker's method directly
        pipeline_without_entity_extraction.embedding_worker.process_chunks = (
            failing_embedding_worker
        )

        # Mock upsert worker to consume the iterator and trigger the exception
        async def consuming_upsert_worker(embedded_chunks_iter):
            result = PipelineResult()
            result.success_count = 0
            result.error_count = 0
            result.successfully_processed_documents = set()
            result.errors = []

            async for _ in embedded_chunks_iter:
                result.success_count += 1

            return result

        pipeline_without_entity_extraction.upsert_worker.process_embedded_chunks = (
            consuming_upsert_worker
        )

        result = await pipeline_without_entity_extraction.process_documents(
            sample_documents
        )

        assert isinstance(result, PipelineResult)
        assert result.error_count == len(sample_documents)
        assert len(result.errors) == 1
        assert "Pipeline failed:" in result.errors[0]

    @pytest.mark.asyncio
    async def test_upsert_worker_error(
        self, pipeline_without_entity_extraction, sample_documents
    ):
        """Test error handling when upsert worker fails."""

        async def failing_upsert_worker(embedded_chunks_iter):
            raise Exception("Upsert failed")

        pipeline_without_entity_extraction.upsert_worker.process_embedded_chunks = (
            failing_upsert_worker
        )

        result = await pipeline_without_entity_extraction.process_documents(
            sample_documents
        )

        assert isinstance(result, PipelineResult)
        assert result.error_count == len(sample_documents)
        assert len(result.errors) == 1
        assert "Pipeline failed:" in result.errors[0]

    @pytest.mark.asyncio
    async def test_entity_extraction_worker_error(
        self, pipeline_with_entity_extraction, sample_documents
    ):
        """Test error handling when entity extraction worker fails."""

        async def failing_entity_extraction(docs):
            raise Exception("Entity extraction failed")
            yield  # Unreachable but makes it an async generator

        pipeline_with_entity_extraction.entity_extraction_worker.process_documents = (
            failing_entity_extraction
        )

        result = await pipeline_with_entity_extraction.process_documents(
            sample_documents
        )

        # Main pipeline should still succeed even if entity extraction fails
        assert isinstance(result, PipelineResult)
        assert result.success_count == 2  # Main pipeline succeeded
        assert result.error_count == 0

    # Timeout Handling Tests
    @pytest.mark.asyncio
    async def test_pipeline_timeout(
        self, pipeline_without_entity_extraction, sample_documents
    ):
        """Test pipeline timeout handling."""

        async def slow_upsert(embedded_chunks_iter):
            await asyncio.sleep(10)  # Longer than timeout
            return PipelineResult()

        pipeline_without_entity_extraction.upsert_worker.process_embedded_chunks = (
            slow_upsert
        )

        # Patch the timeout to be very short for testing
        with patch(
            "qdrant_loader.core.pipeline.document_pipeline.asyncio.wait_for"
        ) as mock_wait_for:
            mock_wait_for.side_effect = TimeoutError()

            result = await pipeline_without_entity_extraction.process_documents(
                sample_documents
            )

            assert isinstance(result, PipelineResult)
            assert result.error_count == len(sample_documents)
            assert len(result.errors) == 1
            assert "Pipeline timed out after 1 hour" in result.errors[0]

    @pytest.mark.asyncio
    async def test_entity_extraction_timeout(
        self, pipeline_with_entity_extraction, sample_documents
    ):
        """Test entity extraction timeout handling."""

        async def slow_entity_extraction(docs):
            await asyncio.sleep(10)  # Longer than timeout
            for doc in docs:
                yield f"result_for_{doc.title}"

        pipeline_with_entity_extraction.entity_extraction_worker.process_documents = (
            slow_entity_extraction
        )

        # Mock asyncio.wait_for to simulate timeout for entity extraction only
        original_wait_for = asyncio.wait_for

        async def selective_timeout(awaitable, timeout=None):
            if timeout == 300.0:  # Entity extraction timeout
                raise TimeoutError()
            return await original_wait_for(awaitable, timeout)

        with patch(
            "qdrant_loader.core.pipeline.document_pipeline.asyncio.wait_for",
            side_effect=selective_timeout,
        ):
            result = await pipeline_with_entity_extraction.process_documents(
                sample_documents
            )

            # Main pipeline should still succeed
            assert isinstance(result, PipelineResult)
            assert result.success_count == 2
            assert result.error_count == 0

    # Entity Extraction Private Method Tests
    @pytest.mark.asyncio
    async def test_process_entity_extraction_success(
        self, pipeline_with_entity_extraction, sample_documents
    ):
        """Test successful entity extraction processing."""
        await pipeline_with_entity_extraction._process_entity_extraction(
            sample_documents
        )
        # No exception should be raised

    @pytest.mark.asyncio
    async def test_process_entity_extraction_no_worker(
        self, pipeline_without_entity_extraction, sample_documents
    ):
        """Test entity extraction processing when no worker is configured."""
        # Should return immediately without error
        await pipeline_without_entity_extraction._process_entity_extraction(
            sample_documents
        )
        # No worker should be called
        assert pipeline_without_entity_extraction.entity_extraction_worker is None

    @pytest.mark.asyncio
    async def test_process_entity_extraction_error(
        self, pipeline_with_entity_extraction, sample_documents
    ):
        """Test entity extraction processing with error."""

        async def failing_process_documents(docs):
            raise Exception("Entity extraction failed")
            yield  # Unreachable but makes it an async generator

        pipeline_with_entity_extraction.entity_extraction_worker.process_documents = (
            failing_process_documents
        )

        # Should raise the exception
        with pytest.raises(Exception, match="Entity extraction failed"):
            await pipeline_with_entity_extraction._process_entity_extraction(
                sample_documents
            )

    # Integration and Workflow Tests
    @pytest.mark.asyncio
    async def test_complete_pipeline_workflow(
        self, pipeline_with_entity_extraction, sample_documents
    ):
        """Test the complete pipeline workflow with all phases."""
        result = await pipeline_with_entity_extraction.process_documents(
            sample_documents
        )

        assert isinstance(result, PipelineResult)
        assert result.success_count == 2
        assert result.error_count == 0

    @pytest.mark.asyncio
    async def test_partial_failure_handling(
        self, pipeline_without_entity_extraction, sample_documents
    ):
        """Test handling of partial failures in pipeline result."""
        # Create a result with partial failures
        partial_result = PipelineResult()
        partial_result.success_count = 1
        partial_result.error_count = 1
        partial_result.successfully_processed_documents = {"doc1"}
        partial_result.failed_document_ids = {"doc2"}
        partial_result.errors = ["Failed to process doc2"]

        async def partial_failure_upsert(embedded_chunks_iter):
            return partial_result

        pipeline_without_entity_extraction.upsert_worker.process_embedded_chunks = (
            partial_failure_upsert
        )

        result = await pipeline_without_entity_extraction.process_documents(
            sample_documents
        )

        assert isinstance(result, PipelineResult)
        assert result.success_count == 1
        assert result.error_count == 1
        assert len(result.successfully_processed_documents) == 1
        assert len(result.errors) == 1

    # Edge Cases and Boundary Tests
    @pytest.mark.asyncio
    async def test_cancelled_error_handling(
        self, pipeline_with_entity_extraction, sample_documents
    ):
        """Test handling of CancelledError during entity extraction."""

        async def cancelling_entity_extraction(docs):
            raise asyncio.CancelledError()
            yield  # Unreachable but makes it an async generator

        pipeline_with_entity_extraction.entity_extraction_worker.process_documents = (
            cancelling_entity_extraction
        )

        result = await pipeline_with_entity_extraction.process_documents(
            sample_documents
        )

        # Main pipeline should still succeed
        assert isinstance(result, PipelineResult)
        assert result.success_count == 2
        assert result.error_count == 0

    @pytest.mark.asyncio
    async def test_logging_verification(
        self, pipeline_without_entity_extraction, sample_documents
    ):
        """Test that appropriate logging methods are called during pipeline execution."""
        with patch("qdrant_loader.core.pipeline.document_pipeline.logger") as mock_logger:
            await pipeline_without_entity_extraction.process_documents(sample_documents)

            # Verify that logger.info was called with expected messages
            info_calls = [call for call in mock_logger.info.call_args_list]
            
            # Extract the actual message strings from the calls
            info_messages = []
            for call in info_calls:
                args, kwargs = call
                if args:
                    info_messages.append(str(args[0]))
            
            # Check for key log messages
            assert any(
                f"Processing {len(sample_documents)} documents through pipeline" in msg
                for msg in info_messages
            )
            assert any("Starting chunking phase" in msg for msg in info_messages)
            assert any(
                "Chunking completed, transitioning to embedding phase" in msg
                for msg in info_messages
            )
            assert any("Embedding phase ready, starting upsert phase" in msg for msg in info_messages)
            assert any("Pipeline completed:" in msg for msg in info_messages)

    @pytest.mark.asyncio
    async def test_timing_measurements(
        self, pipeline_without_entity_extraction, sample_documents
    ):
        """Test that timing measurements are properly calculated."""
        with patch("time.time") as mock_time:
            # Mock time progression - provide enough values for all timing calls
            mock_time.side_effect = [
                i * 1.0 for i in range(20)
            ]  # 20 timestamps should be enough

            result = await pipeline_without_entity_extraction.process_documents(
                sample_documents
            )

            assert isinstance(result, PipelineResult)
            # Verify time.time was called multiple times for timing measurements
            assert mock_time.call_count >= 4
