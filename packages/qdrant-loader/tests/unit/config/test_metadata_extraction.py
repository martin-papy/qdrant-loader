"""Unit tests for the metadata extraction configuration module."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from qdrant_loader.config.metadata_extraction import (
    ExtractionStrategy,
    AuthorExtractionMethod,
    TimestampExtractionMode,
    RelationshipType,
    ValidationLevel,
    ContentParsingMode,
    SecurityPattern,
    CrossReferenceConfig,
    AuthorExtractionConfig,
    TimestampExtractionConfig,
    RelationshipExtractionConfig,
    ContentParsingConfig,
    QualityControlConfig,
    PerformanceConfig,
    SourceSpecificConfig,
    GitSourceConfig,
    ConfluenceSourceConfig,
    JIRASourceConfig,
    LocalFileSourceConfig,
    PublicDocsSourceConfig,
    MetadataExtractionConfig,
)


class TestExtractionStrategy:
    """Test the ExtractionStrategy enum."""

    def test_strategy_values(self):
        """Test that all strategy values are correct."""
        assert ExtractionStrategy.MINIMAL == "minimal"
        assert ExtractionStrategy.STANDARD == "standard"
        assert ExtractionStrategy.COMPREHENSIVE == "comprehensive"
        assert ExtractionStrategy.CUSTOM == "custom"

    def test_strategy_membership(self):
        """Test that strategies can be compared."""
        strategies = [
            ExtractionStrategy.MINIMAL,
            ExtractionStrategy.STANDARD,
            ExtractionStrategy.COMPREHENSIVE,
            ExtractionStrategy.CUSTOM,
        ]
        assert len(strategies) == 4
        assert all(isinstance(s, str) for s in strategies)


class TestAuthorExtractionMethod:
    """Test the AuthorExtractionMethod enum."""

    def test_method_values(self):
        """Test that all method values are correct."""
        assert AuthorExtractionMethod.METADATA == "metadata"
        assert AuthorExtractionMethod.COMMIT_HISTORY == "commit_history"
        assert AuthorExtractionMethod.FILE_SYSTEM == "file_system"
        assert AuthorExtractionMethod.SEMANTIC_ANALYSIS == "semantic_analysis"
        assert AuthorExtractionMethod.API_USER_INFO == "api_user_info"


class TestTimestampExtractionMode:
    """Test the TimestampExtractionMode enum."""

    def test_mode_values(self):
        """Test that all mode values are correct."""
        assert TimestampExtractionMode.CREATED_ONLY == "created_only"
        assert TimestampExtractionMode.MODIFIED_ONLY == "modified_only"
        assert TimestampExtractionMode.BOTH == "both"
        assert TimestampExtractionMode.FULL_HISTORY == "full_history"


class TestRelationshipType:
    """Test the RelationshipType enum."""

    def test_relationship_values(self):
        """Test that all relationship type values are correct."""
        assert RelationshipType.PARENT_CHILD == "parent_child"
        assert RelationshipType.REFERENCES == "references"
        assert RelationshipType.LINKS_TO == "links_to"
        assert RelationshipType.MENTIONS == "mentions"
        assert RelationshipType.SIMILAR_TO == "similar_to"
        assert RelationshipType.DEPENDS_ON == "depends_on"


class TestValidationLevel:
    """Test the ValidationLevel enum."""

    def test_validation_values(self):
        """Test that all validation level values are correct."""
        assert ValidationLevel.NONE == "none"
        assert ValidationLevel.BASIC == "basic"
        assert ValidationLevel.STRICT == "strict"
        assert ValidationLevel.COMPREHENSIVE == "comprehensive"


class TestContentParsingMode:
    """Test the ContentParsingMode enum."""

    def test_parsing_values(self):
        """Test that all parsing mode values are correct."""
        assert ContentParsingMode.FULL_TEXT == "full_text"
        assert ContentParsingMode.SUMMARY_ONLY == "summary_only"
        assert ContentParsingMode.METADATA_ONLY == "metadata_only"
        assert ContentParsingMode.SELECTIVE == "selective"


class TestSecurityPattern:
    """Test the SecurityPattern enum."""

    def test_security_values(self):
        """Test that all security pattern values are correct."""
        assert SecurityPattern.PII_DETECTION == "pii_detection"
        assert SecurityPattern.CREDENTIAL_SCANNING == "credential_scanning"
        assert SecurityPattern.SENSITIVE_DATA_FILTERING == "sensitive_data_filtering"


class TestCrossReferenceConfig:
    """Test the CrossReferenceConfig class."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = CrossReferenceConfig()

        assert config.enabled is True
        assert config.max_depth == 3
        assert config.include_external_links is False
        assert config.resolve_relative_paths is True
        assert config.track_broken_links is True
        assert config.link_validation_timeout == 30.0

    def test_custom_values(self):
        """Test that custom values can be set."""
        config = CrossReferenceConfig(
            enabled=False,
            max_depth=5,
            include_external_links=True,
            resolve_relative_paths=False,
            track_broken_links=False,
            link_validation_timeout=60.0,
        )

        assert config.enabled is False
        assert config.max_depth == 5
        assert config.include_external_links is True
        assert config.resolve_relative_paths is False
        assert config.track_broken_links is False
        assert config.link_validation_timeout == 60.0


