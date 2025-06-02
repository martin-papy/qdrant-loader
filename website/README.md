# QDrant Loader Documentation Website

This directory contains the documentation website generator for QDrant Loader. It automatically converts markdown documentation into a professional, responsive website using Bootstrap templates.

## 🏗️ Architecture

The website generator is a Python-based static site generator that:

- **Converts markdown to HTML** using Python-Markdown with extensions
- **Applies Bootstrap templates** for professional styling and responsive design
- **Generates navigation** automatically from directory structure
- **Processes assets** including favicons, logos, and icons
- **Creates sitemaps and robots.txt** for SEO optimization
- **Supports code coverage reports** integration

## 📁 Directory Structure

```text
website/
├── build.py                    # Main build script
├── templates/                  # Jinja2 HTML templates
│   ├── base.html              # Base template with Bootstrap
│   ├── index.html             # Homepage template
│   ├── docs-index.html        # Documentation index
│   ├── coverage-index.html    # Coverage reports index
│   ├── privacy-policy.html    # Privacy policy page
│   ├── robots.txt             # SEO robots file
│   └── sitemap.xml            # SEO sitemap template
├── assets/                     # Website assets
│   ├── favicons/              # Favicon files (all sizes)
│   ├── icons/                 # SVG icons
│   ├── logos/                 # Project logos and social cards
│   ├── site.webmanifest       # PWA manifest
│   └── generate_favicons.py   # Favicon generation script
└── README.md                  # This file
```

## 🚀 Building the Website

### Prerequisites

```bash
# Install dependencies (from project root)
pip install -e packages/qdrant-loader[dev]
pip install -e packages/qdrant-loader-mcp-server[dev]

# Required Python packages for website generation
pip install markdown jinja2 python-frontmatter
```

### Build Commands

```bash
# Build the complete website
cd website
python build.py

# Build with custom output directory
python build.py --output ../dist

# Build with custom templates directory
python build.py --templates ./custom-templates

# Build with coverage artifacts integration
python build.py --coverage-artifacts ../coverage-html

# Build with test results integration
python build.py --test-results ../test-results

# Build with custom base URL
python build.py --base-url https://qdrant-loader.net
```

### Build Process

1. **Source Processing**: Reads markdown files from the documentation directory
2. **Frontmatter Parsing**: Extracts metadata from markdown frontmatter
3. **Markdown Conversion**: Converts markdown to HTML with syntax highlighting
4. **Template Application**: Applies appropriate Jinja2 templates
5. **Asset Copying**: Copies all assets (images, favicons, etc.)
6. **Navigation Generation**: Creates automatic navigation from directory structure
7. **SEO Generation**: Creates sitemap.xml and robots.txt
8. **Output Writing**: Writes final HTML files to output directory

## 🎨 Templates

### Base Template (`base.html`)

The base template provides:

- **Bootstrap 5** for responsive design and components
- **Syntax highlighting** with Prism.js for code blocks
- **Responsive navigation** with automatic menu generation
- **SEO meta tags** including Open Graph and Twitter Cards
- **Favicon integration** with all required sizes
- **Google Analytics** support (configurable)

### Specialized Templates

- **`index.html`**: Homepage with project overview and quick links
- **`docs-index.html`**: Documentation index with section navigation
- **`coverage-index.html`**: Test coverage reports integration
- **`privacy-policy.html`**: Privacy policy page

### Template Variables

Templates have access to:

- `content`: Rendered markdown content
- `title`: Page title from frontmatter or filename
- `description`: Page description from frontmatter
- `navigation`: Auto-generated navigation structure
- `breadcrumbs`: Current page breadcrumb path
- `assets_url`: Base URL for assets

## 🎯 Assets Management

### Favicons

The website includes comprehensive favicon support:

```text
assets/favicons/
├── favicon.ico              # Classic ICO format
├── favicon-16x16.png        # Small browser tab
├── favicon-32x32.png        # Standard browser tab
├── favicon-48x48.png        # Windows taskbar
├── favicon-64x64.png        # High-DPI browser tab
├── favicon-96x96.png        # Android Chrome
├── favicon-128x128.png      # Chrome Web Store
├── apple-touch-icon.png     # iOS home screen (180x180)
├── android-chrome-192x192.png # Android home screen
└── android-chrome-512x512.png # Android splash screen
```

