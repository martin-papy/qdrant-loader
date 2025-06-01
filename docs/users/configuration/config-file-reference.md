# Configuration File Reference

This comprehensive reference covers all configuration options available in QDrant Loader's YAML configuration files. Configuration files provide a structured way to manage complex settings and are ideal for version control and team collaboration.

## 🎯 Overview

QDrant Loader supports YAML configuration files for managing settings in a structured, version-controllable format. Configuration files are particularly useful for complex setups, team environments, and when you need to document your configuration choices.

### Configuration Priority

```
1. Command-line arguments    (highest priority)
2. Environment variables
3. Configuration file        ← This guide
4. Default values           (lowest priority)
```

### Configuration File Locations

QDrant Loader looks for configuration files in the following order:

```
1. ./qdrant-loader.yaml      (current directory)
2. ./config.yaml             (current directory)
3. ~/.qdrant-loader.yaml     (home directory)
4. /etc/qdrant-loader.yaml   (system-wide)
```

## 📁 Basic Configuration File

### Minimal Configuration

```yaml
# qdrant-loader.yaml - Minimal configuration
qdrant:
  url: "http://localhost:6333"
  collection_name: "documents"

openai:
  api_key: "sk-your-openai-api-key-here"
```

### Complete Configuration Template

```yaml
# qdrant-loader.yaml - Complete configuration template
# Copy this template and customize for your needs

# QDrant Database Configuration
qdrant:
  url: "http://localhost:6333"
  api_key: null  # Optional: for QDrant Cloud or secured instances
  collection_name: "documents"
  timeout: 30
  batch_size: 100
  
# OpenAI Configuration
openai:
  api_key: "sk-your-openai-api-key-here"
  model: "text-embedding-3-small"
  batch_size: 100
  max_retries: 3
  timeout: 30

# Data Sources Configuration
data_sources:
  git:
    username: null
    token: null
    clone_depth: 1
    
  confluence:
    base_url: null
    username: null
    api_token: null
    spaces: []  # Empty list means all accessible spaces
    
  jira:
    base_url: null
    username: null
    api_token: null
    projects: []  # Empty list means all accessible projects

# Processing Configuration
processing:
  chunk_size: 1000
  chunk_overlap: 200
  max_file_size: "50MB"
  supported_formats:
    - "md"
    - "txt"
    - "pdf"
    - "docx"
    - "pptx"
    - "xlsx"
  exclude_patterns:
    - "*.log"
    - "node_modules/"
    - "__pycache__/"

# MCP Server Configuration
mcp_server:
  log_level: "INFO"
  max_results: 10
  timeout: 30
  similarity_threshold: 0.7
  cache:
    enabled: false
    ttl: 300

# Logging Configuration
logging:
  level: "INFO"
  file: null  # null means console only
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Security Configuration
security:
  tls_verify: true
  proxy: null

# Monitoring Configuration
monitoring:
  metrics_enabled: false
  metrics_port: 9090
```

## 🔧 Detailed Configuration Sections

### QDrant Database Configuration

```yaml
qdrant:
  # Required: URL of your QDrant database instance
  url: "http://localhost:6333"
  
  # Optional: API key for QDrant Cloud or secured instances
  api_key: "your-qdrant-cloud-api-key"
  
  # Optional: Name of the QDrant collection (default: "documents")
  collection_name: "my_project_docs"
  
  # Optional: Timeout for QDrant operations in seconds (default: 30)
  timeout: 60
  
  # Optional: Batch size for QDrant operations (default: 100)
  batch_size: 200
  
  # Optional: Vector dimension (auto-detected from embedding model)
  vector_size: 1536
  
  # Optional: Distance metric for similarity search
  distance: "Cosine"  # Options: Cosine, Euclidean, Dot
  
  # Optional: Collection configuration
  collection:
    # Replication factor for the collection
    replication_factor: 1
    
    # Write consistency factor
    write_consistency_factor: 1
    
    # Shard number
    shard_number: 1
    
    # On-disk payload storage
    on_disk_payload: false
```

### OpenAI Configuration

