# File Conversion

QDrant Loader supports comprehensive file conversion to extract text content from 20+ file formats. This guide covers supported formats, conversion processes, and optimization strategies.

## 🎯 Supported File Formats

QDrant Loader uses Microsoft's MarkItDown library and additional processors to handle a wide variety of file formats:

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
| **RAR** | `.rar` | RAR archives | Extract and process contents |

## ⚙️ Configuration

### Basic File Conversion Setup

```yaml
# Global file conversion settings
enable_file_conversion: true
conversion_timeout: 300  # 5 minutes per file
max_file_size: 52428800  # 50MB

# OCR settings for images
ocr:
  enabled: true
  languages: ["eng"]  # English
  confidence_threshold: 60

# Audio transcription settings
audio_transcription:
  enabled: true
  language: "en"
  model: "base"  # whisper model size
```

### Advanced Configuration

```yaml
file_conversion:
  # General settings
  enabled: true
  timeout: 300
  max_file_size: 104857600  # 100MB
  preserve_formatting: true
  extract_metadata: true
  
  # Format-specific settings
  pdf:
    extract_images: true
    ocr_images: true
    extract_tables: true
    password_protected: true
    passwords: ["password123", "default"]
  
  office:
    extract_images: true
    extract_tables: true
    include_comments: true
    include_track_changes: false
  
  images:
    ocr_enabled: true
    ocr_languages: ["eng", "fra", "deu"]
    confidence_threshold: 70
    preprocess_images: true
    dpi: 300
  
  audio:
    transcription_enabled: true
    language: "auto"  # Auto-detect language
    model_size: "base"  # tiny, base, small, medium, large
    chunk_duration: 30  # seconds
    
  archives:
    extract_nested: true
    max_depth: 3
    password_protected: true
    passwords: ["archive123", "backup"]
    
  text:
    encoding_detection: true
    fallback_encoding: "utf-8"
    normalize_whitespace: true
```

### Source-Specific Configuration

```yaml
sources:
  local_files:
    - path: "/documents"
      # Override global conversion settings
      file_conversion:
        pdf:
          extract_images: false  # Skip image extraction for performance
        images:
          ocr_enabled: false     # Skip OCR for this source
  
  confluence:
    - url: "${CONFLUENCE_URL}"
      # Enable attachment conversion
      include_attachments: true
      file_conversion:
        office:
          include_comments: true
          extract_tables: true
```

## 🔧 Conversion Process

### How File Conversion Works

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    File     │───▶│   Format    │───▶│ Conversion  │───▶│    Text     │
│  Detection  │    │ Detection   │    │  Process    │    │  Content    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ MIME Type   │    │ Extension   │    │ MarkItDown  │    │ Structured  │
│ Detection   │    │ Mapping     │    │ + Custom    │    │ Output      │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Conversion Pipeline

1. **File Detection**
   - MIME type detection
   - Extension analysis
   - Content validation

2. **Format-Specific Processing**
   - PDF: Text extraction + OCR for images
   - Office: Document structure + embedded content
   - Images: OCR text extraction
   - Audio: Speech-to-text transcription
   - Archives: Extraction + recursive processing

3. **Content Extraction**
   - Main text content
   - Metadata (author, creation date, etc.)
   - Structured data (tables, lists)
   - Embedded objects (images, charts)

4. **Post-Processing**
   - Text normalization
   - Formatting preservation
   - Chunking for vector storage

## 🚀 Usage Examples

### Document Processing

```yaml
sources:
  local_files:
    - path: "/documents/reports"
      include_patterns: ["**/*.pdf", "**/*.docx"]
      file_conversion:
        pdf:
          extract_images: true
          ocr_images: true
          extract_tables: true
        office:
          extract_tables: true
          include_comments: false
```

### Research Papers and Academic Content

```yaml
sources:
  local_files:
    - path: "/research/papers"
      include_patterns: ["**/*.pdf", "**/*.tex"]
      file_conversion:
        pdf:
          extract_images: true
          ocr_images: true
          extract_tables: true
          # Handle password-protected papers
          passwords: ["research2024", "conference"]
        text:
          # Handle LaTeX files
          preserve_formatting: true
```

### Multimedia Content

