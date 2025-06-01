# Error Messages Reference

This comprehensive reference guide provides detailed explanations and solutions for all error messages you might encounter when using QDrant Loader. Each error includes the exact message, possible causes, and step-by-step solutions.

## 🎯 Error Categories

### Quick Navigation

```
🔌 Connection Errors        → See [Connection Errors](#connection-errors)
🔑 Authentication Errors    → See [Authentication Errors](#authentication-errors)
📊 Data Loading Errors      → See [Data Loading Errors](#data-loading-errors)
⚙️ Configuration Errors     → See [Configuration Errors](#configuration-errors)
🔍 Search Errors           → See [Search Errors](#search-errors)
💾 Memory/Resource Errors   → See [Memory and Resource Errors](#memory-and-resource-errors)
📁 File System Errors      → See [File System Errors](#file-system-errors)
🌐 Network Errors          → See [Network Errors](#network-errors)
```

## 🔌 Connection Errors

### `ConnectionError: Failed to connect to QDrant instance`

**Full Error:**

```
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

# Verify URL format
export QDRANT_URL="http://localhost:6333"  # Local
export QDRANT_URL="https://your-instance.qdrant.cloud"  # Cloud

# Test connectivity
ping your-qdrant-instance.com
telnet your-qdrant-instance.com 6333
```

### `ConnectionRefusedError: [Errno 111] Connection refused`

**Full Error:**

```
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
```

### `TimeoutError: Connection timeout after 30 seconds`

**Full Error:**

```
TimeoutError: Connection timeout after 30 seconds
```

**Causes:**

- Network latency issues
- Server overloaded
- Firewall dropping packets
- DNS resolution slow

**Solutions:**

```bash
# Increase timeout
qdrant-loader config set qdrant.timeout 60

# Test network latency
ping -c 10 your-qdrant-instance.com

# Use IP address instead of hostname
export QDRANT_URL="http://192.168.1.100:6333"
```

## 🔑 Authentication Errors

### `AuthenticationError: Invalid API key`

**Full Error:**

```
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
```

### `OpenAIError: Incorrect API key provided`

**Full Error:**

```
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
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  "https://api.openai.com/v1/models"

# Check account status
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  "https://api.openai.com/v1/usage"
```

### `ConfluenceAuthError: 401 Unauthorized`

**Full Error:**

```
ConfluenceAuthError: 401 Unauthorized - Check your credentials
```

**Causes:**

- Wrong username or API token
- API token expired
- Insufficient permissions
- Account locked

**Solutions:**

```bash
# Test Confluence authentication
curl -u "$CONFLUENCE_USERNAME:$CONFLUENCE_API_TOKEN" \
  "$CONFLUENCE_URL/rest/api/content?limit=1"

# Verify credentials format
echo "Username: $CONFLUENCE_USERNAME"
echo "Token length: $(echo $CONFLUENCE_API_TOKEN | wc -c)"

# Check permissions
curl -u "$CONFLUENCE_USERNAME:$CONFLUENCE_API_TOKEN" \
  "$CONFLUENCE_URL/rest/api/user/current"
```

## 📊 Data Loading Errors

### `DataLoadError: No documents found in source`

**Full Error:**

```
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

# Verify file patterns
qdrant-loader config show | grep -A 5 include_patterns

# Test with broader patterns
qdrant-loader load --source local --path /path/to/docs \
  --include-pattern "**/*" --dry-run
```

### `ChunkingError: Failed to process document`

**Full Error:**

```
ChunkingError: Failed to process document: document.pdf - File too large
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

# Set larger size limit
qdrant-loader load --source local --path /path/to/docs \
  --max-file-size 50MB

# Process large files separately
qdrant-loader load --source local --path /path/to/large-files \
  --chunk-size 2000 --workers 1
```

### `EmbeddingError: Failed to generate embeddings`

**Full Error:**

```
EmbeddingError: Failed to generate embeddings for chunk: Rate limit exceeded
```

**Causes:**

- OpenAI rate limits
- API quota exceeded
- Network issues
- Invalid content

**Solutions:**

```bash
# Add rate limiting
qdrant-loader load --source local --path /path/to/docs \
  --rate-limit 10 --batch-size 5

# Check API usage
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  "https://api.openai.com/v1/usage"

# Use smaller batches
qdrant-loader load --source local --path /path/to/docs \
  --embedding-batch-size 10
```

## ⚙️ Configuration Errors

### `ConfigurationError: Invalid YAML syntax`

**Full Error:**

```
ConfigurationError: Invalid YAML syntax in qdrant-loader.yaml at line 15
```

**Causes:**

- YAML indentation errors
- Missing quotes
- Invalid characters
- Malformed structure

**Solutions:**

```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('qdrant-loader.yaml'))"

# Check specific line
sed -n '15p' qdrant-loader.yaml

# Use YAML validator
yamllint qdrant-loader.yaml

# Generate valid config
qdrant-loader config init --example
```

### `ValidationError: Missing required field 'qdrant.url'`

**Full Error:**

```
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
qdrant-loader config validate --verbose

# Set required fields
export QDRANT_URL="http://localhost:6333"

# Use configuration template
qdrant-loader config init --template minimal
```

### `EnvironmentError: Environment variable not found`

**Full Error:**

```
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

# Use explicit configuration
qdrant-loader load --qdrant-api-key "your-key" --source local --path ./docs
```

## 🔍 Search Errors

### `SearchError: Collection not found`

**Full Error:**

```
SearchError: Collection 'my_collection' not found in QDrant instance
```

**Causes:**

