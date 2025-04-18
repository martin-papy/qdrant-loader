"""Public documentation connector implementation."""

import asyncio
import re
import warnings
from collections import deque
from datetime import UTC, datetime
from typing import cast
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from qdrant_loader.connectors.public_docs.config import PublicDocsSourceConfig
from qdrant_loader.core.document import Document
from qdrant_loader.core.state.models import DocumentStateRecord
from qdrant_loader.core.state.state_change_detector import StateChangeDetector
from qdrant_loader.core.state.state_manager import StateManager
from qdrant_loader.utils.logging import LoggingConfig

# Suppress XML parsing warning
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


logger = LoggingConfig.get_logger(__name__)


class PublicDocsConnector:
    """Generic connector for public documentation websites."""

    def __init__(
        self,
        source_config: PublicDocsSourceConfig,
        state_manager: StateManager,
    ):
        """Initialize the connector with source configuration."""
        self.source_config = source_config
        # Convert HttpUrl to string before applying string operations
        self.base_url = str(source_config.base_url).rstrip("/")
        self.version = source_config.version
        self.session = requests.Session()
        self.visited_urls: set[str] = set()
        self.url_queue: deque = deque()
        self.logger = LoggingConfig.get_logger(__name__)
        self.state_manager = state_manager
        self.change_detector = StateChangeDetector(source_config, state_manager)
        self.logger.debug(
            "Initialized PublicDocsConnector",
            base_url=self.base_url,
            version=self.version,
            exclude_paths=self.source_config.exclude_paths,
            path_pattern=self.source_config.path_pattern,
        )

    def _get_page_url(self, path: str) -> str:
        """Construct the full URL for a documentation page."""
        url = urljoin(self.base_url, path)
        self.logger.debug("Constructed page URL", path=path, full_url=url)
        return url

    def _should_process_url(self, url: str) -> bool:
        """Determine if a URL should be processed based on configuration."""
        self.logger.debug("Checking if URL should be processed", url=url)

        # Check if URL matches the base URL
        if not url.startswith(self.base_url):
            self.logger.debug(
                "URL rejected: does not match base URL", url=url, base_url=self.base_url
            )
            return False

        # Get the path part of the URL
        path = urlparse(url).path
        self.logger.debug("Extracted URL path", url=url, path=path)

        # Check if URL is in exclude paths
        for exclude_path in self.source_config.exclude_paths:
            formatted_exclude = exclude_path.format(version=self.version)
            if formatted_exclude in path:
                self.logger.debug(
                    "URL rejected: matches exclude path", url=url, exclude_path=formatted_exclude
                )
                return False

        # Check if URL matches the path pattern if specified
        if self.source_config.path_pattern:
            pattern = self.source_config.path_pattern.format(version=self.version)
            if not re.match(pattern, path):
                self.logger.debug(
                    "URL rejected: does not match path pattern", url=url, pattern=pattern
                )
                return False

        self.logger.debug("URL accepted for processing", url=url)
        return True

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
            content_selector=self.source_config.selectors.content,
            remove_selectors=self.source_config.selectors.remove,
            code_blocks_selector=self.source_config.selectors.code_blocks,
        )

        # Remove unwanted elements
        for selector in self.source_config.selectors.remove:
            self.logger.debug(f"Removing elements matching selector: {selector}")
            elements = soup.select(selector)
            self.logger.debug(f"Found {len(elements)} elements to remove")
            for element in elements:
                element.decompose()

        # Find main content
        self.logger.debug(
            f"Looking for main content with selector: {self.source_config.selectors.content}"
        )
        content = soup.select_one(self.source_config.selectors.content)
        if not content:
            self.logger.warning(
                "Could not find main content using selector",
                selector=self.source_config.selectors.content,
            )
            # Log the first 1000 characters of the HTML to help debug
            self.logger.debug("HTML content preview", preview=html[:1000])
            return ""

        self.logger.debug("Found main content element", content_length=len(content.text))

        # Preserve code blocks
        self.logger.debug(
            f"Looking for code blocks with selector: {self.source_config.selectors.code_blocks}"
        )
        code_blocks = content.select(self.source_config.selectors.code_blocks)
        self.logger.debug(f"Found {len(code_blocks)} code blocks")

        for code_block in code_blocks:
            code_text = code_block.text
            if code_text:  # Only process non-empty code blocks
                new_code = BeautifulSoup(f"\n```\n{code_text}\n```\n", "html.parser")
                if new_code.string:  # Ensure we have a valid string to replace with
                    code_block.replace_with(new_code.string)  # type: ignore

        extracted_text = content.get_text(separator="\n", strip=True)
        self.logger.debug("Content extraction completed", extracted_length=len(extracted_text))
        return extracted_text

    def _extract_title(self, html: str) -> str:
        """Extract the title from HTML content."""
        self.logger.debug("Starting title extraction", html_length=len(html))
        soup = BeautifulSoup(html, "html.parser")

        # First try to find a title in the main content
        content = soup.select_one(self.source_config.selectors.content)
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

        # Fallback to page title
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)
            self.logger.debug("Found title in title tag", title=title)
            return title

        # If no title found, use a default
        default_title = "Untitled Document"
        self.logger.warning("No title found, using default", default_title=default_title)
        return default_title

    async def _process_page(self, url: str) -> str | None:
        """Process a single documentation page."""
        self.logger.debug("Starting page processing", url=url)
        try:
            self.logger.debug("Making HTTP request", url=url)
            response = await asyncio.to_thread(self.session.get, url)
            response.raise_for_status()
            self.logger.debug("HTTP request successful", url=url, status_code=response.status_code)

            # Extract links for crawling
            self.logger.debug("Extracting links from page", url=url)
            links = self._extract_links(response.text, url)
            self.logger.debug("Adding new links to queue", url=url, new_links=len(links))
            for link in links:
                if link not in self.visited_urls:
                    self.url_queue.append(link)

            if self.source_config.content_type == "html":
                self.logger.debug("Processing HTML content", url=url)
                content = self._extract_content(response.text)
                self.logger.debug("HTML content processed", url=url, content_length=len(content))
                return content
            else:
                self.logger.debug(
                    "Processing raw content", url=url, content_length=len(response.text)
                )
                return response.text

        except requests.RequestException as e:
            self.logger.error("Failed to process page", url=url, error=str(e))
            return None

    async def get_documentation(self) -> list[Document]:
        """Get all documentation pages."""
        self.logger.info("Starting documentation retrieval", base_url=self.base_url)

        # Get last ingestion time
        last_ingestion = await self.state_manager.get_last_ingestion(
            source_type="public_docs",
            source_name=str(self.source_config.base_url),
        )

        # Get all documents
        documents = []
        self.url_queue.append(self.base_url)

        while self.url_queue:
            url = self.url_queue.popleft()
            if url in self.visited_urls:
                continue

            self.visited_urls.add(url)
            content = await self._process_page(url)

            if content:
                doc = Document(
                    id=f"public_docs_{len(documents)}",
                    content=content,
                    source=str(self.source_config.base_url),
                    source_type="public_docs",
                    metadata={
                        "url": url,
                        "title": self._extract_title(content),
                        "content_hash": hash(content),
                        "last_modified": datetime.now().isoformat(),
                        "source": "public_docs",
                        "source_id": str(self.source_config.base_url),
                    },
                )
                documents.append(doc)

        self.logger.info(
            "Documentation retrieval completed",
            page_count=len(documents),
            visited_urls=len(self.visited_urls),
        )

        # Detect changes
        changes = await self.change_detector.detect_changes(
            documents,
            last_ingestion_time=last_ingestion.last_updated if last_ingestion else None,
        )

        # Update state for new and updated documents
        for doc in changes["new"] + changes["updated"]:
            doc_state = DocumentStateRecord(
                source_type="public_docs",
                source_name=str(self.source_config.base_url),
                document_id=doc.id,
                last_updated=datetime.now(UTC),
                last_ingested=datetime.now(UTC),
                is_deleted=False,
            )
            await self.state_manager.update_document_state(doc_state)

        # Mark deleted documents
        for doc in changes["deleted"]:
            await self.state_manager.mark_document_deleted(
                source_type="public_docs",
                source_name=str(self.source_config.base_url),
                document_id=doc.id,
            )

        # Update ingestion history
        await self.state_manager.update_ingestion(
            source_type="public_docs",
            source_name=str(self.source_config.base_url),
            status="success",
            count=len(documents),
        )

        return documents
