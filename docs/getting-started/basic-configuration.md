# Basic Configuration

This guide walks you through configuring QDrant Loader for your specific needs. After completing this guide, you'll have a customized setup ready for your data sources and use cases.

## 🎯 Overview

QDrant Loader uses a flexible configuration system that supports:

- **Environment variables** for credentials and basic settings
- **Configuration files** for detailed customization
- **Command-line arguments** for one-time overrides
- **Multiple environments** (development, staging, production)

## 🔧 Configuration Methods

### Configuration Priority

QDrant Loader uses this priority order (highest to lowest):

```
1. Command-line arguments    (--collection my-docs)
2. Environment variables     (QDRANT_COLLECTION_NAME=my-docs)
3. Configuration file        (config.yaml: collection_name: my-docs)
4. Default values           (collection_name: documents)
```

### Quick Setup vs. Advanced Setup

| Quick Setup | Advanced Setup |
|-------------|----------------|
| Environment variables only | Configuration file + environment variables |
| Good for: Simple use cases | Good for: Complex workflows, multiple environments |
| 5 minutes to configure | 15-30 minutes to configure |

## 🚀 Quick Setup (Environment Variables)

### Essential Environment Variables

Create a `.env` file in your working directory:

```bash
# Required - QDrant Database
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=my_documents

# Required - OpenAI API
OPENAI_API_KEY=your-openai-api-key

# Optional - QDrant Cloud (if using cloud)
QDRANT_API_KEY=your-qdrant-cloud-api-key

# Optional - Customization
QDRANT_LOADER_LOG_LEVEL=INFO
QDRANT_LOADER_BATCH_SIZE=50
```

### Load Environment Variables

```bash
# Option 1: Source the .env file
source .env

# Option 2: Use with commands
export $(cat .env | xargs) && qdrant-loader status

# Option 3: Use dotenv (if installed)
python -m dotenv run qdrant-loader status
```

### Test Quick Setup

```bash
# Verify configuration
qdrant-loader config show

# Test connections
qdrant-loader status

# Expected output:
# ✅ QDrant: Connected (http://localhost:6333)
# ✅ OpenAI: API key configured
# ✅ Collection: my_documents (ready)
```

## ⚙️ Advanced Setup (Configuration File)

### Initialize Configuration

```bash
# Create default configuration file
qdrant-loader config init

# This creates ~/.qdrant-loader/config.yaml
# Or specify custom location:
qdrant-loader config init --config-path ./my-config.yaml
```

### Configuration File Structure

