#!/usr/bin/env python3
"""
Website builder for QDrant Loader documentation site.
Uses templates with replaceable content to generate static HTML pages.
"""

import argparse
import json
import os
import re
import shutil
from pathlib import Path


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

        with open(template_path, encoding="utf-8") as f:
            return f.read()

    def replace_placeholders(self, content: str, replacements: dict[str, str]) -> str:
        """Replace placeholders in content with actual values."""
        for placeholder, value in replacements.items():
            content = content.replace(f"{{{{ {placeholder} }}}}", str(value))
        return content

    def markdown_to_html(
        self, markdown_content: str, source_file: str = "", output_file: str = ""
    ) -> str:
        """Convert markdown to HTML with Bootstrap styling."""
        try:
            import markdown

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

            # Convert markdown links to HTML
            html_content = self.convert_markdown_links_to_html(
                html_content, source_file, output_file
            )

            return html_content

        except ImportError:
            print("⚠️  Markdown library not available, falling back to basic conversion")
            return self.basic_markdown_to_html(markdown_content)

    def convert_markdown_links_to_html(
        self, html_content: str, source_file: str = "", output_file: str = ""
    ) -> str:
        """Convert markdown file links to HTML file links in the content."""
        import re
        from pathlib import Path

        # Convert relative markdown links to HTML links
        # Pattern: href="./path/file.md" or href="path/file.md"
        html_content = re.sub(
            r'href="(\./)?([^"]*?)\.md"', r'href="\1\2.html"', html_content
        )

        # Convert absolute markdown links to HTML links
        # Pattern: href="/docs/file.md"
        html_content = re.sub(r'href="(/[^"]*?)\.md"', r'href="\1.html"', html_content)

        # Convert LICENSE file links to LICENSE.html
        # Pattern: href="path/LICENSE" or href="./path/LICENSE" or href="../../LICENSE"
        html_content = re.sub(
            r'href="([^"]*?)LICENSE"', r'href="\1LICENSE.html"', html_content
        )

        # Fix relative paths when source and output are in different directories
        if source_file and output_file:
            source_path = Path(source_file)
            output_path = Path(output_file)

            # Case 1: Main README.md moved to docs/README.html
            if (
                source_path.name == "README.md"
                and str(source_path.parent) == "."
                and str(output_path.parent).startswith("docs")
            ):

                # Fix links that start with ./docs/ - remove the ./docs/ part since we're already in docs/
                html_content = re.sub(r'href="\./docs/', r'href="./', html_content)
                # Fix links that start with docs/ - make them relative
                html_content = re.sub(r'href="docs/', r'href="./', html_content)

            # Case 2: Package README.md moved from packages/*/README.md to docs/packages/*/README.html
            elif (
                source_path.name == "README.md"
                and str(source_path.parent).startswith("packages/")
                and str(output_path.parent).startswith("docs/packages/")
            ):
                # Calculate how many levels up we need to go to reach docs/
                # From docs/packages/qdrant-loader/ we need to go up 2 levels to reach docs/
                package_depth = (
                    len(output_path.parts) - 2
                )  # Subtract 2: one for filename, one for docs/
                up_levels = "../" * package_depth

                # Only rewrite relative links (not after href="http, href="https, or href="/)
                html_content = re.sub(
                    r'(?<!href="http)(?<!href="https)(?<!href="/)href="((\.\./)*|\./)?docs/',
                    f'href="{up_levels}',
                    html_content,
                )
                # Remove any accidental double slashes (but not after http: or https:)
                html_content = re.sub(r"(?<!http:)(?<!https:)//+", "/", html_content)
                # Remove any double docs/ that may have slipped through
                html_content = re.sub(r"docs/docs/", "docs/", html_content)

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
        additional_replacements: dict[str, str] | None = None,
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
            canonical_url = self.base_url.rstrip("/") + "/docs/"
        else:
            canonical_url = "/docs/"

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
        page_title: str | None = None,
        page_description: str | None = None,
        breadcrumb: str | None = None,
    ) -> None:
        """Build a page from a markdown file using the documentation template."""

        # Read markdown file
        markdown_path = Path(markdown_file)
        if not markdown_path.exists():
            print(f"⚠️  Markdown file not found: {markdown_file}")
            return

        with open(markdown_path, encoding="utf-8") as f:
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
        html_content = self.markdown_to_html(
            markdown_content, markdown_file, output_file
        )

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

            # Calculate docs_url - always point to the docs index page
            if output_file.startswith("docs/"):
                # For pages in docs/ directory structure
                # Count how many levels deep we are from the docs/ directory
                path_parts = Path(output_file).parts
                docs_depth = (
                    len(path_parts) - 2
                )  # Subtract 2: one for filename, one for docs/

                if docs_depth <= 0:
                    # Page is directly in docs/ directory (e.g., docs/README.html)
                    # Link should go to docs/index.html (which is in the same directory)
                    docs_url = "./" if not self.base_url else f"{self.base_url}docs/"
                else:
                    # Page is in a subdirectory of docs/ (e.g., docs/users/README.html, docs/packages/mcp-server/README.html)
                    # Link should go back to docs/index.html
                    if not self.base_url:
                        # For relative paths, go back the number of subdirectory levels to reach docs/
                        docs_url = "../" * docs_depth
                    else:
                        docs_url = f"{self.base_url}docs/"
            else:
                # For non-docs pages, calculate path to docs/
                docs_url = f"{self.base_url}docs/" if self.base_url else "docs/"

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
            canonical_url = (
                self.base_url.rstrip("/") + "/" + output_file.replace("index.html", "")
            )
        else:
            # Relative URL or GitHub Pages - use relative path for local testing
            canonical_url = f"/{output_file.replace('index.html', '')}"

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
        version: str | None = None,
        commit_sha: str | None = None,
        commit_date: str | None = None,
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

        print("📊 Generated: project-info.json")

    def build_license_page(
        self,
        license_file: str,
        output_file: str,
        page_title: str,
        page_description: str,
    ) -> None:
        """Build a page from a plain text LICENSE file."""

        # Read license file
        license_path = Path(license_file)
        if not license_path.exists():
            print(f"⚠️  License file not found: {license_file}")
            return

        with open(license_path, encoding="utf-8") as f:
            license_content = f.read()

        # Wrap license content in a code block for proper display
        html_content = f"""
        <div class="alert alert-info mb-4">
            <h4 class="alert-heading">
                <i class="bi bi-shield-check me-2"></i>License Information
            </h4>
            <p class="mb-0">
                This project is licensed under the GNU General Public License v3.0.
                The full license text is provided below.
            </p>
        </div>

        <div class="card border-0 shadow-sm">
            <div class="card-body">
                <pre class="bg-light p-4 rounded" style="white-space: pre-wrap; font-size: 0.9em; line-height: 1.4;">{license_content}</pre>
            </div>
        </div>

        <div class="mt-4">
            <p class="text-muted">
                <i class="bi bi-info-circle me-1"></i>
                For more information about the GNU GPLv3 license, visit
                <a href="https://www.gnu.org/licenses/gpl-3.0.html" target="_blank" class="text-decoration-none">
                    https://www.gnu.org/licenses/gpl-3.0.html
                </a>
            </p>
        </div>
        """

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
            docs_url = f"{self.base_url}docs/" if self.base_url else "docs/"
            page_base_url = (
                "../" * depth + self.base_url if self.base_url else "../" * depth
            )

        # Create the documentation content template
        doc_content = f"""
        <section class="py-5">
            <div class="container">
                <div class="row justify-content-center">
                    <div class="col-lg-10">
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
                                <li class="breadcrumb-item active" aria-current="page">{page_title}</li>
                            </ol>
                        </nav>

                        <div class="mb-4">
                            <h1 class="display-5 fw-bold text-primary">
                                <i class="bi bi-shield-check me-3"></i>{page_title}
                            </h1>
                            <p class="lead text-muted">{page_description}</p>
                        </div>

                        {html_content}

                        <!-- Navigation footer -->
                        <div class="d-flex justify-content-between align-items-center mt-4">
                            <a href="{docs_url}" class="btn btn-outline-primary">
                                <i class="bi bi-arrow-left me-2"></i>Back to Documentation
                            </a>
                            <div class="text-muted small">
                                <i class="bi bi-file-text me-1"></i>
                                Generated from {license_path.name}
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
            canonical_url = (
                self.base_url.rstrip("/") + "/" + output_file.replace("index.html", "")
            )
        else:
            canonical_url = f"/{output_file.replace('index.html', '')}"

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
            "additional_head": "",
            "additional_scripts": "",
        }

        final_content = self.replace_placeholders(base_template, replacements)

        # Write output file
        output_path = self.output_dir / output_file
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(final_content)

        print(f"📄 Built license page: {output_file}")

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
            (
                "CONTRIBUTING.md",
                "docs/CONTRIBUTING.html",
                "Contributing Guide",
                "How to contribute to the project",
            ),
            (
                "LICENSE",
                "docs/LICENSE.html",
                "License",
                "GNU GPLv3 License",
            ),
        ]

        for source, output, title, description in main_docs:
            if Path(source).exists():
                # Special handling for LICENSE file (plain text)
                if source == "LICENSE":
                    self.build_license_page(source, output, title, description)
                else:
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
        self, coverage_artifacts_dir: str | None = None
    ) -> None:
        """Build coverage reports structure."""
        coverage_output = self.output_dir / "coverage"
        coverage_output.mkdir(parents=True, exist_ok=True)

        if coverage_artifacts_dir and Path(coverage_artifacts_dir).exists():
            # Process coverage artifacts
            artifacts_path = Path(coverage_artifacts_dir)

            # First, look for htmlcov-* directories directly in the artifacts directory
            # (for backward compatibility or local builds)
            for coverage_dir in artifacts_path.glob("htmlcov-*"):
                if coverage_dir.is_dir():
                    package_name = coverage_dir.name.replace("htmlcov-", "")
                    dest_path = coverage_output / package_name

                    if dest_path.exists():
                        shutil.rmtree(dest_path)
                    shutil.copytree(coverage_dir, dest_path)
                    print(f"📊 Copied coverage: {package_name}")

            # Then, look for coverage artifacts in subdirectories (GitHub Actions structure)
            # Pattern: coverage-artifacts/coverage-{package}-{run_id}/htmlcov-{package}/
            for artifact_dir in artifacts_path.glob("coverage-*"):
                if artifact_dir.is_dir():
                    # Look for htmlcov-* directories inside this artifact directory
                    for coverage_dir in artifact_dir.glob("htmlcov-*"):
                        if coverage_dir.is_dir():
                            package_name = coverage_dir.name.replace("htmlcov-", "")
                            dest_path = coverage_output / package_name

                            if dest_path.exists():
                                shutil.rmtree(dest_path)
                            shutil.copytree(coverage_dir, dest_path)
                            print(
                                f"📊 Copied coverage: {package_name} (from {artifact_dir.name})"
                            )
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

        # Generate dynamic sitemap.xml based on actual files
        self.generate_dynamic_sitemap(build_date)

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

    def generate_dynamic_sitemap(self, build_date: str) -> None:
        """Generate sitemap.xml dynamically based on actual HTML files."""
        # Determine base URL for sitemap
        if self.base_url.startswith("http"):
            base_url = self.base_url.rstrip("/")
        else:
            # Use relative base URL for local testing
            base_url = ""

        # Find all HTML files in the output directory
        html_files = list(self.output_dir.rglob("*.html"))

        # Define URL priorities and change frequencies based on path patterns
        url_config = {
            # Main pages
            "index.html": {"priority": "1.0", "changefreq": "weekly"},
            "docs/index.html": {"priority": "0.9", "changefreq": "weekly"},
            "coverage/index.html": {"priority": "0.7", "changefreq": "daily"},
            "privacy-policy.html": {"priority": "0.5", "changefreq": "monthly"},
            # Documentation patterns
            "docs/README.html": {"priority": "0.8", "changefreq": "weekly"},
            "docs/RELEASE_NOTES.html": {"priority": "0.6", "changefreq": "monthly"},
            "docs/packages/": {"priority": "0.8", "changefreq": "weekly"},
            "docs/getting-started/": {"priority": "0.8", "changefreq": "weekly"},
            "docs/users/": {"priority": "0.7", "changefreq": "weekly"},
            "docs/developers/": {"priority": "0.6", "changefreq": "monthly"},
        }

        def get_url_config(file_path: str) -> dict:
            """Get priority and changefreq for a given file path."""
            # Convert to relative path from output directory
            rel_path = file_path.replace(str(self.output_dir) + "/", "")

            # Check for exact matches first
            if rel_path in url_config:
                return url_config[rel_path]

            # Check for pattern matches
            for pattern, config in url_config.items():
                if pattern.endswith("/") and rel_path.startswith(pattern):
                    return config

            # Default configuration
            return {"priority": "0.5", "changefreq": "monthly"}

        # Generate sitemap XML
        sitemap_content = ['<?xml version="1.0" encoding="UTF-8"?>']
        sitemap_content.append(
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        )

        # Sort files for consistent output
        sorted_files = sorted(html_files, key=lambda x: str(x))

        for html_file in sorted_files:
            # Get relative path from output directory
            rel_path = html_file.relative_to(self.output_dir)

            # Convert to URL path
            url_path = str(rel_path).replace("\\", "/")  # Handle Windows paths

            # Get configuration for this URL
            config = get_url_config(str(html_file))

            # Build full URL
            if base_url:
                full_url = f"{base_url}/{url_path}"
            else:
                # For local testing, use relative URLs
                full_url = f"/{url_path}"

            # Add URL entry to sitemap
            sitemap_content.extend(
                [
                    "    <url>",
                    f"        <loc>{full_url}</loc>",
                    f"        <lastmod>{build_date}</lastmod>",
                    f"        <changefreq>{config['changefreq']}</changefreq>",
                    f"        <priority>{config['priority']}</priority>",
                    "    </url>",
                ]
            )

        sitemap_content.append("</urlset>")

        # Write sitemap file
        sitemap_path = self.output_dir / "sitemap.xml"
        with open(sitemap_path, "w", encoding="utf-8") as f:
            f.write("\n".join(sitemap_content))

        print(f"📄 Generated: sitemap.xml ({len(sorted_files)} URLs)")

    def generate_dynamic_docs_index(self) -> str:
        """Generate dynamic documentation index content based on existing files."""

        # Scan for existing documentation files
        docs_structure = {
            "getting_started": [],
            "user_guides": [],
            "developer_docs": [],
            "packages": [],
            "release_info": [],
        }

        # Check for main documentation files
        main_docs = [
            ("README.md", "docs/README.html", "Main README", "Essential", "primary"),
            (
                "RELEASE_NOTES.md",
                "docs/RELEASE_NOTES.html",
                "Release Notes",
                "Updates",
                "secondary",
            ),
            (
                "CONTRIBUTING.md",
                "docs/CONTRIBUTING.html",
                "Contributing",
                "Community",
                "dark",
            ),
            (
                "LICENSE",
                "docs/LICENSE.html",
                "License",
                "Legal",
                "warning",
            ),
        ]

        for source_file, html_path, title, badge_text, badge_color in main_docs:
            if Path(source_file).exists():
                docs_structure["release_info"].append(
                    {
                        "url": html_path.replace("docs/", ""),
                        "title": title,
                        "icon": (
                            "bi-file-text"
                            if "README" in title
                            else (
                                "bi-clock-history"
                                if "Release" in title
                                else (
                                    "bi-people"
                                    if "Contributing" in title
                                    else "bi-shield-check"
                                )
                            )
                        ),
                        "badge": badge_text,
                        "badge_color": badge_color,
                    }
                )

        # Check for package documentation
        package_docs = [
            (
                "packages/qdrant-loader/README.md",
                "packages/qdrant-loader/README.html",
                "QDrant Loader",
                "Core",
                "info",
            ),
            (
                "packages/qdrant-loader-mcp-server/README.md",
                "packages/mcp-server/README.html",
                "MCP Server",
                "Integration",
                "info",
            ),
        ]

        for source_file, html_path, title, badge_text, badge_color in package_docs:
            if Path(source_file).exists():
                docs_structure["packages"].append(
                    {
                        "url": html_path,
                        "title": title,
                        "icon": "bi-arrow-repeat" if "Loader" in title else "bi-plug",
                        "badge": badge_text,
                        "badge_color": badge_color,
                    }
                )

        # Scan docs directory structure
        if Path("docs").exists():
            # Getting started guides
            getting_started_path = Path("docs/getting-started")
            if getting_started_path.exists():
                for md_file in getting_started_path.glob("*.md"):
                    if (
                        md_file.name != "README.md"
                    ):  # Skip README as it's handled separately
                        title = md_file.stem.replace("-", " ").replace("_", " ").title()
                        docs_structure["getting_started"].append(
                            {
                                "url": f"getting-started/{md_file.stem}.html",
                                "title": title,
                                "icon": "bi-play-circle",
                                "badge": "Guide",
                                "badge_color": "primary",
                            }
                        )

            # User guides
            users_path = Path("docs/users")
            if users_path.exists():
                # Main user sections
                user_sections = [
                    ("configuration", "Configuration", "bi-gear"),
                    ("detailed-guides", "Detailed Guides", "bi-book"),
                    ("cli-reference", "CLI Reference", "bi-terminal"),
                    ("workflows", "Workflows", "bi-diagram-3"),
                    ("troubleshooting", "Troubleshooting", "bi-question-circle"),
                ]

                for section_dir, section_title, icon in user_sections:
                    section_path = users_path / section_dir
                    if section_path.exists() and any(section_path.glob("*.md")):
                        docs_structure["user_guides"].append(
                            {
                                "url": f"users/{section_dir}/",
                                "title": section_title,
                                "icon": icon,
                                "badge": "Users",
                                "badge_color": "info",
                            }
                        )

            # Developer documentation
            developers_path = Path("docs/developers")
            if developers_path.exists():
                dev_sections = [
                    ("architecture", "Architecture", "bi-diagram-2"),
                    ("testing", "Testing", "bi-check-circle"),
                    ("deployment", "Deployment", "bi-cloud-upload"),
                    ("extending", "Extending", "bi-puzzle"),
                    ("documentation", "Documentation", "bi-file-text"),
                ]

                for section_dir, section_title, icon in dev_sections:
                    section_path = developers_path / section_dir
                    if section_path.exists() and any(section_path.glob("*.md")):
                        docs_structure["developer_docs"].append(
                            {
                                "url": f"developers/{section_dir}/",
                                "title": section_title,
                                "icon": icon,
                                "badge": "Dev",
                                "badge_color": "dark",
                            }
                        )

        # Generate HTML content
        html_content = self._generate_docs_cards_html(docs_structure)
        return html_content

    def _generate_docs_cards_html(self, docs_structure: dict) -> str:
        """Generate HTML cards for documentation sections."""

        def generate_card(title, color, icon, items, card_id=""):
            if not items:
                return ""

            items_html = ""
            for item in items:
                items_html += f"""
                            <li class="list-group-item d-flex justify-content-between align-items-center">
                                <a href="{item['url']}" class="text-decoration-none">
                                    <i class="{item['icon']} me-2 text-{color}"></i>{item['title']}
                                </a>
                                <span class="badge bg-{item['badge_color']} rounded-pill">{item['badge']}</span>
                            </li>"""

            return f"""
            <div class="col-lg-6">
                <div class="card h-100 border-0 shadow">
                    <div class="card-header bg-{color} text-white">
                        <h4 class="mb-0">
                            <i class="{icon} me-2"></i>{title}
                        </h4>
                    </div>
                    <div class="card-body">
                        <ul class="list-group list-group-flush">{items_html}
                        </ul>
                    </div>
                </div>
            </div>"""

        # Generate cards for each section
        cards_html = ""

        # Getting Started (combine main docs and getting started guides)
        getting_started_items = (
            docs_structure["release_info"] + docs_structure["getting_started"]
        )
        cards_html += generate_card(
            "Getting Started", "primary", "bi-play-circle", getting_started_items
        )

        # Packages
        if docs_structure["packages"]:
            cards_html += generate_card(
                "Packages", "info", "bi-box", docs_structure["packages"]
            )

        # User Guides
        if docs_structure["user_guides"]:
            cards_html += generate_card(
                "User Guides",
                "success",
                "bi-person-check",
                docs_structure["user_guides"],
            )

        # Developer Documentation
        if docs_structure["developer_docs"]:
            cards_html += generate_card(
                "Development", "dark", "bi-code-slash", docs_structure["developer_docs"]
            )

        # Wrap in the main structure
        full_html = f"""
