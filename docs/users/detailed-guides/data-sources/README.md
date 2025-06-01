# Data Sources

QDrant Loader supports multiple data sources to help you index and search across all your organization's knowledge. This guide provides an overview of all supported sources and links to detailed configuration guides.

## 🎯 Supported Data Sources

### 📁 [Git Repositories](git-repositories.md)

Connect to Git repositories across multiple platforms to index code, documentation, and project files.

**Supported Platforms:**

- GitHub (github.com, GitHub Enterprise)
- GitLab (gitlab.com, self-hosted GitLab)
- Bitbucket (bitbucket.org, Bitbucket Server)
- Azure DevOps / TFS
- Self-hosted Git servers

**What Gets Processed:**

- Source code files (Python, JavaScript, Java, C++, etc.)
- Documentation (README, Markdown, reStructuredText)
- Configuration files (YAML, JSON, TOML)
- Project metadata and commit history

**Key Features:**

- Multiple authentication methods (SSH keys, tokens, passwords)
- Branch and tag filtering
- File type and path filtering
- Commit history processing
- Large repository optimization

---

### 🏢 [Confluence](confluence.md)

Index team documentation, knowledge bases, and collaborative content from Confluence Cloud and Data Center.

**Supported Versions:**

- Confluence Cloud (atlassian.com)
- Confluence Data Center / Server

**What Gets Processed:**

- Page content and hierarchy
- Attachments (PDFs, Office docs, images)
- Comments and discussions
- Page metadata (authors, dates, labels)
- Space information

**Key Features:**

- API token and OAuth authentication
- Space and page filtering
- Attachment processing with file conversion
- Version history tracking
- Bulk export support

---

### 🎫 [JIRA](jira.md)

Process project tickets, issues, requirements, and project management data from JIRA Cloud and Data Center.

**Supported Versions:**

- JIRA Cloud (atlassian.com)
- JIRA Data Center / Server

**What Gets Processed:**

- Issue content (summaries, descriptions, comments)
- Issue metadata (status, priority, assignee, labels)
- Custom fields and project-specific data
- Attachments and linked content
- Sprint and agile planning data

**Key Features:**

- API token and OAuth authentication
- JQL (JIRA Query Language) filtering
- Project and issue type filtering
- Custom field processing
- Agile workflow support

---

### 📂 [Local Files](local-files.md)

Process documents, research materials, archives, and any file-based content from your local file system.

**Supported File Types:**

- Documents (PDF, Word, PowerPoint, Excel)
- Text files (Markdown, plain text, reStructuredText)
- Code files (Python, JavaScript, Java, C++, etc.)
- Images (with OCR text extraction)
- Audio files (with transcription)
- Archives (ZIP, TAR, 7Z with extraction)

**What Gets Processed:**

- File content with format-specific conversion
- File metadata (creation date, author, size)
- Directory structure and organization
- Archive contents (recursive processing)

**Key Features:**

- 20+ file format support via MarkItDown
- OCR for image text extraction
- Audio transcription
- Archive extraction and processing
- Flexible file filtering patterns

---

### 🌐 [Public Documentation](public-docs.md)

Crawl and index public documentation websites, API references, and external knowledge sources.

**Supported Content Types:**

- API documentation (REST APIs, OpenAPI specs)
- Technical documentation (framework docs, tutorials)
- Knowledge bases (public wikis, help centers)
- Blog posts and release notes
- Static documentation sites

**What Gets Processed:**

- Web page content with CSS selector targeting
- Multi-page documentation sites
- Versioned documentation
- Code examples and API references
- Structured content extraction

**Key Features:**

- Respectful web crawling with rate limiting
- CSS selector-based content extraction
- JavaScript rendering for dynamic content
- Version-aware processing
- Comprehensive URL filtering

---

## 🔧 File Conversion

All data sources that handle files benefit from QDrant Loader's comprehensive [file conversion capabilities](../file-conversion/):

