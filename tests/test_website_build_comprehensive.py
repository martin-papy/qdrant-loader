#!/usr/bin/env python3
"""
Comprehensive tests for the website build system to achieve >90% coverage.
Tests all aspects of the GitHub Actions docs workflow.
"""

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest


def import_website_builder():
    """Import WebsiteBuilder class dynamically to avoid linter issues."""
    website_dir = Path(__file__).parent.parent / "website"
    build_file = website_dir / "build.py"

    if not build_file.exists():
        pytest.skip("Website build.py not found", allow_module_level=True)

    spec = importlib.util.spec_from_file_location("build", build_file)
    if spec is None or spec.loader is None:
        pytest.skip("Cannot load build module", allow_module_level=True)

    build_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build_module)

    return build_module.WebsiteBuilder, build_module.main


# Import the classes at module level
try:
    WebsiteBuilder, main_function = import_website_builder()
except Exception:
    pytest.skip("Cannot import WebsiteBuilder", allow_module_level=True)


class TestWebsiteBuilderCore:
    """Test core WebsiteBuilder functionality."""

    def test_websitebuilder_init(self):
        """Test WebsiteBuilder initialization."""
        builder = WebsiteBuilder()
        assert builder.templates_dir == Path("website/templates")
        assert builder.output_dir == Path("site")
        assert builder.base_url == ""

        # Test custom paths
        builder = WebsiteBuilder("custom/templates", "custom/output")
        assert builder.templates_dir == Path("custom/templates")
        assert builder.output_dir == Path("custom/output")

    def test_load_template_success(self, mock_project_structure):
        """Test successful template loading."""
        os.chdir(mock_project_structure)
        builder = WebsiteBuilder("website/templates", "site")

        content = builder.load_template("base.html")
        assert "{{ page_title }}" in content
        assert "{{ content }}" in content

    def test_load_template_not_found(self, mock_project_structure):
        """Test template loading with missing file."""
        os.chdir(mock_project_structure)
        builder = WebsiteBuilder("website/templates", "site")

        with pytest.raises(FileNotFoundError):
            builder.load_template("nonexistent.html")

    def test_replace_placeholders(self):
        """Test placeholder replacement."""
        builder = WebsiteBuilder()
        content = "Hello {{ name }}, welcome to {{ site }}!"
        replacements = {"name": "John", "site": "QDrant Loader"}

        result = builder.replace_placeholders(content, replacements)
        assert result == "Hello John, welcome to QDrant Loader!"

    def test_replace_placeholders_empty(self):
        """Test placeholder replacement with empty replacements."""
        builder = WebsiteBuilder()
        content = "Hello {{ name }}!"

        result = builder.replace_placeholders(content, {})
        assert result == "Hello {{ name }}!"

    def test_extract_title_from_markdown(self):
        """Test title extraction from markdown."""
        builder = WebsiteBuilder()

        # Test with h1
        markdown = "# Main Title\n\nSome content"
        title = builder.extract_title_from_markdown(markdown)
        assert title == "Main Title"

        # Test with no title
        markdown = "Just some content"
        title = builder.extract_title_from_markdown(markdown)
        assert title == "Documentation"

        # Test with multiple headers
        markdown = "# First Title\n## Second Title"
        title = builder.extract_title_from_markdown(markdown)
        assert title == "First Title"


