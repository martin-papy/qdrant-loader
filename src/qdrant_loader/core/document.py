import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from ..utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class Document(BaseModel):
    """Document model with enhanced metadata support."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    content_hash: str | None = None
    source: str
    source_type: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    url: str | None = None
    project: str | None = None
    author: str | None = None
    last_updated: datetime | None = None

    def __init__(self, **data):
        # Initialize with provided data
        super().__init__(**data)

        logger.debug(f"Creating document with id: {self.id}")
        logger.debug(f"     Document content length: {len(self.content) if self.content else 0}")
        logger.debug(f"     Document source: {self.source}")
        logger.debug(f"     Document source_type: {self.source_type}")
        logger.debug(f"     Document created_at: {self.created_at}")
        logger.debug(f"     Document metadata: {self.metadata}")

        # Update metadata with core fields
        self.metadata.update(
            {
                "source": self.source,
                "source_type": self.source_type,
                "created_at": self.created_at.isoformat(),
            }
        )

        # Add optional fields to metadata if present
        if self.url:
            self.metadata["url"] = self.url
        if self.project:
            self.metadata["project"] = self.project
        if self.author:
            self.metadata["author"] = self.author
        if self.last_updated:
            self.metadata["last_updated"] = self.last_updated.isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert document to dictionary format for Qdrant."""
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata,
            "source": self.source,
            "source_type": self.source_type,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Document":
        """Create document from dictionary format."""
        metadata = data.get("metadata", {})
        doc = cls(
            id=data.get("id", str(uuid.uuid4())),
            content=data["content"],
            source=data["source"],
            source_type=data["source_type"],
            created_at=datetime.fromisoformat(
                data.get("created_at", datetime.now(UTC).isoformat())
            ),
            url=metadata.get("url"),
            project=metadata.get("project"),
            author=metadata.get("author"),
            last_updated=metadata.get("last_updated", None),
        )
        # Add any additional metadata
        for key, value in metadata.items():
            if key not in [
                "url",
                "project",
                "author",
                "last_updated",
                "source",
                "source_type",
                "created_at",
            ]:
                doc.metadata[key] = value
        return doc
