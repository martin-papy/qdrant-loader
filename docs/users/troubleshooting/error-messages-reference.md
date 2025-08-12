# Error Messages Reference

This comprehensive reference guide provides detailed explanations and solutions for all error messages you might encounter when using QDrant Loader. Each error includes the exact message, possible causes, and step-by-step solutions using actual CLI commands and configuration options.

## 🎯 Error Categories

### Quick Navigation

```text
🔌 Connection Errors → See [Connection Errors](#connection-errors)
🔑 Authentication Errors → See [Authentication Errors](#authentication-errors)
📊 Data Loading Errors → See [Data Loading Errors](#data-loading-errors)
⚙️ Configuration Errors → See [Configuration Errors](#configuration-errors)
🔍 Search Errors → See [Search Errors](#search-errors)
💾 Memory/Resource Errors → See [Memory and Resource Errors](#memory-and-resource-errors)
📁 File System Errors → See [File System Errors](#file-system-errors)
🌐 Network Errors → See [Network Errors](#network-errors)
```

## 🔌 Connection Errors

### `ConnectionError: Failed to connect to QDrant instance`

**Full Error:**

```text
ConnectionError: Failed to connect to QDrant instance at http://localhost:6333
```

**Causes:**

- QDrant instance is not running
- Incorrect URL or port
- Network connectivity issues
- Firewall blocking connection

**Solutions:**

```bash
# Check if QDrant is running
curl -v "$QDRANT_URL/health"

# Verify URL format in configuration
qdrant-loader config --workspace .

# Test connectivity
ping your-qdrant-instance.com
telnet your-qdrant-instance.com 6333

# Validate project configuration
qdrant-loader project status --workspace . --project-id my-project
```

**Configuration Fix:**

```yaml
# Correct QDrant configuration
global:
  qdrant:
    url: "${QDRANT_URL}"   # e.g., http://localhost:6333 or https://your-instance.qdrant.cloud
    api_key: "${QDRANT_API_KEY}"
    collection_name: "${QDRANT_COLLECTION_NAME}"
```

### `ConnectionRefusedError: [Errno 111] Connection refused`

**Full Error:**

```text
ConnectionRefusedError: [Errno 111] Connection refused
```

**Causes:**

- QDrant service not running
- Wrong port number
- Service bound to different interface

**Solutions:**

```bash
# Start QDrant locally
docker run -p 6333:6333 qdrant/qdrant

# Check port binding
netstat -tlnp | grep 6333
ss -tlnp | grep 6333

# Verify service status
systemctl status qdrant  # If installed as service

# Check project status
qdrant-loader project status --workspace .
```

### `TimeoutError: Connection timeout after 30 seconds`

**Full Error:**

```text
TimeoutError: Connection timeout after 30 seconds
```

**Causes:**

- Network latency issues
- Server overloaded
- Firewall dropping packets
- DNS resolution slow

**Solutions:**

```bash
# Test network latency
ping -c 10 your-qdrant-instance.com

# Use IP address instead of hostname
# Update your configuration file:
```

```yaml
global:
  qdrant:
    url: "http://192.168.1.100:6333"   # Use IP instead of hostname
    api_key: "${QDRANT_API_KEY}"
    collection_name: "${QDRANT_COLLECTION_NAME}"
```

## 🔑 Authentication Errors

### `AuthenticationError: Invalid API key`

**Full Error:**

```text
AuthenticationError: Invalid API key for QDrant instance
```

**Causes:**

- Incorrect API key
- API key not set
- API key expired
- Wrong authentication method

**Solutions:**

```bash
# Check API key format
echo $QDRANT_API_KEY | wc -c
echo $QDRANT_API_KEY | head -c 10

# Test authentication
curl -H "api-key: $QDRANT_API_KEY" "$QDRANT_URL/collections"

# Set API key correctly
export QDRANT_API_KEY="your-actual-api-key"

# Validate configuration
qdrant-loader project status --workspace .
```

