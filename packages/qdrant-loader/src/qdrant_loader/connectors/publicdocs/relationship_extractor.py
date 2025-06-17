"""
PublicDocs Relationship Extractor

Extracts metadata and relationships from public documentation websites including
author information, timestamps, web hierarchy, cross-references, and
web-specific metadata.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from qdrant_loader.connectors.metadata.base import (
    BaseMetadataExtractor,
    MetadataExtractionConfig,
)

logger = logging.getLogger(__name__)


class PublicDocsRelationshipExtractor(BaseMetadataExtractor):
    """
    Extracts relationships and metadata from public documentation websites.

    Handles:
    - Author metadata from HTML meta tags and content analysis
    - Publication/modification timestamps from meta tags and content
    - Web hierarchy relationships (navigation, breadcrumbs)
    - Cross-references (internal links, external links, citations)
    - Web-specific metadata (URL structure, domain info, SEO metadata)
    """

    def __init__(self, config: MetadataExtractionConfig, base_url: str):
        """Initialize the PublicDocs relationship extractor.

        Args:
            config: Metadata extraction configuration
            base_url: Base URL for the documentation site
        """
        super().__init__(config)
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc

    def _extract_author_metadata(
        self, content: str, context: Dict[str, Any]
    ) -> List[Dict[str, Any]] | None:
        """Extract author information from HTML meta tags and content.

        Args:
            content: HTML content
            context: Contains url, title, and other page metadata

        Returns:
            List of author metadata dictionaries
        """
        authors = []
        url = context.get("url", "")

        try:
            soup = BeautifulSoup(content, "html.parser")

            # Extract from meta tags
            meta_authors = self._extract_authors_from_meta(soup)
            authors.extend(meta_authors)

            # Extract from content patterns
            content_authors = self._extract_authors_from_content(soup, url)
            authors.extend(content_authors)

            # Extract from structured data (JSON-LD, microdata)
            structured_authors = self._extract_authors_from_structured_data(soup)
            authors.extend(structured_authors)

        except Exception as e:
            self.logger.warning(f"Error extracting authors from {url}: {e}")

        return authors if authors else None

    def _extract_timestamp_metadata(
        self, content: str, context: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        """Extract timestamp information from meta tags and content.

        Args:
            content: HTML content
            context: Contains url, title, and other page metadata

        Returns:
            Dictionary containing timestamp metadata
        """
        timestamps = {}
        url = context.get("url", "")

        try:
            soup = BeautifulSoup(content, "html.parser")

            # Extract from meta tags
            meta_timestamps = self._extract_timestamps_from_meta(soup)
            timestamps.update(meta_timestamps)

            # Extract from content patterns
            content_timestamps = self._extract_timestamps_from_content(soup, url)
            timestamps.update(content_timestamps)

            # Extract from structured data
            structured_timestamps = self._extract_timestamps_from_structured_data(soup)
            timestamps.update(structured_timestamps)

        except Exception as e:
            self.logger.warning(f"Error extracting timestamps from {url}: {e}")

        return timestamps if timestamps else None

    def _extract_relationship_metadata(
        self, content: str, context: Dict[str, Any]
    ) -> List[Dict[str, Any]] | None:
        """Extract web hierarchy and navigation relationships.

        Args:
            content: HTML content
            context: Contains url, title, and other page metadata

        Returns:
            List of relationship metadata dictionaries
        """
        relationships = []
        url = context.get("url", "")

        try:
            soup = BeautifulSoup(content, "html.parser")

            # Extract navigation hierarchy
            nav_relationships = self._extract_navigation_relationships(soup, url)
            relationships.extend(nav_relationships)

            # Extract breadcrumb relationships
            breadcrumb_relationships = self._extract_breadcrumb_relationships(soup, url)
            relationships.extend(breadcrumb_relationships)

            # Extract table of contents relationships
            toc_relationships = self._extract_toc_relationships(soup, url)
            relationships.extend(toc_relationships)

        except Exception as e:
            self.logger.warning(f"Error extracting relationships from {url}: {e}")

        return relationships if relationships else None

    def _extract_cross_reference_metadata(
        self, content: str, context: Dict[str, Any]
    ) -> List[Dict[str, Any]] | None:
        """Extract internal and external links as cross-references.

        Args:
            content: HTML content
            context: Contains url, title, and other page metadata

        Returns:
            List of cross-reference metadata dictionaries
        """
        cross_references = []
        url = context.get("url", "")

        try:
            soup = BeautifulSoup(content, "html.parser")

            # Extract internal links
            internal_links = self._extract_internal_links(soup, url)
            cross_references.extend(internal_links)

            # Extract external links
            external_links = self._extract_external_links(soup, url)
            cross_references.extend(external_links)

            # Extract document/file links
            file_links = self._extract_file_links(soup, url)
            cross_references.extend(file_links)

            # Extract anchor/fragment links
            anchor_links = self._extract_anchor_links(soup, url)
            cross_references.extend(anchor_links)

        except Exception as e:
            self.logger.warning(f"Error extracting cross-references from {url}: {e}")

        return cross_references if cross_references else None

    def _extract_source_specific_metadata(
        self, content: str, context: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        """Extract web-specific metadata.

        Args:
            content: HTML content
            context: Contains url, title, and other page metadata

        Returns:
            Dictionary containing source-specific metadata
        """
        metadata = {}
        url = context.get("url", "")

        try:
            soup = BeautifulSoup(content, "html.parser")
            parsed_url = urlparse(url)

            # URL structure metadata
            metadata.update(
                {
                    "url": url,
                    "domain": parsed_url.netloc,
                    "path": parsed_url.path,
                    "query_params": parsed_url.query,
                    "fragment": parsed_url.fragment,
                    "url_depth": len([p for p in parsed_url.path.split("/") if p]),
                }
            )

            # HTML metadata
            html_meta = self._extract_html_metadata(soup)
            metadata.update(html_meta)

            # Content analysis
            content_meta = self._extract_content_analysis(soup)
            metadata.update(content_meta)

        except Exception as e:
            self.logger.warning(
                f"Error extracting source-specific metadata from {url}: {e}"
            )

        return metadata if metadata else None

    def extract_metadata(self, url: str, content: str) -> Dict[str, Any]:
        """Main entry point for metadata extraction from PublicDocs connector.

        Args:
            url: Page URL
            content: HTML content

        Returns:
            Dictionary containing all extracted metadata under 'enhanced_metadata' key
        """
        context = {
            "url": url,
            "content_type": "html",
            "extraction_timestamp": datetime.now().isoformat(),
            "source_type": "publicdocs",
        }

        # Use the base class method to extract metadata
        metadata = super().extract_metadata(content, context)

        # Return it under the enhanced_metadata key as expected by the connector
        return {"enhanced_metadata": metadata} if metadata else {}

    # Helper methods for author extraction
    def _extract_authors_from_meta(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract authors from HTML meta tags."""
        authors = []

        # Common meta tag patterns
        meta_patterns = [
            'meta[name="author"]',
            'meta[name="authors"]',
            'meta[property="article:author"]',
            'meta[name="DC.Creator"]',
            'meta[name="twitter:creator"]',
        ]

        for pattern in meta_patterns:
            for meta in soup.select(pattern):
                if isinstance(meta, Tag):
                    content_attr = meta.get("content")
                    if content_attr:
                        content = str(content_attr).strip()
                        if content:
                            authors.append(
                                {
                                    "name": content,
                                    "role": "author",
                                    "confidence_score": 0.8,
                                    "source": "meta_tag",
                                }
                            )

        return authors

    def _extract_authors_from_content(
        self, soup: BeautifulSoup, url: str
    ) -> List[Dict[str, Any]]:
        """Extract authors from content patterns."""
        authors = []

        # Common content selectors for author information
        author_selectors = [
            ".author",
            ".byline",
            ".contributor",
            ".writer",
            '[rel="author"]',
            ".post-author",
            ".article-author",
        ]

        for selector in author_selectors:
            for element in soup.select(selector):
                if isinstance(element, Tag):
                    text = element.get_text(strip=True)
                    if text and len(text) < 100:  # Reasonable author name length
                        authors.append(
                            {
                                "name": text,
                                "role": "content_author",
                                "confidence_score": 0.6,
                                "source": "content_analysis",
                            }
                        )

        return authors[:5]  # Limit to avoid noise

    def _extract_authors_from_structured_data(
        self, soup: BeautifulSoup
    ) -> List[Dict[str, Any]]:
        """Extract authors from structured data (JSON-LD, microdata)."""
        authors = []

        # Extract from JSON-LD
        for script in soup.find_all("script", type="application/ld+json"):
            if isinstance(script, Tag):
                try:
                    import json

                    script_content = getattr(script, "string", None)
                    if script_content:
                        data = json.loads(str(script_content))
                        if isinstance(data, dict):
                            author = data.get("author")
                            if author:
                                if isinstance(author, str):
                                    authors.append(
                                        {
                                            "name": author,
                                            "role": "structured_data_author",
                                            "confidence_score": 0.9,
                                            "source": "json_ld",
                                        }
                                    )
                                elif isinstance(author, dict) and author.get("name"):
                                    authors.append(
                                        {
                                            "name": author["name"],
                                            "role": "structured_data_author",
                                            "confidence_score": 0.9,
                                            "source": "json_ld",
                                        }
                                    )
                except (json.JSONDecodeError, KeyError):
                    continue

        return authors

    # Helper methods for timestamp extraction
    def _extract_timestamps_from_meta(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract timestamps from meta tags."""
        timestamps = {}

        # Publication date patterns
        pub_patterns = [
            ('meta[property="article:published_time"]', "published"),
            ('meta[name="publication_date"]', "published"),
            ('meta[name="DC.Date.Created"]', "created"),
            ('meta[name="date"]', "published"),
        ]

        # Modified date patterns
        mod_patterns = [
            ('meta[property="article:modified_time"]', "modified"),
            ('meta[name="last-modified"]', "modified"),
            ('meta[name="DC.Date.Modified"]', "modified"),
        ]

        for pattern, timestamp_type in pub_patterns + mod_patterns:
            meta = soup.select_one(pattern)
            if isinstance(meta, Tag):
                content_attr = meta.get("content")
                if content_attr:
                    try:
                        timestamp_str = str(content_attr)
                        # Try to parse the timestamp
                        parsed_time = self._parse_timestamp(timestamp_str)
                        if parsed_time:
                            timestamps[timestamp_type] = {
                                "timestamp": parsed_time,
                                "confidence_score": 0.8,
                                "source": "meta_tag",
                            }
                    except Exception:
                        continue

        return timestamps

    def _extract_timestamps_from_content(
        self, soup: BeautifulSoup, url: str
    ) -> Dict[str, Any]:
        """Extract timestamps from content."""
        timestamps = {}

        # Time elements
        for time_elem in soup.find_all("time"):
            if isinstance(time_elem, Tag):
                datetime_attr = time_elem.get("datetime")
                if datetime_attr:
                    parsed_time = self._parse_timestamp(str(datetime_attr))
                    if parsed_time:
                        # Determine type based on context
                        parent_text = ""
                        if time_elem.parent and isinstance(time_elem.parent, Tag):
                            parent_text = time_elem.parent.get_text().lower()

                        if any(
                            word in parent_text
                            for word in ["published", "created", "posted"]
                        ):
                            timestamp_type = "published"
                        elif any(
                            word in parent_text
                            for word in ["updated", "modified", "revised"]
                        ):
                            timestamp_type = "modified"
                        else:
                            timestamp_type = "content_date"

                        timestamps[timestamp_type] = {
                            "timestamp": parsed_time,
                            "confidence_score": 0.7,
                            "source": "time_element",
                        }
                        break  # Use first valid timestamp

        return timestamps

    def _extract_timestamps_from_structured_data(
        self, soup: BeautifulSoup
    ) -> Dict[str, Any]:
        """Extract timestamps from structured data."""
        timestamps = {}

        for script in soup.find_all("script", type="application/ld+json"):
            if isinstance(script, Tag):
                try:
                    import json

                    script_content = getattr(script, "string", None)
                    if script_content:
                        data = json.loads(str(script_content))
                        if isinstance(data, dict):
                            # Check for common timestamp fields
                            timestamp_fields = {
                                "datePublished": "published",
                                "dateCreated": "created",
                                "dateModified": "modified",
                                "dateUpdated": "modified",
                            }

                            for field, timestamp_type in timestamp_fields.items():
                                if field in data:
                                    parsed_time = self._parse_timestamp(data[field])
                                    if parsed_time:
                                        timestamps[timestamp_type] = {
                                            "timestamp": parsed_time,
                                            "confidence_score": 0.9,
                                            "source": "structured_data",
                                        }
                except (json.JSONDecodeError, KeyError):
                    continue

        return timestamps

    def _parse_timestamp(self, timestamp_str: str) -> str | None:
        """Parse various timestamp formats into ISO format."""
        if not timestamp_str:
            return None

        try:
            # Common patterns to try
            patterns = [
                "%Y-%m-%dT%H:%M:%S%z",  # ISO with timezone
                "%Y-%m-%dT%H:%M:%S",  # ISO without timezone
                "%Y-%m-%d %H:%M:%S",  # Standard datetime
                "%Y-%m-%d",  # Date only
                "%m/%d/%Y",  # US format
                "%d/%m/%Y",  # European format
            ]

            for pattern in patterns:
                try:
                    dt = datetime.strptime(timestamp_str, pattern)
                    return dt.isoformat()
                except ValueError:
                    continue

        except Exception:
            pass

        return None

    # Helper methods for relationship extraction
    def _extract_navigation_relationships(
        self, soup: BeautifulSoup, url: str
    ) -> List[Dict[str, Any]]:
        """Extract navigation hierarchy relationships."""
        relationships = []

        # Navigation elements
        nav_selectors = ["nav", ".navigation", ".nav", ".menu", '[role="navigation"]']

        for selector in nav_selectors:
            for nav in soup.select(selector)[:3]:  # Limit to first 3 nav elements
                if isinstance(nav, Tag):
                    for link in nav.find_all("a", href=True):
                        if isinstance(link, Tag):
                            href_attr = link.get("href")
                            if href_attr:
                                href = str(href_attr)
                                full_url = urljoin(url, href)

                                if self._is_internal_url(full_url):
                                    relationships.append(
                                        {
                                            "source_id": url,
                                            "target_id": full_url,
                                            "type": "navigates_to",
                                            "confidence_score": 0.7,
                                            "context": "navigation",
                                        }
                                    )

        return relationships[:20]  # Limit total relationships

    def _extract_breadcrumb_relationships(
        self, soup: BeautifulSoup, url: str
    ) -> List[Dict[str, Any]]:
        """Extract breadcrumb hierarchy relationships."""
        relationships = []

        # Breadcrumb selectors
        breadcrumb_selectors = [
            ".breadcrumb",
            ".breadcrumbs",
            '[role="breadcrumb"]',
            ".path",
            ".location",
            "nav ol",
            ".navigation-path",
        ]

        for selector in breadcrumb_selectors:
            breadcrumb = soup.select_one(selector)
            if isinstance(breadcrumb, Tag):
                links = breadcrumb.find_all("a", href=True)
                for i, link in enumerate(links):
                    if isinstance(link, Tag):
                        href_attr = link.get("href")
                        if href_attr:
                            href = str(href_attr)
                            full_url = urljoin(url, href)

                            if self._is_internal_url(full_url):
                                relationships.append(
                                    {
                                        "source_id": url,
                                        "target_id": full_url,
                                        "type": (
                                            "child_of"
                                            if i == len(links) - 1
                                            else "descendant_of"
                                        ),
                                        "confidence_score": 0.9,
                                        "context": "breadcrumb",
                                    }
                                )
                break  # Use first breadcrumb found

        return relationships

    def _extract_toc_relationships(
        self, soup: BeautifulSoup, url: str
    ) -> List[Dict[str, Any]]:
        """Extract table of contents relationships."""
        relationships = []

        # ToC selectors
        toc_selectors = [
            ".toc",
            ".table-of-contents",
            "#toc",
            ".contents",
            ".page-contents",
        ]

        for selector in toc_selectors:
            toc = soup.select_one(selector)
            if isinstance(toc, Tag):
                for link in toc.find_all("a", href=True)[:10]:  # Limit ToC links
                    if isinstance(link, Tag):
                        href_attr = link.get("href")
                        if href_attr:
                            href = str(href_attr)
                            if href.startswith("#"):
                                # Internal page anchor
                                relationships.append(
                                    {
                                        "source_id": url,
                                        "target_id": f"{url}{href}",
                                        "type": "contains_section",
                                        "confidence_score": 0.8,
                                        "context": "table_of_contents",
                                    }
                                )
                            else:
                                full_url = urljoin(url, href)
                                if self._is_internal_url(full_url):
                                    relationships.append(
                                        {
                                            "source_id": url,
                                            "target_id": full_url,
                                            "type": "references",
                                            "confidence_score": 0.8,
                                            "context": "table_of_contents",
                                        }
                                    )
                break

        return relationships

    # Helper methods for cross-reference extraction
    def _extract_internal_links(
        self, soup: BeautifulSoup, url: str
    ) -> List[Dict[str, Any]]:
        """Extract internal links as cross-references."""
        cross_references = []

        # Find all links in content areas
        content_selectors = ["main", "article", ".content", ".post", ".page-content"]
        content_area = soup.select_one(", ".join(content_selectors)) or soup

        for link in content_area.find_all("a", href=True)[:30]:  # Limit to avoid noise
            if isinstance(link, Tag):
                href_attr = link.get("href")
                if href_attr:
                    href = str(href_attr)
                    full_url = urljoin(url, href)

                    if self._is_internal_url(full_url) and full_url != url:
                        link_text = link.get_text(strip=True)
                        cross_references.append(
                            {
                                "target": full_url,
                                "type": "internal_link",
                                "reference_text": (
                                    link_text[:100] if link_text else href
                                ),
                                "confidence_score": 0.8,
                            }
                        )

        return cross_references

    def _extract_external_links(
        self, soup: BeautifulSoup, url: str
    ) -> List[Dict[str, Any]]:
        """Extract external links as cross-references."""
        cross_references = []

        content_selectors = ["main", "article", ".content", ".post", ".page-content"]
        content_area = soup.select_one(", ".join(content_selectors)) or soup

        for link in content_area.find_all("a", href=True)[:20]:  # Limit external links
            if isinstance(link, Tag):
                href_attr = link.get("href")
                if href_attr:
                    href = str(href_attr)
                    if href.startswith(
                        ("http://", "https://")
                    ) and not self._is_internal_url(href):
                        link_text = link.get_text(strip=True)
                        cross_references.append(
                            {
                                "target": href,
                                "type": "external_link",
                                "reference_text": (
                                    link_text[:100] if link_text else href
                                ),
                                "confidence_score": 0.7,
                            }
                        )

        return cross_references

    def _extract_file_links(
        self, soup: BeautifulSoup, url: str
    ) -> List[Dict[str, Any]]:
        """Extract links to files (PDFs, docs, etc.)."""
        cross_references = []

        file_extensions = [
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".ppt",
            ".pptx",
            ".zip",
            ".tar.gz",
        ]

        for link in soup.find_all("a", href=True):
            if isinstance(link, Tag):
                href_attr = link.get("href")
                if href_attr:
                    href = str(href_attr)
                    if any(href.lower().endswith(ext) for ext in file_extensions):
                        full_url = urljoin(url, href)
                        link_text = link.get_text(strip=True)

                        cross_references.append(
                            {
                                "target": full_url,
                                "type": "file_link",
                                "reference_text": (
                                    link_text[:100] if link_text else href
                                ),
                                "confidence_score": 0.8,
                            }
                        )

        return cross_references[:10]  # Limit file links

    def _extract_anchor_links(
        self, soup: BeautifulSoup, url: str
    ) -> List[Dict[str, Any]]:
        """Extract internal anchor/fragment links."""
        cross_references = []

        for link in soup.find_all("a", href=True):
            if isinstance(link, Tag):
                href_attr = link.get("href")
                if href_attr:
                    href = str(href_attr)
                    if href.startswith("#") and len(href) > 1:
                        link_text = link.get_text(strip=True)
                        cross_references.append(
                            {
                                "target": f"{url}{href}",
                                "type": "anchor_link",
                                "reference_text": (
                                    link_text[:100] if link_text else href
                                ),
                                "confidence_score": 0.6,
                            }
                        )

        return cross_references[:15]  # Limit anchor links

    # Helper methods for HTML and content analysis
    def _extract_html_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract HTML meta information."""
        metadata = {}

        # Basic HTML metadata
        title = soup.find("title")
        if isinstance(title, Tag):
            metadata["html_title"] = title.get_text(strip=True)

        # Meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if isinstance(meta_desc, Tag):
            content_attr = meta_desc.get("content")
            if content_attr:
                metadata["meta_description"] = str(content_attr)

        # Meta keywords
        meta_keywords = soup.find("meta", attrs={"name": "keywords"})
        if isinstance(meta_keywords, Tag):
            content_attr = meta_keywords.get("content")
            if content_attr:
                metadata["meta_keywords"] = str(content_attr)

        # Language
        html_tag = soup.find("html")
        if isinstance(html_tag, Tag):
            lang_attr = html_tag.get("lang")
            if lang_attr:
                metadata["language"] = str(lang_attr)

        # Open Graph metadata
        og_metadata = {}
        for og_tag in soup.find_all("meta"):
            if isinstance(og_tag, Tag):
                property_attr = og_tag.get("property")
                if property_attr and str(property_attr).startswith("og:"):
                    prop = str(property_attr).replace("og:", "")
                    content_attr = og_tag.get("content")
                    if prop and content_attr:
                        og_metadata[prop] = str(content_attr)

        if og_metadata:
            metadata["open_graph"] = og_metadata

        return metadata

    def _extract_content_analysis(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract content analysis metadata."""
        metadata = {}

        # Remove script and style elements
        for element in soup(["script", "style", "nav", "header", "footer"]):
            if isinstance(element, Tag):
                element.decompose()

        # Get main content
        content_area = soup.find("main") or soup.find("article") or soup
        if isinstance(content_area, Tag):
            text_content = content_area.get_text()

            # Basic content stats
            metadata.update(
                {
                    "content_length": len(text_content),
                    "word_count": len(text_content.split()),
                    "paragraph_count": len(content_area.find_all("p")),
                    "heading_count": len(
                        content_area.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
                    ),
                    "link_count": len(content_area.find_all("a", href=True)),
                    "image_count": len(content_area.find_all("img")),
                }
            )

            # Content structure
            headings = []
            for heading in content_area.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])[
                :10
            ]:
                if isinstance(heading, Tag) and heading.name:
                    headings.append(
                        {
                            "level": int(heading.name[1]),
                            "text": heading.get_text(strip=True)[:100],
                        }
                    )

            if headings:
                metadata["headings"] = headings

        return metadata

    def _is_internal_url(self, url: str) -> bool:
        """Check if URL is internal to the base domain."""
        try:
            parsed = urlparse(url)
            return (
                not parsed.netloc or parsed.netloc == self.domain or url.startswith("/")
            )
        except Exception:
            return False