```yaml
sources:
  local_files:
    - path: "/media/presentations"
      include_patterns: ["**/*.pptx", "**/*.mp3", "**/*.png"]
      file_conversion:
        office:
          extract_images: true
          include_speaker_notes: true
        audio:
          transcription_enabled: true
          language: "en"
          model_size: "medium"
        images:
          ocr_enabled: true
          ocr_languages: ["eng"]
```

### Archive Processing

```yaml
sources:
  local_files:
    - path: "/archives/backups"
      include_patterns: ["**/*.zip", "**/*.tar.gz"]
      file_conversion:
        archives:
          extract_nested: true
          max_depth: 5
          password_protected: true
          passwords: ["backup123", "archive2024"]
          # Process extracted files
          process_extracted: true
```

### Data Files

```yaml
sources:
  local_files:
    - path: "/data/exports"
      include_patterns: ["**/*.json", "**/*.csv", "**/*.xml"]
      file_conversion:
        data:
          preserve_structure: true
          extract_schema: true
          max_records: 10000  # Limit for large datasets
```

## 🔍 Advanced Features

### OCR Configuration

```yaml
file_conversion:
  images:
    ocr_enabled: true
    
    # Language support
    ocr_languages: ["eng", "fra", "deu", "spa"]
    
    # Quality settings
    confidence_threshold: 70
    dpi: 300
    preprocess_images: true
    
    # Image preprocessing
    preprocessing:
      - "deskew"      # Correct skewed text
      - "denoise"     # Remove noise
      - "enhance"     # Enhance contrast
      - "binarize"    # Convert to black/white
    
    # OCR engine settings
    engine: "tesseract"  # or "easyocr"
    psm: 6  # Page segmentation mode
```

### Audio Transcription

```yaml
file_conversion:
  audio:
    transcription_enabled: true
    
    # Whisper model configuration
    model_size: "base"  # tiny, base, small, medium, large
    language: "auto"    # Auto-detect or specify: "en", "fr", etc.
    
    # Processing settings
    chunk_duration: 30  # seconds
    overlap_duration: 5 # seconds
    
    # Quality settings
    temperature: 0.0    # Deterministic output
    beam_size: 5        # Beam search size
    
    # Output format
    include_timestamps: true
    include_confidence: true
```

### Password-Protected Files

```yaml
file_conversion:
  # Global password list
  passwords:
    - "password123"
    - "company2024"
    - "default"
  
  # Format-specific passwords
  pdf:
    passwords:
      - "pdf_password"
      - "document123"
  
  archives:
    passwords:
      - "archive_password"
      - "backup2024"
  
  # File-specific passwords
  password_mapping:
    "sensitive.pdf": "secret123"
    "backup_*.zip": "backup_password"
```

### Custom Conversion Rules

```yaml
file_conversion:
  custom_rules:
    # Skip conversion for specific files
    skip_patterns:
      - "**/*.log"
      - "**/temp/**"
      - "**/*.cache"
    
    # Force specific converters
    force_converters:
      "**/*.data": "text"  # Treat .data files as text
      "**/*.config": "yaml"  # Treat .config as YAML
    
    # Size limits per format
    size_limits:
      pdf: 104857600      # 100MB
      audio: 524288000    # 500MB
      images: 20971520    # 20MB
```

## 🧪 Testing and Validation

### Test File Conversion

```bash
# Test conversion for specific file types
qdrant-loader --workspace . test-conversion --file-type pdf

# Test single file conversion
qdrant-loader --workspace . convert-file --file "/path/to/test.pdf"

# Validate conversion configuration
qdrant-loader --workspace . validate-conversion

# Check supported formats
qdrant-loader --workspace . list-formats
```

### Debug Conversion Issues

```bash
# Enable verbose conversion logging
qdrant-loader --workspace . --verbose ingest --debug-conversion

# Test OCR on specific image
qdrant-loader --workspace . test-ocr --file "/path/to/image.png"

# Test audio transcription
qdrant-loader --workspace . test-transcription --file "/path/to/audio.mp3"
```

## 🔧 Troubleshooting

### Common Issues

#### PDF Conversion Problems

**Problem**: PDFs not converting or missing text

**Solutions**:

```yaml
file_conversion:
  pdf:
    # Try different extraction methods
    extraction_method: "auto"  # auto, pdfplumber, pymupdf, pdfminer
    
    # Enable OCR for scanned PDFs
    ocr_images: true
    fallback_to_ocr: true
    
    # Handle password protection
    password_protected: true
    passwords: ["", "password", "default"]
```

