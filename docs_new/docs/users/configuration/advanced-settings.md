# Advanced Settings & Performance Tuning

This guide covers advanced configuration options and performance tuning strategies for QDrant Loader. These settings help you optimize performance, memory usage, and processing efficiency for your specific use case and infrastructure.

## 🎯 Overview

Advanced settings allow you to fine-tune QDrant Loader's behavior for optimal performance in your environment. Whether you're processing large datasets, optimizing for speed, or managing resource constraints, these configurations help you get the best results.

### Performance Areas

```
🚀 Processing Speed    - Parallel processing, batch sizes, chunking
💾 Memory Usage       - Memory limits, caching, garbage collection
🔄 I/O Optimization   - Network settings, file handling, database tuning
⚡ Search Performance - Indexing, similarity thresholds, result caching
🔧 Resource Management - CPU usage, disk space, connection pooling
```

## 🚀 Processing Performance

### Parallel Processing Configuration

```yaml
# qdrant-loader.yaml - Parallel processing optimization
processing:
  parallel:
    # Number of worker processes (default: CPU count)
    workers: 8
    
    # Maximum files to process simultaneously
    max_concurrent_files: 20
    
    # Batch size for parallel processing
    batch_size: 100
    
    # Queue size for work distribution
    queue_size: 1000
    
    # Worker process configuration
    worker_config:
      # Memory limit per worker (in MB)
      memory_limit: 512
      
      # Timeout for worker processes (seconds)
      timeout: 300
      
      # Restart workers after N tasks (prevents memory leaks)
      max_tasks_per_worker: 1000
    
    # Load balancing strategy
    load_balancing: "round_robin"  # round_robin, least_loaded, random
    
    # Enable process monitoring
    monitoring:
      enabled: true
      log_interval: 60  # seconds

# Environment variables for parallel processing
# QDRANT_LOADER_WORKERS=8
# QDRANT_LOADER_MAX_CONCURRENT_FILES=20
# QDRANT_LOADER_BATCH_SIZE=100
```

### Chunking Optimization

```yaml
processing:
  chunking:
    # Advanced chunking strategy
    strategy: "adaptive"  # fixed, recursive, semantic, adaptive
    
    # Base chunk size (tokens)
    chunk_size: 1000
    
    # Chunk overlap (tokens)
    chunk_overlap: 200
    
    # Adaptive chunking settings
    adaptive:
      # Minimum chunk size
      min_chunk_size: 500
      
      # Maximum chunk size
      max_chunk_size: 2000
      
      # Adjust chunk size based on content type
      content_aware: true
      
      # Preserve sentence boundaries
      preserve_sentences: true
      
      # Preserve paragraph boundaries
      preserve_paragraphs: true
    
    # Content-specific chunking
    content_specific:
      # Code files
      code:
        chunk_size: 1500
        overlap: 100
        preserve_functions: true
        preserve_classes: true
      
      # Documentation
      documentation:
        chunk_size: 1200
        overlap: 300
        preserve_sections: true
        preserve_lists: true
      
      # API documentation
      api_docs:
        chunk_size: 800
        overlap: 150
        preserve_endpoints: true
        preserve_examples: true
    
    # Performance optimization
    optimization:
      # Cache tokenization results
      cache_tokenization: true
      
      # Parallel chunking
      parallel_chunking: true
      
      # Chunk validation
      validate_chunks: false  # Disable for speed
```

### File Processing Optimization

```yaml
processing:
  files:
    # File processing strategy
    strategy: "streaming"  # streaming, batch, memory_mapped
    
    # Maximum file size to process
    max_file_size: "200MB"
    
    # File reading buffer size
    buffer_size: "64KB"
    
    # Enable memory mapping for large files
    memory_mapping:
      enabled: true
      threshold: "10MB"  # Use memory mapping for files larger than this
    
    # File type specific settings
    file_types:
      pdf:
        # PDF processing engine
        engine: "pymupdf"  # pymupdf, pdfplumber, pdfminer
        
        # Extract images from PDFs
        extract_images: false
        
        # OCR for scanned PDFs
        ocr_enabled: false
        
        # Memory limit for PDF processing
        memory_limit: "1GB"
      
      docx:
        # Extract embedded objects
        extract_embedded: false
        
        # Process headers and footers
        include_headers_footers: true
        
        # Process comments
        include_comments: false
      
      xlsx:
        # Maximum rows to process per sheet
        max_rows: 10000
        
        # Process all sheets or just first
        all_sheets: false
        
        # Include formulas
        include_formulas: false
    
    # Caching
    caching:
      # Cache processed files
      enabled: true
      
      # Cache directory
      directory: "~/.qdrant-loader/cache"
      
      # Cache size limit
      max_size: "5GB"
      
      # Cache TTL (time to live)
      ttl: 86400  # 24 hours
      
      # Cache compression
      compression: true
```

