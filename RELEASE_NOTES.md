# 🚀 Release Notes

## 🆕 Version 0.3.2 - File Conversion Support (May 31, 2025)

### 🎉 Major New Feature: File Conversion Support

QDrant Loader now supports automatic conversion of diverse file formats to markdown for processing:

#### 📁 Supported File Types (20+)

- **Documents**: PDF, Word (.docx), PowerPoint (.pptx), Excel (.xlsx)
- **Images**: PNG, JPEG, GIF, BMP, TIFF (with optional OCR)
- **Archives**: ZIP files with automatic extraction
- **Data**: JSON, CSV, XML, YAML
- **Audio**: MP3, WAV (transcription support)
- **E-books**: EPUB format
- **And more**: All MarkItDown-supported formats

#### 🔧 Key Features

- **Universal Support**: Works across all connectors (Git, Confluence, JIRA, PublicDocs, LocalFile)
- **Attachment Processing**: Download and convert attachments from Confluence, JIRA, and documentation sites
- **Intelligent Detection**: Automatic file type detection and conversion routing
- **Fallback Handling**: Graceful handling when conversion fails
- **Performance Optimized**: Configurable size limits, timeouts, and lazy loading
- **Metadata Preservation**: Complete tracking of conversion information

#### ⚙️ Configuration

```yaml
# Global settings
global:
  file_conversion:
    max_file_size: 52428800  # 50MB
    conversion_timeout: 300  # 5 minutes

# Enable per connector
sources:
  git:
    my-repo:
      enable_file_conversion: true
  confluence:
    my-space:
      enable_file_conversion: true
      download_attachments: true
```

#### 🚀 Getting Started

1. **Update to v0.3.2**: `pip install --upgrade qdrant-loader`
2. **Enable conversion**: Add `enable_file_conversion: true` to your connectors
3. **Run ingestion**: Files are automatically detected and converted

See the [File Conversion Guide](./docs/FileConversionGuide.md) for detailed documentation.

### 🔧 Technical Improvements

- **Enhanced State Management**: Complete tracking of conversion metadata and attachment relationships
- **Monitoring Integration**: Comprehensive metrics for conversion operations
- **Error Handling**: Robust fallback mechanisms for conversion failures
- **Performance**: Optimized memory usage and processing speed

### 🔌 MCP Server Enhancements

- **Hierarchy-Aware Search**: Enhanced Confluence search with page hierarchy understanding
  - Added hierarchy information to search results (parent/child relationships, breadcrumb paths, depth levels)
  - New `hierarchy_search` tool with advanced filtering capabilities
  - Support for filtering by hierarchy depth, parent pages, root pages, and pages with children
  - Hierarchical organization of search results with tree-like structure display

- **Attachment-Aware Search**: Comprehensive file attachment support and parent document relationships
  - Added attachment information to all search results (file metadata, parent document context)
  - New `attachment_search` tool for specialized file discovery and filtering
  - Support for filtering by file type, size, author, and parent document
  - Rich attachment context display with visual indicators

- **Enhanced Search Result Model**: Extended SearchResult with comprehensive metadata for both hierarchy and attachment information
- **Advanced Search Tools**: Three specialized search tools for different use cases (`search`, `hierarchy_search`, `attachment_search`)

### 🧪 Testing

- **100+ Unit Tests**: Comprehensive test coverage for all file conversion components
- **Integration Tests**: End-to-end testing of conversion workflows
- **Demo Scripts**: Working examples for all connector types

### 📚 Documentation

- **[File Conversion Guide](./docs/FileConversionGuide.md)**: Comprehensive setup and usage guide
- **[Migration Guide](./docs/MigrationGuide.md)**: Step-by-step upgrade instructions
- **Updated READMEs**: Enhanced documentation with file conversion examples
- **[Advanced Search Examples](./docs/mcp-server/SearchExamples.md)**: Comprehensive MCP server search capabilities
- **[Hierarchy Search Guide](./docs/mcp-server/SearchHierarchyExemple.md)**: Confluence hierarchy navigation and filtering
- **[Attachment Search Guide](./docs/mcp-server/AttachementSearchExemple.md)**: File attachment discovery and management

