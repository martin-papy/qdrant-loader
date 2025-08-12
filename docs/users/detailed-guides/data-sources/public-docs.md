# Public Documentation

Connect QDrant Loader to public documentation websites, API references, and external knowledge sources. This guide covers setup for web scraping and processing publicly available content.

## 🎯 What Gets Processed

When you configure public documentation processing, QDrant Loader can handle:

- **API Documentation** - REST API docs, OpenAPI specs, SDK documentation
- **Technical Documentation** - Framework docs, library references, tutorials
- **Knowledge Bases** - Public wikis, help centers, support documentation
- **Blog Posts** - Technical blogs, release notes, announcements
- **Static Sites** - Documentation sites built with Jekyll, Hugo, GitBook
- **Versioned Documentation** - Specific versions of documentation

## 🔧 Setup and Configuration

QDrant Loader uses a **project-based configuration structure**. Each project can have multiple public documentation sources.

### Basic Configuration

```yaml
projects:
  my-project:
    display_name: "My Documentation Project"
    description: "External documentation and knowledge sources"
    collection_name: "my-docs"
    sources:
      publicdocs:
        example-docs:
          base_url: "https://docs.example.com"
          version: "1.0"
          content_type: "html"
          selectors:
            content: "article, main, .content"
            remove:
              - "nav"
              - "header"
              - "footer"
              - ".sidebar"
            code_blocks: "pre code"
          download_attachments: false
          enable_file_conversion: false
```

### Advanced Configuration

```yaml
projects:
  my-project:
    display_name: "My Documentation Project"
    description: "External documentation and knowledge sources"
    collection_name: "my-docs"
    sources:
      publicdocs:
        example-docs:
          base_url: "https://docs.example.com"
          version: "1.0"
          content_type: "html"
          
          # Path filtering
          path_pattern: "/docs/**"
          exclude_paths:
            - "/docs/archive/**"
            - "/docs/deprecated/**"
            - "/api/internal/**"
          
          # Content extraction selectors
          selectors:
            content: "article, main, .content"
            remove:
              - "nav"
              - "header"
              - "footer"
              - ".sidebar"
              - ".advertisement"
            code_blocks: "pre code, .highlight code"
          
          # Attachment handling
          download_attachments: true
          attachment_selectors:
            - "a[href$='.pdf']"
            - "a[href$='.doc']"
            - "a[href$='.docx']"
            - "a[href$='.xlsx']"
            - "a[href$='.pptx']"
          
          # File conversion
          enable_file_conversion: true
```

### Multiple Documentation Sites

```yaml
projects:
  multi-docs:
    display_name: "Multi-Documentation Project"
    description: "Documentation from multiple external sources"
    collection_name: "multi-docs"
    sources:
      publicdocs:
        # Main API documentation
        api-docs:
          base_url: "https://api.example.com/docs"
          version: "v2"
          content_type: "html"
          path_pattern: "/docs/**"
          selectors:
            content: ".api-content"
            remove:
              - ".sidebar"
              - ".navigation"
          download_attachments: false
          enable_file_conversion: false
        
        # Framework documentation
        framework-docs:
          base_url: "https://framework.example.com"
          version: "latest"
          content_type: "html"
          path_pattern: "/guide/**"
          selectors:
            content: ".documentation"
            remove:
              - ".menu"
              - ".footer"
          download_attachments: false
          enable_file_conversion: false
        
        # Community wiki
        community-wiki:
          base_url: "https://wiki.example.com"
          version: "current"
          content_type: "html"
          exclude_paths:
            - "/wiki/user:**"
            - "/wiki/talk:**"
          selectors:
            content: ".wiki-content"
            remove:
              - ".sidebar"
              - ".edit-section"
          download_attachments: false
          enable_file_conversion: false
```

## 🎯 Configuration Options

### Validator Requirements

- `content_type` allowed: `html`, `markdown`, or `rst`
- `download_attachments` default: `false`
- `attachment_selectors` have sensible defaults for common file types

### Required Settings

| Option | Type | Description | Example |
|--------|------|-------------|---------|
| `base_url` | string | Base URL to start crawling | `https://docs.example.com` |
| `version` | string | Version identifier for the documentation | `1.0` |

### Content Settings

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `content_type` | string | Content type: `html`, `markdown`, or `rst` | `html` |

### Path Filtering

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `path_pattern` | string | Specific path pattern to match | `null` (all paths) |
| `exclude_paths` | list | List of paths to exclude from processing | `[]` |

### Content Extraction

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `selectors.content` | string | Main content CSS selector | `article, main, .content` |
| `selectors.remove` | list | Elements to remove from content | `["nav", "header", "footer", ".sidebar"]` |
| `selectors.code_blocks` | string | Code blocks CSS selector | `pre code` |

### Attachment Processing

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `download_attachments` | bool | Download and process linked files | `false` |
| `attachment_selectors` | list | CSS selectors for finding attachments | PDF, DOC, XLS, PPT selectors |
| `enable_file_conversion` | bool | Enable file conversion for attachments | `false` |