class TestAuthorExtractionConfig:
    """Test the AuthorExtractionConfig class."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = AuthorExtractionConfig()

        assert config.enabled is True
        assert config.methods == [AuthorExtractionMethod.METADATA]
        assert config.fallback_to_system_user is True
        assert config.normalize_names is True
        assert config.extract_email is True
        assert config.extract_full_name is True

    def test_custom_values(self):
        """Test that custom values can be set."""
        methods = [
            AuthorExtractionMethod.COMMIT_HISTORY,
            AuthorExtractionMethod.API_USER_INFO,
        ]
        config = AuthorExtractionConfig(
            enabled=False,
            methods=methods,
            fallback_to_system_user=False,
            normalize_names=False,
            extract_email=False,
            extract_full_name=False,
        )

        assert config.enabled is False
        assert config.methods == methods
        assert config.fallback_to_system_user is False
        assert config.normalize_names is False
        assert config.extract_email is False
        assert config.extract_full_name is False


class TestTimestampExtractionConfig:
    """Test the TimestampExtractionConfig class."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = TimestampExtractionConfig()

        assert config.enabled is True
        assert config.mode == TimestampExtractionMode.BOTH
        assert config.timezone_handling == "preserve"
        assert config.normalize_to_utc is True
        assert config.extract_precision == "seconds"

    def test_custom_values(self):
        """Test that custom values can be set."""
        config = TimestampExtractionConfig(
            enabled=False,
            mode=TimestampExtractionMode.CREATED_ONLY,
            timezone_handling="convert",
            normalize_to_utc=False,
            extract_precision="milliseconds",
        )

        assert config.enabled is False
        assert config.mode == TimestampExtractionMode.CREATED_ONLY
        assert config.timezone_handling == "convert"
        assert config.normalize_to_utc is False
        assert config.extract_precision == "milliseconds"


class TestRelationshipExtractionConfig:
    """Test the RelationshipExtractionConfig class."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = RelationshipExtractionConfig()

        assert config.enabled is True
        assert config.types == [
            RelationshipType.PARENT_CHILD,
            RelationshipType.REFERENCES,
        ]
        assert config.max_relationships_per_document == 100
        assert config.similarity_threshold == 0.7
        assert config.include_implicit_relationships is True

    def test_custom_values(self):
        """Test that custom values can be set."""
        types = [RelationshipType.LINKS_TO, RelationshipType.MENTIONS]
        config = RelationshipExtractionConfig(
            enabled=False,
            types=types,
            max_relationships_per_document=50,
            similarity_threshold=0.8,
            include_implicit_relationships=False,
        )

        assert config.enabled is False
        assert config.types == types
        assert config.max_relationships_per_document == 50
        assert config.similarity_threshold == 0.8
        assert config.include_implicit_relationships is False


class TestContentParsingConfig:
    """Test the ContentParsingConfig class."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = ContentParsingConfig()

        assert config.mode == ContentParsingMode.FULL_TEXT
        assert config.extract_tables is True
        assert config.extract_images is True
        assert config.extract_links is True
        assert config.preserve_formatting is True
        assert config.handle_embedded_content is True

    def test_custom_values(self):
        """Test that custom values can be set."""
        config = ContentParsingConfig(
            mode=ContentParsingMode.SUMMARY_ONLY,
            extract_tables=False,
            extract_images=False,
            extract_links=False,
            preserve_formatting=False,
            handle_embedded_content=False,
        )

        assert config.mode == ContentParsingMode.SUMMARY_ONLY
        assert config.extract_tables is False
        assert config.extract_images is False
        assert config.extract_links is False
        assert config.preserve_formatting is False
        assert config.handle_embedded_content is False


