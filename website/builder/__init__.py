"""
Website Build Package - Modular Website Build Architecture.

This package provides comprehensive website building capabilities through modular components:
- core: Core WebsiteBuilder class with lifecycle management
- templates: Template loading and placeholder processing
- markdown: Markdown-to-HTML conversion with extensions
- assets: Asset management and static file handling
- navigation: Documentation navigation and TOC generation
- pages: Page building and content orchestration
- seo: SEO metadata, sitemaps, and optimization
- utils: Shared utilities and helper functions
"""

# Re-export the main WebsiteBuilder class for backward compatibility
from .core import WebsiteBuilder

__all__ = [
    "WebsiteBuilder",
]