```yaml
openai:
  # Required: OpenAI API key
  api_key: "sk-your-openai-api-key-here"
  
  # Optional: Embedding model (default: "text-embedding-3-small")
  model: "text-embedding-3-large"
  
  # Optional: Batch size for API calls (default: 100)
  batch_size: 500
  
  # Optional: Maximum retries for failed API calls (default: 3)
  max_retries: 5
  
  # Optional: Timeout for API calls in seconds (default: 30)
  timeout: 60
  
  # Optional: Base URL for OpenAI API (for custom endpoints)
  base_url: "https://api.openai.com/v1"
  
  # Optional: Organization ID
  organization: "org-your-organization-id"
  
  # Optional: Rate limiting
  rate_limit:
    requests_per_minute: 3000
    tokens_per_minute: 1000000
```

### Data Sources Configuration

#### Git Repository Configuration

```yaml
data_sources:
  git:
    # Optional: Username for Git authentication
    username: "your-github-username"
    
    # Optional: Personal access token for Git authentication
    token: "ghp_your-github-token"
    
    # Optional: Clone depth (default: 1 for shallow clone)
    clone_depth: 1
    
    # Optional: Default branch to clone
    default_branch: "main"
    
    # Optional: SSH key path for Git authentication
    ssh_key_path: "~/.ssh/id_rsa"
    
    # Optional: Git configuration
    config:
      # Timeout for Git operations in seconds
      timeout: 300
      
      # Maximum repository size to clone
      max_repo_size: "1GB"
      
      # File patterns to include
      include_patterns:
        - "*.md"
        - "*.txt"
        - "*.rst"
        - "docs/**"
      
      # File patterns to exclude
      exclude_patterns:
        - ".git/"
        - "node_modules/"
        - "*.log"
        - "build/"
        - "dist/"
```

#### Confluence Configuration

```yaml
data_sources:
  confluence:
    # Required: Base URL of your Confluence instance
    base_url: "https://company.atlassian.net"
    
    # Required: Confluence username or email
    username: "user@company.com"
    
    # Required: Confluence API token
    api_token: "your-confluence-api-token"
    
    # Optional: Specific spaces to index (empty means all accessible)
    spaces:
      - "DOCS"
      - "TECH"
      - "SUPPORT"
    
    # Optional: Confluence-specific settings
    settings:
      # Include page attachments
      include_attachments: true
      
      # Include page comments
      include_comments: false
      
      # Include archived pages
      include_archived: false
      
      # Maximum pages to fetch per request
      page_size: 50
      
      # Content expansion options
      expand:
        - "body.storage"
        - "metadata"
        - "version"
        - "space"
      
      # CQL (Confluence Query Language) filter
      cql_filter: "type=page AND space in (DOCS, TECH)"
```

#### JIRA Configuration

```yaml
data_sources:
  jira:
    # Required: Base URL of your JIRA instance
    base_url: "https://company.atlassian.net"
    
    # Required: JIRA username or email
    username: "user@company.com"
    
    # Required: JIRA API token
    api_token: "your-jira-api-token"
    
    # Optional: Specific projects to index (empty means all accessible)
    projects:
      - "PROJ"
      - "DOCS"
      - "SUPPORT"
    
    # Optional: JIRA-specific settings
    settings:
      # Include issue comments
      include_comments: true
      
      # Include issue attachments
      include_attachments: true
      
      # Include issue history
      include_history: false
      
      # Issue types to include
      issue_types:
        - "Story"
        - "Bug"
        - "Task"
        - "Epic"
      
      # Issue statuses to include
      statuses:
        - "Open"
        - "In Progress"
        - "Done"
      
      # JQL (JIRA Query Language) filter
      jql_filter: "project in (PROJ, DOCS) AND status != Closed"
      
      # Maximum issues to fetch per request
      max_results: 50
      
      # Fields to expand
      expand:
        - "changelog"
        - "renderedFields"
        - "names"
        - "schema"
```

### Processing Configuration

