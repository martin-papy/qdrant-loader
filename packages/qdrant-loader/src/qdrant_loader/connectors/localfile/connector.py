import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from urllib.parse import unquote, urlparse

from qdrant_loader.utils.sensitive import sanitize_exception_message
from qdrant_loader.connectors.base import BaseConnector, resolve_safe_path
from qdrant_loader.core.conversion.service import ConversionService
from qdrant_loader.core.document import Document
from qdrant_loader.core.file_conversion import (
    FileConversionConfig,
    FileDetector,
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
        # Parse base_url (file://...) to get the local path with Windows support
        parsed = urlparse(str(config.base_url))
        self.base_path = self._fix_windows_file_path(parsed.path)
        self.file_processor = LocalFileFileProcessor(config, self.base_path)
        self.metadata_extractor = LocalFileMetadataExtractor(self.base_path)
        self.logger = LoggingConfig.get_logger(__name__)
        self._initialized = True

        # Initialize file conversion components if enabled
        self.conversion_service = None
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

    def _fix_windows_file_path(self, path: str) -> str:
        """Fix Windows file path from URL parsing.

        urlparse() adds a leading slash to Windows drive letters, e.g.:
        file:///C:/Users/... -> path = "/C:/Users/..."
        This method removes the leading slash for Windows paths and handles URL decoding.

        Args:
            path: Raw path from urlparse()

        Returns:
            Fixed path suitable for the current platform
        """
        # First decode URL encoding (e.g., %20 -> space)
        path = unquote(path)

        # Handle Windows paths: remove leading slash if it's a drive letter
        if len(path) >= 3 and path[0] == "/" and path[2] == ":":
            # This looks like a Windows path with leading slash: "/C:/..." or "/C:" -> "C:/..." or "C:"
            path = path[1:]

        return path

    def set_file_conversion_config(self, file_conversion_config: FileConversionConfig):
        """Set file conversion configuration from global config.

        Args:
            file_conversion_config: Global file conversion configuration
        """
        if self.config.enable_file_conversion:
            self.conversion_service = ConversionService(file_conversion_config)
            self.logger.debug(
                "Conversion service initialized",
                engine=str(file_conversion_config.engine),
            )

    def _build_file_document(self, file_path: str) -> Document | None:
        """Build a Document for a local file, or None if the file should be skipped.

        Used by both stream_documents and fetch_by_id.
        """
        file = os.path.basename(file_path)
        # Get relative path from base directory
        rel_path = os.path.relpath(file_path, self.base_path)
        file_extension = os.path.splitext(file)[1].lower()

        if self.config.enable_file_conversion and file_extension in {".doc", ".ppt"}:
            file_info = (
                self.file_detector.get_file_type_info(file_path)
                if self.file_detector
                else {
                    "mime_type": None,
                    "file_extension": file_extension,
                }
            )
            self.logger.warning(
                "Skipping file: old doc/ppt are not supported for MarkItDown conversion",
                file_path=rel_path.replace("\\", "/"),
                mime_type=file_info.get("mime_type"),
                file_extension=file_info.get("file_extension"),
            )
            return None

        # Check if file needs conversion. The eligibility gate is the
        # ConversionService (engine-aware): for docling it also enforces
        # the enabled-format + size policy, so a file the active engine
        # can't convert is skipped here instead of falling into a fallback.
        needs_conversion = (
            self.config.enable_file_conversion
            and self.conversion_service is not None
            and self.conversion_service.is_supported(file_path)
        )

        converted_document = None
        original_file_type = None
        if needs_conversion:
            self.logger.debug(
                "File needs conversion",
                file_path=rel_path.replace("\\", "/"),
            )
            # ConversionService picks the engine (markitdown|docling) and
            # returns success or a fallback document — it never raises for a
            # per-document conversion failure.
            assert self.conversion_service is not None  # Type checker hint
            converted = self.conversion_service.convert(file_path)
            content = converted.content
            content_type = "md"  # Converted files (and fallbacks) are markdown
            conversion_method = converted.conversion_method
            conversion_failed = converted.conversion_failed
            converted_document = converted.converted_document
            original_file_type = converted.original_file_type
            self.logger.info(
                "File conversion completed",
                file_path=rel_path.replace("\\", "/"),
                conversion_method=conversion_method,
                conversion_failed=conversion_failed,
            )
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

        metadata = self.metadata_extractor.extract_all_metadata(file_path, content)

        # Add file conversion metadata if applicable
        if needs_conversion:
            metadata.update(
                {
                    "conversion_method": conversion_method,
                    "conversion_failed": conversion_failed,
                    "original_file_type": original_file_type,
                }
            )

        self.logger.debug(f"Processed local file: {rel_path.replace('\\', '/')}")

        # Create consistent URL with forward slashes for cross-platform compatibility
        normalized_path = os.path.realpath(file_path).replace("\\", "/")
        doc = Document(
            title=os.path.basename(file_path),
            content=content,
            content_type=content_type,
            metadata=metadata,
            source_type="localfile",
            source=self.config.source,
            url=f"file://{normalized_path}",
            is_deleted=False,
            updated_at=updated_at,
        )
        # Carry the structured artifact (docling path) to the chunker,
        # in-process and by reference — never serialized.
        doc.converted_document = converted_document
        return doc

    def _is_within_base_path(self, file_path: str) -> bool:
        base_real = os.path.realpath(self.base_path)
        file_real = os.path.realpath(file_path)
        return file_real == base_real or file_real.startswith(base_real + os.sep)

    async def stream_documents(
        self, since: datetime | None = None
    ) -> AsyncIterator[Document]:
        """Stream documents from the local file source (WS-1 connector contract).

        Note:
            The `since` parameter is not yet implemented for incremental
            ingestion. All files are processed regardless of modification time.
        """
        for root, _, files in os.walk(self.base_path):
            for file in files:
                file_path = os.path.join(root, file)
                if not self._is_within_base_path(file_path):
                    self.logger.warning(
                        "Skipping file outside base path",
                        file_path=file_path.replace("\\", "/"),
                    )
                    continue
                if not self.file_processor.should_process_file(file_path):
                    continue
                try:
                    doc = self._build_file_document(file_path)
                    if doc is not None:
                        yield doc
                except (OSError, UnicodeError, ValueError) as e:
                    self.logger.warning(
                        "Failed to process file",
                        file_path=file_path.replace("\\", "/"),
                        error=sanitize_exception_message(e),
                    )
                    continue
                except Exception:
                    raise

    async def get_documents(self) -> list[Document]:
        """Get documents from the local file source (DEPRECATED - use stream_documents)."""
        return await super().get_documents()

    async def fetch_by_id(self, entity_id: str) -> Document | None:
        """Fetch a single file by its path relative to the connector's base directory."""
        file_path = resolve_safe_path(self.base_path, entity_id)
        if file_path is None:
            self.logger.warning(
                "Path traversal attempt blocked", entity_id=entity_id
            )
            return None
        if not os.path.exists(
            file_path
        ) or not self.file_processor.should_process_file(file_path):
            return None
        try:
            return self._build_file_document(file_path)
        except (OSError, UnicodeError, ValueError) as e:
            self.logger.warning(
                "Failed to fetch file by id",
                entity_id=entity_id,
                error=sanitize_exception_message(e),
            )
            return None

    async def list_entity_ids(self) -> AsyncIterator[str]:
        """Stream paths (relative to base_path, forward slashes) for all processable files."""
        for root, _, files in os.walk(self.base_path):
            for file in files:
                file_path = os.path.join(root, file)
                if not self._is_within_base_path(file_path):
                    continue
                if self.file_processor.should_process_file(file_path):
                    rel_path = os.path.relpath(file_path, self.base_path)
                    yield rel_path.replace(os.sep, "/").replace("\\", "/")
