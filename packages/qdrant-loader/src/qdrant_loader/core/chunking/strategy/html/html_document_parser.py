"""HTML-specific document parser for DOM structure analysis."""

import re
from enum import Enum
from typing import Any

from bs4 import BeautifulSoup, Tag

from qdrant_loader.core.chunking.strategy.base.document_parser import BaseDocumentParser


class SectionType(Enum):
    """Types of sections in an HTML document."""

    HEADER = "header"
    ARTICLE = "article"
    SECTION = "section"
    NAV = "nav"
    ASIDE = "aside"
    MAIN = "main"
    PARAGRAPH = "paragraph"
    LIST = "list"
    TABLE = "table"
    CODE_BLOCK = "code_block"
    BLOCKQUOTE = "blockquote"
    DIV = "div"
    FOOTER = "footer"


class HTMLDocumentParser(BaseDocumentParser):
    """Parser for HTML documents with semantic analysis."""

    def __init__(self):
        """Initialize the HTML document parser."""
        # Define semantic HTML elements that should be treated as section boundaries
        self.section_elements = {
            "article",
            "section",
            "main",
            "header",
            "footer",
            "nav",
            "aside",
        }

        # Define heading elements for hierarchy
        self.heading_elements = {"h1", "h2", "h3", "h4", "h5", "h6"}

        # Define block-level elements that can form chunks
        self.block_elements = {
            "div",
            "p",
            "blockquote",
            "pre",
            "ul",
            "ol",
            "li",
            "table",
            "figure",
            "form",
        }

    def parse_document_structure(self, content: str) -> dict[str, Any]:
        """Parse HTML DOM structure and extract semantic information."""
        try:
            soup = BeautifulSoup(content, "html.parser")

            # Remove script and style elements for cleaner analysis
            for script in soup(["script", "style"]):
                script.decompose()

            # Extract document outline
            headings = self._extract_heading_hierarchy(soup)
            semantic_elements = self._identify_semantic_elements(soup)
            links = self._extract_links(soup)
            accessibility = self._analyze_accessibility(soup)

            return {
                "heading_hierarchy": headings,
                "semantic_elements": semantic_elements,
                "internal_links": len(
                    [link for link in links if link.get("internal", False)]
                ),
                "external_links": len(
                    [link for link in links if not link.get("internal", False)]
                ),
                "has_navigation": bool(soup.find("nav")),
                "has_main_content": bool(soup.find("main")),
                "has_header": bool(soup.find("header")),
                "has_footer": bool(soup.find("footer")),
                "has_aside": bool(soup.find("aside")),
                "structure_type": "html",
                "accessibility_features": accessibility,
                "form_count": len(soup.find_all("form")),
                "table_count": len(soup.find_all("table")),
                "image_count": len(soup.find_all("img")),
                "list_count": len(soup.find_all(["ul", "ol"])),
                "content_sections": len(soup.find_all(list(self.section_elements))),
            }
        except Exception as e:
            # Fallback structure for malformed HTML
            return {
                "heading_hierarchy": [],
                "semantic_elements": [],
                "internal_links": 0,
                "external_links": 0,
                "has_navigation": False,
                "has_main_content": False,
                "has_header": False,
                "has_footer": False,
                "has_aside": False,
                "structure_type": "html_malformed",
                "accessibility_features": {},
                "form_count": 0,
                "table_count": 0,
                "image_count": 0,
                "list_count": 0,
                "content_sections": 0,
                "parse_error": str(e),
            }

    def extract_section_metadata(self, section: Any) -> dict[str, Any]:
        """Extract metadata from an HTML section."""
        if isinstance(section, dict):
            # Already processed section metadata
            return section

        if isinstance(section, Tag):
            return self._extract_tag_metadata(section)

        # Fallback for string content
        return {
            "tag_name": "div",
            "section_type": SectionType.DIV.value,
            "level": 0,
            "attributes": {},
            "has_links": bool(re.search(r"<a\s+[^>]*href", str(section))),
            "has_images": bool(re.search(r"<img\s+[^>]*src", str(section))),
        }

    def _extract_heading_hierarchy(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        """Extract document heading hierarchy."""
        headings = []

        for heading in soup.find_all(list(self.heading_elements)):
            level = int(heading.name[1])  # Extract number from h1, h2, etc.
            text = heading.get_text(strip=True)

            headings.append(
                {
                    "level": level,
                    "text": text,
                    "tag": heading.name,
                    "id": heading.get("id"),
                    "classes": heading.get("class", []),
                }
            )

        return headings

    def _identify_semantic_elements(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        """Identify semantic HTML elements and their roles."""
        semantic_elements = []

        for element in soup.find_all(list(self.section_elements)):
            semantic_elements.append(
                {
                    "tag": element.name,
                    "role": element.get("role"),
                    "id": element.get("id"),
                    "classes": element.get("class", []),
                    "text_length": len(element.get_text(strip=True)),
                    "has_children": bool(element.find_all()),
                }
            )

        return semantic_elements

    def _extract_links(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        """Extract and categorize links."""
        links = []

        for link in soup.find_all("a", href=True):
            href = link["href"]
            text = link.get_text(strip=True)

            # Determine if link is internal or external
            is_internal = (
                href.startswith("#")
                or href.startswith("/")
                or href.startswith("./")
                or href.startswith("../")
                or not href.startswith(("http://", "https://", "mailto:", "tel:"))
            )

            links.append(
                {
                    "href": href,
                    "text": text,
                    "internal": is_internal,
                    "title": link.get("title"),
                    "target": link.get("target"),
                }
            )

        return links

    def _analyze_accessibility(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Analyze accessibility features of the HTML document."""
        accessibility = {
            "has_lang_attribute": bool(soup.find("html", lang=True)),
            "has_title": bool(soup.find("title")),
            "images_with_alt": 0,
            "images_without_alt": 0,
            "headings_properly_nested": True,
            "has_skip_links": False,
            "form_labels": 0,
            "form_inputs": 0,
        }

        # Analyze images
        for img in soup.find_all("img"):
            if img.get("alt") is not None:
                accessibility["images_with_alt"] += 1
            else:
                accessibility["images_without_alt"] += 1

        # Check for skip links
        skip_link_indicators = ["skip", "jump", "goto"]
        for link in soup.find_all("a", href=True):
            link_text = link.get_text(strip=True).lower()
            if any(indicator in link_text for indicator in skip_link_indicators):
                accessibility["has_skip_links"] = True
                break

        # Analyze forms
        accessibility["form_inputs"] = len(
            soup.find_all(["input", "textarea", "select"])
        )
        accessibility["form_labels"] = len(soup.find_all("label"))

        # Check heading nesting (simplified)
        headings = soup.find_all(list(self.heading_elements))
        if len(headings) > 1:
            prev_level = 0
            for heading in headings:
                level = int(heading.name[1])
                if prev_level > 0 and level > prev_level + 1:
                    accessibility["headings_properly_nested"] = False
                    break
                prev_level = level

        return accessibility

    def _extract_tag_metadata(self, tag: Tag) -> dict[str, Any]:
        """Extract metadata from a BeautifulSoup tag."""
        tag_name = tag.name.lower()
        section_type = self._identify_section_type(tag)

        # Get attributes (limited for performance)
        attributes = {}
        if tag.attrs:
            # Only keep essential attributes
            for attr in ["id", "class", "role", "data-*"]:
                if attr in tag.attrs:
                    attributes[attr] = tag.attrs[attr]
                elif attr == "data-*":
                    # Collect data attributes
                    data_attrs = {
                        k: v for k, v in tag.attrs.items() if k.startswith("data-")
                    }
                    if data_attrs:
                        attributes["data_attributes"] = data_attrs

        text_content = tag.get_text(strip=True)

        return {
            "tag_name": tag_name,
            "section_type": section_type.value,
            "level": self._get_heading_level(tag),
            "attributes": attributes,
            "text_content": text_content,
            "word_count": len(text_content.split()),
            "char_count": len(text_content),
            "has_code": section_type == SectionType.CODE_BLOCK,
            "has_links": bool(tag.find_all("a")),
            "has_images": bool(tag.find_all("img")),
            "is_semantic": tag_name in self.section_elements,
            "is_heading": tag_name in self.heading_elements,
            "child_count": len(tag.find_all()),
        }

    def _identify_section_type(self, tag: Tag) -> SectionType:
        """Identify the type of section based on the HTML tag."""
        tag_name = tag.name.lower()

        if tag_name in self.heading_elements:
            return SectionType.HEADER
        elif tag_name == "article":
            return SectionType.ARTICLE
        elif tag_name == "section":
            return SectionType.SECTION
        elif tag_name == "nav":
            return SectionType.NAV
        elif tag_name == "aside":
            return SectionType.ASIDE
        elif tag_name == "main":
            return SectionType.MAIN
        elif tag_name == "footer":
            return SectionType.FOOTER
        elif tag_name in ["ul", "ol", "li"]:
            return SectionType.LIST
        elif tag_name == "table":
            return SectionType.TABLE
        elif tag_name in ["pre", "code"]:
            return SectionType.CODE_BLOCK
        elif tag_name == "blockquote":
            return SectionType.BLOCKQUOTE
        elif tag_name == "p":
            return SectionType.PARAGRAPH
        else:
            return SectionType.DIV

    def _get_heading_level(self, tag: Tag) -> int:
        """Get the heading level from an HTML heading tag."""
        if tag.name.lower() in self.heading_elements:
            return int(tag.name[1])  # Extract number from h1, h2, etc.
        return 0

    def extract_section_title(self, content: str) -> str:
        """Extract a title from HTML content."""
        try:
            soup = BeautifulSoup(content, "html.parser")

            # Try to find title in various elements
            for tag in ["h1", "h2", "h3", "h4", "h5", "h6", "title"]:
                element = soup.find(tag)
                if element:
                    title = element.get_text(strip=True)
                    if title:
                        return title[:100]  # Limit title length

            # Try to find text in semantic elements
            for tag in ["article", "section", "main"]:
                element = soup.find(tag)
                if element:
                    text = element.get_text(strip=True)
                    if text:
                        return self._extract_title_from_content(text)

            # Fallback to first text content
            text = soup.get_text(strip=True)
            if text:
                return self._extract_title_from_content(text)

            return "Untitled Section"

        except Exception:
            return "Untitled Section"

    def _extract_title_from_content(self, content: str) -> str:
        """Extract a title from content text."""
        if not content:
            return "Untitled Section"

        # Take first line or first 50 characters, whichever is shorter
        lines = content.strip().split("\n")
        first_line = lines[0].strip() if lines else ""

        if first_line:
            # Limit title length for performance
            return first_line[:100] if len(first_line) > 100 else first_line

        return "Untitled Section"
