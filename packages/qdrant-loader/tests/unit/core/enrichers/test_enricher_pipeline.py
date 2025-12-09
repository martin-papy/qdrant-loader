"""Unit tests for the pluggable enricher pipeline.

POC2-006: Tests for the enricher system implementing LlamaIndex pattern.
"""

import asyncio
from unittest.mock import MagicMock, AsyncMock

import pytest

from qdrant_loader.core.enrichers import (
    BaseEnricher,
    EnricherConfig,
    EnricherPipeline,
    EnricherPriority,
    EnricherResult,
    PipelineResult,
)
from qdrant_loader.core.document import Document


class MockEnricher(BaseEnricher):
    """Mock enricher for testing."""

    def __init__(
        self,
        name: str = "mock_enricher",
        priority: EnricherPriority = EnricherPriority.NORMAL,
        metadata: dict | None = None,
        should_fail: bool = False,
        should_skip: bool = False,
    ):
        # Don't call super().__init__ since we're mocking settings
        self._name = name
        self.config = EnricherConfig(priority=priority)
        self._metadata = metadata or {"mock_key": "mock_value"}
        self._should_fail = should_fail
        self._should_skip = should_skip
        self.call_count = 0

    @property
    def name(self) -> str:
        return self._name

    def should_process(self, document: Document) -> tuple[bool, str | None]:
        if self._should_skip:
            return False, "test_skip"
        return True, None

    async def enrich(self, document: Document) -> EnricherResult:
        self.call_count += 1
        if self._should_fail:
            return EnricherResult.error_result("test_error")
        return EnricherResult(metadata=self._metadata.copy())


def create_test_document(content: str = "Test content", **kwargs) -> Document:
    """Create a document for testing."""
    return Document(
        content=content,
        source="test",
        source_type="test",
        url="http://test.com",
        title="Test Document",
        content_type="text/plain",
        metadata=kwargs.get("metadata", {}),
    )


class TestEnricherResult:
    """Tests for EnricherResult dataclass."""

    def test_default_values(self):
        """Test default result values."""
        result = EnricherResult()
        assert result.success is True
        assert result.metadata == {}
        assert result.errors == []
        assert result.skipped is False
        assert result.skip_reason is None

    def test_skipped_result(self):
        """Test creating a skipped result."""
        result = EnricherResult.skipped_result("too_large")
        assert result.success is True
        assert result.skipped is True
        assert result.skip_reason == "too_large"

    def test_error_result(self):
        """Test creating an error result."""
        result = EnricherResult.error_result("something went wrong")
        assert result.success is False
        assert "something went wrong" in result.errors


class TestEnricherConfig:
    """Tests for EnricherConfig dataclass."""

    def test_default_values(self):
        """Test default config values."""
        config = EnricherConfig()
        assert config.enabled is True
        assert config.priority == EnricherPriority.NORMAL
        assert config.max_content_length == 100_000
        assert config.timeout_seconds == 30.0


