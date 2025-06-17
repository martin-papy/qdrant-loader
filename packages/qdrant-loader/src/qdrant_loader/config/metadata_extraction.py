"""Comprehensive metadata extraction configuration.

This module provides detailed configuration options for metadata extraction
across all data source connectors, extending the base metadata extraction
framework with advanced settings.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from qdrant_loader.config.base import BaseConfig


class ExtractionStrategy(str, Enum):
    """Strategies for metadata extraction."""

    MINIMAL = "minimal"  # Extract only essential metadata
    STANDARD = "standard"  # Extract common metadata types
    COMPREHENSIVE = "comprehensive"  # Extract all available metadata
    CUSTOM = "custom"  # Use custom configuration


class AuthorExtractionMethod(str, Enum):
    """Methods for extracting author metadata."""

    CONTENT_ANALYSIS = "content_analysis"  # Analyze content for author information
    SYSTEM_METADATA = "system_metadata"  # Use system-provided metadata
    VERSION_CONTROL = "version_control"  # Extract from version control systems
    API_ATTRIBUTES = "api_attributes"  # Use API-provided attributes
    HYBRID = "hybrid"  # Combine multiple methods


class TimestampExtractionMethod(str, Enum):
    """Methods for extracting timestamp metadata."""

    FILESYSTEM = "filesystem"  # Use filesystem timestamps
    CONTENT_PARSING = "content_parsing"  # Parse timestamps from content
    API_METADATA = "api_metadata"  # Use API-provided timestamps
    VERSION_HISTORY = "version_history"  # Extract from version history
    HYBRID = "hybrid"  # Combine multiple methods


class RelationshipExtractionMethod(str, Enum):
    """Methods for extracting relationship metadata."""

    CONTENT_LINKS = "content_links"  # Extract links from content
    DIRECTORY_STRUCTURE = "directory_structure"  # Use directory hierarchy
    API_RELATIONSHIPS = "api_relationships"  # Use API-provided relationships
    SEMANTIC_ANALYSIS = "semantic_analysis"  # Analyze semantic relationships
    CROSS_REFERENCE = "cross_reference"  # Extract cross-references
    HYBRID = "hybrid"  # Combine multiple methods


class AuthorExtractionConfig(BaseModel):
    """Configuration for author metadata extraction."""

    enabled: bool = Field(default=True, description="Enable author extraction")

    methods: List[AuthorExtractionMethod] = Field(
        default=[AuthorExtractionMethod.HYBRID],
        description="Methods to use for author extraction",
    )

    extract_display_names: bool = Field(
        default=True, description="Extract author display names"
    )

    extract_email_addresses: bool = Field(
        default=True, description="Extract author email addresses"
    )

    extract_usernames: bool = Field(
        default=True, description="Extract author usernames/handles"
    )

    extract_roles: bool = Field(
        default=True, description="Extract author roles (creator, editor, etc.)"
    )

    extract_avatars: bool = Field(
        default=False, description="Extract author avatar URLs"
    )

    extract_profiles: bool = Field(
        default=False, description="Extract author profile URLs"
    )

    # Content analysis settings
    content_analysis: Dict[str, Any] = Field(
        default_factory=lambda: {
            "search_patterns": [
                r"(?i)author[:\s]+([^\n\r]+)",
                r"(?i)by[:\s]+([^\n\r]+)",
                r"(?i)created by[:\s]+([^\n\r]+)",
                r"(?i)written by[:\s]+([^\n\r]+)",
            ],
            "exclude_patterns": [r"(?i)system", r"(?i)automated", r"(?i)unknown"],
            "confidence_threshold": 0.7,
        },
        description="Content analysis settings for author extraction",
    )

    # Deduplication and normalization
    deduplicate_authors: bool = Field(
        default=True, description="Remove duplicate author entries"
    )

    normalize_names: bool = Field(
        default=True, description="Normalize author names (case, whitespace)"
    )

    merge_similar_authors: bool = Field(
        default=True, description="Merge authors with similar names/emails"
    )

    similarity_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Threshold for merging similar authors",
    )


class TimestampExtractionConfig(BaseModel):
    """Configuration for timestamp metadata extraction."""

    enabled: bool = Field(default=True, description="Enable timestamp extraction")

    methods: List[TimestampExtractionMethod] = Field(
        default=[TimestampExtractionMethod.HYBRID],
        description="Methods to use for timestamp extraction",
    )

    extract_created: bool = Field(
        default=True, description="Extract creation timestamps"
    )

    extract_modified: bool = Field(
        default=True, description="Extract modification timestamps"
    )

    extract_published: bool = Field(
        default=True, description="Extract publication timestamps"
    )

    extract_accessed: bool = Field(
        default=False, description="Extract access timestamps"
    )

    extract_archived: bool = Field(
        default=False, description="Extract archive timestamps"
    )

    extract_versions: bool = Field(
        default=True, description="Extract version information"
    )

    # Content parsing settings
    content_parsing: Dict[str, Any] = Field(
        default_factory=lambda: {
            "date_patterns": [
                r"(?i)date[:\s]+(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
                r"(?i)created[:\s]+(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
                r"(?i)modified[:\s]+(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
                r"(?i)published[:\s]+(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
            ],
            "time_patterns": [
                r"(\d{1,2}:\d{2}(?::\d{2})?)",
                r"(\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM))",
            ],
            "timezone_patterns": [r"(UTC[+-]\d{1,2})", r"([A-Z]{3,4})"],
        },
        description="Content parsing settings for timestamp extraction",
    )

    # Timezone handling
    default_timezone: Optional[str] = Field(
        default="UTC",
        description="Default timezone for timestamps without timezone info",
    )

    normalize_to_utc: bool = Field(
        default=True, description="Normalize all timestamps to UTC"
    )


class RelationshipExtractionConfig(BaseModel):
    """Configuration for relationship metadata extraction."""

    enabled: bool = Field(default=True, description="Enable relationship extraction")

    methods: List[RelationshipExtractionMethod] = Field(
        default=[RelationshipExtractionMethod.HYBRID],
        description="Methods to use for relationship extraction",
    )

    max_relationships: int = Field(
        default=100, description="Maximum number of relationships to extract"
    )

    # Specific relationship types
    extract_hierarchical: bool = Field(
        default=True, description="Extract hierarchical relationships (parent/child)"
    )

    extract_dependencies: bool = Field(
        default=True, description="Extract dependency relationships"
    )

    extract_references: bool = Field(
        default=True, description="Extract reference relationships"
    )

    extract_similarities: bool = Field(
        default=False, description="Extract similarity relationships"
    )

    extract_sequences: bool = Field(
        default=True, description="Extract sequence relationships"
    )

    # Content link analysis
    content_links: Dict[str, Any] = Field(
        default_factory=lambda: {
            "extract_internal_links": True,
            "extract_external_links": False,
            "extract_anchor_text": True,
            "resolve_relative_links": True,
            "include_fragment_links": False,
            "link_patterns": [
                r"\[([^\]]+)\]\(([^)]+)\)",  # Markdown links
                r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>([^<]+)</a>",  # HTML links
                r"href=[\"']([^\"']+)[\"']",  # Generic href attributes
            ],
        },
        description="Content link analysis settings",
    )

    # Directory structure analysis
    directory_structure: Dict[str, Any] = Field(
        default_factory=lambda: {
            "max_depth": 10,
            "include_parent_child": True,
            "include_sibling": False,
            "include_ancestor": True,
            "weight_by_depth": True,
            "depth_weight_factor": 0.8,
        },
        description="Directory structure analysis settings",
    )

    # Semantic analysis settings
    semantic_analysis: Dict[str, Any] = Field(
        default_factory=lambda: {
            "enabled": False,
            "similarity_threshold": 0.7,
            "max_comparisons": 1000,
            "use_embeddings": True,
            "embedding_model": "text-embedding-3-small",
            "content_similarity_weight": 0.6,
            "title_similarity_weight": 0.4,
        },
        description="Semantic analysis settings",
    )

    # Relationship scoring and filtering
    minimum_confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score for relationships",
    )

    deduplicate_relationships: bool = Field(
        default=True, description="Remove duplicate relationships"
    )

    bidirectional_relationships: bool = Field(
        default=False, description="Create bidirectional relationships by default"
    )


class CrossReferenceExtractionConfig(BaseModel):
    """Configuration for cross-reference metadata extraction."""

    enabled: bool = Field(default=True, description="Enable cross-reference extraction")

    max_cross_references: int = Field(
        default=50, description="Maximum number of cross-references to extract"
    )

    # Cross-reference types
    extract_links: bool = Field(default=True, description="Extract link references")

    extract_mentions: bool = Field(
        default=True, description="Extract mention references"
    )

    extract_citations: bool = Field(
        default=True, description="Extract citation references"
    )

    extract_attachments: bool = Field(
        default=True, description="Extract attachment references"
    )

    extract_embeds: bool = Field(default=True, description="Extract embed references")

    extract_includes: bool = Field(
        default=True, description="Extract include references"
    )

    extract_imports: bool = Field(default=True, description="Extract import references")

    # Reference resolution
    resolve_references: bool = Field(
        default=True, description="Attempt to resolve reference targets"
    )

    resolution_timeout: int = Field(
        default=5, description="Timeout for reference resolution (seconds)"
    )

    include_external_references: bool = Field(
        default=False, description="Include references to external resources"
    )

    # Pattern matching
    mention_patterns: List[str] = Field(
        default_factory=lambda: [
            r"@([a-zA-Z0-9_-]+)",  # @mentions
            r"#([a-zA-Z0-9_-]+)",  # #hashtags
            r"\b([A-Z][A-Z0-9_]+-\d+)\b",  # Issue/ticket references
            r"\b(RFC\s*\d+)\b",  # RFC references
            r"\b(DOC-\d+)\b",  # Document references
        ],
        description="Patterns for detecting mentions",
    )

    citation_patterns: List[str] = Field(
        default_factory=lambda: [
            r"\[(\d+)\]",  # Numbered citations
            r"\[([^\]]+,\s*\d{4})\]",  # Author, year citations
            r"\(([^\)]+,\s*\d{4})\)",  # Parenthetical citations
            r"(?i)see\s+([^\n\r.]+)",  # "See also" references
            r"(?i)ref(?:erence)?[:\s]+([^\n\r.]+)",  # Reference indicators
        ],
        description="Patterns for detecting citations",
    )


class SourceSpecificExtractionConfig(BaseModel):
    """Configuration for source-specific metadata extraction."""

    enabled: bool = Field(default=True, description="Enable source-specific extraction")

    # Git-specific settings
    git: Dict[str, Any] = Field(
        default_factory=lambda: {
            "extract_commit_info": True,
            "extract_branch_info": True,
            "extract_tag_info": True,
            "extract_merge_info": True,
            "extract_file_history": True,
            "max_history_depth": 100,
            "include_parent_commits": True,
            "extract_commit_stats": True,
            "extract_author_stats": True,
        },
        description="Git-specific extraction settings",
    )

    # Confluence-specific settings
    confluence: Dict[str, Any] = Field(
        default_factory=lambda: {
            "extract_space_info": True,
            "extract_page_hierarchy": True,
            "extract_labels": True,
            "extract_restrictions": True,
            "extract_attachments": True,
            "extract_comments": False,
            "extract_page_history": True,
            "max_history_versions": 10,
            "extract_macro_info": True,
            "extract_template_info": True,
        },
        description="Confluence-specific extraction settings",
    )

    # JIRA-specific settings
    jira: Dict[str, Any] = Field(
        default_factory=lambda: {
            "extract_issue_hierarchy": True,
            "extract_linked_issues": True,
            "extract_components": True,
            "extract_versions": True,
            "extract_labels": True,
            "extract_custom_fields": True,
            "extract_comments": False,
            "extract_workflow_history": True,
            "max_history_entries": 50,
            "extract_time_tracking": True,
            "extract_attachments": True,
        },
        description="JIRA-specific extraction settings",
    )

    # LocalFile-specific settings
    localfile: Dict[str, Any] = Field(
        default_factory=lambda: {
            "extract_filesystem_metadata": True,
            "extract_file_permissions": False,
            "extract_file_stats": True,
            "extract_directory_structure": True,
            "extract_file_type_metadata": True,
            "extract_encoding_info": True,
            "extract_content_structure": True,
            "analyze_code_files": True,
            "analyze_document_files": True,
            "analyze_config_files": True,
        },
        description="LocalFile-specific extraction settings",
    )

    # PublicDocs-specific settings
    publicdocs: Dict[str, Any] = Field(
        default_factory=lambda: {
            "extract_html_metadata": True,
            "extract_seo_metadata": True,
            "extract_navigation_structure": True,
            "extract_breadcrumbs": True,
            "extract_social_metadata": True,
            "extract_schema_org": True,
            "extract_dublin_core": True,
            "extract_open_graph": True,
            "extract_twitter_cards": True,
            "analyze_page_structure": True,
        },
        description="PublicDocs-specific extraction settings",
    )


class PerformanceConfig(BaseModel):
    """Configuration for metadata extraction performance."""

    # Parallel processing
    max_parallel_extractions: int = Field(
        default=4, description="Maximum parallel metadata extractions"
    )

    extraction_timeout: int = Field(
        default=30, description="Timeout for metadata extraction (seconds)"
    )

    # Caching
    enable_caching: bool = Field(
        default=True, description="Enable metadata extraction caching"
    )

    cache_ttl: int = Field(default=3600, description="Cache time-to-live (seconds)")

    cache_size_limit: int = Field(default=1000, description="Maximum cache entries")

    # Memory management
    max_content_size: int = Field(
        default=10485760,  # 10MB
        description="Maximum content size for metadata extraction (bytes)",
    )

    chunk_large_content: bool = Field(
        default=True, description="Process large content in chunks"
    )

    chunk_size: int = Field(
        default=1048576,  # 1MB
        description="Chunk size for large content processing (bytes)",
    )

    # Error handling
    continue_on_error: bool = Field(
        default=True, description="Continue extraction on individual errors"
    )

    max_retries: int = Field(
        default=3, description="Maximum retries for failed extractions"
    )

    retry_delay: float = Field(
        default=1.0, description="Delay between retries (seconds)"
    )


class QualityConfig(BaseModel):
    """Configuration for metadata quality control."""

    # Validation
    enable_validation: bool = Field(
        default=True, description="Enable metadata validation"
    )

    strict_validation: bool = Field(
        default=False, description="Use strict validation rules"
    )

    # Quality scoring
    enable_quality_scoring: bool = Field(
        default=True, description="Enable quality scoring for metadata"
    )

    minimum_quality_score: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Minimum quality score for metadata inclusion",
    )

    # Completeness requirements
    required_fields: List[str] = Field(
        default_factory=lambda: [
            "content_length",
            "content_type",
            "extraction_timestamp",
        ],
        description="Required metadata fields",
    )

    # Consistency checks
    enable_consistency_checks: bool = Field(
        default=True, description="Enable consistency checks across metadata"
    )

    cross_validate_timestamps: bool = Field(
        default=True, description="Cross-validate timestamp consistency"
    )

    cross_validate_authors: bool = Field(
        default=True, description="Cross-validate author consistency"
    )

    # Sanitization
    sanitize_metadata: bool = Field(
        default=True, description="Sanitize metadata for security"
    )

    remove_sensitive_data: bool = Field(
        default=True, description="Remove potentially sensitive data"
    )

    sensitive_patterns: List[str] = Field(
        default_factory=lambda: [
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
            r"\b\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b",  # Credit card
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email (optional)
            r"\b(?:\d{1,3}\.){3}\d{1,3}\b",  # IP address
        ],
        description="Patterns for detecting sensitive data",
    )


class MetadataExtractionConfig(BaseConfig):
    """Comprehensive metadata extraction configuration.

    This configuration extends the base metadata extraction framework with
    detailed settings for different extraction strategies, source-specific
    configurations, and quality control measures.
    """

    # Global settings
    enabled: bool = Field(default=True, description="Enable metadata extraction")

    strategy: ExtractionStrategy = Field(
        default=ExtractionStrategy.STANDARD, description="Overall extraction strategy"
    )

    # Component configurations
    authors: AuthorExtractionConfig = Field(
        default_factory=AuthorExtractionConfig,
        description="Author metadata extraction configuration",
    )

    timestamps: TimestampExtractionConfig = Field(
        default_factory=TimestampExtractionConfig,
        description="Timestamp metadata extraction configuration",
    )

    relationships: RelationshipExtractionConfig = Field(
        default_factory=RelationshipExtractionConfig,
        description="Relationship metadata extraction configuration",
    )

    cross_references: CrossReferenceExtractionConfig = Field(
        default_factory=CrossReferenceExtractionConfig,
        description="Cross-reference metadata extraction configuration",
    )

    source_specific: SourceSpecificExtractionConfig = Field(
        default_factory=SourceSpecificExtractionConfig,
        description="Source-specific metadata extraction configuration",
    )

    # System configurations
    performance: PerformanceConfig = Field(
        default_factory=PerformanceConfig,
        description="Performance optimization configuration",
    )

    quality: QualityConfig = Field(
        default_factory=QualityConfig, description="Quality control configuration"
    )

    # Legacy compatibility
    include_system_metadata: bool = Field(
        default=False, description="Include system-level metadata (legacy)"
    )

    max_relationships: int = Field(
        default=100, description="Maximum relationships (legacy)"
    )

    max_cross_references: int = Field(
        default=50, description="Maximum cross-references (legacy)"
    )

    def get_strategy_config(self) -> Dict[str, Any]:
        """Get configuration based on the selected strategy."""
        if self.strategy == ExtractionStrategy.MINIMAL:
            return {
                "authors": {"enabled": True, "methods": ["system_metadata"]},
                "timestamps": {"enabled": True, "methods": ["filesystem"]},
                "relationships": {"enabled": False},
                "cross_references": {"enabled": False},
                "source_specific": {"enabled": False},
            }
        elif self.strategy == ExtractionStrategy.STANDARD:
            return {
                "authors": {"enabled": True, "methods": ["hybrid"]},
                "timestamps": {"enabled": True, "methods": ["hybrid"]},
                "relationships": {
                    "enabled": True,
                    "methods": ["content_links", "directory_structure"],
                },
                "cross_references": {"enabled": True},
                "source_specific": {"enabled": True},
            }
        elif self.strategy == ExtractionStrategy.COMPREHENSIVE:
            return {
                "authors": {"enabled": True, "methods": ["hybrid"]},
                "timestamps": {"enabled": True, "methods": ["hybrid"]},
                "relationships": {"enabled": True, "methods": ["hybrid"]},
                "cross_references": {"enabled": True},
                "source_specific": {"enabled": True},
            }
        else:  # CUSTOM
            return {}

    def apply_strategy(self) -> None:
        """Apply the selected strategy to component configurations."""
        strategy_config = self.get_strategy_config()

        if not strategy_config:  # CUSTOM strategy - use existing config
            return

        # Apply strategy-specific settings
        for component, settings in strategy_config.items():
            if hasattr(self, component):
                component_config = getattr(self, component)
                for key, value in settings.items():
                    if hasattr(component_config, key):
                        setattr(component_config, key, value)

    def to_base_config(self) -> "BaseMetadataExtractionConfig":
        """Convert to base metadata extraction config for compatibility."""
        from qdrant_loader.connectors.metadata.base import (
            MetadataExtractionConfig as BaseConfig,
        )

        return BaseConfig(
            enabled=self.enabled,
            extract_authors=self.authors.enabled,
            extract_timestamps=self.timestamps.enabled,
            extract_relationships=self.relationships.enabled,
            extract_cross_references=self.cross_references.enabled,
            max_relationships=min(
                self.max_relationships, self.relationships.max_relationships
            ),
            max_cross_references=min(
                self.max_cross_references, self.cross_references.max_cross_references
            ),
            include_system_metadata=self.include_system_metadata,
        )

    def validate_config(self) -> List[str]:
        """Validate the configuration and return any warnings."""
        warnings = []

        # Check for performance implications
        if (
            self.relationships.semantic_analysis.get("enabled", False)
            and self.relationships.semantic_analysis.get("max_comparisons", 0) > 10000
        ):
            warnings.append(
                "High semantic analysis comparison limit may impact performance"
            )

        # Check for memory implications
        if self.performance.max_content_size > 100 * 1024 * 1024:  # 100MB
            warnings.append("Large content size limit may cause memory issues")

        # Check for consistency
        if not self.enabled and any(
            [
                self.authors.enabled,
                self.timestamps.enabled,
                self.relationships.enabled,
                self.cross_references.enabled,
            ]
        ):
            warnings.append(
                "Component extraction enabled while global extraction disabled"
            )

        return warnings