- Collection doesn't exist
- Wrong collection name
- Collection deleted
- Permission issues

**Solutions:**

```bash
# List available collections
qdrant-loader collection list

# Create collection
qdrant-loader collection create my_collection

# Check collection status
qdrant-loader status --collection my_collection

# Use correct collection name
qdrant-loader search "query" --collection correct_name
```

### `SearchError: Empty query provided`

**Full Error:**

```
SearchError: Empty query provided - search query cannot be empty
```

**Causes:**

- No search query specified
- Query string is whitespace only
- Variable not set
- Command line parsing issue

**Solutions:**

```bash
# Provide valid query
qdrant-loader search "your search query"

# Check for whitespace
qdrant-loader search "$(echo 'your query' | xargs)"

# Use quotes for complex queries
qdrant-loader search "query with spaces and symbols"
```

### `SearchError: No results found`

**Full Error:**

```
SearchError: No results found for query 'test' in collection 'docs'
```

**Causes:**

- Collection is empty
- Query too specific
- Similarity threshold too high
- Wrong collection

**Solutions:**

```bash
# Check collection has data
qdrant-loader status --collection docs

# Lower similarity threshold
qdrant-loader search "test" --threshold 0.3

# Try broader query
qdrant-loader search "test" --limit 10

# Check different collection
qdrant-loader search "test" --collection other_collection
```

## 💾 Memory and Resource Errors

### `MemoryError: Unable to allocate memory`

**Full Error:**

```
MemoryError: Unable to allocate 2.5 GB for document processing
```

**Causes:**

- Insufficient RAM
- Memory leak
- Large files
- Too many parallel workers

**Solutions:**

```bash
# Check available memory
free -h

# Reduce memory usage
qdrant-loader load --source local --path ./docs \
  --workers 2 --batch-size 10 --memory-limit 2GB

# Process smaller chunks
qdrant-loader load --source local --path ./docs \
  --chunk-size 500 --chunk-overlap 100
```

### `ResourceError: Too many open files`

**Full Error:**

```
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

# Reduce concurrent operations
qdrant-loader load --source local --path ./docs --workers 2

# Set system limits permanently
echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
```

### `DiskSpaceError: No space left on device`

**Full Error:**

```
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
qdrant-loader cache clear
rm -rf /tmp/qdrant-loader-*

# Clean logs
sudo journalctl --vacuum-time=7d

# Use different temporary directory
export TMPDIR="/path/to/larger/disk"
```

## 📁 File System Errors

### `FileNotFoundError: No such file or directory`

**Full Error:**

```
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
qdrant-loader load --source local --path "$(pwd)/docs"

# Check permissions
ls -ld /path/to/docs

# Find correct path
find / -name "docs" -type d 2>/dev/null
```

### `PermissionError: Permission denied`

**Full Error:**

```
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

# Run with sudo (if necessary)
sudo qdrant-loader load --source local --path /restricted/docs

# Check file ownership
ls -la /restricted/docs
chown -R $USER:$USER /restricted/docs
```

### `EncodingError: Unable to decode file`

**Full Error:**

```
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

# Skip binary files
qdrant-loader load --source local --path ./docs \
  --exclude-pattern "*.pdf,*.jpg,*.png,*.zip"

# Specify encoding
qdrant-loader load --source local --path ./docs \
  --encoding "latin-1"
```

## 🌐 Network Errors

### `NetworkError: Name or service not known`

**Full Error:**

```
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

# Use IP address
export QDRANT_URL="http://192.168.1.100:6333"

# Check network connectivity
ping 8.8.8.8
```

### `SSLError: Certificate verification failed`

**Full Error:**

```
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
```

### `ProxyError: Cannot connect to proxy`

**Full Error:**

```
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
```

## 🔧 Advanced Error Handling

### Error Recovery Strategies

```bash
# Automatic retry with exponential backoff
qdrant-loader load --source local --path ./docs \
  --max-retries 5 --retry-delay 2 --exponential-backoff

# Graceful degradation
qdrant-loader load --source local --path ./docs \
  --continue-on-error --skip-failed-files

# Detailed error logging
qdrant-loader load --source local --path ./docs \
  --verbose --log-file error.log --log-level DEBUG
```

### Error Monitoring and Alerting

```bash
# Set up error monitoring
qdrant-loader monitor errors --alert-threshold 10 --alert-email admin@company.com

# Generate error reports
qdrant-loader report errors --period 24h --output error-report.html

# Custom error handling
qdrant-loader load --source local --path ./docs \
  --error-handler custom_handler.py
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
qdrant-loader emergency-recovery --backup-config --reset-cache

# Safe mode operation
qdrant-loader load --source local --path ./docs --safe-mode

# Minimal configuration test
qdrant-loader config test --minimal --verbose
```

### Error Prevention

```bash
# Pre-flight checks
qdrant-loader preflight-check --source local --path ./docs

# Configuration validation
qdrant-loader config validate --strict

# Dry run before actual operation
qdrant-loader load --source local --path ./docs --dry-run
```

## 🔗 Related Documentation

- **[Common Issues](./common-issues.md)** - General troubleshooting
- **[Performance Issues](./performance-issues.md)** - Performance optimization
- **[Connection Problems](./connection-problems.md)** - Network and connectivity
- **[Configuration Reference](../configuration/config-file-reference.md)** - Configuration options
- **[CLI Reference](../cli/commands-reference.md)** - Command-line interface

---

**Error messages decoded!** 🔍

This comprehensive reference covers all common error messages. For general troubleshooting, see the [Common Issues Guide](./common-issues.md), and for specific problem types, check the specialized troubleshooting guides.
