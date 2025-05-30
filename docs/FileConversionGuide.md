# File Conversion Support Guide

**Version**: 0.3.1  
**Release Date**: May 30, 2025

## Overview

QDrant Loader v0.3.1 introduces comprehensive file conversion support, enabling automatic processing of PDF, Office documents, images, and 20+ file types. Files are converted to markdown format using Microsoft's MarkItDown library, then processed through the existing chunking and embedding pipeline.

## 🚀 Quick Start

### Enable File Conversion

Add to your `config.yaml`:

```yaml
# Global file conversion settings
global:
  file_conversion:
    max_file_size: 52428800  # 50MB
    conversion_timeout: 300  # 5 minutes

# Enable per connector
sources:
  git:
    my-repo:
      enable_file_conversion: true
      # ... other settings
  
  confluence:
    my-space:
      enable_file_conversion: true
      download_attachments: true  # Also process attachments
      # ... other settings
```

### Basic Usage

```bash
# Convert files during ingestion
qdrant-loader ingest

# Check conversion statistics
qdrant-loader status
```

## 📁 Supported File Types

### Documents

- **PDF**: Text extraction with layout preservation
- **Microsoft Office**: Word (.docx), PowerPoint (.pptx), Excel (.xlsx)
- **OpenDocument**: ODT, ODS, ODP formats

### Images

- **Formats**: PNG, JPEG, GIF, BMP, TIFF, WebP
- **OCR Support**: Optional text extraction from images
- **Metadata**: EXIF data preservation

### Data Formats

- **Structured**: JSON, CSV, XML, YAML
- **Tabular**: Excel spreadsheets with multiple sheets
- **Configuration**: INI, TOML files

### Archives

- **ZIP Files**: Automatic extraction and processing of contents
- **Nested Archives**: Support for archives within archives

### Audio

- **Formats**: MP3, WAV, M4A
- **Transcription**: Automatic speech-to-text conversion
- **Metadata**: Duration, format information

### E-books

- **EPUB**: Chapter extraction and metadata
- **Text Preservation**: Formatting and structure maintained

### Other Formats

- **Markdown**: Enhanced processing (existing files)
- **HTML**: Improved extraction (existing files)
- **Plain Text**: Enhanced metadata extraction

## ⚙️ Configuration

### Global Configuration

```yaml
global:
  file_conversion:
    # Maximum file size for conversion (bytes)
    max_file_size: 52428800  # 50MB default
    
    # Timeout for conversion operations (seconds)
    conversion_timeout: 300  # 5 minutes default
    
    # MarkItDown specific settings
    markitdown:
      # Enable LLM integration for image descriptions
      enable_llm_descriptions: false
      
      # LLM model for image descriptions (when enabled)
      llm_model: "gpt-4o"
      
      # LLM endpoint (when enabled)
      llm_endpoint: "https://api.openai.com/v1"
```

### Per-Connector Configuration

#### Git Repositories

```yaml
sources:
  git:
    my-repo:
      enable_file_conversion: true
      base_url: "https://github.com/user/repo.git"
      # Files are automatically detected and converted
      # No additional configuration needed
```

#### Confluence Spaces

```yaml
sources:
  confluence:
    my-space:
      enable_file_conversion: true
      download_attachments: true  # Required for attachment conversion
      base_url: "https://company.atlassian.net"
      space_key: "DOCS"
      # Attachments are automatically downloaded and converted
```

#### JIRA Projects

```yaml
sources:
  jira:
    my-project:
      enable_file_conversion: true
      download_attachments: true  # Required for attachment conversion
      base_url: "https://company.atlassian.net"
      project_key: "PROJ"
      # Issue attachments are automatically processed
```

#### Local Files

```yaml
sources:
  localfile:
    my-docs:
      enable_file_conversion: true
      base_url: "file:///path/to/documents"
      # All supported file types in the directory are converted
```

#### Public Documentation

```yaml
sources:
  publicdocs:
    my-docs:
      enable_file_conversion: true
      download_attachments: true  # Required for attachment conversion
      base_url: "https://docs.example.com"
      # Linked files are automatically downloaded and converted
```

## 🔧 Advanced Configuration

### Image Processing with LLM

Enable AI-powered image descriptions:

```yaml
global:
  file_conversion:
    markitdown:
      enable_llm_descriptions: true
      llm_model: "gpt-4o"
      llm_endpoint: "https://api.openai.com/v1"
```

**Environment Variables Required**:

```bash
OPENAI_API_KEY=your_openai_api_key
```

### Performance Tuning

```yaml
global:
  file_conversion:
    # Increase for larger files (max 100MB recommended)
    max_file_size: 104857600  # 100MB
    
    # Increase for complex documents
    conversion_timeout: 600  # 10 minutes
    
    # Batch processing (future enhancement)
    batch_size: 10
```

### File Type Filtering

While file conversion is automatic, you can control which files are processed using existing connector filters:

```yaml
sources:
  git:
    my-repo:
      enable_file_conversion: true
      # Include specific file types
      file_types: ["*.pdf", "*.docx", "*.xlsx", "*.png"]
      # Exclude certain paths
      exclude_paths: ["archive/**", "temp/**"]
```