```yaml
processing:
  # Text chunking settings
  chunking:
    # Maximum size of text chunks in tokens (default: 1000)
    chunk_size: 1500
    
    # Overlap between chunks in tokens (default: 200)
    chunk_overlap: 300
    
    # Chunking strategy
    strategy: "recursive"  # Options: recursive, semantic, fixed
    
    # Separators for recursive chunking
    separators:
      - "\n\n"
      - "\n"
      - " "
      - ""
  
  # File processing settings
  files:
    # Maximum file size to process
    max_file_size: "100MB"
    
    # Supported file formats
    supported_formats:
      - "md"
      - "txt"
      - "pdf"
      - "docx"
      - "pptx"
      - "xlsx"
      - "html"
      - "json"
      - "yaml"
      - "csv"
    
    # File patterns to exclude
    exclude_patterns:
      - "*.log"
      - "*.tmp"
      - "node_modules/"
      - "__pycache__/"
      - ".git/"
      - "build/"
      - "dist/"
    
    # File patterns to include (overrides exclude)
    include_patterns:
      - "docs/**"
      - "*.md"
      - "README*"
  
  # Content extraction settings
  extraction:
    # Extract text from images using OCR
    ocr_enabled: false
    
    # OCR language
    ocr_language: "eng"
    
    # Extract metadata from files
    extract_metadata: true
    
    # Clean extracted text
    clean_text: true
    
    # Remove empty lines
    remove_empty_lines: true
    
    # Normalize whitespace
    normalize_whitespace: true
  
  # Parallel processing settings
  parallel:
    # Number of worker processes (default: CPU count)
    workers: 4
    
    # Maximum files to process in parallel
    max_files: 10
    
    # Batch size for parallel processing
    batch_size: 50
```

### MCP Server Configuration

```yaml
mcp_server:
  # Logging level for MCP server
  log_level: "INFO"  # Options: DEBUG, INFO, WARNING, ERROR
  
  # Maximum number of search results to return
  max_results: 20
  
  # Timeout for MCP server operations in seconds
  timeout: 60
  
  # Minimum similarity score for search results
  similarity_threshold: 0.75
  
  # Search configuration
  search:
    # Enable fuzzy search
    fuzzy_search: true
    
    # Fuzzy search threshold
    fuzzy_threshold: 0.8
    
    # Enable semantic search
    semantic_search: true
    
    # Enable keyword search
    keyword_search: true
    
    # Search result ranking weights
    ranking:
      semantic_weight: 0.7
      keyword_weight: 0.2
      recency_weight: 0.1
  
  # Caching configuration
  cache:
    # Enable caching for search results
    enabled: true
    
    # Cache time-to-live in seconds
    ttl: 600
    
    # Maximum cache size (number of entries)
    max_size: 1000
    
    # Cache backend
    backend: "memory"  # Options: memory, redis
    
    # Redis configuration (if backend is redis)
    redis:
      host: "localhost"
      port: 6379
      db: 0
      password: null
  
  # Server configuration
  server:
    # Server host
    host: "localhost"
    
    # Server port
    port: 8080
    
    # Enable CORS
    cors_enabled: true
    
    # CORS origins
    cors_origins:
      - "http://localhost:3000"
      - "https://cursor.sh"
    
    # Request timeout
    request_timeout: 30
    
    # Maximum request size
    max_request_size: "10MB"
```

### Logging Configuration

```yaml
logging:
  # Log level
  level: "INFO"  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
  
  # Log file path (null means console only)
  file: "/var/log/qdrant-loader/app.log"
  
  # Log format
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  
  # Log rotation
  rotation:
    # Enable log rotation
    enabled: true
    
    # Maximum file size before rotation
    max_size: "100MB"
    
    # Number of backup files to keep
    backup_count: 5
    
    # Rotation interval
    interval: "daily"  # Options: daily, weekly, monthly
  
  # Structured logging
  structured:
    # Enable JSON logging
    enabled: false
    
    # Additional fields to include
    fields:
      service: "qdrant-loader"
      version: "1.0.0"
      environment: "production"
  
  # Logger-specific configuration
  loggers:
    qdrant_loader:
      level: "INFO"
      handlers: ["console", "file"]
    
    mcp_server:
      level: "DEBUG"
      handlers: ["console"]
    
    openai:
      level: "WARNING"
      handlers: ["file"]
```

### Security Configuration

```yaml
security:
  # TLS/SSL configuration
  tls:
    # Verify TLS certificates
    verify: true
    
    # CA certificate bundle path
    ca_bundle: null
    
    # Client certificate path
    cert_file: null
    
    # Client private key path
    key_file: null
  
  # Proxy configuration
  proxy:
    # HTTP proxy URL
    http: "http://proxy.company.com:8080"
    
    # HTTPS proxy URL
    https: "https://proxy.company.com:8080"
    
    # No proxy hosts
    no_proxy:
      - "localhost"
      - "127.0.0.1"
      - "*.local"
  
  # API key management
  api_keys:
    # Encryption key for storing API keys
    encryption_key: null
    
    # Key storage backend
    storage: "file"  # Options: file, keyring, vault
    
    # Storage configuration
    storage_config:
      file_path: "~/.qdrant-loader/keys.enc"
  
  # Access control
  access_control:
    # Enable access control
    enabled: false
    
    # Allowed IP addresses
    allowed_ips:
      - "127.0.0.1"
      - "192.168.1.0/24"
    
    # API key for MCP server access
    api_key: "your-mcp-server-api-key"
```

