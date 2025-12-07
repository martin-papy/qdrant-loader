"""SharePoint connector for qdrant-loader using Microsoft Graph API.

This connector uses GraphClient from office365-rest-python-client to access
SharePoint Online document libraries through Microsoft Graph API.

Features:
- Client Credentials and User Credentials authentication
- Document library traversal and file ingestion
- File filtering by extension, path patterns, and size
- Rate limiting for API requests
- File conversion support

Pattern: Hybrid connector combining:
- API-based auth (like Confluence) with function-based authentication
- File-based processing (like Git) with FileProcessor and MetadataExtractor
"""

import asyncio
from typing import Optional

from office365.graph_client import GraphClient

from qdrant_loader.connectors.base import BaseConnector
from qdrant_loader.connectors.shared.http import RateLimiter
from qdrant_loader.core.document import Document
from qdrant_loader.core.file_conversion import (
    FileConversionConfig,
    FileConverter,
    FileDetector,
)
from qdrant_loader.utils.logging import LoggingConfig

from .auth import create_graph_client, validate_connection, SharePointAuthError
from .config import SharePointConfig
from .metadata_extractor import SharePointMetadataExtractor


logger = LoggingConfig.get_logger(__name__)


class SharePointConnector(BaseConnector):
    """Connector for ingesting documents from SharePoint using Microsoft Graph API.

    Uses function-based authentication with GraphClient:
    - create_graph_client(config) -> GraphClient
    - validate_connection(client) -> dict

    Example:
        async with SharePointConnector(config) as connector:
            documents = await connector.get_documents()
    """

    def __init__(self, config: SharePointConfig):
        super().__init__(config)
        self.config: SharePointConfig = config
        self._initialized = False

        # GraphClient - created on __aenter__
        self._client: Optional[GraphClient] = None
        self._site = None
        self._site_info: Optional[dict] = None

        # Rate limiter (like Confluence/Jira pattern)
        self._rate_limiter = RateLimiter.per_minute(config.requests_per_minute)

        # Metadata extractor (like Git/LocalFile pattern)
        self.metadata_extractor = SharePointMetadataExtractor(config)

        # File conversion (like Git/LocalFile pattern)
        self.file_converter: Optional[FileConverter] = None
        self.file_detector: Optional[FileDetector] = None
        if self.config.enable_file_conversion:
            logger.debug("File conversion enabled for SharePoint connector")
            self.file_detector = FileDetector()

    async def __aenter__(self):
        """Async context manager entry - initialize GraphClient and validate connection."""
        if not self._initialized:
            try:
                # Create GraphClient using function-based auth
                self._client = create_graph_client(self.config)

                # Validate connection
                self._site_info = validate_connection(self._client)
                logger.info(
                    "SharePoint connector initialized",
                    site=self._site_info.get("display_name"),
                )

                self._initialized = True
            except SharePointAuthError:
                raise
            except Exception as e:
                raise SharePointAuthError(f"Failed to initialize connector: {e}") from e

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self._initialized = False
        self._client = None
        self._site = None

    @property
    def client(self) -> GraphClient:
        """Get the GraphClient, raising error if not initialized."""
        if self._client is None:
            raise RuntimeError(
                "SharePointConnector not initialized. Use 'async with' context manager."
            )
        return self._client

    def _get_site(self):
        """Get SharePoint site object."""
        if self._site is None:
            # Parse site info from config
            site_url = str(self.config.site_url).rstrip("/")
            # Extract host from site_url (e.g., "company.sharepoint.com")
            host = site_url.replace("https://", "").replace("http://", "").split("/")[0]
            relative_url = self.config.relative_url

            # Format: host:/sites/sitename
            site_path = f"{host}:{relative_url}"
            logger.debug(f"Connecting to SharePoint site: {site_path}")

            self._site = self.client.sites.get_by_url(site_path)
            self.client.execute_query()

            logger.info(
                f"Connected to SharePoint site: {self._site.properties.get('displayName', 'N/A')}"
            )

        return self._site

    async def _execute_with_rate_limit(self):
        """Execute pending Graph API queries with rate limiting.

        Wraps execute_query() calls with rate limiter to respect API limits.
        """
        await self._rate_limiter.acquire()
        try:
            self.client.execute_query()
        except Exception as e:
            if "429" in str(e):
                logger.warning("Rate limited by SharePoint API, waiting 60s...")
                await asyncio.sleep(60)
                await self._rate_limiter.acquire()
                self.client.execute_query()
            else:
                raise

    def set_file_conversion_config(self, file_conversion_config: FileConversionConfig):
        """Set file conversion configuration from global config."""
        super().set_file_conversion_config(file_conversion_config)
        if self.config.enable_file_conversion:
            self.file_converter = FileConverter(file_conversion_config)
            logger.debug("File converter initialized with global config")

    async def get_documents(self) -> list[Document]:
        """Get all documents from SharePoint document libraries."""
        documents = []

        try:
            site = self._get_site()
            drives = site.drives.get().execute_query()

            logger.info(f"Found {len(drives)} document libraries")

            for drive in drives:
                drive_name = drive.properties.get("name", "Unknown")

                # Filter by document_libraries if specified
                if (
                    self.config.document_libraries
                    and drive_name not in self.config.document_libraries
                ):
                    logger.debug(f"Skipping library: {drive_name} (not in filter)")
                    continue

                logger.info(f"Processing library: {drive_name}")

                try:
                    library_docs = await self._process_drive(drive, drive_name)
                    documents.extend(library_docs)
                except Exception as e:
                    logger.warning(f"Error processing library {drive_name}: {e}")

            logger.info(f"Collected {len(documents)} documents from SharePoint")

        except Exception as e:
            logger.error(f"Error fetching documents from SharePoint: {e}")
            raise

        return documents

    async def _process_drive(self, drive, drive_name: str) -> list[Document]:
        """Process a single document library/drive."""
        documents = []

        try:
            await self._process_folder(drive.root, drive_name, "", documents)
        except Exception as e:
            logger.warning(f"Error processing drive root: {e}")

        return documents

    async def _process_folder(
        self, folder, drive_name: str, path: str, documents: list[Document]
    ):
        """Recursively process a folder and its contents."""
        try:
            items = folder.children.get().execute_query()
        except Exception as e:
            logger.warning(f"Cannot access folder {path}: {e}")
            return

        for item in items:
            props = item.properties
            name = props.get("name", "")
            item_path = f"{path}/{name}" if path else name

            # Check exclude paths
            if self._should_exclude(item_path):
                logger.debug(f"Skipping excluded path: {item_path}")
                continue

            folder_info = props.get("folder")
            if folder_info is not None:
                # It's a folder - recurse
                try:
                    await self._process_folder(item, drive_name, item_path, documents)
                except Exception as e:
                    logger.warning(f"Error processing folder {item_path}: {e}")
            else:
                # It's a file
                try:
                    doc = await self._process_file(item, drive_name, item_path)
                    if doc:
                        documents.append(doc)
                except Exception as e:
                    logger.warning(f"Error processing file {item_path}: {e}")

    async def _process_file(
        self, item, drive_name: str, path: str
    ) -> Document | None:
        """Process a single file and return a Document."""
        props = item.properties
        name = props.get("name", "")

        # Check file extension filter
        if not self._should_process_file(name):
            logger.debug(f"Skipping file (extension filter): {name}")
            return None

        # Check file size
        size = props.get("size", 0) or 0
        if size > self.config.max_file_size:
            logger.debug(
                f"Skipping file (too large): {name} ({size} > {self.config.max_file_size})"
            )
            return None

        # Get file content
        content = await self._download_file_content(item, props)
        if content is None:
            return None

        # Extract metadata using SharePointMetadataExtractor
        metadata = self.metadata_extractor.extract_metadata(props, drive_name, path)

        # Create document ID
        doc_id = f"sharepoint:{self.config.source}:{props.get('id', path)}"

        # Determine content type
        file_info = props.get("file") or {}
        mime_type = (
            file_info.get("mimeType", "")
            if isinstance(file_info, dict)
            else ""
        )
        content_type = self.metadata_extractor.get_content_type(mime_type, name)

        return Document(
            id=doc_id,
            title=name,
            content_type=content_type,
            content=content,
            metadata=metadata,
            source_type="sharepoint",
            source=self.config.source,
            url=props.get("webUrl", ""),
        )

    async def _download_file_content(self, item, props: dict) -> str | None:
        """Download file content and return as text."""
        try:
            # Try to get download URL
            download_url = props.get("@microsoft.graph.downloadUrl")
            if not download_url:
                # Fallback: get content through API
                logger.debug(
                    f"No download URL for {props.get('name')}, trying content API"
                )
                try:
                    content_stream = item.get_content().execute_query()
                    if content_stream:
                        return content_stream.value.decode("utf-8", errors="replace")
                except Exception as e:
                    logger.debug(f"Content API failed: {e}")
                    return None

            # Download using requests in a thread to avoid blocking the event loop
            import requests

            def download_sync():
                resp = requests.get(download_url, timeout=60)
                resp.raise_for_status()
                return resp.content

            content_bytes = await asyncio.to_thread(download_sync)

            # Try to decode as text
            try:
                return content_bytes.decode("utf-8")
            except UnicodeDecodeError:
                # Binary file - return placeholder or use file conversion
                if self.file_converter:
                    # TODO: Implement file conversion for binary files
                    logger.debug(
                        f"Binary file {props.get('name')} - conversion not yet implemented"
                    )
                return f"[Binary file: {props.get('name')}]"

        except Exception as e:
            logger.warning(f"Error downloading file content: {e}")
            return None

    def _should_process_file(self, filename: str) -> bool:
        """Check if file should be processed based on extension filter."""
        if not self.config.file_types:
            return True  # No filter, process all

        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        return ext in self.config.file_types

    def _should_exclude(self, path: str) -> bool:
        """Check if path should be excluded."""
        if not self.config.exclude_paths:
            return False

        for exclude_pattern in self.config.exclude_paths:
            if exclude_pattern in path:
                return True
        return False