class TestQualityControlConfig:
    """Test the QualityControlConfig class."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = QualityControlConfig()

        assert config.enabled is True
        assert config.validation_level == ValidationLevel.BASIC
        assert config.require_minimum_metadata is True
        assert config.validate_data_integrity is True
        assert config.sanitize_extracted_data is True
        assert config.detect_anomalies is False

    def test_custom_values(self):
        """Test that custom values can be set."""
        config = QualityControlConfig(
            enabled=False,
            validation_level=ValidationLevel.COMPREHENSIVE,
            require_minimum_metadata=False,
            validate_data_integrity=False,
            sanitize_extracted_data=False,
            detect_anomalies=True,
        )

        assert config.enabled is False
        assert config.validation_level == ValidationLevel.COMPREHENSIVE
        assert config.require_minimum_metadata is False
        assert config.validate_data_integrity is False
        assert config.sanitize_extracted_data is False
        assert config.detect_anomalies is True


class TestPerformanceConfig:
    """Test the PerformanceConfig class."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = PerformanceConfig()

        assert config.max_concurrent_extractions == 5
        assert config.extraction_timeout == 300.0
        assert config.cache_extracted_metadata is True
        assert config.batch_size == 10
        assert config.memory_limit_mb == 512

    def test_custom_values(self):
        """Test that custom values can be set."""
        config = PerformanceConfig(
            max_concurrent_extractions=10,
            extraction_timeout=600.0,
            cache_extracted_metadata=False,
            batch_size=20,
            memory_limit_mb=1024,
        )

        assert config.max_concurrent_extractions == 10
        assert config.extraction_timeout == 600.0
        assert config.cache_extracted_metadata is False
        assert config.batch_size == 20
        assert config.memory_limit_mb == 1024


class TestSourceSpecificConfig:
    """Test the SourceSpecificConfig class."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = SourceSpecificConfig()

        assert isinstance(config.git, GitSourceConfig)
        assert isinstance(config.confluence, ConfluenceSourceConfig)
        assert isinstance(config.jira, JIRASourceConfig)
        assert isinstance(config.localfile, LocalFileSourceConfig)
        assert isinstance(config.publicdocs, PublicDocsSourceConfig)


class TestGitSourceConfig:
    """Test the GitSourceConfig class."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = GitSourceConfig()

        assert config.extract_commit_metadata is True
        assert config.extract_branch_info is True
        assert config.extract_diff_stats is False
        assert config.include_merge_commits is True
        assert config.max_commit_history == 1000

    def test_custom_values(self):
        """Test that custom values can be set."""
        config = GitSourceConfig(
            extract_commit_metadata=False,
            extract_branch_info=False,
            extract_diff_stats=True,
            include_merge_commits=False,
            max_commit_history=500,
        )

        assert config.extract_commit_metadata is False
        assert config.extract_branch_info is False
        assert config.extract_diff_stats is True
        assert config.include_merge_commits is False
        assert config.max_commit_history == 500


class TestConfluenceSourceConfig:
    """Test the ConfluenceSourceConfig class."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = ConfluenceSourceConfig()

        assert config.extract_page_hierarchy is True
        assert config.extract_attachments is True
        assert config.extract_comments is False
        assert config.extract_page_restrictions is True
        assert config.extract_labels is True

    def test_custom_values(self):
        """Test that custom values can be set."""
        config = ConfluenceSourceConfig(
            extract_page_hierarchy=False,
            extract_attachments=False,
            extract_comments=True,
            extract_page_restrictions=False,
            extract_labels=False,
        )

        assert config.extract_page_hierarchy is False
        assert config.extract_attachments is False
        assert config.extract_comments is True
        assert config.extract_page_restrictions is False
        assert config.extract_labels is False


class TestJIRASourceConfig:
    """Test the JIRASourceConfig class."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = JIRASourceConfig()

        assert config.extract_issue_links is True
        assert config.extract_comments is True
        assert config.extract_attachments is True
        assert config.extract_workflow_history is False
        assert config.extract_custom_fields is True

    def test_custom_values(self):
        """Test that custom values can be set."""
        config = JIRASourceConfig(
            extract_issue_links=False,
            extract_comments=False,
            extract_attachments=False,
            extract_workflow_history=True,
            extract_custom_fields=False,
        )

        assert config.extract_issue_links is False
        assert config.extract_comments is False
        assert config.extract_attachments is False
        assert config.extract_workflow_history is True
        assert config.extract_custom_fields is False


