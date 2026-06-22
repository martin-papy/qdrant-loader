# File Conversion

QDrant Loader extracts text content from a wide range of binary and document formats so they can be chunked, embedded, and searched. Conversion is performed by one of two engines — **MarkItDown** (the default) or **Docling** — selected with `file_conversion.engine`. This guide covers the engines, supported formats, configuration, and best practices.

## 🔀 Conversion Engines

Two conversion engines are available; choose one per deployment with `global.file_conversion.engine`:

| Engine         | Value                  | When to use                                                                                                                                                                                                          |
| -------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **MarkItDown** | `markitdown` (default) | Broadest format coverage (audio, archives, many text formats) via Microsoft's MarkItDown. Produces a markdown string that is then chunked by the per-format strategies.                                              |
| **Docling**    | `docling`              | Structure-aware conversion of office and PDF documents. Preserves headings, tables, and reading order, and feeds the token-budgeted docling chunking strategy. Best for retrieval quality on born-digital PDFs, Word, PowerPoint, and Excel. |

The engine is config-driven, not a feature flag: set `engine: docling` to opt in. The default remains `markitdown`, so existing configurations are unchanged.

Docling converts a focused set of formats — `pdf`, `docx`, `pptx`, `xlsx`, images, and `csv` — and is tuned with a **conversion profile** (`fast`, `accurate`, or `scanned`). See [Docling Engine Settings](#docling-engine-settings) below. The format tables in the next section describe the default MarkItDown engine.

## 🎯 Supported File Formats

The default **MarkItDown** engine handles a wide variety of file formats:

### 📄 Document Formats

| Format           | Extension              | Description                        | Features                                  |
| ---------------- | ---------------------- | ---------------------------------- | ----------------------------------------- |
| **PDF**          | `.pdf`                 | Portable Document Format           | Text extraction, OCR for images, metadata |
| **Word**         | `.docx`                | Microsoft Word documents           | Text, tables, images, metadata            |
| **PowerPoint**   | `.pptx`                | Microsoft PowerPoint presentations | Slide text, speaker notes, metadata       |
| **Excel**        | `.xlsx`, `.xls`        | Microsoft Excel spreadsheets       | Cell data, formulas, sheet names          |
| **OpenDocument** | `.odt`, `.ods`, `.odp` | LibreOffice/OpenOffice documents   | Text, tables, metadata                    |

### 📝 Text Formats

| Format               | Extension          | Description             | Features                              |
| -------------------- | ------------------ | ----------------------- | ------------------------------------- |
| **Markdown**         | `.md`, `.markdown` | Markdown markup         | Formatted text, code blocks, tables   |
| **reStructuredText** | `.rst`             | reStructuredText markup | Formatted text, directives            |
| **Plain Text**       | `.txt`             | Plain text files        | Raw text content                      |
| **Rich Text**        | `.rtf`             | Rich Text Format        | Formatted text, basic styling         |
| **LaTeX**            | `.tex`             | LaTeX documents         | Mathematical content, structured text |

### 🖼️ Image Formats (with OCR)

| Format   | Extension       | Description   | Features                              |
| -------- | --------------- | ------------- | ------------------------------------- |
| **JPEG** | `.jpg`, `.jpeg` | JPEG images   | OCR text extraction, metadata         |
| **PNG**  | `.png`          | PNG images    | OCR text extraction, transparency     |
| **GIF**  | `.gif`          | GIF images    | OCR text extraction, animation frames |
| **TIFF** | `.tiff`, `.tif` | TIFF images   | OCR text extraction, high quality     |
| **BMP**  | `.bmp`          | Bitmap images | OCR text extraction                   |

### 🎵 Audio Formats (with Transcription)

| Format   | Extension | Description | Features                     |
| -------- | --------- | ----------- | ---------------------------- |
| **MP3**  | `.mp3`    | MP3 audio   | Speech-to-text transcription |
| **WAV**  | `.wav`    | WAV audio   | Speech-to-text transcription |
| **M4A**  | `.m4a`    | M4A audio   | Speech-to-text transcription |
| **FLAC** | `.flac`   | FLAC audio  | Speech-to-text transcription |

### 📊 Data Formats

| Format   | Extension       | Description            | Features                    |
| -------- | --------------- | ---------------------- | --------------------------- |
| **JSON** | `.json`         | JSON data              | Structured data extraction  |
| **CSV**  | `.csv`          | Comma-separated values | Tabular data, headers       |
| **XML**  | `.xml`          | XML documents          | Structured data, attributes |
| **YAML** | `.yaml`, `.yml` | YAML configuration     | Configuration data          |
| **TOML** | `.toml`         | TOML configuration     | Configuration data          |

### 📦 Archive Formats

| Format    | Extension                 | Description    | Features                     |
| --------- | ------------------------- | -------------- | ---------------------------- |
| **ZIP**   | `.zip`                    | ZIP archives   | Extract and process contents |
| **TAR**   | `.tar`, `.tar.gz`, `.tgz` | TAR archives   | Extract and process contents |
| **7-Zip** | `.7z`                     | 7-Zip archives | Extract and process contents |

## ⚙️ Configuration

### Global File Conversion Configuration

File conversion is configured globally and applies to all projects and sources that enable it:

> **Note**: `markitdown.llm_*` fields are optional overrides for MarkItDown image-description flows. Prefer `global.llm` as the primary LLM configuration.

```yaml
global:
  file_conversion:
    # Maximum file size for conversion (in bytes)
    max_file_size: 52428800 # 50MB

    # Timeout for conversion operations (in seconds)
    conversion_timeout: 300 # 5 minutes

    # Conversion engine: "markitdown" (default) or "docling"
    engine: markitdown

    # MarkItDown specific settings (used when engine: markitdown)
    markitdown:
      # Enable LLM integration for image descriptions
      enable_llm_descriptions: false

      # LLM model for image descriptions (when enabled)
      llm_model: "gpt-4o"

      # LLM endpoint (when enabled)
      llm_endpoint: "https://api.openai.com/v1"

      # API key for LLM service (required when enable_llm_descriptions is true)
      llm_api_key: "${LLM_API_KEY}"

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

| Option               | Type   | Description                                          | Default           |
| -------------------- | ------ | --------------------------------------------------- | ----------------- |
| `max_file_size`      | int    | Maximum file size in bytes                          | `52428800` (50MB) |
| `conversion_timeout` | int    | Timeout for conversion operations in seconds        | `300` (5 minutes) |
| `engine`             | string | Conversion engine: `markitdown` or `docling`        | `markitdown`      |

#### MarkItDown Settings

`markitdown.llm_*` values are optional override fields. In most setups, keep LLM provider/model/auth under `global.llm`.

| Option                    | Type   | Description                                   | Default                     |
| ------------------------- | ------ | --------------------------------------------- | --------------------------- |
| `enable_llm_descriptions` | bool   | Enable LLM integration for image descriptions | `false`                     |
| `llm_model`               | string | LLM model for image descriptions              | `gpt-4o`                    |
| `llm_endpoint`            | string | LLM endpoint URL                              | `https://api.openai.com/v1` |
| `llm_api_key`             | string | API key for LLM service                       | `null`                      |

#### Docling Engine Settings

Used when `engine: docling`. A **profile** selects the cost/fidelity baseline; the optional fields below override individual knobs on top of it. Only fields you explicitly set override the profile — unset fields keep the profile's value.

```yaml
global:
  file_conversion:
    engine: docling
    docling:
      # Baseline cost vs. fidelity: fast | accurate | scanned
      profile: fast

      # Optional overrides (unset = inherit from the profile)
      # max_file_size: 52428800        # bytes
      # document_timeout: 300.0        # seconds (wall-clock per document)
      # enabled_formats: ["pdf", "docx", "pptx", "xlsx", "image", "csv"]
      # device: auto                   # auto | cpu | cuda | mps
      # num_threads: 4
      # compile_models: false         # torch.compile warm-up (off on CPU)
      # artifacts_path: null          # offline model dir; null fetches on first run

      # API image captioning (off by default)
      picture:
        enabled: false
        url: "https://api.openai.com/v1/chat/completions"
        model: "gpt-4o-mini"
        api_key: "${LLM_API_KEY}"
        prompt: "Describe this image in a few sentences."
        timeout: 60.0
        concurrency: 1
```

| Option            | Type        | Description                                                                            | Default                                          |
| ----------------- | ----------- | ------------------------------------------------------------------------------------- | ------------------------------------------------ |
| `profile`         | string      | Baseline bundle of OCR/table/timeout settings: `fast`, `accurate`, or `scanned`       | `fast`                                           |
| `max_file_size`   | int         | Override max file size in bytes                                                        | profile value                                    |
| `document_timeout`| float       | Override per-document wall-clock timeout in seconds                                    | profile value                                    |
| `enabled_formats` | list        | Override the converted formats                                                         | `[pdf, docx, pptx, xlsx, image, csv]`            |
| `device`          | string      | Compute device: `auto`, `cpu`, `cuda`, `mps`                                           | `auto`                                           |
| `num_threads`     | int         | CPU threads for conversion                                                             | `4`                                              |
| `compile_models`  | bool        | Enable `torch.compile` model warm-up (costly on CPU)                                   | `false`                                          |
| `artifacts_path`  | string      | Local directory of pre-downloaded models for offline runs                             | `null` (fetch on first run)                      |
| `picture.*`       | object      | API image-captioning settings (mirrors `markitdown.llm_*`); off by default            | disabled                                         |

**Conversion profiles:**

- **`fast`** (default) — CPU-only, fast table recognition, OCR off. Tuned for born-digital documents.
- **`accurate`** — Higher-fidelity table structure recognition. Slower, better tables.
- **`scanned`** — Full-page OCR on, accurate tables, and an extended `document_timeout` (600s). Use for scanned PDFs and image-only documents.

> **Chunking:** Documents converted by docling are chunked by the **docling chunking strategy**, which sizes chunks by a token budget aligned to your embedding model's tokenizer. Tune it under `global.chunking.strategies.docling` — see the [Configuration Reference](../../configuration/config-file-reference.md#chunking-configuration). For exact token budgeting, set `embedding.tokenizer` to match your embedding model.

#### Source-Level Settings

Each data source can enable or disable file conversion:

| Option                   | Type | Description                            | Default |
| ------------------------ | ---- | -------------------------------------- | ------- |
| `enable_file_conversion` | bool | Enable file conversion for this source | `false` |

## 🔧 How File Conversion Works

### Conversion Process

```text
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│     File     │──▶│    Format    │──▶ │  MarkItDown  │──▶│   Markdown   │
│  Detection   │    │  Detection   │    │ Conversion   │    │   Content    │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
       │                  │                  │                     │
       ▼                  ▼                  ▼                     ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐      ┌──────────────┐
│  MIME Type   │   │  Extension   │   │ Text + OCR   │      │  Structured  │
│  Detection   │   │   Mapping    │   │   + Audio    │      │ Text Output  │
└──────────────┘   └──────────────┘   └──────────────┘      └──────────────┘
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
global:
  file_conversion:
    max_file_size: 52428800 # 50MB
    conversion_timeout: 300 # 5 minutes
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
global:
  file_conversion:
    max_file_size: 104857600 # 100MB for large papers
    conversion_timeout: 600 # 10 minutes
    markitdown:
      enable_llm_descriptions: true
      llm_model: "gpt-4o"
      llm_endpoint: "https://api.openai.com/v1"
      llm_api_key: "${LLM_API_KEY}"

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
global:
  file_conversion:
    max_file_size: 52428800
    conversion_timeout: 900 # 15 minutes for audio/video
    markitdown:
      enable_llm_descriptions: true
      llm_model: "gpt-4o"
      llm_api_key: "${LLM_API_KEY}"

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
global:
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
qdrant-loader init --workspace .

# Test ingestion with file conversion enabled
qdrant-loader ingest --workspace . --project my-project

# Check configuration and project status
qdrant-loader config --workspace .

# Enable debug logging to see conversion details
qdrant-loader ingest --workspace . --log-level DEBUG --project my-project
```

### Validate Configuration

```bash
# Validate configuration (includes all projects)
qdrant-loader config --workspace .

# Display configuration with debug logging
qdrant-loader config --workspace . --log-level DEBUG
```

## 🔧 Troubleshooting

### Common Issues

#### File Size Exceeded

**Problem**: Files are too large to process

**Solutions**:

```yaml
global:
  file_conversion:
    # Increase size limit
    max_file_size: 104857600 # 100MB

    # Or filter at source level
projects:
  my-project:
    sources:
      localfile:
        documents:
          max_file_size: 20971520 # 20MB limit for this source
```

#### Conversion Timeout

**Problem**: Large files timing out during conversion

**Solutions**:

```yaml
global:
  file_conversion:
    # Increase timeout
    conversion_timeout: 900 # 15 minutes
```

#### LLM Integration Issues

**Problem**: Image descriptions not working

**Solutions**:

1. **Check API key**:

```bash
echo $LLM_API_KEY
# Or check legacy variable
echo $OPENAI_API_KEY
```

1. **Verify configuration**:

```yaml
global:
  file_conversion:
    markitdown:
      enable_llm_descriptions: true
      llm_api_key: "${LLM_API_KEY}"
```

1. **Test API access**:

```bash
curl -H "Authorization: Bearer $LLM_API_KEY" \
  https://api.openai.com/v1/models
```

#### Memory Issues

**Problem**: Large files causing memory problems

**Solutions**:

```yaml
global:
  file_conversion:
    # Reduce file size limits
    max_file_size: 20971520 # 20MB

    # Reduce timeout to fail faster
    conversion_timeout: 180 # 3 minutes
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

1. **Verify MarkItDown support** - Check if the file format is supported by MarkItDown

2. **Enable file conversion**:

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
# View configuration and project status
qdrant-loader config --workspace .

# Monitor with debug logging
qdrant-loader ingest --workspace . --log-level DEBUG --project my-project
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
