"""Public documentation connector implementation."""

import asyncio
import re
from collections import deque
from datetime import datetime
from typing import List, Optional, Set, cast
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from qdrant_loader.connectors.public_docs.config import PublicDocsSourceConfig
from qdrant_loader.core.document import Document
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class PublicDocsConnector:
    """Generic connector for public documentation websites."""

    def __init__(self, source_config: PublicDocsSourceConfig):
        """Initialize the connector with source configuration."""
        self.source_config = source_config
        # Convert HttpUrl to string before applying string operations
        self.base_url = str(source_config.base_url).rstrip("/")
        self.version = source_config.version
        self.session = requests.Session()
        self.visited_urls: Set[str] = set()
        self.url_queue: deque = deque()
        self.logger = LoggingConfig.get_logger(__name__)

    def _get_page_url(self, path: str) -> str:
        """Construct the full URL for a documentation page."""
        return urljoin(self.base_url, path)

    def _should_process_url(self, url: str) -> bool:
        """Determine if a URL should be processed based on configuration."""
        # Check if URL matches the base URL
        if not url.startswith(self.base_url):
            return False

        # Get the path part of the URL
        path = urlparse(url).path

        # Check if URL is in exclude paths
        for exclude_path in self.source_config.exclude_paths:
            if exclude_path.format(version=self.version) in path:
                return False

        # Check if URL matches the path pattern if specified
        if self.source_config.path_pattern:
            pattern = self.source_config.path_pattern.format(version=self.version)
            if not re.match(pattern, path):
                return False

        return True

    def _extract_links(self, html: str, current_url: str) -> List[str]:
        """Extract all links from the HTML content."""
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

        return links

    def _extract_content(self, html: str) -> str:
        """Extract the main content from HTML using configured selectors."""
        soup = BeautifulSoup(html, "html.parser")

        # Remove unwanted elements
        for selector in self.source_config.selectors.remove:
            for element in soup.select(selector):
                element.decompose()

        # Find main content
        content = soup.select_one(self.source_config.selectors.content)
        if not content:
            self.logger.warning(
                "Could not find main content using selector",
                selector=self.source_config.selectors.content,
            )
            return ""

        # Preserve code blocks
        for code_block in content.select(self.source_config.selectors.code_blocks):
            code_block.replace_with(BeautifulSoup(f"\n```\n{code_block.text}\n```\n", "html.parser").string)  # type: ignore

        return content.get_text(separator="\n", strip=True)

    async def _process_page(self, url: str) -> Optional[str]:
        """Process a single documentation page."""
        try:
            response = await asyncio.to_thread(self.session.get, url)
            response.raise_for_status()

            # Extract links for crawling
            links = self._extract_links(response.text, url)
            for link in links:
                if link not in self.visited_urls:
                    self.url_queue.append(link)

            if self.source_config.content_type == "html":
                return self._extract_content(response.text)
            else:
                return response.text

        except requests.RequestException as e:
            self.logger.error("Failed to process page", url=url, error=str(e))
            return None

    async def get_documentation(self) -> List[Document]:
        """Fetch and process all documentation pages using crawling."""
        self.logger.info(
            "Starting documentation fetch",
            base_url=self.base_url,
            version=self.version,
        )

        documents = []
        # Start with the base URL
        self.url_queue.append(self.base_url)

        while self.url_queue:
            current_url = self.url_queue.popleft()

            # Skip if already visited
            if current_url in self.visited_urls:
                continue

            # Mark as visited
            self.visited_urls.add(current_url)

            # Check if URL should be processed
            if not self._should_process_url(current_url):
                continue

            self.logger.debug("Processing page", url=current_url)
            page_content = await self._process_page(current_url)

            if page_content:
                doc = Document(
                    id=current_url,
                    content=page_content,
                    source=self.base_url,
                    source_type="public-docs",
                    url=current_url,
                    metadata={
                        "version": self.version,
                        "content_type": self.source_config.content_type,
                    },
                    last_updated=datetime.now(),
                )
                documents.append(doc)
                self.logger.info("Successfully processed page", url=current_url)
            else:
                self.logger.warning("Failed to process page", url=current_url)

        self.logger.info(
            "Finished crawling",
            processed_pages=len(documents),
            total_visited=len(self.visited_urls),
        )
        return documents
