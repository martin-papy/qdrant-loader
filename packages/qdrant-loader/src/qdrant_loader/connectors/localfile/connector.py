import os
from datetime import UTC, datetime
from urllib.parse import urlparse

from qdrant_loader.connectors.base import BaseConnector
from qdrant_loader.core.document import Document
from qdrant_loader.core.file_conversion import (
    FileConverter,
    FileDetector,
    FileConversionConfig,
    FileConversionError,
)
from qdrant_loader.utils.logging import LoggingConfig

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
        self.logger = LoggingConfig.get_logger(__name__)
        self._initialized = True

        # Initialize file conversion components if enabled
        self.file_converter = None
        self.file_detector = None
        if self.config.enable_file_conversion:
            self.logger.debug("File conversion enabled for LocalFile connector")
            # File conversion config will be set from global config during ingestion
            self.file_detector = FileDetector()
            # Update file processor with file detector
            self.file_processor = LocalFileFileProcessor(
                config, self.base_path, self.file_detector
            )
        else:
            self.logger.debug("File conversion disabled for LocalFile connector")

    def set_file_conversion_config(self, file_conversion_config: FileConversionConfig):
        """Set file conversion configuration from global config.

        Args:
            file_conversion_config: Global file conversion configuration
        """
        if self.config.enable_file_conversion:
            self.file_converter = FileConverter(file_conversion_config)
            self.logger.debug("File converter initialized with global config")

    async def get_documents(self) -> list[Document]:
        """Get all documents from the local file source."""
        documents = []
        for root, _, files in os.walk(self.base_path):
            for file in files:
                file_path = os.path.join(root, file)
                if not self.file_processor.should_process_file(file_path):
                    continue
                try:
                    # Get relative path from base directory
                    rel_path = os.path.relpath(file_path, self.base_path)

                    # Check if file needs conversion
                    needs_conversion = (
                        self.config.enable_file_conversion
                        and self.file_detector
                        and self.file_converter
                        and self.file_detector.is_supported_for_conversion(file_path)
                    )

                    if needs_conversion:
                        self.logger.debug("File needs conversion", file_path=rel_path)
                        try:
                            # Convert file to markdown
                            assert self.file_converter is not None  # Type checker hint
                            content = self.file_converter.convert_file(file_path)
                            content_type = "md"  # Converted files are markdown
                            conversion_method = "markitdown"
                            conversion_failed = False
                            self.logger.info(
                                "File conversion successful", file_path=rel_path
                            )
                        except FileConversionError as e:
                            self.logger.warning(
                                "File conversion failed, creating fallback document",
                                file_path=rel_path,
                                error=str(e),
                            )
                            # Create fallback document
                            assert self.file_converter is not None  # Type checker hint
                            content = self.file_converter.create_fallback_document(
                                file_path, e
                            )
                            content_type = "md"  # Fallback is also markdown
                            conversion_method = "markitdown_fallback"
                            conversion_failed = True
                    else:
                        # Read file content normally
                        with open(file_path, encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                        # Get file extension without the dot
                        content_type = os.path.splitext(file)[1].lower().lstrip(".")
                        conversion_method = None
                        conversion_failed = False

                    # Get file modification time
                    file_mtime = os.path.getmtime(file_path)
                    updated_at = datetime.fromtimestamp(file_mtime, tz=UTC)

                    metadata = self.metadata_extractor.extract_all_metadata(
                        file_path, content
                    )

                    # Add file conversion metadata if applicable
                    if needs_conversion:
                        metadata.update(
                            {
                                "conversion_method": conversion_method,
                                "conversion_failed": conversion_failed,
                                "original_file_type": os.path.splitext(file)[1]
                                .lower()
                                .lstrip("."),
                            }
                        )

                    self.logger.debug(f"Processed local file: {rel_path}")

                    doc = Document(
                        title=os.path.basename(file_path),
                        content=content,
                        content_type=content_type,
                        metadata=metadata,
                        source_type="localfile",
                        source=self.config.source,
                        url=f"file://{os.path.realpath(file_path)}",
                        is_deleted=False,
                        updated_at=updated_at,
                    )
                    documents.append(doc)
                except Exception as e:
                    self.logger.error(
                        "Failed to process file", file_path=file_path, error=str(e)
                    )
                    continue
        return documents
