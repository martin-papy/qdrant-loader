import os
from typing import List
import structlog
from datetime import datetime, timezone
from urllib.parse import urlparse
from qdrant_loader.connectors.base import BaseConnector
from qdrant_loader.core.document import Document
from .config import LocalFileConfig
from .file_processor import LocalFileFileProcessor
from .metadata_extractor import LocalFileMetadataExtractor


class LocalFileConnector(BaseConnector):
    """Connector for ingesting local files."""

    def __init__(self, config: LocalFileConfig):
        super().__init__(config)
        self.config = config
        # Parse base_url (file://...) to get the local path
        parsed = urlparse(str(config.base_url))
        self.base_path = parsed.path
        self.file_processor = LocalFileFileProcessor(config, self.base_path)
        self.metadata_extractor = LocalFileMetadataExtractor(self.base_path)
        self.logger = structlog.get_logger(__name__)
        self._initialized = True

    async def get_documents(self) -> List[Document]:
        """Get all documents from the local file source."""
        documents = []
        for root, _, files in os.walk(self.base_path):
            for file in files:
                file_path = os.path.join(root, file)
                if not self.file_processor.should_process_file(file_path):
                    continue
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                    # Get file modification time
                    file_mtime = os.path.getmtime(file_path)
                    updated_at = datetime.fromtimestamp(file_mtime, tz=timezone.utc)

                    metadata = self.metadata_extractor.extract_all_metadata(file_path, content)
                    file_ext = os.path.splitext(file)[1].lower().lstrip(".")
                    rel_path = os.path.relpath(file_path, self.base_path)
                    doc = Document(
                        title=os.path.basename(file_path),
                        content=content,
                        content_type=file_ext,
                        metadata=metadata,
                        source_type="localfile",
                        source=self.config.source,
                        url=f"file://{os.path.realpath(file_path)}",
                        is_deleted=False,
                        updated_at=updated_at,
                    )
                    documents.append(doc)
                except Exception as e:
                    self.logger.error("Failed to process file", file_path=file_path, error=str(e))
                    continue
        return documents