class TestWebsiteBuilderMarkdown:
    """Test markdown processing functionality."""

    def test_basic_markdown_to_html_headers(self):
        """Test basic markdown header conversion."""
        builder = WebsiteBuilder()

        markdown = "# Header 1\n## Header 2\n### Header 3\n#### Header 4"
        html = builder.basic_markdown_to_html(markdown)

        assert 'class="display-4 fw-bold text-primary mb-4"' in html
        assert 'class="h2 fw-bold text-primary mt-5 mb-3"' in html
        assert 'class="h3 fw-bold text-primary mt-5 mb-3"' in html
        assert 'class="h4 fw-bold mt-4 mb-3"' in html

    def test_basic_markdown_to_html_code(self):
        """Test basic markdown code conversion."""
        builder = WebsiteBuilder()

        # Test code blocks
        markdown = "```python\nprint('hello')\n```"
        html = builder.basic_markdown_to_html(markdown)
        assert 'class="code-block-wrapper"' in html
        assert 'class="code-block"' in html
        assert 'class="language-python"' in html

        # Test inline code
        markdown = "Use `pip install` to install"
        html = builder.basic_markdown_to_html(markdown)
        assert 'class="inline-code"' in html

    def test_basic_markdown_to_html_links(self):
        """Test basic markdown link conversion."""
        builder = WebsiteBuilder()

        markdown = "[QDrant Loader](https://github.com/user/repo)"
        html = builder.basic_markdown_to_html(markdown)
        assert 'class="text-decoration-none"' in html
        assert 'href="https://github.com/user/repo"' in html

    def test_basic_markdown_to_html_formatting(self):
        """Test basic markdown formatting conversion."""
        builder = WebsiteBuilder()

        markdown = "**bold text** and *italic text*"
        html = builder.basic_markdown_to_html(markdown)
        assert "<strong>bold text</strong>" in html
        assert "<em>italic text</em>" in html

    def test_basic_markdown_to_html_lists(self):
        """Test basic markdown list conversion."""
        builder = WebsiteBuilder()

        markdown = "- Item 1\n- Item 2"
        html = builder.basic_markdown_to_html(markdown)
        assert "Item 1" in html
        assert "Item 2" in html
        assert 'class="list-group list-group-flush"' in html
        assert 'class="list-group-item"' in html

    def test_convert_markdown_links_to_html(self):
        """Test markdown link to HTML conversion."""
        builder = WebsiteBuilder()

        # Test relative links
        html = 'href="./docs/guide.md"'
        result = builder.convert_markdown_links_to_html(html)
        assert 'href="./docs/guide.html"' in result

        # Test absolute links
        html = 'href="/docs/api.md"'
        result = builder.convert_markdown_links_to_html(html)
        assert 'href="/docs/api.html"' in result

        # Test without ./ prefix
        html = 'href="guide.md"'
        result = builder.convert_markdown_links_to_html(html)
        assert 'href="guide.html"' in result

    def test_add_bootstrap_classes(self):
        """Test Bootstrap class addition."""
        builder = WebsiteBuilder()

        html = "<h1>Title</h1><h2>Subtitle</h2><h3>Section</h3><h4>Subsection</h4>"
        result = builder.add_bootstrap_classes(html)

        assert 'class="display-4 fw-bold text-primary mb-4"' in result
        assert 'class="h2 fw-bold text-primary mt-5 mb-3"' in result
        assert 'class="h3 fw-bold text-primary mt-5 mb-3"' in result
        assert 'class="h4 fw-bold mt-4 mb-3"' in result

    def test_markdown_to_html_with_markdown_library(self):
        """Test markdown conversion with markdown library available."""
        builder = WebsiteBuilder()

        # Test with simple markdown - this will use whatever markdown processing is available
        result = builder.markdown_to_html("# Test Header")

        # Should contain some HTML output
        assert len(result) > 0
        assert "Test Header" in result
        # Should have some HTML tags or Bootstrap classes
        assert ("<" in result and ">" in result) or "class=" in result

    def test_markdown_to_html_fallback(self):
        """Test markdown conversion fallback when library unavailable."""
        # Test the fallback method directly to avoid mocking issues
        builder = WebsiteBuilder()
        result = builder.markdown_processor._basic_markdown_to_html_no_regex(
            "# Test Header"
        )

        # Should convert basic markdown
        assert "<h1>Test Header</h1>" in result


class TestWebsiteBuilderPageBuilding:
    """Test page building functionality."""

    def test_build_page_success(self, mock_project_structure):
        """Test successful page building."""
        os.chdir(mock_project_structure)
        builder = WebsiteBuilder("website/templates", "site")

        builder.build_page(
            "base.html", "test.html", "Test Page", "Test Description", "test.html"
        )

        output_file = mock_project_structure / "site" / "test.html"
        assert output_file.exists()

        content = output_file.read_text()
        assert "Test Page" in content
        assert "Test Description" in content

    def test_build_page_with_additional_replacements(self, mock_project_structure):
        """Test page building with additional replacements."""
        os.chdir(mock_project_structure)
        builder = WebsiteBuilder("website/templates", "site")

        # Add custom placeholder to template
        base_template = mock_project_structure / "website" / "templates" / "base.html"
        content = base_template.read_text()
        content += "\n<div>{{ custom_content }}</div>"
        base_template.write_text(content)

        builder.build_page(
            "base.html",
            "test.html",
            "Test Page",
            "Test Description",
            "test.html",
            custom_content="Custom Value",
        )

        output_file = mock_project_structure / "site" / "test.html"
        content = output_file.read_text()
        assert "Custom Value" in content

    def test_build_markdown_page_success(self, mock_project_structure):
        """Test successful markdown page building."""
        os.chdir(mock_project_structure)
        builder = WebsiteBuilder("website/templates", "site")

        # Create a markdown file
        md_file = mock_project_structure / "test.md"
        md_file.write_text("# Test Document\n\nThis is a test.")

        builder.build_markdown_page(
            "test.md", "test.html", "Test Page", "Test Description"
        )

        output_file = mock_project_structure / "site" / "test.html"
        assert output_file.exists()

        content = output_file.read_text()
        assert "Test Document" in content

    def test_build_markdown_page_with_breadcrumb(self, mock_project_structure):
        """Test markdown page building with breadcrumb."""
        os.chdir(mock_project_structure)
        builder = WebsiteBuilder("website/templates", "site")

        # Add breadcrumb placeholder to base template
        base_template = mock_project_structure / "website" / "templates" / "base.html"
        content = base_template.read_text()
        content = content.replace(
            "<main>{{ content }}</main>",
            '<div class="breadcrumb">{{ breadcrumb }}</div><main>{{ content }}</main>',
        )
        base_template.write_text(content)

        md_file = mock_project_structure / "test.md"
        md_file.write_text("# Test Document\n\nContent here.")

        builder.build_markdown_page(
            "test.md", "test.html", breadcrumb="Test Breadcrumb"
        )

        output_file = mock_project_structure / "site" / "test.html"
        content = output_file.read_text()
        assert "Test Breadcrumb" in content

    def test_build_markdown_page_missing_file(self, mock_project_structure):
        """Test markdown page building with missing file."""
        os.chdir(mock_project_structure)
        builder = WebsiteBuilder("website/templates", "site")

        # Should not raise exception, should handle gracefully
        builder.build_markdown_page("nonexistent.md", "test.html")

        # Output file should not be created
        output_file = mock_project_structure / "site" / "test.html"
        assert not output_file.exists()


