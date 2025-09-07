# Local Files

> **🔄 Breaking Change**: The configuration root has been renamed from `global_config` to `global`. If you're upgrading from an earlier version, update your configuration files to use `global:` instead of `global_config:`.

Connect QDrant Loader to your local file system to index documents, research materials, archives, and any file-based content. This guide covers setup for processing local directories and files.

## 🎯 What Gets Processed

When you configure local file processing, QDrant Loader can handle:

- **Documents** - PDFs, Word docs, PowerPoint, Excel files (with file conversion)
- **Text files** - Markdown, plain text, and other text formats
- **Code files** - Python, JavaScript, Java, C++, and more
- **Data files** - JSON, CSV, XML, YAML configuration files
- **Any file type** - When file conversion is enabled, many additional formats are supported

## 🔧 Setup and Configuration

### Basic Configuration

```yaml
global:
  qdrant:
    url: "http://localhost:6333"
    collection_name: "documents"
  llm:
    provider: "openai"
    base_url: "https://api.openai.com/v1"
    api_key: "${LLM_API_KEY}"
    models:
      embeddings: "text-embedding-3-small"
      chat: "gpt-4o-mini"
    embeddings:
      vector_size: 1536
projects:
  my-project:
    sources:
      localfile:
        my-docs:
          base_url: "file:///path/to/documents"
          include_paths:
            - "**"
          exclude_paths:
            - "**/.*"
            - "**/~*"
            - "**/*.tmp"
          file_types:
            - "*.pdf"
            - "*.docx"
            - "*.md"
            - "*.txt"
          max_file_size: 52428800  # 50MB
```

### Advanced Configuration

```yaml
global:
  qdrant:
    url: "http://localhost:6333"
    collection_name: "documents"
  llm:
    provider: "openai"
    base_url: "https://api.openai.com/v1"
    api_key: "${LLM_API_KEY}"
    models:
      embeddings: "text-embedding-3-small"
      chat: "gpt-4o-mini"
    embeddings:
      vector_size: 1536
projects:
  my-project:
    sources:
      localfile:
        my-docs:
          base_url: "file:///path/to/documents"
          # File filtering
          include_paths:
            - "**"  # Include all files recursively
          exclude_paths:
            - "**/.*"  # Hidden files
            - "**/~*"  # Temporary files
            - "**/*.tmp"  # Temporary files
            - "**/node_modules/**"  # Dependencies
            - "**/__pycache__/**"  # Python cache
            - "**/build/**"  # Build artifacts
            - "**/dist/**"  # Distribution files
          # File types to process
          file_types:
            - "*.pdf"
            - "*.docx"
            - "*.doc"
            - "*.pptx"
            - "*.ppt"
            - "*.xlsx"
            - "*.xls"
            - "*.md"
            - "*.txt"
            - "*.py"
            - "*.js"
            - "*.json"
            - "*.yaml"
            - "*.yml"
          # Size limits
          max_file_size: 52428800  # 50MB
          # File conversion (requires global file_conversion config)
          enable_file_conversion: true
```

### Multiple Directory Sources

```yaml
global:
  qdrant:
    url: "http://localhost:6333"
    collection_name: "documents"
  llm:
    provider: "openai"
    base_url: "https://api.openai.com/v1"
    api_key: "${LLM_API_KEY}"
    models:
      embeddings: "text-embedding-3-small"
      chat: "gpt-4o-mini"
    embeddings:
      vector_size: 1536
projects:
  my-project:
    sources:
      localfile:
        # Research papers
        research-papers:
          base_url: "file:///home/user/research/papers"
          file_types:
            - "*.pdf"
            - "*.tex"
          max_file_size: 104857600  # 100MB
        # Project documentation
        project-docs:
          base_url: "file:///home/user/projects/docs"
          file_types:
            - "*.md"
            - "*.rst"
          exclude_paths:
            - "**/build/**"
            - "**/_build/**"
        # Source code
        source-code:
          base_url: "file:///home/user/code"
          file_types:
            - "*.py"
            - "*.js"
            - "*.java"
            - "*.cpp"
            - "*.h"
          exclude_paths:
            - "**/node_modules/**"
            - "**/__pycache__/**"
            - "**/.git/**"
            - "**/build/**"
            - "**/dist/**"
```

## 🎯 Configuration Options

### Base URL Requirements

- `base_url` must start with `file://` (validator enforced)

### Connection Settings

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `base_url` | string | Directory path with `file://` prefix | Required |

### File Filtering

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `include_paths` | list | Glob patterns for paths to include | `[]` |
| `exclude_paths` | list | Glob patterns for paths to exclude | `[]` |
| `file_types` | list | File extensions to process | `[]` |
| `max_file_size` | int | Maximum file size in bytes | `1048576` (1MB) |