### 🔄 Backward Compatibility

- **No Breaking Changes**: File conversion is disabled by default
- **Existing Configurations**: Continue to work unchanged
- **Performance**: Minimal impact when conversion is disabled

---

## 🆕 Latest Features

### Confluence Data Center Support

QDrant Loader now supports **both Confluence Cloud and Data Center/Server** deployments:

- **Secure authentication methods**: API tokens (Cloud) and Personal Access Tokens (Data Center)
- **Deployment-specific optimization**: Proper pagination and API handling for each deployment type
- **Seamless migration**: Easy transition from Cloud to Data Center configurations
- **Auto-detection**: Automatic deployment type detection based on URL patterns

See our [Confluence Data Center Support Guide](./docs/ConfluenceDataCenterSupport.md) for detailed setup instructions.

## 📋 Release Process Updates

The QDrant Loader project has been updated with a new unified versioning approach and enhanced release management system.

## 🔄 Major Changes

### Unified Versioning

- **Both packages now use the same version number** instead of independent versioning
- **`qdrant-loader` is the source of truth** for the current version
- **Automatic version mismatch detection** prevents releases with inconsistent versions
- **Version synchronization command** to easily sync packages when needed

### Enhanced Release Script

The `release.py` script has been completely rewritten with:

- ✅ **Comprehensive safety checks** (git status, branch, workflows, etc.)
- ✅ **Dry run mode** that continues through all steps to show all issues
- ✅ **User-friendly output** with emojis, clear formatting, and actionable guidance
- ✅ **Version synchronization** with `--sync-versions` flag
- ✅ **GitHub integration** for automated tag and release creation
- ✅ **Error recovery** that shows all problems instead of stopping at the first one

## 🎯 Benefits

### For Developers

- **Clearer release process** with step-by-step guidance
- **Safer releases** with comprehensive pre-flight checks
- **Better debugging** with verbose mode and detailed error messages
- **Faster iteration** with dry-run mode to preview changes

### For Users

- **Simplified dependency management** with unified versions
- **Guaranteed compatibility** between packages
- **Clearer versioning** without confusion about which versions work together
- **More reliable releases** with automated safety checks

## 🚀 Quick Start

### Check Release Readiness

```bash
python release.py --dry-run
```

### Sync Package Versions (if needed)

```bash
python release.py --sync-versions
```

### Create a Release

```bash
python release.py
```

## 📚 Documentation

- **[Release Management Guide](./docs/RELEASE.md)** - Comprehensive documentation
- **[Contributing Guide](./docs/CONTRIBUTING.md)** - Updated with new release process
- **[Main README](./README.md)** - Updated with unified versioning information

## 🔧 Migration

### For Existing Developers

1. **Update your workflow**:
   - Use `python release.py --dry-run` before releasing
   - Use `python release.py --sync-versions` if packages get out of sync
   - Follow the new safety checks and fix any issues

2. **Update documentation references**:
   - Both packages now have the same version
   - Reference the new release documentation

### For CI/CD

- The release script creates the same tags as before
- GitHub Actions workflows should continue to work
- Consider updating workflows to use the new script

## ⚠️ Breaking Changes

- **Unified versioning**: Both packages must have the same version
- **Release process**: Must use the new `release.py` script
- **Safety checks**: All checks must pass before releasing

## 🆘 Support

If you encounter issues:

1. **Check the verbose output**: `python release.py --dry-run --verbose`
2. **Review the documentation**: [Release Management Guide](./docs/RELEASE.md)
3. **Create an issue**: [GitHub Issues](https://github.com/martin-papy/qdrant-loader/issues)

---

**Happy Releasing! 🎉**
