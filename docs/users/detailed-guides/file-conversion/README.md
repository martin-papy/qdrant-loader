# File Conversion

QDrant Loader supports comprehensive file conversion to extract text content from various file formats using Microsoft's MarkItDown library. This guide covers supported formats, configuration, and best practices.

## 🎯 Supported File Formats

QDrant Loader uses Microsoft's MarkItDown library to handle a wide variety of file formats:

### 📄 Document Formats

| Format | Extension | Description | Features |
|--------|-----------|-------------|----------|
| **PDF** | `.pdf` | Portable Document Format | Text extraction, OCR for images, metadata |
| **Word** | `.docx`, `.doc` | Microsoft Word documents | Text, tables, images, metadata |
| **PowerPoint** | `.pptx`, `.ppt` | Microsoft PowerPoint presentations | Slide text, speaker notes, metadata |
| **Excel** | `.xlsx`, `.xls` | Microsoft Excel spreadsheets | Cell data, formulas, sheet names |
| **OpenDocument** | `.odt`, `.ods`, `.odp` | LibreOffice/OpenOffice documents | Text, tables, metadata |

### 📝 Text Formats

| Format | Extension | Description | Features |
|--------|-----------|-------------|----------|
| **Markdown** | `.md`, `.markdown` | Markdown markup | Formatted text, code blocks, tables |
| **reStructuredText** | `.rst` | reStructuredText markup | Formatted text, directives |
| **Plain Text** | `.txt` | Plain text files | Raw text content |
| **Rich Text** | `.rtf` | Rich Text Format | Formatted text, basic styling |
| **LaTeX** | `.tex` | LaTeX documents | Mathematical content, structured text |

### 🖼️ Image Formats (with OCR)

| Format | Extension | Description | Features |
|--------|-----------|-------------|----------|
| **JPEG** | `.jpg`, `.jpeg` | JPEG images | OCR text extraction, metadata |
| **PNG** | `.png` | PNG images | OCR text extraction, transparency |
| **GIF** | `.gif` | GIF images | OCR text extraction, animation frames |
| **TIFF** | `.tiff`, `.tif` | TIFF images | OCR text extraction, high quality |
| **BMP** | `.bmp` | Bitmap images | OCR text extraction |

### 🎵 Audio Formats (with Transcription)

| Format | Extension | Description | Features |
|--------|-----------|-------------|----------|
| **MP3** | `.mp3` | MP3 audio | Speech-to-text transcription |
| **WAV** | `.wav` | WAV audio | Speech-to-text transcription |
| **M4A** | `.m4a` | M4A audio | Speech-to-text transcription |
| **FLAC** | `.flac` | FLAC audio | Speech-to-text transcription |

### 📊 Data Formats

| Format | Extension | Description | Features |
|--------|-----------|-------------|----------|
| **JSON** | `.json` | JSON data | Structured data extraction |
| **CSV** | `.csv` | Comma-separated values | Tabular data, headers |
| **XML** | `.xml` | XML documents | Structured data, attributes |
| **YAML** | `.yaml`, `.yml` | YAML configuration | Configuration data |
| **TOML** | `.toml` | TOML configuration | Configuration data |

### 📦 Archive Formats

| Format | Extension | Description | Features |
|--------|-----------|-------------|----------|
| **ZIP** | `.zip` | ZIP archives | Extract and process contents |
| **TAR** | `.tar`, `.tar.gz`, `.tgz` | TAR archives | Extract and process contents |
| **7-Zip** | `.7z` | 7-Zip archives | Extract and process contents |

## ⚙️ Configuration

### Global File Conversion Configuration

File conversion is configured globally and applies to all projects and sources that enable it:

```yaml
global_config:
  # File conversion configuration
  file_conversion:
    # Maximum file size for conversion (in bytes)
    max_file_size: 52428800  # 50MB
    
    # Timeout for conversion operations (in seconds)
    conversion_timeout: 300  # 5 minutes
    
    # MarkItDown specific settings
    markitdown:
      # Enable LLM integration for image descriptions
      enable_llm_descriptions: false
      # LLM model for image descriptions (when enabled)
      llm_model: "gpt-4o"
      # LLM endpoint (when enabled)
      llm_endpoint: "https://api.openai.com/v1"
      # API key for LLM service (required when enable_llm_descriptions is True)
      llm_api_key: "${OPENAI_API_KEY}"

projects:
  my-project:
    display_name: "My Project"
    description: "Project with file conversion enabled"

    sources:
      localfile:
        documents:
          base_url: "file:///path/to/documents"
          file_types:
            - "*.pdf"
            - "*.docx"
            - "*.pptx"
            - "*.xlsx"
          max_file_size: 52428800
          # Enable file conversion for this source
          enable_file_conversion: true
```