### Processing Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `enable_file_conversion` | bool | Enable file conversion for supported formats | `false` |

## 🚀 Usage Examples

### Research Team

```yaml
global:
  qdrant:
    url: "http://localhost:6333"
    collection_name: "research-docs"
  llm:
    provider: "openai"
    base_url: "https://api.openai.com/v1"
    api_key: "${LLM_API_KEY}"
    models:
      embeddings: "text-embedding-3-small"
      chat: "gpt-4o-mini"
    embeddings:
      vector_size: 1536
projects:
  research:
    sources:
      localfile:
        # Research papers and publications
        research-papers:
          base_url: "file:///research/papers"
          file_types:
            - "*.pdf"
            - "*.tex"
            - "*.bib"
            - "*.md"
          max_file_size: 104857600  # 100MB for large papers
          enable_file_conversion: true
        # Datasets and data files
        research-data:
          base_url: "file:///research/datasets"
          file_types:
            - "*.csv"
            - "*.json"
            - "*.xml"
            - "*.xlsx"
          exclude_paths:
            - "**/raw/**"  # Skip raw data
            - "**/temp/**"  # Skip temporary files
```

### Documentation Team

```yaml
global:
  qdrant:
    url: "http://localhost:6333"
    collection_name: "documentation"
  llm:
    provider: "openai"
    base_url: "https://api.openai.com/v1"
    api_key: "${LLM_API_KEY}"
    models:
      embeddings: "text-embedding-3-small"
      chat: "gpt-4o-mini"
    embeddings:
      vector_size: 1536
projects:
  documentation:
    sources:
      localfile:
        # Main documentation
        docs-content:
          base_url: "file:///docs/content"
          file_types:
            - "*.md"
            - "*.rst"
            - "*.txt"
            - "*.adoc"
        # Legacy documents
        legacy-docs:
          base_url: "file:///docs/legacy"
          file_types:
            - "*.doc"
            - "*.docx"
            - "*.pdf"
            - "*.ppt"
            - "*.pptx"
          enable_file_conversion: true
          max_file_size: 20971520  # 20MB
```

### Software Development

```yaml
global:
  qdrant:
    url: "http://localhost:6333"
    collection_name: "dev-docs"
  llm:
    provider: "openai"
    base_url: "https://api.openai.com/v1"
    api_key: "${LLM_API_KEY}"
    models:
      embeddings: "text-embedding-3-small"
      chat: "gpt-4o-mini"
    embeddings:
      vector_size: 1536
projects:
  development:
    sources:
      localfile:
        # Source code
        source-code:
          base_url: "file:///projects/src"
          file_types:
            - "*.py"
            - "*.js"
            - "*.ts"
            - "*.java"
            - "*.cpp"
            - "*.h"
            - "*.md"
            - "*.rst"
          exclude_paths:
            - "**/node_modules/**"
            - "**/__pycache__/**"
            - "**/build/**"
            - "**/dist/**"
            - "**/.git/**"
        # Configuration files
        config-files:
          base_url: "file:///projects/config"
          file_types:
            - "*.yaml"
            - "*.yml"
            - "*.json"
            - "*.toml"
            - "*.ini"
            - "*.conf"
```

### Personal Knowledge Base

```yaml
global:
  qdrant:
    url: "http://localhost:6333"
    collection_name: "personal-knowledge"
  llm:
    provider: "openai"
    base_url: "https://api.openai.com/v1"
    api_key: "${LLM_API_KEY}"
    models:
      embeddings: "text-embedding-3-small"
      chat: "gpt-4o-mini"
    embeddings:
      vector_size: 1536
projects:
  personal:
    sources:
      localfile:
        # Notes and writings
        personal-notes:
          base_url: "file:///personal/notes"
          file_types:
            - "*.md"
            - "*.txt"
            - "*.org"
        # Books and references
        personal-library:
          base_url: "file:///personal/library"
          file_types:
            - "*.pdf"
            - "*.epub"
          max_file_size: 104857600  # 100MB (maximum allowed)
          enable_file_conversion: true
```

## 🧪 Testing and Validation

### Initialize and Configure

```bash
# Initialize workspace
qdrant-loader init --workspace .

# Configure the project
qdrant-loader config --workspace .
```

### Validate Configuration

```bash
# Validate project configuration
qdrant-loader config --workspace .

# Check project status
qdrant-loader config --workspace .

# List all projects
qdrant-loader config --workspace .
```

### Process Local Files

```bash
# Process all configured sources
qdrant-loader ingest --workspace .

# Process specific project
qdrant-loader ingest --workspace . --project my-project

# Process with verbose logging
qdrant-loader ingest --workspace . --log-level debug
```

