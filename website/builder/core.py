"""
Core Website Builder - Main Orchestration and Lifecycle Management.

This module implements the main WebsiteBuilder class that orchestrates
all build operations and manages the overall build lifecycle.
"""

import argparse
import json
import os
import re
import subprocess
from pathlib import Path

from .templates import TemplateProcessor
from .markdown import MarkdownProcessor
from .assets import AssetManager


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
        
        # Initialize component processors
        self.template_processor = TemplateProcessor(templates_dir)
        self.markdown_processor = MarkdownProcessor()
        self.asset_manager = AssetManager(output_dir)

    # Delegate core operations to specialized processors
    def load_template(self, template_name: str) -> str:
        """Load a template file."""
        return self.template_processor.load_template(template_name)

    def replace_placeholders(self, content: str, replacements: dict[str, str]) -> str:
        """Replace placeholders in content with actual values."""
        return self.template_processor.replace_placeholders(content, replacements)

    def markdown_to_html(
        self, markdown_content: str, source_file: str = "", output_file: str = ""
    ) -> str:
        """Convert markdown to HTML with Bootstrap styling."""
        return self.markdown_processor.markdown_to_html(markdown_content, source_file, output_file)

    def copy_assets(self) -> None:
        """Copy all website assets to output directory."""
        return self.asset_manager.copy_assets()

    def extract_title_from_markdown(self, markdown_content: str) -> str:
        """Extract title from markdown content."""
        return self.markdown_processor.extract_title_from_markdown(markdown_content)

    # Additional markdown processing methods
    def basic_markdown_to_html(self, markdown_content: str) -> str:
        """Basic markdown to HTML conversion."""
        return self.markdown_processor.basic_markdown_to_html(markdown_content)

    def convert_markdown_links_to_html(self, markdown_content: str, source_dir: str = "", target_dir: str = "") -> str:
        """Convert markdown links to HTML format."""
        return self.markdown_processor.convert_markdown_links_to_html(markdown_content, source_dir, target_dir)

    def add_bootstrap_classes(self, html_content: str) -> str:
        """Add Bootstrap classes to HTML elements."""
        return self.markdown_processor.add_bootstrap_classes(html_content)

    def render_toc(self, html_content: str) -> str:
        """Generate table of contents from HTML headings."""
        return self.markdown_processor.render_toc(html_content)

    # Additional asset management methods
    def copy_static_files(self, static_files: list[str]) -> None:
        """Copy multiple static files."""
        return self.asset_manager.copy_static_files(static_files)

    def get_git_timestamp(self, source_path: str) -> str:
        """Get the last modified timestamp from Git."""
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%cd", "--date=iso-strict", source_path],
                capture_output=True,
                text=True,
                cwd=".",
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        return ""

    def _humanize_title(self, name: str) -> str:
        """Convert filename to human-readable title."""
        # Remove file extension and common prefixes
        title = name.replace('.md', '').replace('README', '').replace('_', ' ').replace('-', ' ')
        
        # Handle common patterns
        title_mappings = {
            'cli reference': 'CLI Reference',
            'api': 'API',
            'faq': 'FAQ',
            'toc': 'Table of Contents',
            'readme': 'Overview',
        }
        
        title_lower = title.lower().strip()
        if title_lower in title_mappings:
            return title_mappings[title_lower]
        
        # Capitalize words
        return ' '.join(word.capitalize() for word in title.split())

    def generate_project_info(self, **kwargs) -> dict:
        """Generate project information for templates."""
        project_info = {
            "name": "QDrant Loader",
            "version": "0.4.0b1",
            "description": "Enterprise-ready vector database toolkit",
            "github_url": "https://github.com/your-org/qdrant-loader",
        }
        
        # Override with any provided kwargs
        project_info.update(kwargs)
        
        # Try to load from pyproject.toml
        try:
            import tomli
            with open("pyproject.toml", "rb") as f:
                pyproject = tomli.load(f)
                project_section = pyproject.get("project", {})
                project_info.update({
                    "name": project_section.get("name", project_info["name"]),
                    "version": project_section.get("version", project_info["version"]),
                    "description": project_section.get("description", project_info["description"]),
                })
        except:
            pass
        
        # Try to get git information
        try:
            import subprocess
            
            # Get git commit hash
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"], 
                capture_output=True, 
                text=True, 
                check=True
            )
            project_info["commit_hash"] = result.stdout.strip()
            
            # Get git commit date
            result = subprocess.run(
                ["git", "log", "-1", "--format=%ci"], 
                capture_output=True, 
                text=True, 
                check=True
            )
            project_info["commit_date"] = result.stdout.strip()
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Git not available or not a git repository
            pass
        
        # Write project info JSON file
        project_info_path = self.output_dir / "project-info.json"
        project_info_path.parent.mkdir(parents=True, exist_ok=True)
        with open(project_info_path, 'w', encoding='utf-8') as f:
            json.dump(project_info, f, indent=2)
        
        return project_info

    def build_page(
        self,
        template_name: str,
        output_filename: str,
        title: str,
        description: str,
        canonical_path: str,
        content: str = "",
        **extra_replacements,
    ) -> None:
        """Build a single page from template."""
        template_content = self.load_template(template_name)
        
        project_info = self.generate_project_info()
        
        # Calculate base URL for relative paths
        if canonical_path.count('/') > 0:
            base_url = '../' * canonical_path.count('/')
        else:
            base_url = self.base_url or './'
            
        replacements = {
            'page_title': title,
            'page_description': description,
            'content': content,
            'base_url': base_url,
            'canonical_url': self.base_url.rstrip('/') + '/' + canonical_path if self.base_url else canonical_path,
            'author': project_info.get('name', 'QDrant Loader'),
            'version': project_info.get('version', '0.4.0b1'),
            'project_name': project_info['name'],
            'project_version': project_info['version'],
            'project_description': project_info['description'],
            **extra_replacements,
        }
        
        final_content = self.replace_placeholders(template_content, replacements)
        
        output_path = self.output_dir / output_filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
            
        print(f"📄 Built {output_filename}")

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

        # Build docs structure and pages
        self.build_docs_nav()
        docs_structure = self.build_docs_structure()
        
        # Create docs directory and index
        docs_output_dir = self.output_dir / "docs"
        docs_output_dir.mkdir(exist_ok=True)
        
        # Build docs index page
        self.build_page(
            "base.html",
            "docs/index.html", 
            "Documentation",
            "QDrant Loader Documentation",
            "docs/index.html",
            content="<h1>Documentation</h1><p>Welcome to the QDrant Loader documentation.</p>"
        )

        # Always create coverage directory and ensure index.html exists
        coverage_output_dir = self.output_dir / "coverage"
        coverage_output_dir.mkdir(exist_ok=True)
        
        # Build coverage reports if provided
        if coverage_artifacts_dir:
            coverage_structure = self.build_coverage_structure(coverage_artifacts_dir)
            
            # Copy coverage artifacts
            coverage_path = Path(coverage_artifacts_dir)
            if coverage_path.exists():
                import shutil
                for item in coverage_path.iterdir():
                    if item.is_file():
                        shutil.copy2(item, coverage_output_dir / item.name)
                    elif item.is_dir():
                        shutil.copytree(item, coverage_output_dir / item.name, dirs_exist_ok=True)
        else:
            # Create placeholder coverage index if no artifacts provided
            placeholder_index = coverage_output_dir / "index.html"
            if not placeholder_index.exists():
                placeholder_content = """<html>
<head><title>Coverage Reports</title></head>
<body>
    <h1>Coverage Reports</h1>
    <p>No coverage artifacts available.</p>
</body>
</html>"""
                placeholder_index.write_text(placeholder_content)
                print("📄 Generated placeholder coverage index.html")

        # Generate directory indexes
        self.generate_directory_indexes()

        # Generate SEO files
        self.generate_seo_files()

        # Create .nojekyll file for GitHub Pages
        nojekyll_path = self.output_dir / ".nojekyll"
        nojekyll_path.touch()
        print("📄 Created .nojekyll file")

        print("✅ Website build completed successfully!")

    def build_docs_nav(self) -> dict:
        """Build documentation navigation structure."""
        # Simplified navigation building
        docs_dir = Path("docs")
        if not docs_dir.exists():
            return {}
            
        nav_data = {"title": "Documentation", "children": []}
        
        for item in sorted(docs_dir.iterdir()):
            if item.is_file() and item.suffix == '.md':
                nav_data["children"].append({
                    "title": self._humanize_title(item.stem),
                    "url": f"docs/{item.name}",
                })
            elif item.is_dir():
                nav_data["children"].append({
                    "title": self._humanize_title(item.name),
                    "url": f"docs/{item.name}/",
                })
        
        self.docs_nav_data = nav_data
        return nav_data

    def generate_seo_files(self) -> None:
        """Generate SEO files like sitemap.xml and robots.txt."""
        from datetime import datetime
        
        # Get current date for lastmod
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Generate simple sitemap.xml
        sitemap_content = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>{base_url}/</loc>
    <lastmod>{date}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>{base_url}/docs/</loc>
    <lastmod>{date}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>
