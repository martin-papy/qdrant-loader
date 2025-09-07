# Performance Issues Guide

This guide helps you diagnose and resolve performance issues with QDrant Loader, including slow data loading, memory problems, and optimization strategies. Whether you're dealing with large datasets or need to improve processing times, this guide provides practical solutions using the actual CLI commands and configuration options.

## 🎯 Performance Issue Types

### Quick Diagnosis

```text
🐌 Slow data loading → See [Loading Performance](#loading-performance-issues)
💾 High memory usage → See [Memory Issues](#memory-issues)
🔥 High CPU usage → See [CPU Issues](#cpu-issues)
📊 Poor throughput → See [Throughput Optimization](#throughput-optimization)
🌐 Network bottlenecks → See [Network Performance](#network-performance)
```

## 📊 Performance Monitoring

### Basic Performance Metrics

```bash
# Check system resources
htop
iostat -x 1
free -h

# Check project status and validation
qdrant-loader config --workspace .
qdrant-loader config --workspace .

# Monitor QDrant instance health
curl -s "$QDRANT_URL/health"
curl -s "$QDRANT_URL/metrics" | grep -E "(memory|cpu|disk)"

# Monitor network usage
iftop
nethogs
```

### Performance Benchmarking

```bash
# Benchmark data loading with timing
time qdrant-loader ingest --workspace . --project my-project

# Test configuration validation
time qdrant-loader config --workspace . --project-id my-project

# Monitor file processing
find ./docs -type f -name "*.md" -exec wc -c {} + | sort -n
find ./docs -type f | wc -l
```

## 🚀 Loading Performance Issues

### Issue: Slow data loading

**Symptoms:**

- Ingestion takes much longer than expected
- High CPU usage during processing
- Memory usage grows continuously
- Process appears to hang

**Diagnostic Steps:**

```bash
# Check file sizes and counts in your data sources
find ./docs -type f -name "*.md" -exec wc -c {} + | sort -n
find ./docs -type f | wc -l

# Validate project configuration
qdrant-loader config --workspace . --project-id my-project

# Check project status
qdrant-loader config --workspace . --project-id my-project
```

**Optimization Solutions:**

1. **Optimize file conversion settings:**

```yaml
# In your workspace config file
global:
  file_conversion:
    max_file_size: 10485760  # 10MB limit
    conversion_timeout: 30   # 30 seconds timeout
    markitdown:
      enable_llm_descriptions: false  # Disable for faster processing
```

1. **Filter unnecessary files:**

```yaml
# In your project configuration
projects:
  my-project:
    sources:
      localfile:
        my-docs:
          base_url: "file:///path/to/docs"
          include_paths:
            - "*.md"
            - "*.txt"
          exclude_paths:
            - "node_modules/**"
            - ".git/**"
            - "*.pdf"  # Skip large PDFs if not needed
          file_types:
            - "md"
            - "txt"
          max_file_size: 5242880  # 5MB limit
```

1. **Process in smaller batches:**

```bash
# Process specific projects only
qdrant-loader ingest --workspace . --project specific-project

# Use force flag to reprocess if needed
qdrant-loader init --workspace . --force
qdrant-loader ingest --workspace . --project my-project
```

### Issue: Memory usage grows during loading

**Symptoms:**

- RAM usage increases continuously
- System becomes unresponsive
- Out of memory errors
- Swap usage increases

**Solutions:**

```bash
# Monitor memory usage during processing
watch -n 1 'free -h && ps aux | grep qdrant-loader'

# Process smaller datasets first
qdrant-loader ingest --workspace . --project small-project

# Check configuration for memory-intensive settings
qdrant-loader config --workspace .
```

**Memory Optimization:**

```yaml
# Memory-efficient configuration
global:
  file_conversion:
    max_file_size: 2097152  # 2MB limit
    conversion_timeout: 15  # Shorter timeout
    markitdown:
      enable_llm_descriptions: false  # Disable LLM processing

projects:
  my-project:
    sources:
      localfile:
        docs:
          max_file_size: 1048576  # 1MB limit per file
          file_types:
            - "md"
            - "txt"  # Exclude large file types
          exclude_paths:
            - "*.pdf"
            - "*.zip"
            - "*.tar.gz"
```

### Issue: Loading fails with large files

**Symptoms:**

- Processing stops on specific large files
- Timeout errors
- Memory allocation errors
- File conversion failures

**Solutions:**

```bash
# Identify large files
find ./docs -type f -size +10M -exec ls -lh {} \;

# Configure smaller file size limits
qdrant-loader config --workspace .
```

**Large File Configuration:**

```yaml
# Handle large files appropriately
global:
  file_conversion:
    max_file_size: 5242880   # 5MB limit
    conversion_timeout: 60   # Longer timeout for large files

projects:
  my-project:
    sources:
      localfile:
        large-docs:
          base_url: "file:///path/to/large-docs"
          max_file_size: 10485760  # 10MB for this specific source
          file_types:
            - "md"
            - "txt"
          exclude_paths:
            - "*.pdf"  # Skip PDFs that are too large
```