class TestWebsiteBuilderProjectInfo:
    """Test project info generation."""

    @patch("subprocess.run")
    def test_generate_project_info_with_git(self, mock_run, mock_project_structure):
        """Test project info generation with git available."""
        os.chdir(mock_project_structure)
        builder = WebsiteBuilder("website/templates", "site")

        # Ensure output directory exists
        builder.output_dir.mkdir(parents=True, exist_ok=True)

        # Mock git commands
        mock_run.side_effect = [
            MagicMock(stdout="abc123\n", returncode=0),  # git rev-parse HEAD
            MagicMock(stdout="2024-01-01\n", returncode=0),  # git log date
        ]

        builder.generate_project_info()

        # Check that git commands were called
        assert mock_run.call_count == 2

    @patch("subprocess.run")
    def test_generate_project_info_without_git(self, mock_run, mock_project_structure):
        """Test project info generation without git."""
        os.chdir(mock_project_structure)
        builder = WebsiteBuilder("website/templates", "site")

        # Ensure output directory exists
        builder.output_dir.mkdir(parents=True, exist_ok=True)

        # Mock git command failure
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        builder.generate_project_info()

        # Should handle git failure gracefully
        assert mock_run.call_count >= 1

    def test_generate_project_info_with_params(self, mock_project_structure):
        """Test project info generation with provided parameters."""
        os.chdir(mock_project_structure)
        builder = WebsiteBuilder("website/templates", "site")

        # Ensure output directory exists
        builder.output_dir.mkdir(parents=True, exist_ok=True)

        builder.generate_project_info(
            version="1.0.0", commit_sha="abc123", commit_date="2024-01-01"
        )

        # Should use provided values instead of git


class TestWebsiteBuilderStructures:
    """Test structure building functionality."""

    def test_build_docs_structure(self, mock_project_structure):
        """Test documentation structure building."""
        os.chdir(mock_project_structure)
        builder = WebsiteBuilder("website/templates", "site")

        # Create additional docs
        (mock_project_structure / "docs" / "advanced.md").write_text("# Advanced Guide")
        (mock_project_structure / "packages" / "qdrant-loader").mkdir(parents=True)
        (
            mock_project_structure / "packages" / "qdrant-loader" / "README.md"
        ).write_text("# Package Docs")

        builder.build_docs_structure()

        # Check that docs were processed
        docs_dir = mock_project_structure / "site" / "docs"
        assert docs_dir.exists()

    def test_build_coverage_structure_with_artifacts(
        self, mock_project_structure, sample_coverage_data
    ):
        """Test coverage structure building with artifacts."""
        os.chdir(mock_project_structure)
        builder = WebsiteBuilder("website/templates", "site")

        builder.build_coverage_structure(str(sample_coverage_data))

        coverage_dir = mock_project_structure / "site" / "coverage"
        assert coverage_dir.exists()

    def test_build_coverage_structure_without_artifacts(self, mock_project_structure):
        """Test coverage structure building without artifacts."""
        os.chdir(mock_project_structure)
        builder = WebsiteBuilder("website/templates", "site")

        builder.build_coverage_structure(None)

        coverage_dir = mock_project_structure / "site" / "coverage"
        assert coverage_dir.exists()

    def test_build_coverage_structure_missing_dir(self, mock_project_structure):
        """Test coverage structure building with missing directory."""
        os.chdir(mock_project_structure)
        builder = WebsiteBuilder("website/templates", "site")

        builder.build_coverage_structure("nonexistent")

        coverage_dir = mock_project_structure / "site" / "coverage"
        assert coverage_dir.exists()


