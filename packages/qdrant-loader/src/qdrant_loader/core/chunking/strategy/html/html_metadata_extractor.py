"""HTML-specific metadata extractor for enhanced HTML document analysis."""

import re
from typing import Any

from bs4 import BeautifulSoup

from qdrant_loader.core.chunking.strategy.base.metadata_extractor import (
    BaseMetadataExtractor,
)
from qdrant_loader.core.document import Document

from .html_document_parser import HTMLDocumentParser


class HTMLMetadataExtractor(BaseMetadataExtractor):
    """Metadata extractor for HTML documents with semantic and accessibility analysis."""

    def __init__(self):
        """Initialize the HTML metadata extractor."""
        self.document_parser = HTMLDocumentParser()

    def extract_hierarchical_metadata(
        self, content: str, chunk_metadata: dict[str, Any], document: Document
    ) -> dict[str, Any]:
        """Extract HTML-specific hierarchical metadata."""
        try:
            soup = BeautifulSoup(content, "html.parser")

            metadata = chunk_metadata.copy()

            # Add HTML-specific metadata
            metadata.update(
                {
                    "dom_path": self._build_dom_path_breadcrumb(soup),
                    "semantic_tags": self._extract_semantic_tags(soup),
                    "accessibility_score": self._calculate_accessibility_score(soup),
                    "has_structured_data": self._has_structured_data(soup),
                    "interactive_elements": self._analyze_interactive_elements(soup),
                    "media_elements": self._analyze_media_elements(soup),
                    "content_type": "html",
                    "html_features": self._analyze_html_features(soup),
                    "seo_indicators": self._analyze_seo_indicators(soup),
                    "markup_quality": self._assess_markup_quality(soup),
                }
            )

            return metadata

        except Exception as e:
            # Fallback metadata for malformed HTML
            metadata = chunk_metadata.copy()
            metadata.update(
                {
                    "content_type": "html_malformed",
                    "parse_error": str(e),
                    "dom_path": "unknown",
                    "semantic_tags": [],
                    "accessibility_score": 0.0,
                    "has_structured_data": False,
                }
            )
            return metadata

    def extract_entities(self, text: str) -> list[str]:
        """Extract HTML-specific entities including semantic elements and IDs."""
        try:
            soup = BeautifulSoup(text, "html.parser")
            entities = []

            # Extract IDs as entities
            for element in soup.find_all(id=True):
                entities.append(f"#{element.get('id')}")

            # Extract class names as entities
            for element in soup.find_all(class_=True):
                classes = element.get("class", [])
                entities.extend([f".{cls}" for cls in classes])

            # Extract semantic element types
            semantic_elements = soup.find_all(
                list(self.document_parser.section_elements)
            )
            entities.extend([elem.name for elem in semantic_elements])

            # Extract link destinations
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if href.startswith("#"):
                    entities.append(href)  # Internal link
                elif href.startswith("http"):
                    entities.append(href)  # External link

            # Remove duplicates and limit
            return list(set(entities))[:50]

        except Exception:
            return []

    def _build_dom_path_breadcrumb(self, soup: BeautifulSoup) -> str:
        """Build a DOM path breadcrumb for context."""
        try:
            # Find the deepest meaningful element
            meaningful_elements = []

            for element in soup.find_all():
                if (
                    element.name in self.document_parser.section_elements
                    or element.name in self.document_parser.heading_elements
                    or element.get("id")
                    or element.get("role")
                ):
                    meaningful_elements.append(element)

            if not meaningful_elements:
                return "body"

            # Build path from the first meaningful element
            element = meaningful_elements[0]
            path_parts = []

            while element and len(path_parts) < 5:  # Limit depth
                part = element.name
                if element.get("id"):
                    part += f"#{element.get('id')}"
                elif element.get("class"):
                    classes = element.get("class", [])[:2]  # Limit classes
                    part += f".{'.'.join(classes)}"

                path_parts.append(part)
                element = element.parent

                # Stop at body or html
                if element and element.name in ["body", "html"]:
                    break

            return " > ".join(reversed(path_parts)) if path_parts else "body"

        except Exception:
            return "unknown"

    def _extract_semantic_tags(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        """Extract semantic HTML tags and their properties."""
        semantic_tags = []

        try:
            for element in soup.find_all():
                if element.name in self.document_parser.section_elements:
                    tag_info = {
                        "tag": element.name,
                        "role": element.get("role"),
                        "id": element.get("id"),
                        "classes": element.get("class", [])[:3],  # Limit classes
                        "has_content": bool(element.get_text(strip=True)),
                        "child_count": len(element.find_all()),
                    }
                    semantic_tags.append(tag_info)

            return semantic_tags[:10]  # Limit results

        except Exception:
            return []

    def _calculate_accessibility_score(self, soup: BeautifulSoup) -> float:
        """Calculate an accessibility score for the HTML content."""
        try:
            score = 0.0
            max_score = 10.0

            # Check for lang attribute
            if soup.find("html", lang=True):
                score += 1.0

            # Check image alt texts
            images = soup.find_all("img")
            if images:
                images_with_alt = len(
                    [img for img in images if img.get("alt") is not None]
                )
                score += (images_with_alt / len(images)) * 2.0
            else:
                score += 2.0  # No images, full score

            # Check heading hierarchy
            headings = soup.find_all(list(self.document_parser.heading_elements))
            if headings:
                # Simple check: first heading should be h1
                if headings[0].name == "h1":
                    score += 1.0
                # Check for proper nesting (simplified)
                proper_nesting = True
                prev_level = 0
                for heading in headings:
                    level = int(heading.name[1])
                    if prev_level > 0 and level > prev_level + 1:
                        proper_nesting = False
                        break
                    prev_level = level
                if proper_nesting:
                    score += 1.0

            # Check for skip links
            skip_indicators = ["skip", "jump", "goto"]
            for link in soup.find_all("a", href=True):
                link_text = link.get_text(strip=True).lower()
                if any(indicator in link_text for indicator in skip_indicators):
                    score += 1.0
                    break

            # Check form labels
            forms = soup.find_all("form")
            if forms:
                inputs = soup.find_all(["input", "textarea", "select"])
                labels = soup.find_all("label")
                if inputs:
                    label_ratio = len(labels) / len(inputs)
                    score += min(label_ratio, 1.0) * 2.0
            else:
                score += 2.0  # No forms, full score

            # Check for ARIA attributes
            aria_elements = soup.find_all(attrs={"role": True})
            aria_elements.extend(soup.find_all(attrs=re.compile(r"^aria-")))
            if aria_elements:
                score += 1.0

            # Check for semantic HTML5 elements
            semantic_count = len(
                soup.find_all(list(self.document_parser.section_elements))
            )
            if semantic_count > 0:
                score += min(
                    semantic_count / 3.0, 1.0
                )  # Up to 1 point for semantic elements

            return min(score / max_score, 1.0)  # Normalize to 0-1

        except Exception:
            return 0.0

    def _has_structured_data(self, soup: BeautifulSoup) -> bool:
        """Check if the HTML contains structured data."""
        try:
            # Check for JSON-LD
            json_ld = soup.find("script", type="application/ld+json")
            if json_ld:
                return True

            # Check for microdata
            microdata = soup.find_all(attrs={"itemscope": True})
            if microdata:
                return True

            # Check for RDFa
            rdfa = soup.find_all(attrs={"property": True})
            if rdfa:
                return True

            # Check for Open Graph
            og_tags = soup.find_all("meta", property=re.compile(r"^og:"))
            if og_tags:
                return True

            # Check for Twitter Cards
            twitter_tags = soup.find_all(
                "meta", attrs={"name": re.compile(r"^twitter:")}
            )
            if twitter_tags:
                return True

            return False

        except Exception:
            return False

    def _analyze_interactive_elements(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Analyze interactive elements in the HTML."""
        try:
            interactive = {
                "forms": len(soup.find_all("form")),
                "buttons": len(
                    soup.find_all(
                        ["button", "input[type='button']", "input[type='submit']"]
                    )
                ),
                "links": len(soup.find_all("a", href=True)),
                "inputs": len(soup.find_all(["input", "textarea", "select"])),
                "clickable_elements": 0,
                "has_javascript_events": False,
            }

            # Count elements with click events
            clickable = soup.find_all(attrs=re.compile(r"^on(click|touch|mouse)"))
            interactive["clickable_elements"] = len(clickable)

            # Check for JavaScript event handlers
            js_events = soup.find_all(attrs=re.compile(r"^on[a-z]+"))
            interactive["has_javascript_events"] = len(js_events) > 0

            return interactive

        except Exception:
            return {}

    def _analyze_media_elements(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Analyze media elements in the HTML."""
        try:
            media = {
                "images": len(soup.find_all("img")),
                "videos": len(soup.find_all("video")),
                "audio": len(soup.find_all("audio")),
                "iframes": len(soup.find_all("iframe")),
                "canvas": len(soup.find_all("canvas")),
                "svg": len(soup.find_all("svg")),
            }

            # Analyze image properties
            images = soup.find_all("img")
            if images:
                media["images_with_alt"] = len(
                    [img for img in images if img.get("alt")]
                )
                media["images_with_title"] = len(
                    [img for img in images if img.get("title")]
                )
                media["responsive_images"] = len(
                    [img for img in images if img.get("srcset")]
                )

            return media

        except Exception:
            return {}

    def _analyze_html_features(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Analyze HTML5 and modern web features."""
        try:
            features = {
                "html5_semantic_tags": 0,
                "custom_elements": 0,
                "data_attributes": 0,
                "css_classes": 0,
                "inline_styles": 0,
            }

            # Count HTML5 semantic tags
            features["html5_semantic_tags"] = len(
                soup.find_all(list(self.document_parser.section_elements))
            )

            # Count custom elements (tags with hyphens)
            custom_elements = soup.find_all(lambda tag: tag.name and "-" in tag.name)
            features["custom_elements"] = len(custom_elements)

            # Count data attributes
            data_attrs = soup.find_all(attrs=re.compile(r"^data-"))
            features["data_attributes"] = len(data_attrs)

            # Count CSS classes
            elements_with_class = soup.find_all(class_=True)
            features["css_classes"] = sum(
                len(elem.get("class", [])) for elem in elements_with_class
            )

            # Count inline styles
            features["inline_styles"] = len(soup.find_all(style=True))

            return features

        except Exception:
            return {}

    def _analyze_seo_indicators(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Analyze SEO-related indicators."""
        try:
            seo = {
                "has_title": False,
                "has_meta_description": False,
                "has_h1": False,
                "heading_count": 0,
                "internal_links": 0,
                "external_links": 0,
                "has_canonical": False,
                "has_robots_meta": False,
            }

            # Check for title
            title = soup.find("title")
            seo["has_title"] = bool(title and title.get_text(strip=True))

            # Check for meta description
            meta_desc = soup.find("meta", attrs={"name": "description"})
            seo["has_meta_description"] = bool(meta_desc and meta_desc.get("content"))

            # Check for H1
            h1 = soup.find("h1")
            seo["has_h1"] = bool(h1 and h1.get_text(strip=True))

            # Count headings
            headings = soup.find_all(list(self.document_parser.heading_elements))
            seo["heading_count"] = len(headings)

            # Analyze links
            links = soup.find_all("a", href=True)
            for link in links:
                href = link["href"]
                if href.startswith(("http://", "https://")) and "://" in href:
                    seo["external_links"] += 1
                else:
                    seo["internal_links"] += 1

            # Check for canonical link
            canonical = soup.find("link", rel="canonical")
            seo["has_canonical"] = bool(canonical)

            # Check for robots meta
            robots = soup.find("meta", attrs={"name": "robots"})
            seo["has_robots_meta"] = bool(robots)

            return seo

        except Exception:
            return {}

    def _assess_markup_quality(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Assess the quality of HTML markup."""
        try:
            quality = {
                "semantic_ratio": 0.0,
                "accessibility_features": 0,
                "deprecated_tags": 0,
                "inline_styles": 0,
                "proper_nesting": True,
                "valid_attributes": True,
            }

            # Calculate semantic ratio
            all_elements = soup.find_all()
            semantic_elements = soup.find_all(
                list(self.document_parser.section_elements)
            )
            if all_elements:
                quality["semantic_ratio"] = len(semantic_elements) / len(all_elements)

            # Count accessibility features
            accessibility_features = 0
            if soup.find_all(alt=True):
                accessibility_features += 1
            if soup.find_all(attrs={"role": True}):
                accessibility_features += 1
            if soup.find_all(attrs=re.compile(r"^aria-")):
                accessibility_features += 1
            if soup.find_all("label"):
                accessibility_features += 1
            quality["accessibility_features"] = accessibility_features

            # Count deprecated tags (simplified list)
            deprecated_tags = ["font", "center", "big", "small", "strike", "tt"]
            quality["deprecated_tags"] = sum(
                len(soup.find_all(tag)) for tag in deprecated_tags
            )

            # Count inline styles
            quality["inline_styles"] = len(soup.find_all(style=True))

            return quality

        except Exception:
            return {}