class TestLocalFileSourceConfig:
    """Test the LocalFileSourceConfig class."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = LocalFileSourceConfig()

        assert config.extract_file_permissions is True
        assert config.extract_extended_attributes is False
        assert config.extract_file_hashes is False
        assert config.follow_symlinks is False
        assert config.scan_hidden_files is False

    def test_custom_values(self):
        """Test that custom values can be set."""
        config = LocalFileSourceConfig(
            extract_file_permissions=False,
            extract_extended_attributes=True,
            extract_file_hashes=True,
            follow_symlinks=True,
            scan_hidden_files=True,
        )

        assert config.extract_file_permissions is False
        assert config.extract_extended_attributes is True
        assert config.extract_file_hashes is True
        assert config.follow_symlinks is True
        assert config.scan_hidden_files is True


class TestPublicDocsSourceConfig:
    """Test the PublicDocsSourceConfig class."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = PublicDocsSourceConfig()

        assert config.extract_web_metadata is True
        assert config.extract_social_tags is False
        assert config.extract_page_structure is True
        assert config.follow_redirects is True
        assert config.respect_robots_txt is True

    def test_custom_values(self):
        """Test that custom values can be set."""
        config = PublicDocsSourceConfig(
            extract_web_metadata=False,
            extract_social_tags=True,
            extract_page_structure=False,
            follow_redirects=False,
            respect_robots_txt=False,
        )

        assert config.extract_web_metadata is False
        assert config.extract_social_tags is True
        assert config.extract_page_structure is False
        assert config.follow_redirects is False
        assert config.respect_robots_txt is False