### Monitoring Configuration

```yaml
monitoring:
  # Enable performance metrics collection
  metrics_enabled: true
  
  # Metrics server port
  metrics_port: 9090
  
  # Metrics endpoint path
  metrics_path: "/metrics"
  
  # Health check configuration
  health_check:
    # Enable health check endpoint
    enabled: true
    
    # Health check port
    port: 8081
    
    # Health check path
    path: "/health"
    
    # Health check interval
    interval: 30
  
  # Performance monitoring
  performance:
    # Enable performance tracking
    enabled: true
    
    # Sample rate for performance tracking
    sample_rate: 0.1
    
    # Performance thresholds
    thresholds:
      response_time: 1000  # milliseconds
      memory_usage: 80     # percentage
      cpu_usage: 80        # percentage
  
  # External monitoring integrations
  integrations:
    # Prometheus configuration
    prometheus:
      enabled: true
      job_name: "qdrant-loader"
      scrape_interval: "15s"
    
    # Grafana configuration
    grafana:
      enabled: false
      dashboard_url: "http://grafana.company.com"
    
    # Custom webhook for alerts
    webhook:
      enabled: false
      url: "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
```

## 📋 Environment-Specific Configurations

### Development Configuration

```yaml
# qdrant-loader.dev.yaml - Development environment
qdrant:
  url: "http://localhost:6333"
  collection_name: "dev_documents"
  timeout: 30

openai:
  api_key: "sk-your-dev-openai-api-key"
  model: "text-embedding-3-small"
  batch_size: 50

processing:
  chunk_size: 500
  chunk_overlap: 100
  max_file_size: "10MB"
  parallel:
    workers: 2

mcp_server:
  log_level: "DEBUG"
  max_results: 5
  timeout: 10
  cache:
    enabled: false

logging:
  level: "DEBUG"
  file: null  # Console only for development

security:
  tls:
    verify: false  # For local development only

monitoring:
  metrics_enabled: false
```

### Production Configuration

```yaml
# qdrant-loader.prod.yaml - Production environment
qdrant:
  url: "https://your-qdrant-cluster.qdrant.io"
  api_key: "your-production-qdrant-api-key"
  collection_name: "production_documents"
  timeout: 60
  batch_size: 200

openai:
  api_key: "sk-your-prod-openai-api-key"
  model: "text-embedding-3-small"
  batch_size: 200
  max_retries: 5

data_sources:
  confluence:
    base_url: "https://company.atlassian.net"
    username: "service-account@company.com"
    api_token: "your-confluence-api-token"
    spaces: ["DOCS", "TECH", "SUPPORT"]
  
  jira:
    base_url: "https://company.atlassian.net"
    username: "service-account@company.com"
    api_token: "your-jira-api-token"
    projects: ["PROJ", "DOCS", "SUPPORT"]

processing:
  chunk_size: 1200
  chunk_overlap: 300
  max_file_size: "100MB"
  parallel:
    workers: 8

mcp_server:
  log_level: "INFO"
  max_results: 15
  timeout: 30
  similarity_threshold: 0.75
  cache:
    enabled: true
    ttl: 600

logging:
  level: "INFO"
  file: "/var/log/qdrant-loader/app.log"
  rotation:
    enabled: true
    max_size: "100MB"
    backup_count: 5

security:
  tls:
    verify: true
  proxy:
    http: "http://proxy.company.com:8080"
    https: "https://proxy.company.com:8080"

monitoring:
  metrics_enabled: true
  metrics_port: 9090
  health_check:
    enabled: true
    port: 8081
```

### Team Configuration

```yaml
# qdrant-loader.team.yaml - Team/shared environment
qdrant:
  url: "http://qdrant.team.local:6333"
  collection_name: "team_knowledge"
  timeout: 45

openai:
  api_key: "sk-your-team-openai-api-key"
  model: "text-embedding-3-small"
  batch_size: 100

data_sources:
  confluence:
    base_url: "https://team.atlassian.net"
    # Use environment variables for personal credentials
    username: "${CONFLUENCE_USERNAME}"
    api_token: "${CONFLUENCE_API_TOKEN}"
    spaces: ["TEAM", "DOCS", "TECH"]
  
  git:
    username: "${GIT_USERNAME}"
    token: "${GIT_TOKEN}"

processing:
  chunk_size: 1000
  chunk_overlap: 200
  max_file_size: "50MB"
  parallel:
    workers: 4

mcp_server:
  log_level: "INFO"
  max_results: 10
  timeout: 30
  cache:
    enabled: true
    ttl: 300

logging:
  level: "INFO"
  file: "~/.qdrant-loader/logs/team.log"

monitoring:
  metrics_enabled: true
  metrics_port: 9090
```