**Configuration Fix:**

```yaml
global:
  qdrant:
    url: "${QDRANT_URL}"
    api_key: "${QDRANT_API_KEY}"   # Ensure this environment variable is set
    collection_name: "${QDRANT_COLLECTION_NAME}"
```

### `OpenAIError: Incorrect API key provided`

**Full Error:**

```text
OpenAIError: Incorrect API key provided: sk-***
```

**Causes:**

- Invalid OpenAI API key
- API key format incorrect
- Account suspended
- Rate limits exceeded

**Solutions:**

```bash
# Verify API key format (should start with sk-)
echo $OPENAI_API_KEY | grep -E "^sk-"

# Test OpenAI API
curl -H "Authorization: Bearer $OPENAI_API_KEY" "https://api.openai.com/v1/models"

# Check account status
curl -H "Authorization: Bearer $OPENAI_API_KEY" "https://api.openai.com/v1/usage"

# Validate configuration
qdrant-loader project status --workspace .
```

**Configuration Fix:**

```yaml
global:
  openai:
    api_key: "${OPENAI_API_KEY}"   # Ensure this environment variable is set correctly
```

### `ConfluenceAuthError: 401 Unauthorized`

**Full Error:**

```text
ConfluenceAuthError: 401 Unauthorized - Check your credentials
```

**Causes:**

- Wrong email or API token
- API token expired
- Insufficient permissions
- Account locked

**Solutions:**

```bash
# Test Confluence authentication
curl -u "$CONFLUENCE_EMAIL:$CONFLUENCE_TOKEN" \
  "$CONFLUENCE_URL/rest/api/content?limit=1"

# Verify credentials format
echo "Email: $CONFLUENCE_EMAIL"
echo "Token length: $(echo $CONFLUENCE_TOKEN | wc -c)"

# Check permissions
curl -u "$CONFLUENCE_EMAIL:$CONFLUENCE_TOKEN" \
  "$CONFLUENCE_URL/rest/api/user/current"

# Validate project configuration
qdrant-loader project status --workspace . --project-id my-project
```

**Configuration Fix:**

```yaml
projects:
  my-project:
    sources:
      confluence:
        my-confluence:
          base_url: "${CONFLUENCE_URL}"
          deployment_type: "cloud"  # or "server"
          space_key: "DOCS"
          email: "${CONFLUENCE_EMAIL}"
          token: "${CONFLUENCE_TOKEN}"
```

## 📊 Data Loading Errors

### `DataLoadError: No documents found in source`

**Full Error:**

```text
DataLoadError: No documents found in source: /path/to/docs
```

**Causes:**

- Empty directory
- No matching file patterns
- Incorrect path
- Permission issues

**Solutions:**

```bash
# Check directory contents
ls -la /path/to/docs
find /path/to/docs -name "*.md" | head -10

# Check project configuration
qdrant-loader project status --workspace . --project-id my-project

# Validate configuration
qdrant-loader project validate --workspace . --project-id my-project
```

**Configuration Fix:**

```yaml
projects:
  my-project:
    sources:
      localfile:
        docs:
          base_url: "file:///path/to/docs"
          include_paths:
            - "*.md"
            - "*.txt"
            - "docs/**/*"
          file_types:
            - "md"
            - "txt"
            - "rst"
```

### `FileConversionError: Failed to process document`

**Full Error:**

```text
FileConversionError: Failed to process document: document.pdf - File too large
```

**Causes:**

- File exceeds size limits
- Corrupted file
- Unsupported file format
- Memory limitations

**Solutions:**

```bash
# Check file size
ls -lh document.pdf

# Check current file conversion settings
qdrant-loader config --workspace .

# Process with different settings
qdrant-loader ingest --workspace . --project my-project
```

**Configuration Fix:**