class TestMetadataExtractionConfig:
    """Test the main MetadataExtractionConfig class."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = MetadataExtractionConfig()

        assert config.strategy == ExtractionStrategy.STANDARD
        assert config.enabled is True
        assert isinstance(config.cross_references, CrossReferenceConfig)
        assert isinstance(config.authors, AuthorExtractionConfig)
        assert isinstance(config.timestamps, TimestampExtractionConfig)
        assert isinstance(config.relationships, RelationshipExtractionConfig)
        assert isinstance(config.content_parsing, ContentParsingConfig)
        assert isinstance(config.quality_control, QualityControlConfig)
        assert isinstance(config.performance, PerformanceConfig)
        assert isinstance(config.source_specific, SourceSpecificConfig)
        assert config.security_patterns == [SecurityPattern.PII_DETECTION]

    def test_custom_values(self):
        """Test that custom values can be set."""
        cross_ref = CrossReferenceConfig(enabled=False)
        authors = AuthorExtractionConfig(enabled=False)
        timestamps = TimestampExtractionConfig(enabled=False)
        relationships = RelationshipExtractionConfig(enabled=False)
        content_parsing = ContentParsingConfig(mode=ContentParsingMode.METADATA_ONLY)
        quality_control = QualityControlConfig(enabled=False)
        performance = PerformanceConfig(max_concurrent_extractions=1)
        source_specific = SourceSpecificConfig()
        security_patterns = [SecurityPattern.CREDENTIAL_SCANNING]

        config = MetadataExtractionConfig(
            strategy=ExtractionStrategy.MINIMAL,
            enabled=False,
            cross_references=cross_ref,
            authors=authors,
            timestamps=timestamps,
            relationships=relationships,
            content_parsing=content_parsing,
            quality_control=quality_control,
            performance=performance,
            source_specific=source_specific,
            security_patterns=security_patterns,
        )

        assert config.strategy == ExtractionStrategy.MINIMAL
        assert config.enabled is False
        assert config.cross_references == cross_ref
        assert config.authors == authors
        assert config.timestamps == timestamps
        assert config.relationships == relationships
        assert config.content_parsing == content_parsing
        assert config.quality_control == quality_control
        assert config.performance == performance
        assert config.source_specific == source_specific
        assert config.security_patterns == security_patterns

    @patch("qdrant_loader.connectors.metadata.base.MetadataExtractionConfig")
    def test_to_base_config(self, mock_base_config):
        """Test the to_base_config method."""
        mock_base_instance = MagicMock()
        mock_base_config.return_value = mock_base_instance

        config = MetadataExtractionConfig()
        result = config.to_base_config()

        # Verify that the base config constructor was called with correct parameters
        mock_base_config.assert_called_once_with(
            extract_authors=config.authors.enabled,
            extract_timestamps=config.timestamps.enabled,
            extract_relationships=config.relationships.enabled,
            extract_content_metadata=True,
            max_relationships=config.relationships.max_relationships_per_document,
            similarity_threshold=config.relationships.similarity_threshold,
            enable_caching=config.performance.cache_extracted_metadata,
            extraction_timeout=config.performance.extraction_timeout,
        )

        assert result == mock_base_instance

    def test_to_base_config_disabled_authors(self):
        """Test to_base_config when authors are disabled."""
        config = MetadataExtractionConfig()
        config.authors.enabled = False

        with patch(
            "qdrant_loader.connectors.metadata.base.MetadataExtractionConfig"
        ) as mock_base_config:
            mock_base_instance = MagicMock()
            mock_base_config.return_value = mock_base_instance

            result = config.to_base_config()

            # Check that extract_authors is False
            call_args = mock_base_config.call_args[1]
            assert call_args["extract_authors"] is False

    def test_to_base_config_disabled_timestamps(self):
        """Test to_base_config when timestamps are disabled."""
        config = MetadataExtractionConfig()
        config.timestamps.enabled = False

        with patch(
            "qdrant_loader.connectors.metadata.base.MetadataExtractionConfig"
        ) as mock_base_config:
            mock_base_instance = MagicMock()
            mock_base_config.return_value = mock_base_instance

            result = config.to_base_config()

            # Check that extract_timestamps is False
            call_args = mock_base_config.call_args[1]
            assert call_args["extract_timestamps"] is False

    def test_to_base_config_disabled_relationships(self):
        """Test to_base_config when relationships are disabled."""
        config = MetadataExtractionConfig()
        config.relationships.enabled = False

        with patch(
            "qdrant_loader.connectors.metadata.base.MetadataExtractionConfig"
        ) as mock_base_config:
            mock_base_instance = MagicMock()
            mock_base_config.return_value = mock_base_instance

            result = config.to_base_config()

            # Check that extract_relationships is False
            call_args = mock_base_config.call_args[1]
            assert call_args["extract_relationships"] is False

    def test_minimal_strategy_defaults(self):
        """Test that minimal strategy sets appropriate defaults."""
        config = MetadataExtractionConfig(strategy=ExtractionStrategy.MINIMAL)

        # Should still have the same default values unless explicitly overridden
        assert config.strategy == ExtractionStrategy.MINIMAL
        assert config.enabled is True

    def test_comprehensive_strategy_defaults(self):
        """Test that comprehensive strategy sets appropriate defaults."""
        config = MetadataExtractionConfig(strategy=ExtractionStrategy.COMPREHENSIVE)

        assert config.strategy == ExtractionStrategy.COMPREHENSIVE
        assert config.enabled is True

    def test_custom_strategy_defaults(self):
        """Test that custom strategy sets appropriate defaults."""
        config = MetadataExtractionConfig(strategy=ExtractionStrategy.CUSTOM)

        assert config.strategy == ExtractionStrategy.CUSTOM
        assert config.enabled is True

    def test_pydantic_validation(self):
        """Test that Pydantic validation works correctly."""
        # Test that invalid enum values raise ValidationError
        with pytest.raises(ValueError):
            MetadataExtractionConfig(strategy="invalid_strategy")

    def test_nested_config_modification(self):
        """Test that nested configs can be modified independently."""
        config = MetadataExtractionConfig()

        # Modify nested configuration
        config.authors.enabled = False
        config.performance.max_concurrent_extractions = 20
        config.source_specific.git.extract_commit_metadata = False

        assert config.authors.enabled is False
        assert config.performance.max_concurrent_extractions == 20
        assert config.source_specific.git.extract_commit_metadata is False

        # Other configs should remain unchanged
        assert config.timestamps.enabled is True
        assert config.relationships.enabled is True
