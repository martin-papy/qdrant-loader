from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import uuid
from datetime import datetime, UTC

class Document(BaseModel):
    """Document model with enhanced metadata support."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source: str
    source_type: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    url: Optional[str] = None
    project: Optional[str] = None
    author: Optional[str] = None
    last_updated: Optional[datetime] = None

    def __init__(self, **data):
        # Initialize with provided data
        super().__init__(**data)
        
        # Update metadata with core fields
        self.metadata.update({
            'source': self.source,
            'source_type': self.source_type,
            'created_at': self.created_at.isoformat()
        })
        
        # Add optional fields to metadata if present
        if self.url:
            self.metadata['url'] = self.url
        if self.project:
            self.metadata['project'] = self.project
        if self.author:
            self.metadata['author'] = self.author
        if self.last_updated:
            self.metadata['last_updated'] = self.last_updated.isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert document to dictionary format for Qdrant."""
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata,
            "source": self.source,
            "source_type": self.source_type,
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Document":
        """Create document from dictionary format."""
        metadata = data.get("metadata", {})
        doc = cls(
            id=data.get("id", str(uuid.uuid4())),
            content=data["content"],
            source=data["source"],
            source_type=data["source_type"],
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now(UTC).isoformat())),
            url=metadata.get("url"),
            project=metadata.get("project"),
            author=metadata.get("author"),
            last_updated=metadata.get("last_updated", None)
        )
        # Add any additional metadata
        for key, value in metadata.items():
            if key not in ['url', 'project', 'author', 'last_updated', 'source', 'source_type', 'created_at']:
                doc.metadata[key] = value
        return doc 