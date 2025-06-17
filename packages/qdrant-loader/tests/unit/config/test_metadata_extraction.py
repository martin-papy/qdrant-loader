"""Unit tests for the metadata_extraction configuration module."""

import pytest
from pydantic import ValidationError
from typing import Any, cast

from qdrant_loader.config.metadata_extraction import (
    AuthorExtractionConfig,
    AuthorExtractionMethod,
    CrossReferenceExtractionConfig,
    ExtractionStrategy,
    MetadataExtractionConfig,
    PerformanceConfig,
    QualityConfig,
    RelationshipExtractionConfig,
    RelationshipExtractionMethod,
    SourceSpecificExtractionConfig,
    TimestampExtractionConfig,
    TimestampExtractionMethod,
)


# Test Enums
def test_extraction_strategy_enum():
    assert ExtractionStrategy.MINIMAL == "minimal"
    assert ExtractionStrategy.STANDARD == "standard"
    assert ExtractionStrategy.COMPREHENSIVE == "comprehensive"
    assert ExtractionStrategy.CUSTOM == "custom"


def test_author_extraction_method_enum():
    assert AuthorExtractionMethod.CONTENT_ANALYSIS == "content_analysis"
    assert AuthorExtractionMethod.SYSTEM_METADATA == "system_metadata"


def test_timestamp_extraction_method_enum():
    assert TimestampExtractionMethod.FILESYSTEM == "filesystem"
    assert TimestampExtractionMethod.CONTENT_PARSING == "content_parsing"


def test_relationship_extraction_method_enum():
    assert RelationshipExtractionMethod.CONTENT_LINKS == "content_links"
    assert RelationshipExtractionMethod.DIRECTORY_STRUCTURE == "directory_structure"


# Test Config Models
class TestAuthorExtractionConfig:
    def test_defaults(self):
        config = AuthorExtractionConfig()
        assert config.enabled is True
        assert config.methods == [AuthorExtractionMethod.HYBRID]

    def test_custom_values(self):
        config = AuthorExtractionConfig(
            enabled=False, methods=[AuthorExtractionMethod.SYSTEM_METADATA]
        )
        assert config.enabled is False
        assert config.methods == [AuthorExtractionMethod.SYSTEM_METADATA]


class TestTimestampExtractionConfig:
    def test_defaults(self):
        config = TimestampExtractionConfig()
        assert config.enabled is True
        assert config.methods == [TimestampExtractionMethod.HYBRID]
        assert config.normalize_to_utc is True

    def test_custom_values(self):
        config = TimestampExtractionConfig(
            enabled=False,
            methods=[TimestampExtractionMethod.FILESYSTEM],
            normalize_to_utc=False,
        )
        assert config.enabled is False
        assert config.methods == [TimestampExtractionMethod.FILESYSTEM]
        assert config.normalize_to_utc is False


class TestRelationshipExtractionConfig:
    def test_defaults(self):
        config = RelationshipExtractionConfig()
        assert config.enabled is True
        assert config.methods == [RelationshipExtractionMethod.HYBRID]

    def test_custom_values(self):
        config = RelationshipExtractionConfig(
            enabled=False, methods=[RelationshipExtractionMethod.CONTENT_LINKS]
        )
        assert config.enabled is False
        assert config.methods == [RelationshipExtractionMethod.CONTENT_LINKS]


class TestCrossReferenceExtractionConfig:
    def test_defaults(self):
        config = CrossReferenceExtractionConfig()
        assert config.enabled is True
        assert config.max_cross_references == 50

    def test_custom_values(self):
        config = CrossReferenceExtractionConfig(enabled=False, max_cross_references=10)
        assert config.enabled is False
        assert config.max_cross_references == 10


class TestSourceSpecificExtractionConfig:
    def test_defaults(self):
        config = SourceSpecificExtractionConfig()
        assert config.enabled is True
        assert config.git["extract_commit_info"] is True
        assert config.confluence["extract_labels"] is True

    def test_custom_values(self):
        config = SourceSpecificExtractionConfig(
            enabled=False,
            git={"extract_commit_info": False},
            confluence={"extract_labels": False},
        )
        assert config.enabled is False
        assert config.git["extract_commit_info"] is False
        assert (
            "extract_branch_info" not in config.git
        )  # Check that defaults are overwritten
        assert config.confluence["extract_labels"] is False


class TestPerformanceConfig:
    def test_defaults(self):
        config = PerformanceConfig()
        assert config.max_parallel_extractions == 4
        assert config.enable_caching is True

    def test_custom_values(self):
        config = PerformanceConfig(max_parallel_extractions=8, enable_caching=False)
        assert config.max_parallel_extractions == 8
        assert config.enable_caching is False


class TestQualityConfig:
    def test_defaults(self):
        config = QualityConfig()
        assert config.enable_validation is True
        assert config.minimum_quality_score == 0.6

    def test_custom_values(self):
        config = QualityConfig(enable_validation=False, minimum_quality_score=0.8)
        assert config.enable_validation is False
        assert config.minimum_quality_score == 0.8


class TestMetadataExtractionConfig:
    def test_defaults(self):
        config = MetadataExtractionConfig()
        assert config.enabled is True
        assert config.strategy == ExtractionStrategy.STANDARD
        assert isinstance(config.authors, AuthorExtractionConfig)
        assert isinstance(config.timestamps, TimestampExtractionConfig)
        assert isinstance(config.relationships, RelationshipExtractionConfig)
        assert isinstance(config.cross_references, CrossReferenceExtractionConfig)
        assert isinstance(config.source_specific, SourceSpecificExtractionConfig)
        assert isinstance(config.performance, PerformanceConfig)
        assert isinstance(config.quality, QualityConfig)

    def test_custom_values(self):
        config = MetadataExtractionConfig(
            enabled=False, strategy=ExtractionStrategy.COMPREHENSIVE
        )
        assert config.enabled is False
        assert config.strategy == ExtractionStrategy.COMPREHENSIVE

    def test_validation_error(self):
        with pytest.raises(ValidationError):
            # Use a dictionary and cast to bypass static type checking
            invalid_data = {"strategy": "invalid_strategy"}
            MetadataExtractionConfig(**cast(Any, invalid_data))

    def test_to_base_config(self):
        # This test may need adjustment based on the actual implementation
        # of to_base_config and the structure of the base config.
        config = MetadataExtractionConfig()
        base_config = config.to_base_config()
        assert isinstance(base_config, dict) is False
        assert hasattr(base_config, "enabled")
        assert base_config.enabled is True