class TestEnricherPipeline:
    """Tests for EnricherPipeline class."""

    def test_empty_pipeline(self):
        """Test pipeline with no enrichers."""
        pipeline = EnricherPipeline()
        assert len(pipeline.enrichers) == 0

    def test_add_enricher(self):
        """Test adding enrichers to pipeline."""
        pipeline = EnricherPipeline()
        enricher = MockEnricher(name="test")
        pipeline.add_enricher(enricher)
        assert len(pipeline.enrichers) == 1
        assert pipeline.enrichers[0].name == "test"

    def test_add_enricher_chaining(self):
        """Test method chaining when adding enrichers."""
        pipeline = EnricherPipeline()
        result = pipeline.add_enricher(MockEnricher(name="a")).add_enricher(MockEnricher(name="b"))
        assert result is pipeline
        assert len(pipeline.enrichers) == 2

    def test_remove_enricher(self):
        """Test removing enricher by name."""
        pipeline = EnricherPipeline([
            MockEnricher(name="keep"),
            MockEnricher(name="remove"),
        ])
        pipeline.remove_enricher("remove")
        assert len(pipeline.enrichers) == 1
        assert pipeline.enrichers[0].name == "keep"

    def test_get_enricher(self):
        """Test getting enricher by name."""
        enricher = MockEnricher(name="target")
        pipeline = EnricherPipeline([enricher])

        found = pipeline.get_enricher("target")
        assert found is enricher

        not_found = pipeline.get_enricher("nonexistent")
        assert not_found is None

    def test_duplicate_enricher_replacement(self):
        """Test that adding enricher with same name replaces existing."""
        pipeline = EnricherPipeline([MockEnricher(name="dup", metadata={"v": 1})])
        pipeline.add_enricher(MockEnricher(name="dup", metadata={"v": 2}))
        assert len(pipeline.enrichers) == 1

    def test_priority_ordering(self):
        """Test that enrichers are sorted by priority."""
        low = MockEnricher(name="low", priority=EnricherPriority.LOW)
        high = MockEnricher(name="high", priority=EnricherPriority.HIGH)
        normal = MockEnricher(name="normal", priority=EnricherPriority.NORMAL)

        pipeline = EnricherPipeline([low, normal, high])
        names = [e.name for e in pipeline.enrichers]
        assert names == ["high", "normal", "low"]

    @pytest.mark.asyncio
    async def test_enrich_single_document(self):
        """Test enriching a single document."""
        enricher = MockEnricher(metadata={"extracted": "value"})
        pipeline = EnricherPipeline([enricher])
        document = create_test_document()

        result = await pipeline.enrich(document)

        assert result.success is True
        assert result.merged_metadata == {"extracted": "value"}
        assert enricher.call_count == 1

    @pytest.mark.asyncio
    async def test_enrich_multiple_enrichers(self):
        """Test running multiple enrichers."""
        enricher1 = MockEnricher(name="e1", metadata={"key1": "val1"})
        enricher2 = MockEnricher(name="e2", metadata={"key2": "val2"})
        pipeline = EnricherPipeline([enricher1, enricher2])
        document = create_test_document()

        result = await pipeline.enrich(document)

        assert result.success is True
        assert result.merged_metadata == {"key1": "val1", "key2": "val2"}
        assert enricher1.call_count == 1
        assert enricher2.call_count == 1

    @pytest.mark.asyncio
    async def test_enrich_with_skipped_enricher(self):
        """Test that skipped enrichers don't affect results."""
        active = MockEnricher(name="active", metadata={"active": True})
        skipped = MockEnricher(name="skipped", should_skip=True)
        pipeline = EnricherPipeline([active, skipped])
        document = create_test_document()

        result = await pipeline.enrich(document)

        assert "skipped" in result.get_skipped_enrichers()
        assert "active" in result.get_successful_enrichers()
        assert result.merged_metadata == {"active": True}

    @pytest.mark.asyncio
    async def test_enrich_with_failed_enricher(self):
        """Test handling of failed enrichers."""
        success = MockEnricher(name="success", metadata={"ok": True})
        failure = MockEnricher(name="failure", should_fail=True)
        pipeline = EnricherPipeline([success, failure])
        document = create_test_document()

        result = await pipeline.enrich(document)

        assert "failure" in result.get_failed_enrichers()
        assert "success" in result.get_successful_enrichers()
        assert "test_error" in result.errors[0]

    @pytest.mark.asyncio
    async def test_stop_on_error(self):
        """Test stop_on_error mode."""
        first = MockEnricher(name="first", priority=EnricherPriority.HIGH, metadata={"first": True})
        failure = MockEnricher(name="failure", priority=EnricherPriority.NORMAL, should_fail=True)
        last = MockEnricher(name="last", priority=EnricherPriority.LOW, metadata={"last": True})

        pipeline = EnricherPipeline([first, failure, last], stop_on_error=True)
        document = create_test_document()

        result = await pipeline.enrich(document)

        assert result.success is False
        assert first.call_count == 1
        assert last.call_count == 0  # Should not be called due to stop_on_error

    @pytest.mark.asyncio
    async def test_enrich_batch(self):
        """Test batch enrichment."""
        enricher = MockEnricher(metadata={"batch": True})
        pipeline = EnricherPipeline([enricher])
        documents = [create_test_document(f"Doc {i}") for i in range(5)]

        results = await pipeline.enrich_batch(documents)

        assert len(results) == 5
        assert all(r.success for r in results)
        assert enricher.call_count == 5

    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        """Test parallel enricher execution."""
        # Create enrichers with same priority to run in parallel
        e1 = MockEnricher(name="e1", priority=EnricherPriority.NORMAL, metadata={"e1": True})
        e2 = MockEnricher(name="e2", priority=EnricherPriority.NORMAL, metadata={"e2": True})

        pipeline = EnricherPipeline([e1, e2], parallel=True)
        document = create_test_document()

        result = await pipeline.enrich(document)

        assert result.success is True
        assert result.merged_metadata == {"e1": True, "e2": True}

    @pytest.mark.asyncio
    async def test_pipeline_shutdown(self):
        """Test pipeline shutdown cleans up enrichers."""
        enricher = MockEnricher()
        enricher.shutdown = AsyncMock()
        pipeline = EnricherPipeline([enricher])

        await pipeline.shutdown()

        enricher.shutdown.assert_called_once()

    def test_pipeline_repr(self):
        """Test pipeline string representation."""
        pipeline = EnricherPipeline([
            MockEnricher(name="a"),
            MockEnricher(name="b"),
        ])
        repr_str = repr(pipeline)
        assert "a" in repr_str
        assert "b" in repr_str


class TestPipelineResult:
    """Tests for PipelineResult dataclass."""

    def test_get_successful_enrichers(self):
        """Test getting successful enricher names."""
        result = PipelineResult(
            enricher_results={
                "success": EnricherResult(success=True),
                "failed": EnricherResult(success=False),
                "skipped": EnricherResult(success=True, skipped=True),
            }
        )

        successful = result.get_successful_enrichers()
        assert successful == ["success"]

    def test_get_skipped_enrichers(self):
        """Test getting skipped enricher names."""
        result = PipelineResult(
            enricher_results={
                "success": EnricherResult(success=True),
                "skipped": EnricherResult(success=True, skipped=True),
            }
        )

        skipped = result.get_skipped_enrichers()
        assert skipped == ["skipped"]

    def test_get_failed_enrichers(self):
        """Test getting failed enricher names."""
        result = PipelineResult(
            enricher_results={
                "success": EnricherResult(success=True),
                "failed": EnricherResult(success=False),
            }
        )

        failed = result.get_failed_enrichers()
        assert failed == ["failed"]
