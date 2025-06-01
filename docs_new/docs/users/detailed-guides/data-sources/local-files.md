# Local Files

Connect QDrant Loader to your local file system to index documents, research materials, archives, and any file-based content. This guide covers setup for processing local directories and files.

## 🎯 What Gets Processed

When you configure local file processing, QDrant Loader can handle:

- **Documents** - PDFs, Word docs, PowerPoint, Excel files
- **Text files** - Markdown, plain text, reStructuredText, LaTeX
- **Code files** - Python, JavaScript, Java, C++, and more
- **Data files** - JSON, CSV, XML, YAML configuration files
- **Images** - PNG, JPEG, GIF (with OCR text extraction)
- **Archives** - ZIP, TAR, 7Z files (extracts and processes contents)
- **Audio files** - MP3, WAV (with transcription)
- **Structured data** - Database exports, log files

## 🔧 Setup and Configuration

### Basic Configuration

```yaml
sources:
  local_files:
    - path: "/path/to/documents"
      include_patterns:
        - "**/*.pdf"
        - "**/*.docx"
        - "**/*.md"
        - "**/*.txt"
      exclude_patterns:
        - "**/.*"
        - "**/node_modules/**"
        - "**/__pycache__/**"
```

### Advanced Configuration

```yaml
sources:
  local_files:
    - path: "/path/to/documents"
      name: "main_documents"  # Optional identifier
      
      # File filtering
      include_patterns:
        - "**/*.pdf"
        - "**/*.docx"
        - "**/*.pptx"
        - "**/*.xlsx"
        - "**/*.md"
        - "**/*.txt"
        - "**/*.py"
        - "**/*.js"
        - "**/*.json"
        - "**/*.yaml"
      exclude_patterns:
        - "**/.*"              # Hidden files
        - "**/node_modules/**" # Dependencies
        - "**/__pycache__/**"  # Python cache
        - "**/build/**"        # Build artifacts
        - "**/dist/**"         # Distribution files
        - "**/*.log"           # Log files
        - "**/*.tmp"           # Temporary files
      
      # Size and age limits
      max_file_size: 52428800    # 50MB
      max_age_days: 365          # Only files modified in last year
      min_file_size: 100         # Skip very small files
      
      # Directory traversal
      max_depth: 10              # Maximum directory depth
      follow_symlinks: false     # Don't follow symbolic links
      include_hidden: false      # Skip hidden files/directories
      
      # File processing options
      extract_metadata: true     # Extract file metadata
      preserve_structure: true   # Maintain directory structure
      include_file_content: true # Process file contents
      
      # Archive handling
      extract_archives: true     # Extract ZIP, TAR, etc.
      max_archive_size: 104857600 # 100MB
      archive_password: null     # Password for encrypted archives
      
      # Performance settings
      max_concurrent_files: 5    # Concurrent file processing
      chunk_size: 1000           # Text chunk size
      enable_caching: true       # Cache processed files
```

### Multiple Directory Sources

```yaml
sources:
  local_files:
    # Research papers
    - path: "/home/user/research/papers"
      name: "research_papers"
      include_patterns: ["**/*.pdf", "**/*.tex"]
      
    # Project documentation
    - path: "/home/user/projects/docs"
      name: "project_docs"
      include_patterns: ["**/*.md", "**/*.rst"]
      
    # Code repositories
    - path: "/home/user/code"
      name: "source_code"
      include_patterns: ["**/*.py", "**/*.js", "**/*.java"]
      exclude_patterns: ["**/node_modules/**", "**/.git/**"]
      
    # Legacy documents
    - path: "/archive/old_docs"
      name: "legacy_docs"
      include_patterns: ["**/*.doc", "**/*.xls", "**/*.ppt"]
      max_age_days: null  # Process all files regardless of age
```

## 🎯 Configuration Options

### Path and Identification

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `path` | string | Directory path to process | Required |
| `name` | string | Identifier for this source | Directory name |
| `description` | string | Human-readable description | None |

### File Filtering

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `include_patterns` | list | Glob patterns for files to include | `["**/*"]` |
| `exclude_patterns` | list | Glob patterns for files to exclude | `[]` |
| `max_file_size` | int | Maximum file size in bytes | `52428800` (50MB) |
| `min_file_size` | int | Minimum file size in bytes | `1` |
| `max_age_days` | int | Only process files modified within N days | None |

### Directory Traversal

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `max_depth` | int | Maximum directory depth to traverse | `10` |
| `follow_symlinks` | bool | Follow symbolic links | `false` |
| `include_hidden` | bool | Include hidden files/directories | `false` |
| `case_sensitive` | bool | Case-sensitive pattern matching | `true` |

### Processing Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `extract_metadata` | bool | Extract file metadata | `true` |
| `preserve_structure` | bool | Maintain directory structure | `true` |
| `include_file_content` | bool | Process file contents | `true` |
| `detect_encoding` | bool | Auto-detect text encoding | `true` |

