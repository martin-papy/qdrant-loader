# QDrant Loader Website Templates

This directory contains the template system for building the QDrant Loader documentation website. The templates use Bootstrap 5 for a modern, professional appearance and support dynamic content replacement with **automatic markdown to HTML conversion**.

## 🏗️ Architecture

### Template Structure

```
website/
├── templates/
│   ├── base.html           # Base template with navigation, footer, and layout
│   ├── index.html          # Homepage content template
│   ├── docs-index.html     # Documentation index template
│   └── coverage-index.html # Coverage reports index template
├── build.py               # Python builder script with markdown conversion
└── README.md             # This file
```

### Template System

The website uses a **template inheritance** system with **automatic markdown conversion**:

1. **Base Template** (`base.html`): Contains the common layout, navigation, footer, and Bootstrap framework
2. **Content Templates**: Contain page-specific content that gets injected into the base template
3. **Markdown Conversion**: Automatically converts all `.md` files to beautiful HTML pages with Bootstrap styling
4. **Builder Script**: Processes templates, converts markdown, and replaces placeholders with dynamic content

## 🎨 Design Features

### Modern UI Framework

- **Bootstrap 5.3.2**: Latest stable version with modern components
- **Bootstrap Icons**: Comprehensive icon library
- **Responsive Design**: Mobile-first approach with breakpoints
- **Professional Color Scheme**: Custom CSS variables for consistent branding

### Markdown to HTML Conversion

- **Full Markdown Support**: Headers, lists, tables, code blocks, links, images
- **Syntax Highlighting**: Code blocks with highlight.js and GitHub theme
- **Bootstrap Styling**: Automatic application of Bootstrap classes to all elements
- **Table of Contents**: Automatic generation with anchor links
- **Breadcrumb Navigation**: Contextual navigation for all documentation pages
- **Professional Typography**: Consistent heading hierarchy and spacing

### Key Design Elements

- **Gradient Hero Sections**: Eye-catching headers with gradient backgrounds
- **Card-based Layout**: Clean, organized content presentation with shadows
- **Hover Effects**: Interactive elements with smooth transitions
- **Status Indicators**: Real-time test status and coverage information
- **Professional Typography**: System fonts with proper hierarchy
- **Code Highlighting**: Syntax-highlighted code blocks with dark theme

## 🔧 Usage

### Building the Website

#### Basic Usage

```bash
python website/build.py
```

#### Advanced Usage

```bash
python website/build.py \
  --output site \
  --templates website/templates \
  --coverage-artifacts coverage-artifacts/ \
  --test-results test-results/ \
  --base-url "https://martin-papy.github.io/qdrant-loader/"
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--output`, `-o` | Output directory for built website | `site` |
| `--templates`, `-t` | Templates directory | `website/templates` |
| `--coverage-artifacts` | Coverage artifacts directory | None |
| `--test-results` | Test results directory | None |
| `--base-url` | Base URL for the website | `""` |

## 📝 Template Placeholders

### Base Template Placeholders

| Placeholder | Description | Example |
|-------------|-------------|---------|
| `{{ page_title }}` | Page title for `<title>` tag | "Home" |
| `{{ page_description }}` | Meta description | "Enterprise-ready toolkit" |
| `{{ content }}` | Main page content | Content from content templates |
| `{{ base_url }}` | Base URL for links | `""` or `"https://..."` |
| `{{ additional_head }}` | Extra head content | Custom CSS/JS |
| `{{ additional_scripts }}` | Extra scripts | Page-specific JavaScript |

### Dynamic Content

The builder automatically generates:

- **Project Information**: Version, commit info, build timestamp
- **Test Status**: Real-time test results and coverage data
- **Documentation Structure**: Organized docs with proper linking
- **Coverage Reports**: Interactive coverage analysis
- **Markdown Conversion**: All `.md` files converted to styled HTML pages

## 📄 Markdown Conversion Features

### Automatic Conversion

The builder automatically converts all markdown files to HTML with:

- **Bootstrap Classes**: Automatically applied to all HTML elements
- **Syntax Highlighting**: Code blocks with highlight.js
- **Responsive Tables**: Bootstrap table styling with horizontal scrolling
- **Professional Typography**: Consistent heading hierarchy and spacing
- **Navigation Elements**: Breadcrumbs and back-to-docs links

### Supported Markdown Features

| Feature | Bootstrap Styling | Example |
|---------|------------------|---------|
| Headers | `display-4`, `h3`, `h4` classes with primary color | `# Title` → Large primary header |
| Paragraphs | `mb-3` spacing | Consistent paragraph spacing |
| Lists | `list-group` styling | Clean, modern list appearance |
| Tables | `table-responsive`, `table-striped` | Professional data tables |
| Code Blocks | `bg-dark`, syntax highlighting | Dark theme with language detection |
| Inline Code | `bg-light` badges | Subtle inline code styling |
| Links | `text-decoration-none`, external link detection | Clean links with target handling |
| Blockquotes | `blockquote` with primary border | Styled quote blocks |

### Enhanced Features

