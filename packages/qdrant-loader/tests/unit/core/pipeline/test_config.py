"""Tests for PipelineConfig."""

from qdrant_loader.core.pipeline.config import PipelineConfig


class TestPipelineConfig:
    """Test cases for PipelineConfig."""

    def test_default_values(self):
        """Test that PipelineConfig has correct default values."""
        config = PipelineConfig()

        assert config.max_chunk_workers == 10
        assert config.max_embed_workers == 4
        assert config.max_upsert_workers == 4
        assert config.queue_size == 1000
        assert config.upsert_batch_size is None
        assert config.enable_metrics is False

    def test_custom_values(self):
        """Test that PipelineConfig accepts custom values."""
        config = PipelineConfig(
            max_chunk_workers=20,
            max_embed_workers=8,
            max_upsert_workers=6,
            queue_size=2000,
            upsert_batch_size=100,
            enable_metrics=True,
        )

        assert config.max_chunk_workers == 20
        assert config.max_embed_workers == 8
        assert config.max_upsert_workers == 6
        assert config.queue_size == 2000
        assert config.upsert_batch_size == 100
        assert config.enable_metrics is True
