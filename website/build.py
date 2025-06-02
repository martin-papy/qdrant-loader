#!/usr/bin/env python3
"""
Website builder for QDrant Loader documentation site.
Uses templates with replaceable content to generate static HTML pages.
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
import argparse
import re


class WebsiteBuilder:
    """Builds the QDrant Loader documentation website from templates."""

    def __init__(
        self, templates_dir: str = "website/templates", output_dir: str = "site"
    ):
        """Initialize the website builder."""
        self.templates_dir = Path(templates_dir)
        self.output_dir = Path(output_dir)
        self.base_url = ""

    def load_template(self, template_name: str) -> str:
        """Load a template file."""
        template_path = self.templates_dir / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()

    def replace_placeholders(self, content: str, replacements: Dict[str, str]) -> str:
        """Replace placeholders in content with actual values."""
        for placeholder, value in replacements.items():
            content = content.replace(f"{{{{ {placeholder} }}}}", str(value))
        return content

    def markdown_to_html(self, markdown_content: str) -> str:
        """Convert markdown to HTML with Bootstrap styling."""
        try:
            import markdown
            from markdown.extensions import codehilite, toc, tables, fenced_code

            md = markdown.Markdown(
                extensions=[
                    "codehilite",
                    "toc",
                    "tables",
                    "fenced_code",
                    "attr_list",
                    "def_list",
                    "footnotes",
                    "md_in_html",
                ],
                extension_configs={
                    "codehilite": {"css_class": "highlight", "use_pygments": True},
                    "toc": {
                        "permalink": False,  # Disable the ¶ characters
                        "permalink_class": "text-decoration-none",
                        "permalink_title": "Link to this section",
                    },
                },
            )

            html_content = md.convert(markdown_content)

            # Add Bootstrap classes to common elements
            html_content = self.add_bootstrap_classes(html_content)

            # Convert markdown links to HTML links
            html_content = self.convert_markdown_links_to_html(html_content)

            return html_content

        except ImportError:
            print("⚠️  Markdown library not available, falling back to basic conversion")
            return self.basic_markdown_to_html(markdown_content)

    def convert_markdown_links_to_html(self, html_content: str) -> str:
        """Convert markdown file links to HTML file links in the content."""
        import re

        # Convert relative markdown links to HTML links
        # Pattern: href="./path/file.md" or href="path/file.md"
        html_content = re.sub(
            r'href="(\./)?([^"]*?)\.md"', r'href="\1\2.html"', html_content
        )

        # Convert absolute markdown links to HTML links
        # Pattern: href="/docs/file.md"
        html_content = re.sub(r'href="(/[^"]*?)\.md"', r'href="\1.html"', html_content)

        return html_content

    def basic_markdown_to_html(self, markdown_content: str) -> str:
        """Basic markdown to HTML conversion without external dependencies."""
        html = markdown_content

        # Headers
        html = re.sub(
            r"^# (.*?)$",
            r'<h1 class="display-4 fw-bold text-primary mb-4">\1</h1>',
            html,
            flags=re.MULTILINE,
        )
        html = re.sub(
            r"^## (.*?)$",
            r'<h2 class="h3 fw-bold text-primary mt-5 mb-3">\1</h2>',
            html,
            flags=re.MULTILINE,
        )
        html = re.sub(
            r"^### (.*?)$",
            r'<h3 class="h4 fw-bold mt-4 mb-3">\1</h3>',
            html,
            flags=re.MULTILINE,
        )
        html = re.sub(
            r"^#### (.*?)$",
            r'<h4 class="h5 fw-bold mt-3 mb-2">\1</h4>',
            html,
            flags=re.MULTILINE,
        )

        # Code blocks
        html = re.sub(
            r"```(\w+)?\n(.*?)\n```",
            r'<pre class="bg-dark text-light p-3 rounded"><code>\2</code></pre>',
            html,
            flags=re.DOTALL,
        )
        html = re.sub(
            r"`([^`]+)`",
            r'<code class="bg-light text-dark px-2 py-1 rounded">\1</code>',
            html,
        )

        # Links
        html = re.sub(
            r"\[([^\]]+)\]\(([^)]+)\)",
            r'<a href="\2" class="text-decoration-none">\1</a>',
            html,
        )

        # Bold and italic
        html = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", html)
        html = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", html)

        # Lists
        html = re.sub(r"^- (.*?)$", r"<li>\1</li>", html, flags=re.MULTILINE)
        html = re.sub(
            r"(<li>.*?</li>)",
            r'<ul class="list-group list-group-flush">\1</ul>',
            html,
            flags=re.DOTALL,
        )

        # Paragraphs
        lines = html.split("\n")
        processed_lines = []
        in_list = False

        for line in lines:
            line = line.strip()
            if not line:
                continue
            elif (
                line.startswith("<h")
                or line.startswith("<pre")
                or line.startswith("<ul")
                or line.startswith("<li")
            ):
                processed_lines.append(line)
            else:
                processed_lines.append(f'<p class="mb-3">{line}</p>')

        return "\n".join(processed_lines)

    def add_bootstrap_classes(self, html_content: str) -> str:
        """Add Bootstrap classes to HTML elements."""
        # Headers
        html_content = re.sub(
            r"<h1([^>]*)>",
            r'<h1\1 class="display-4 fw-bold text-primary mb-4">',
            html_content,
        )
        html_content = re.sub(
            r"<h2([^>]*)>",
            r'<h2\1 class="h3 fw-bold text-primary mt-5 mb-3">',
            html_content,
        )
        html_content = re.sub(
            r"<h3([^>]*)>", r'<h3\1 class="h4 fw-bold mt-4 mb-3">', html_content
        )
        html_content = re.sub(
            r"<h4([^>]*)>", r'<h4\1 class="h5 fw-bold mt-3 mb-2">', html_content
        )
        html_content = re.sub(
            r"<h5([^>]*)>", r'<h5\1 class="h6 fw-bold mt-3 mb-2">', html_content
        )
        html_content = re.sub(
            r"<h6([^>]*)>", r'<h6\1 class="fw-bold mt-2 mb-2">', html_content
        )

        # Paragraphs
        html_content = re.sub(r"<p([^>]*)>", r'<p\1 class="mb-3">', html_content)

        # Lists
        html_content = re.sub(
            r"<ul([^>]*)>",
            r'<ul\1 class="list-group list-group-flush mb-4">',
            html_content,
        )
        html_content = re.sub(
            r"<ol([^>]*)>",
            r'<ol\1 class="list-group list-group-numbered mb-4">',
            html_content,
        )
        html_content = re.sub(
            r"<li([^>]*)>",
            r'<li\1 class="list-group-item border-0 px-0">',
            html_content,
        )

        # Tables
        html_content = re.sub(
            r"<table([^>]*)>",
            r'<div class="table-responsive mb-4"><table\1 class="table table-striped table-hover">',
            html_content,
        )
        html_content = re.sub(r"</table>", r"</table></div>", html_content)
        html_content = re.sub(
            r"<th([^>]*)>", r'<th\1 class="bg-primary text-white">', html_content
        )

        # Code blocks
        html_content = re.sub(
            r"<pre([^>]*)>",
            r'<pre\1 class="bg-dark text-light p-3 rounded mb-4">',
            html_content,
        )
        html_content = re.sub(
            r"<code([^>]*)>",
            r'<code\1 class="bg-light text-dark px-2 py-1 rounded">',
            html_content,
        )

        # Links
        html_content = re.sub(
            r'<a([^>]*href="http[^"]*"[^>]*)>',
            r'<a\1 class="text-decoration-none" target="_blank">',
            html_content,
        )
        html_content = re.sub(
            r'<a([^>]*href="(?!http)[^"]*"[^>]*)>',
            r'<a\1 class="text-decoration-none">',
            html_content,
        )

        # Blockquotes
        html_content = re.sub(
            r"<blockquote([^>]*)>",
            r'<blockquote\1 class="blockquote border-start border-primary border-4 ps-3 mb-4">',
            html_content,
        )

        return html_content

    def extract_title_from_markdown(self, markdown_content: str) -> str:
        """Extract the first H1 title from markdown content."""
        lines = markdown_content.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
        return "Documentation"

    def build_page(
        self,
        template_name: str,
        content_template: str,
        page_title: str,
        page_description: str,
        output_file: str,
        additional_replacements: Optional[Dict[str, str]] = None,
    ) -> None:
        """Build a complete page using base template and content template."""

        # Load templates
        base_template = self.load_template("base.html")
        content = self.load_template(content_template)

        # Calculate relative path to root based on output file location
        output_path = Path(output_file)
        depth = len(output_path.parts) - 1  # Number of directories deep

        # Calculate correct base URL for this page depth
        if depth == 0:
            page_base_url = self.base_url
        else:
            page_base_url = (
                "../" * depth + self.base_url if self.base_url else "../" * depth
            )

        # Calculate canonical URL
        if self.base_url.startswith("http"):
            # Full URL provided
            canonical_url = (
                self.base_url.rstrip("/") + "/" + output_file.replace("index.html", "")
            )
        else:
            # Relative URL or GitHub Pages
            canonical_url = (
                f"https://qdrant-loader.net/{output_file.replace('index.html', '')}"
            )

        # Get version from project info if available
        version = "0.4.0b1"  # Default version
        try:
            import tomli

            with open("pyproject.toml", "rb") as f:
                pyproject = tomli.load(f)
                version = pyproject.get("project", {}).get("version", version)
        except:
            pass

        # Prepare replacements
        replacements = {
            "page_title": page_title,
            "page_description": page_description,
            "content": content,
            "base_url": page_base_url,  # Use calculated base URL
            "canonical_url": canonical_url,
            "version": version,
            "additional_head": "",
            "additional_scripts": "",
        }

        # Add any additional replacements
        if additional_replacements:
            replacements.update(additional_replacements)

        # Replace placeholders
        final_content = self.replace_placeholders(base_template, replacements)

        # Write output file
        output_path = self.output_dir / output_file
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(final_content)

        print(f"✅ Built: {output_file}")

    def build_markdown_page(
        self,
        markdown_file: str,
        output_file: str,
        page_title: Optional[str] = None,
        page_description: Optional[str] = None,
        breadcrumb: Optional[str] = None,
    ) -> None:
        """Build a page from a markdown file using the documentation template."""

        # Read markdown file
        markdown_path = Path(markdown_file)
        if not markdown_path.exists():
            print(f"⚠️  Markdown file not found: {markdown_file}")
            return

        with open(markdown_path, "r", encoding="utf-8") as f:
            markdown_content = f.read()

        # Extract title if not provided
        if not page_title:
            page_title = self.extract_title_from_markdown(markdown_content)

        # Generate description if not provided
        if not page_description:
            # Use first paragraph as description
            lines = markdown_content.split("\n")
            for line in lines:
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("```"):
                    page_description = line[:150] + "..." if len(line) > 150 else line
                    break
            if not page_description:
                page_description = f"Documentation for {page_title}"

        # Convert markdown to HTML
        html_content = self.markdown_to_html(markdown_content)

        # Calculate relative paths based on output file location
        output_path = Path(output_file)
        depth = len(output_path.parts) - 1  # Number of directories deep

        # Calculate relative path to root
        if depth == 0:
            home_url = self.base_url
            docs_url = f"{self.base_url}docs/"
            page_base_url = self.base_url
        else:
            home_url = "../" * depth + self.base_url if self.base_url else "../" * depth
            docs_url = (
                "../" * (depth - 1) + self.base_url
                if self.base_url
                else "../" * (depth - 1)
            )
            page_base_url = (
                "../" * depth + self.base_url if self.base_url else "../" * depth
            )

        # Create breadcrumb navigation
        breadcrumb_html = ""
        if breadcrumb:
            breadcrumb_html = f"""
            <nav aria-label="breadcrumb" class="mb-4">
                <ol class="breadcrumb">
                    <li class="breadcrumb-item">
                        <a href="{home_url}" class="text-decoration-none">
                            <i class="bi bi-house me-1"></i>Home
                        </a>
                    </li>
                    <li class="breadcrumb-item">
                        <a href="{docs_url}" class="text-decoration-none">Documentation</a>
                    </li>
                    <li class="breadcrumb-item active" aria-current="page">{breadcrumb}</li>
                </ol>
            </nav>
            """

        # Create the documentation content template
        doc_content = f"""
        <section class="py-5">
            <div class="container">
                <div class="row justify-content-center">
                    <div class="col-lg-10">
                        {breadcrumb_html}
                        <div class="card border-0 shadow">
                            <div class="card-body p-5">
                                {html_content}
                            </div>
                        </div>
                        
                        <!-- Navigation footer -->
                        <div class="d-flex justify-content-between align-items-center mt-4">
                            <a href="{docs_url}" class="btn btn-outline-primary">
                                <i class="bi bi-arrow-left me-2"></i>Back to Documentation
                            </a>
                            <div class="text-muted small">
                                <i class="bi bi-file-text me-1"></i>
                                Generated from {markdown_path.name}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </section>
        """

        # Build the page using base template
        base_template = self.load_template("base.html")

        # Calculate canonical URL
        if self.base_url.startswith("http"):
            # Full URL provided
            canonical_url = (
                self.base_url.rstrip("/") + "/" + output_file.replace("index.html", "")
            )
        else:
            # Relative URL or GitHub Pages
            canonical_url = (
                f"https://qdrant-loader.net/{output_file.replace('index.html', '')}"
            )

        # Get version from project info if available
        version = "0.4.0b1"  # Default version
        try:
            import tomli

            with open("pyproject.toml", "rb") as f:
                pyproject = tomli.load(f)
                version = pyproject.get("project", {}).get("version", version)
        except:
            pass

        replacements = {
            "page_title": page_title,
            "page_description": page_description,
            "content": doc_content,
            "base_url": page_base_url,
            "canonical_url": canonical_url,
            "version": version,
            "additional_head": """
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css">
            """,
            "additional_scripts": """
            <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
            <script>hljs.highlightAll();</script>
            """,
        }

        final_content = self.replace_placeholders(base_template, replacements)

        # Write output file
        output_path = self.output_dir / output_file
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(final_content)

        print(f"📄 Built markdown page: {output_file}")

    def copy_static_files(self, source_dirs: list) -> None:
        """Copy static files (docs, coverage, etc.) to output directory."""
        for source_dir in source_dirs:
            source_path = Path(source_dir)
            if source_path.exists():
                if source_path.is_dir():
                    dest_path = self.output_dir / source_path.name
                    if dest_path.exists():
                        shutil.rmtree(dest_path)
                    shutil.copytree(source_path, dest_path)
                    print(f"📁 Copied directory: {source_dir} -> {dest_path}")
                else:
                    dest_path = self.output_dir / source_path.name
                    shutil.copy2(source_path, dest_path)
                    print(f"📄 Copied file: {source_dir} -> {dest_path}")
            else:
                print(f"⚠️  Source not found: {source_dir}")

    def generate_project_info(
        self,
        version: Optional[str] = None,
        commit_sha: Optional[str] = None,
        commit_date: Optional[str] = None,
    ) -> None:
        """Generate project information JSON file."""
        import subprocess
        from datetime import datetime

        # Get version from pyproject.toml if not provided
        if not version:
            try:
                import tomli

                with open("pyproject.toml", "rb") as f:
                    data = tomli.load(f)
                    version = data["project"]["version"]
            except Exception:
                version = "unknown"

        # Get git info if not provided
        if not commit_sha:
            try:
                commit_sha = (
                    subprocess.check_output(["git", "rev-parse", "HEAD"])
                    .decode()
                    .strip()
                )
            except Exception:
                commit_sha = "unknown"

        if not commit_date:
            try:
                commit_date = (
                    subprocess.check_output(
                        ["git", "log", "-1", "--format=%cd", "--date=iso"]
                    )
                    .decode()
                    .strip()
                )
            except Exception:
                commit_date = datetime.now().isoformat()

        project_info = {
            "name": "QDrant Loader",
            "version": version,
            "description": "Enterprise-ready vector database toolkit for building searchable knowledge bases from multiple data sources",
            "commit": {
                "sha": commit_sha,
                "short": commit_sha[:7] if commit_sha != "unknown" else "unknown",
                "date": commit_date,
            },
            "build": {
                "timestamp": datetime.now().isoformat(),
                "workflow_run_id": os.getenv("GITHUB_RUN_ID", "local"),
            },
        }

        project_info_path = self.output_dir / "project-info.json"
        with open(project_info_path, "w", encoding="utf-8") as f:
            json.dump(project_info, f, indent=2)

        print(f"📊 Generated: project-info.json")

    def build_docs_structure(self) -> None:
        """Build documentation structure by converting markdown files to HTML."""
        docs_output = self.output_dir / "docs"
        docs_output.mkdir(parents=True, exist_ok=True)

        # Main documentation files
        main_docs = [
            ("README.md", "docs/README.html", "QDrant Loader", "Main documentation"),
            (
                "RELEASE_NOTES.md",
                "docs/RELEASE_NOTES.html",
                "Release Notes",
                "Version history and changes",
            ),
        ]

        for source, output, title, description in main_docs:
            if Path(source).exists():
                self.build_markdown_page(source, output, title, description, title)

        # Documentation directory files
        if Path("docs").exists():
            for md_file in Path("docs").rglob("*.md"):
                relative_path = md_file.relative_to("docs")
                output_path = f"docs/{relative_path.with_suffix('.html')}"
                breadcrumb = (
                    relative_path.stem.replace("-", " ").replace("_", " ").title()
                )

                self.build_markdown_page(
                    str(md_file), output_path, breadcrumb=breadcrumb
                )

        # Package documentation
        package_docs = [
            (
                "packages/qdrant-loader/README.md",
                "docs/packages/qdrant-loader/README.html",
                "QDrant Loader Package",
                "Core package documentation",
            ),
            (
                "packages/qdrant-loader-mcp-server/README.md",
                "docs/packages/mcp-server/README.html",
                "MCP Server Package",
                "Model Context Protocol server documentation",
            ),
        ]

        for source, output, title, description in package_docs:
            if Path(source).exists():
                self.build_markdown_page(source, output, title, description, title)

    def build_coverage_structure(
        self, coverage_artifacts_dir: Optional[str] = None
    ) -> None:
        """Build coverage reports structure."""
        coverage_output = self.output_dir / "coverage"
        coverage_output.mkdir(parents=True, exist_ok=True)

        if coverage_artifacts_dir and Path(coverage_artifacts_dir).exists():
            # Process coverage artifacts
            artifacts_path = Path(coverage_artifacts_dir)

            # Find and copy coverage reports
            for coverage_dir in artifacts_path.glob("htmlcov-*"):
                if coverage_dir.is_dir():
                    package_name = coverage_dir.name.replace("htmlcov-", "")
                    dest_path = coverage_output / package_name

                    if dest_path.exists():
                        shutil.rmtree(dest_path)
                    shutil.copytree(coverage_dir, dest_path)
                    print(f"📊 Copied coverage: {package_name}")
        else:
            print("⚠️  No coverage artifacts found")

    def copy_assets(self) -> None:
        """Copy assets directory to output, excluding Python files."""
        assets_src = self.templates_dir.parent / "assets"
        assets_dest = self.output_dir / "assets"

        if assets_src.exists():
            if assets_dest.exists():
                shutil.rmtree(assets_dest)

            # Copy assets but exclude Python files
            def ignore_python_files(dir, files):
                return [f for f in files if f.endswith(".py")]

            shutil.copytree(assets_src, assets_dest, ignore=ignore_python_files)
            print(f"📁 Copied assets to {assets_dest} (excluding Python files)")
        else:
            print("⚠️  Assets directory not found")

    def generate_seo_files(self) -> None:
        """Generate sitemap.xml and robots.txt for SEO."""
        from datetime import datetime

        build_date = datetime.now().strftime("%Y-%m-%d")

        # Generate sitemap.xml
        sitemap_template = self.load_template("sitemap.xml")
        sitemap_content = sitemap_template.replace("{{ build_date }}", build_date)

        # Replace hardcoded URLs with base_url if provided
        if self.base_url:
            # Replace the hardcoded domain with the provided base_url
            sitemap_content = sitemap_content.replace(
                "https://qdrant-loader.net", self.base_url.rstrip("/")
            )

        sitemap_path = self.output_dir / "sitemap.xml"
        with open(sitemap_path, "w", encoding="utf-8") as f:
            f.write(sitemap_content)
        print("📄 Generated: sitemap.xml")

        # Generate robots.txt
        robots_template = self.load_template("robots.txt")
        robots_path = self.output_dir / "robots.txt"
        with open(robots_path, "w", encoding="utf-8") as f:
            f.write(robots_template)
        print("📄 Generated: robots.txt")

        # Generate .nojekyll for GitHub Pages optimization
        nojekyll_path = self.output_dir / ".nojekyll"
        nojekyll_path.touch()
        print("📄 Generated: .nojekyll")

    def build_site(
        self,
        coverage_artifacts_dir: Optional[str] = None,
        test_results_dir: Optional[str] = None,
    ) -> None:
        """Build the complete website."""
        print("🏗️  Building QDrant Loader website...")

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Copy assets first
        self.copy_assets()

        # Generate project info
        self.generate_project_info()

        # Generate SEO files
        self.generate_seo_files()

        # Build main pages
        self.build_page(
            "base.html",
            "index.html",
            "Home",
            "Enterprise-ready vector database toolkit for building searchable knowledge bases from multiple data sources including Confluence, Jira, and local files.",
            "index.html",
        )

        self.build_page(
            "base.html",
            "docs-index.html",
            "Documentation",
            "Comprehensive documentation for QDrant Loader - learn how to load data into Qdrant vector database from various sources.",
            "docs/index.html",
        )

        self.build_page(
            "base.html",
            "coverage-index.html",
            "Test Coverage",
            "Test coverage analysis and reports for QDrant Loader packages - ensuring code quality and reliability.",
            "coverage/index.html",
        )

        # Build documentation structure (converts MD to HTML)
        self.build_docs_structure()

        # Build coverage structure
        self.build_coverage_structure(coverage_artifacts_dir)

        # Copy test results if available
        if test_results_dir and Path(test_results_dir).exists():
            dest_path = self.output_dir / "test-results"
            if dest_path.exists():
                shutil.rmtree(dest_path)
            shutil.copytree(test_results_dir, dest_path)
            print(f"📊 Copied: test results")

        print(f"✅ Website built successfully in {self.output_dir}")
        print(f"📊 Generated {len(list(self.output_dir.rglob('*.html')))} HTML pages")
        print(f"📁 Total files: {len(list(self.output_dir.rglob('*')))}")


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

    try:
        builder.build_site(args.coverage_artifacts, args.test_results)
    except Exception as e:
        print(f"❌ Build failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
