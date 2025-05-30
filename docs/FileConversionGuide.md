# File Conversion Support Guide

**Version**: 0.3.1  
**Release Date**: May 30, 2025  
**Updated**: January 2025 - Added timeout and LLM features

## Overview

QDrant Loader v0.3.1 introduces comprehensive file conversion support, enabling automatic processing of PDF, Office documents, images, and 20+ file types. Files are converted to markdown format using Microsoft's MarkItDown library, then processed through the existing chunking and embedding pipeline.

### ✨ New Features (January 2025)

- **⏱️ Conversion Timeout Control**: Configurable timeouts prevent long-running conversions from hanging
- **🤖 AI-Powered Image Descriptions**: LLM integration for intelligent image content extraction
- **🔧 Enhanced Error Handling**: Better timeout and LLM error management

## 🚀 Quick Start

### Enable File Conversion

Add to your `config.yaml`:

```yaml
# Global file conversion settings
global:
  file_conversion:
    max_file_size: 52428800  # 50MB
    conversion_timeout: 300  # 5 minutes - NEW: Prevents hanging conversions
    
    # NEW: AI-powered image descriptions
    markitdown:
      enable_llm_descriptions: false  # Enable for AI image descriptions
      llm_model: "gpt-4o"             # Model for image analysis
      llm_endpoint: "https://api.openai.com/v1"  # LLM API endpoint

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
- **🆕 AI Descriptions**: LLM-powered content analysis when enabled
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
    
    # 🆕 Timeout for conversion operations (seconds)
    conversion_timeout: 300  # 5 minutes default - prevents hanging conversions
    
    # 🆕 MarkItDown specific settings
    markitdown:
      # Enable LLM integration for AI-powered image descriptions
      enable_llm_descriptions: false  # Set to true to enable
      
      # LLM model for image descriptions (when enabled)
      llm_model: "gpt-4o"  # Supports GPT-4o, GPT-4, etc.
      
      # LLM endpoint (when enabled)
      llm_endpoint: "https://api.openai.com/v1"  # OpenAI or compatible API
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

### 🆕 Conversion Timeout Management

Control how long conversions can run before timing out:

```yaml
global:
  file_conversion:
    # Timeout settings for different scenarios
    conversion_timeout: 300   # 5 minutes for most files
    # conversion_timeout: 600   # 10 minutes for large/complex files
    # conversion_timeout: 60    # 1 minute for fast processing
```

**When to adjust timeout:**

- **Increase** for large PDFs, complex Office documents, or slow systems
- **Decrease** for faster processing and early failure detection
- **Monitor logs** to see actual conversion times

### 🆕 AI-Powered Image Processing

Enable intelligent image content extraction using LLMs:

```yaml
global:
  file_conversion:
    markitdown:
      enable_llm_descriptions: true
      llm_model: "gpt-4o"  # Recommended for best image understanding
      llm_endpoint: "https://api.openai.com/v1"
```

**Environment Variables Required**:

```bash
# For OpenAI endpoints
OPENAI_API_KEY=your_openai_api_key

# For custom endpoints
LLM_API_KEY=your_custom_api_key
```

**Supported LLM Endpoints:**

- **OpenAI**: `https://api.openai.com/v1`
- **Azure OpenAI**: `https://your-resource.openai.azure.com/`
- **Custom OpenAI-compatible APIs**: Any endpoint following OpenAI API format

**Image Processing Benefits:**

- **Searchable visual content**: Charts, diagrams, screenshots become searchable
- **Enhanced context**: Better understanding of document visual elements
- **Multimodal extraction**: Combines text and visual information

**Example Output:**

```markdown
# Document with Chart

![Chart Description: A bar chart showing quarterly sales performance from Q1 to Q4 2024. Q1 shows $2.3M, Q2 shows $2.8M, Q3 shows $3.1M, and Q4 shows $3.5M. The chart uses blue bars with a white background and includes a trend line showing steady growth throughout the year.]

The quarterly results demonstrate consistent growth...
```

### Performance Tuning

