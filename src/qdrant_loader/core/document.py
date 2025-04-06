from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import uuid
from datetime import datetime

class Document(BaseModel):
    """Document model with enhanced metadata support."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source: str
    source_type: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        arbitrary_types_allowed = True

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
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            content=data["content"],
            metadata=data.get("metadata", {}),
            source=data["source"],
            source_type=data["source_type"],
            created_at=datetime.fromisoformat(data.get("created_at", datetime.utcnow().isoformat()))
        ) 