import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from qdrant_loader.utils.logging import LoggingConfig


logger = LoggingConfig.get_logger(__name__)


class Document(BaseModel):
    """Document model with enhanced metadata support."""

    id: str
    title: str
    content_type: str
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
        logger.debug(
            f"     Document content length: {len(self.content) if self.content else 0}"
        )
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
            "url": self.url,
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
            content_hash=cls.calculate_content_hash(
                data["content"], data["title"], metadata
            ),
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
    def calculate_content_hash(
        content: str, title: str, metadata: dict[str, Any]
    ) -> str:
        """Calculate a consistent hash of document content.

        Args:
            content: The document content
            title: The document title
            metadata: The document metadata

        Returns:
            A consistent hash string of the content
        """
        import json
        from typing import Any

        def normalize_value(value: Any) -> Any:
            """Normalize a value for consistent hashing."""
            if value is None:
                return "null"
            if isinstance(value, str | int | float | bool):
                return value
            if isinstance(value, dict):
                return {k: normalize_value(v) for k, v in sorted(value.items())}
            if isinstance(value, list | tuple):
                return [normalize_value(v) for v in value]
            return str(value)

        # Normalize all inputs
        normalized_content = content.replace("\r\n", "\n")
        normalized_title = title.replace("\r\n", "\n")
        normalized_metadata = normalize_value(metadata)

        # Create a consistent string representation
        content_string = json.dumps(
            {
                "content": normalized_content,
                "title": normalized_title,
                "metadata": normalized_metadata,
            },
            sort_keys=True,
            ensure_ascii=False,
        )

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
        from urllib.parse import urlparse, urlunparse

        logger = LoggingConfig.get_logger(__name__)

        def normalize_url(url: str) -> str:
            """Normalize a URL for consistent hashing.

            This function normalizes URLs by:
            1. Converting to lowercase
            2. Removing trailing slashes
            3. Removing query parameters
            4. Removing fragments
            5. Handling empty paths
            6. Handling malformed URLs
            """
            try:
                # Convert to lowercase first to handle case variations
                url = url.lower().strip()

                # Parse the URL
                parsed = urlparse(url)

                # Normalize the scheme and netloc (already lowercase from above)
                scheme = parsed.scheme
                netloc = parsed.netloc

                # Normalize the path
                path = parsed.path.rstrip("/")
                if not path:  # Handle empty paths
                    path = "/"

                # Construct normalized URL without query parameters and fragments
                normalized = urlunparse(
                    (scheme, netloc, path, "", "", "")  # params  # query  # fragment
                )

                logger.debug(f"Normalized URL: {normalized}")
                return normalized
            except Exception as e:
                logger.error(f"Error normalizing URL {url}: {str(e)}")
                # If URL parsing fails, return the original URL in lowercase
                return url.lower().strip()

        def normalize_string(s: str) -> str:
            """Normalize a string for consistent hashing."""
            normalized = s.strip().lower()
            logger.debug(f"Normalized string '{s}' to '{normalized}'")
            return normalized

        # Normalize all inputs
        normalized_source_type = normalize_string(source_type)
        normalized_source = normalize_string(source)
        normalized_url = normalize_url(url)

        # Create a consistent string combining all identifying elements
        identifier = f"{normalized_source_type}:{normalized_source}:{normalized_url}"
        logger.debug(f"Generated identifier: {identifier}")

        # Generate a SHA-256 hash of the identifier
        sha256_hash = hashlib.sha256(identifier.encode("utf-8")).digest()

        # Convert the first 16 bytes to a UUID (UUID is 16 bytes)
        # This ensures a valid UUID that Qdrant will accept
        consistent_uuid = uuid.UUID(bytes=sha256_hash[:16])
        logger.debug(f"Generated UUID: {consistent_uuid}")

        return str(consistent_uuid)

    @staticmethod
    def generate_chunk_id(document_id: str, chunk_index: int) -> str:
        """Generate a unique ID for a document chunk.

        Args:
            document_id: The parent document's ID
            chunk_index: The index of the chunk

        Returns:
            A unique chunk ID
        """
        # Create a string combining document ID and chunk index
        chunk_string = f"{document_id}_{chunk_index}"

        # Hash the string to get a consistent length ID
        chunk_hash = hashlib.sha256(chunk_string.encode()).hexdigest()

        # Convert to UUID format for Qdrant compatibility
        chunk_uuid = uuid.UUID(chunk_hash[:32])

        return str(chunk_uuid)

    # Hierarchy convenience methods
    def get_parent_id(self) -> str | None:
        """Get the parent document ID if available.

        Returns:
            Parent document ID or None if this is a root document
        """
        return self.metadata.get("parent_id")

    def get_parent_title(self) -> str | None:
        """Get the parent document title if available.

        Returns:
            Parent document title or None if this is a root document
        """
        return self.metadata.get("parent_title")

    def get_breadcrumb(self) -> list[str]:
        """Get the breadcrumb trail for this document.

        Returns:
            List of ancestor titles leading to this document
        """
        return self.metadata.get("breadcrumb", [])

    def get_breadcrumb_text(self) -> str:
        """Get the breadcrumb trail as a formatted string.

        Returns:
            Breadcrumb trail formatted as "Parent > Child > Current"
        """
        return self.metadata.get("breadcrumb_text", "")

    def get_depth(self) -> int:
        """Get the depth of this document in the hierarchy.

        Returns:
            Depth level (0 for root documents, 1 for first level children, etc.)
        """
        return self.metadata.get("depth", 0)

    def get_ancestors(self) -> list[dict]:
        """Get the list of ancestor documents.

        Returns:
            List of ancestor document information (id, title, type)
        """
        return self.metadata.get("ancestors", [])

    def get_children(self) -> list[dict]:
        """Get the list of child documents.

        Returns:
            List of child document information (id, title, type)
        """
        return self.metadata.get("children", [])

    def is_root_document(self) -> bool:
        """Check if this is a root document (no parent).

        Returns:
            True if this is a root document, False otherwise
        """
        return self.get_parent_id() is None

    def has_children(self) -> bool:
        """Check if this document has child documents.

        Returns:
            True if this document has children, False otherwise
        """
        return len(self.get_children()) > 0

    def get_hierarchy_context(self) -> str:
        """Get a formatted string describing the document's position in the hierarchy.

        Returns:
            Formatted hierarchy context string
        """
        breadcrumb = self.get_breadcrumb_text()
        depth = self.get_depth()
        children_count = len(self.get_children())

        context_parts = []

        if breadcrumb:
            context_parts.append(f"Path: {breadcrumb}")

        context_parts.append(f"Depth: {depth}")

        if children_count > 0:
            context_parts.append(f"Children: {children_count}")

        return " | ".join(context_parts)