```yaml
global:
  file_conversion:
    max_file_size: 52428800  # 50MB limit
    conversion_timeout: 60   # 60 seconds timeout
    markitdown:
      enable_llm_descriptions: false  # Disable for large files

projects:
  my-project:
    sources:
      localfile:
        docs:
          max_file_size: 10485760  # 10MB per file
          exclude_paths:
            - "*.pdf"  # Skip PDFs if too large
```

### `EmbeddingError: Failed to generate embeddings`

**Full Error:**

```text
EmbeddingError: Failed to generate embeddings for chunk: Rate limit exceeded
```

**Causes:**

- OpenAI rate limits
- API quota exceeded
- Network issues
- Invalid content

**Solutions:**

```bash
# Check API usage
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  "https://api.openai.com/v1/usage"

# Process smaller batches
qdrant-loader ingest --workspace . --project small-project

# Check project status
qdrant-loader project status --workspace .
```

**Configuration Fix:**

```yaml
global:
  openai:
    api_key: "${OPENAI_API_KEY}"
  file_conversion:
    max_file_size: 2097152  # 2MB - smaller files for rate limiting
    conversion_timeout: 30
    markitdown:
      enable_llm_descriptions: false  # Reduce API calls
```

## ⚙️ Configuration Errors

### `ConfigurationError: Invalid YAML syntax`

**Full Error:**

```text
ConfigurationError: Invalid YAML syntax in config.yaml at line 15
```

**Causes:**

- YAML indentation errors
- Missing quotes
- Invalid characters
- Malformed structure

**Solutions:**

```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Check specific line
sed -n '15p' config.yaml

# Use YAML validator
yamllint config.yaml

# Validate with QDrant Loader
qdrant-loader project validate --workspace .
```

### `ValidationError: Missing required field 'qdrant.url'`

**Full Error:**

```text
ValidationError: Missing required field 'qdrant.url' in configuration
```

**Causes:**

- Required configuration missing
- Typo in field name
- Wrong configuration structure
- Environment variable not set

**Solutions:**

```bash
# Check configuration structure
qdrant-loader config --workspace .

# Set required environment variables
export QDRANT_URL="http://localhost:6333"
export QDRANT_API_KEY="your-api-key"
export QDRANT_COLLECTION_NAME="your-collection"

# Validate configuration
qdrant-loader project validate --workspace .
```

**Configuration Fix:**

```yaml
# Correct configuration structure
global:
  qdrant:
    url: "${QDRANT_URL}"                    # Required
    api_key: "${QDRANT_API_KEY}"           # Required
    collection_name: "${QDRANT_COLLECTION_NAME}"  # Required
  openai:
    api_key: "${OPENAI_API_KEY}"           # Required
```

### `EnvironmentError: Environment variable not found`

**Full Error:**

```text
EnvironmentError: Environment variable 'QDRANT_API_KEY' not found
```

**Causes:**

- Environment variable not set
- Variable name typo
- Shell session issues
- .env file not loaded

**Solutions:**

```bash
# Set environment variable
export QDRANT_API_KEY="your-api-key"

# Load from .env file
set -a && source .env && set +a

# Check variable is set
echo $QDRANT_API_KEY

# List all QDrant Loader related variables
env | grep -E "(QDRANT|OPENAI|CONFLUENCE|JIRA|REPO)"

# Validate configuration
qdrant-loader project validate --workspace .
```

## 💾 Memory and Resource Errors

### `MemoryError: Unable to allocate memory`

**Full Error:**

```text
MemoryError: Unable to allocate 2.5 GB for document processing
```

**Causes:**

- Insufficient RAM
- Memory leak
- Large files
- Too many files processed simultaneously

**Solutions:**

```bash
# Check available memory
free -h

# Process smaller projects
qdrant-loader ingest --workspace . --project small-project

# Check system resources
top -p $(pgrep -f qdrant-loader)
```

**Configuration Fix:**