<!-- Documentation Header -->
<section class="py-5 bg-light">
    <div class="container">
        <div class="row justify-content-center text-center">
            <div class="col-lg-8">
                <h1 class="display-4 fw-bold text-primary">
                    <i class="bi bi-book me-3"></i>Documentation
                </h1>
                <p class="lead text-muted">
                    Comprehensive documentation for QDrant Loader and MCP Server
                </p>
            </div>
        </div>
    </div>
</section>

<!-- Documentation Grid -->
<section class="py-5">
    <div class="container">
        <div class="row g-4">
{cards_html}
        </div>
    </div>
</section>

<!-- Quick Actions -->
<section class="py-5 bg-light">
    <div class="container">
        <div class="row justify-content-center">
            <div class="col-lg-8 text-center">
                <h3 class="mb-4">Quick Actions</h3>
                <div class="d-flex justify-content-center gap-3 flex-wrap">
                    <a href="../coverage/" class="btn btn-outline-primary">
                        <i class="bi bi-graph-up me-2"></i>View Coverage Reports
                    </a>
                    <a href="https://github.com/martin-papy/qdrant-loader" class="btn btn-outline-secondary"
                        target="_blank">
                        <i class="bi bi-github me-2"></i>GitHub Repository
                    </a>
                    <a href="https://pypi.org/project/qdrant-loader/" class="btn btn-outline-info" target="_blank">
                        <i class="bi bi-box me-2"></i>QDrant Loader PyPI
                    </a>
                    <a href="https://pypi.org/project/qdrant-loader-mcp-server/" class="btn btn-outline-info"
                        target="_blank">
                        <i class="bi bi-plug me-2"></i>MCP Server PyPI
                    </a>
                </div>
            </div>
        </div>
    </div>
