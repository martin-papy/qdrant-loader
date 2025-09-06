#!/usr/bin/env python3
"""
Website Builder - Re-export Module.

This module provides comprehensive website building functionality through a clean,
modular architecture. The original WebsiteBuilder class and its methods have been
extracted to the 'builder' sub-package for better maintainability and testability.

Architecture:
- builder.core: Main WebsiteBuilder class with lifecycle management
- builder.templates: Template loading and placeholder processing
- builder.markdown: Markdown-to-HTML conversion with extensions
- builder.assets: Asset management and static file handling
"""

import argparse

# Re-export the main WebsiteBuilder class for backward compatibility
# Handle both relative import (when used as module) and absolute import (when run as script)
try:
    from .builder.core import WebsiteBuilder
except ImportError:
    # Fallback for when script is run directly
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent))
    from builder.core import WebsiteBuilder


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Build QDrant Loader documentation website"
    )
    parser.add_argument("--output", "-o", default="site", help="Output directory")
    parser.add_argument(
        "--templates", "-t", default="website/templates", help="Templates directory"
    )
    parser.add_argument("--coverage-artifacts", help="Coverage artifacts directory")
    parser.add_argument("--test-results", help="Test results directory")
    parser.add_argument("--base-url", default="", help="Base URL for the website")

    args = parser.parse_args()

    builder = WebsiteBuilder(args.templates, args.output)
    builder.base_url = args.base_url
    # Mark that base_url came from CLI (even if empty string). Avoid auto-overrides.
    try:
        builder.base_url_user_set = True
    except Exception:
        pass

    try:
        builder.build_site(args.coverage_artifacts, args.test_results)
    except Exception as e:
        print(f"❌ Build failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
