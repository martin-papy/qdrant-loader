"""Public documentation connector implementation."""

import fnmatch
import warnings
from collections import deque
from datetime import UTC, datetime
from typing import cast
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from qdrant_loader.connectors.base import BaseConnector
from qdrant_loader.connectors.exceptions import (
    ConnectorError,
    ConnectorNotInitializedError,
    DocumentProcessingError,
    HTTPRequestError,
)
from qdrant_loader.connectors.publicdocs.config import PublicDocsSourceConfig
from qdrant_loader.core.attachment_downloader import (
    AttachmentDownloader,
    AttachmentMetadata,
)
from qdrant_loader.core.document import Document
from qdrant_loader.core.file_conversion import (
    FileConversionConfig,
    FileConverter,
    FileDetector,
)
from qdrant_loader.utils.logging import LoggingConfig

# Suppress XML parsing warning
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


logger = LoggingConfig.get_logger(__name__)


class PublicDocsConnector(BaseConnector):
    """Connector for public documentation sources."""

    def __init__(self, config: PublicDocsSourceConfig):
        """Initialize the connector.

        Args:
            config: Configuration for the public documentation source
            state_manager: State manager for tracking document states
        """
        super().__init__(config)
        self.config = config
        self.logger = LoggingConfig.get_logger(__name__)
        self._initialized = False
        self.base_url = str(config.base_url)
        self.url_queue = deque()
        self.visited_urls = set()
        self.version = config.version
        self.logger.debug(
            "Initialized PublicDocsConnector",
            base_url=self.base_url,
            version=self.version,
            exclude_paths=config.exclude_paths,
            path_pattern=config.path_pattern,
        )

        # Initialize file conversion components if enabled
        self.file_converter: FileConverter | None = None
        self.file_detector: FileDetector | None = None
        self.attachment_downloader: AttachmentDownloader | None = None

        if config.enable_file_conversion:
            self.file_detector = FileDetector()
            # FileConverter will be initialized when file_conversion_config is set

    async def __aenter__(self):
        """Async context manager entry."""
        if not self._initialized:
            self._client = aiohttp.ClientSession()
            self._initialized = True

            # Initialize attachment downloader with aiohttp session if needed
            if self.config.download_attachments:
                # Convert aiohttp session to requests session for compatibility
                import requests

                session = requests.Session()
                self.attachment_downloader = AttachmentDownloader(session=session)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._initialized and self._client:
            await self._client.close()
            self._client = None
            self._initialized = False

    @property
    def client(self) -> aiohttp.ClientSession:
        """Get the client session."""
        if not self._client or not self._initialized:
            raise RuntimeError(
                "Client session not initialized. Use async context manager."
            )
        return self._client

    def set_file_conversion_config(self, config: FileConversionConfig) -> None:
        """Set the file conversion configuration.

        Args:
            config: File conversion configuration
        """
        if self.config.enable_file_conversion and self.file_detector:
            self.file_converter = FileConverter(config)
            if self.config.download_attachments and self.attachment_downloader:
                # Reinitialize attachment downloader with file conversion config
                import requests

                session = requests.Session()
                self.attachment_downloader = AttachmentDownloader(
                    session=session,
                    file_conversion_config=config,
                    enable_file_conversion=True,
                    max_attachment_size=config.max_file_size,
                )

    def _should_process_url(self, url: str) -> bool:
        """Check if a URL should be processed based on configuration."""
        self.logger.debug(f"Checking if URL should be processed: {url}")

        # Check if URL matches base URL
        if not url.startswith(str(self.base_url)):
            self.logger.debug(f"URL does not match base URL: {url}")
            return False
        self.logger.debug(f"URL matches base URL: {url}")

        # Extract path from URL
        path = url[len(str(self.base_url)) :]
        self.logger.debug(f"Extracted path from URL: {path}")

        # Check exclude paths
        for exclude_path in self.config.exclude_paths:
            self.logger.debug(f"Checking exclude path: {exclude_path} against {path}")
            if fnmatch.fnmatch(path, exclude_path):
                self.logger.debug(f"URL path matches exclude pattern: {path}")
                return False
        self.logger.debug(f"URL path not in exclude paths: {path}")

        # Check path pattern
        if self.config.path_pattern is None:
            self.logger.debug("No path pattern specified, skipping pattern check")
            return True

        self.logger.debug(f"Checking path pattern: {self.config.path_pattern}")
        if not fnmatch.fnmatch(path, self.config.path_pattern):
            self.logger.debug(f"URL path does not match pattern: {path}")
            return False
        self.logger.debug(f"URL path matches pattern: {path}")

        self.logger.debug(f"URL passed all checks, will be processed: {url}")
        return True

    async def get_documents(self) -> list[Document]:
        """Get documentation pages from the source.

        Returns:
            List of documents

        Raises:
            RuntimeError: If connector is not initialized
            RuntimeError: If change detector is not initialized
        """
        if not self._initialized:
            raise RuntimeError(
                "Connector not initialized. Use the connector as an async context manager."
            )

        try:
            # Get all pages
            pages = await self._get_all_pages()
            self.logger.debug(f"Found {len(pages)} pages to process", pages=pages)
            documents = []

            for page in pages:
                try:
                    if not self._should_process_url(page):
                        self.logger.debug("Skipping URL", url=page)
                        continue

                    self.logger.debug("Processing URL", url=page)

                    content, title = await self._process_page(page)
                    if (
                        content and content.strip()
                    ):  # Only add documents with non-empty content
                        # Generate a consistent document ID based on the URL
                        doc_id = str(hash(page))  # Use URL hash as document ID
                        doc = Document(
                            id=doc_id,
                            title=title,
                            content=content,
                            content_type="html",
                            metadata={
                                "title": title,
                                "url": page,
                                "version": self.version,
                            },
                            source_type=self.config.source_type,
                            source=self.config.source,
                            url=page,
                            # For public docs, we don't have a created or updated date. So we use a very old date.
                            # The content hash will be the same for the same page, so it will be update if the hash changes.
                            created_at=datetime(1970, 1, 1, 0, 0, 0, 0, UTC),
                            updated_at=datetime(1970, 1, 1, 0, 0, 0, 0, UTC),
                        )
                        self.logger.debug(
                            "Created document",
                            url=page,
                            content_length=len(content),
                            title=title,
                            doc_id=doc_id,
                        )
                        documents.append(doc)
                        self.logger.debug(
                            "Document created",
                            url=page,
                            content_length=len(content),
                            title=title,
                            doc_id=doc_id,
                        )

                        # Process attachments if enabled
                        if (
                            self.config.download_attachments
                            and self.attachment_downloader
                        ):
                            # We need to get the HTML again to extract attachments
                            try:
                                response = await self.client.get(page)
                                html = await response.text()
                                attachment_metadata = self._extract_attachments(
                                    html, page, doc_id
                                )

                                if attachment_metadata:
                                    self.logger.info(
                                        "Processing attachments for PublicDocs page",
                                        page_url=page,
                                        attachment_count=len(attachment_metadata),
                                    )

                                    attachment_documents = await self.attachment_downloader.download_and_process_attachments(
                                        attachment_metadata, doc
                                    )
                                    documents.extend(attachment_documents)

                                    self.logger.debug(
                                        "Processed attachments for PublicDocs page",
                                        page_url=page,
                                        processed_count=len(attachment_documents),
                                    )
                            except Exception as e:
                                self.logger.error(
                                    f"Failed to process attachments for page {page}: {e}"
                                )
                                # Continue processing even if attachment processing fails
                    else:
                        self.logger.warning(
                            "Skipping page with empty content",
                            url=page,
                            title=title,
                        )
                except Exception as e:
                    self.logger.error(f"Failed to process page {page}: {e}")
                    continue

            if not documents:
                self.logger.warning("No valid documents found to process")
                return []

            return documents

        except Exception as e:
            self.logger.error("Failed to get documentation", error=str(e))
            raise

    async def _process_page(self, url: str) -> tuple[str | None, str | None]:
        """Process a single documentation page.

        Returns:
            tuple[str | None, str | None]: A tuple containing (content, title)

        Raises:
            ConnectorNotInitializedError: If connector is not initialized
            HTTPRequestError: If HTTP request fails
            PageProcessingError: If page processing fails
        """
        self.logger.debug("Starting page processing", url=url)
        try:
            if not self._initialized:
                raise ConnectorNotInitializedError(
                    "Connector not initialized. Use async context manager."
                )

            self.logger.debug("Making HTTP request", url=url)
            try:
                response = await self.client.get(url)
                response.raise_for_status()  # This is a synchronous method, no need to await
            except aiohttp.ClientError as e:
                raise HTTPRequestError(url=url, message=str(e)) from e

            self.logger.debug(
                "HTTP request successful", url=url, status_code=response.status
            )

            try:
                # Extract links for crawling
                self.logger.debug("Extracting links from page", url=url)
                html = await response.text()
                links = self._extract_links(html, url)
                self.logger.debug(
                    "Adding new links to queue", url=url, new_links=len(links)
                )
                for link in links:
                    if link not in self.visited_urls:
                        self.url_queue.append(link)

                # Extract title from raw HTML
                title = self._extract_title(html)
                self.logger.debug("Extracted title", url=url, title=title)

                if self.config.content_type == "html":
                    self.logger.debug("Processing HTML content", url=url)
                    content = self._extract_content(html)
                    self.logger.debug(
                        "HTML content processed",
                        url=url,
                        content_length=len(content) if content else 0,
                    )
                    return content, title
                else:
                    self.logger.debug("Processing raw content", url=url)
                    self.logger.debug(
                        "Raw content length",
                        url=url,
                        content_length=len(html) if html else 0,
                    )
                    return html, title
            except Exception as e:
                raise DocumentProcessingError(
                    f"Failed to process page {url}: {e!s}"
                ) from e

        except (
            ConnectorNotInitializedError,
            HTTPRequestError,
            DocumentProcessingError,
        ):
            raise
        except Exception as e:
            raise ConnectorError(
                f"Unexpected error processing page {url}: {e!s}"
            ) from e

    def _extract_links(self, html: str, current_url: str) -> list[str]:
        """Extract all links from the HTML content."""
        self.logger.debug(
            "Starting link extraction", current_url=current_url, html_length=len(html)
        )
        soup = BeautifulSoup(html, "html.parser")
        links = []

        for link in soup.find_all("a", href=True):
            href = str(cast(BeautifulSoup, link)["href"])  # type: ignore
            # Convert relative URLs to absolute
            absolute_url = urljoin(current_url, href)

            # Only include links that are under the base URL
            if absolute_url.startswith(self.base_url):
                # Remove fragment identifiers
                absolute_url = absolute_url.split("#")[0]
                links.append(absolute_url)
                self.logger.debug(
                    "Found valid link", original_href=href, absolute_url=absolute_url
                )

        self.logger.debug("Link extraction completed", total_links=len(links))
        return links

    def _extract_content(self, html: str) -> str:
        """Extract the main content from HTML using configured selectors."""
        self.logger.debug("Starting content extraction", html_length=len(html))
        self.logger.debug("HTML content preview", preview=html[:1000])
        soup = BeautifulSoup(html, "html.parser")
        self.logger.debug("HTML parsed successfully")

        # Log the selectors being used
        self.logger.debug(
            "Using selectors",
            content_selector=self.config.selectors.content,
            remove_selectors=self.config.selectors.remove,
            code_blocks_selector=self.config.selectors.code_blocks,
        )

        # Remove unwanted elements
        for selector in self.config.selectors.remove:
            self.logger.debug(f"Processing selector: {selector}")
            elements = soup.select(selector)
            self.logger.debug(
                f"Found {len(elements)} elements for selector: {selector}"
            )
            for element in elements:
                element.decompose()

        # Find main content
        self.logger.debug(
            f"Looking for main content with selector: {self.config.selectors.content}"
        )
        content = soup.select_one(self.config.selectors.content)
        if not content:
            self.logger.warning(
                "Could not find main content using selector",
                selector=self.config.selectors.content,
            )
            # Log the first 1000 characters of the HTML to help debug
            self.logger.debug("HTML content preview", preview=html[:1000])
            return ""

        self.logger.debug(
            "Found main content element", content_length=len(content.text)
        )

        # Preserve code blocks
        self.logger.debug(
            f"Looking for code blocks with selector: {self.config.selectors.code_blocks}"
        )
        code_blocks = content.select(self.config.selectors.code_blocks)
        self.logger.debug(f"Found {len(code_blocks)} code blocks")

        for code_block in code_blocks:
            code_text = code_block.text
            if code_text:  # Only process non-empty code blocks
                new_code = BeautifulSoup(f"\n```\n{code_text}\n```\n", "html.parser")
                if new_code.string:  # Ensure we have a valid string to replace with
                    code_block.replace_with(new_code.string)  # type: ignore[arg-type]

        extracted_text = content.get_text(separator="\n", strip=True)
        self.logger.debug(
            "Content extraction completed",
            extracted_length=len(extracted_text),
            preview=extracted_text[:200] if extracted_text else "",
        )
        return extracted_text

    def _extract_title(self, html: str) -> str:
        """Extract the title from HTML content."""
        self.logger.debug("Starting title extraction", html_length=len(html))
        soup = BeautifulSoup(html, "html.parser")

        # Debug: Log the first 500 characters of the HTML to see what we're parsing
        self.logger.debug("HTML preview", preview=html[:500])

        # Debug: Log all title tags found
        title_tags = soup.find_all("title")
        self.logger.debug(
            "Found title tags",
            count=len(title_tags),
            tags=[str(tag) for tag in title_tags],
        )

        # First try to find the title in head/title
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)
            self.logger.debug("Found title in title tag", title=title)
            return title

        # Then try to find a title in the main content
        content = soup.select_one(self.config.selectors.content)
        if content:
            # Look for h1 in the content
            h1 = content.find("h1")
            if h1:
                title = h1.get_text(strip=True)
                self.logger.debug("Found title in content", title=title)
                return title

            # Look for the first heading
            heading = content.find(["h1", "h2", "h3", "h4", "h5", "h6"])
            if heading:
                title = heading.get_text(strip=True)
                self.logger.debug("Found title in heading", title=title)
                return title

        # If no title found, use a default
        default_title = "Untitled Document"
        self.logger.warning(
            "No title found, using default", default_title=default_title
        )
        return default_title

    def _extract_attachments(
        self, html: str, page_url: str, document_id: str
    ) -> list[AttachmentMetadata]:
        """Extract attachment links from HTML content.

        Args:
            html: HTML content to parse
            page_url: URL of the current page
            document_id: ID of the parent document

        Returns:
            List of attachment metadata objects
        """
        if not self.config.download_attachments:
            return []

        self.logger.debug("Starting attachment extraction", page_url=page_url)
        soup = BeautifulSoup(html, "html.parser")
        attachments = []

        # Use configured selectors to find attachment links
        for selector in self.config.attachment_selectors:
            links = soup.select(selector)
            self.logger.debug(f"Found {len(links)} links for selector: {selector}")

            for link in links:
                href = link.get("href")
                if not href:
                    continue

                # Convert relative URLs to absolute
                absolute_url = urljoin(page_url, str(href))

                # Extract filename from URL
                parsed_url = urlparse(absolute_url)
                filename = (
                    parsed_url.path.split("/")[-1] if parsed_url.path else "unknown"
                )

                # Try to determine file extension and MIME type
                file_ext = filename.split(".")[-1].lower() if "." in filename else ""
                mime_type = self._get_mime_type_from_extension(file_ext)

                # Create attachment metadata
                attachment = AttachmentMetadata(
                    id=f"{document_id}_{len(attachments)}",  # Simple ID generation
                    filename=filename,
                    size=0,  # We don't know the size until we download
                    mime_type=mime_type,
                    download_url=absolute_url,
                    parent_document_id=document_id,
                    created_at=None,
                    updated_at=None,
                    author=None,
                )
                attachments.append(attachment)

                self.logger.debug(
                    "Found attachment",
                    filename=filename,
                    url=absolute_url,
                    mime_type=mime_type,
                )

        self.logger.debug(f"Extracted {len(attachments)} attachments from page")
        return attachments

    def _get_mime_type_from_extension(self, extension: str) -> str:
        """Get MIME type from file extension.

        Args:
            extension: File extension (without dot)

        Returns:
            MIME type string
        """
        mime_types = {
            "pdf": "application/pdf",
            "doc": "application/msword",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "xls": "application/vnd.ms-excel",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "ppt": "application/vnd.ms-powerpoint",
            "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "txt": "text/plain",
            "csv": "text/csv",
            "json": "application/json",
            "xml": "application/xml",
            "zip": "application/zip",
        }
        return mime_types.get(extension, "application/octet-stream")

    async def _get_all_pages(self) -> list[str]:
        """Get all pages from the source.

        Returns:
            List of page URLs

        Raises:
            ConnectorNotInitializedError: If connector is not initialized
            HTTPRequestError: If HTTP request fails
            PublicDocsConnectorError: If page discovery fails
        """
        if not self._initialized:
            raise ConnectorNotInitializedError(
                "Connector not initialized. Use async context manager."
            )

        try:
            self.logger.debug(
                "Fetching pages from base URL",
                base_url=str(self.config.base_url),
                path_pattern=self.config.path_pattern,
            )

            async with aiohttp.ClientSession() as client:
                try:
                    response = await client.get(str(self.config.base_url))
                    response.raise_for_status()
                except aiohttp.ClientError as e:
                    raise HTTPRequestError(
                        url=str(self.config.base_url), message=str(e)
                    ) from e

                self.logger.debug(
                    "HTTP request successful", status_code=response.status
                )

                try:
                    html = await response.text()
                    self.logger.debug(
                        "Received HTML response",
                        status_code=response.status,
                        content_length=len(html),
                    )

                    soup = BeautifulSoup(html, "html.parser")
                    pages = [str(self.config.base_url)]  # Start with the base URL

                    for link in soup.find_all("a"):
                        try:
                            href = str(cast(BeautifulSoup, link)["href"])  # type: ignore
                            if not href or not isinstance(href, str):
                                continue

                            # Skip anchor links
                            if href.startswith("#"):
                                continue

                            # Convert relative URLs to absolute
                            absolute_url = urljoin(str(self.config.base_url), href)

                            # Remove any fragment identifiers
                            absolute_url = absolute_url.split("#")[0]

                            # Check if URL matches our criteria
                            if (
                                absolute_url.startswith(str(self.config.base_url))
                                and absolute_url not in pages
                                and not any(
                                    exclude in absolute_url
                                    for exclude in self.config.exclude_paths
                                )
                                and (
                                    not self.config.path_pattern
                                    or fnmatch.fnmatch(
                                        absolute_url, self.config.path_pattern
                                    )
                                )
                            ):
                                self.logger.debug(
                                    "Found valid page URL", url=absolute_url
                                )
                                pages.append(absolute_url)
                        except Exception as e:
                            self.logger.warning(
                                "Failed to process link",
                                href=str(link.get("href", "")),  # type: ignore
                                error=str(e),
                            )
                            continue

                    self.logger.debug(
                        "Page discovery completed",
                        total_pages=len(pages),
                        pages=pages,
                    )
                    return pages
                except Exception as e:
                    raise ConnectorError(
                        f"Failed to process page content: {e!s}"
                    ) from e

        except (ConnectorNotInitializedError, HTTPRequestError, ConnectorError):
            raise
        except Exception as e:
            raise ConnectorError(f"Unexpected error getting pages: {e!s}") from e