### Supported Formats

- **Documents**: PDF, Word, PowerPoint, Excel, OpenDocument
- **Text**: Markdown, reStructuredText, plain text, LaTeX
- **Images**: JPEG, PNG, GIF, TIFF (with OCR)
- **Audio**: MP3, WAV, M4A (with transcription)
- **Data**: JSON, CSV, XML, YAML
- **Archives**: ZIP, TAR, 7-Zip, RAR

### Advanced Features

- **OCR Text Extraction**: Extract text from images and scanned documents
- **Audio Transcription**: Convert speech to text using Whisper
- **Password Protection**: Handle encrypted files and archives
- **Metadata Extraction**: Preserve file metadata and properties
- **Batch Processing**: Efficient processing of large file collections

## ⚙️ Configuration Overview

### Basic Multi-Source Setup

```yaml
# Configure multiple data sources
sources:
  # Git repositories
  git:
    - url: "https://github.com/company/docs"
      name: "company_docs"
      auth_token: "${GITHUB_TOKEN}"
      
  # Confluence spaces
  confluence:
    - url: "${CONFLUENCE_URL}"
      username: "${CONFLUENCE_USER}"
      api_token: "${CONFLUENCE_TOKEN}"
      spaces: ["DOCS", "TECH"]
      
  # JIRA projects
  jira:
    - url: "${JIRA_URL}"
      username: "${JIRA_USER}"
      api_token: "${JIRA_TOKEN}"
      projects: ["PROJ", "SUPPORT"]
      
  # Local documentation
  local_files:
    - path: "/docs/internal"
      include_patterns: ["**/*.md", "**/*.pdf"]
      
  # Public API docs
  public_docs:
    - url: "https://api.example.com/docs"
      css_selector: ".api-content"
      include_patterns: ["/docs/**"]
```

### Environment Variables

```bash
# Git authentication
export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"
export GITLAB_TOKEN="glpat-xxxxxxxxxxxx"

# Confluence authentication
export CONFLUENCE_URL="https://company.atlassian.net"
export CONFLUENCE_USER="user@company.com"
export CONFLUENCE_TOKEN="ATATT3xFfGF0xxxxxxxxxxxx"

# JIRA authentication
export JIRA_URL="https://company.atlassian.net"
export JIRA_USER="user@company.com"
export JIRA_TOKEN="ATATT3xFfGF0xxxxxxxxxxxx"
```

## 🚀 Quick Start Examples

### Development Team

```yaml
sources:
  # Source code repositories
  git:
    - url: "https://github.com/company/backend"
      include_patterns: ["**/*.py", "**/*.md"]
    - url: "https://github.com/company/frontend"
      include_patterns: ["**/*.js", "**/*.ts", "**/*.md"]
      
  # Technical documentation
  confluence:
    - url: "${CONFLUENCE_URL}"
      spaces: ["DEV", "API", "ARCH"]
      
  # Development tickets
  jira:
    - url: "${JIRA_URL}"
      projects: ["DEV", "BUG"]
      jql: "project in (DEV, BUG) AND status != Closed"
```

### Documentation Team

```yaml
sources:
  # Documentation repositories
  git:
    - url: "https://github.com/company/docs"
      include_patterns: ["**/*.md", "**/*.rst"]
      
  # Knowledge base
  confluence:
    - url: "${CONFLUENCE_URL}"
      spaces: ["DOCS", "KB", "HELP"]
      include_attachments: true
      
  # Legacy documents
  local_files:
    - path: "/docs/legacy"
      include_patterns: ["**/*.pdf", "**/*.docx"]
      
  # External API documentation
  public_docs:
    - url: "https://docs.external-api.com"
      css_selector: ".documentation"
```

### Research Team

