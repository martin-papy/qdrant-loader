from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

@dataclass
class Document:
    """Base class for all document types."""
    content: str
    source: str
    source_type: str
    url: Optional[str] = None
    last_updated: Optional[datetime] = None
    project: Optional[str] = None
    author: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Initialize metadata if not provided."""
        if self.metadata is None:
            self.metadata = {}
        
        # Always set core metadata fields
        self.metadata['source'] = self.source
        self.metadata['source_type'] = self.source_type
        
        # Add optional metadata if not present
        if 'url' not in self.metadata and self.url:
            self.metadata['url'] = self.url
        if 'last_updated' not in self.metadata and self.last_updated:
            self.metadata['last_updated'] = self.last_updated.isoformat()
        if 'project' not in self.metadata and self.project:
            self.metadata['project'] = self.project
        if 'author' not in self.metadata and self.author:
            self.metadata['author'] = self.author 