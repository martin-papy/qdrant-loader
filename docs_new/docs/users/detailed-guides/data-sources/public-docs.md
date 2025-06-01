# Public Documentation

Connect QDrant Loader to public documentation websites, API references, and external knowledge sources. This guide covers setup for web scraping and processing publicly available content.

## 🎯 What Gets Processed

When you configure public documentation processing, QDrant Loader can handle:

- **API Documentation** - REST API docs, OpenAPI specs, SDK documentation
- **Technical Documentation** - Framework docs, library references, tutorials
- **Knowledge Bases** - Public wikis, help centers, support documentation
- **Blog Posts** - Technical blogs, release notes, announcements
- **Static Sites** - Documentation sites built with Jekyll, Hugo, GitBook
- **Multi-page Sites** - Comprehensive documentation with navigation
- **Versioned Documentation** - Multiple versions of the same documentation

## 🔧 Setup and Configuration

### Basic Configuration

```yaml
sources:
  public_docs:
    - url: "https://docs.example.com"
      name: "example_docs"
      css_selector: ".content"
      include_patterns:
        - "/docs/**"
        - "/api/**"
      exclude_patterns:
        - "/docs/archive/**"
        - "**/*.pdf"
```

### Advanced Configuration

```yaml
sources:
  public_docs:
    - url: "https://docs.example.com"
      name: "example_api_docs"
      
      # Content extraction
      css_selector: ".main-content"
      title_selector: "h1, .page-title"
      content_selectors:
        - ".content"
        - ".documentation"
        - ".api-docs"
      exclude_selectors:
        - ".sidebar"
        - ".navigation"
        - ".footer"
        - ".advertisement"
      
      # URL filtering
      include_patterns:
        - "/docs/**"
        - "/api/**"
        - "/guides/**"
        - "/tutorials/**"
      exclude_patterns:
        - "/docs/archive/**"
        - "/docs/deprecated/**"
        - "**/*.pdf"
        - "**/*.zip"
        - "**/search**"
        - "**/login**"
      
      # Crawling behavior
      max_depth: 5
      max_pages: 1000
      follow_external_links: false
      respect_robots_txt: true
      
      # Request settings
      request_delay: 1.0
      max_concurrent_requests: 3
      request_timeout: 30
      retry_attempts: 3
      user_agent: "QDrant-Loader/1.0"
      
      # Content processing
      extract_code_blocks: true
      preserve_formatting: true
      include_images: false
      extract_tables: true
      
      # Versioning
      version_detection: true
      version_pattern: "/v\\d+\\.\\d+/"
      latest_version_only: true
      
      # Caching
      enable_caching: true
      cache_ttl_hours: 24
      respect_cache_headers: true
```

### Multiple Documentation Sites

```yaml
sources:
  public_docs:
    # Main API documentation
    - url: "https://api.example.com/docs"
      name: "api_docs"
      css_selector: ".api-content"
      include_patterns: ["/docs/**", "/reference/**"]
      
    # Framework documentation
    - url: "https://framework.example.com"
      name: "framework_docs"
      css_selector: ".documentation"
      include_patterns: ["/guide/**", "/api/**"]
      max_depth: 3
      
    # Community wiki
    - url: "https://wiki.example.com"
      name: "community_wiki"
      css_selector: ".wiki-content"
      include_patterns: ["/wiki/**"]
      exclude_patterns: ["/wiki/user:**", "/wiki/talk:**"]
      
    # Release notes and blog
    - url: "https://blog.example.com"
      name: "release_blog"
      css_selector: ".post-content"
      include_patterns: ["/release-notes/**", "/announcements/**"]
      max_pages: 100
```

## 🎯 Configuration Options

### Basic Settings

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `url` | string | Base URL to start crawling | Required |
| `name` | string | Identifier for this source | URL domain |
| `description` | string | Human-readable description | None |

### Content Extraction

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `css_selector` | string | Main content CSS selector | `"body"` |
| `title_selector` | string | Page title CSS selector | `"h1, title"` |
| `content_selectors` | list | Multiple content selectors | `[]` |
| `exclude_selectors` | list | Elements to exclude | `[]` |

### URL Filtering

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `include_patterns` | list | URL patterns to include | `["**"]` |
| `exclude_patterns` | list | URL patterns to exclude | `[]` |
| `max_depth` | int | Maximum crawl depth | `5` |
| `max_pages` | int | Maximum pages to process | `1000` |
| `follow_external_links` | bool | Follow links to other domains | `false` |

