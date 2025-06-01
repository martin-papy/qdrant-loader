# Performance Issues Guide

This guide helps you diagnose and resolve performance issues with QDrant Loader, including slow data loading, poor search performance, memory problems, and optimization strategies. Whether you're dealing with large datasets or need to improve response times, this guide provides practical solutions.

## 🎯 Performance Issue Types

### Quick Diagnosis

```
🐌 Slow data loading         → See [Loading Performance](#loading-performance-issues)
🔍 Slow search responses     → See [Search Performance](#search-performance-issues)
💾 High memory usage         → See [Memory Issues](#memory-issues)
🔥 High CPU usage           → See [CPU Issues](#cpu-issues)
📊 Poor throughput          → See [Throughput Optimization](#throughput-optimization)
🌐 Network bottlenecks      → See [Network Performance](#network-performance)
```

## 📊 Performance Monitoring

### Basic Performance Metrics

```bash
# Check system resources
htop
iostat -x 1
free -h

# Monitor QDrant Loader performance
qdrant-loader status --collection your_collection --performance

# Check QDrant instance metrics
curl -s "$QDRANT_URL/metrics" | grep -E "(memory|cpu|disk)"

# Monitor network usage
iftop
nethogs
```

### Performance Benchmarking

```bash
# Benchmark data loading
time qdrant-loader load --source local --path ./large-dataset --verbose

# Benchmark search performance
time qdrant-loader search "test query" --collection your_collection --limit 10

# Stress test search
for i in {1..100}; do
  qdrant-loader search "query $i" --collection your_collection --limit 5
done
```

## 🚀 Loading Performance Issues

### Issue: Slow data loading

**Symptoms:**

- Loading takes much longer than expected
- High CPU usage during loading
- Memory usage grows continuously
- Process appears to hang

**Diagnostic Steps:**

```bash
# Check file sizes and counts
find ./docs -type f -name "*.md" -exec wc -c {} + | sort -n
find ./docs -type f | wc -l

# Monitor loading progress
qdrant-loader load --source local --path ./docs --verbose --progress

# Check chunk processing
qdrant-loader load --source local --path ./docs --chunk-size 500 --dry-run --verbose
```

**Optimization Solutions:**

1. **Optimize chunk size:**

```yaml
# Configuration optimization
processing:
  chunk_size: 800        # Reduce from default 1200
  chunk_overlap: 150     # Reduce from default 300
  parallel_workers: 8    # Increase based on CPU cores
```

2. **Use parallel processing:**

```bash
# Enable parallel processing
qdrant-loader load --source local --path ./docs --workers 8

# Process in batches
qdrant-loader load --source local --path ./docs --batch-size 50
```

3. **Filter unnecessary files:**

```yaml
# Exclude large or unnecessary files
data_sources:
  local:
    paths:
      - path: "./docs"
        exclude_patterns:
          - "*.pdf"      # Skip large PDFs if not needed
          - "*.zip"
          - "node_modules/**"
          - ".git/**"
```

### Issue: Memory usage grows during loading

**Symptoms:**

- RAM usage increases continuously
- System becomes unresponsive
- Out of memory errors
- Swap usage increases

**Solutions:**

```bash
# Monitor memory usage
watch -n 1 'free -h && ps aux | grep qdrant-loader'

# Use memory-efficient loading
qdrant-loader load --source local --path ./docs --memory-limit 2GB

# Process in smaller batches
qdrant-loader load --source local --path ./docs --batch-size 10 --workers 2
```

**Memory Optimization:**

```yaml
# Memory-efficient configuration
processing:
  batch_size: 20         # Smaller batches
  parallel_workers: 2    # Fewer workers
  memory_limit: "2GB"    # Set memory limit
  cleanup_interval: 100  # Clean up more frequently

# Disable features that use more memory
features:
  duplicate_detection: false  # Disable if not needed
  content_extraction: minimal # Reduce extraction depth
```

### Issue: Loading fails with large files

**Symptoms:**

- Loading stops on specific large files
- Timeout errors
- Memory allocation errors
- Chunk processing failures

**Solutions:**

```bash
# Identify large files
find ./docs -type f -size +10M -exec ls -lh {} \;

# Skip large files temporarily
qdrant-loader load --source local --path ./docs --max-file-size 5MB

# Process large files separately with different settings
qdrant-loader load --source local --path ./large-files \
  --chunk-size 2000 --chunk-overlap 400 --workers 1
```

## 🔍 Search Performance Issues

### Issue: Slow search responses

**Symptoms:**

- Search takes more than 2-3 seconds
- Timeouts on search requests
- High CPU usage during search
- Inconsistent response times

**Diagnostic Steps:**

