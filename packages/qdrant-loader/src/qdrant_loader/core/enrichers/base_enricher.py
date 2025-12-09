"""Base interface for metadata enrichers.

POC2-001: LlamaIndex-inspired pluggable enricher interface.

This module defines the abstract base class and supporting types for
all metadata enrichers. The design follows these principles:

1. Single Responsibility: Each enricher handles one type of metadata
2. Configurable: Each enricher can have its own configuration
3. Composable: Enrichers can be chained in a pipeline
4. Graceful Degradation: Failures in one enricher don't break others
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from qdrant_loader.utils.logging import LoggingConfig

if TYPE_CHECKING:
    from qdrant_loader.config import Settings
    from qdrant_loader.core.document import Document

logger = LoggingConfig.get_logger(__name__)


class EnricherPriority(Enum):
    """Priority levels for enricher execution order.

    Higher priority enrichers run first, allowing their results
    to be used by lower priority enrichers.
    """

    HIGHEST = 0  # Run first (e.g., basic text analysis)
    HIGH = 1  # Important enrichers (e.g., entity extraction)
    NORMAL = 2  # Standard enrichers (e.g., keyword extraction)
    LOW = 3  # Can depend on other enrichers (e.g., topic modeling)
    LOWEST = 4  # Run last (e.g., summary generation)


@dataclass
class EnricherConfig:
    """Configuration for an enricher.

    Attributes:
        enabled: Whether the enricher is active
        priority: Execution priority (lower = earlier)
        max_content_length: Skip enrichment for content longer than this
        timeout_seconds: Maximum time allowed for enrichment
        custom_settings: Enricher-specific settings
    """

    enabled: bool = True
    priority: EnricherPriority = EnricherPriority.NORMAL
    max_content_length: int = 100_000  # 100KB default
    timeout_seconds: float = 30.0
    custom_settings: dict[str, Any] = field(default_factory=dict)


@dataclass
class EnricherResult:
    """Result of an enrichment operation.

    Attributes:
        success: Whether enrichment succeeded
        metadata: Extracted metadata to merge into document
        errors: Any errors that occurred
        skipped: Whether enrichment was skipped (e.g., content too large)
        skip_reason: Reason for skipping if applicable
        processing_time_ms: Time taken to process in milliseconds
    """

    success: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str | None = None
    processing_time_ms: float = 0.0

    @classmethod
    def skipped_result(cls, reason: str) -> "EnricherResult":
        """Create a skipped result with the given reason."""
        return cls(success=True, skipped=True, skip_reason=reason)

    @classmethod
    def error_result(cls, error: str) -> "EnricherResult":
        """Create an error result with the given error message."""
        return cls(success=False, errors=[error])


class BaseEnricher(ABC):
    """Abstract base class for all metadata enrichers.

    Enrichers extract specific types of metadata from documents and
    add them to the document's metadata dictionary. Each enricher
    should focus on a single type of enrichment.

    Example implementation:
        class MyEnricher(BaseEnricher):
            @property
            def name(self) -> str:
                return "my_enricher"

            async def enrich(self, document: Document) -> EnricherResult:
                metadata = {"my_field": extract_value(document.content)}
                return EnricherResult(metadata=metadata)

    Lifecycle:
        1. __init__: Initialize with settings and config
        2. should_process: Check if document should be processed
        3. enrich: Extract metadata from document
        4. shutdown: Clean up resources (optional)
    """

    def __init__(
        self,
        settings: "Settings",
        config: EnricherConfig | None = None,
    ):
        """Initialize the enricher.

        Args:
            settings: Application settings
            config: Enricher-specific configuration (optional)
        """
        self.settings = settings
        self.config = config or EnricherConfig()
        self.logger = LoggingConfig.get_logger(self.__class__.__name__)

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this enricher.

        Used for logging, metrics, and configuration lookup.
        Should be lowercase with underscores (e.g., "entity_enricher").
        """
        pass

    @property
    def priority(self) -> EnricherPriority:
        """Execution priority for this enricher."""
        return self.config.priority

    def should_process(self, document: "Document") -> tuple[bool, str | None]:
        """Determine if this enricher should process the document.

        Override this method to add custom filtering logic.

        Args:
            document: The document to potentially process

        Returns:
            Tuple of (should_process, skip_reason)
        """
        if not self.config.enabled:
            return False, "enricher_disabled"

        content_length = len(document.content) if document.content else 0
        if content_length > self.config.max_content_length:
            return False, f"content_too_large ({content_length} > {self.config.max_content_length})"

        return True, None

    @abstractmethod
    async def enrich(self, document: "Document") -> EnricherResult:
        """Extract metadata from the document.

        This is the main method that performs the enrichment. It should:
        1. Extract relevant metadata from document.content
        2. Return an EnricherResult with the extracted metadata
        3. Handle errors gracefully, returning error results instead of raising

        Args:
            document: The document to enrich

        Returns:
            EnricherResult containing extracted metadata or error information
        """
        pass

    async def shutdown(self) -> None:
        """Clean up any resources used by this enricher.

        Override this method if your enricher allocates resources
        that need explicit cleanup (e.g., model weights, connections).
        """
        pass

    def get_metadata_keys(self) -> list[str]:
        """Return the list of metadata keys this enricher produces.

        Used for documentation and validation. Override to specify
        the exact keys your enricher adds to document metadata.

        Returns:
            List of metadata key names
        """
        return []

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, priority={self.priority.name})"
