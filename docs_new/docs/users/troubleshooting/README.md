# Troubleshooting Guide

Having issues with QDrant Loader? This section provides solutions to common problems, debugging techniques, and guidance for getting help when you need it.

## 🎯 Quick Problem Solving

### Most Common Issues

| Problem | Quick Solution | Detailed Guide |
|---------|---------------|----------------|
| **Authentication failed** | Check API keys and permissions | [Data Source Issues](./data-source-issues.md#authentication-problems) |
| **Slow processing** | Adjust batch size and concurrency | [Performance Optimization](./performance-optimization.md) |
| **Out of memory** | Reduce chunk size and file limits | [Performance Optimization](./performance-optimization.md#memory-management) |
| **Connection timeout** | Increase timeout settings | [Common Issues](./common-issues.md#connection-timeouts) |
| **File conversion fails** | Check file format support | [Common Issues](./common-issues.md#file-conversion-issues) |

### Quick Diagnostic Commands

```bash
# Check configuration validity
qdrant-loader --workspace . validate

# Test data source connections
qdrant-loader --workspace . test-connections

# View current status
qdrant-loader --workspace . status --verbose

# Check processing statistics
qdrant-loader --workspace . stats
```

## 📚 Troubleshooting Sections

### 🔧 [Common Issues](./common-issues.md)

Frequently encountered problems and their solutions:

- **Configuration errors** - Invalid settings and missing requirements
- **Authentication problems** - API key and permission issues
- **File processing errors** - Format support and conversion problems
- **Connection timeouts** - Network and API limit issues
- **Memory and performance** - Resource usage optimization

### 📊 [Performance Optimization](./performance-optimization.md)

Speed up processing and reduce resource usage:

- **Memory management** - Optimize memory usage for large datasets
- **Processing speed** - Improve throughput and reduce processing time
- **Network optimization** - Handle rate limits and connection issues
- **Storage optimization** - Efficient disk usage and caching

### 🔌 [Data Source Issues](./data-source-issues.md)

Source-specific troubleshooting:

- **Git repository problems** - Authentication, cloning, and access issues
- **Confluence issues** - API limits, permissions, and content access
- **JIRA problems** - Project access, issue types, and API configuration
- **Local file issues** - Permissions, paths, and file format problems
- **Public documentation** - Web scraping and access restrictions

### 🆘 [Getting Help](./getting-help.md)

How to get effective support:

- **Gathering information** - What to include in bug reports
- **Community resources** - Where to ask questions and get help
- **Bug reporting** - How to report issues effectively
- **Feature requests** - How to suggest improvements

## 🚀 Quick Fixes

### Configuration Problems

```bash
# Problem: "Configuration file not found"
# Solution: Ensure config.yaml exists in workspace
ls -la config.yaml
# If missing, download template:
curl -o config.yaml https://raw.githubusercontent.com/martin-papy/qdrant-loader/main/packages/qdrant-loader/conf/config.template.yaml

# Problem: "Invalid YAML syntax"
# Solution: Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Problem: "Missing environment variables"
# Solution: Check required variables
qdrant-loader --workspace . validate
```

### Authentication Issues

```bash
# Problem: "GitHub authentication failed"
# Solution: Check token validity
curl -H "Authorization: token $REPO_TOKEN" https://api.github.com/user

# Problem: "Confluence access denied"
# Solution: Test Confluence connection
curl -u "$CONFLUENCE_EMAIL:$CONFLUENCE_TOKEN" \
  "$CONFLUENCE_URL/rest/api/space"

# Problem: "JIRA authentication failed"
# Solution: Verify JIRA credentials
curl -u "$JIRA_EMAIL:$JIRA_TOKEN" \
  "$JIRA_URL/rest/api/2/myself"
```

### Performance Issues

```bash
# Problem: "Processing too slow"
# Solution: Increase batch size and concurrency
# Edit config.yaml:
batch_size: 100
max_concurrent_requests: 10

# Problem: "Out of memory"
# Solution: Reduce chunk size and file limits
# Edit config.yaml:
chunk_size: 500
max_file_size: 1048576  # 1MB
```

### Connection Problems

```bash
# Problem: "QDrant connection failed"
# Solution: Check QDrant status
curl $QDRANT_URL/collections

# Problem: "OpenAI API error"
# Solution: Test API key
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/models

# Problem: "Network timeouts"
# Solution: Increase timeout settings
# Edit config.yaml:
timeout_seconds: 60
retry_attempts: 5
```

## 🔍 Diagnostic Tools

### Built-in Diagnostics

```bash
# Comprehensive system check
qdrant-loader --workspace . validate --verbose

# Test all connections
qdrant-loader --workspace . test-connections --verbose

# Check processing status
qdrant-loader --workspace . status --verbose

# View detailed statistics
qdrant-loader --workspace . stats --verbose
```

### Manual Diagnostics

```bash
# Check Python environment
python --version
pip list | grep qdrant

# Check disk space
df -h .

# Check memory usage
free -h

# Check network connectivity
ping -c 3 api.openai.com
ping -c 3 github.com
```

### Log Analysis

```bash
# Enable debug logging
qdrant-loader --workspace . --log-level DEBUG ingest

# Save logs to file
qdrant-loader --workspace . \
              --log-level DEBUG \
              --log-file debug.log \
              ingest

# Analyze logs for errors
grep -i error debug.log
grep -i timeout debug.log
grep -i failed debug.log
```

## 🎯 Problem Categories

### By Symptom

#### "Command not found"

- **Cause**: QDrant Loader not installed or not in PATH
- **Solution**: Install with `pip install qdrant-loader`
- **Check**: `which qdrant-loader`

#### "Permission denied"

- **Cause**: Insufficient file permissions or API access
- **Solution**: Check file permissions and API credentials
- **Check**: File permissions with `ls -la`, API access with test commands

#### "Connection refused"

- **Cause**: Service not running or network issues
- **Solution**: Check service status and network connectivity
- **Check**: Service status, firewall settings, network connectivity

#### "Out of memory"

- **Cause**: Processing large files or datasets
- **Solution**: Reduce batch sizes and file limits
- **Check**: Memory usage with `free -h`, adjust configuration

#### "Processing stuck"

- **Cause**: Large files, network issues, or infinite loops
- **Solution**: Check logs, reduce file sizes, increase timeouts
- **Check**: Process status with `ps`, log files for errors

### By Component

#### QDrant Connection

```bash
# Test QDrant connectivity
curl $QDRANT_URL/collections
curl $QDRANT_URL/health

# Check collection status
curl $QDRANT_URL/collections/$QDRANT_COLLECTION_NAME
```

#### Data Sources

```bash
# Test Git access
git ls-remote $REPO_URL

# Test Confluence API
curl -u "$CONFLUENCE_EMAIL:$CONFLUENCE_TOKEN" \
  "$CONFLUENCE_URL/rest/api/space"

# Test JIRA API
curl -u "$JIRA_EMAIL:$JIRA_TOKEN" \
  "$JIRA_URL/rest/api/2/myself"
```

#### File Processing

```bash
# Check file conversion support
python -c "import markitdown; print('MarkItDown available')"

# Test file processing
qdrant-loader --workspace . --dry-run ingest --limit 1
```

## 🔧 Environment Debugging

### Python Environment

```bash
# Check Python version (3.8+ required)
python --version

# Check installed packages
pip list | grep -E "(qdrant|openai|requests)"

# Check for conflicts
pip check

# Reinstall if needed
pip uninstall qdrant-loader qdrant-loader-mcp-server
pip install qdrant-loader qdrant-loader-mcp-server
```

### System Resources

```bash
# Check available memory
free -h

# Check disk space
df -h .

# Check CPU usage
top -n 1 | head -5

# Check network connectivity
ping -c 3 api.openai.com
curl -I https://api.github.com
```

### Configuration Environment

```bash
# Check environment variables
env | grep -E "(QDRANT|OPENAI|CONFLUENCE|JIRA|REPO)"

# Validate configuration files
qdrant-loader --workspace . validate

# Check file permissions
ls -la config.yaml .env

# Test configuration loading
qdrant-loader --workspace . config --verbose
```

## 📊 Performance Monitoring

### Resource Usage

```bash
# Monitor during processing
top -p $(pgrep -f qdrant-loader)

# Memory usage over time
while true; do
  ps -p $(pgrep -f qdrant-loader) -o pid,vsz,rss,pcpu,pmem,time
  sleep 5
done

# Disk I/O monitoring
iostat -x 1
```

### Processing Metrics

```bash
# Processing speed
time qdrant-loader --workspace . ingest

# Detailed timing
/usr/bin/time -v qdrant-loader --workspace . ingest

# Statistics tracking
qdrant-loader --workspace . stats --format json > stats.json
```

## 🆘 When to Get Help

### Try Self-Help First

1. **Check this troubleshooting guide** - Most issues have solutions here
2. **Search existing issues** - Someone may have had the same problem
3. **Check the documentation** - Configuration and usage guides
4. **Try the diagnostic commands** - Built-in tools can identify problems

### Get Community Help When

- **Problem persists** after trying documented solutions
- **Error messages are unclear** or not covered in documentation
- **Need guidance** on best practices or configuration
- **Want to discuss** feature requests or improvements

### Report Bugs When

- **Reproducible errors** that seem like software bugs
- **Crashes or unexpected behavior** that shouldn't happen
- **Documentation errors** or missing information
- **Performance issues** that seem abnormal

## 📚 Related Documentation

- **[Common Issues](./common-issues.md)** - Detailed solutions to frequent problems
- **[Performance Optimization](./performance-optimization.md)** - Speed and memory optimization
- **[Data Source Issues](./data-source-issues.md)** - Source-specific troubleshooting
- **[Getting Help](./getting-help.md)** - How to get effective support
- **[Configuration Reference](../configuration/)** - Complete configuration options

## 🔗 Quick Links

### Community Resources

- **[GitHub Issues](https://github.com/martin-papy/qdrant-loader/issues)** - Bug reports and feature requests
- **[GitHub Discussions](https://github.com/martin-papy/qdrant-loader/discussions)** - Community Q&A
- **[Documentation](../../)** - Complete user and developer guides

### Diagnostic Commands

```bash
# Quick health check
qdrant-loader --workspace . validate && \
qdrant-loader --workspace . test-connections && \
qdrant-loader --workspace . status

# Full diagnostic
qdrant-loader --workspace . --verbose validate && \
qdrant-loader --workspace . --verbose test-connections && \
qdrant-loader --workspace . --verbose stats
```

---

**Still having issues?** Check the specific troubleshooting guides above or visit our [Getting Help](./getting-help.md) page for information on community support and bug reporting.