## 💾 Memory Management

### Memory Optimization

```yaml
memory:
  # Global memory settings
  limits:
    # Maximum memory usage (total)
    max_total_memory: "8GB"
    
    # Maximum memory per process
    max_process_memory: "2GB"
    
    # Memory warning threshold
    warning_threshold: 0.8  # 80%
    
    # Memory cleanup threshold
    cleanup_threshold: 0.9  # 90%
  
  # Garbage collection settings
  garbage_collection:
    # Enable aggressive garbage collection
    aggressive: false
    
    # GC frequency (seconds)
    frequency: 300
    
    # Force GC after N operations
    force_after_operations: 1000
  
  # Memory monitoring
  monitoring:
    enabled: true
    
    # Log memory usage interval
    log_interval: 60  # seconds
    
    # Memory profiling
    profiling:
      enabled: false
      output_dir: "~/.qdrant-loader/profiles"
  
  # Memory optimization strategies
  optimization:
    # Use memory-efficient data structures
    efficient_structures: true
    
    # Stream large datasets
    streaming: true
    
    # Lazy loading
    lazy_loading: true
    
    # Memory pooling
    pooling:
      enabled: true
      pool_size: 100

# Environment variables for memory management
# QDRANT_LOADER_MAX_MEMORY=8GB
# QDRANT_LOADER_AGGRESSIVE_GC=false
```

### Caching Strategy

```yaml
caching:
  # Multi-level caching
  levels:
    # L1: In-memory cache
    memory:
      enabled: true
      max_size: "1GB"
      ttl: 3600  # 1 hour
      
      # LRU eviction policy
      eviction_policy: "lru"
      
      # Cache hit rate monitoring
      monitoring: true
    
    # L2: Disk cache
    disk:
      enabled: true
      directory: "~/.qdrant-loader/cache"
      max_size: "10GB"
      ttl: 86400  # 24 hours
      
      # Compression for disk cache
      compression:
        enabled: true
        algorithm: "lz4"  # lz4, gzip, zstd
        level: 1
    
    # L3: Distributed cache (Redis)
    distributed:
      enabled: false
      backend: "redis"
      
      redis:
        host: "localhost"
        port: 6379
        db: 0
        password: null
        
        # Connection pooling
        pool_size: 10
        
        # Serialization
        serialization: "pickle"  # pickle, json, msgpack
  
  # Cache warming
  warming:
    enabled: true
    
    # Warm cache on startup
    on_startup: true
    
    # Background cache warming
    background: true
    
    # Cache warming strategies
    strategies:
      - "frequent_queries"
      - "recent_documents"
      - "popular_collections"
  
  # Cache invalidation
  invalidation:
    # Automatic invalidation
    auto: true
    
    # Invalidation strategies
    strategies:
      - "time_based"  # TTL
      - "content_based"  # Content changes
      - "manual"  # Explicit invalidation
    
    # Batch invalidation
    batch_size: 100
```

## 🔄 I/O Optimization

### Network Configuration

```yaml
network:
  # Connection settings
  connections:
    # Maximum concurrent connections
    max_connections: 100
    
    # Connection timeout (seconds)
    timeout: 30
    
    # Read timeout (seconds)
    read_timeout: 60
    
    # Connection pooling
    pooling:
      enabled: true
      pool_size: 20
      max_overflow: 10
      
      # Pool recycle time (seconds)
      recycle: 3600
      
      # Pre-ping connections
      pre_ping: true
  
  # Retry configuration
  retry:
    # Maximum retry attempts
    max_attempts: 3
    
    # Retry delay (seconds)
    delay: 1
    
    # Exponential backoff
    backoff_factor: 2
    
    # Retry on specific errors
    retry_on:
      - "connection_error"
      - "timeout"
      - "rate_limit"
  
  # Rate limiting
  rate_limiting:
    enabled: true
    
    # Requests per second
    requests_per_second: 10
    
    # Burst capacity
    burst_capacity: 50
    
    # Rate limiting strategy
    strategy: "token_bucket"  # token_bucket, sliding_window
  
  # Compression
  compression:
    # Enable request compression
    enabled: true
    
    # Compression algorithm
    algorithm: "gzip"  # gzip, deflate, br
    
    # Compression level
    level: 6
    
    # Minimum size for compression
    min_size: 1024  # bytes

# Environment variables for network optimization
# QDRANT_LOADER_MAX_CONNECTIONS=100
# QDRANT_LOADER_CONNECTION_TIMEOUT=30
# QDRANT_LOADER_RATE_LIMIT=10
```