```yaml
sources:
  # Research repositories
  git:
    - url: "https://github.com/research/papers"
      include_patterns: ["**/*.tex", "**/*.bib", "**/*.md"]
      
  # Research papers and datasets
  local_files:
    - path: "/research/papers"
      include_patterns: ["**/*.pdf", "**/*.tex"]
    - path: "/research/datasets"
      include_patterns: ["**/*.csv", "**/*.json"]
      
  # Project tracking
  jira:
    - url: "${JIRA_URL}"
      projects: ["RESEARCH"]
      include_attachments: true
```

## 🧪 Testing and Validation

### Test All Data Sources

```bash
# Test connectivity to all configured sources
qdrant-loader --workspace . test-connections

# Validate all source configurations
qdrant-loader --workspace . validate

# Preview what would be processed
qdrant-loader --workspace . --dry-run ingest

# Process specific sources only
qdrant-loader --workspace . ingest --sources git,confluence
```

### Debug Individual Sources

```bash
# Test specific source type
qdrant-loader --workspace . test-connections --sources git
qdrant-loader --workspace . test-connections --sources confluence

# Validate specific configuration
qdrant-loader --workspace . validate --sources local_files

# Check processing status
qdrant-loader --workspace . status --detailed
```

## 📊 Monitoring and Management

### Processing Statistics

```bash
# View overall processing statistics
qdrant-loader --workspace . stats

# Source-specific statistics
qdrant-loader --workspace . stats --sources git
qdrant-loader --workspace . stats --sources confluence

# Monitor processing progress
qdrant-loader --workspace . status --watch
```

### Performance Optimization

```yaml
# Global performance settings
performance:
  max_concurrent_sources: 3
  max_concurrent_files: 5
  batch_size: 100
  enable_caching: true
  
# Source-specific optimization
sources:
  git:
    - url: "https://github.com/large-repo"
      # Optimize for large repositories
      max_file_size: 10485760  # 10MB
      exclude_patterns: ["**/node_modules/**"]
      
  local_files:
    - path: "/large-dataset"
      # Optimize for many files
      max_concurrent_files: 10
      enable_caching: true
```

## 🔧 Troubleshooting

### Common Issues

#### Authentication Problems

**Problem**: `401 Unauthorized` or `403 Forbidden` errors

**Solutions**:

1. Verify API tokens and credentials
2. Check token permissions and scopes
3. Ensure URLs are correct
4. Test authentication manually

#### Performance Issues

**Problem**: Slow processing or timeouts

**Solutions**:

1. Reduce concurrent operations
2. Filter content more aggressively
3. Enable caching
4. Process in smaller batches

#### Content Not Found

**Problem**: Expected content not being processed

**Solutions**:

1. Check include/exclude patterns
2. Verify source permissions
3. Test with verbose logging
4. Validate configuration syntax

### Getting Help

```bash
# Enable verbose logging for debugging
qdrant-loader --workspace . --verbose ingest

# Check configuration syntax
qdrant-loader --workspace . validate

# View detailed error information
qdrant-loader --workspace . status --detailed

# Test individual components
qdrant-loader --workspace . test-connections --sources git
```

## 📚 Detailed Guides

Each data source has comprehensive documentation covering:

- **Setup and Authentication** - Step-by-step configuration
- **Configuration Options** - Complete parameter reference
- **Usage Examples** - Real-world scenarios and patterns
- **Advanced Features** - Power user capabilities
- **Troubleshooting** - Common issues and solutions
- **Best Practices** - Optimization and security recommendations

### 📖 Individual Source Guides

- **[Git Repositories](git-repositories.md)** - Complete Git integration guide
- **[Confluence](confluence.md)** - Confluence Cloud and Data Center setup
- **[JIRA](jira.md)** - JIRA Cloud and Data Center configuration
- **[Local Files](local-files.md)** - File system processing guide
- **[Public Documentation](public-docs.md)** - Web crawling and content extraction
- **[File Conversion](../file-conversion/)** - Format support and conversion options

---

**Ready to connect your data sources?** Choose the sources that match your organization's tools and follow the detailed guides for step-by-step setup instructions.