```yaml
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
          max_file_size: 524288  # 512KB per file
          file_types:
            - "md"
            - "txt"
```

### `ResourceError: Too many open files`

**Full Error:**

```text
ResourceError: [Errno 24] Too many open files
```

**Causes:**

- File descriptor limit exceeded
- Resource leak
- Too many concurrent operations
- System limits

**Solutions:**

```bash
# Check current limits
ulimit -n

# Increase file descriptor limit
ulimit -n 65536

# Set system limits permanently
echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf

# Process fewer files at once
qdrant-loader ingest --workspace . --project small-batch
```

### `DiskSpaceError: No space left on device`

**Full Error:**

```text
DiskSpaceError: [Errno 28] No space left on device
```

**Causes:**

- Disk full
- Large temporary files
- Log files growing
- Cache accumulation

**Solutions:**

```bash
# Check disk space
df -h

# Clean up temporary files
rm -rf /tmp/qdrant-loader-*

# Clean logs
sudo journalctl --vacuum-time=7d

# Use different temporary directory
export TMPDIR="/path/to/larger/disk"

# Check project status
qdrant-loader project status --workspace .
```

## 📁 File System Errors

### `FileNotFoundError: No such file or directory`

**Full Error:**

```text
FileNotFoundError: [Errno 2] No such file or directory: '/path/to/docs'
```

**Causes:**

- Path doesn't exist
- Typo in path
- Permission denied
- Symbolic link broken

**Solutions:**

```bash
# Check if path exists
ls -la /path/to/docs

# Use absolute path
qdrant-loader config --workspace .

# Check permissions
ls -ld /path/to/docs

# Find correct path
find / -name "docs" -type d 2>/dev/null

# Validate project configuration
qdrant-loader project status --workspace . --project-id my-project
```

### `PermissionError: Permission denied`

**Full Error:**

```text
PermissionError: [Errno 13] Permission denied: '/restricted/docs'
```

**Causes:**

- Insufficient file permissions
- Directory not readable
- SELinux restrictions
- File ownership issues

**Solutions:**

```bash
# Check permissions
ls -la /restricted/docs

# Change permissions (if appropriate)
chmod -R 755 /restricted/docs

# Check file ownership
ls -la /restricted/docs
chown -R $USER:$USER /restricted/docs

# Validate configuration
qdrant-loader project validate --workspace .
```

### `EncodingError: Unable to decode file`

**Full Error:**

```text
EncodingError: 'utf-8' codec can't decode byte 0xff in position 0
```

**Causes:**

- Binary file processed as text
- Wrong character encoding
- Corrupted file
- Unsupported format

**Solutions:**

```bash
# Check file type
file /path/to/problematic-file

# Detect encoding
chardet /path/to/problematic-file

# Check project configuration
qdrant-loader config --workspace .
```

**Configuration Fix:**

```yaml
projects:
  my-project:
    sources:
      localfile:
        docs:
          file_types:
            - "md"
            - "txt"
            - "rst"
          exclude_paths:
            - "*.pdf"
            - "*.jpg"
            - "*.png"
            - "*.zip"
            - "*.bin"
```

## 🌐 Network Errors

### `NetworkError: Name or service not known`

**Full Error:**

```text
NetworkError: [Errno -2] Name or service not known: 'invalid-host.com'
```

**Causes:**

- DNS resolution failure
- Invalid hostname
- Network connectivity issues
- DNS server problems

**Solutions:**

```bash
# Test DNS resolution
nslookup invalid-host.com
dig invalid-host.com

# Try different DNS server
nslookup invalid-host.com 8.8.8.8

# Check network connectivity
ping 8.8.8.8

# Validate configuration
qdrant-loader project validate --workspace .
```

**Configuration Fix:**

```yaml
global:
  qdrant:
    url: "http://192.168.1.100:6333"  # Use IP instead of hostname
    api_key: "${QDRANT_API_KEY}"
    collection_name: "${QDRANT_COLLECTION_NAME}"
```