#### OCR Issues

**Problem**: Poor OCR quality or missing text from images

**Solutions**:

```yaml
file_conversion:
  images:
    # Improve OCR quality
    dpi: 300
    confidence_threshold: 60  # Lower threshold
    preprocess_images: true
    
    # Try different languages
    ocr_languages: ["eng", "fra", "deu"]
    
    # Use different OCR engine
    engine: "easyocr"  # Alternative to tesseract
```

#### Audio Transcription Problems

**Problem**: Audio files not transcribing or poor quality

**Solutions**:

```yaml
file_conversion:
  audio:
    # Use larger model for better accuracy
    model_size: "medium"  # or "large"
    
    # Specify language if known
    language: "en"  # Instead of "auto"
    
    # Adjust chunk settings
    chunk_duration: 60
    overlap_duration: 10
    
    # Preprocessing
    normalize_audio: true
    remove_silence: true
```

#### Memory Issues

**Problem**: Large files causing memory problems

**Solutions**:

```yaml
file_conversion:
  # Reduce memory usage
  max_file_size: 20971520  # 20MB limit
  
  # Process in chunks
  chunk_processing: true
  chunk_size: 1048576  # 1MB chunks
  
  # Streaming for large files
  stream_large_files: true
  
  # Limit concurrent conversions
  max_concurrent_conversions: 2
```

#### Archive Extraction Issues

**Problem**: Archives not extracting or processing

**Solutions**:

```yaml
file_conversion:
  archives:
    # Limit extraction depth
    max_depth: 2
    
    # Skip large archives
    max_archive_size: 104857600  # 100MB
    
    # Handle password protection
    password_protected: true
    passwords: ["", "password", "archive"]
    
    # Skip problematic formats
    skip_formats: ["rar"]  # If RAR support unavailable
```

### Debugging Commands

```bash
# Check file format detection
file /path/to/unknown_file

# Test PDF extraction manually
python -c "import markitdown; print(markitdown.MarkItDown().convert('/path/to/file.pdf').text_content)"

# Check OCR installation
tesseract --version
tesseract --list-langs

# Test audio transcription
whisper --help
```

## 📊 Monitoring and Metrics

### Conversion Statistics

```bash
# View conversion statistics
qdrant-loader --workspace . stats --conversion

# Check format-specific statistics
qdrant-loader --workspace . stats --conversion --format pdf

# Monitor conversion performance
qdrant-loader --workspace . status --conversion --watch
```

### Performance Metrics

Monitor these metrics for file conversion:

- **Conversion success rate** - Percentage of files successfully converted
- **Processing time per format** - Average time to convert each format
- **Memory usage** - Peak memory during conversion
- **OCR accuracy** - Quality of text extraction from images
- **File size distribution** - Understanding of content characteristics

## 🔄 Best Practices

### Performance Optimization

1. **Set appropriate size limits** - Avoid processing very large files
2. **Use format-specific settings** - Optimize for each file type
3. **Enable caching** - Cache conversion results
4. **Process in parallel** - Use concurrent conversion when possible

### Quality Assurance

1. **Validate extracted content** - Check conversion quality
2. **Use appropriate OCR settings** - Optimize for your content
3. **Handle encoding properly** - Ensure text files are readable
4. **Test with sample files** - Validate configuration with known files

### Security Considerations

1. **Scan files for malware** - Verify files are safe before processing
2. **Handle passwords securely** - Store passwords in environment variables
3. **Limit file sizes** - Prevent resource exhaustion
4. **Validate file types** - Ensure files match expected formats

### Resource Management

1. **Monitor memory usage** - Watch for memory leaks
2. **Set processing timeouts** - Prevent hanging conversions
3. **Limit concurrent operations** - Avoid overwhelming the system
4. **Clean up temporary files** - Remove intermediate files

## 📚 Related Documentation

- **[Data Sources](../data-sources/)** - Configuring data sources that use file conversion
- **[Configuration Reference](../../configuration/)** - Complete configuration options
- **[Troubleshooting](../../troubleshooting/)** - Common issues and solutions
- **[Performance Tuning](../../../developers/deployment/performance-tuning.md)** - Optimization strategies

---

**Ready to process your files?** Start with the basic configuration above and customize based on your specific file types and quality requirements.