```yaml
global:
  file_conversion:
    # Increase for larger files (max 100MB recommended)
    max_file_size: 104857600  # 100MB
    
    # 🆕 Adjust timeout based on your needs
    conversion_timeout: 600  # 10 minutes for complex documents
    
    # Future enhancement
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

### 🆕 Enhanced Metadata Tracking

Converted files now include additional metadata:

```json
{
  "conversion_method": "markitdown",
  "original_file_type": "pdf",
  "original_filename": "document.pdf",
  "file_size": 1048576,
  "conversion_time": 2.5,
  "timeout_used": 300,
  "llm_enabled": true,
  "llm_model": "gpt-4o",
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

#### 🆕 Timeout Issues

**Problem**: Large files timeout during conversion
**Solutions**:

1. **Increase timeout**: `conversion_timeout: 600` (10 minutes)
2. **Check file complexity**: Some PDFs/Office docs take longer
3. **Monitor system resources**: CPU/memory constraints
4. **Process files individually**: Test with single files first

```yaml
# For large/complex files
global:
  file_conversion:
    conversion_timeout: 900  # 15 minutes
    max_file_size: 104857600  # 100MB
```

#### 🆕 LLM Integration Issues

**Problem**: LLM features not working
**Solutions**:

1. **Check API key**: Verify `OPENAI_API_KEY` or `LLM_API_KEY`
2. **Test endpoint**: Ensure LLM endpoint is accessible
3. **Verify model**: Check if specified model is available
4. **Check dependencies**: Ensure `openai` library is installed

```bash
# Test LLM connectivity
python -c "
from openai import OpenAI
client = OpenAI()
print('LLM client created successfully')
"
```

#### Memory Issues

**Problem**: High memory usage during conversion
**Solutions**:

1. Reduce `max_file_size`
2. Process files in smaller batches
3. Increase system memory
4. Use file type filtering

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

#### 🆕 "Conversion timeout exceeded"

```yaml
global:
  file_conversion:
    conversion_timeout: 600  # Increase timeout
```

#### 🆕 "OpenAI library required for LLM integration"

```bash
pip install openai>=1.0.0
```

#### 🆕 "LLM API key not found"

```bash
# Set appropriate environment variable
export OPENAI_API_KEY=your_api_key
# or for custom endpoints
export LLM_API_KEY=your_api_key
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
       conversion_timeout: 300  # 🆕 New timeout setting
       
       # 🆕 Optional: Enable LLM features
       markitdown:
         enable_llm_descriptions: false  # Set to true to enable
         llm_model: "gpt-4o"
         llm_endpoint: "https://api.openai.com/v1"
   
   # Enable per connector
   sources:
     your_connector:
       enable_file_conversion: true
   ```

3. **🆕 Install LLM dependencies** (if using LLM features):

   ```bash
   pip install openai>=1.0.0
   ```

4. **Test conversion**:

   ```bash
   # Dry run to test configuration
   qdrant-loader config --validate
   
   # Test with a small dataset
   qdrant-loader ingest --source-type localfile --source test-docs
   ```

### Backward Compatibility

- **File conversion is disabled by default** - no breaking changes
- **🆕 Timeout defaults to 5 minutes** - existing behavior preserved
- **🆕 LLM features are disabled by default** - no impact on existing setups
- **Existing configurations work unchanged**
- **New metadata fields are optional**
- **Performance impact is minimal when disabled**

## 📈 Performance Considerations

### Resource Usage

- **Memory**: ~100-500MB per file during conversion
- **CPU**: Moderate usage during conversion
- **🆕 Timeout overhead**: Minimal signal handling overhead
- **🆕 LLM API calls**: Additional latency when enabled (~1-5 seconds per image)
- **Disk**: Temporary files created and cleaned up
- **Network**: Additional bandwidth for attachment downloads and LLM API calls

### 🆕 Performance Tips

1. **Timeout tuning**: Start with 300s, adjust based on your file types
2. **LLM usage**: Enable only when image descriptions are needed
3. **Batch processing**: Process large document sets during off-peak hours
4. **Resource monitoring**: Monitor CPU/memory usage during conversion

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