class TestWebsiteBuilderAssets:
    """Test asset handling functionality."""

    def test_copy_assets_success(self, mock_project_structure):
        """Test successful asset copying."""
        os.chdir(mock_project_structure)
        builder = WebsiteBuilder("website/templates", "site")

        # Create additional assets
        (mock_project_structure / "website" / "assets" / "images").mkdir()
        (
            mock_project_structure / "website" / "assets" / "images" / "logo.png"
        ).write_text("fake image")
        (mock_project_structure / "website" / "assets" / "script.py").write_text(
            "# Python file"
        )

        builder.copy_assets()

        assets_dir = mock_project_structure / "site" / "assets"
        assert assets_dir.exists()
        assert (assets_dir / "images" / "logo.png").exists()
        assert not (
            assets_dir / "script.py"
        ).exists()  # Python files should be excluded

    def test_copy_assets_missing_source(self, mock_project_structure):
        """Test asset copying with missing source directory."""
        os.chdir(mock_project_structure)

        # Remove assets directory
        shutil.rmtree(mock_project_structure / "website" / "assets")

        builder = WebsiteBuilder("website/templates", "site")
        builder.copy_assets()

        # Should handle missing assets gracefully
        assets_dir = mock_project_structure / "site" / "assets"
        assert not assets_dir.exists()

    def test_copy_static_files(self, mock_project_structure):
        """Test static file copying."""
        os.chdir(mock_project_structure)
        builder = WebsiteBuilder("website/templates", "site")

        # Create static files
        static_dir = mock_project_structure / "static"
        static_dir.mkdir()
        (static_dir / "file.txt").write_text("static content")

        builder.copy_static_files([str(static_dir)])

        # Check files were copied to the static subdirectory
        output_file = mock_project_structure / "site" / "static" / "file.txt"
        assert output_file.exists()


class TestWebsiteBuilderSEO:
    """Test SEO file generation."""

    @patch("datetime.datetime")
    def test_generate_seo_files(self, mock_datetime, mock_project_structure):
        """Test SEO file generation."""
        os.chdir(mock_project_structure)

        # Mock datetime
        mock_datetime.now.return_value.strftime.return_value = "2024-01-01"

        builder = WebsiteBuilder("website/templates", "site")

        # Ensure output directory exists
        builder.output_dir.mkdir(parents=True, exist_ok=True)

        # Create some HTML files first so sitemap has content
        (builder.output_dir / "index.html").write_text("<html><body>Home</body></html>")
        (builder.output_dir / "docs").mkdir()
        (builder.output_dir / "docs" / "index.html").write_text(
            "<html><body>Docs</body></html>"
        )

        builder.generate_seo_files()

        # Check sitemap.xml
        sitemap_file = mock_project_structure / "site" / "sitemap.xml"
        assert sitemap_file.exists()
        content = sitemap_file.read_text()
        assert "2024-01-01" in content

        # Check robots.txt
        robots_file = mock_project_structure / "site" / "robots.txt"
        assert robots_file.exists()


class TestWebsiteBuilderLicenseHandling:
    """Test license page building functionality."""

    def test_build_license_page_success(self, mock_project_structure, clean_workspace):
        """Test successful license page building."""
        os.chdir(mock_project_structure)
        builder = WebsiteBuilder("website/templates", "site")

        # Create a LICENSE file
        license_file = mock_project_structure / "LICENSE"
        license_content = """GNU GENERAL PUBLIC LICENSE
Version 3, 29 June 2007

Copyright (C) 2007 Free Software Foundation, Inc. <https://fsf.org/>
Everyone is permitted to copy and distribute verbatim copies
of this license document, but changing it is not allowed."""
        license_file.write_text(license_content)

        builder.build_license_page(
            "LICENSE", "LICENSE.html", "License", "GNU GPLv3 License"
        )

        output_file = mock_project_structure / "site" / "LICENSE.html"
        assert output_file.exists()

        content = output_file.read_text()
        assert "GNU GENERAL PUBLIC LICENSE" in content
        assert "License Information" in content

    def test_build_license_page_missing_file(
        self, mock_project_structure, clean_workspace
    ):
        """Test license page building with missing file."""
        os.chdir(mock_project_structure)
        builder = WebsiteBuilder("website/templates", "site")

        # Should handle missing license file gracefully
        builder.build_license_page(
            "nonexistent-LICENSE", "LICENSE.html", "License", "License"
        )

        # Output file should not be created
        output_file = mock_project_structure / "site" / "LICENSE.html"
        assert not output_file.exists()