- **Table of Contents**: Automatic generation with anchor links
- **Breadcrumb Navigation**: Contextual navigation for all pages
- **External Link Detection**: Automatic `target="_blank"` for external URLs
- **Image Handling**: Responsive image styling
- **Code Language Detection**: Automatic syntax highlighting based on language

## 🎯 Customization

### Adding New Pages

1. **Create Content Template**:

   ```html
   <!-- website/templates/my-page.html -->
   <section class="py-5">
       <div class="container">
           <h1>My Custom Page</h1>
           <p>Custom content here...</p>
       </div>
   </section>
   ```

2. **Update Builder Script**:

   ```python
   # In build_all method
   self.build_page(
       "base.html", "my-page.html",
       "My Page", "Description of my page",
       "my-page/index.html"
   )
   ```

### Adding Markdown Documentation

Simply add `.md` files to the `docs/` directory or package directories. The builder will automatically:

1. Convert them to HTML with Bootstrap styling
2. Add breadcrumb navigation
3. Include syntax highlighting
4. Generate proper page titles and descriptions
5. Create appropriate directory structure

### Customizing Styles

The base template includes CSS variables for easy customization:

```css
:root {
    --primary-color: #667eea;
    --secondary-color: #764ba2;
    --success-color: #48bb78;
    --danger-color: #f56565;
    --warning-color: #ed8936;
    --info-color: #4299e1;
}
```

### Adding Custom JavaScript

Use the `additional_scripts` placeholder:

```python
additional_replacements = {
    "additional_scripts": """
    <script>
        // Custom JavaScript here
        console.log('Custom script loaded');
    </script>
    """
}

self.build_page(
    "base.html", "content.html",
    "Title", "Description", "output.html",
    additional_replacements
)
```

## 🚀 Integration with GitHub Actions

The template system integrates seamlessly with the GitHub Actions workflow:

### Workflow Integration

```yaml
- name: Install dependencies
  run: |
    python -m pip install --upgrade pip
    pip install -e ".[docs]"

- name: Build website using templates
  run: |
    python website/build.py \
      --output site \
      --coverage-artifacts coverage-artifacts/ \
      --test-results test-results/
```

### Dynamic Data Sources

The website automatically integrates:

- **Test Results**: From `test-results/status.json`
- **Coverage Reports**: From `coverage-artifacts/htmlcov-*/`
- **Project Info**: From `pyproject.toml` and Git
- **Documentation**: From `docs/` and package READMEs (converted to HTML)
- **Markdown Files**: All `.md` files automatically converted to styled HTML

## 📊 Features

### Homepage

- Hero section with project overview
- Feature cards with hover effects
- Installation instructions
- Quick start guide

### Documentation Index

- Organized by categories
- Color-coded sections
- Badge indicators for content type
- Quick action buttons
- **Links to HTML versions** of all documentation

### Coverage Reports

- Real-time test status
- Coverage metrics display
- Interactive coverage reports
- Test run information

### Documentation Pages

- **Professional HTML conversion** from markdown
- **Syntax-highlighted code blocks**
- **Responsive Bootstrap styling**
- **Breadcrumb navigation**
- **Table of contents with anchor links**
- **Back-to-documentation navigation**

## 🔄 Benefits Over Embedded HTML

### Maintainability

- **Separation of Concerns**: Templates separate from workflow logic
- **Reusable Components**: Base template shared across pages
- **Easy Updates**: Change design without touching workflow files
- **Markdown Workflow**: Write docs in markdown, get professional HTML

### Professional Design

- **Bootstrap Framework**: Industry-standard UI components
- **Responsive Layout**: Works on all devices
- **Modern Aesthetics**: Professional appearance for enterprise use
- **Consistent Styling**: All documentation pages use the same design

### Flexibility

- **Dynamic Content**: Easy to add new data sources
- **Customizable**: Simple to modify design and layout
- **Extensible**: Easy to add new pages and features
- **Markdown Support**: Write documentation in markdown, get styled HTML

## 🛠️ Development

### Local Testing

```bash
# Build website locally
python website/build.py --output local-site

# Serve locally (requires Python 3)
cd local-site
python -m http.server 8000

# Open http://localhost:8000
```

### Template Development

1. Edit templates in `website/templates/`
2. Add markdown files to `docs/` or package directories
3. Test with local build
4. Commit changes
5. GitHub Actions will automatically deploy

### Dependencies

The builder requires these Python packages, which are defined in the `docs` optional dependencies in `pyproject.toml`:

- `tomli`: For reading pyproject.toml files
- `markdown`: For markdown to HTML conversion with extensions
- `pygments`: For syntax highlighting
- `cairosvg`: For favicon generation from SVG
- `pillow`: For image processing in favicon generation

Install with:

```bash
pip install -e ".[docs]"
```

This template system provides a professional, maintainable foundation for the QDrant Loader documentation website while keeping the GitHub Actions workflow clean and focused. The automatic markdown conversion ensures that all documentation maintains a consistent, professional appearance while allowing developers to write in familiar markdown format.