## 🔧 Troubleshooting

### Common Issues

#### Permission Errors

**Problem**: `Permission denied` or `Access denied`
**Solutions**:

```bash
# Check file permissions
ls -la /path/to/files
# Fix permissions if needed
chmod -R 755 /path/to/files
# Check if running user has access
sudo -u qdrant-user ls /path/to/files
```

#### Large File Processing

**Problem**: Files are too large or processing is slow
**Solutions**:

```yaml
projects:
  my-project:
    sources:
      localfile:
        my-docs:
          base_url: "file:///large_files"
          # Increase size limits
          max_file_size: 104857600  # 100MB (maximum allowed)
          # Skip very large files
          exclude_paths:
            - "**/*.iso"
            - "**/*.dmg"
            - "**/*.vm*"
```

#### File Type Issues

**Problem**: Files not being processed
**Solutions**:

```yaml
projects:
  my-project:
    sources:
      localfile:
        my-docs:
          base_url: "file:///documents"
          # Ensure file types are specified
          file_types:
            - "*.pdf"
            - "*.docx"
            - "*.txt"
            - "*.md"
          # Enable file conversion for additional formats
          enable_file_conversion: true
```

#### Path Issues

**Problem**: Files not found or incorrect paths
**Solutions**:

```yaml
projects:
  my-project:
    sources:
      localfile:
        my-docs:
          # Use absolute path with file:// prefix
          base_url: "file:///absolute/path/to/documents"
          # Include all files recursively
          include_paths:
            - "**"
          # Check exclude patterns
          exclude_paths:
            - "**/.*"  # Hidden files
            - "**/~*"  # Temporary files
```

### Debugging Commands

```bash
# Check file system access
find /path/to/files -type f -name "*.pdf" | head -10

# Test file processing manually
file /path/to/test.pdf
head -100 /path/to/test.txt

# Check disk space
df -h /path/to/files

# Monitor processing with verbose logging
qdrant-loader ingest --workspace . --log-level debug
```

## 📊 Monitoring and Performance

### Check Processing Status

```bash
# Check project status
qdrant-loader config --workspace .

# Check specific project
qdrant-loader config --workspace . --project-id my-project

# List all projects
qdrant-loader config --workspace .
```

### Performance Optimization

Monitor these aspects for local file processing:

- **Files processed per minute** - Processing throughput
- **File size distribution** - Understanding data characteristics
- **Error rate** - Percentage of files that failed to process
- **Memory usage** - Peak memory during processing
- **Disk I/O** - Read/write operations per second

## 🔄 Best Practices

### File Organization

1. **Use consistent directory structure** - Organize files logically
2. **Apply meaningful naming conventions** - Use descriptive file names
3. **Separate by content type** - Group similar files together
4. **Archive old content** - Move outdated files to archive directories

### Optimization Best Practices

1. **Filter aggressively** - Only process files you need with specific file_types
2. **Set appropriate size limits** - Avoid processing very large files
3. **Use exclude patterns** - Skip unnecessary directories and files
4. **Enable file conversion selectively** - Only when needed for additional formats

#### Example: Include/Exclude Patterns

```yaml
projects:
  my-project:
    sources:
      localfile:
        my-docs:
          base_url: "file:///documents"
          # Include patterns - be specific
          include_paths:
            - "**/*.pdf"      # All PDFs recursively
            - "docs/**/*.md"  # Markdown in docs folder
            - "reports/2024/**"  # 2024 reports only
          # Exclude patterns - avoid unnecessary files
          exclude_paths:
            - "**/.*"            # Hidden files
            - "**/*.tmp"      # Temporary files
            - "**/*.log"      # Log files
            - "**/node_modules/**"  # Dependencies
            - "**/build/**"   # Build artifacts
            - "**/cache/**"   # Cache directories
```

### Security Considerations

1. **Check file permissions** - Ensure appropriate access controls
2. **Scan for malware** - Verify files are safe before processing
3. **Handle sensitive data** - Be careful with confidential files
4. **Backup important files** - Maintain backups before processing

### Data Quality

1. **Validate file integrity** - Check for corrupted files
2. **Handle encoding properly** - Ensure text files are readable
3. **Remove duplicates** - Avoid processing duplicate content
4. **Update regularly** - Keep file collections current

## 📚 Related Documentation

- **[File Conversion](../file-conversion/)** - Processing different file formats
- **[Configuration Reference](../../configuration/)** - Complete configuration options
- **[Troubleshooting](../../troubleshooting/)** - Common issues and solutions
- **[MCP Server](../mcp-server/)** - Using processed local content with AI tools

---

**Ready to process your local files?** Start with the basic configuration above and customize based on your file types and directory structure.
