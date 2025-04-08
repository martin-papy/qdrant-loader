"""Public documentation connector implementation."""

from typing import List, Optional, Set
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
from collections import deque
from .config import PublicDocsSourceConfig

logger = logging.getLogger(__name__)

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
            href = link["href"]
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
            logger.warning("Could not find main content using selector: %s", 
                         self.source_config.selectors.content)
            return ""
            
        # Preserve code blocks
        for code_block in content.select(self.source_config.selectors.code_blocks):
            code_block.replace_with(f"\n```\n{code_block.text}\n```\n")
            
        return content.get_text(separator="\n", strip=True)
    
    def _process_page(self, url: str) -> Optional[str]:
        """Process a single documentation page."""
        try:
            response = self.session.get(url)
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
            logger.error("Failed to process page %s: %s", url, str(e))
            return None
    
    def get_documentation(self) -> List[str]:
        """Fetch and process all documentation pages using crawling."""
        logger.info("Starting documentation fetch from %s (version: %s)", 
                   self.base_url, self.version)
        
        content = []
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
                
            logger.debug("Processing page: %s", current_url)
            page_content = self._process_page(current_url)
            
            if page_content:
                content.append(page_content)
                logger.info("Successfully processed page: %s", current_url)
            else:
                logger.warning("Failed to process page: %s", current_url)
                
        logger.info("Finished crawling. Processed %d pages.", len(content))
        return content 