## 🚀 Usage Examples

### API Documentation

```yaml
projects:
  api-documentation:
    display_name: "API Documentation"
    description: "External API documentation sources"
    collection_name: "api-docs"
    sources:
      publicdocs:
        # REST API Documentation
        stripe-api:
          base_url: "https://stripe.com/docs/api"
          version: "2023-10-16"
          content_type: "html"
          path_pattern: "/docs/api/**"
          selectors:
            content: ".api-content"
            remove:
              - ".sidebar"
              - ".navigation"
              - ".footer"
            code_blocks: "pre code, .highlight code"
          download_attachments: false
          enable_file_conversion: false
        
        # OpenAPI/Swagger Documentation
        petstore-api:
          base_url: "https://petstore.swagger.io"
          version: "v3"
          content_type: "html"
          path_pattern: "/v3/**"
          selectors:
            content: ".swagger-ui"
            remove:
              - ".topbar"
              - ".information-container"
          download_attachments: false
          enable_file_conversion: false
```

### Framework Documentation

```yaml
projects:
  frameworks:
    display_name: "Framework Documentation"
    description: "Documentation for development frameworks"
    collection_name: "framework-docs"
    sources:
      publicdocs:
        # React Documentation
        react-docs:
          base_url: "https://react.dev"
          version: "18"
          content_type: "html"
          path_pattern: "/learn/**"
          exclude_paths:
            - "/blog/**"
            - "/community/**"
          selectors:
            content: ".content"
            remove:
              - ".sidebar"
              - ".navigation"
          download_attachments: false
          enable_file_conversion: false
        
        # Django Documentation
        django-docs:
          base_url: "https://docs.djangoproject.com"
          version: "stable"
          content_type: "html"
          path_pattern: "/en/stable/**"
          selectors:
            content: ".document"
            remove:
              - ".sphinxsidebar"
              - ".related"
          download_attachments: false
          enable_file_conversion: false
```

### Knowledge Bases and Wikis

```yaml
projects:
  knowledge:
    display_name: "Knowledge Base"
    description: "External knowledge bases and wikis"
    collection_name: "knowledge-base"
    sources:
      publicdocs:
        # GitHub Wiki
        vscode-wiki:
          base_url: "https://github.com/microsoft/vscode/wiki"
          version: "current"
          content_type: "html"
          selectors:
            content: ".markdown-body"
            remove:
              - ".gh-header"
              - ".pagehead"
          download_attachments: false
          enable_file_conversion: false
        
        # GitBook Documentation
        gitbook-docs:
          base_url: "https://docs.gitbook.com"
          version: "latest"
          content_type: "html"
          path_pattern: "/product-tour/**"
          selectors:
            content: ".page-content"
            remove:
              - ".sidebar"
              - ".header"
          download_attachments: false
          enable_file_conversion: false
```

### Technical Blogs and Release Notes

```yaml
projects:
  technical-content:
    display_name: "Technical Content"
    description: "Technical blogs and release notes"
    collection_name: "tech-content"
    sources:
      publicdocs:
        # Engineering Blog
        engineering-blog:
          base_url: "https://engineering.example.com"
          version: "current"
          content_type: "html"
          path_pattern: "/posts/**"
          exclude_paths:
            - "/author/**"
            - "/tag/**"
          selectors:
            content: ".post-content"
            remove:
              - ".sidebar"
              - ".author-bio"
              - ".related-posts"
          download_attachments: false
          enable_file_conversion: false
        
        # Release Notes
        release-notes:
          base_url: "https://releases.example.com"
          version: "latest"
          content_type: "html"
          path_pattern: "/notes/**"
          selectors:
            content: ".release-content"
            remove:
              - ".navigation"
              - ".footer"
          download_attachments: false
          enable_file_conversion: false
```

## 🧪 Testing and Validation

### Initialize and Test Configuration

```bash
# Initialize the project (creates collection if needed)
qdrant-loader init --workspace .

# Test ingestion with your public docs configuration
qdrant-loader ingest --workspace . --project my-project

# Check project status
qdrant-loader project --workspace . --project-id my-project

# List all configured projects
qdrant-loader project --workspace .

# Validate project configuration
qdrant-loader project --workspace . --project-id my-project
```

### Debug Public Documentation Processing

```bash
# Enable debug logging
qdrant-loader ingest --workspace . --log-level DEBUG --project my-project

# Process specific project only
qdrant-loader ingest --workspace . --project my-project

# Process specific source within a project
qdrant-loader ingest --workspace . --project my-project --source-type publicdocs --source example-docs
```

## 🔧 Troubleshooting

### Common Issues

#### Access Denied or Blocked

**Problem**: `403 Forbidden`, `429 Too Many Requests`, or blocked by anti-bot measures

**Solutions**:

1. **Check robots.txt**: Ensure the site allows crawling
2. **Verify URL accessibility**: Test the base URL manually
3. **Check path patterns**: Ensure path_pattern matches actual site structure

```bash
# Test website accessibility
curl -I "https://docs.example.com"

# Check robots.txt
curl "https://docs.example.com/robots.txt"
```