### Configuration Options

#### Global File Conversion Settings

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `max_file_size` | int | Maximum file size in bytes | `52428800` (50MB) |
| `conversion_timeout` | int | Timeout for conversion operations in seconds | `300` (5 minutes) |

#### MarkItDown Settings

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `enable_llm_descriptions` | bool | Enable LLM integration for image descriptions | `false` |
| `llm_model` | string | LLM model for image descriptions | `gpt-4o` |
| `llm_endpoint` | string | LLM endpoint URL | `https://api.openai.com/v1` |
| `llm_api_key` | string | API key for LLM service | `null` |

#### Source-Level Settings

Each data source can enable or disable file conversion:

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `enable_file_conversion` | bool | Enable file conversion for this source | `false` |

## 🔧 How File Conversion Works

### Conversion Process

```text
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    File     │───▶│   Format    │───▶│ MarkItDown  │───▶│  Markdown   │
│  Detection  │    │ Detection   │    │ Conversion  │    │  Content    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ MIME Type   │    │ Extension   │    │ Text + OCR  │    │ Structured  │
│ Detection   │    │ Mapping     │    │ + Audio     │    │ Text Output │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Processing Pipeline

1. **File Detection**
   - MIME type detection
   - Extension analysis
   - File size validation

2. **Format-Specific Processing**
   - **PDF**: Text extraction + OCR for images
   - **Office Documents**: Document structure + embedded content
   - **Images**: OCR text extraction
   - **Audio**: Speech-to-text transcription
   - **Archives**: Extraction + recursive processing

3. **Content Extraction**
   - Main text content
   - Metadata (author, creation date, etc.)
   - Structured data (tables, lists)
   - Embedded objects (images, charts)

4. **Output Generation**
   - Markdown-formatted text
   - Preserved formatting where possible
   - Ready for chunking and vector storage

## 🚀 Usage Examples

### Basic Document Processing

```yaml
global_config:
  file_conversion:
    max_file_size: 52428800  # 50MB
    conversion_timeout: 300  # 5 minutes
    markitdown:
      enable_llm_descriptions: false

projects:
  documents:
    display_name: "Document Processing"
    description: "Process various document formats"
    
    sources:
      localfile:
        office-docs:
          base_url: "file:///documents/office"
          file_types:
            - "*.pdf"
            - "*.docx"
            - "*.pptx"
            - "*.xlsx"
          enable_file_conversion: true
```

### Research Papers with LLM Enhancement

```yaml
global_config:
  file_conversion:
    max_file_size: 104857600  # 100MB for large papers
    conversion_timeout: 600   # 10 minutes
    markitdown:
      enable_llm_descriptions: true
      llm_model: "gpt-4o"
      llm_endpoint: "https://api.openai.com/v1"
      llm_api_key: "${OPENAI_API_KEY}"

projects:
  research:
    display_name: "Research Papers"
    description: "Academic papers and research documents"
    
    sources:
      localfile:
        papers:
          base_url: "file:///research/papers"
          file_types:
            - "*.pdf"
            - "*.tex"
          enable_file_conversion: true
```

### Multimedia Content Processing

```yaml
global_config:
  file_conversion:
    max_file_size: 52428800
    conversion_timeout: 900  # 15 minutes for audio/video
    markitdown:
      enable_llm_descriptions: true
      llm_model: "gpt-4o"
      llm_api_key: "${OPENAI_API_KEY}"

projects:
  multimedia:
    display_name: "Multimedia Content"
    description: "Audio, images, and presentations"
    
    sources:
      localfile:
        media:
          base_url: "file:///media/content"
          file_types:
            - "*.mp3"
            - "*.wav"
            - "*.png"
            - "*.jpg"
            - "*.pptx"
          enable_file_conversion: true
```

### Confluence with Attachment Processing

```yaml
global_config:
  file_conversion:
    max_file_size: 52428800
    conversion_timeout: 300
    markitdown:
      enable_llm_descriptions: false

projects:
  confluence-docs:
    display_name: "Confluence Documentation"
    description: "Confluence pages and attachments"
    
    sources:
      confluence:
        company-wiki:
          base_url: "${CONFLUENCE_URL}"
          deployment_type: "cloud"
          space_key: "DOCS"
          email: "${CONFLUENCE_EMAIL}"
          token: "${CONFLUENCE_TOKEN}"
          download_attachments: true
          enable_file_conversion: true
```

## 🧪 Testing and Validation

### Test File Conversion

```bash
# Initialize the project
qdrant-loader --workspace . init

# Test ingestion with file conversion enabled
qdrant-loader --workspace . ingest --project my-project

# Check project status
qdrant-loader --workspace . project status --project-id my-project