### Crawling Behavior

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `respect_robots_txt` | bool | Respect robots.txt file | `true` |
| `request_delay` | float | Delay between requests (seconds) | `1.0` |
| `max_concurrent_requests` | int | Concurrent requests | `3` |
| `request_timeout` | int | Request timeout (seconds) | `30` |
| `retry_attempts` | int | Number of retry attempts | `3` |
| `user_agent` | string | User agent string | `"QDrant-Loader/1.0"` |

### Content Processing

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `extract_code_blocks` | bool | Extract code blocks separately | `true` |
| `preserve_formatting` | bool | Maintain HTML formatting | `false` |
| `include_images` | bool | Process image content | `false` |
| `extract_tables` | bool | Extract table data | `true` |
| `clean_html` | bool | Remove HTML tags | `true` |

### Versioning

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `version_detection` | bool | Detect documentation versions | `false` |
| `version_pattern` | string | Regex pattern for version detection | None |
| `latest_version_only` | bool | Only process latest version | `true` |
| `version_mapping` | dict | Map version URLs to names | `{}` |

### Caching and Performance

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `enable_caching` | bool | Cache downloaded pages | `true` |
| `cache_ttl_hours` | int | Cache time-to-live | `24` |
| `respect_cache_headers` | bool | Respect HTTP cache headers | `true` |
| `compress_cache` | bool | Compress cached content | `true` |

## 🚀 Usage Examples

### API Documentation

```yaml
sources:
  public_docs:
    # REST API Documentation
    - url: "https://api.stripe.com/docs"
      name: "stripe_api"
      css_selector: ".api-content"
      include_patterns:
        - "/docs/api/**"
        - "/docs/webhooks/**"
        - "/docs/connect/**"
      extract_code_blocks: true
      preserve_formatting: true
      
    # OpenAPI/Swagger Documentation
    - url: "https://petstore.swagger.io"
      name: "swagger_petstore"
      css_selector: ".swagger-ui"
      include_patterns: ["/v2/**", "/v3/**"]
      extract_tables: true
      
    # SDK Documentation
    - url: "https://docs.aws.amazon.com/sdk-for-python"
      name: "aws_python_sdk"
      css_selector: ".main-content"
      include_patterns: ["/latest/**"]
      exclude_patterns: ["/latest/reference/services/**"]
      max_depth: 4
```

### Framework Documentation

```yaml
sources:
  public_docs:
    # React Documentation
    - url: "https://react.dev"
      name: "react_docs"
      css_selector: ".content"
      include_patterns:
        - "/learn/**"
        - "/reference/**"
        - "/community/**"
      exclude_patterns:
        - "/blog/**"
      
    # Django Documentation
    - url: "https://docs.djangoproject.com"
      name: "django_docs"
      css_selector: ".document"
      include_patterns: ["/en/stable/**"]
      version_detection: true
      version_pattern: "/en/(\\d+\\.\\d+)/"
      latest_version_only: true
      
    # FastAPI Documentation
    - url: "https://fastapi.tiangolo.com"
      name: "fastapi_docs"
      css_selector: ".md-content"
      include_patterns: ["/tutorial/**", "/advanced/**"]
      extract_code_blocks: true
```

### Knowledge Bases and Wikis

```yaml
sources:
  public_docs:
    # Confluence Public Space
    - url: "https://confluence.atlassian.com/doc"
      name: "atlassian_docs"
      css_selector: ".wiki-content"
      include_patterns: ["/doc/**"]
      exclude_patterns: ["/doc/user/**"]
      
    # GitHub Wiki
    - url: "https://github.com/microsoft/vscode/wiki"
      name: "vscode_wiki"
      css_selector: ".markdown-body"
      follow_external_links: false
      
    # GitBook Documentation
    - url: "https://docs.gitbook.com"
      name: "gitbook_docs"
      css_selector: ".page-content"
      include_patterns: ["/product-tour/**", "/content-creation/**"]
```

### Technical Blogs and Release Notes

```yaml
sources:
  public_docs:
    # Engineering Blog
    - url: "https://engineering.example.com"
      name: "engineering_blog"
      css_selector: ".post-content"
      include_patterns: ["/posts/**", "/articles/**"]
      exclude_patterns: ["/author/**", "/tag/**"]
      max_pages: 200
      
    # Release Notes
    - url: "https://releases.example.com"
      name: "release_notes"
      css_selector: ".release-content"
      include_patterns: ["/notes/**", "/changelog/**"]
      
    # Product Updates
    - url: "https://updates.example.com"
      name: "product_updates"
      css_selector: ".update-content"
      include_patterns: ["/updates/**"]
      max_depth: 2
```

## 🔍 Advanced Features

### Custom Content Extraction

