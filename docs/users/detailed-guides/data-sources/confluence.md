# Confluence

Connect QDrant Loader to Confluence to index team documentation, knowledge bases, and collaborative content. This guide covers setup for both Confluence Cloud and Confluence Data Center.

## 🎯 What Gets Processed

When you connect to Confluence, QDrant Loader can process:

- **Page content** - All text content from Confluence pages
- **Page hierarchy** - Parent/child relationships between pages
- **Attachments** - Files attached to pages (PDFs, Office docs, images)
- **Comments** - Page comments and discussions
- **Page metadata** - Authors, creation dates, labels, versions
- **Space information** - Space descriptions and metadata

## 🔧 Authentication Setup

### Confluence Cloud

#### API Token (Recommended)

1. **Create an API Token**:
   - Go to [Atlassian Account Settings](https://id.atlassian.com/manage-profile/security/api-tokens)
   - Click "Create API token"
   - Give it a descriptive name like "QDrant Loader"
   - Copy the token

2. **Set environment variables**:

   ```bash
   export CONFLUENCE_URL=https://your-domain.atlassian.net
   export CONFLUENCE_EMAIL=your-email@company.com
   export CONFLUENCE_TOKEN=your_api_token_here
   ```

#### OAuth 2.0 (Enterprise)

For enterprise setups with OAuth:

```bash
export CONFLUENCE_URL=https://your-domain.atlassian.net
export CONFLUENCE_CLIENT_ID=your_oauth_client_id
export CONFLUENCE_CLIENT_SECRET=your_oauth_client_secret
export CONFLUENCE_REDIRECT_URI=your_redirect_uri
```

### Confluence Data Center

#### Personal Access Token

1. **Create a Personal Access Token**:
   - Go to Confluence → Settings → Personal Access Tokens
   - Click "Create token"
   - Set appropriate permissions: `READ` for spaces and pages
   - Copy the token

2. **Set environment variables**:

   ```bash
   export CONFLUENCE_URL=https://confluence.your-company.com
   export CONFLUENCE_TOKEN=your_personal_access_token
   ```

#### Basic Authentication

For older Data Center versions:

```bash
export CONFLUENCE_URL=https://confluence.your-company.com
export CONFLUENCE_USERNAME=your_username
export CONFLUENCE_PASSWORD=your_password
```

## ⚙️ Configuration

### Basic Configuration

```yaml
sources:
  confluence:
    - url: "${CONFLUENCE_URL}"
      username: "${CONFLUENCE_EMAIL}"
      token: "${CONFLUENCE_TOKEN}"
      spaces:
        - "DOCS"
        - "TECH"
        - "PROJ"
      include_attachments: true
      include_comments: false
```

### Advanced Configuration

```yaml
sources:
  confluence:
    - url: "${CONFLUENCE_URL}"
      username: "${CONFLUENCE_EMAIL}"
      token: "${CONFLUENCE_TOKEN}"
      
      # Space filtering
      spaces:
        - "DOCS"
        - "TECH"
      exclude_spaces:
        - "ARCHIVE"
        - "TEMP"
      
      # Content filtering
      include_patterns:
        - "Architecture/*"
        - "API Documentation/*"
        - "User Guides/*"
      exclude_patterns:
        - "*/Archive/*"
        - "*/Draft/*"
      
      # Page filtering
      include_page_types:
        - "page"
        - "blogpost"
      exclude_page_labels:
        - "draft"
        - "obsolete"
        - "internal-only"
      
      # Content options
      include_attachments: true
      include_comments: true
      include_page_history: false
      max_page_versions: 1
      
      # File filtering for attachments
      attachment_patterns:
        - "**/*.pdf"
        - "**/*.docx"
        - "**/*.pptx"
        - "**/*.md"
      max_attachment_size: 10485760  # 10MB
      
      # Performance settings
      max_concurrent_pages: 5
      request_timeout: 30
      retry_attempts: 3
      enable_caching: true
```

### Multiple Confluence Instances

```yaml
sources:
  confluence:
    # Production Confluence
    - url: "https://company.atlassian.net"
      username: "${CONFLUENCE_EMAIL}"
      token: "${CONFLUENCE_TOKEN}"
      spaces: ["DOCS", "TECH"]
      
    # Internal Confluence Data Center
    - url: "https://internal-confluence.company.com"
      username: "${INTERNAL_CONFLUENCE_USERNAME}"
      token: "${INTERNAL_CONFLUENCE_TOKEN}"
      spaces: ["INTERNAL", "RESEARCH"]
```

## 🎯 Configuration Options

### Connection Settings

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `url` | string | Confluence base URL | Required |
| `username` | string | Username or email | Required |
| `token` | string | API token or password | Required |
| `verify_ssl` | bool | Verify SSL certificates | `true` |

### Space and Page Filtering

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `spaces` | list | Space keys to include | All accessible |
| `exclude_spaces` | list | Space keys to exclude | `[]` |
| `include_patterns` | list | Page title patterns to include | `["*"]` |
| `exclude_patterns` | list | Page title patterns to exclude | `[]` |
| `include_page_types` | list | Page types to include | `["page"]` |
| `exclude_page_labels` | list | Page labels to exclude | `[]` |

### Content Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `include_attachments` | bool | Process page attachments | `true` |
| `include_comments` | bool | Include page comments | `false` |
| `include_page_history` | bool | Include page versions | `false` |
| `max_page_versions` | int | Maximum versions per page | `1` |
| `strip_html` | bool | Remove HTML formatting | `true` |

### Attachment Processing

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `attachment_patterns` | list | File patterns to include | `["**/*"]` |
| `max_attachment_size` | int | Maximum file size in bytes | `10485760` |
| `download_attachments` | bool | Download and process files | `true` |

### Performance Settings

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `max_concurrent_pages` | int | Concurrent page requests | `5` |
| `request_timeout` | int | Request timeout in seconds | `30` |
| `retry_attempts` | int | Number of retry attempts | `3` |
| `enable_caching` | bool | Cache pages locally | `true` |

## 🚀 Usage Examples

### Documentation Team

```yaml
sources:
  confluence:
    - url: "${CONFLUENCE_URL}"
      username: "${CONFLUENCE_EMAIL}"
      token: "${CONFLUENCE_TOKEN}"
      
      # Focus on documentation spaces
      spaces:
        - "DOCS"      # Main documentation
        - "GUIDES"    # User guides
        - "API"       # API documentation
        - "ARCH"      # Architecture docs
      
      # Include comprehensive content
      include_attachments: true
      include_comments: true
      
      # Filter out drafts and archives
      exclude_patterns:
        - "*/Draft/*"
        - "*/Archive/*"
        - "*/Template/*"
      exclude_page_labels:
        - "draft"
        - "wip"
        - "obsolete"
      
      # Process various file types
      attachment_patterns:
        - "**/*.pdf"
        - "**/*.docx"
        - "**/*.pptx"
        - "**/*.xlsx"
        - "**/*.md"
        - "**/*.txt"
```

### Software Development Team

```yaml
sources:
  confluence:
    - url: "${CONFLUENCE_URL}"
      username: "${CONFLUENCE_EMAIL}"
      token: "${CONFLUENCE_TOKEN}"
      
      # Development-focused spaces
      spaces:
        - "DEV"       # Development docs
        - "ARCH"      # Architecture
        - "API"       # API documentation
        - "DEPLOY"    # Deployment guides
      
      # Include specific content types
      include_patterns:
        - "Architecture/*"
        - "API/*"
        - "Development Guidelines/*"
        - "Deployment/*"
      
      # Skip meeting notes and personal pages
      exclude_patterns:
        - "*/Meeting Notes/*"
        - "*/Personal/*"
        - "*/Scratch/*"
      
      # Include technical attachments
      attachment_patterns:
        - "**/*.pdf"
        - "**/*.md"
        - "**/*.yaml"
        - "**/*.json"
        - "**/*.xml"
```

### Knowledge Management

```yaml
sources:
  confluence:
    - url: "${CONFLUENCE_URL}"
      username: "${CONFLUENCE_EMAIL}"
      token: "${CONFLUENCE_TOKEN}"
      
      # All knowledge spaces
      spaces:
        - "KB"        # Knowledge base
        - "FAQ"       # Frequently asked questions
        - "PROC"      # Processes and procedures
        - "TRAIN"     # Training materials
      
      # Include everything except archives
      exclude_patterns:
        - "*/Archive/*"
        - "*/Deprecated/*"
      
      # Include comments for context
      include_comments: true
      
      # Process all document types
      include_attachments: true
      max_attachment_size: 20971520  # 20MB
```

## 🔍 Advanced Features

### Hierarchy-Aware Processing

```yaml
sources:
  confluence:
    - url: "${CONFLUENCE_URL}"
      username: "${CONFLUENCE_EMAIL}"
      token: "${CONFLUENCE_TOKEN}"
      spaces: ["DOCS"]
      
      # Preserve page hierarchy
      preserve_hierarchy: true
      include_parent_context: true
      
      # Process child pages
      include_child_pages: true
      max_depth: 5
```

### Version and History Tracking

```yaml
sources:
  confluence:
    - url: "${CONFLUENCE_URL}"
      username: "${CONFLUENCE_EMAIL}"
      token: "${CONFLUENCE_TOKEN}"
      spaces: ["DOCS"]
      
      # Include page history
      include_page_history: true
      max_page_versions: 5
      
      # Track changes
      include_version_metadata: true
      track_page_changes: true
```

### Custom Field Processing

```yaml
sources:
  confluence:
    - url: "${CONFLUENCE_URL}"
      username: "${CONFLUENCE_EMAIL}"
      token: "${CONFLUENCE_TOKEN}"
      spaces: ["DOCS"]
      
      # Include custom metadata
      include_custom_fields: true
      custom_field_mapping:
        "customfield_10001": "priority"
        "customfield_10002": "category"
        "customfield_10003": "owner"
```

### Performance Optimization

```yaml
sources:
  confluence:
    - url: "${CONFLUENCE_URL}"
      username: "${CONFLUENCE_EMAIL}"
      token: "${CONFLUENCE_TOKEN}"
      spaces: ["DOCS"]
      
      # Optimize for large spaces
      max_concurrent_pages: 10
      batch_size: 50
      
      # Enable aggressive caching
      enable_caching: true
      cache_ttl_hours: 24
      
      # Limit processing scope
      max_pages_per_space: 1000
      modified_since: "2024-01-01"
```

## 🧪 Testing and Validation

### Test Confluence Connection

```bash
# Test Confluence connectivity
qdrant-loader --workspace . test-connections --sources confluence

# Validate Confluence configuration
qdrant-loader --workspace . validate --sources confluence

# List accessible spaces
qdrant-loader --workspace . list-spaces --sources confluence

# Dry run to see what would be processed
qdrant-loader --workspace . --dry-run ingest --sources confluence
```

### Debug Confluence Processing

```bash
# Enable verbose logging
qdrant-loader --workspace . --verbose ingest --sources confluence

# Process specific spaces only
qdrant-loader --workspace . ingest --sources confluence --spaces DOCS,TECH

# Check processing status
qdrant-loader --workspace . status --sources confluence --detailed
```

## 🔧 Troubleshooting

### Common Issues

#### Authentication Failures

**Problem**: `401 Unauthorized` or `403 Forbidden`

**Solutions**:

```bash
# Test API token manually
curl -u "your-email@company.com:your-api-token" \
  "https://your-domain.atlassian.net/wiki/rest/api/space"

# Check token permissions
curl -u "your-email@company.com:your-api-token" \
  "https://your-domain.atlassian.net/wiki/rest/api/user/current"

# For Data Center, test with username/password
curl -u "username:password" \
  "https://confluence.company.com/rest/api/space"
```

#### Space Access Issues

**Problem**: `Space not found` or `No permission to access space`

**Solutions**:

```bash
# List accessible spaces
curl -u "your-email:your-token" \
  "https://your-domain.atlassian.net/wiki/rest/api/space" | jq '.results[].key'

# Check specific space permissions
curl -u "your-email:your-token" \
  "https://your-domain.atlassian.net/wiki/rest/api/space/SPACKEY"
```

#### Rate Limiting

**Problem**: `429 Too Many Requests`

**Solutions**:

```yaml
sources:
  confluence:
    - url: "${CONFLUENCE_URL}"
      username: "${CONFLUENCE_EMAIL}"
      token: "${CONFLUENCE_TOKEN}"
      
      # Reduce concurrent requests
      max_concurrent_pages: 2
      request_delay: 1.0
      
      # Increase timeout
      request_timeout: 60
      retry_attempts: 5
```

#### Large Space Performance

**Problem**: Processing takes too long or times out

**Solutions**:

```yaml
sources:
  confluence:
    - url: "${CONFLUENCE_URL}"
      username: "${CONFLUENCE_EMAIL}"
      token: "${CONFLUENCE_TOKEN}"
      
      # Limit scope
      spaces: ["DOCS"]
      max_pages_per_space: 500
      
      # Filter aggressively
      exclude_patterns:
        - "*/Archive/*"
        - "*/Old/*"
        - "*/Deprecated/*"
      
      # Optimize processing
      include_attachments: false
      include_comments: false
      max_concurrent_pages: 3
```

#### Attachment Processing Issues

**Problem**: Attachments fail to download or process

**Solutions**:

```yaml
sources:
  confluence:
    - url: "${CONFLUENCE_URL}"
      username: "${CONFLUENCE_EMAIL}"
      token: "${CONFLUENCE_TOKEN}"
      
      # Limit attachment processing
      max_attachment_size: 5242880  # 5MB
      attachment_patterns:
        - "**/*.pdf"
        - "**/*.docx"
        - "**/*.md"
      
      # Skip problematic file types
      exclude_attachment_patterns:
        - "**/*.exe"
        - "**/*.zip"
        - "**/*.bin"
```

### Debugging Commands

```bash
# Check Confluence API version
curl -u "email:token" "https://domain.atlassian.net/wiki/rest/api/space" | jq '.size'

# List pages in a space
curl -u "email:token" \
  "https://domain.atlassian.net/wiki/rest/api/space/DOCS/content/page" | \
  jq '.results[].title'

# Check page content
curl -u "email:token" \
  "https://domain.atlassian.net/wiki/rest/api/content/PAGE_ID?expand=body.storage"
```

## 📊 Monitoring and Metrics

### Processing Statistics

```bash
# View Confluence processing statistics
qdrant-loader --workspace . stats --sources confluence

# Check space-specific statistics
qdrant-loader --workspace . stats --sources confluence --spaces DOCS

# Monitor processing progress
qdrant-loader --workspace . status --sources confluence --watch
```

### Performance Metrics

Monitor these metrics for Confluence processing:

- **Pages processed per minute** - Processing throughput
- **API request rate** - Requests per second to Confluence
- **Error rate** - Percentage of failed page requests
- **Attachment download time** - Time to download and process files
- **Memory usage** - Peak memory during processing

## 🔄 Best Practices

### Content Organization

1. **Use descriptive space keys** - Make spaces easy to identify
2. **Organize with page hierarchy** - Use parent/child relationships
3. **Apply consistent labeling** - Use labels for categorization
4. **Archive old content** - Move outdated content to archive spaces

### Performance Optimization

1. **Filter aggressively** - Only process content you need
2. **Limit attachment sizes** - Set reasonable size limits
3. **Use caching** - Enable local caching for repeated runs
4. **Process incrementally** - Use modified date filtering

### Security Considerations

1. **Use API tokens** - Prefer tokens over passwords
2. **Limit token scope** - Grant minimal necessary permissions
3. **Rotate tokens regularly** - Update tokens periodically
4. **Monitor access** - Track which content is being accessed

### Content Quality

1. **Maintain page hierarchy** - Keep logical organization
2. **Use consistent formatting** - Follow documentation standards
3. **Update regularly** - Keep content current and relevant
4. **Remove duplicates** - Avoid redundant information

## 📚 Related Documentation

- **[File Conversion](../file-conversion/)** - Processing Confluence attachments
- **[Configuration Reference](../../configuration/)** - Complete configuration options
- **[Troubleshooting](../../troubleshooting/)** - Common issues and solutions
- **[MCP Server](../mcp-server/)** - Using processed Confluence content with AI tools

---

**Ready to connect your Confluence instance?** Start with the basic configuration above and customize based on your space structure and content needs.