## 💾 Memory Issues

### Issue: High memory usage

**Symptoms:**

- QDrant Loader uses excessive RAM
- System becomes slow
- Other applications affected
- Swap usage increases

**Diagnostic Steps:**

```bash
# Monitor memory usage
ps aux | grep qdrant-loader
free -h

# Check project configuration for memory-intensive settings
qdrant-loader config --workspace . --project-id my-project
```

**Solutions:**

```bash
# Set system memory limits
ulimit -m 2097152  # 2GB limit

# Process projects individually
qdrant-loader ingest --workspace . --project project1
qdrant-loader ingest --workspace . --project project2

# Use smaller file size limits
qdrant-loader config --workspace .
```

**Memory-Efficient Configuration:**

```yaml
# Optimize for lower memory usage
global:
  file_conversion:
    max_file_size: 1048576  # 1MB limit
    conversion_timeout: 30
    markitdown:
      enable_llm_descriptions: false

projects:
  my-project:
    sources:
      localfile:
        docs:
          max_file_size: 524288  # 512KB limit
          file_types:
            - "md"
            - "txt"
```

## 🔥 CPU Issues

### Issue: High CPU usage

**Symptoms:**

- CPU usage consistently above 80%
- System becomes unresponsive
- Fan noise increases
- Other processes slow down

**Solutions:**

```bash
# Limit CPU usage with nice
nice -n 10 qdrant-loader ingest --workspace .

# Process smaller batches
qdrant-loader ingest --workspace . --project small-project

# Use CPU throttling
cpulimit -l 50 -- qdrant-loader ingest --workspace .
```

**CPU Optimization:**

```yaml
# CPU-efficient configuration
global:
  file_conversion:
    conversion_timeout: 15  # Shorter processing time
    markitdown:
      enable_llm_descriptions: false  # Disable CPU-intensive LLM processing

projects:
  my-project:
    sources:
      localfile:
        docs:
          file_types:
            - "md"
            - "txt"  # Exclude CPU-intensive file types
          exclude_paths:
            - "*.pdf"
            - "*.docx"
            - "*.pptx"
```

## 📈 Throughput Optimization

### Optimizing Data Loading Throughput

```bash
# Process multiple projects efficiently
qdrant-loader config --workspace .
qdrant-loader ingest --workspace . --project project1
qdrant-loader ingest --workspace . --project project2

# Validate configuration before processing
qdrant-loader config --workspace .
```

### Configuration Optimization

```yaml
# Optimized configuration for better throughput
global:
  qdrant:
    url: "${QDRANT_URL}"
    api_key: "${QDRANT_API_KEY}"
    collection_name: "${QDRANT_COLLECTION_NAME}"
  llm:
    provider: "openai"
    base_url: "https://api.openai.com/v1"
    api_key: "${LLM_API_KEY}"
    models:
      embeddings: "text-embedding-3-small"
  file_conversion:
    max_file_size: 5242880  # 5MB - balance between size and processing time
    conversion_timeout: 30
    markitdown:
      enable_llm_descriptions: false  # Faster processing

projects:
  my-project:
    sources:
      localfile:
        docs:
          base_url: "file:///path/to/docs"
          file_types:
            - "md"
            - "txt"
            - "rst"
          max_file_size: 2097152  # 2MB per file
          include_paths:
            - "docs/**/*"
            - "*.md"
          exclude_paths:
            - "node_modules/**"
            - ".git/**"
            - "*.log"
```

## 🌐 Network Performance

### Issue: Slow network operations

**Symptoms:**

- Slow loading from remote sources (Git, Confluence, JIRA)
- Timeouts connecting to QDrant
- High network latency
- Connection drops

**Diagnostic Steps:**

```bash
# Test QDrant connectivity
curl -w "@curl-format.txt" -o /dev/null -s "$QDRANT_URL/health"

# Test API endpoints
curl -H "Authorization: Bearer $QDRANT_API_KEY" "$QDRANT_URL/collections"

# Monitor network usage
iftop -i eth0
```

**Solutions:**

```yaml
# Network-optimized configuration
global:
  qdrant:
    url: "${QDRANT_URL}"
    api_key: "${QDRANT_API_KEY}"
    collection_name: "${QDRANT_COLLECTION_NAME}"

projects:
  my-project:
    sources:
      git:
        my-repo:
          base_url: "https://github.com/user/repo.git"
          branch: "main"
          token: "${REPO_TOKEN}"
          # Optimize for network performance
          include_paths:
            - "docs/**/*"
          exclude_paths:
            - "*.pdf"
            - "*.zip"
            - ".git/**"
          file_types:
            - "md"
            - "txt"
          max_file_size: 1048576  # 1MB to reduce network load
      confluence:
        my-confluence:
          base_url: "${CONFLUENCE_URL}"
          deployment_type: "cloud"
          space_key: "DOCS"
          email: "${CONFLUENCE_EMAIL}"
          token: "${CONFLUENCE_TOKEN}"
          # Network optimization
          content_types:
            - "page"
          download_attachments: false  # Reduce network load
```