### Database Optimization

```yaml
qdrant:
  # Connection optimization
  connection:
    # Connection pool size
    pool_size: 20
    
    # Maximum overflow connections
    max_overflow: 10
    
    # Connection timeout
    timeout: 30
    
    # Keep-alive settings
    keep_alive:
      enabled: true
      interval: 60  # seconds
      
    # Connection validation
    validation:
      enabled: true
      query: "SELECT 1"
  
  # Batch operations
  batch:
    # Batch size for inserts
    insert_batch_size: 1000
    
    # Batch size for updates
    update_batch_size: 500
    
    # Batch size for deletes
    delete_batch_size: 200
    
    # Batch timeout (seconds)
    timeout: 300
    
    # Parallel batch processing
    parallel_batches: 4
  
  # Indexing optimization
  indexing:
    # Index creation strategy
    strategy: "background"  # immediate, background, deferred
    
    # Index parameters
    parameters:
      # HNSW parameters
      hnsw:
        m: 16  # Number of bi-directional links
        ef_construct: 200  # Size of dynamic candidate list
        
      # Quantization
      quantization:
        enabled: false
        type: "scalar"  # scalar, product
        
        scalar:
          type: "int8"  # int8, int4
          quantile: 0.99
    
    # Index maintenance
    maintenance:
      # Automatic optimization
      auto_optimize: true
      
      # Optimization interval (seconds)
      optimize_interval: 3600
      
      # Vacuum threshold
      vacuum_threshold: 0.1  # 10% deleted vectors
  
  # Search optimization
  search:
    # Default search parameters
    default_params:
      # Exact search threshold
      exact: false
      
      # HNSW search parameters
      hnsw_ef: 128  # Size of dynamic candidate list during search
      
      # Search timeout
      timeout: 10  # seconds
    
    # Result caching
    result_caching:
      enabled: true
      ttl: 300  # 5 minutes
      max_size: 1000  # Number of cached queries
    
    # Search result optimization
    result_optimization:
      # Enable result deduplication
      deduplicate: true
      
      # Similarity threshold for deduplication
      dedup_threshold: 0.95
      
      # Result ranking optimization
      ranking_optimization: true
```

## ⚡ Search Performance

### Search Optimization

```yaml
search:
  # Search strategy
  strategy: "hybrid"  # vector, keyword, hybrid
  
  # Hybrid search configuration
  hybrid:
    # Vector search weight
    vector_weight: 0.7
    
    # Keyword search weight
    keyword_weight: 0.3
    
    # Fusion method
    fusion_method: "rrf"  # rrf, weighted_sum, max
    
    # RRF parameter
    rrf_k: 60
  
  # Vector search optimization
  vector:
    # Similarity threshold
    similarity_threshold: 0.7
    
    # Search precision
    precision: "balanced"  # speed, balanced, accuracy
    
    # Pre-filtering
    pre_filtering:
      enabled: true
      max_candidates: 10000
    
    # Post-filtering
    post_filtering:
      enabled: true
      rerank: true
  
  # Keyword search optimization
  keyword:
    # Search engine
    engine: "bm25"  # bm25, tfidf, boolean
    
    # BM25 parameters
    bm25:
      k1: 1.2
      b: 0.75
    
    # Stemming
    stemming:
      enabled: true
      language: "english"
    
    # Stop words
    stop_words:
      enabled: true
      custom_words: []
  
  # Result optimization
  results:
    # Maximum results per query
    max_results: 50
    
    # Result diversification
    diversification:
      enabled: true
      threshold: 0.8
      max_similar: 3
    
    # Result ranking
    ranking:
      # Custom ranking factors
      factors:
        relevance: 0.6
        recency: 0.2
        popularity: 0.1
        authority: 0.1
      
      # Learning to rank
      learning_to_rank:
        enabled: false
        model: "xgboost"
        features: ["relevance", "recency", "click_through"]
  
  # Search analytics
  analytics:
    enabled: true
    
    # Query logging
    query_logging:
      enabled: true
      log_level: "INFO"
      include_results: false
    
    # Performance metrics
    metrics:
      enabled: true
      track_latency: true
      track_throughput: true
      track_accuracy: true
    
    # A/B testing
    ab_testing:
      enabled: false
      experiments: []

# Environment variables for search optimization
# QDRANT_LOADER_SEARCH_STRATEGY=hybrid
# QDRANT_LOADER_SIMILARITY_THRESHOLD=0.7
# QDRANT_LOADER_MAX_RESULTS=50
```