### Archive Handling

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `extract_archives` | bool | Extract and process archive contents | `true` |
| `max_archive_size` | int | Maximum archive size to process | `104857600` (100MB) |
| `archive_password` | string | Password for encrypted archives | None |
| `archive_formats` | list | Archive formats to process | `["zip", "tar", "gz", "7z"]` |

### Performance Settings

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `max_concurrent_files` | int | Concurrent file processing | `5` |
| `chunk_size` | int | Text chunk size for processing | `1000` |
| `enable_caching` | bool | Cache processed files | `true` |
| `cache_ttl_hours` | int | Cache time-to-live in hours | `24` |

## 🚀 Usage Examples

### Research Team

```yaml
sources:
  local_files:
    # Research papers and publications
    - path: "/research/papers"
      name: "research_papers"
      include_patterns:
        - "**/*.pdf"
        - "**/*.tex"
        - "**/*.bib"
        - "**/*.md"
      max_file_size: 104857600  # 100MB for large papers
      
    # Datasets and data files
    - path: "/research/datasets"
      name: "research_data"
      include_patterns:
        - "**/*.csv"
        - "**/*.json"
        - "**/*.xml"
        - "**/*.xlsx"
      exclude_patterns:
        - "**/raw/**"      # Skip raw data
        - "**/temp/**"     # Skip temporary files
      
    # Analysis notebooks
    - path: "/research/notebooks"
      name: "analysis_notebooks"
      include_patterns:
        - "**/*.ipynb"
        - "**/*.py"
        - "**/*.r"
        - "**/*.md"
```

### Documentation Team

```yaml
sources:
  local_files:
    # Main documentation
    - path: "/docs/content"
      name: "documentation"
      include_patterns:
        - "**/*.md"
        - "**/*.rst"
        - "**/*.txt"
        - "**/*.adoc"
      preserve_structure: true
      
    # Legacy documents
    - path: "/docs/legacy"
      name: "legacy_docs"
      include_patterns:
        - "**/*.doc"
        - "**/*.docx"
        - "**/*.pdf"
        - "**/*.ppt"
        - "**/*.pptx"
      extract_archives: true
      
    # Images and diagrams
    - path: "/docs/images"
      name: "documentation_images"
      include_patterns:
        - "**/*.png"
        - "**/*.jpg"
        - "**/*.svg"
        - "**/*.drawio"
      max_file_size: 20971520  # 20MB for images
```

### Software Development

```yaml
sources:
  local_files:
    # Source code
    - path: "/projects/src"
      name: "source_code"
      include_patterns:
        - "**/*.py"
        - "**/*.js"
        - "**/*.ts"
        - "**/*.java"
        - "**/*.cpp"
        - "**/*.h"
        - "**/*.md"
        - "**/*.rst"
      exclude_patterns:
        - "**/node_modules/**"
        - "**/__pycache__/**"
        - "**/build/**"
        - "**/dist/**"
        - "**/.git/**"
      
    # Configuration files
    - path: "/projects/config"
      name: "configuration"
      include_patterns:
        - "**/*.yaml"
        - "**/*.yml"
        - "**/*.json"
        - "**/*.toml"
        - "**/*.ini"
        - "**/*.conf"
      
    # Documentation and specs
    - path: "/projects/docs"
      name: "project_docs"
      include_patterns:
        - "**/*.md"
        - "**/*.rst"
        - "**/*.txt"
        - "**/*.pdf"
```

### Personal Knowledge Base

```yaml
sources:
  local_files:
    # Notes and writings
    - path: "/personal/notes"
      name: "personal_notes"
      include_patterns:
        - "**/*.md"
        - "**/*.txt"
        - "**/*.org"
        - "**/*.tex"
      preserve_structure: true
      
    # Books and references
    - path: "/personal/library"
      name: "personal_library"
      include_patterns:
        - "**/*.pdf"
        - "**/*.epub"
        - "**/*.mobi"
      max_file_size: 209715200  # 200MB for large books
      
    # Archives and backups
    - path: "/personal/archives"
      name: "personal_archives"
      include_patterns:
        - "**/*.zip"
        - "**/*.tar.gz"
        - "**/*.7z"
      extract_archives: true
      max_archive_size: 524288000  # 500MB
```

## 🔍 Advanced Features

### Metadata Extraction

```yaml
sources:
  local_files:
    - path: "/documents"
      extract_metadata: true
      metadata_fields:
        - "author"
        - "title"
        - "creation_date"
        - "modification_date"
        - "file_size"
        - "mime_type"
        - "encoding"
      
      # Custom metadata extraction
      custom_metadata:
        project: "extract_from_path"  # Extract project from path
        category: "infer_from_content"  # Infer category from content
```

### Content Processing