```yaml
# ~/.qdrant-loader/config.yaml

# QDrant Database Configuration
qdrant:
  url: "${QDRANT_URL}"
  api_key: "${QDRANT_API_KEY}"  # Optional, for QDrant Cloud
  collection_name: "${QDRANT_COLLECTION_NAME}"
  timeout: 30
  
  # Advanced QDrant settings
  vector_config:
    size: 1536
    distance: "Cosine"
  
  # Performance tuning
  hnsw_config:
    m: 16
    ef_construct: 200
  
  # Storage optimization
  optimizers_config:
    deleted_threshold: 0.2
    vacuum_min_vector_number: 1000

# OpenAI Configuration
openai:
  api_key: "${OPENAI_API_KEY}"
  model: "text-embedding-3-small"
  batch_size: 100
  max_retries: 3
  timeout: 30
  
  # Rate limiting
  requests_per_minute: 1000
  tokens_per_minute: 150000

# Processing Configuration
processing:
  # Text chunking
  chunk_size: 1000
  chunk_overlap: 200
  min_chunk_size: 100
  
  # File processing
  max_file_size: "50MB"
  supported_formats:
    - "md"
    - "txt"
    - "pdf"
    - "docx"
    - "pptx"
    - "xlsx"
    - "html"
    - "rst"
    - "json"
    - "yaml"
  
  # Content filtering
  exclude_patterns:
    - "*.log"
    - "node_modules/"
    - ".git/"
    - "__pycache__/"
  
  # Language detection
  detect_language: true
  supported_languages:
    - "en"
    - "es"
    - "fr"
    - "de"

# Data Source Configuration
sources:
  # Git repositories
  git:
    enabled: true
    clone_depth: 1
    include_patterns:
      - "*.md"
      - "*.rst"
      - "*.txt"
      - "docs/**"
      - "README*"
    exclude_patterns:
      - "node_modules/"
      - ".git/"
      - "*.log"
    
    # Authentication (if needed)
    auth:
      username: "${GIT_USERNAME}"
      token: "${GIT_TOKEN}"
  
  # Confluence
  confluence:
    enabled: false
    base_url: "${CONFLUENCE_BASE_URL}"
    username: "${CONFLUENCE_USERNAME}"
    api_token: "${CONFLUENCE_API_TOKEN}"
    
    # Spaces to index
    spaces:
      - "DOCS"
      - "TECH"
      - "SUPPORT"
    
    # Content filtering
    include_labels:
      - "public"
      - "documentation"
    exclude_labels:
      - "draft"
      - "private"
  
  # JIRA
  jira:
    enabled: false
    base_url: "${JIRA_BASE_URL}"
    username: "${JIRA_USERNAME}"
    api_token: "${JIRA_API_TOKEN}"
    
    # Projects to index
    projects:
      - "PROJ"
      - "DOCS"
    
    # Issue types to include
    issue_types:
      - "Story"
      - "Task"
      - "Bug"
    
    # Fields to index
    fields:
      - "summary"
      - "description"
      - "comments"
  
  # Local files
  local:
    enabled: true
    watch_for_changes: true
    follow_symlinks: false
  
  # Public documentation
  public_docs:
    enabled: false
    sites:
      - url: "https://docs.example.com"
        depth: 3
        include_patterns:
          - "/docs/"
          - "/api/"
        exclude_patterns:
          - "/admin/"

# MCP Server Configuration
mcp_server:
  # Server settings
  host: "localhost"
  port: 8000
  log_level: "INFO"
  
  # Search configuration
  search:
    default_limit: 10
    max_limit: 100
    similarity_threshold: 0.7
    
    # Result formatting
    include_metadata: true
    include_content: true
    max_content_length: 500
  
  # Tool configuration
  tools:
    search:
      enabled: true
      description: "Semantic search across all documents"
    
    hierarchy_search:
      enabled: true
      description: "Search with document hierarchy context"
      max_depth: 5
    
    attachment_search:
      enabled: true
      description: "Search file attachments"
      supported_types:
        - "pdf"
        - "docx"
        - "xlsx"
        - "pptx"

# Logging Configuration
logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  
  # File logging
  file:
    enabled: true
    path: "~/.qdrant-loader/logs/qdrant-loader.log"
    max_size: "10MB"
    backup_count: 5
  
  # Console logging
  console:
    enabled: true
    colored: true

# Monitoring and Metrics
monitoring:
  enabled: false
  
  # Metrics collection
  metrics:
    enabled: false
    port: 9090
    path: "/metrics"
  
  # Health checks
  health_check:
    enabled: true
    interval: 60  # seconds
    
  # Performance tracking
  performance:
    track_ingestion_speed: true
    track_search_latency: true
    track_memory_usage: true
```

### Validate Configuration

```bash
# Check configuration syntax
qdrant-loader config validate

# Show current configuration
qdrant-loader config show

# Test all connections
qdrant-loader config test
```

## 🎯 Common Configuration Scenarios

### Scenario 1: Personal Knowledge Base

**Use Case**: Index personal documents, notes, and bookmarks

```yaml
# Personal setup
qdrant:
  collection_name: "personal_knowledge"

processing:
  chunk_size: 800
  supported_formats:
    - "md"
    - "txt"
    - "pdf"
    - "html"

sources:
  local:
    enabled: true
  git:
    enabled: true
    include_patterns:
      - "*.md"
      - "README*"
      - "docs/**"
  confluence:
    enabled: false
  jira:
    enabled: false
```

### Scenario 2: Team Documentation Hub

**Use Case**: Centralize team documentation from multiple sources

```yaml
# Team setup
qdrant:
  collection_name: "team_docs"

sources:
  git:
    enabled: true
    include_patterns:
      - "*.md"
      - "*.rst"
      - "docs/**"
      - "wiki/**"
  
  confluence:
    enabled: true
    spaces:
      - "TEAM"
      - "DOCS"
      - "ONBOARDING"
  
  jira:
    enabled: true
    projects:
      - "TEAM"
    issue_types:
      - "Story"
      - "Task"
  
  local:
    enabled: true

mcp_server:
  search:
    default_limit: 15
    similarity_threshold: 0.75
```

### Scenario 3: Enterprise Knowledge Management

**Use Case**: Large-scale documentation with multiple teams