### MCP Server Performance

```yaml
mcp_server:
  # Server performance
  performance:
    # Request handling
    request_handling:
      # Maximum concurrent requests
      max_concurrent: 100
      
      # Request timeout
      timeout: 30
      
      # Request queue size
      queue_size: 1000
      
      # Worker threads
      worker_threads: 8
    
    # Response optimization
    response:
      # Enable response compression
      compression: true
      
      # Response caching
      caching:
        enabled: true
        ttl: 300
        max_size: 1000
      
      # Streaming responses
      streaming:
        enabled: true
        chunk_size: 8192
    
    # Connection management
    connections:
      # Keep-alive timeout
      keep_alive_timeout: 60
      
      # Maximum connections per client
      max_per_client: 10
      
      # Connection pooling
      pooling: true
  
  # Search performance
  search_performance:
    # Search caching
    caching:
      enabled: true
      
      # Cache levels
      levels:
        query_cache:
          enabled: true
          ttl: 300
          max_size: 1000
        
        result_cache:
          enabled: true
          ttl: 600
          max_size: 500
    
    # Search optimization
    optimization:
      # Parallel search across collections
      parallel_search: true
      
      # Search result prefetching
      prefetching: true
      
      # Query optimization
      query_optimization: true
    
    # Performance monitoring
    monitoring:
      enabled: true
      
      # Metrics collection
      metrics:
        - "search_latency"
        - "search_throughput"
        - "cache_hit_rate"
        - "error_rate"
      
      # Performance alerts
      alerts:
        latency_threshold: 1000  # milliseconds
        error_rate_threshold: 0.05  # 5%
```

## 🔧 Resource Management

### CPU Optimization

```yaml
cpu:
  # CPU usage limits
  limits:
    # Maximum CPU usage (percentage)
    max_usage: 80
    
    # CPU affinity (specific cores)
    affinity: []  # Empty means use all cores
    
    # Process priority
    priority: "normal"  # low, normal, high
  
  # CPU optimization
  optimization:
    # Enable CPU-specific optimizations
    native_optimizations: true
    
    # SIMD instructions
    simd: true
    
    # Multi-threading
    threading:
      enabled: true
      
      # Thread pool size
      pool_size: 8
      
      # Thread affinity
      affinity: true
  
  # CPU monitoring
  monitoring:
    enabled: true
    
    # Monitoring interval
    interval: 60  # seconds
    
    # CPU usage alerts
    alerts:
      high_usage_threshold: 90  # percentage
      sustained_duration: 300  # seconds

# Environment variables for CPU optimization
# QDRANT_LOADER_MAX_CPU=80
# QDRANT_LOADER_CPU_THREADS=8
```

### Disk I/O Optimization

```yaml
disk:
  # I/O optimization
  io:
    # I/O scheduler
    scheduler: "mq-deadline"  # noop, deadline, cfq, mq-deadline
    
    # Read-ahead size
    read_ahead: "128KB"
    
    # Write buffer size
    write_buffer: "64KB"
    
    # Sync strategy
    sync_strategy: "periodic"  # immediate, periodic, lazy
    
    # Periodic sync interval
    sync_interval: 30  # seconds
  
  # Disk space management
  space:
    # Minimum free space
    min_free_space: "1GB"
    
    # Space monitoring
    monitoring:
      enabled: true
      check_interval: 300  # seconds
      
      # Space alerts
      alerts:
        low_space_threshold: "5GB"
        critical_threshold: "1GB"
    
    # Automatic cleanup
    cleanup:
      enabled: true
      
      # Cleanup strategies
      strategies:
        - "old_cache_files"
        - "temporary_files"
        - "log_rotation"
      
      # Cleanup schedule
      schedule: "daily"  # hourly, daily, weekly
  
  # Temporary files
  temp_files:
    # Temporary directory
    directory: "/tmp/qdrant-loader"
    
    # Automatic cleanup
    auto_cleanup: true
    
    # Cleanup age
    cleanup_age: 3600  # seconds (1 hour)
    
    # Maximum temp space
    max_space: "2GB"

# Environment variables for disk optimization
# QDRANT_LOADER_TEMP_DIR=/tmp/qdrant-loader
# QDRANT_LOADER_MIN_FREE_SPACE=1GB
```