```bash
# Benchmark search performance
time qdrant-loader search "test query" --collection your_collection

# Check collection size and optimization
qdrant-loader status --collection your_collection --detailed

# Test different search parameters
qdrant-loader search "query" --collection your_collection --limit 5 --threshold 0.7
```

**Optimization Solutions:**

1. **Optimize collection:**

```bash
# Optimize collection structure
qdrant-loader optimize --collection your_collection

# Rebuild with better parameters
qdrant-loader load --source local --path ./docs \
  --chunk-size 800 --chunk-overlap 200 --force
```

2. **Tune search parameters:**

```bash
# Use higher similarity threshold
qdrant-loader search "query" --threshold 0.8 --limit 5

# Enable search caching
qdrant-loader search "query" --cache --cache-ttl 300
```

3. **QDrant instance optimization:**

```yaml
# QDrant configuration optimization
qdrant:
  url: "${QDRANT_URL}"
  api_key: "${QDRANT_API_KEY}"
  timeout: 30
  max_retries: 3
  
  # Performance settings
  performance:
    search_timeout: 10
    batch_size: 100
    parallel_searches: 4
```

### Issue: Poor search quality affecting performance

**Symptoms:**

- Need to search through many results to find relevant content
- Low similarity scores require broader searches
- Multiple search attempts needed

**Solutions:**

```bash
# Improve embedding quality
qdrant-loader load --source local --path ./docs \
  --embedding-model "text-embedding-3-large" --force

# Use better chunking strategy
qdrant-loader load --source local --path ./docs \
  --chunk-strategy semantic --chunk-size 1000 --force

# Add metadata for filtering
qdrant-loader search "query" --filter "content_type:documentation" --limit 5
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
pmap $(pgrep qdrant-loader)

# Check for memory leaks
valgrind --tool=memcheck qdrant-loader load --source local --path ./small-test
```

**Solutions:**

```bash
# Set memory limits
ulimit -m 2097152  # 2GB limit
qdrant-loader load --source local --path ./docs --memory-limit 2GB

# Use streaming processing
qdrant-loader load --source local --path ./docs --streaming --batch-size 10

# Clear cache periodically
qdrant-loader cache clear
```

### Issue: Memory leaks

**Symptoms:**

- Memory usage grows over time
- Performance degrades with usage
- Eventually runs out of memory

**Solutions:**

```bash
# Restart MCP server periodically
qdrant-loader mcp-server restart

# Use process monitoring
while true; do
  qdrant-loader mcp-server status
  sleep 300  # Check every 5 minutes
done

# Set automatic restart
qdrant-loader mcp-server start --auto-restart --memory-limit 1GB
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
# Limit CPU usage
nice -n 10 qdrant-loader load --source local --path ./docs

# Reduce parallel workers
qdrant-loader load --source local --path ./docs --workers 2

# Use CPU throttling
cpulimit -l 50 qdrant-loader load --source local --path ./docs
```

**CPU Optimization:**

```yaml
# CPU-efficient configuration
processing:
  parallel_workers: 2      # Reduce based on available cores
  cpu_limit: "50%"         # Limit CPU usage
  priority: "low"          # Lower process priority
  
  # Reduce processing intensity
  chunk_overlap: 100       # Smaller overlap
  embedding_batch_size: 10 # Smaller batches
```

## 📈 Throughput Optimization

### Optimizing Data Loading Throughput

```bash
# Parallel source processing
qdrant-loader load \
  --source git --url repo1 \
  --source git --url repo2 \
  --source local --path ./docs \
  --parallel-sources

# Batch optimization
qdrant-loader load --source local --path ./docs \
  --batch-size 100 \
  --workers 8 \
  --chunk-size 1000
```

### Optimizing Search Throughput

```bash
# Enable search result caching
qdrant-loader mcp-server start --cache-enabled --cache-size 1GB

# Use connection pooling
qdrant-loader search "query" --connection-pool-size 10

# Batch search requests
qdrant-loader search-batch queries.txt --output results.json
```

## 🌐 Network Performance

### Issue: Slow network operations

**Symptoms:**

- Slow loading from remote sources
- Timeouts connecting to QDrant
- High network latency
- Connection drops

**Diagnostic Steps:**

```bash
# Test network connectivity
ping your-qdrant-instance.com
curl -w "@curl-format.txt" -o /dev/null -s "$QDRANT_URL/health"

# Check bandwidth
iperf3 -c your-qdrant-instance.com

# Monitor network usage
iftop -i eth0
```

**Solutions:**

```bash
# Use compression
qdrant-loader load --source git --url repo --compression gzip

# Increase timeouts
qdrant-loader load --source confluence --timeout 60

# Use local caching
qdrant-loader load --source git --url repo --cache-locally
```

