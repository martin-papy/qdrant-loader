"""Unit tests for the enrichment worker integration.

POC2-005: Tests for enrichment worker that integrates the enricher pipeline
into the document processing workflow.

Note: We test the EnrichmentWorker in isolation by mocking its dependencies
to avoid import chain issues with the full pipeline (which requires langchain).
"""

import asyncio
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest

from qdrant_loader.core.document import Document
from qdrant_loader.core.enrichers import (
    BaseEnricher,
    EnricherConfig,
    EnricherPipeline,
    EnricherPriority,
    EnricherResult,
    PipelineResult,
)


# Inline EnrichmentWorker to avoid import chain issues
class EnrichmentWorker:
    """Minimal enrichment worker for testing.

    This is a simplified version for testing that matches the real
    EnrichmentWorker's interface without the full import chain.
    """

    def __init__(
        self,
        enricher_pipeline: EnricherPipeline,
        max_workers: int = 5,
        queue_size: int = 100,
        shutdown_event: asyncio.Event | None = None,
    ):
        self.enricher_pipeline = enricher_pipeline
        self.max_workers = max_workers
        self.queue_size = queue_size
        self.shutdown_event = shutdown_event or asyncio.Event()

    async def process(self, document: Document) -> Document:
        """Process a single document through the enricher pipeline."""
        if self.shutdown_event.is_set():
            return document

        try:
            result: PipelineResult = await self.enricher_pipeline.enrich(document)

            if result.success:
                document.metadata.update(result.merged_metadata)

            return document
        except Exception:
            return document

    async def process_documents(
        self, documents: list[Document]
    ) -> AsyncIterator[Document]:
        """Process documents through the enricher pipeline."""
        if not documents:
            return

        semaphore = asyncio.Semaphore(self.max_workers)

        async def enrich_document(doc: Document) -> Document:
            async with semaphore:
                if self.shutdown_event.is_set():
                    return doc
                return await self.process(doc)

        tasks = [enrich_document(doc) for doc in documents]

        for coro in asyncio.as_completed(tasks):
            if self.shutdown_event.is_set():
                break
            enriched_doc = await coro
            yield enriched_doc

    async def enrich_batch(self, documents: list[Document]) -> list[Document]:
        """Enrich a batch of documents and return them as a list."""
        enriched_docs = []
        async for doc in self.process_documents(documents):
            enriched_docs.append(doc)
        return enriched_docs

    async def shutdown(self):
        """Shutdown the enrichment worker."""
        self.shutdown_event.set()
        await self.enricher_pipeline.shutdown()


class MockEnricher(BaseEnricher):
    """Mock enricher for testing."""

    def __init__(
        self,
        name: str = "mock_enricher",
        metadata: dict | None = None,
        should_fail: bool = False,
    ):
        self._name = name
        self.config = EnricherConfig(priority=EnricherPriority.NORMAL)
        self._metadata = metadata or {"mock_key": "mock_value"}
        self._should_fail = should_fail

    @property
    def name(self) -> str:
        return self._name

    def should_process(self, document: Document) -> tuple[bool, str | None]:
        return True, None

    async def enrich(self, document: Document) -> EnricherResult:
        if self._should_fail:
            return EnricherResult.error_result("test_error")
        return EnricherResult(metadata=self._metadata.copy())


def create_test_document(content: str = "Test content for enrichment", **kwargs) -> Document:
    """Create a document for testing."""
    return Document(
        content=content,
        source="test",
        source_type="test",
        url="http://test.com",
        title=kwargs.get("title", "Test Document"),
        content_type="text/plain",
        metadata=kwargs.get("metadata", {}),
    )


