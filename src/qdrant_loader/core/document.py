import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class Document(BaseModel):
    """Document model with enhanced metadata support."""

    id: str
    title: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    content_hash: str
    source_type: str
    source: str
    url: str
    is_deleted: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    def __init__(self, **data):
        # Generate ID
        data["id"] = self.generate_id(data["source_type"], data["source"], data["url"])

        # Calculate content hash
        data["content_hash"] = self.calculate_content_hash(
            data["content"], data["title"], data["metadata"]
        )

        # Initialize with provided data
        super().__init__(**data)

        logger.debug(f"Creating document with id: {self.id}")
        logger.debug(f"     Document content length: {len(self.content) if self.content else 0}")
        logger.debug(f"     Document source: {self.source}")
        logger.debug(f"     Document source_type: {self.source_type}")
        logger.debug(f"     Document created_at: {self.created_at}")
        logger.debug(f"     Document metadata: {self.metadata}")

    def to_dict(self) -> dict[str, Any]:
        """Convert document to dictionary format for Qdrant."""
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata,
            "source": self.source,
            "source_type": self.source_type,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "title": self.title,
            "content_hash": self.content_hash,
            "is_deleted": self.is_deleted,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Document":
        """Create document from dictionary format."""
        metadata = data.get("metadata", {})
        doc = cls(
            id=cls.generate_id(data["source_type"], data["source"], data["url"]),
            content=data["content"],
            source=data["source"],
            source_type=data["source_type"],
            created_at=datetime.fromisoformat(
                data.get("created_at", datetime.now(UTC).isoformat())
            ),
            url=metadata.get("url"),
            title=data["title"],
            updated_at=metadata.get("updated_at", None),
            content_hash=cls.calculate_content_hash(data["content"], data["title"], metadata),
            is_deleted=data.get("is_deleted", False),
        )
        # Add any additional metadata
        for key, value in metadata.items():
            if key not in [
                "url",
                "source",
                "source_type",
                "created_at",
                "updated_at",
                "title",
                "content",
                "id",
                "content_hash",
            ]:
                doc.metadata[key] = value

        return doc

    @staticmethod
    def calculate_content_hash(content: str, title: str, metadata: dict[str, Any]) -> str:
        """Calculate a consistent hash of document content.

        Args:
            content: The document content
            title: The document title
            metadata: The document metadata

        Returns:
            A consistent hash string of the content
        """
        # Create a consistent string combining all content elements
        content_string = f"{content}{title}{sorted(metadata.items())!s}"

        # Generate SHA-256 hash
        content_hash = hashlib.sha256(content_string.encode("utf-8")).hexdigest()

        return content_hash

    @staticmethod
    def generate_id(source_type: str, source: str, url: str) -> str:
        """Generate a consistent document ID based on source attributes.

        Args:
            source_type: The type of source (e.g., 'publicdocs', 'confluence', etc.)
            source: The source identifier
            url: Optional URL of the document

        Returns:
            A consistent UUID string generated from the inputs
        """
        # Create a consistent string combining all identifying elements
        identifier = f"{source_type}:{source}:{url or ''}"

        # Generate a SHA-256 hash of the identifier
        sha256_hash = hashlib.sha256(identifier.encode("utf-8")).digest()

        # Convert the first 16 bytes to a UUID (UUID is 16 bytes)
        # This ensures a valid UUID that Qdrant will accept
        consistent_uuid = uuid.UUID(bytes=sha256_hash[:16])

        return str(consistent_uuid)