# Enable debug logging to see conversion details
qdrant-loader --workspace . --log-level DEBUG ingest --project my-project
```

### Validate Configuration

```bash
# Validate project configuration
qdrant-loader --workspace . project validate --project-id my-project

# Check all projects
qdrant-loader --workspace . project list

# View current configuration
qdrant-loader --workspace . config
```

## 🔧 Troubleshooting

### Common Issues

#### File Size Exceeded

**Problem**: Files are too large to process

**Solutions**:

```yaml
global_config:
  file_conversion:
    # Increase size limit
    max_file_size: 104857600  # 100MB
    
    # Or filter at source level
projects:
  my-project:
    sources:
      localfile:
        documents:
          max_file_size: 20971520  # 20MB limit for this source
```

#### Conversion Timeout

**Problem**: Large files timing out during conversion

**Solutions**:

```yaml
global_config:
  file_conversion:
    # Increase timeout
    conversion_timeout: 900  # 15 minutes
```

#### LLM Integration Issues

**Problem**: Image descriptions not working

**Solutions**:

1. **Check API key**:

   ```bash
   echo $OPENAI_API_KEY
   ```

2. **Verify configuration**:

   ```yaml
   global_config:
     file_conversion:
       markitdown:
         enable_llm_descriptions: true
         llm_api_key: "${OPENAI_API_KEY}"
   ```

3. **Test API access**:

   ```bash
   curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models
   ```

#### Memory Issues

**Problem**: Large files causing memory problems

**Solutions**:

```yaml
global_config:
  file_conversion:
    # Reduce file size limits
    max_file_size: 20971520  # 20MB
    
    # Reduce timeout to fail faster
    conversion_timeout: 180  # 3 minutes
```

#### Unsupported File Types

**Problem**: Some files not being processed

**Solutions**:

1. **Check file types in source configuration**:

   ```yaml
   sources:
     localfile:
       documents:
         file_types:
           - "*.pdf"
           - "*.docx"
           - "*.txt"
   ```

2. **Verify MarkItDown support** - Check if the file format is supported by MarkItDown

3. **Enable file conversion**:

   ```yaml
   sources:
     localfile:
       documents:
         enable_file_conversion: true
   ```

### Debugging Commands

```bash
# Check file type detection
file /path/to/unknown_file

# Test MarkItDown manually
python -c "
from markitdown import MarkItDown
md = MarkItDown()
result = md.convert('/path/to/file.pdf')
print(result.text_content[:500])
"

# Check available Python packages
pip list | grep -E "(markitdown|tesseract|whisper)"
```

## 📊 Monitoring and Performance

### Check Processing Status

```bash
# View project status
qdrant-loader --workspace . project status

# Check specific project
qdrant-loader --workspace . project status --project-id my-project

# Monitor with debug logging
qdrant-loader --workspace . --log-level DEBUG ingest --project my-project
```

### Performance Considerations

Monitor these aspects for file conversion:

- **Conversion success rate** - Percentage of files successfully converted
- **Processing time per format** - Average time to convert each format
- **Memory usage** - Peak memory during conversion
- **File size distribution** - Understanding of content characteristics
- **Timeout frequency** - Files that exceed conversion timeout

## 🔄 Best Practices

### Performance Optimization

1. **Set appropriate size limits** - Balance between coverage and performance
2. **Use reasonable timeouts** - Prevent hanging conversions
3. **Monitor memory usage** - Watch for memory leaks during processing
4. **Test with sample files** - Validate configuration with representative files

### Quality Assurance

1. **Validate extracted content** - Check conversion quality with sample files
2. **Handle encoding properly** - Ensure text files are readable
3. **Test different file types** - Verify support for your specific formats
4. **Monitor conversion logs** - Watch for errors and warnings

### Security Considerations

1. **Scan files for malware** - Verify files are safe before processing
2. **Limit file sizes** - Prevent resource exhaustion attacks
3. **Validate file types** - Ensure files match expected formats
4. **Secure API keys** - Store LLM API keys in environment variables

### Resource Management

1. **Monitor disk space** - Temporary files during conversion
2. **Set processing timeouts** - Prevent hanging conversions
3. **Clean up temporary files** - Remove intermediate files after processing
4. **Limit concurrent operations** - Avoid overwhelming the system

## 📚 Related Documentation

- **[Data Sources](../data-sources/)** - Configuring data sources that use file conversion
- **[Configuration Reference](../../configuration/)** - Complete configuration options
- **[Troubleshooting](../../troubleshooting/)** - Common issues and solutions
- **[Local Files](../data-sources/local-files.md)** - Processing local files with conversion
- **[Confluence](../data-sources/confluence.md)** - Processing Confluence attachments

---

**Ready to process your files?** Start with the basic configuration above and customize based on your specific file types and requirements.
