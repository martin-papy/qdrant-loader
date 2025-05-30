"""Generic attachment downloader for connectors that support file attachments."""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests

from qdrant_loader.core.document import Document
from qdrant_loader.core.file_conversion import (
    FileConverter,
    FileDetector,
    FileConversionConfig,
    FileConversionError,
)
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class AttachmentMetadata:
    """Metadata for an attachment."""

    def __init__(
        self,
        id: str,
        filename: str,
        size: int,
        mime_type: str,
        download_url: str,
        parent_document_id: str,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        author: Optional[str] = None,
    ):
        """Initialize attachment metadata.

        Args:
            id: Unique identifier for the attachment
            filename: Original filename
            size: File size in bytes
            mime_type: MIME type of the file
            download_url: URL to download the attachment
            parent_document_id: ID of the parent document
            created_at: Creation timestamp
            updated_at: Last update timestamp
            author: Author of the attachment
        """
        self.id = id
        self.filename = filename
        self.size = size
        self.mime_type = mime_type
        self.download_url = download_url
        self.parent_document_id = parent_document_id
        self.created_at = created_at
        self.updated_at = updated_at
        self.author = author


class AttachmentDownloader:
    """Generic attachment downloader for various connector types."""

    def __init__(
        self,
        session: requests.Session,
        file_conversion_config: Optional[FileConversionConfig] = None,
        enable_file_conversion: bool = False,
        max_attachment_size: int = 52428800,  # 50MB default
    ):
        """Initialize the attachment downloader.

        Args:
            session: Authenticated requests session
            file_conversion_config: File conversion configuration
            enable_file_conversion: Whether to enable file conversion
            max_attachment_size: Maximum attachment size to download (bytes)
        """
        self.session = session
        self.enable_file_conversion = enable_file_conversion
        self.max_attachment_size = max_attachment_size
        self.logger = logger

        # Initialize file conversion components if enabled
        self.file_converter = None
        self.file_detector = None
        if enable_file_conversion and file_conversion_config:
            self.file_converter = FileConverter(file_conversion_config)
            self.file_detector = FileDetector()
            self.logger.info("File conversion enabled for attachment downloader")
        else:
            self.logger.debug("File conversion disabled for attachment downloader")

    def should_download_attachment(self, attachment: AttachmentMetadata) -> bool:
        """Determine if an attachment should be downloaded and processed.

        Args:
            attachment: Attachment metadata

        Returns:
            bool: True if attachment should be downloaded
        """
        # Check file size limit
        if attachment.size > self.max_attachment_size:
            self.logger.debug(
                "Skipping attachment due to size limit",
                filename=attachment.filename,
                size=attachment.size,
                max_size=self.max_attachment_size,
            )
            return False

        # If file conversion is enabled, check if file is supported
        if self.enable_file_conversion and self.file_detector:
            # We can't check the actual file path yet, so check by MIME type and extension
            file_ext = Path(attachment.filename).suffix.lower()

            # Check if MIME type is supported
            if attachment.mime_type in self.file_detector.SUPPORTED_MIME_TYPES:
                return True

            # Check if extension is supported (fallback)
            if file_ext:
                extension_without_dot = file_ext.lstrip(".")
                supported_extensions = set(
                    self.file_detector.SUPPORTED_MIME_TYPES.values()
                )
                if extension_without_dot in supported_extensions:
                    return True

        # For now, download all attachments within size limits
        # In the future, this could be configurable by file type
        return True

    async def download_attachment(
        self, attachment: AttachmentMetadata
    ) -> Optional[str]:
        """Download an attachment to a temporary file.

        Args:
            attachment: Attachment metadata

        Returns:
            str: Path to downloaded temporary file, or None if download failed
        """
        if not self.should_download_attachment(attachment):
            return None

        try:
            self.logger.info(
                "Downloading attachment",
                filename=attachment.filename,
                size=attachment.size,
                url=attachment.download_url,
            )

            # Prepare headers for download request
            headers = {}

            # For Confluence downloads, we need to handle authentication properly
            # The session should already have the right authentication, but we may need
            # to handle redirects and different response types

            # Some Confluence instances return different content types or require
            # specific headers for attachment downloads
            headers.update(
                {
                    "Accept": "*/*",
                    "User-Agent": "qdrant-loader-attachment-downloader/1.0",
                }
            )

            # Download the file with proper error handling for different deployment types
            response = self.session.get(
                attachment.download_url,
                stream=True,
                headers=headers,
                allow_redirects=True,  # Important for some Confluence setups
                timeout=30,  # Reasonable timeout for downloads
            )
            response.raise_for_status()

            # Validate content type if possible
            content_type = response.headers.get("content-type", "").lower()
            if content_type and "text/html" in content_type:
                # This might indicate an authentication error or redirect to login page
                self.logger.warning(
                    "Received HTML response for attachment download, possible authentication issue",
                    filename=attachment.filename,
                    url=attachment.download_url,
                    content_type=content_type,
                )
                return None

            # Validate content length if available
            content_length = response.headers.get("content-length")
            if content_length:
                try:
                    actual_size = int(content_length)
                    if (
                        attachment.size > 0
                        and abs(actual_size - attachment.size) > 1024
                    ):
                        # Size mismatch (allowing for small differences)
                        self.logger.warning(
                            "Content length mismatch for attachment",
                            filename=attachment.filename,
                            expected_size=attachment.size,
                            actual_size=actual_size,
                        )
                except ValueError:
                    pass  # Invalid content-length header

            # Create temporary file with original extension
            file_ext = Path(attachment.filename).suffix
            temp_file = tempfile.NamedTemporaryFile(
                delete=False, suffix=file_ext, prefix=f"attachment_{attachment.id}_"
            )

            # Write content to temporary file with progress tracking
            downloaded_size = 0
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    temp_file.write(chunk)
                    downloaded_size += len(chunk)

                    # Check if we're exceeding expected size significantly
                    if attachment.size > 0 and downloaded_size > attachment.size * 1.5:
                        self.logger.warning(
                            "Download size exceeding expected size, stopping",
                            filename=attachment.filename,
                            expected_size=attachment.size,
                            downloaded_size=downloaded_size,
                        )
                        temp_file.close()
                        self.cleanup_temp_file(temp_file.name)
                        return None

            temp_file.close()

            # Final size validation
            actual_file_size = os.path.getsize(temp_file.name)
            if actual_file_size == 0:
                self.logger.warning(
                    "Downloaded file is empty",
                    filename=attachment.filename,
                    temp_path=temp_file.name,
                )
                self.cleanup_temp_file(temp_file.name)
                return None

            self.logger.debug(
                "Attachment downloaded successfully",
                filename=attachment.filename,
                temp_path=temp_file.name,
                expected_size=attachment.size,
                actual_size=actual_file_size,
            )

            return temp_file.name

        except requests.exceptions.Timeout:
            self.logger.error(
                "Timeout downloading attachment",
                filename=attachment.filename,
                url=attachment.download_url,
            )
            return None
        except requests.exceptions.HTTPError as e:
            self.logger.error(
                "HTTP error downloading attachment",
                filename=attachment.filename,
                url=attachment.download_url,
                status_code=e.response.status_code if e.response else None,
                error=str(e),
            )
            return None
        except Exception as e:
            self.logger.error(
                "Failed to download attachment",
                filename=attachment.filename,
                url=attachment.download_url,
                error=str(e),
            )
            return None

    def process_attachment(
        self,
        attachment: AttachmentMetadata,
        temp_file_path: str,
        parent_document: Document,
    ) -> Optional[Document]:
        """Process a downloaded attachment into a Document.

        Args:
            attachment: Attachment metadata
            temp_file_path: Path to downloaded temporary file
            parent_document: Parent document this attachment belongs to

        Returns:
            Document: Processed attachment document, or None if processing failed
        """
        try:
            # Check if file needs conversion
            needs_conversion = (
                self.enable_file_conversion
                and self.file_detector
                and self.file_converter
                and self.file_detector.is_supported_for_conversion(temp_file_path)
            )

            if needs_conversion:
                self.logger.debug(
                    "Attachment needs conversion", filename=attachment.filename
                )
                try:
                    # Convert file to markdown
                    assert self.file_converter is not None  # Type checker hint
                    content = self.file_converter.convert_file(temp_file_path)
                    content_type = "md"  # Converted files are markdown
                    conversion_method = "markitdown"
                    conversion_failed = False
                    self.logger.info(
                        "Attachment conversion successful", filename=attachment.filename
                    )
                except FileConversionError as e:
                    self.logger.warning(
                        "Attachment conversion failed, creating fallback document",
                        filename=attachment.filename,
                        error=str(e),
                    )
                    # Create fallback document
                    assert self.file_converter is not None  # Type checker hint
                    content = self.file_converter.create_fallback_document(
                        temp_file_path, e
                    )
                    content_type = "md"  # Fallback is also markdown
                    conversion_method = "markitdown_fallback"
                    conversion_failed = True
            else:
                # For non-convertible files, create a minimal document
                content = f"# {attachment.filename}\n\nFile type: {attachment.mime_type}\nSize: {attachment.size} bytes\n\nThis attachment could not be converted to text."
                content_type = "md"
                conversion_method = None
                conversion_failed = False

            # Create attachment metadata
            attachment_metadata = {
                "attachment_id": attachment.id,
                "original_filename": attachment.filename,
                "file_size": attachment.size,
                "mime_type": attachment.mime_type,
                "parent_document_id": attachment.parent_document_id,
                "is_attachment": True,
                "author": attachment.author,
            }

            # Add conversion metadata if applicable
            if needs_conversion:
                attachment_metadata.update(
                    {
                        "conversion_method": conversion_method,
                        "conversion_failed": conversion_failed,
                        "original_file_type": Path(attachment.filename)
                        .suffix.lower()
                        .lstrip("."),
                    }
                )

            # Create attachment document
            document = Document(
                title=f"Attachment: {attachment.filename}",
                content=content,
                content_type=content_type,
                metadata=attachment_metadata,
                source_type=parent_document.source_type,
                source=parent_document.source,
                url=f"{parent_document.url}#attachment-{attachment.id}",
                is_deleted=False,
                updated_at=parent_document.updated_at,
                created_at=parent_document.created_at,
            )

            self.logger.debug(
                "Attachment processed successfully", filename=attachment.filename
            )

            return document

        except Exception as e:
            self.logger.error(
                "Failed to process attachment",
                filename=attachment.filename,
                error=str(e),
            )
            return None

    def cleanup_temp_file(self, temp_file_path: str) -> None:
        """Clean up a temporary file.

        Args:
            temp_file_path: Path to temporary file to delete
        """
        try:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                self.logger.debug("Cleaned up temporary file", path=temp_file_path)
        except Exception as e:
            self.logger.warning(
                "Failed to clean up temporary file",
                path=temp_file_path,
                error=str(e),
            )

    async def download_and_process_attachments(
        self,
        attachments: List[AttachmentMetadata],
        parent_document: Document,
    ) -> List[Document]:
        """Download and process multiple attachments.

        Args:
            attachments: List of attachment metadata
            parent_document: Parent document

        Returns:
            List[Document]: List of processed attachment documents
        """
        attachment_documents = []
        temp_files = []

        try:
            for attachment in attachments:
                # Download attachment
                temp_file_path = await self.download_attachment(attachment)
                if not temp_file_path:
                    continue

                temp_files.append(temp_file_path)

                # Process attachment
                attachment_doc = self.process_attachment(
                    attachment, temp_file_path, parent_document
                )
                if attachment_doc:
                    attachment_documents.append(attachment_doc)

        finally:
            # Clean up all temporary files
            for temp_file in temp_files:
                self.cleanup_temp_file(temp_file)

        self.logger.debug(
            "Processed attachments",
            total_attachments=len(attachments),
            processed_attachments=len(attachment_documents),
            parent_document_id=parent_document.id,
        )

        return attachment_documents