```yaml
# Enterprise setup
qdrant:
  collection_name: "enterprise_knowledge"
  
  # Performance optimization for large datasets
  hnsw_config:
    m: 32
    ef_construct: 400
  
  optimizers_config:
    deleted_threshold: 0.1
    vacuum_min_vector_number: 10000

processing:
  chunk_size: 1200
  chunk_overlap: 300
  max_file_size: "100MB"
  
  # Support more formats
  supported_formats:
    - "md"
    - "txt"
    - "pdf"
    - "docx"
    - "pptx"
    - "xlsx"
    - "html"
    - "rst"
    - "json"
    - "yaml"

sources:
  git:
    enabled: true
    include_patterns:
      - "*.md"
      - "*.rst"
      - "docs/**"
      - "wiki/**"
      - "specifications/**"
  
  confluence:
    enabled: true
    spaces:
      - "ENGINEERING"
      - "PRODUCT"
      - "SUPPORT"
      - "LEGAL"
      - "HR"
  
  jira:
    enabled: true
    projects:
      - "ENG"
      - "PROD"
      - "SUPP"
    fields:
      - "summary"
      - "description"
      - "comments"
      - "acceptance_criteria"

monitoring:
  enabled: true
  metrics:
    enabled: true
  performance:
    track_ingestion_speed: true
    track_search_latency: true
    track_memory_usage: true
```

### Scenario 4: Development Team Setup

**Use Case**: Code documentation and development resources

```yaml
# Development team setup
qdrant:
  collection_name: "dev_docs"

processing:
  supported_formats:
    - "md"
    - "rst"
    - "txt"
    - "py"    # Python files
    - "js"    # JavaScript files
    - "ts"    # TypeScript files
    - "yaml"
    - "json"

sources:
  git:
    enabled: true
    include_patterns:
      - "*.md"
      - "*.rst"
      - "*.py"
      - "*.js"
      - "*.ts"
      - "docs/**"
      - "README*"
      - "CHANGELOG*"
      - "API.md"
    exclude_patterns:
      - "node_modules/"
      - "__pycache__/"
      - "*.pyc"
      - ".git/"
      - "build/"
      - "dist/"
  
  confluence:
    enabled: true
    spaces:
      - "DEV"
      - "API"
      - "ARCH"
  
  local:
    enabled: true

mcp_server:
  tools:
    search:
      enabled: true
    hierarchy_search:
      enabled: true
      max_depth: 10  # Deeper for code hierarchies
```

## 🔐 Security Configuration

### Environment Variables for Credentials

```bash
# .env file - never commit to version control
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your-qdrant-cloud-api-key
OPENAI_API_KEY=sk-your-openai-api-key

# Git authentication
GIT_USERNAME=your-username
GIT_TOKEN=your-personal-access-token

# Confluence authentication
CONFLUENCE_BASE_URL=https://company.atlassian.net
CONFLUENCE_USERNAME=your-email@company.com
CONFLUENCE_API_TOKEN=your-confluence-api-token

# JIRA authentication
JIRA_BASE_URL=https://company.atlassian.net
JIRA_USERNAME=your-email@company.com
JIRA_API_TOKEN=your-jira-api-token
```

### Secure Configuration Practices

```yaml
# config.yaml - safe to commit (no secrets)
qdrant:
  url: "${QDRANT_URL}"
  api_key: "${QDRANT_API_KEY}"  # Reference environment variable

openai:
  api_key: "${OPENAI_API_KEY}"  # Reference environment variable

sources:
  confluence:
    base_url: "${CONFLUENCE_BASE_URL}"
    username: "${CONFLUENCE_USERNAME}"
    api_token: "${CONFLUENCE_API_TOKEN}"
```

### File Permissions

```bash
# Secure configuration files
chmod 600 ~/.qdrant-loader/config.yaml
chmod 600 .env

# Secure log directory
chmod 700 ~/.qdrant-loader/logs/
```

## 🌍 Multi-Environment Setup

### Development Environment

```yaml
# config-dev.yaml
qdrant:
  url: "http://localhost:6333"
  collection_name: "dev_docs"

processing:
  chunk_size: 500  # Smaller for faster testing

sources:
  local:
    enabled: true
  git:
    enabled: true
  confluence:
    enabled: false  # Disable in dev
  jira:
    enabled: false  # Disable in dev

logging:
  level: "DEBUG"
  console:
    enabled: true
    colored: true
```

### Production Environment