```yaml
sources:
  public_docs:
    - url: "https://complex-docs.example.com"
      name: "complex_docs"
      
      # Multiple content areas
      content_selectors:
        - ".main-content"
        - ".sidebar-content"
        - ".code-examples"
      
      # Exclude navigation and ads
      exclude_selectors:
        - ".navigation"
        - ".breadcrumb"
        - ".advertisement"
        - ".social-share"
        - ".comments"
      
      # Custom title extraction
      title_selector: ".page-title, .article-title, h1"
      
      # Metadata extraction
      extract_metadata: true
      metadata_selectors:
        author: ".author-name"
        date: ".publish-date"
        category: ".category-tag"
```

### Version-Aware Processing

```yaml
sources:
  public_docs:
    - url: "https://versioned-docs.example.com"
      name: "versioned_docs"
      
      # Version detection
      version_detection: true
      version_pattern: "/v(\\d+\\.\\d+)/"
      
      # Process multiple versions
      latest_version_only: false
      version_mapping:
        "/v2.0/": "2.0"
        "/v1.5/": "1.5"
        "/v1.0/": "1.0"
      
      # Version-specific patterns
      include_patterns:
        - "/v2.0/docs/**"
        - "/v1.5/docs/**"
      exclude_patterns:
        - "/v*/deprecated/**"
```

### JavaScript-Rendered Content

```yaml
sources:
  public_docs:
    - url: "https://spa-docs.example.com"
      name: "spa_docs"
      
      # Enable JavaScript rendering
      render_javascript: true
      wait_for_selector: ".content-loaded"
      page_load_timeout: 30
      
      # Handle dynamic content
      scroll_to_bottom: true
      wait_after_load: 2
      
      # Browser settings
      browser_headless: true
      browser_user_agent: "Mozilla/5.0 (compatible; QDrant-Loader)"
```

### Authentication and Headers

```yaml
sources:
  public_docs:
    - url: "https://protected-docs.example.com"
      name: "protected_docs"
      
      # Authentication
      auth_type: "bearer"
      auth_token: "${DOCS_API_TOKEN}"
      
      # Custom headers
      headers:
        "Authorization": "Bearer ${DOCS_API_TOKEN}"
        "X-API-Key": "${DOCS_API_KEY}"
        "Accept": "text/html,application/xhtml+xml"
      
      # Cookies
      cookies:
        "session_id": "${SESSION_ID}"
        "auth_token": "${AUTH_TOKEN}"
```

### Performance Optimization

```yaml
sources:
  public_docs:
    - url: "https://large-docs.example.com"
      name: "large_docs"
      
      # Optimize crawling
      max_concurrent_requests: 5
      request_delay: 0.5
      batch_size: 100
      
      # Intelligent filtering
      smart_filtering: true
      content_similarity_threshold: 0.8
      
      # Caching optimization
      enable_caching: true
      cache_compression: true
      cache_directory: "/tmp/docs_cache"
      
      # Resource limits
      max_page_size: 10485760  # 10MB
      max_total_size: 1073741824  # 1GB
```

## 🧪 Testing and Validation

### Test Public Documentation Access

```bash
# Test website accessibility
qdrant-loader --workspace . test-connections --sources public_docs

# Validate public docs configuration
qdrant-loader --workspace . validate --sources public_docs

# Preview pages that would be crawled
qdrant-loader --workspace . preview-crawl --sources public_docs

# Test CSS selectors
qdrant-loader --workspace . test-selectors --sources public_docs --url "https://example.com/page"

# Dry run to see crawling plan
qdrant-loader --workspace . --dry-run ingest --sources public_docs
```

### Debug Web Scraping

```bash
# Enable verbose logging
qdrant-loader --workspace . --verbose ingest --sources public_docs

# Test single page processing
qdrant-loader --workspace . process-url --url "https://example.com/specific-page"

# Check crawling status
qdrant-loader --workspace . status --sources public_docs --detailed

# Monitor crawling progress
qdrant-loader --workspace . status --sources public_docs --watch
```

## 🔧 Troubleshooting

### Common Issues

#### Access Denied or Blocked

**Problem**: `403 Forbidden`, `429 Too Many Requests`, or blocked by anti-bot measures

**Solutions**:

```yaml
sources:
  public_docs:
    - url: "https://protected-site.com"
      # Reduce request rate
      request_delay: 2.0
      max_concurrent_requests: 1
      
      # Use realistic user agent
      user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      
      # Add headers to appear more like a browser
      headers:
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        "Accept-Language": "en-US,en;q=0.5"
        "Accept-Encoding": "gzip, deflate"
        "Connection": "keep-alive"
```