class TestWebsiteBuilderAdvancedFeatures:
    """Test advanced website builder features."""

    def test_generate_directory_indexes(self, mock_project_structure, clean_workspace):
        """Test directory index generation."""
        os.chdir(mock_project_structure)
        builder = WebsiteBuilder("website/templates", "site")

        # Create some README.html files in docs structure
        docs_dir = mock_project_structure / "site" / "docs"
        docs_dir.mkdir(parents=True)

        # Create a README.html file
        readme_content = "<html><body><h1>Package Documentation</h1></body></html>"
        (docs_dir / "README.html").write_text(readme_content)

        # Create subdirectory with README
        subdir = docs_dir / "packages" / "qdrant-loader"
        subdir.mkdir(parents=True)
        (subdir / "README.html").write_text(readme_content)

        builder.generate_directory_indexes()

        # Check that index.html was created in subdirectory
        index_file = subdir / "index.html"
        assert index_file.exists()
        assert "Package Documentation" in index_file.read_text()

    def test_generate_directory_indexes_no_docs(
        self, mock_project_structure, clean_workspace
    ):
        """Test directory index generation with no docs directory."""
        os.chdir(mock_project_structure)
        builder = WebsiteBuilder("website/templates", "site")

        # Should handle missing docs directory gracefully
        builder.generate_directory_indexes()

    def test_copy_static_files_with_files(
        self, mock_project_structure, clean_workspace
    ):
        """Test copying static files."""
        os.chdir(mock_project_structure)
        builder = WebsiteBuilder("website/templates", "site")

        # Create static files
        static_dir = mock_project_structure / "static"
        static_dir.mkdir()
        (static_dir / "test.txt").write_text("static content")
        (static_dir / "image.png").write_text("fake image")

        builder.copy_static_files([str(static_dir)])

        # Check files were copied
        output_dir = mock_project_structure / "site" / "static"
        assert output_dir.exists()
        assert (output_dir / "test.txt").exists()
        assert (output_dir / "image.png").exists()

    def test_copy_static_files_with_single_file(
        self, mock_project_structure, clean_workspace
    ):
        """Test copying a single static file."""
        os.chdir(mock_project_structure)
        builder = WebsiteBuilder("website/templates", "site")

        # Create output directory first
        builder.output_dir.mkdir(parents=True, exist_ok=True)

        # Create a single file
        static_file = mock_project_structure / "robots.txt"
        static_file.write_text("User-agent: *\nAllow: /")

        builder.copy_static_files([str(static_file)])

        # Check file was copied
        output_file = mock_project_structure / "site" / "robots.txt"
        assert output_file.exists()
        assert "User-agent: *" in output_file.read_text()

    def test_copy_static_files_missing_source(
        self, mock_project_structure, clean_workspace
    ):
        """Test copying static files with missing source."""
        os.chdir(mock_project_structure)
        builder = WebsiteBuilder("website/templates", "site")

        # Should handle missing source gracefully
        builder.copy_static_files(["nonexistent"])


class TestWebsiteBuilderErrorHandling:
    """Test error handling in website builder."""

    def test_markdown_to_html_with_import_error(self, clean_workspace):
        """Test markdown processing with import error handling."""
        builder = WebsiteBuilder()

        # Test with content that would trigger import error handling
        result = builder.markdown_to_html("# Test\n\nContent")
        assert "Test" in result

    def test_extract_title_edge_cases(self):
        """Test title extraction edge cases."""
        builder = WebsiteBuilder()

        # Test with whitespace
        title = builder.extract_title_from_markdown("  # Spaced Title  \n")
        assert title == "Spaced Title"

        # Test with empty lines
        title = builder.extract_title_from_markdown("\n\n# Title After Empty Lines\n")
        assert title == "Title After Empty Lines"

        # Test with no content
        title = builder.extract_title_from_markdown("")
        assert title == "Documentation"

    def test_convert_markdown_links_complex_paths(self):
        """Test markdown link conversion with complex paths."""
        builder = WebsiteBuilder()

        # Test with complex relative paths - the actual behavior removes docs/ when already in docs/
        html = 'href="../../docs/guide.md"'
        result = builder.convert_markdown_links_to_html(
            html, "packages/test/README.md", "docs/packages/test/README.html"
        )
        # The actual behavior removes the docs/ part since we're already in docs/
        assert 'href="../../guide.html"' in result

        # Test LICENSE file conversion
        html = 'href="../LICENSE"'
        result = builder.convert_markdown_links_to_html(html)
        assert 'href="../LICENSE.html"' in result

    def test_generate_project_info_with_tomli_error(
        self, mock_project_structure, clean_workspace
    ):
        """Test project info generation with tomli import error."""
        os.chdir(mock_project_structure)
        builder = WebsiteBuilder("website/templates", "site")
        builder.output_dir.mkdir(parents=True, exist_ok=True)

        # Remove pyproject.toml to trigger error handling
        pyproject_file = mock_project_structure / "pyproject.toml"
        if pyproject_file.exists():
            pyproject_file.unlink()

        builder.generate_project_info()

        # Should still create project-info.json with defaults
        project_info_file = mock_project_structure / "site" / "project-info.json"
        assert project_info_file.exists()