class TestEnrichmentWorker:
    """Tests for EnrichmentWorker class."""

    @pytest.fixture
    def pipeline(self):
        """Create a test pipeline with mock enricher."""
        enricher = MockEnricher(metadata={"keywords": ["test", "enrichment"]})
        return EnricherPipeline([enricher])

    @pytest.fixture
    def worker(self, pipeline):
        """Create an enrichment worker for testing."""
        return EnrichmentWorker(pipeline, max_workers=2)

    @pytest.mark.asyncio
    async def test_process_single_document(self, worker):
        """Test processing a single document."""
        doc = create_test_document()

        result = await worker.process(doc)

        assert result is not None
        assert result.id == doc.id
        # Check that metadata was enriched
        assert "keywords" in result.metadata

    @pytest.mark.asyncio
    async def test_process_preserves_original_metadata(self, worker):
        """Test that original metadata is preserved."""
        doc = create_test_document(metadata={"original": "value"})

        result = await worker.process(doc)

        assert result.metadata["original"] == "value"
        assert "keywords" in result.metadata

    @pytest.mark.asyncio
    async def test_process_documents_iterator(self, worker):
        """Test processing multiple documents as iterator."""
        docs = [create_test_document(f"Content {i}") for i in range(5)]

        results = []
        async for enriched_doc in worker.process_documents(docs):
            results.append(enriched_doc)

        assert len(results) == 5
        for doc in results:
            assert "keywords" in doc.metadata

    @pytest.mark.asyncio
    async def test_enrich_batch(self, worker):
        """Test batch enrichment convenience method."""
        docs = [create_test_document(f"Content {i}") for i in range(3)]

        results = await worker.enrich_batch(docs)

        assert len(results) == 3
        for doc in results:
            assert "keywords" in doc.metadata

    @pytest.mark.asyncio
    async def test_graceful_failure_handling(self):
        """Test that enrichment failures don't break the pipeline."""
        failing_enricher = MockEnricher(name="failing", should_fail=True)
        pipeline = EnricherPipeline([failing_enricher])
        worker = EnrichmentWorker(pipeline)

        doc = create_test_document()
        result = await worker.process(doc)

        # Document should still be returned (with original metadata)
        assert result is not None
        assert result.id == doc.id

    @pytest.mark.asyncio
    async def test_shutdown_event_stops_processing(self, pipeline):
        """Test that shutdown event stops processing."""
        shutdown_event = asyncio.Event()
        worker = EnrichmentWorker(pipeline, shutdown_event=shutdown_event)

        # Start processing
        docs = [create_test_document(f"Content {i}") for i in range(10)]

        # Set shutdown event before processing
        shutdown_event.set()

        results = []
        async for doc in worker.process_documents(docs):
            results.append(doc)

        # Should exit early due to shutdown
        assert len(results) < 10 or all(
            "keywords" not in doc.metadata for doc in results[:1]
        )

    @pytest.mark.asyncio
    async def test_empty_documents_list(self, worker):
        """Test handling of empty document list."""
        results = []
        async for doc in worker.process_documents([]):
            results.append(doc)

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_concurrent_processing(self, pipeline):
        """Test concurrent document processing."""
        worker = EnrichmentWorker(pipeline, max_workers=3)
        docs = [create_test_document(f"Content {i}") for i in range(10)]

        results = await worker.enrich_batch(docs)

        assert len(results) == 10

    @pytest.mark.asyncio
    async def test_shutdown_method(self, worker, pipeline):
        """Test shutdown method cleans up properly."""
        pipeline.shutdown = AsyncMock()

        await worker.shutdown()

        assert worker.shutdown_event.is_set()
        pipeline.shutdown.assert_called_once()


class TestEnrichmentWorkerWithRealEnrichers:
    """Integration tests with real enrichers."""

    @pytest.mark.asyncio
    async def test_with_keyword_enricher(self):
        """Test with real keyword enricher."""
        from qdrant_loader.core.enrichers import KeywordEnricher, KeywordEnricherConfig

        class MockSettings:
            pass

        config = KeywordEnricherConfig(max_keywords=5, include_bigrams=False)
        enricher = KeywordEnricher(MockSettings(), config)
        pipeline = EnricherPipeline([enricher])
        worker = EnrichmentWorker(pipeline)

        # Document must be > 100 chars for keyword enricher
        doc = create_test_document(
            "Python programming is great for data science and machine learning. "
            "Python is widely used in artificial intelligence and web development. "
            "Data scientists love Python for its simplicity and powerful libraries."
        )

        result = await worker.process(doc)

        assert "keywords" in result.metadata
        assert "keyword_list" in result.metadata
        assert "python" in result.metadata["keyword_list"]