```yaml
sources:
  local_files:
    - path: "/documents"
      # Text processing options
      normalize_text: true
      remove_formatting: false
      extract_tables: true
      extract_images: true
      
      # Language detection
      detect_language: true
      language_threshold: 0.8
      
      # OCR for images
      enable_ocr: true
      ocr_languages: ["eng", "fra", "deu"]
```

### Archive Processing

```yaml
sources:
  local_files:
    - path: "/archives"
      extract_archives: true
      
      # Archive-specific settings
      archive_formats: ["zip", "tar", "gz", "bz2", "xz", "7z"]
      max_archive_depth: 3  # Nested archive levels
      preserve_archive_structure: true
      
      # Password-protected archives
      archive_passwords:
        "sensitive.zip": "password123"
        "backup_*.7z": "backup_password"
```

### Performance Optimization

```yaml
sources:
  local_files:
    - path: "/large_dataset"
      # Parallel processing
      max_concurrent_files: 10
      batch_size: 100
      
      # Memory management
      max_memory_usage: 2147483648  # 2GB
      stream_large_files: true
      
      # Caching
      enable_caching: true
      cache_directory: "/tmp/qdrant_cache"
      cache_ttl_hours: 48
      
      # Progress tracking
      show_progress: true
      progress_interval: 100
```

## 🧪 Testing and Validation

### Test Local File Processing

```bash
# Test local file access
qdrant-loader --workspace . test-connections --sources local_files

# Validate local file configuration
qdrant-loader --workspace . validate --sources local_files

# List files that would be processed
qdrant-loader --workspace . list-files --sources local_files

# Dry run to see processing plan
qdrant-loader --workspace . --dry-run ingest --sources local_files

# Process specific directory
qdrant-loader --workspace . ingest --sources local_files --path "/specific/path"
```

### Debug File Processing

```bash
# Enable verbose logging
qdrant-loader --workspace . --verbose ingest --sources local_files

# Process single file for testing
qdrant-loader --workspace . process-file --file "/path/to/test.pdf"

# Check file processing status
qdrant-loader --workspace . status --sources local_files --detailed
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
sources:
  local_files:
    - path: "/large_files"
      # Increase size limits
      max_file_size: 209715200  # 200MB
      
      # Optimize processing
      max_concurrent_files: 2
      stream_large_files: true
      
      # Skip very large files
      exclude_patterns:
        - "**/*.iso"
        - "**/*.dmg"
        - "**/*.vm*"
```

#### Encoding Issues

**Problem**: Text files with encoding errors

**Solutions**:

```yaml
sources:
  local_files:
    - path: "/text_files"
      # Enable encoding detection
      detect_encoding: true
      fallback_encoding: "utf-8"
      
      # Handle encoding errors
      encoding_errors: "replace"  # or "ignore"
```

#### Archive Processing Issues

**Problem**: Archives fail to extract or process

**Solutions**:

```yaml
sources:
  local_files:
    - path: "/archives"
      # Limit archive processing
      max_archive_size: 52428800  # 50MB
      max_archive_depth: 2
      
      # Skip problematic archives
      exclude_patterns:
        - "**/*.rar"  # If RAR support not available
        - "**/*.dmg"  # macOS disk images
```

#### Memory Issues

**Problem**: High memory usage or out-of-memory errors

**Solutions**:

```yaml
sources:
  local_files:
    - path: "/large_dataset"
      # Reduce concurrent processing
      max_concurrent_files: 2
      
      # Enable streaming for large files
      stream_large_files: true
      max_memory_usage: 1073741824  # 1GB
      
      # Process in smaller batches
      batch_size: 50
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

# Monitor processing
tail -f /var/log/qdrant-loader.log
```

## 📊 Monitoring and Metrics

### Processing Statistics

```bash
# View local file processing statistics
qdrant-loader --workspace . stats --sources local_files

# Check directory-specific statistics
qdrant-loader --workspace . stats --sources local_files --path "/specific/path"

# Monitor processing progress
qdrant-loader --workspace . status --sources local_files --watch
```

### Performance Metrics

Monitor these metrics for local file processing:

- **Files processed per minute** - Processing throughput
- **File size distribution** - Understanding data characteristics
- **Error rate** - Percentage of files that failed to process
- **Memory usage** - Peak memory during processing
- **Disk I/O** - Read/write operations per second
- **Cache hit rate** - Effectiveness of file caching

## 🔄 Best Practices

### File Organization

1. **Use consistent directory structure** - Organize files logically
2. **Apply meaningful naming conventions** - Use descriptive file names
3. **Separate by content type** - Group similar files together
4. **Archive old content** - Move outdated files to archive directories

### Performance Optimization

1. **Filter aggressively** - Only process files you need
2. **Set appropriate size limits** - Avoid processing very large files
3. **Use caching** - Enable caching for repeated processing
4. **Monitor disk space** - Ensure adequate storage for processing

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
