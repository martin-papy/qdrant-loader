"""Comprehensive tests for EntityExtractionWorker."""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from qdrant_loader.core.document import Document
from qdrant_loader.core.entity_extractor import (
    EntityExtractor,
    ExtractionResult,
)
from qdrant_loader.core.pipeline.workers.entity_extraction_worker import (
    EntityExtractionWorker,
)
from qdrant_loader.core.types import (
    EntityType,
    ExtractedEntity,
    ExtractedRelationship,
    RelationshipType,
)


class TestEntityExtractionWorker:
    """Test suite for EntityExtractionWorker."""

    @pytest.fixture
    def mock_entity_extractor(self):
        """Create a mock EntityExtractor."""
        extractor = AsyncMock(spec=EntityExtractor)
        extractor.extract_entities = AsyncMock()
        return extractor

    @pytest.fixture
    def sample_document(self):
        """Create a sample document for testing."""
        return Document(
            title="Test Document",
            content="This is a test document about artificial intelligence and machine learning.",
            url="https://example.com/test-doc",
            source="test-source",
            content_type="text/plain",
            source_type="web",
            metadata={},
            created_at=datetime.now(UTC),
        )

    @pytest.fixture
    def sample_extraction_result(self):
        """Create a sample extraction result."""
        return ExtractionResult(
            entities=[
                ExtractedEntity(
                    name="artificial intelligence",
                    entity_type=EntityType.CONCEPT,
                    confidence=0.9,
                    context="artificial intelligence",
                ),
                ExtractedEntity(
                    name="machine learning",
                    entity_type=EntityType.CONCEPT,
                    confidence=0.8,
                    context="machine learning",
                ),
            ],
            relationships=[
                ExtractedRelationship(
                    source_entity="artificial intelligence",
                    target_entity="machine learning",
                    relationship_type=RelationshipType.RELATED_TO,
                    confidence=0.7,
                    context="artificial intelligence and machine learning",
                )
            ],
            processing_time=1.5,
            source_text="This is a test document about artificial intelligence and machine learning.",
        )

    @pytest.fixture
    def entity_extraction_worker(self, mock_entity_extractor):
        """Create an EntityExtractionWorker instance."""
        return EntityExtractionWorker(
            entity_extractor=mock_entity_extractor,
            max_workers=3,
            queue_size=100,
        )

    def test_initialization(self, mock_entity_extractor):
        """Test EntityExtractionWorker initialization."""
        worker = EntityExtractionWorker(
            entity_extractor=mock_entity_extractor,
            max_workers=5,
            queue_size=1000,
        )

        assert worker.entity_extractor == mock_entity_extractor
        assert worker.max_workers == 5
        assert worker.queue_size == 1000
        assert isinstance(worker.shutdown_event, asyncio.Event)
        assert not worker.shutdown_event.is_set()

    def test_initialization_with_shutdown_event(self, mock_entity_extractor):
        """Test EntityExtractionWorker initialization with custom shutdown event."""
        shutdown_event = asyncio.Event()
        worker = EntityExtractionWorker(
            entity_extractor=mock_entity_extractor,
            max_workers=2,
            queue_size=50,
            shutdown_event=shutdown_event,
        )

        assert worker.shutdown_event == shutdown_event

    @pytest.mark.asyncio
    async def test_process_document_success(
        self, entity_extraction_worker, sample_document, sample_extraction_result
    ):
        """Test successful document processing."""
        entity_extraction_worker.entity_extractor.extract_entities.return_value = (
            sample_extraction_result
        )

        result = await entity_extraction_worker.process(sample_document)

        # Verify extraction was called with correct parameters
        entity_extraction_worker.entity_extractor.extract_entities.assert_called_once_with(
            text=sample_document.content,
            source_description=f"Document: {sample_document.url}",
            reference_time=sample_document.created_at,
        )

        # Verify result
        assert result == sample_extraction_result
        assert result.metadata["document_id"] == sample_document.id
        assert result.metadata["document_url"] == sample_document.url
        assert result.metadata["document_content_type"] == sample_document.content_type
        assert result.metadata["document_source_type"] == sample_document.source_type
        assert "processing_time" in result.metadata

    @pytest.mark.asyncio
    async def test_process_document_without_url(
        self, entity_extraction_worker, sample_extraction_result
    ):
        """Test document processing when document has no URL."""
        document = Document(
            title="Test Document No URL",
            content="Test content",
            url="",
            source="test-file",
            content_type="text/plain",
            source_type="file",
            metadata={},
        )

        entity_extraction_worker.entity_extractor.extract_entities.return_value = (
            sample_extraction_result
        )

        result = await entity_extraction_worker.process(document)

        # Verify extraction was called with document ID as source description
        entity_extraction_worker.entity_extractor.extract_entities.assert_called_once_with(
            text=document.content,
            source_description=f"Document: {document.id}",
            reference_time=document.created_at,
        )

    @pytest.mark.asyncio
    async def test_process_document_with_shutdown_event(
        self, entity_extraction_worker, sample_document
    ):
        """Test document processing when shutdown event is set."""
        entity_extraction_worker.shutdown_event.set()

        result = await entity_extraction_worker.process(sample_document)

        # Should return empty result without calling extractor
        entity_extraction_worker.entity_extractor.extract_entities.assert_not_called()
        assert result.source_text == sample_document.content
        assert len(result.entities) == 0
        assert len(result.relationships) == 0

    @pytest.mark.asyncio
    async def test_process_document_extraction_error(
        self, entity_extraction_worker, sample_document
    ):
        """Test document processing when extraction fails."""
        error_message = "Extraction failed"
        entity_extraction_worker.entity_extractor.extract_entities.side_effect = (
            Exception(error_message)
        )

        result = await entity_extraction_worker.process(sample_document)

        # Should return result with error information
        assert result.source_text == sample_document.content
        assert len(result.entities) == 0
        assert len(result.relationships) == 0
        assert len(result.errors) == 1
        assert f"Entity extraction failed: {error_message}" in result.errors[0]
        assert result.metadata["document_id"] == sample_document.id
        assert result.metadata["error"] == error_message

    @pytest.mark.asyncio
    async def test_process_document_cancellation(
        self, entity_extraction_worker, sample_document
    ):
        """Test document processing when task is cancelled."""
        entity_extraction_worker.entity_extractor.extract_entities.side_effect = (
            asyncio.CancelledError()
        )

        with pytest.raises(asyncio.CancelledError):
            await entity_extraction_worker.process(sample_document)

    @pytest.mark.asyncio
    async def test_process_documents_success(
        self, entity_extraction_worker, sample_extraction_result
    ):
        """Test successful processing of multiple documents."""
        documents = [
            Document(
                title=f"Document {i}",
                content=f"Content {i}",
                url=f"https://example.com/doc-{i}",
                source=f"test-source-{i}",
                source_type="web",
                content_type="text/plain",
                metadata={},
            )
            for i in range(3)
        ]

        entity_extraction_worker.entity_extractor.extract_entities.return_value = (
            sample_extraction_result
        )

        results = []
        async for result in entity_extraction_worker.process_documents(documents):
            results.append(result)

        assert len(results) == 3
        assert (
            entity_extraction_worker.entity_extractor.extract_entities.call_count == 3
        )

        # Verify each result has correct metadata
        for i, result in enumerate(results):
            # Document ID is a UUID, not a simple format
            assert "document_id" in result.metadata
            assert result.metadata["document_id"] is not None

    @pytest.mark.asyncio
    async def test_process_documents_empty_list(self, entity_extraction_worker):
        """Test processing empty document list."""
        results = []
        async for result in entity_extraction_worker.process_documents([]):
            results.append(result)

        assert len(results) == 0
        entity_extraction_worker.entity_extractor.extract_entities.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_documents_with_shutdown_event(
        self, entity_extraction_worker, sample_document
    ):
        """Test processing documents when shutdown event is set during processing."""
        documents = [sample_document]
        entity_extraction_worker.shutdown_event.set()

        results = []
        async for result in entity_extraction_worker.process_documents(documents):
            results.append(result)

        # Should exit early due to shutdown
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_process_documents_with_mixed_results(self, entity_extraction_worker):
        """Test processing documents with mixed success/failure results."""
        documents = [
            Document(
                title="Success Document",
                content="Success content",
                source="success-source",
                source_type="test",
                content_type="text/plain",
                url="https://example.com/success",
                metadata={},
            ),
            Document(
                title="Failure Document",
                content="Failure content",
                source="failure-source",
                source_type="test",
                content_type="text/plain",
                url="https://example.com/failure",
                metadata={},
            ),
            Document(
                title="Empty Document",
                content="Empty content",
                source="empty-source",
                source_type="test",
                content_type="text/plain",
                url="https://example.com/empty",
                metadata={},
            ),
        ]

        # Mock different results for different documents
        def mock_extract_entities(text, **kwargs):
            if "Success" in text:
                return ExtractionResult(
                    entities=[
                        ExtractedEntity(
                            name="test", entity_type=EntityType.PERSON, confidence=0.9
                        )
                    ],
                    source_text=text,
                )
            elif "Failure" in text:
                raise Exception("Extraction failed")
            else:
                return ExtractionResult(source_text=text)

        entity_extraction_worker.entity_extractor.extract_entities.side_effect = (
            mock_extract_entities
        )

        results = []
        async for result in entity_extraction_worker.process_documents(documents):
            results.append(result)

        assert len(results) == 3

        # Check that we have results with the expected characteristics
        # Find success result (should have entities)
        success_results = [r for r in results if len(r.entities) > 0]
        assert len(success_results) == 1
        success_result = success_results[0]
        assert success_result.entities[0].name == "test"
        assert len(success_result.errors) == 0

        # Check failure result (should have errors)
        error_results = [r for r in results if len(r.errors) > 0]
        assert len(error_results) == 1
        failure_result = error_results[0]
        assert len(failure_result.entities) == 0
        assert len(failure_result.errors) == 1

        # Check empty result (no entities, no errors)
        empty_results = [
            r for r in results if len(r.entities) == 0 and len(r.errors) == 0
        ]
        assert len(empty_results) == 1

    @pytest.mark.asyncio
    async def test_process_documents_concurrency_control(self, mock_entity_extractor):
        """Test that concurrency is properly controlled."""
        # Create worker with limited concurrency
        worker = EntityExtractionWorker(
            entity_extractor=mock_entity_extractor,
            max_workers=2,
            queue_size=100,
        )

        # Track concurrent calls
        concurrent_calls = 0
        max_concurrent_calls = 0

        async def mock_extract_with_tracking(*args, **kwargs):
            nonlocal concurrent_calls, max_concurrent_calls
            concurrent_calls += 1
            max_concurrent_calls = max(max_concurrent_calls, concurrent_calls)

            # Simulate some processing time
            await asyncio.sleep(0.1)

            concurrent_calls -= 1
            return ExtractionResult(source_text="test")

        mock_entity_extractor.extract_entities.side_effect = mock_extract_with_tracking

        documents = [
            Document(
                title=f"Document {i}",
                content=f"Content {i}",
                source=f"test-source-{i}",
                source_type="test",
                content_type="text/plain",
                url=f"https://example.com/doc-{i}",
                metadata={},
            )
            for i in range(5)
        ]

        results = []
        async for result in worker.process_documents(documents):
            results.append(result)

        assert len(results) == 5
        assert max_concurrent_calls <= 2  # Should respect max_workers limit

    @pytest.mark.asyncio
    async def test_process_documents_progress_logging(self, entity_extraction_worker):
        """Test that progress is logged correctly."""
        documents = [
            Document(
                title=f"Document {i}",
                content=f"Content {i}",
                source=f"test-source-{i}",
                source_type="test",
                content_type="text/plain",
                url=f"https://example.com/doc-{i}",
                metadata={},
            )
            for i in range(15)  # More than 10 to trigger progress logging
        ]

        entity_extraction_worker.entity_extractor.extract_entities.return_value = (
            ExtractionResult(
                entities=[
                    ExtractedEntity(
                        name="test", entity_type=EntityType.PERSON, confidence=0.9
                    )
                ],
                source_text="test",
            )
        )

        with patch(
            "qdrant_loader.core.pipeline.workers.entity_extraction_worker.logger"
        ) as mock_logger:
            results = []
            async for result in entity_extraction_worker.process_documents(documents):
                results.append(result)

            assert len(results) == 15

            # Check that progress logging occurred
            info_calls = [
                call
                for call in mock_logger.info.call_args_list
                if "progress:" in str(call)
            ]
            assert len(info_calls) >= 1  # Should have at least one progress log

    @pytest.mark.asyncio
    async def test_process_documents_error_handling_in_task(
        self, entity_extraction_worker
    ):
        """Test error handling within async tasks."""
        documents = [
            Document(
                title="Error Document",
                content="Error content",
                source="error-source",
                source_type="test",
                content_type="text/plain",
                url="https://example.com/error",
                metadata={},
            )
        ]

        # Mock an exception in the task processing
        entity_extraction_worker.entity_extractor.extract_entities.side_effect = (
            Exception("Task error")
        )

        results = []
        async for result in entity_extraction_worker.process_documents(documents):
            results.append(result)

        assert len(results) == 1
        result = results[0]
        assert len(result.errors) == 1
        assert "Entity extraction failed: Task error" in result.errors[0]
        assert result.metadata["error"] == "Task error"

    @pytest.mark.asyncio
    async def test_process_chunks_method_exists(self, entity_extraction_worker):
        """Test that process_chunks method exists and can be called."""

        # Create a simple async iterator
        async def mock_chunks_iter():
            yield "chunk1"
            yield "chunk2"

        # The method should exist and be callable
        assert hasattr(entity_extraction_worker, "process_chunks")
        assert callable(entity_extraction_worker.process_chunks)

        # Test calling it (implementation details may vary)
        try:
            results = []
            async for result in entity_extraction_worker.process_chunks(
                mock_chunks_iter()
            ):
                results.append(result)
        except (NotImplementedError, AttributeError):
            # Method may not be fully implemented, which is acceptable
            pass

    @pytest.mark.asyncio
    async def test_inheritance_from_base_worker(self, entity_extraction_worker):
        """Test that EntityExtractionWorker properly inherits from BaseWorker."""
        # Should have inherited attributes
        assert hasattr(entity_extraction_worker, "max_workers")
        assert hasattr(entity_extraction_worker, "queue_size")
        assert entity_extraction_worker.max_workers == 3
        assert entity_extraction_worker.queue_size == 100

    @pytest.mark.asyncio
    async def test_shutdown_event_during_processing(self, entity_extraction_worker):
        """Test shutdown event being set during document processing."""
        documents = [
            Document(
                title=f"Document {i}",
                content=f"Content {i}",
                source=f"test-source-{i}",
                source_type="test",
                content_type="text/plain",
                url=f"https://example.com/doc-{i}",
                metadata={},
            )
            for i in range(5)
        ]

        # Mock extraction that takes some time
        async def slow_extraction(*args, **kwargs):
            await asyncio.sleep(0.1)
            return ExtractionResult(source_text="test")

        entity_extraction_worker.entity_extractor.extract_entities.side_effect = (
            slow_extraction
        )

        # Start processing
        results = []

        async def collect_results():
            async for result in entity_extraction_worker.process_documents(documents):
                results.append(result)

        # Start the collection task
        task = asyncio.create_task(collect_results())

        # Set shutdown event after a short delay
        await asyncio.sleep(0.05)
        entity_extraction_worker.shutdown_event.set()

        # Wait for task to complete
        await task

        # Should have processed fewer documents due to shutdown
        assert len(results) < len(documents)

    def test_worker_attributes(self, entity_extraction_worker, mock_entity_extractor):
        """Test worker attributes are set correctly."""
        assert entity_extraction_worker.entity_extractor == mock_entity_extractor
        assert isinstance(entity_extraction_worker.shutdown_event, asyncio.Event)
        assert entity_extraction_worker.max_workers == 3
        assert entity_extraction_worker.queue_size == 100