## 📊 Monitoring and Metrics

### Conversion Statistics

Check conversion metrics:

```bash
# View overall status including conversion stats
qdrant-loader status

# Detailed metrics (if available)
qdrant-loader metrics --conversion
```

### Logging

Enable detailed conversion logging:

```bash
# Debug level logging
qdrant-loader ingest --log-level DEBUG

# Focus on conversion operations
export LOG_FILTER=file_conversion
qdrant-loader ingest
```

### Metadata Tracking

Converted files include additional metadata:

```json
{
  "conversion_method": "markitdown",
  "original_file_type": "pdf",
  "original_filename": "document.pdf",
  "file_size": 1048576,
  "conversion_time": 2.5,
  "is_attachment": false,
  "parent_document_id": null
}
```

## 🔍 Troubleshooting

### Common Issues

#### Conversion Failures

**Problem**: Files fail to convert
**Solutions**:

1. Check file size limits
2. Verify file format is supported
3. Increase timeout for large files
4. Check MarkItDown dependency installation

```bash
# Verify MarkItDown installation
pip install "markitdown[all]>=0.1.2"

# Test conversion manually
python -c "from markitdown import MarkItDown; print('MarkItDown available')"
```

#### Memory Issues

**Problem**: High memory usage during conversion
**Solutions**:

1. Reduce `max_file_size`
2. Process files in smaller batches
3. Increase system memory
4. Use file type filtering

#### Timeout Issues

**Problem**: Large files timeout during conversion
**Solutions**:

1. Increase `conversion_timeout`
2. Reduce file size limits
3. Check system performance
4. Process files individually

### Error Messages

#### "MarkItDown not available"

```bash
pip install "markitdown[all]>=0.1.2"
```

#### "File too large for conversion"

```yaml
global:
  file_conversion:
    max_file_size: 104857600  # Increase limit
```

#### "Conversion timeout exceeded"

```yaml
global:
  file_conversion:
    conversion_timeout: 600  # Increase timeout
```

### Debug Mode

Enable comprehensive debugging:

```bash
# Full debug output
qdrant-loader ingest --log-level DEBUG --verbose

# Save debug logs
qdrant-loader ingest --log-level DEBUG > conversion.log 2>&1
```

## 🚀 Migration Guide

### Upgrading from v0.3.0

1. **Update package**:

   ```bash
   pip install --upgrade qdrant-loader
   ```

2. **Update configuration** (optional):

   ```yaml
   # Add to existing config.yaml
   global:
     file_conversion:
       max_file_size: 52428800
       conversion_timeout: 300
   
   # Enable per connector
   sources:
     your_connector:
       enable_file_conversion: true
   ```

3. **Test conversion**:

   ```bash
   # Dry run to test configuration
   qdrant-loader config --validate
   
   # Test with a small dataset
   qdrant-loader ingest --source-type localfile --source test-docs
   ```

### Backward Compatibility

- **File conversion is disabled by default** - no breaking changes
- **Existing configurations work unchanged**
- **New metadata fields are optional**
- **Performance impact is minimal when disabled**

## 📈 Performance Considerations

### Resource Usage

- **Memory**: ~100-500MB per file during conversion
- **CPU**: Moderate usage during conversion
- **Disk**: Temporary files created and cleaned up
- **Network**: Additional bandwidth for attachment downloads

### Optimization Tips

1. **File Size Limits**: Set appropriate limits for your use case
2. **Selective Conversion**: Use file type filters
3. **Batch Processing**: Process large datasets in smaller batches
4. **Monitoring**: Watch system resources during large conversions

### Scaling Recommendations

- **Small datasets** (<1000 files): Default settings work well
- **Medium datasets** (1000-10000 files): Increase timeouts, monitor memory
- **Large datasets** (>10000 files): Consider batch processing, dedicated resources

## 🔮 Future Enhancements

### Planned Features

- **Caching Layer**: Persistent conversion cache to avoid re-processing
- **Parallel Processing**: Multi-threaded conversion for better performance
- **Custom Converters**: Plugin system for custom file type handlers
- **Cloud Storage**: Direct integration with S3, GCS, Azure Blob
- **Advanced OCR**: Enhanced image and PDF text extraction

### Feedback and Requests

We welcome feedback and feature requests:

- [GitHub Issues](https://github.com/martin-papy/qdrant-loader/issues)
- [GitHub Discussions](https://github.com/martin-papy/qdrant-loader/discussions)

## 📚 Related Documentation

- [Main README](../README.md) - Project overview
- [QDrant Loader README](../packages/qdrant-loader/README.md) - Package documentation
- [Configuration Guide](../packages/qdrant-loader/config.template.yaml) - Full configuration reference
- [Contributing Guide](./CONTRIBUTING.md) - Development guidelines
- [Release Notes](../RELEASE_NOTES.md) - Version history

## 🆘 Support

For support with file conversion:

1. **Check this guide** for common solutions
2. **Review logs** with debug mode enabled
3. **Search existing issues** on GitHub
4. **Create a new issue** with detailed information:
   - File types being processed
   - Configuration used
   - Error messages and logs
   - System information

---

**Happy Converting! 📄➡️📝**