### Logos and Icons

- **`qdrant-loader-logo.svg`**: Main project logo
- **`qdrant-loader-logo-horizontal.svg`**: Horizontal layout logo
- **`qdrant-loader-icon.svg`**: Animated icon
- **`qdrant-loader-icon-static.svg`**: Static icon
- **`qdrant-loader-social-card.png`**: Social media sharing image

### Generating New Favicons

```bash
cd website/assets
python generate_favicons.py

# This script generates all favicon sizes from the main logo
# Requires Pillow (PIL) for image processing
```

## 🔧 Configuration

### Environment Variables

```bash
# Optional: Google Analytics tracking ID
export GA_TRACKING_ID="G-XXXXXXXXXX"

# Optional: Base URL for absolute links
export SITE_BASE_URL="https://qdrant-loader.net"
```

### Frontmatter Options

Markdown files can include frontmatter for metadata:

```yaml
---
title: "Custom Page Title"
description: "Page description for SEO"
template: "custom-template.html"  # Optional custom template
nav_order: 10                    # Optional navigation ordering
hide_nav: true                   # Optional: hide from navigation
---

# Your markdown content here
```

## 🚀 Development Workflow

### Local Development

```bash
# Build and serve locally (requires a simple HTTP server)
cd website
python build.py --output ../dist
cd ../dist
python -m http.server 8000

# Open http://localhost:8000 in your browser
```

### Adding New Pages

1. **Create markdown file** in the appropriate documentation directory
2. **Add frontmatter** if needed for custom title or description
3. **Rebuild website** with `python build.py`
4. **Test locally** to ensure proper rendering and navigation

### Modifying Templates

1. **Edit template files** in `website/templates/`
2. **Test changes** by rebuilding the website
3. **Ensure responsive design** works across devices
4. **Validate HTML** and check for accessibility

### Adding New Assets

1. **Add files** to appropriate `website/assets/` subdirectory
2. **Update templates** if needed to reference new assets
3. **Rebuild website** to copy assets to output
4. **Test asset loading** in the generated website

## 📊 Integration Features

### Test Coverage Reports

The website can integrate test coverage reports:

```bash
# Generate coverage reports (from project root)
pytest --cov=packages --cov-report=html --cov-report-dir=website/coverage

# Build website with coverage integration
cd website
python build.py --coverage-artifacts ../coverage-html
```

### Documentation Versioning

The build system supports multiple documentation versions:

```bash
# Build specific documentation version
python build.py --output ../dist/v1
python build.py --output ../dist/v2
```

## 🔍 SEO and Performance

### SEO Features

- **Semantic HTML** with proper heading hierarchy
- **Meta descriptions** from frontmatter or auto-generated
- **Open Graph tags** for social media sharing
- **Twitter Card tags** for Twitter sharing
- **Structured data** for search engines
- **Sitemap.xml** generation
- **Robots.txt** configuration

### Performance Optimizations

- **Minified CSS and JS** in production builds
- **Optimized images** with appropriate formats and sizes
- **Lazy loading** for images and non-critical resources
- **CDN-ready assets** with proper caching headers
- **Progressive Web App** features with manifest

## 🤝 Contributing

### Adding New Features

1. **Modify `build.py`** for new build functionality
2. **Update templates** for new UI features
3. **Add assets** as needed
4. **Test thoroughly** across different browsers and devices
5. **Update this README** with new features

### Template Guidelines

- **Use Bootstrap classes** for consistent styling
- **Ensure responsive design** with mobile-first approach
- **Include proper accessibility** attributes
- **Follow semantic HTML** structure
- **Test with various content** lengths and types

### Asset Guidelines

- **Optimize images** for web delivery
- **Use SVG** for icons and logos when possible
- **Provide multiple sizes** for raster images
- **Include alt text** and descriptions
- **Test loading performance** on slow connections

---

**Need help?** Check the [main documentation](../docs/) or open an [issue](https://github.com/martin-papy/qdrant-loader/issues) for website-specific questions.