## 🔧 Configuration Management

### Loading Configuration Files

#### Specify Configuration File

```bash
# Use specific configuration file
qdrant-loader --config /path/to/config.yaml status

# Use environment-specific configuration
qdrant-loader --config qdrant-loader.prod.yaml load

# Use configuration from URL
qdrant-loader --config https://config.company.com/qdrant-loader.yaml status
```

#### Configuration File Discovery

```bash
# QDrant Loader automatically looks for configuration files in:
# 1. ./qdrant-loader.yaml (current directory)
# 2. ./config.yaml (current directory)
# 3. ~/.qdrant-loader.yaml (home directory)
# 4. /etc/qdrant-loader.yaml (system-wide)

# Check which configuration file is being used
qdrant-loader config show --source
```

### Configuration Validation

#### Validate Configuration

```bash
# Validate configuration file syntax
qdrant-loader config validate

# Validate specific configuration file
qdrant-loader config validate --config qdrant-loader.prod.yaml

# Test configuration connectivity
qdrant-loader config test

# Show effective configuration (after merging all sources)
qdrant-loader config show
```

#### Configuration Schema

```yaml
# JSON Schema for configuration validation
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "qdrant": {
      "type": "object",
      "properties": {
        "url": {"type": "string", "format": "uri"},
        "api_key": {"type": ["string", "null"]},
        "collection_name": {"type": "string"},
        "timeout": {"type": "integer", "minimum": 1}
      },
      "required": ["url", "collection_name"]
    },
    "openai": {
      "type": "object",
      "properties": {
        "api_key": {"type": "string"},
        "model": {"type": "string"},
        "batch_size": {"type": "integer", "minimum": 1, "maximum": 2048}
      },
      "required": ["api_key"]
    }
  },
  "required": ["qdrant", "openai"]
}
```

### Configuration Templates

#### Generate Configuration Template

```bash
# Generate basic configuration template
qdrant-loader config init

# Generate configuration for specific environment
qdrant-loader config init --env production

# Generate configuration with all options
qdrant-loader config init --full

# Generate configuration from existing setup
qdrant-loader config export > current-config.yaml
```

#### Configuration Inheritance

```yaml
# base.yaml - Base configuration
qdrant:
  collection_name: "documents"
  timeout: 30

openai:
  model: "text-embedding-3-small"
  batch_size: 100

processing:
  chunk_size: 1000
  chunk_overlap: 200

---
# production.yaml - Production overrides
extends: "base.yaml"

qdrant:
  url: "https://prod-qdrant.company.com"
  api_key: "prod-api-key"
  collection_name: "production_documents"

openai:
  api_key: "sk-prod-openai-key"
  batch_size: 200

logging:
  level: "INFO"
  file: "/var/log/qdrant-loader/app.log"
```

## 🔗 Related Documentation

- **[Environment Variables Reference](./environment-variables.md)** - Environment variable configuration
- **[Basic Configuration](../getting-started/basic-configuration.md)** - Getting started with configuration
- **[Security Considerations](./security-considerations.md)** - Security best practices
- **[Advanced Settings](./advanced-settings.md)** - Performance tuning options

## 📋 Configuration File Checklist

- [ ] **Configuration file** created in appropriate location
- [ ] **Required sections** configured (qdrant, openai)
- [ ] **Data source credentials** configured for your sources
- [ ] **Processing settings** tuned for your use case
- [ ] **MCP server settings** configured for AI tools
- [ ] **Logging configuration** appropriate for your environment
- [ ] **Security settings** properly configured
- [ ] **Configuration validated** with test commands
- [ ] **File permissions** set appropriately (chmod 600 for sensitive configs)
- [ ] **Version control** configured (exclude sensitive files)

---

**Configuration file setup complete!** 🎉

Your QDrant Loader is now configured using structured YAML files. This provides a maintainable, version-controllable way to manage complex configurations while supporting different environments and team collaboration.
