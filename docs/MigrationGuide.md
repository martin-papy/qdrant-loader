# Migration Guide: Upgrading to v0.3.2

**Version**: 0.3.2  
**Date**: May 31, 2025
**Compatibility**: Backward compatible upgrade

## Overview

This guide helps you migrate from previous versions of QDrant Loader to v0.3.2, which introduces comprehensive file conversion support. The upgrade is **backward compatible** with no breaking changes.

## 🚀 Quick Migration

### 1. Update Package

```bash
# Update to latest version
pip install --upgrade qdrant-loader

# Verify installation
qdrant-loader --version
# Should show: qdrant-loader 0.3.2
```

### 2. Optional: Enable File Conversion

File conversion is **disabled by default** to maintain backward compatibility. To enable:

```yaml
# Add to your existing config.yaml
sources:
  your_existing_connector:
    enable_file_conversion: true  # Add this line
    # ... your existing settings remain unchanged
```

### 3. Test Your Setup

```bash
# Validate configuration
qdrant-loader config --validate

# Test with existing data (no conversion)
qdrant-loader ingest --dry-run

# Test with file conversion enabled
qdrant-loader ingest --source-type localfile --source test-docs
```

## 📋 Detailed Migration Steps

### Step 1: Backup Your Data

Before upgrading, backup your existing data:

```bash
# Backup state database
cp /path/to/your/state.db /path/to/your/state.db.backup

# Backup configuration
cp config.yaml config.yaml.backup

# Optional: Export QDrant collection
# (Follow QDrant documentation for collection backup)
```

### Step 2: Update Dependencies

```bash
# Update qdrant-loader
pip install --upgrade qdrant-loader

# Verify new dependencies are installed
pip list | grep markitdown
# Should show: markitdown>=0.1.2
```

### Step 3: Update Configuration (Optional)

#### Add Global File Conversion Settings

Add to your `config.yaml`:

```yaml
global:
  # ... your existing global settings ...
  
  # New: File conversion configuration
  file_conversion:
    max_file_size: 52428800  # 50MB (adjust as needed)
    conversion_timeout: 300  # 5 minutes (adjust as needed)
    markitdown:
      enable_llm_descriptions: false  # Enable AI image descriptions
      llm_model: "gpt-4o"
      llm_endpoint: "https://api.openai.com/v1"
```

#### Enable Per-Connector File Conversion

Update your source configurations:

```yaml
sources:
  # Git repositories
  git:
    my-repo:
      # ... your existing settings ...
      enable_file_conversion: true  # Add this line
  
  # Confluence spaces
  confluence:
    my-space:
      # ... your existing settings ...
      enable_file_conversion: true   # Add this line
      download_attachments: true     # Add this line for attachments
  
  # JIRA projects
  jira:
    my-project:
      # ... your existing settings ...
      enable_file_conversion: true   # Add this line
      download_attachments: true     # Add this line for attachments
  
  # Local files
  localfile:
    my-docs:
      # ... your existing settings ...
      enable_file_conversion: true   # Add this line
  
  # Public documentation
  publicdocs:
    my-docs:
      # ... your existing settings ...
      enable_file_conversion: true   # Add this line
      download_attachments: true     # Add this line for attachments
```

### Step 4: Test File Conversion

#### Test with Sample Files

Create a test directory with various file types:

```bash
mkdir test-conversion
cd test-conversion

# Create test files (or copy existing ones)
echo "Test document" > test.txt
# Add PDF, Word, Excel files, etc.
```

#### Configure Test Source

Add to your `config.yaml`:

```yaml
sources:
  localfile:
    test-conversion:
      base_url: "file:///path/to/test-conversion"
      enable_file_conversion: true
      file_types: ["*"]  # Process all file types
```

#### Run Test Ingestion

```bash
# Test file conversion
qdrant-loader ingest --source-type localfile --source test-conversion --log-level DEBUG

# Check results
qdrant-loader status
```

### Step 5: Monitor Conversion Results

#### Check Conversion Statistics

```bash
# View overall status
qdrant-loader status

# Check for conversion errors in logs
grep -i "conversion" qdrant-loader.log
```

#### Verify Converted Documents

Use the MCP server or direct QDrant queries to verify converted documents:

```bash
# Start MCP server
mcp-qdrant-loader

# Search for converted documents
# Look for metadata fields: conversion_method, original_file_type
```

## 🔧 Configuration Migration Examples

### Before v0.3.2