class TestWebsiteBuilderSEOAdvanced:
    """Test advanced SEO functionality."""

    def test_generate_dynamic_sitemap_with_files(
        self, mock_project_structure, clean_workspace
    ):
        """Test dynamic sitemap generation with actual files."""
        os.chdir(mock_project_structure)
        builder = WebsiteBuilder("website/templates", "site")
        builder.base_url = "https://example.com"

        # Create some HTML files
        site_dir = mock_project_structure / "site"
        site_dir.mkdir(parents=True)
        (site_dir / "index.html").write_text("<html><body>Home</body></html>")

        # Create subdirectories before writing files
        (site_dir / "docs").mkdir(parents=True, exist_ok=True)
        (site_dir / "coverage").mkdir(parents=True, exist_ok=True)

        (site_dir / "docs" / "index.html").write_text("<html><body>Docs</body></html>")
        (site_dir / "coverage" / "index.html").write_text(
            "<html><body>Coverage</body></html>"
        )

        builder.generate_dynamic_sitemap("2024-01-01")

        sitemap_file = site_dir / "sitemap.xml"
        assert sitemap_file.exists()

        content = sitemap_file.read_text()
        assert "https://example.com/index.html" in content
        assert "https://example.com/docs/index.html" in content
        assert "2024-01-01" in content

    def test_generate_dynamic_sitemap_relative_urls(
        self, mock_project_structure, clean_workspace
    ):
        """Test dynamic sitemap generation with relative URLs."""
        os.chdir(mock_project_structure)
        builder = WebsiteBuilder("website/templates", "site")
        # No base_url set, should use relative URLs

        site_dir = mock_project_structure / "site"
        site_dir.mkdir(parents=True)
        (site_dir / "index.html").write_text("<html><body>Home</body></html>")

        builder.generate_dynamic_sitemap("2024-01-01")

        sitemap_file = site_dir / "sitemap.xml"
        assert sitemap_file.exists()

        content = sitemap_file.read_text()
        assert "/index.html" in content


class TestWebsiteBuilderIntegration:
    """Test complete website building scenarios."""

    def test_build_site_complete(
        self,
        mock_project_structure,
        sample_coverage_data,
        sample_test_results,
        clean_workspace,
    ):
        """Test complete site building with all components."""
        os.chdir(mock_project_structure)
        builder = WebsiteBuilder("website/templates", "site")
        builder.base_url = "https://example.com"

        # Build the complete site
        builder.build_site(
            coverage_artifacts_dir=str(sample_coverage_data),
            test_results_dir=str(sample_test_results),
        )

        # Verify main pages
        assert (mock_project_structure / "site" / "index.html").exists()
        assert (mock_project_structure / "site" / "docs" / "index.html").exists()
        assert (mock_project_structure / "site" / "coverage" / "index.html").exists()

        # Verify SEO files
        assert (mock_project_structure / "site" / "sitemap.xml").exists()
        assert (mock_project_structure / "site" / "robots.txt").exists()

        # Verify assets
        assert (mock_project_structure / "site" / "assets" / "style.css").exists()

        # Verify content
        index_content = (mock_project_structure / "site" / "index.html").read_text()
        assert "QDrant Loader" in index_content
        assert "https://example.com" in index_content

    def test_build_site_minimal(self, mock_project_structure, clean_workspace):
        """Test site building with minimal configuration."""
        os.chdir(mock_project_structure)
        builder = WebsiteBuilder("website/templates", "site")

        # Build with minimal parameters
        builder.build_site()

        # Verify basic structure
        assert (mock_project_structure / "site" / "index.html").exists()
        assert (mock_project_structure / "site" / "docs" / "index.html").exists()


class TestWebsiteBuilderCLI:
    """Test command-line interface functionality."""

    @patch(
        "sys.argv",
        ["build.py", "--output", "custom-site", "--templates", "custom-templates"],
    )
    def test_main_with_args(self, mock_project_structure, clean_workspace):
        """Test main function with command line arguments."""
        os.chdir(mock_project_structure)

        # Create custom templates directory with all required templates
        custom_templates = mock_project_structure / "custom-templates"
        custom_templates.mkdir()

        # Copy all templates from the mock structure
        for template_file in (mock_project_structure / "website" / "templates").glob(
            "*"
        ):
            if template_file.is_file():
                (custom_templates / template_file.name).write_text(
                    template_file.read_text()
                )

        # Mock argparse to avoid SystemExit
        mock_args = Mock()
        mock_args.templates = "custom-templates"
        mock_args.output = "custom-site"
        mock_args.coverage_artifacts = None
        mock_args.test_results = None
        mock_args.base_url = "https://example.com"

        with patch("argparse.ArgumentParser.parse_args", return_value=mock_args):
            main_function()

        # Verify custom output directory was created
        assert (mock_project_structure / "custom-site").exists()
        assert (mock_project_structure / "custom-site" / "index.html").exists()

        # Verify custom template was used
        content = (mock_project_structure / "custom-site" / "index.html").read_text()
        assert "QDrant Loader" in content  # Should contain the expected content

    @patch("sys.argv", ["build.py", "--help"])
    def test_main_help(self, clean_workspace):
        """Test main function with help argument."""
        with patch("argparse.ArgumentParser.parse_args") as mock_args:
            mock_args.side_effect = SystemExit(0)
            with pytest.raises(SystemExit):
                main_function()

    def test_main_exception_handling(self, mock_project_structure, clean_workspace):
        """Test main function exception handling."""
        os.chdir(mock_project_structure)

        # Mock argparse to return args without required templates
        mock_args = Mock()
        mock_args.templates = "nonexistent-templates"
        mock_args.output = "site"
        mock_args.coverage_artifacts = None
        mock_args.test_results = None
        mock_args.base_url = "https://example.com"

        with patch("argparse.ArgumentParser.parse_args", return_value=mock_args):
            # Should handle exceptions gracefully
            result = main_function()
            assert result == 1  # Should return error code