## 📊 Performance Monitoring

### Metrics Collection

```yaml
monitoring:
  # Performance metrics
  metrics:
    enabled: true
    
    # Metrics collection interval
    interval: 60  # seconds
    
    # Metrics retention
    retention: 86400  # 24 hours
    
    # Metrics categories
    categories:
      system:
        - "cpu_usage"
        - "memory_usage"
        - "disk_usage"
        - "network_io"
      
      application:
        - "processing_speed"
        - "search_latency"
        - "cache_hit_rate"
        - "error_rate"
      
      business:
        - "documents_processed"
        - "searches_performed"
        - "user_activity"
  
  # Performance alerts
  alerts:
    enabled: true
    
    # Alert thresholds
    thresholds:
      cpu_usage: 90  # percentage
      memory_usage: 85  # percentage
      disk_usage: 90  # percentage
      search_latency: 1000  # milliseconds
      error_rate: 0.05  # 5%
    
    # Alert channels
    channels:
      email:
        enabled: false
        recipients: ["admin@company.com"]
      
      slack:
        enabled: false
        webhook_url: "https://hooks.slack.com/..."
      
      webhook:
        enabled: false
        url: "https://monitoring.company.com/alerts"
  
  # Performance profiling
  profiling:
    enabled: false
    
    # Profiling modes
    modes:
      - "cpu"
      - "memory"
      - "io"
    
    # Profiling output
    output_dir: "~/.qdrant-loader/profiles"
    
    # Profiling schedule
    schedule:
      enabled: false
      interval: 3600  # seconds
      duration: 300  # seconds
```

### Performance Tuning Presets

```yaml
# Performance presets for different scenarios
performance_presets:
  # Speed-optimized preset
  speed:
    processing:
      parallel:
        workers: 16
        max_concurrent_files: 50
        batch_size: 200
      
      chunking:
        strategy: "fixed"
        chunk_size: 800
        chunk_overlap: 100
    
    memory:
      limits:
        max_total_memory: "16GB"
      
      caching:
        levels:
          memory:
            max_size: "4GB"
    
    search:
      strategy: "vector"
      vector:
        precision: "speed"
        similarity_threshold: 0.6
  
  # Memory-optimized preset
  memory:
    processing:
      parallel:
        workers: 4
        max_concurrent_files: 10
        batch_size: 50
      
      chunking:
        strategy: "streaming"
        chunk_size: 500
        chunk_overlap: 50
    
    memory:
      limits:
        max_total_memory: "4GB"
      
      optimization:
        streaming: true
        lazy_loading: true
    
    search:
      strategy: "hybrid"
      results:
        max_results: 20
  
  # Accuracy-optimized preset
  accuracy:
    processing:
      chunking:
        strategy: "semantic"
        chunk_size: 1500
        chunk_overlap: 400
    
    search:
      strategy: "hybrid"
      vector:
        precision: "accuracy"
        similarity_threshold: 0.8
      
      results:
        diversification:
          enabled: true
          threshold: 0.9

# Apply preset
# qdrant-loader config apply-preset speed
```

## 🔗 Related Documentation

- **[Environment Variables Reference](./environment-variables.md)** - Environment variable configuration
- **[Configuration File Reference](./config-file-reference.md)** - YAML configuration options
- **[Workspace Mode](./workspace-mode.md)** - Workspace configuration
- **[Performance Optimization](../troubleshooting/performance-optimization.md)** - Troubleshooting performance issues

## 📋 Performance Tuning Checklist

- [ ] **Hardware resources** assessed (CPU, memory, disk, network)
- [ ] **Workload characteristics** analyzed (file sizes, types, volume)
- [ ] **Performance baseline** established
- [ ] **Parallel processing** configured for your CPU count
- [ ] **Memory limits** set appropriately
- [ ] **Caching strategy** implemented
- [ ] **Network settings** optimized
- [ ] **Database parameters** tuned
- [ ] **Search configuration** optimized
- [ ] **Monitoring** enabled
- [ ] **Performance testing** completed
- [ ] **Alerts** configured for critical metrics

---

**Advanced configuration complete!** 🎉

Your QDrant Loader is now optimized for maximum performance in your environment. These advanced settings provide fine-grained control over every aspect of the system's behavior, ensuring optimal resource utilization and response times.