#### Content Not Found

**Problem**: CSS selectors don't match content or pages appear empty

**Solutions**:

```bash
# Test CSS selectors manually
curl -s "https://example.com/page" | grep -A 10 -B 10 "class=\"content\""

# Use browser developer tools to find correct selectors
```

```yaml
projects:
  my-project:
    sources:
      publicdocs:
        example-docs:
          base_url: "https://example.com"
          version: "1.0"
          
          # Try multiple selectors
          selectors:
            content: "article, main, .content, .documentation, .md-content"
            remove:
              - "nav"
              - "header"
              - "footer"
              - ".sidebar"
              - ".menu"
```

#### Path Pattern Issues

**Problem**: No pages being processed due to incorrect path patterns

**Solutions**:

```yaml
projects:
  my-project:
    sources:
      publicdocs:
        example-docs:
          base_url: "https://docs.example.com"
          version: "1.0"
          
          # Use broader path pattern or remove it entirely
          path_pattern: "/**"  # Allow all paths
          
          # Or be more specific
          # path_pattern: "/docs/**"
          
          # Check exclude patterns
          exclude_paths:
            - "/docs/archive/**"
            - "/api/internal/**"
```

#### Configuration Issues

**Problem**: Configuration validation errors

**Solutions**:

1. **Verify project structure**:

```yaml
projects:
  your-project:  # Project ID
    sources:
      publicdocs:
        source-name:  # Source name
          base_url: "..."
          # ... other settings
```

1. **Check required fields**:
   - `base_url`: Must be a valid URL
   - `version`: Must be a non-empty string
   - `content_type`: Must be `html`, `markdown`, or `rst`

2. **Validate selectors**:

```yaml
selectors:
  content: "article, main, .content"  # Valid CSS selector
  remove:
    - "nav"
    - "header"
    - "footer"  # List of CSS selectors
  code_blocks: "pre code"  # Valid CSS selector
```

#### Attachment Processing Issues

**Problem**: Attachments not being downloaded or processed

**Solutions**:

```yaml
projects:
  my-project:
    sources:
      publicdocs:
        example-docs:
          base_url: "https://docs.example.com"
          version: "1.0"
          
          # Enable attachment processing
          download_attachments: true
          enable_file_conversion: true
          
          # Customize attachment selectors
          attachment_selectors:
            - "a[href$='.pdf']"
            - "a[href$='.doc']"
            - "a[href$='.docx']"
            - "a[href*='download']"
```

### Debugging Commands

```bash
# Check website structure
curl -s "https://example.com" | grep -E '<title>|<h1>|class="content"'

# Test specific page
curl -s "https://example.com/docs/page" | head -50

# Check for JavaScript requirements
curl -s "https://example.com" | grep -i javascript
```

## 📊 Monitoring and Processing

### Check Processing Status

```bash
# View project status
qdrant-loader project --workspace .

# Check specific project
qdrant-loader project --workspace . --project-id my-project

# List all projects
qdrant-loader project --workspace .
```

### Configuration Management

```bash
# View current configuration
qdrant-loader config --workspace .

# Validate all projects
qdrant-loader project --workspace .
```

## 🔄 Best Practices

### Site Selection

1. **Choose stable documentation sites** - Avoid frequently changing sites
2. **Verify site accessibility** - Ensure the site allows automated access
3. **Check content structure** - Verify consistent HTML structure
4. **Test CSS selectors** - Ensure selectors work across different pages

### Performance Optimization

1. **Use specific path patterns** - Limit crawling to relevant sections
2. **Optimize CSS selectors** - Use efficient selectors for content extraction
3. **Filter aggressively** - Exclude unnecessary paths and content
4. **Enable file conversion selectively** - Only when needed for attachments

### Content Quality

1. **Verify content extraction** - Check that selectors capture the right content
2. **Remove navigation elements** - Exclude menus, headers, and footers
3. **Handle code blocks properly** - Use appropriate selectors for code
4. **Test with sample pages** - Verify configuration with representative pages

### Security Considerations

1. **Respect robots.txt** - Follow site crawling guidelines
2. **Avoid overloading servers** - Use reasonable crawling rates
3. **Check terms of service** - Ensure compliance with site policies
4. **Monitor access patterns** - Track which content is being accessed

### Maintenance

1. **Monitor site changes** - Documentation sites may change structure
2. **Update selectors regularly** - Adjust selectors when sites are updated
3. **Version documentation appropriately** - Use meaningful version identifiers
4. **Regular validation** - Periodically check that processing still works

## 📚 Related Documentation

- **[Configuration Reference](../../configuration/)** - Complete configuration options
- **[File Conversion](../file-conversion/)** - Processing downloaded attachments
- **[Troubleshooting](../../troubleshooting/)** - Common issues and solutions
- **[MCP Server](../mcp-server/)** - Using processed documentation with AI tools
- **[Project Management](../../cli-reference/)** - Managing multiple projects

---

**Ready to connect to public documentation?** Start with the basic configuration above and customize based on the specific documentation site structure and your needs.