## 🔧 Advanced Optimization

### Project Structure Optimization

```yaml
# Organize projects for optimal processing
global:
  qdrant:
    url: "${QDRANT_URL}"
    api_key: "${QDRANT_API_KEY}"
    collection_name: "${QDRANT_COLLECTION_NAME}"
  llm:
    provider: "openai"
    base_url: "https://api.openai.com/v1"
    api_key: "${LLM_API_KEY}"
    models:
      embeddings: "text-embedding-3-small"
  file_conversion:
    max_file_size: 5242880
    conversion_timeout: 30
    markitdown:
      enable_llm_descriptions: false

# Separate projects by data source type for better management
projects:
  local-docs:
    sources:
      localfile:
        documentation:
          base_url: "file:///path/to/docs"
          file_types: ["md", "txt"]
          max_file_size: 2097152
  git-repos:
    sources:
      git:
        main-repo:
          base_url: "https://github.com/user/repo.git"
          branch: "main"
          token: "${REPO_TOKEN}"
          file_types: ["md", "py", "js"]
  confluence-content:
    sources:
      confluence:
        company-wiki:
          base_url: "${CONFLUENCE_URL}"
          deployment_type: "cloud"
          space_key: "DOCS"
          email: "${CONFLUENCE_EMAIL}"
          token: "${CONFLUENCE_TOKEN}"
          download_attachments: false
```

### System-Level Optimization

```bash
# Increase file descriptor limits
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf

# Monitor system resources during processing
top -p $(pgrep -f qdrant-loader)

# Check disk space
df -h

# Monitor I/O
iostat -x 1
```

## 📊 Performance Tuning Presets

### Small Dataset (< 1GB)

```yaml
global:
  file_conversion:
    max_file_size: 10485760  # 10MB
    conversion_timeout: 60
    markitdown:
      enable_llm_descriptions: true  # Can afford LLM processing

projects:
  small-project:
    sources:
      localfile:
        docs:
          max_file_size: 5242880  # 5MB per file
```

### Medium Dataset (1-10GB)

```yaml
global:
  file_conversion:
    max_file_size: 5242880  # 5MB
    conversion_timeout: 30
    markitdown:
      enable_llm_descriptions: false  # Skip for performance

projects:
  medium-project:
    sources:
      localfile:
        docs:
          max_file_size: 2097152  # 2MB per file
          exclude_paths:
            - "*.pdf"
            - "*.zip"
```

### Large Dataset (> 10GB)

```yaml
global:
  file_conversion:
    max_file_size: 2097152  # 2MB
    conversion_timeout: 15
    markitdown:
      enable_llm_descriptions: false

projects:
  large-project:
    sources:
      localfile:
        docs:
          max_file_size: 1048576  # 1MB per file
          file_types:
            - "md"
            - "txt"
          exclude_paths:
            - "*.pdf"
            - "*.docx"
            - "*.pptx"
            - "*.zip"
            - "*.tar.gz"
```

## 🚨 Performance Emergency Procedures

### When System is Unresponsive

```bash
# 1. Check system resources
top
df -h
free -h

# 2. Kill runaway processes
pkill -f qdrant-loader

# 3. Clear system caches
sync && echo 3 > /proc/sys/vm/drop_caches

# 4. Restart with minimal configuration
qdrant-loader config --workspace .
qdrant-loader config --workspace .
```

### Performance Recovery

```bash
# 1. Check system resources
top
df -h
free -h

# 2. Validate configuration
qdrant-loader config --workspace .

# 3. Restart processing with smaller scope
qdrant-loader init --workspace . --force
qdrant-loader ingest --workspace . --project small-project

# 4. Monitor progress
qdrant-loader config --workspace .
```

## 📈 Performance Monitoring

### Key Metrics to Track

```bash
# Monitor system resources
htop
free -h
df -h
iostat -x 1

# Check project status
qdrant-loader config --workspace .
qdrant-loader config --workspace .

# Validate configuration
qdrant-loader config --workspace .
```

### Performance Testing

```bash
# Time the ingestion process
time qdrant-loader ingest --workspace . --project test-project

# Monitor memory usage during processing
watch -n 1 'free -h && ps aux | grep qdrant-loader'

# Check file processing statistics
find ./docs -type f -name "*.md" | wc -l
du -sh ./docs
```

## 🔗 Related Documentation

- **[Common Issues](./common-issues.md)** - General troubleshooting
- **[Connection Problems](./connection-problems.md)** - Network and connectivity issues
- **[Error Messages Reference](./error-messages-reference.md)** - Specific error solutions
- **[CLI Reference](../cli-reference/README.md)** - Command-line options
- **[Configuration Reference](../configuration/README.md)** - Configuration options
- **[Installation Guide](../../getting-started/installation.md)** - System requirements

---

**Performance optimized!** 🚀

This guide covers comprehensive performance optimization strategies using actual QDrant Loader commands and configuration options. For specific error messages, check the [Error Messages Reference](./error-messages-reference.md), and for general issues, see the [Common Issues Guide](./common-issues.md).
