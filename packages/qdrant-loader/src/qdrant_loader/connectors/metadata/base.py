"""Base metadata extraction framework.

This module defines the base classes and interfaces for metadata extraction
across all data source connectors.
"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class MetadataExtractionConfig(BaseModel):
    """Configuration for metadata extraction."""

    enabled: bool = Field(default=True, description="Enable metadata extraction")
    extract_authors: bool = Field(
        default=True, description="Extract author information"
    )
    extract_timestamps: bool = Field(
        default=True, description="Extract timestamp information"
    )
    extract_relationships: bool = Field(
        default=True, description="Extract relationship information"
    )
    extract_cross_references: bool = Field(
        default=True, description="Extract cross-references"
    )
    max_relationships: int = Field(
        default=100, description="Maximum number of relationships to extract"
    )
    max_cross_references: int = Field(
        default=50, description="Maximum number of cross-references to extract"
    )
    include_system_metadata: bool = Field(
        default=False, description="Include system-level metadata"
    )


class BaseMetadataExtractor(ABC):
    """Base class for all metadata extractors.

    This class provides the common interface and functionality for extracting
    metadata from different data sources without modifying the public connector
    interfaces.
    """

    def __init__(self, config: MetadataExtractionConfig):
        """Initialize the metadata extractor.

        Args:
            config: Configuration for metadata extraction
        """
        self.config = config
        self.logger = LoggingConfig.get_logger(self.__class__.__name__)

    def extract_metadata(self, content: str, context: dict[str, Any]) -> dict[str, Any]:
        """Extract metadata from content and context.

        This is the main entry point for metadata extraction. It orchestrates
        the extraction of different types of metadata based on configuration.

        Args:
            content: The content to extract metadata from
            context: Additional context information (source-specific)

        Returns:
            Dictionary containing extracted metadata
        """
        if not self.config.enabled:
            return {}

        metadata = {}

        try:
            # Extract base metadata
            base_metadata = self._extract_base_metadata(content, context)
            metadata.update(base_metadata)

            # Extract author information
            if self.config.extract_authors:
                author_metadata = self._extract_author_metadata(content, context)
                if author_metadata:
                    metadata["authors"] = author_metadata

            # Extract timestamp information
            if self.config.extract_timestamps:
                timestamp_metadata = self._extract_timestamp_metadata(content, context)
                if timestamp_metadata:
                    metadata["timestamps"] = timestamp_metadata

            # Extract relationships
            if self.config.extract_relationships:
                relationship_metadata = self._extract_relationship_metadata(
                    content, context
                )
                if relationship_metadata:
                    metadata["relationships"] = relationship_metadata[
                        : self.config.max_relationships
                    ]

            # Extract cross-references
            if self.config.extract_cross_references:
                cross_ref_metadata = self._extract_cross_reference_metadata(
                    content, context
                )
                if cross_ref_metadata:
                    metadata["cross_references"] = cross_ref_metadata[
                        : self.config.max_cross_references
                    ]

            # Extract source-specific metadata
            source_metadata = self._extract_source_specific_metadata(content, context)
            if source_metadata:
                metadata["source_specific"] = source_metadata

            self.logger.debug(
                f"Extracted metadata with {len(metadata)} top-level fields"
            )

        except Exception as e:
            self.logger.error(f"Error extracting metadata: {e}")
            # Return partial metadata if extraction fails

        return metadata

    def _extract_base_metadata(
        self, content: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Extract base metadata common to all sources.

        Args:
            content: The content to extract metadata from
            context: Additional context information

        Returns:
            Dictionary containing base metadata
        """
        return {
            "content_length": len(content),
            "content_type": context.get("content_type", "text"),
            "extraction_timestamp": context.get("extraction_timestamp"),
            "source_type": context.get("source_type"),
        }

    @abstractmethod
    def _extract_author_metadata(
        self, content: str, context: dict[str, Any]
    ) -> list[dict[str, Any]] | None:
        """Extract author metadata.

        Args:
            content: The content to extract metadata from
            context: Additional context information

        Returns:
            List of author metadata dictionaries or None
        """
        pass

    @abstractmethod
    def _extract_timestamp_metadata(
        self, content: str, context: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Extract timestamp metadata.

        Args:
            content: The content to extract metadata from
            context: Additional context information

        Returns:
            Dictionary containing timestamp metadata or None
        """
        pass

    @abstractmethod
    def _extract_relationship_metadata(
        self, content: str, context: dict[str, Any]
    ) -> list[dict[str, Any]] | None:
        """Extract relationship metadata.

        Args:
            content: The content to extract metadata from
            context: Additional context information

        Returns:
            List of relationship metadata dictionaries or None
        """
        pass

    @abstractmethod
    def _extract_cross_reference_metadata(
        self, content: str, context: dict[str, Any]
    ) -> list[dict[str, Any]] | None:
        """Extract cross-reference metadata.

        Args:
            content: The content to extract metadata from
            context: Additional context information

        Returns:
            List of cross-reference metadata dictionaries or None
        """
        pass

    def _extract_source_specific_metadata(
        self, content: str, context: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Extract source-specific metadata.

        This method can be overridden by subclasses to extract metadata
        specific to their data source.

        Args:
            content: The content to extract metadata from
            context: Additional context information

        Returns:
            Dictionary containing source-specific metadata or None
        """
        return None

    def validate_metadata(self, metadata: dict[str, Any]) -> bool:
        """Validate extracted metadata.

        Args:
            metadata: The metadata to validate

        Returns:
            True if metadata is valid, False otherwise
        """
        try:
            # Basic validation - ensure required fields are present
            if not isinstance(metadata, dict):
                return False

            # Validate author metadata if present
            if "authors" in metadata:
                if not isinstance(metadata["authors"], list):
                    return False
                for author in metadata["authors"]:
                    if not isinstance(author, dict) or "name" not in author:
                        return False

            # Validate timestamp metadata if present
            if "timestamps" in metadata:
                if not isinstance(metadata["timestamps"], dict):
                    return False

            # Validate relationships if present
            if "relationships" in metadata:
                if not isinstance(metadata["relationships"], list):
                    return False
                for rel in metadata["relationships"]:
                    if not isinstance(rel, dict) or "type" not in rel:
                        return False

            # Validate cross-references if present
            if "cross_references" in metadata:
                if not isinstance(metadata["cross_references"], list):
                    return False
                for ref in metadata["cross_references"]:
                    if not isinstance(ref, dict) or "target" not in ref:
                        return False

            return True

        except Exception as e:
            self.logger.error(f"Error validating metadata: {e}")
            return False

    def serialize_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """Serialize metadata for storage.

        Args:
            metadata: The metadata to serialize

        Returns:
            Serialized metadata dictionary
        """
        try:
            # Ensure all values are JSON-serializable
            serialized = {}
            for key, value in metadata.items():
                if isinstance(value, str | int | float | bool | type(None)):
                    serialized[key] = value
                elif isinstance(value, list | dict):
                    serialized[key] = value  # Assume these are already serializable
                else:
                    # Convert other types to string
                    serialized[key] = str(value)

            return serialized

        except Exception as e:
            self.logger.error(f"Error serializing metadata: {e}")
            return metadata  # Return original if serialization fails