### `SSLError: Certificate verification failed`

**Full Error:**

```text
SSLError: HTTPSConnectionPool(host='api.openai.com', port=443):
Max retries exceeded with url: /v1/embeddings
(Caused by SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED]')))
```

**Causes:**

- Expired SSL certificate
- Self-signed certificate
- Certificate chain issues
- System time incorrect

**Solutions:**

```bash
# Check certificate
openssl s_client -connect api.openai.com:443 -servername api.openai.com

# Update certificates
sudo apt-get update && sudo apt-get install ca-certificates

# Check system time
date
sudo ntpdate -s time.nist.gov

# Temporary workaround (NOT for production)
export PYTHONHTTPSVERIFY=0

# Test configuration
qdrant-loader project validate --workspace .
```

### `ProxyError: Cannot connect to proxy`

**Full Error:**

```text
ProxyError: HTTPSConnectionPool(host='proxy.company.com', port=8080):
Max retries exceeded
```

**Causes:**

- Proxy server down
- Wrong proxy configuration
- Authentication required
- Proxy blocking requests

**Solutions:**

```bash
# Test proxy connectivity
curl --proxy "http://proxy.company.com:8080" -v "https://google.com"

# Configure proxy authentication
export HTTP_PROXY="http://username:password@proxy.company.com:8080"

# Bypass proxy for specific hosts
export NO_PROXY="localhost,127.0.0.1,.local"

# Check proxy settings
env | grep -i proxy

# Test configuration
qdrant-loader project validate --workspace .
```

## 📊 Error Code Reference

### Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success | Continue normally |
| 1 | General error | Check logs and configuration |
| 2 | Configuration error | Fix configuration file |
| 3 | Connection error | Check network and credentials |
| 4 | Authentication error | Verify API keys and permissions |
| 5 | Data error | Check input data and formats |
| 6 | Resource error | Check memory, disk, and limits |
| 7 | Permission error | Check file and directory permissions |
| 8 | Network error | Check connectivity and DNS |

### HTTP Status Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 400 | Bad Request | Invalid parameters, malformed request |
| 401 | Unauthorized | Invalid API key, expired token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Collection/resource doesn't exist |
| 429 | Rate Limited | Too many requests, quota exceeded |
| 500 | Server Error | QDrant instance issues |
| 502 | Bad Gateway | Proxy/load balancer issues |
| 503 | Service Unavailable | Service overloaded or down |
| 504 | Gateway Timeout | Request timeout through proxy |

## 🚨 Emergency Error Recovery

### Critical Error Recovery

```bash
# When everything fails
# 1. Check system resources
top
df -h
free -h

# 2. Validate configuration
qdrant-loader project validate --workspace .

# 3. Check project status
qdrant-loader project status --workspace .

# 4. Restart with minimal configuration
qdrant-loader init --workspace . --force
qdrant-loader ingest --workspace . --project small-project
```

### Error Prevention

```bash
# Pre-flight checks
qdrant-loader project validate --workspace .

# Configuration validation
qdrant-loader config --workspace .

# Check project status before processing
qdrant-loader project status --workspace .

# Monitor system resources
htop
free -h
df -h
```

## 🔗 Related Documentation

- **[Common Issues](./common-issues.md)** - General troubleshooting
- **[Performance Issues](./performance-issues.md)** - Performance optimization
- **[Connection Problems](./connection-problems.md)** - Network and connectivity
- **[Configuration Reference](../configuration/config-file-reference.md)** - Configuration options
- **[CLI Reference](../cli-reference/README.md)** - Command-line interface

---

**Error messages decoded!** 🔍

This comprehensive reference covers all common error messages using actual QDrant Loader commands and configuration options. For general troubleshooting, see the [Common Issues Guide](./common-issues.md), and for specific problem types, check the specialized troubleshooting guides.
