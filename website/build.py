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
        # Cached docs navigation data (built once per run)
        self.docs_nav_data: dict | None = None

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
                    "toc",
                    "tables",
                    "fenced_code",
                    "attr_list",
                    "def_list",
                    "footnotes",
                    "md_in_html",
                    "admonition",
                    "pymdownx.superfences",
                    "pymdownx.details",
                    "pymdownx.tabbed",
                    "pymdownx.emoji",
                    "pymdownx.tasklist",
                ],
                extension_configs={
                    "toc": {
                        "permalink": False,
                        "permalink_class": "text-decoration-none",
                        "permalink_title": "Link to this section",
                    },
                    "pymdownx.emoji": {
                        "emoji_generator": "pymdownx.emoji.to_alt",
                    },
                    "pymdownx.tasklist": {
                        "custom_checkbox": True
                    }
                },
            )

            html_content = md.convert(markdown_content)

            # Add Bootstrap classes to common elements
            html_content = self.add_bootstrap_classes(html_content)

            # Convert markdown links to HTML
            html_content = self.convert_markdown_links_to_html(
                html_content, source_file, output_file
            )

            # Ensure headings have id attributes for TOC/ScrollSpy
            html_content = self.ensure_heading_ids(html_content)

            return html_content

        except ImportError:
            print("⚠️  Markdown library not available, falling back to basic conversion")
            # Avoid importing any modules here because tests may mock __import__ globally
            # Use only built-ins and our own helper methods
            html_content = self.basic_markdown_to_html(markdown_content)
            # Ensure links to markdown files are mapped to their HTML counterparts
            html_content = self.convert_markdown_links_to_html(
                html_content, source_file, output_file
            )
            # Add heading ids and Bootstrap classes for consistent UX
            html_content = self.ensure_heading_ids(html_content)
            html_content = self.add_bootstrap_classes(html_content)
            return html_content

    def ensure_heading_ids(self, html_content: str) -> str:
        """Add id attributes to h2/h3 headings if missing, based on their text content."""

        def slugify(text: str) -> str:
            text = re.sub(r"<[^>]+>", "", text)  # strip HTML
            text = text.strip().lower()
            text = re.sub(r"[^a-z0-9\s_-]", "", text)
            text = re.sub(r"\s+", "-", text)
            text = re.sub(r"-+", "-", text)
            return text or "section"

        def add_id(match: re.Match) -> str:
            tag = match.group(1)
            attrs = match.group(2) or ""
            inner = match.group(3)
            # If already has id, return unchanged
            if re.search(r"\bid=\"[^\"]+\"", attrs):
                return match.group(0)
            anchor_id = slugify(inner)
            # Insert id as the first attribute
            attrs_with_id = f' id="{anchor_id}"' + (" " + attrs.strip() if attrs.strip() else "")
            return f"<{tag}{attrs_with_id}>{inner}</{tag}>"

        pattern = re.compile(r"<(h[23])(\s[^>]*)?>([\s\S]*?)</h[23]>", re.IGNORECASE)
        return pattern.sub(add_id, html_content)

    # --------------------
    # Git metadata and prev/next helpers
    # --------------------
    def get_git_timestamp(self, source_path: str) -> str:
        """Return last commit date for a file, fallback to file mtime (ISO)."""
        from datetime import datetime
        import subprocess
        try:
            ts = (
                subprocess.check_output(
                    ["git", "log", "-1", "--format=%cd", "--date=iso", source_path]
                )
                .decode()
                .strip()
            )
            if ts:
                return ts
        except Exception:
            pass
        try:
            mtime = Path(source_path).stat().st_mtime
            return datetime.fromtimestamp(mtime).isoformat()
        except Exception:
            return "unknown"

    def get_prev_next_links(self, markdown_file: str) -> tuple[dict | None, dict | None]:
        """Compute previous and next links within the same directory, using frontmatter nav_order then filename."""
        md_path = Path(markdown_file)
        parent = md_path.parent
        if not parent.exists() or not md_path.exists():
            return None, None

        def read_frontmatter_order(path: Path) -> tuple[int | None, str]:
            # Return (nav_order, title)
            try:
                import frontmatter  # type: ignore
                post = frontmatter.load(str(path))
                nav_order = post.get("nav_order", None)
                title = self.extract_title_from_markdown(post.content or "")
                return (int(nav_order) if nav_order is not None else None, title)
            except Exception:
                try:
                    with open(path, encoding="utf-8") as f:
                        content = f.read()
                    return (None, self.extract_title_from_markdown(content))
                except Exception:
                    return (None, path.stem.replace("-", " ").replace("_", " ").title())

        # Gather siblings
        siblings = [p for p in sorted(parent.glob("*.md"))]
        items: list[tuple[Path, int | None, str]] = []
        for p in siblings:
            nav_order, title = read_frontmatter_order(p)
            items.append((p, nav_order, title))

        # Sort by (nav_order present first), nav_order, then title then filename
        def sort_key(t: tuple[Path, int | None, str]):
            p, order, title = t
            return (order is None, order if order is not None else 0, title.lower(), p.name.lower())

        items.sort(key=sort_key)

        # Find current index
        try:
            idx = [p for p, _, _ in items].index(md_path)
        except ValueError:
            return None, None

        def to_link(p: Path, title: str) -> dict:
            # Map markdown path to output URL under docs/
            try:
                rel = p.relative_to(Path("docs"))
                url = f"docs/{rel.with_suffix('.html').as_posix()}"
            except Exception:
                if p.name == "README.md":
                    url = "docs/README.html"
                else:
                    # Fallback: map to docs/ + path
                    url = f"docs/{p.with_suffix('.html').as_posix()}"
            return {"url": url, "title": title}

        prev_link = None
        next_link = None
        if idx > 0:
            p, _, t = items[idx - 1]
            prev_link = to_link(p, t)
        if idx < len(items) - 1:
            p, _, t = items[idx + 1]
            next_link = to_link(p, t)

        return prev_link, next_link

    # --------------------
    # Docs Navigation (left sidebar)
    # --------------------
    def _humanize_title(self, name: str) -> str:
        """Convert file or directory names to human readable titles."""
        # Remove extension if present
        name = name.rsplit(".", 1)[0]
        # Special case README
        if name.lower() == "readme":
            return "Overview"
        name = name.replace("-", " ").replace("_", " ")
        return name.title()

    def _build_nav_tree(self, root_dir: Path) -> dict:
        """Build a nested navigation tree from the docs directory."""
        tree: dict = {"title": "Documentation", "url": "index.html", "children": []}

        if not root_dir.exists():
            return tree

        # Collect all markdown files
        md_files = sorted(root_dir.rglob("*.md"))

        # Build a mapping from directory to children
        dir_to_node: dict[Path, dict] = {root_dir: tree}

        for md_path in md_files:
            rel_md = md_path.relative_to(root_dir)
            parts = list(rel_md.parts)

            # Determine parent directory and file title
            parent_dir = root_dir
            parent_node = tree

            # Walk directories, create nodes as needed
            for i, part in enumerate(parts[:-1]):
                parent_dir = parent_dir / part
                if parent_dir not in dir_to_node:
                    node = {
                        "title": self._humanize_title(part),
                        "url": f"{parent_dir.relative_to(root_dir).as_posix()}/",
                        "children": [],
                    }
                    # Attach to current parent_node's children
                    parent_node.setdefault("children", []).append(node)
                    dir_to_node[parent_dir] = node
                parent_node = dir_to_node[parent_dir]

            # File node
            file_name = parts[-1]
            title = self._humanize_title(file_name)
            rel_html = rel_md.with_suffix(".html").as_posix()
            file_node = {"title": title, "url": rel_html, "children": []}

            # Attach to parent
            parent_node["children"].append(file_node)

        # Deduplicate and sort children by title
        def sort_children(node: dict):
            if "children" in node and node["children"]:
                node["children"].sort(key=lambda n: ("children" not in n or not n["children"], n["title"].lower()))
                for child in node["children"]:
                    sort_children(child)

        sort_children(tree)
        return tree

    def render_docs_nav_html(self, nav_data: dict, active_url: str, link_prefix: str = "") -> str:
        """Render the left sidebar navigation HTML.

        - active_url: path relative to docs/ root (e.g. "users/config.html")
        - link_prefix: prefix to prepend to every href so links resolve from the current page
          e.g. for a page under docs/users/x.html, use "../../docs/" so that hrefs
          like "getting-started.html" point to the correct docs root.
        """

        def render_node(node: dict, depth: int = 0) -> str:
            children = node.get("children", [])
            url = node.get("url", "")
            title = node.get("title", "")
            is_section = bool(children)
            is_active = active_url == url
            is_parent_of_active = active_url.startswith(url) if is_section and url.endswith("/") else False
            active_class = " active" if is_active else (" open" if is_parent_of_active else "")

            if is_section:
                items_html = "".join(render_node(child, depth + 1) for child in children)
                return (
                    f'<li class="nav-item docs-nav-section depth-{depth}{active_class}">'  # section
                    f'<a href="{link_prefix}{url}" class="nav-link section-link">{title}</a>'
                    f'<ul class="nav flex-column ms-2">{items_html}</ul>'
                    f"</li>"
                )
            else:
                return (
                    f'<li class="nav-item depth-{depth}">'  # file
                    f'<a href="{link_prefix}{url}" class="nav-link{active_class}">{title}</a>'
                    f"</li>"
                )

        # Skip the root wrapper when rendering; render its children
        children = nav_data.get("children", [])
        items_html = "".join(render_node(child, 0) for child in children)
        html = f"""
<nav class=\"docs-sidebar\" aria-label=\"Documentation navigation\">
  <div class=\"docs-sidebar-inner\">
    <h6 class=\"text-uppercase text-muted small mb-3\">Documentation</h6>
    <ul class=\"nav flex-column\">
      {items_html}
    </ul>
  </div>
</nav>
"""
        return html

    def build_docs_nav(self) -> dict:
        """Build docs nav data, cache it, and write site/docs/_nav.json."""
        docs_root = Path("docs")
        nav_data = self._build_nav_tree(docs_root)
        self.docs_nav_data = nav_data

        # Ensure output/docs exists
        docs_output = self.output_dir / "docs"
        docs_output.mkdir(parents=True, exist_ok=True)

        # Write JSON for client-side consumption (future search/UX)
        try:
            nav_json_path = docs_output / "_nav.json"
            with open(nav_json_path, "w", encoding="utf-8") as f:
                json.dump(nav_data, f, indent=2)
            print(f"📄 Generated: {nav_json_path.relative_to(self.output_dir)}")
        except Exception as e:
            print(f"⚠️  Failed to write docs/_nav.json: {e}")

        return nav_data

    # --------------------
    # In-page TOC (right sidebar)
    # --------------------
    def render_toc(self, html_content: str) -> str:
        """Render 'On this page' TOC from h2/h3 headings in the HTML content."""
        import re

        # Find h2 and h3 with ids
        heading_pattern = re.compile(r"<h([23])([^>]*)>(.*?)</h[23]>", re.IGNORECASE | re.DOTALL)
        id_pattern = re.compile(r'id="([^"]+)"')

        items: list[tuple[int, str, str]] = []  # (level, id, text)
        for match in heading_pattern.finditer(html_content):
            level = int(match.group(1))
            attrs = match.group(2)
            text = re.sub(r"<[^>]+>", "", match.group(3)).strip()
            m = id_pattern.search(attrs)
            if not m:
                # No id, skip (Bootstrap ScrollSpy requires anchors)
                continue
            anchor_id = m.group(1)
            items.append((level, anchor_id, text))

        if not items:
            return ""

        # Build nested list: h2 as top-level, h3 nested
        toc_html = [
            '<nav id="on-this-page" class="docs-toc" aria-label="On this page">',
            '<div class="docs-toc-inner">',
            '<h6 class="text-uppercase text-muted small mb-3">On this page</h6>',
            '<ul class="nav flex-column small">',
        ]

        open_sub = False
        for i, (level, anchor_id, text) in enumerate(items):
            if level == 2:
                if open_sub:
                    toc_html.append("</ul></li>")
                    open_sub = False
                toc_html.append(
                    f'<li class="nav-item"><a class="nav-link" href="#{anchor_id}">{text}</a>'
                )
                # Lookahead to see if next is h3
                if i + 1 < len(items) and items[i + 1][0] == 3:
                    toc_html.append('<ul class="nav flex-column ms-2">')
                    open_sub = True
                else:
                    toc_html.append("</li>")
            else:  # h3
                if not open_sub:
                    toc_html.append('<ul class="nav flex-column ms-2">')
                    open_sub = True
                toc_html.append(
                    f'<li class="nav-item"><a class="nav-link" href="#{anchor_id}">{text}</a></li>'
                )

        if open_sub:
            toc_html.append("</ul></li>")

        toc_html.extend(["</ul>", "</div>", "</nav>"])
        return "\n".join(toc_html)

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

        # Normalize links that mistakenly prefix with "docs/" when already under docs/
        # Many pages link like href="docs/section/page.html" which, when resolved from
        # a docs subpage, creates duplicated paths. Rewrite to be relative to docs root.
        try:
            if output_file.startswith("docs/"):
                rel_parts = Path(output_file).relative_to("docs").parts
                # Depth below docs root (exclude filename)
                depth_to_docs_root = max(len(rel_parts) - 1, 0)
                prefix_to_docs_root = "" if depth_to_docs_root == 0 else "../" * depth_to_docs_root
                # Replace href="docs/..." with a link relative to docs root
                html_content = re.sub(
                    r'href="docs/([^"]+)"',
                    lambda m: f'href="{prefix_to_docs_root}{m.group(1)}"',
                    html_content,
                )
                # Replace href="/docs/..." with the same relative link
                html_content = re.sub(
                    r'href="/docs/([^"]+)"',
                    lambda m: f'href="{prefix_to_docs_root}{m.group(1)}"',
                    html_content,
                )
        except Exception:
            # Best-effort normalization; ignore on failure
            pass

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

        # Prepare left navigation and right TOC for docs pages
        active_url_rel = output_file.replace("docs/", "", 1) if output_file.startswith("docs/") else output_file
        if self.docs_nav_data is None:
            # Build once if not available yet
            self.build_docs_nav()
        # Placeholder; will compute nav_link_prefix after page_base_url is known
        left_nav_html = ""
        right_toc_html = ""

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

        # Determine link prefix so sidebar and prev/next links resolve correctly from this page
        if output_file.startswith("docs/"):
            rel_parts = Path(output_file).relative_to("docs").parts
            subdirs_depth = max(len(rel_parts) - 1, 0)
            if self.base_url:
                nav_link_prefix = f"{page_base_url}docs/"
            else:
                nav_link_prefix = ("../" * subdirs_depth) if subdirs_depth > 0 else ""
        else:
            nav_link_prefix = ""

        left_nav_html = self.render_docs_nav_html(self.docs_nav_data or {}, active_url_rel, nav_link_prefix)
        right_toc_html = self.render_toc(html_content)

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

        # Compute prev/next and last updated
        prev_link, next_link = self.get_prev_next_links(markdown_file)
        last_updated = self.get_git_timestamp(markdown_file)
        # Compute edit and feedback links
        repo_base = "https://github.com/martin-papy/qdrant-loader/blob/main/"
        source_rel = str(Path(markdown_file))
        edit_url = repo_base + source_rel
        try:
            from urllib.parse import quote
            feedback_title = quote(f"Docs feedback: {page_title}")
            feedback_body = quote(f"Page: /{output_file}\n\nFeedback:")
        except Exception:
            feedback_title = f"Docs%20feedback%3A%20{page_title}"
            feedback_body = f"Page%3A%20%2F{output_file}%0A%0AFeedback%3A"
        feedback_url = (
            "https://github.com/martin-papy/qdrant-loader/issues/new?labels=docs&title="
            + feedback_title
            + "&body="
            + feedback_body
        )

        # Helper to adjust doc-root URLs (starting with "docs/") to be resolvable from current page
        def adjust_doc_href(url: str) -> str:
            if url.startswith("docs/"):
                return f"{nav_link_prefix}{url[len('docs/'):]}"
            if url.startswith("/docs/"):
                return f"{nav_link_prefix}{url[len('/docs/') :]}"
            return url

        # Create the documentation content template with sidebars
        doc_content = f"""
        <section class="py-5">
            <div class="container">
                <div class="row">
                    <aside class="col-lg-3 d-none d-md-block">
                        <div class="position-sticky" style="top: 80px;">{left_nav_html}</div>
                    </aside>

                    <div class="col-lg-7 col-md-12">
                        {breadcrumb_html}
                        <div id="doc-content" data-bs-spy="scroll" data-bs-target="#on-this-page" data-bs-offset="100" tabindex="0">
                        <div class="card border-0 shadow">
                            <div class="card-body p-5">
                                {html_content}
                            </div>
                        </div>

                        <!-- Navigation footer -->
                            <div class="d-flex justify-content-between align-items-center mt-4 flex-wrap gap-2">
                                <div class="d-flex align-items-center gap-2">
                            <a href="{docs_url}" class="btn btn-outline-primary">
                                <i class="bi bi-arrow-left me-2"></i>Back to Documentation
                            </a>
                                    {f'<a class="btn btn-outline-secondary" href="{adjust_doc_href(prev_link["url"]) }"><i class="bi bi-arrow-left-circle me-2"></i>Prev: {prev_link["title"]}</a>' if prev_link else ''}
                                    {f'<a class="btn btn-outline-secondary" href="{adjust_doc_href(next_link["url"]) }">Next: {next_link["title"]} <i class="bi bi-arrow-right-circle ms-2"></i></a>' if next_link else ''}
                            </div>
                                <div class="d-flex align-items-center gap-2">
                                    <a href="{edit_url}" target="_blank" class="btn btn-sm btn-outline-dark">
                                        <i class="bi bi-pencil-square me-1"></i>Edit this page
                                    </a>
                                    <a href="{feedback_url}" target="_blank" class="btn btn-sm btn-outline-info">
                                        <i class="bi bi-chat-dots me-1"></i>Was this helpful?
                                    </a>
                                    <span class="text-muted small"><i class="bi bi-clock ms-2 me-1"></i>Last updated: {last_updated}</span>
                        </div>
                    </div>
                    </div>
                    </div>

                    <aside class="col-lg-2 d-none d-xl-block">
                        <div class="position-sticky" style="top: 80px;">{right_toc_html}</div>
                    </aside>
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

        # Include docs.css on docs pages and initialize ScrollSpy
        additional_head = """
            <link rel="stylesheet" href="{base_url}assets/css/docs.css">
        """.replace("{base_url}", page_base_url)

        additional_scripts = """
            <script>
                document.addEventListener('DOMContentLoaded', function() {
                    if (window.bootstrap) {
                        var el = document.querySelector('#doc-content');
                        if (el) new bootstrap.ScrollSpy(el, { target: '#on-this-page', offset: 100 });
                    }
                });
            </script>
        """

        # On docs pages, include client-side search, mermaid (if used), and code UX scripts
        search_script_tag = f"<script src=\"{page_base_url}assets/js/search.js\"></script>"
        codeux_script_tag = f"<script src=\"{page_base_url}assets/js/codeux.js\"></script>"
        mermaid_tags = """
            <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js" integrity="" crossorigin="anonymous"></script>
            <script src="{base_url}assets/js/mermaid-init.js"></script>
        """.replace("{base_url}", page_base_url)

        replacements = {
            "page_title": page_title,
            "page_description": page_description,
            "content": doc_content,
            "base_url": page_base_url,
            "canonical_url": canonical_url,
            "version": version,
            "additional_head": additional_head,
            "additional_scripts": additional_scripts + "\n" + search_script_tag + "\n" + codeux_script_tag + "\n" + mermaid_tags,
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

        # Generate 404.html using base template if template exists
        try:
            base_template = self.load_template("base.html")
            content_404 = self.load_template("404.html")

            replacements = {
                "page_title": "Not Found",
                "page_description": "The requested page could not be found.",
                "content": content_404,
                "base_url": self.base_url or "",
                "canonical_url": "/404.html",
                "version": "",
                "additional_head": "",
                "additional_scripts": "",
            }
            final_404 = self.replace_placeholders(base_template, replacements)
            with open(self.output_dir / "404.html", "w", encoding="utf-8") as f:
                f.write(final_404)
            print("📄 Generated: 404.html")
        except FileNotFoundError:
            print("⏭️  Skipping 404.html generation (template missing)")

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

    def generate_search_index(self) -> None:
        """Generate docs/search-index.json for client-side search.

        Each entry contains: url, title, headings, content, tags.
        """
        docs_root = Path("docs")
        search_entries: list[dict] = []

        def read_file_text(path: Path) -> str:
            try:
                with open(path, encoding="utf-8") as f:
                    return f.read()
            except Exception:
                return ""

        def extract_headings(markdown_text: str) -> list[str]:
            import re
            headings: list[str] = []
            for line in markdown_text.splitlines():
                if line.startswith("## ") and not line.startswith("### "):
                    headings.append(line[3:].strip())
                elif line.startswith("### "):
                    headings.append(line[4:].strip())
            return headings

        def strip_markdown(md: str) -> str:
            import re
            # Remove fenced code blocks
            md = re.sub(r"```[\s\S]*?```", " ", md)
            # Remove inline code
            md = re.sub(r"`[^`]+`", " ", md)
            # Remove images
            md = re.sub(r"!\[[^\]]*\]\([^\)]+\)", " ", md)
            # Replace links with their text
            md = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", md)
            # Remove headings markers
            md = re.sub(r"^#{1,6}\s*", "", md, flags=re.MULTILINE)
            # Remove HTML tags
            md = re.sub(r"<[^>]+>", " ", md)
            # Collapse whitespace
            md = re.sub(r"\s+", " ", md).strip()
            return md

        def add_md_file(md_path: Path, base_prefix: str = "docs/") -> None:
            markdown_text = read_file_text(md_path)
            if not markdown_text:
                return
            title = self.extract_title_from_markdown(markdown_text)
            headings = extract_headings(markdown_text)
            content = strip_markdown(markdown_text)
            rel_html = (md_path.relative_to(docs_root) if md_path.is_relative_to(docs_root) else md_path).with_suffix(".html")
            if not str(rel_html).startswith("docs/"):
                url = base_prefix + rel_html.as_posix()
            else:
                url = rel_html.as_posix()
            # Normalize url to be relative to output root
            if not url.startswith("docs/"):
                url = f"docs/{rel_html.as_posix()}"
            tags = []
            try:
                rel_parts = md_path.relative_to(docs_root).parts
                tags = list(rel_parts[:-1])
            except Exception:
                # Not under docs/ - categorize as root
                pass
            entry = {
                "url": url,
                "title": title,
                "headings": headings,
                "content": content,
                "tags": tags,
            }
            search_entries.append(entry)

        # Include docs/ markdown files
        if docs_root.exists():
            for md_file in docs_root.rglob("*.md"):
                add_md_file(md_file)

        # Include main markdown files that are rendered under docs/
        main_docs = [
            Path("README.md"),
            Path("RELEASE_NOTES.md"),
            Path("CONTRIBUTING.md"),
        ]
        for md in main_docs:
            if md.exists():
                add_md_file(md)

        # Write JSON
        docs_output = self.output_dir / "docs"
        docs_output.mkdir(parents=True, exist_ok=True)
        out_path = docs_output / "search-index.json"
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(search_entries, f, ensure_ascii=False, separators=(",", ":"))
            print(f"📄 Generated: {out_path.relative_to(self.output_dir)} ({len(search_entries)} docs)")
        except Exception as e:
            print(f"⚠️  Failed to write search-index.json: {e}")

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

        # Prebuild docs navigation (left sidebar) and write docs/_nav.json
        self.build_docs_nav()

        # Build dynamic documentation index content
        dynamic_docs_content = self.generate_dynamic_docs_index()

        # Build docs index page with dynamic content and left sidebar
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

        # Render left nav for docs index
        left_nav_html = self.render_docs_nav_html(self.docs_nav_data or {}, "index.html")
        right_toc_html = ""  # No TOC on index page

        docs_index_content = f"""
        <section class=\"py-5\">
            <div class=\"container\">
                <div class=\"row\"> 
                    <aside class=\"col-lg-3 d-none d-md-block\">
                        <div class=\"position-sticky\" style=\"top: 80px;\">{left_nav_html}</div>
                    </aside>
                    <div class=\"col-lg-7 col-md-12\">{dynamic_docs_content}</div>
                    <aside class=\"col-lg-2 d-none d-xl-block\">
                        <div class=\"position-sticky\" style=\"top: 80px;\">{right_toc_html}</div>
                    </aside>
                </div>
            </div>
        </section>
        """

        replacements = {
            "page_title": "Documentation",
            "page_description": "Comprehensive documentation for QDrant Loader - learn how to load data into Qdrant vector database from various sources.",
            "content": docs_index_content,
            "base_url": docs_index_base_url,
            "canonical_url": canonical_url,
            "version": version,
            "additional_head": f"<link rel=\"stylesheet\" href=\"{docs_index_base_url}assets/css/docs.css\">",
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

        # Generate search index for client-side search (docs only)
        self.generate_search_index()

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