```yaml
# config-prod.yaml
qdrant:
  url: "${QDRANT_PROD_URL}"
  api_key: "${QDRANT_PROD_API_KEY}"
  collection_name: "production_docs"
  
  # Production optimization
  hnsw_config:
    m: 32
    ef_construct: 400

processing:
  chunk_size: 1200
  max_file_size: "100MB"

sources:
  git:
    enabled: true
  confluence:
    enabled: true
  jira:
    enabled: true
  local:
    enabled: false  # Disable in production

logging:
  level: "INFO"
  file:
    enabled: true
    path: "/var/log/qdrant-loader/app.log"

monitoring:
  enabled: true
  metrics:
    enabled: true
```

### Using Different Configurations

```bash
# Use specific configuration file
qdrant-loader --config config-dev.yaml status
qdrant-loader --config config-prod.yaml ingest --source git

# Set via environment variable
export QDRANT_LOADER_CONFIG=config-prod.yaml
qdrant-loader status
```

## 🔧 Performance Tuning

### For Large Datasets

```yaml
# Optimize for large datasets
qdrant:
  hnsw_config:
    m: 32              # Higher for better recall
    ef_construct: 400  # Higher for better quality
  
  optimizers_config:
    deleted_threshold: 0.1
    vacuum_min_vector_number: 10000

processing:
  chunk_size: 1500     # Larger chunks for better context
  chunk_overlap: 400   # More overlap for continuity
  max_file_size: "200MB"

openai:
  batch_size: 200      # Larger batches for efficiency
  requests_per_minute: 2000
```

### For Fast Ingestion

```yaml
# Optimize for speed
processing:
  chunk_size: 800      # Smaller chunks process faster
  chunk_overlap: 100   # Less overlap for speed

openai:
  batch_size: 500      # Maximum batch size
  max_retries: 1       # Fewer retries for speed
  timeout: 10          # Shorter timeout

sources:
  git:
    clone_depth: 1     # Shallow clones
```

### For Memory Efficiency

```yaml
# Optimize for low memory
processing:
  chunk_size: 500      # Smaller chunks use less memory
  max_file_size: "10MB"

openai:
  batch_size: 50       # Smaller batches

qdrant:
  # Use disk-based storage
  storage_type: "disk"
```

## ✅ Configuration Validation

### Test Your Configuration

```bash
# Validate configuration syntax
qdrant-loader config validate

# Test all connections
qdrant-loader config test

# Show resolved configuration
qdrant-loader config show --resolved

# Test specific data source
qdrant-loader config test --source confluence
```

### Common Configuration Issues

#### 1. Invalid YAML Syntax

**Error**: `yaml.scanner.ScannerError`

**Solution**:

```bash
# Check YAML syntax
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Use proper indentation (2 spaces)
# Use quotes for strings with special characters
```

#### 2. Missing Environment Variables

**Error**: `KeyError: 'OPENAI_API_KEY'`

**Solution**:

```bash
# Check environment variables
env | grep QDRANT
env | grep OPENAI

# Set missing variables
export OPENAI_API_KEY="your-key-here"
```

#### 3. Connection Failures

**Error**: `ConnectionError: Unable to connect to QDrant`

**Solution**:

```bash
# Test QDrant connection
curl http://localhost:6333/health

# Check configuration
qdrant-loader config show | grep qdrant
```

## 📋 Configuration Checklist

- [ ] **Environment variables** set for all credentials
- [ ] **Configuration file** created and validated
- [ ] **QDrant connection** tested successfully
- [ ] **OpenAI API** key configured and tested
- [ ] **Data sources** configured for your use case
- [ ] **File permissions** secured (600 for config files)
- [ ] **Logging** configured appropriately
- [ ] **Performance settings** tuned for your dataset size
- [ ] **MCP server** configured if using AI tools
- [ ] **Backup strategy** for configuration files

## 🔗 Next Steps

With your configuration complete:

1. **[User Guides](../users/)** - Explore specific features and workflows
2. **[Data Source Guides](../users/detailed-guides/data-sources/)** - Configure specific connectors
3. **[MCP Server Setup](../users/detailed-guides/mcp-server/)** - Set up AI tool integration
4. **[CLI Reference](../users/cli-reference/)** - Learn all available commands

---

**Configuration Complete!** 🎉

Your QDrant Loader is now configured for your specific needs. You can start ingesting documents and using the search capabilities with your AI tools.