```yaml
global:
  qdrant:
    url: "http://localhost:6333"
    collection_name: "documents"
  chunking:
    chunk_size: 1500
    chunk_overlap: 200

sources:
  git:
    my-repo:
      base_url: "https://github.com/user/repo.git"
      branch: "main"
      file_types: ["*.md", "*.py"]
```

### After v0.3.2 (with file conversion)

```yaml
global:
  qdrant:
    url: "http://localhost:6333"
    collection_name: "documents"
  chunking:
    chunk_size: 1500
    chunk_overlap: 200
  
  # New: File conversion settings
  file_conversion:
    max_file_size: 52428800
    conversion_timeout: 300

sources:
  git:
    my-repo:
      base_url: "https://github.com/user/repo.git"
      branch: "main"
      file_types: ["*.md", "*.py", "*.pdf", "*.docx"]  # Can now include more types
      enable_file_conversion: true  # New: Enable conversion
```

## 🔍 Troubleshooting Migration Issues

### Common Issues

#### 1. MarkItDown Import Error

**Error**: `ModuleNotFoundError: No module named 'markitdown'`

**Solution**:

```bash
pip install "markitdown[all]>=0.1.2"
```

#### 2. Configuration Validation Error

**Error**: `Unknown configuration key: enable_file_conversion`

**Solution**: Update to v0.3.2:

```bash
pip install --upgrade qdrant-loader
qdrant-loader --version  # Verify version
```

#### 3. Large File Conversion Timeout

**Error**: `Conversion timeout exceeded for file: large-document.pdf`

**Solution**: Increase timeout in configuration:

```yaml
global:
  file_conversion:
    conversion_timeout: 600  # Increase to 10 minutes
```

#### 4. Memory Issues During Conversion

**Error**: `MemoryError` or high memory usage

**Solutions**:

1. Reduce file size limit:

   ```yaml
   global:
     file_conversion:
       max_file_size: 26214400  # Reduce to 25MB
   ```

2. Process files in smaller batches
3. Exclude large file types temporarily

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
# Full debug output
qdrant-loader ingest --log-level DEBUG --verbose

# Save debug logs
qdrant-loader ingest --log-level DEBUG > migration.log 2>&1

# Check for specific errors
grep -i "error\|failed\|exception" migration.log
```

## 📊 Performance Considerations

### Before Migration

- Document your current ingestion performance
- Note memory usage and processing times
- Identify largest files in your datasets

### After Migration

- Monitor conversion times for different file types
- Watch memory usage during conversion
- Adjust file size limits based on your system resources

### Optimization Tips

1. **Start Small**: Enable conversion for one connector at a time
2. **File Size Limits**: Set conservative limits initially
3. **Selective Conversion**: Use file type filters to control what gets converted
4. **Monitor Resources**: Watch CPU and memory usage during conversion

## 🔄 Rollback Plan

If you encounter issues, you can easily rollback:

### Disable File Conversion

```yaml
sources:
  your_connector:
    enable_file_conversion: false  # Disable conversion
    # Keep all other settings
```

### Downgrade Package (if necessary)

```bash
# Downgrade to previous version
pip install qdrant-loader==0.3.1

# Restore backup configuration
cp config.yaml.backup config.yaml

# Restore state database
cp /path/to/your/state.db.backup /path/to/your/state.db
```

## ✅ Migration Checklist

- [ ] **Backup**: State database and configuration files
- [ ] **Update**: Package to v0.3.2
- [ ] **Verify**: Installation and version
- [ ] **Test**: Existing functionality without file conversion
- [ ] **Configure**: Add file conversion settings (optional)
- [ ] **Test**: File conversion with sample files
- [ ] **Monitor**: Performance and resource usage
- [ ] **Deploy**: Enable conversion for production connectors
- [ ] **Document**: Update your internal documentation

## 🆘 Getting Help

If you encounter issues during migration:

1. **Check this guide** for common solutions
2. **Review logs** with debug mode enabled
3. **Search existing issues**: [GitHub Issues](https://github.com/martin-papy/qdrant-loader/issues)
4. **Create a new issue** with:
   - Migration step where issue occurred
   - Error messages and logs
   - Configuration used
   - System information

## 📚 Related Documentation

- [File Conversion Guide](./FileConversionGuide.md) - Detailed file conversion documentation
- [Configuration Reference](../packages/qdrant-loader/config.template.yaml) - Complete configuration options
- [Release Notes](../RELEASE_NOTES.md) - Full v0.3.2 release notes
- [Troubleshooting Guide](./FileConversionGuide.md#troubleshooting) - Common issues and solutions

---

**Welcome to QDrant Loader v0.3.2! 🎉**
