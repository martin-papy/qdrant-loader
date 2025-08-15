"""
Markdown Processing - Markdown-to-HTML Conversion.

This module handles markdown processing, HTML conversion,
and content formatting for the website builder.
"""

import re
import subprocess
from pathlib import Path


class MarkdownProcessor:
    """Handles markdown processing and HTML conversion."""

    def markdown_to_html(
        self, markdown_content: str, source_file: str = "", output_file: str = ""
    ) -> str:
        """Convert markdown to HTML with Bootstrap styling."""
        try:
            import markdown

            md = markdown.Markdown(
                extensions=[
                    "fenced_code", 
                    "codehilite",
                    "tables",
                    "toc",
                    "attr_list",
                    "def_list",
                    "footnotes",
                    "md_in_html",
                    "sane_lists",
                ]
            )
            html = md.convert(markdown_content)
            
            # Add Bootstrap classes
            html = self.add_bootstrap_classes(html)
            
            # Ensure heading IDs
            html = self.ensure_heading_ids(html)
            
            return html
            
        except ImportError:
            # Fallback to basic conversion
            html = self._basic_markdown_to_html_no_regex(markdown_content)
            # Apply Bootstrap classes to fallback HTML too
            html = self.add_bootstrap_classes(html)
            # Ensure heading IDs
            html = self.ensure_heading_ids(html)
            return html

    def _basic_markdown_to_html_no_regex(self, markdown_content: str) -> str:
        """Basic markdown to HTML conversion without regex."""
        lines = markdown_content.split('\n')
        html_lines = []
        in_code_block = False
        
        for line in lines:
            if line.startswith('```'):
                if in_code_block:
                    html_lines.append('</code></pre>')
                    in_code_block = False
                else:
                    html_lines.append('<pre><code>')
                    in_code_block = True
            elif in_code_block:
                html_lines.append(line)
            elif line.startswith('# '):
                html_lines.append(f'<h1>{line[2:]}</h1>')
            elif line.startswith('## '):
                html_lines.append(f'<h2>{line[3:]}</h2>')
            elif line.startswith('### '):
                html_lines.append(f'<h3>{line[4:]}</h3>')
            elif line.startswith('- '):
                html_lines.append(f'<li>{line[2:]}</li>')
            elif line.strip():
                html_lines.append(f'<p>{line}</p>')
            else:
                html_lines.append('')
        
        return '\n'.join(html_lines)

    def ensure_heading_ids(self, html_content: str) -> str:
        """Ensure all headings have IDs for anchor links."""
        def slugify(text: str) -> str:
            """Convert text to URL-safe slug."""
            import re
            slug = re.sub(r'[^\w\s-]', '', text.lower())
            return re.sub(r'[-\s]+', '-', slug).strip('-')

        def add_id(match: re.Match) -> str:
            """Add ID to heading if not present."""
            tag = match.group(1)
            attrs = match.group(2) or ""
            content = match.group(3)
            
            if 'id=' not in attrs:
                heading_id = slugify(content)
                if attrs:
                    attrs = f' id="{heading_id}" {attrs.strip()}'
                else:
                    attrs = f' id="{heading_id}"'
            
            return f'<{tag}{attrs}>{content}</{tag}>'

        # Add IDs to headings that don't have them
        heading_pattern = r'<(h[1-6])([^>]*)>([^<]+)</h[1-6]>'
        return re.sub(heading_pattern, add_id, html_content)

    def add_bootstrap_classes(self, html_content: str) -> str:
        """Add Bootstrap classes to HTML elements."""
        
        # Add Bootstrap header classes
        html_content = re.sub(
            r'<h1([^>]*)>',
            r'<h1\1 class="display-4 fw-bold text-primary mb-4">',
            html_content
        )
        html_content = re.sub(
            r'<h2([^>]*)>',
            r'<h2\1 class="h2 fw-bold text-primary mt-5 mb-3">',
            html_content
        )
        html_content = re.sub(
            r'<h3([^>]*)>',
            r'<h3\1 class="h3 fw-bold text-primary mt-5 mb-3">',
            html_content
        )
        html_content = re.sub(
            r'<h4([^>]*)>',
            r'<h4\1 class="h4 fw-bold mt-4 mb-3">',
            html_content
        )
        html_content = re.sub(
            r'<h5([^>]*)>',
            r'<h5\1 class="h5 fw-bold mt-3 mb-2">',
            html_content
        )
        html_content = re.sub(
            r'<h6([^>]*)>',
            r'<h6\1 class="h6 fw-semibold mt-2 mb-1">',
            html_content
        )
        
        # Add Bootstrap code block classes  
        html_content = re.sub(
            r'<div class="codehilite">',
            '<div class="bg-dark text-light p-3 rounded">',
            html_content
        )
        html_content = re.sub(
            r'<pre>',
            '<pre class="bg-dark text-light p-3 rounded">',
            html_content
        )
        # Add Bootstrap inline code classes
        html_content = re.sub(
            r'<code>',
            '<code class="bg-light text-dark px-2 py-1 rounded">',
            html_content
        )
        
        # Add Bootstrap link classes
        html_content = re.sub(
            r'<a([^>]*?)href="([^"]*)"([^>]*?)>',
            r'<a\1href="\2"\3 class="text-decoration-none">',
            html_content
        )
        
        # Add Bootstrap list classes
        html_content = re.sub(
            r'<ul>',
            '<ul class="list-group list-group-flush">',
            html_content
        )
        html_content = re.sub(
            r'<ol>',
            '<ol class="list-group list-group-numbered">',
            html_content
        )
        html_content = re.sub(
            r'<li>',
            '<li class="list-group-item">',
            html_content
        )

        # Add Bootstrap table classes
        html_content = re.sub(
            r'<table>',
            '<table class="table table-striped table-hover">',
            html_content
        )
        
        # Add Bootstrap alert classes for blockquotes  
        html_content = re.sub(
            r'<blockquote>',
            '<blockquote class="alert alert-info">',
            html_content
        )
        
        # Add Bootstrap button classes to links that look like buttons
        html_content = re.sub(
            r'<a([^>]*?)class="[^"]*btn[^"]*"([^>]*?)>',
            r'<a\1class="btn btn-primary"\2>',
            html_content
        )
        
        return html_content

    def extract_title_from_markdown(self, markdown_content: str) -> str:
        """Extract title from markdown content."""
        lines = markdown_content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('# '):
                return line[2:].strip()
        return "Documentation"  # Default fallback title

    def basic_markdown_to_html(self, markdown_content: str) -> str:
        """Basic markdown to HTML conversion - alias for compatibility."""
        return self.markdown_to_html(markdown_content)

    def convert_markdown_links_to_html(self, content: str, source_dir: str = "", target_dir: str = "") -> str:
        """Convert markdown links to HTML format."""
        
        # Convert [text](link.md) to [text](link.html) - markdown style
        def replace_md_links(match):
            text = match.group(1)
            link = match.group(2)
            link = self._process_link_path(link)
            return f'[{text}]({link})'
        
        # Convert href="link.md" to href="link.html" - HTML style
        def replace_href_links(match):
            prefix = match.group(1)
            link = match.group(2)
            suffix = match.group(3)
            link = self._process_link_path(link)
            return f'{prefix}{link}{suffix}'
        
        # Apply conversions - expanded patterns to catch more file types
        # Catch .md files and well-known files without extensions
        content = re.sub(r'\[([^\]]+)\]\(([^)]+\.md)\)', replace_md_links, content)
        content = re.sub(r'\[([^\]]+)\]\(([^)]*(?:LICENSE|README|CHANGELOG|CONTRIBUTING)(?:/[^)]*)?)\)', replace_md_links, content)
        content = re.sub(r'(href=")([^"]+\.md)(")', replace_href_links, content)
        content = re.sub(r'(href=")([^"]*(?:LICENSE|README|CHANGELOG|CONTRIBUTING)(?:/[^"]*)?)(\")', replace_href_links, content)
        
        return content
    
    def _process_link_path(self, link: str) -> str:
        """Process a link path for conversion."""
        # Convert .md to .html
        if link.endswith('.md'):
            link = link[:-3] + '.html'
        else:
            # Handle well-known files without extensions
            filename = link.split('/')[-1]
            if filename.upper() in ['LICENSE', 'README', 'CHANGELOG', 'CONTRIBUTING']:
                if '.' not in filename:
                    link = link + '.html'
        
        # Remove redundant docs/ in relative paths when we're already in a docs context
        # This handles cases like ../../docs/guide.md -> ../../guide.html
        if '/docs/' in link and link.count('../') >= 1:
            # Check if this is a relative path going up and then into docs
            parts = link.split('/docs/', 1)
            if len(parts) == 2 and parts[0].endswith('..'):
                # Remove the docs/ part since we're already in docs context
                link = parts[0] + '/' + parts[1]
        
        return link

    def render_toc(self, html_content: str) -> str:
        """Generate table of contents from HTML headings."""
        
        # Find all headings
        heading_pattern = r'<(h[1-6])[^>]*id="([^"]+)"[^>]*>([^<]+)</h[1-6]>'
        headings = re.findall(heading_pattern, html_content)
        
        if not headings:
            return ""
        
        toc_html = '<div class="toc"><h3>Table of Contents</h3><ul>'
        for tag, heading_id, text in headings:
            level = int(tag[1])  # Extract number from h1, h2, etc.
            indent = "  " * (level - 1)
            toc_html += f'{indent}<li><a href="#{heading_id}">{text}</a></li>\n'
        toc_html += '</ul></div>'
        
        return toc_html