**Network Optimization:**

```yaml
# Network-optimized configuration
network:
  timeout: 60
  max_retries: 5
  retry_delay: 2
  compression: true
  keep_alive: true
  connection_pool_size: 10

# Use CDN or local mirrors
data_sources:
  git:
    repositories:
      - url: "https://cdn.company.com/docs.git"  # Use CDN
        local_cache: true
```

## 🔧 Advanced Optimization

### QDrant Instance Optimization

```yaml
# QDrant configuration for performance
qdrant:
  url: "${QDRANT_URL}"
  api_key: "${QDRANT_API_KEY}"
  
  # Performance tuning
  collection_config:
    vectors:
      size: 1536
      distance: "Cosine"
    optimizers_config:
      default_segment_number: 2
      max_segment_size: 20000
      memmap_threshold: 50000
    hnsw_config:
      m: 16
      ef_construct: 100
      full_scan_threshold: 10000
```

### System-Level Optimization

```bash
# Increase file descriptor limits
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf

# Optimize disk I/O
echo mq-deadline > /sys/block/sda/queue/scheduler

# Tune network settings
echo 'net.core.rmem_max = 16777216' >> /etc/sysctl.conf
echo 'net.core.wmem_max = 16777216' >> /etc/sysctl.conf
sysctl -p
```

### Monitoring and Alerting

```bash
# Set up performance monitoring
qdrant-loader monitor start --metrics-port 9090

# Create performance alerts
qdrant-loader alert create \
  --metric "search_latency" \
  --threshold 2000 \
  --action "restart_mcp_server"

# Generate performance reports
qdrant-loader report performance --period 24h --output performance-report.html
```

## 📊 Performance Tuning Presets

### Small Dataset (< 1GB)

```yaml
processing:
  chunk_size: 1200
  chunk_overlap: 300
  parallel_workers: 4
  batch_size: 50

qdrant:
  collection_config:
    optimizers_config:
      default_segment_number: 1
      max_segment_size: 10000
```

### Medium Dataset (1-10GB)

```yaml
processing:
  chunk_size: 1000
  chunk_overlap: 200
  parallel_workers: 8
  batch_size: 100

qdrant:
  collection_config:
    optimizers_config:
      default_segment_number: 2
      max_segment_size: 20000
```

### Large Dataset (> 10GB)

```yaml
processing:
  chunk_size: 800
  chunk_overlap: 150
  parallel_workers: 16
  batch_size: 200
  streaming: true

qdrant:
  collection_config:
    optimizers_config:
      default_segment_number: 4
      max_segment_size: 50000
      memmap_threshold: 100000
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

# 3. Clear caches
qdrant-loader cache clear
sync && echo 3 > /proc/sys/vm/drop_caches

# 4. Restart with minimal settings
qdrant-loader mcp-server start --workers 1 --memory-limit 512MB
```

### Performance Recovery

```bash
# 1. Optimize collections
qdrant-loader optimize --collection your_collection --force

# 2. Rebuild indexes
qdrant-loader reindex --collection your_collection

# 3. Clean up old data
qdrant-loader cleanup --collection your_collection --older-than 30d

# 4. Restart services
qdrant-loader mcp-server restart
```

## 📈 Performance Monitoring Dashboard

### Key Metrics to Track

```bash
# Create monitoring dashboard
qdrant-loader dashboard create --metrics \
  "search_latency,load_throughput,memory_usage,cpu_usage,disk_io"

# Set up alerts
qdrant-loader alert create --metric search_latency --threshold 2000ms
qdrant-loader alert create --metric memory_usage --threshold 80%
qdrant-loader alert create --metric cpu_usage --threshold 90%
```

### Performance Reports

```bash
# Generate daily performance report
qdrant-loader report performance \
  --period 24h \
  --metrics all \
  --output daily-performance.html

# Weekly trend analysis
qdrant-loader report trends \
  --period 7d \
  --output weekly-trends.json
```

## 🔗 Related Documentation

- **[Common Issues](./common-issues.md)** - General troubleshooting
- **[Connection Problems](./connection-problems.md)** - Network and connectivity issues
- **[Advanced Settings](../configuration/advanced-settings.md)** - Performance configuration
- **[CLI Reference](../cli/commands-reference.md)** - Command-line options
- **[System Requirements](../getting-started/installation.md#system-requirements)** - Hardware recommendations

---

**Performance optimized!** 🚀

This guide covers comprehensive performance optimization strategies. For specific error messages, check the [Error Messages Reference](./error-messages-reference.md), and for general issues, see the [Common Issues Guide](./common-issues.md).
