"""Public documentation connector implementation."""

import re
import warnings
from collections import deque
from datetime import datetime, timezone
from typing import cast
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from qdrant_loader.connectors.exceptions import (
    ConnectorError,
    ConnectorNotInitializedError,
    DocumentProcessingError,
    HTTPRequestError,
)
from qdrant_loader.connectors.publicdocs.config import PublicDocsSourceConfig
from qdrant_loader.core.document import Document
from qdrant_loader.utils.logging import LoggingConfig

# Suppress XML parsing warning
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


logger = LoggingConfig.get_logger(__name__)


class PublicDocsConnector:
    """Connector for public documentation sources."""

    def __init__(self, config: PublicDocsSourceConfig):
        """Initialize the connector.

        Args:
            config: Configuration for the public documentation source
            state_manager: State manager for tracking document states
        """
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

    async def __aenter__(self):
        """Async context manager entry."""
        if not self._initialized:
            self._client = aiohttp.ClientSession()
            self._initialized = True
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
            raise RuntimeError("Client session not initialized. Use async context manager.")
        return self._client

    def _should_process_url(self, url: str) -> bool:
        """Determine if a URL should be processed based on configuration."""
        # Check if URL matches the base URL
        if not url.startswith(self.base_url):
            return False

        # Get the path part of the URL
        path = urlparse(url).path

        # Check if URL is in exclude paths
        for exclude_path in self.config.exclude_paths:
            if exclude_path in path:
                return False

        # Check if URL matches the path pattern if specified
        if self.config.path_pattern:
            pattern = self.config.path_pattern
            if not re.match(pattern, path):
                return False

        return True

    async def get_documentation(self) -> list[Document]:
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

                    content, title = await self._process_page(page)
                    if content and content.strip():  # Only add documents with non-empty content
                        # Generate a consistent document ID based on the URL
                        doc_id = str(hash(page))  # Use URL hash as document ID
                        doc = Document(
                            id=doc_id,
                            title=title,
                            content=content,
                            metadata={
                                "title": title,
                                "url": page,
                                "last_modified": datetime.now(timezone.utc).isoformat(),
                            },
                            source_type=self.config.source_type,
                            source=self.config.source,
                            url=page,
                            created_at=datetime.now(timezone.utc),
                            updated_at=datetime.now(timezone.utc),
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
            async with aiohttp.ClientSession() as client:
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                except aiohttp.ClientError as e:
                    raise HTTPRequestError(url=url, message=str(e)) from e

                self.logger.debug("HTTP request successful", url=url, status_code=response.status)

                try:
                    # Extract links for crawling
                    self.logger.debug("Extracting links from page", url=url)
                    html = await response.text()
                    links = self._extract_links(html, url)
                    self.logger.debug("Adding new links to queue", url=url, new_links=len(links))
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
                    raise DocumentProcessingError(f"Failed to process page {url}: {e!s}") from e

        except (ConnectorNotInitializedError, HTTPRequestError, DocumentProcessingError):
            raise
        except Exception as e:
            raise ConnectorError(f"Unexpected error processing page {url}: {e!s}") from e

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
                self.logger.debug("Found valid link", original_href=href, absolute_url=absolute_url)

        self.logger.debug("Link extraction completed", total_links=len(links))
        return links

    def _extract_content(self, html: str) -> str:
        """Extract the main content from HTML using configured selectors."""
        self.logger.debug("Starting content extraction", html_length=len(html))
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
            self.logger.debug(f"Removing elements matching selector: {selector}")
            elements = soup.select(selector)
            self.logger.debug(f"Found {len(elements)} elements to remove")
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

        self.logger.debug("Found main content element", content_length=len(content.text))

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
            "Found title tags", count=len(title_tags), tags=[str(tag) for tag in title_tags]
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
        self.logger.warning("No title found, using default", default_title=default_title)
        return default_title

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
                    raise HTTPRequestError(url=str(self.config.base_url), message=str(e)) from e

                self.logger.debug("HTTP request successful", status_code=response.status)

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
                                    exclude in absolute_url for exclude in self.config.exclude_paths
                                )
                                and (
                                    not self.config.path_pattern
                                    or re.match(self.config.path_pattern, absolute_url)
                                )
                            ):
                                self.logger.debug("Found valid page URL", url=absolute_url)
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
                    raise ConnectorError(f"Failed to process page content: {e!s}") from e

        except (ConnectorNotInitializedError, HTTPRequestError, ConnectorError):
            raise
        except Exception as e:
            raise ConnectorError(f"Unexpected error getting pages: {e!s}") from e