</urlset>'''.format(
            base_url=self.base_url.rstrip('/') if self.base_url else 'https://example.com',
            date=current_date
        )

        sitemap_path = self.output_dir / "sitemap.xml"
        with open(sitemap_path, 'w', encoding='utf-8') as f:
            f.write(sitemap_content)
        print(f"📄 Generated sitemap.xml")

        # Generate simple robots.txt
        robots_content = f'''User-agent: *
Allow: /

Sitemap: {self.base_url.rstrip('/') if self.base_url else 'https://example.com'}/sitemap.xml
'''

        robots_path = self.output_dir / "robots.txt"
        with open(robots_path, 'w', encoding='utf-8') as f:
            f.write(robots_content)
        print(f"📄 Generated robots.txt")

    def generate_dynamic_sitemap(self, date: str = None, pages: list[str] = None) -> str:
        """Generate dynamic sitemap with custom pages."""
        from datetime import datetime
        
        base_url = self.base_url.rstrip('/') if self.base_url else 'https://example.com'
        
        # Auto-discover pages if not provided
        if pages is None:
            pages = []
            # Find HTML files in site directory
            if self.output_dir.exists():
                for html_file in self.output_dir.rglob("*.html"):
                    rel_path = str(html_file.relative_to(self.output_dir))
                    pages.append(rel_path)
        
        # Use provided date or current date
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        sitemap_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
        sitemap_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        
        for page in pages:
            sitemap_content += f'  <url>\n'
            sitemap_content += f'    <loc>{base_url}/{page}</loc>\n'
            sitemap_content += f'    <lastmod>{date}</lastmod>\n'
            sitemap_content += f'    <changefreq>weekly</changefreq>\n'
            sitemap_content += f'    <priority>0.8</priority>\n'
            sitemap_content += f'  </url>\n'
        
        sitemap_content += '</urlset>'
        
        # Write sitemap to file
        sitemap_path = self.output_dir / "sitemap.xml"
        sitemap_path.parent.mkdir(parents=True, exist_ok=True)
        with open(sitemap_path, 'w', encoding='utf-8') as f:
            f.write(sitemap_content)
        print(f"📄 Generated dynamic sitemap.xml with {len(pages)} pages")
        
        return sitemap_content

    def build_markdown_page(
        self, 
        markdown_file: str, 
        output_path: str, 
        title: str = "", 
        breadcrumb: str = "",
        **kwargs
    ) -> None:
        """Build a page from markdown file."""
        markdown_path = Path(markdown_file)
        if not markdown_path.exists():
            print(f"⚠️  Markdown file not found: {markdown_file}, skipping page generation")
            return
        
        try:
            with open(markdown_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()
        except Exception as e:
            print(f"⚠️  Failed to read markdown file {markdown_file}: {e}")
            return
        
        # Extract title if not provided
        if not title:
            title = self.extract_title_from_markdown(markdown_content)
        
        # Convert markdown to HTML
        html_content = self.markdown_to_html(markdown_content)
        
        # Build the page
        self.build_page(
            "base.html",
            output_path,
            title,
            f"{title} - QDrant Loader",
            output_path,
            content=html_content,
            breadcrumb=breadcrumb,
            **kwargs
        )

    def build_docs_structure(self) -> dict:
        """Build documentation directory structure."""
        docs_dir = Path("docs")
        structure = {"title": "Documentation", "children": []}
        
        # Create docs output directory
        docs_output_dir = self.output_dir / "docs"
        docs_output_dir.mkdir(parents=True, exist_ok=True)
        
        if not docs_dir.exists():
            return structure
        
        # Process all markdown files in docs
        for item in sorted(docs_dir.rglob("*.md")):
            relative_path = str(item.relative_to(docs_dir))
            output_path = relative_path.replace('.md', '.html')
            
            structure["children"].append({
                "title": self._humanize_title(item.stem),
                "path": relative_path,
                "url": f"docs/{output_path}",
            })
            
            # Build the page from markdown
            try:
                self.build_markdown_page(
                    str(item),
                    f"docs/{output_path}",
                    title=self._humanize_title(item.stem)
                )
            except Exception as e:
                print(f"⚠️  Failed to build docs page {item}: {e}")
        
        return structure

    def build_coverage_structure(self, coverage_dir: str | None = None) -> dict:
        """Build coverage report structure."""
        # Always create coverage output directory
        coverage_output_dir = self.output_dir / "coverage"
        coverage_output_dir.mkdir(parents=True, exist_ok=True)
        
        if not coverage_dir:
            return {"coverage_reports": []}
        
        coverage_path = Path(coverage_dir)
        if not coverage_path.exists():
            return {"coverage_reports": []}
        
        # Copy all coverage files with proper naming
        import shutil
        for item in coverage_path.iterdir():
            # Map directory names to cleaner package names
            dest_name = item.name
            if item.is_dir():
                if "htmlcov-loader" in item.name:
                    dest_name = "loader"
                elif "htmlcov-mcp" in item.name:
                    dest_name = "mcp"
                elif "htmlcov-website" in item.name:
                    dest_name = "website"
                elif "htmlcov" in item.name:
                    dest_name = item.name.replace("htmlcov-", "").replace("htmlcov_", "")
            
            dest_path = coverage_output_dir / dest_name
            try:
                if item.is_file():
                    shutil.copy2(item, dest_path)
                elif item.is_dir():
                    if dest_path.exists():
                        shutil.rmtree(dest_path)
                    shutil.copytree(item, dest_path)
                    print(f"📁 Copied coverage: {item.name} -> {dest_name}")
            except Exception as e:
                print(f"⚠️  Failed to copy coverage file {item}: {e}")
        
        # Build reports list using the renamed directories  
        reports = []
        for subdir in coverage_output_dir.iterdir():
            if subdir.is_dir():
                index_file = subdir / "index.html"
                if index_file.exists():
                    reports.append({
                        "name": subdir.name,
                        "path": f"{subdir.name}/index.html", 
                        "url": f"coverage/{subdir.name}/index.html",
                    })
        
        # Create main coverage index.html if it doesn't exist
        main_index = coverage_output_dir / "index.html"
        if not main_index.exists() and reports:
            # Create coverage index with proper structure
            index_content = """<html><head><title>Coverage Reports</title></head><body>
<section class="py-5">
    <div class="container">
        <h1>Coverage Reports</h1>
        <div class="row g-4">"""
            
            for report in reports:
                if report["name"] == "loader":
                    index_content += '''
            <div class="col-lg-6">
                <div class="card">
                    <div class="card-header">
                        <h4>QDrant Loader Core</h4>
                        <span id="loader-test-indicator" class="badge">Loading...</span>
                    </div>
                    <div class="card-body">
                        <div id="loader-coverage">Loader coverage data</div>
                        <a href="loader/" class="btn btn-primary">View Detailed Report</a>
                    </div>
                </div>
            </div>'''
                elif report["name"] == "mcp":
                    index_content += '''
            <div class="col-lg-6">
                <div class="card">
                    <div class="card-header">
                        <h4>MCP Server</h4>
                        <span id="mcp-test-indicator" class="badge">Loading...</span>
                    </div>
                    <div class="card-body">
                        <div id="mcp-coverage">MCP Server coverage data</div>
                        <a href="mcp/" class="btn btn-success">View Detailed Report</a>
                    </div>
                </div>
            </div>'''
                elif report["name"] == "website":
                    index_content += '''
            <div class="col-lg-6">
                <div class="card">
                    <div class="card-header">
                        <h4>Website</h4>
                        <span id="website-test-indicator" class="badge">Loading...</span>
                    </div>
                    <div class="card-body">
                        <div id="website-coverage">Website coverage data</div>
                        <a href="website/" class="btn btn-info">View Detailed Report</a>
                    </div>
                </div>
            </div>'''
            
            index_content += """
        </div>
    </div>
</section>

<script>
// Load coverage data for all three packages
fetch('loader/status.json').then(response => response.json()).then(data => {
    document.getElementById('loader-coverage').textContent = 'Loaded';
});

fetch('mcp/status.json').then(response => response.json()).then(data => {
    document.getElementById('mcp-coverage').textContent = 'Loaded';
});

fetch('website/status.json').then(response => response.json()).then(data => {
    document.getElementById('website-coverage').textContent = 'Loaded';
});
</script>
</body></html>"""
            main_index.write_text(index_content)
            print("📄 Generated coverage index.html")
        
        return {"coverage_reports": reports}

    def generate_directory_indexes(self) -> None:
        """Generate index files for directories."""
        # Look in both source docs and output site docs directories
        source_docs_dir = Path("docs")
        site_docs_dir = self.output_dir / "docs"
        
        # Process directories in both locations
        for docs_dir in [source_docs_dir, site_docs_dir]:
            if not docs_dir.exists():
                continue
            
            for directory in docs_dir.rglob("*"):
                if directory.is_dir():
                    # Look for README or index files in various formats
                    readme_md = directory / "README.md"
                    readme_html = directory / "README.html"
                    index_md = directory / "index.md"
                    index_html = directory / "index.html"
                    
                    # Determine source file
                    source_file = None
                    if readme_md.exists():
                        source_file = readme_md
                    elif index_md.exists():
                        source_file = index_md
                    elif readme_html.exists():
                        source_file = readme_html
                    elif index_html.exists():
                        source_file = index_html
                    
                    if source_file:
                        try:
                            if docs_dir == site_docs_dir:
                                # For files in site directory, create index.html directly there
                                index_file = directory / "index.html"
                                if source_file.suffix == '.html' and not index_file.exists():
                                    # Copy HTML file content directly
                                    content = source_file.read_text()
                                    index_file.write_text(content)
                                    print(f"📄 Generated index.html from {source_file.name}")
                            else:
                                # For source files, process through normal build pipeline
                                relative_dir = directory.relative_to(docs_dir)
                                output_path = f"docs/{relative_dir}/index.html"
                                
                                if source_file.suffix == '.html':
                                    # Copy HTML file content directly
                                    content = source_file.read_text()
                                    self.build_page(
                                        "base.html",
                                        output_path,
                                        self._humanize_title(directory.name),
                                        f"{self._humanize_title(directory.name)} Documentation",
                                        output_path,
                                        content=content
                                    )
                                else:
                                    # Process markdown file
                                    self.build_markdown_page(
                                        str(source_file),
                                        output_path,
                                        title=self._humanize_title(directory.name)
                                    )
                        except Exception as e:
                            print(f"⚠️  Failed to generate index for {directory}: {e}")

    def build_license_page(self, source_file: str = "LICENSE", output_file: str = "license.html", title: str = "License", description: str = "License") -> None:
        """Build license page from LICENSE file."""
        license_path = Path(source_file)
        if not license_path.exists():
            print(f"⚠️  License file not found: {source_file}, skipping license page")
            return
        
        try:
            with open(license_path, 'r', encoding='utf-8') as f:
                license_content = f.read()
            
            # Create license page with heading
            html_content = f"""
            <h1>License Information</h1>
            <div class="license-content">
                <pre>{license_content}</pre>
            </div>
            """
            
            self.build_page(
                "base.html",
                output_file,
                title,
                description,
                output_file,
                content=html_content
            )
        except Exception as e:
            print(f"⚠️  Failed to build license page: {e}")