#### Content Not Found

**Problem**: CSS selectors don't match content or pages appear empty

**Solutions**:

```bash
# Test CSS selectors manually
curl -s "https://example.com/page" | grep -A 10 -B 10 "class=\"content\""

# Use browser developer tools to find correct selectors
# Check if content is loaded dynamically with JavaScript
```

```yaml
sources:
  public_docs:
    - url: "https://example.com"
      # Try multiple selectors
      content_selectors:
        - ".main-content"
        - ".content"
        - ".documentation"
        - "main"
        - "article"
      
      # Enable JavaScript rendering if needed
      render_javascript: true
```

#### Rate Limiting

**Problem**: Getting rate limited or IP blocked

**Solutions**:

```yaml
sources:
  public_docs:
    - url: "https://example.com"
      # Slow down requests
      request_delay: 3.0
      max_concurrent_requests: 1
      
      # Respect robots.txt
      respect_robots_txt: true
      
      # Add random delays
      random_delay: true
      delay_range: [1.0, 3.0]
```

#### JavaScript-Heavy Sites

**Problem**: Content not loading because it requires JavaScript

**Solutions**:

```yaml
sources:
  public_docs:
    - url: "https://spa-site.com"
      # Enable JavaScript rendering
      render_javascript: true
      browser_headless: true
      
      # Wait for content to load
      wait_for_selector: ".content-loaded"
      page_load_timeout: 30
      wait_after_load: 3
```

#### Large Sites Performance

**Problem**: Crawling takes too long or uses too much memory

**Solutions**:

```yaml
sources:
  public_docs:
    - url: "https://large-site.com"
      # Limit scope
      max_pages: 500
      max_depth: 3
      
      # Filter aggressively
      include_patterns: ["/docs/**"]
      exclude_patterns: 
        - "/docs/archive/**"
        - "/docs/old/**"
        - "**/*.pdf"
      
      # Optimize processing
      max_concurrent_requests: 2
      enable_caching: true
```

### Debugging Commands

```bash
# Test website accessibility
curl -I "https://example.com"

# Check robots.txt
curl "https://example.com/robots.txt"

# Test CSS selector
curl -s "https://example.com" | pup '.content text{}'

# Check page structure
curl -s "https://example.com" | pup 'title, h1, h2'
```

## 📊 Monitoring and Metrics

### Processing Statistics

```bash
# View public docs processing statistics
qdrant-loader --workspace . stats --sources public_docs

# Check site-specific statistics
qdrant-loader --workspace . stats --sources public_docs --site "example.com"

# Monitor crawling progress
qdrant-loader --workspace . status --sources public_docs --watch
```

### Performance Metrics

Monitor these metrics for public documentation processing:

- **Pages crawled per minute** - Crawling throughput
- **Request success rate** - Percentage of successful requests
- **Content extraction rate** - Pages with successfully extracted content
- **Cache hit rate** - Effectiveness of page caching
- **Average page size** - Understanding content characteristics
- **Crawl depth distribution** - How deep the crawler goes

## 🔄 Best Practices

### Respectful Crawling

1. **Respect robots.txt** - Always check and follow robots.txt rules
2. **Use reasonable delays** - Don't overwhelm servers with requests
3. **Limit concurrent requests** - Keep concurrent requests low
4. **Use appropriate user agents** - Identify your crawler properly

### Content Quality

1. **Use specific CSS selectors** - Target main content areas precisely
2. **Exclude navigation and ads** - Focus on actual content
3. **Handle dynamic content** - Enable JavaScript rendering when needed
4. **Validate extracted content** - Check that content makes sense

### Performance Optimization

1. **Cache aggressively** - Enable caching to avoid re-downloading
2. **Filter URLs early** - Use include/exclude patterns effectively
3. **Limit crawl scope** - Set reasonable depth and page limits
4. **Monitor resource usage** - Watch memory and disk usage

### Legal and Ethical Considerations

1. **Check terms of service** - Ensure crawling is allowed
2. **Respect copyright** - Only use content appropriately
3. **Be transparent** - Use clear user agent identification
4. **Handle personal data carefully** - Avoid collecting personal information

## 📚 Related Documentation

- **[File Conversion](../file-conversion/)** - Processing downloaded files
- **[Configuration Reference](../../configuration/)** - Complete configuration options
- **[Troubleshooting](../../troubleshooting/)** - Common issues and solutions
- **[MCP Server](../mcp-server/)** - Using processed public content with AI tools

---

**Ready to crawl public documentation?** Start with the basic configuration above and customize based on the specific sites and content you need to process.