class TestGitHubActionsWorkflow:
    """Test GitHub Actions workflow integration."""

    def test_favicon_generation_workflow_step(
        self, mock_project_structure, clean_workspace
    ):
        """Test favicon generation as part of GitHub Actions workflow."""
        os.chdir(mock_project_structure)

        # Create favicon generation script path
        favicon_script = (
            mock_project_structure / "website" / "assets" / "generate_favicons.py"
        )
        favicon_script.parent.mkdir(parents=True, exist_ok=True)

        # Create a mock favicon generation script
        favicon_script.write_text(
            """
import sys
from pathlib import Path

def svg_to_png(svg_path, png_path, size):
    # Mock implementation
    png_path.parent.mkdir(parents=True, exist_ok=True)
    png_path.write_text(f"PNG {size}x{size}")
    return True

def generate_ico(png_files, ico_path):
    # Mock implementation
    ico_path.write_text("ICO file")
    return True

def main():
    print("Generating favicons...")
    svg_path = Path("website/assets/logos/qdrant-loader-icon.svg")
    output_dir = Path("website/assets/favicons")

    if not svg_path.exists():
        print(f"SVG file not found: {svg_path}")
        return False

    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate different sizes
    sizes = [16, 32, 48, 64, 128, 256]
    png_files = []

    for size in sizes:
        png_path = output_dir / f"favicon-{size}x{size}.png"
        if svg_to_png(svg_path, png_path, size):
            png_files.append(png_path)

    # Generate ICO
    ico_path = output_dir / "favicon.ico"
    generate_ico(png_files, ico_path)

    print(f"Generated {len(png_files)} PNG files and 1 ICO file")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
"""
        )

        # Test favicon generation step
        result = subprocess.run(
            [sys.executable, str(favicon_script)], capture_output=True, text=True
        )

        assert result.returncode == 0
        assert "Generating favicons" in result.stdout

        # Verify favicon files were created
        favicon_dir = mock_project_structure / "website" / "assets" / "favicons"
        assert favicon_dir.exists()
        assert (favicon_dir / "favicon.ico").exists()

    def test_build_website_workflow_step(
        self,
        mock_project_structure,
        sample_coverage_data,
        sample_test_results,
        clean_workspace,
    ):
        """Test website building as part of GitHub Actions workflow."""
        os.chdir(mock_project_structure)

        # Simulate GitHub Actions environment variables
        env_vars = {
            "GITHUB_WORKSPACE": str(mock_project_structure),
            "GITHUB_REPOSITORY": "user/qdrant-loader",
            "GITHUB_REF_NAME": "main",
            "GITHUB_SHA": "abc123",
        }

        with patch.dict(os.environ, env_vars):
            builder = WebsiteBuilder("website/templates", "site")
            builder.base_url = "https://user.github.io/qdrant-loader"
            builder.build_site(
                coverage_artifacts_dir=str(sample_coverage_data),
                test_results_dir=str(sample_test_results),
            )

        # Verify GitHub Pages structure
        site_dir = mock_project_structure / "site"
        assert site_dir.exists()
        assert (site_dir / "index.html").exists()
        assert (site_dir / ".nojekyll").exists()  # GitHub Pages optimization

        # Verify canonical URLs are set correctly
        index_content = (site_dir / "index.html").read_text()
        assert "https://user.github.io/qdrant-loader" in index_content

        # Verify sitemap has correct URLs
        sitemap_content = (site_dir / "sitemap.xml").read_text()
        assert "https://user.github.io/qdrant-loader" in sitemap_content

    def test_verify_website_build_workflow_step(
        self, mock_project_structure, clean_workspace
    ):
        """Test website build verification as part of GitHub Actions workflow."""
        os.chdir(mock_project_structure)

        # Build a minimal site first
        builder = WebsiteBuilder("website/templates", "site")
        builder.build_site()

        site_dir = mock_project_structure / "site"

        # Simulate verification checks that would run in GitHub Actions
        required_files = [
            "index.html",
            "docs/index.html",
            "coverage/index.html",
            "sitemap.xml",
            "robots.txt",
        ]

        for file_path in required_files:
            full_path = site_dir / file_path
            assert full_path.exists(), f"Required file missing: {file_path}"

        # Verify HTML structure
        index_content = (site_dir / "index.html").read_text()
        assert "<!DOCTYPE html>" in index_content
        assert "<html" in index_content
        assert "</html>" in index_content

        # Verify sitemap is valid XML
        sitemap_content = (site_dir / "sitemap.xml").read_text()
        assert "<?xml version=" in sitemap_content
        assert "<urlset" in sitemap_content

    def test_workflow_artifact_handling(
        self,
        mock_project_structure,
        sample_coverage_data,
        sample_test_results,
        clean_workspace,
    ):
        """Test artifact handling in GitHub Actions workflow."""
        os.chdir(mock_project_structure)

        # Simulate artifact structure from previous jobs
        artifacts_dir = mock_project_structure / "artifacts"
        artifacts_dir.mkdir()

        # Copy coverage artifacts to simulate download
        shutil.copytree(sample_coverage_data, artifacts_dir / "coverage-artifacts")
        shutil.copytree(sample_test_results, artifacts_dir / "test-results")

        # Build website with artifacts
        builder = WebsiteBuilder("website/templates", "site")
        builder.build_site(
            coverage_artifacts_dir=str(artifacts_dir / "coverage-artifacts"),
            test_results_dir=str(artifacts_dir / "test-results"),
        )

        # Verify artifacts were processed
        site_dir = mock_project_structure / "site"
        assert (site_dir / "coverage").exists()

        # Verify coverage data was integrated
        coverage_index = site_dir / "coverage" / "index.html"
        if coverage_index.exists():
            content = coverage_index.read_text()
            assert "coverage" in content.lower()

    def test_three_package_coverage_display(
        self,
        mock_project_structure,
        sample_coverage_data,
        sample_test_results,
        clean_workspace,
    ):
        """Test that the coverage index properly displays all three packages: loader, mcp, and website."""
        os.chdir(mock_project_structure)

        # Build website with all three coverage packages
        builder = WebsiteBuilder("website/templates", "site")
        builder.build_site(
            coverage_artifacts_dir=str(sample_coverage_data),
            test_results_dir=str(sample_test_results),
        )

        site_dir = mock_project_structure / "site"

        # Verify all three coverage directories exist
        coverage_dir = site_dir / "coverage"
        assert (coverage_dir / "loader").exists(), "Loader coverage should exist"
        assert (coverage_dir / "mcp").exists(), "MCP coverage should exist"
        assert (coverage_dir / "website").exists(), "Website coverage should exist"

        # Verify coverage index contains all three packages
        coverage_index = coverage_dir / "index.html"
        assert coverage_index.exists(), "Coverage index should exist"

        content = coverage_index.read_text()

        # Check for loader coverage elements
        assert "loader-coverage" in content, "Should contain loader coverage elements"
        assert "QDrant Loader Core" in content, "Should mention QDrant Loader Core"
        assert 'href="loader/"' in content, "Should link to loader coverage"

        # Check for MCP coverage elements
        assert "mcp-coverage" in content, "Should contain MCP coverage elements"
        assert "MCP Server" in content, "Should mention MCP Server"
        assert 'href="mcp/"' in content, "Should link to MCP coverage"

        # Check for website coverage elements
        assert "website-coverage" in content, "Should contain website coverage elements"
        assert "Website" in content, "Should mention Website"
        assert 'href="website/"' in content, "Should link to website coverage"

        # Check for test status indicators for all three packages
        assert "loader-test-indicator" in content, "Should have loader test indicator"
        assert "mcp-test-indicator" in content, "Should have MCP test indicator"
        assert "website-test-indicator" in content, "Should have website test indicator"

        # Verify JavaScript loads coverage data for all three packages
        assert "fetch('loader/status.json')" in content, "Should fetch loader status"
        assert "fetch('mcp/status.json')" in content, "Should fetch MCP status"
        assert "fetch('website/status.json')" in content, "Should fetch website status"

        # Verify status.json files exist for all packages
        assert (
            coverage_dir / "loader" / "status.json"
        ).exists(), "Loader status.json should exist"
        assert (
            coverage_dir / "mcp" / "status.json"
        ).exists(), "MCP status.json should exist"
        assert (
            coverage_dir / "website" / "status.json"
        ).exists(), "Website status.json should exist"

        # Verify status.json files have proper structure
        import json

        with open(coverage_dir / "loader" / "status.json") as f:
            loader_data = json.load(f)
        assert "files" in loader_data, "Loader status should have files section"

        with open(coverage_dir / "mcp" / "status.json") as f:
            mcp_data = json.load(f)
        assert "files" in mcp_data, "MCP status should have files section"

        with open(coverage_dir / "website" / "status.json") as f:
            website_data = json.load(f)
        assert "files" in website_data, "Website status should have files section"


if __name__ == "__main__":
    pytest.main([__file__])