</section>"""

        return full_html

    def build_site(
        self,
        coverage_artifacts_dir: str | None = None,
        test_results_dir: str | None = None,
    ) -> None:
        """Build the complete website."""
        print("🏗️  Building QDrant Loader website...")

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Copy assets first
        self.copy_assets()

        # Generate project info
        self.generate_project_info()

        # Build main pages
        self.build_page(
            "base.html",
            "index.html",
            "Home",
            "Enterprise-ready vector database toolkit for building searchable knowledge bases from multiple data sources including Confluence, Jira, and local files.",
            "index.html",
        )

        # Build dynamic documentation index
        dynamic_docs_content = self.generate_dynamic_docs_index()

        # Build docs index page with dynamic content
        base_template = self.load_template("base.html")

        # Calculate canonical URL
        if self.base_url.startswith("http"):
            canonical_url = self.base_url.rstrip("/") + "/docs/"
        else:
            canonical_url = "/docs/"

        # Get version from project info if available
        version = "0.4.0b1"  # Default version
        try:
            import tomli

            with open("pyproject.toml", "rb") as f:
                pyproject = tomli.load(f)
                version = pyproject.get("project", {}).get("version", version)
        except:
            pass

        # Set base_url to '../' for docs/index.html (one level deep)
        docs_index_base_url = "../" if not self.base_url else self.base_url

        replacements = {
            "page_title": "Documentation",
            "page_description": "Comprehensive documentation for QDrant Loader - learn how to load data into Qdrant vector database from various sources.",
            "content": dynamic_docs_content,
            "base_url": docs_index_base_url,
            "canonical_url": canonical_url,
            "version": version,
            "additional_head": "",
            "additional_scripts": "",
        }

        final_content = self.replace_placeholders(base_template, replacements)

        # Write docs index file
        docs_index_path = self.output_dir / "docs" / "index.html"
        docs_index_path.parent.mkdir(parents=True, exist_ok=True)

        with open(docs_index_path, "w", encoding="utf-8") as f:
            f.write(final_content)

        print("✅ Built: docs/index.html (dynamic)")

        self.build_page(
            "base.html",
            "coverage-index.html",
            "Test Coverage",
            "Test coverage analysis and reports for QDrant Loader packages - ensuring code quality and reliability.",
            "coverage/index.html",
        )

        # Build privacy policy page
        from datetime import datetime

        last_updated = datetime.now().strftime("%B %d, %Y")

        self.build_page(
            "base.html",
            "privacy-policy.html",
            "Privacy Policy",
            "Privacy policy for QDrant Loader website - learn how we collect, use, and protect your information when you visit our documentation and use our services.",
            "privacy-policy.html",
            additional_replacements={"last_updated": last_updated},
        )

        # Build documentation structure (converts MD to HTML)
        self.build_docs_structure()

        # Generate directory index pages to prevent directory listings
        self.generate_directory_indexes()

        # Build coverage structure
        self.build_coverage_structure(coverage_artifacts_dir)

        # Copy test results if available
        if test_results_dir and Path(test_results_dir).exists():
            dest_path = self.output_dir / "test-results"
            if dest_path.exists():
                shutil.rmtree(dest_path)
            shutil.copytree(test_results_dir, dest_path)
            print("📊 Copied: test results")

        # Generate SEO files after all pages are built
        self.generate_seo_files()

        print(f"✅ Website built successfully in {self.output_dir}")
        print(f"📊 Generated {len(list(self.output_dir.rglob('*.html')))} HTML pages")
        print(f"📁 Total files: {len(list(self.output_dir.rglob('*')))}")

    def generate_directory_indexes(self) -> None:
        """Generate index.html files from README.html files to prevent directory listings."""

        # Find all README.html files in the docs directory
        docs_path = self.output_dir / "docs"
        if not docs_path.exists():
            return

        readme_files = list(docs_path.rglob("README.html"))

        for readme_file in readme_files:
            # Skip the main docs/README.html since docs/index.html is custom-built
            if readme_file.parent == docs_path:
                print("⏭️  Skipping main docs/README.html (custom index exists)")
                continue

            # Create index.html in the same directory as README.html
            index_file = readme_file.parent / "index.html"

            # Copy README.html content to index.html
            try:
                with open(readme_file, encoding="utf-8") as f:
                    content = f.read()

                with open(index_file, "w", encoding="utf-8") as f:
                    f.write(content)

                print(
                    f"📄 Generated index.html: {index_file.relative_to(self.output_dir)}"
                )

            except Exception as e:
                print(f"⚠️  Failed to generate index for {readme_file}: {e}")


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
