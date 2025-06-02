# Configuration Reference

This section provides comprehensive documentation for configuring QDrant Loader. Learn how to set up data sources, optimize performance, configure security, and customize behavior for your specific needs.

## 🎯 Configuration Overview

QDrant Loader uses a combination of configuration files and environment variables:

- **`config.yaml`** - Main configuration file for data sources and processing options
- **`.env`** - Environment variables for credentials and system settings
- **Command-line options** - Runtime parameters and overrides

## 📁 Configuration Structure

```text
your-workspace/
├── config.yaml          # Main configuration file
├── .env                 # Environment variables
├── state.db            # Processing state (auto-generated)
└── logs/               # Log files (optional)
```

## 🚀 Quick Configuration

### 1. Download Templates

```bash
# Download configuration templates
curl -o config.yaml https://raw.githubusercontent.com/martin-papy/qdrant-loader/main/packages/qdrant-loader/conf/config.template.yaml
curl -o .env https://raw.githubusercontent.com/martin-papy/qdrant-loader/main/packages/qdrant-loader/conf/.env.template
```

### 2. Basic Environment Setup

Edit `.env` file:

```bash
# QDrant Configuration
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=my_docs
QDRANT_API_KEY=your_api_key  # Required for QDrant Cloud

# Embedding Configuration
OPENAI_API_KEY=your_openai_key

# State Management
STATE_DB_PATH=./state.db
```

### 3. Basic Data Sources

Edit `config.yaml`:

```yaml
sources:
  git:
    - url: "https://github.com/your-org/your-repo.git"
      branch: "main"
      include_patterns:
        - "**/*.md"
        - "**/*.py"

  local_files:
    - path: "./docs"
      include_patterns:
        - "**/*.md"
        - "**/*.pdf"

# Global settings
enable_file_conversion: true
chunk_size: 1000
chunk_overlap: 200
```

## 📚 Configuration Sections

### 🔧 [Environment Variables](./environment-variables.md)

Complete reference for all environment variables including:

- **QDrant connection settings** - URL, API keys, collection configuration
- **Authentication credentials** - API tokens for data sources
- **Processing options** - Embedding models, file conversion settings
- **Performance tuning** - Memory limits, concurrency settings

### 🔒 [Security Considerations](./security-considerations.md)

Security best practices and configuration:

- **API key management** - Secure storage and rotation
- **Access control** - Permissions and authentication
- **Data privacy** - Handling sensitive information
- **Network security** - TLS, firewalls, and secure connections

## 🎯 Configuration by Use Case

### 👨‍💻 Software Development Team

**Goal**: Integrate code repositories, documentation, and project management

```yaml
# config.yaml
sources:
  git:
    - url: "https://github.com/company/main-app.git"
      branch: "main"
      include_patterns: ["src/**/*.py", "docs/**/*.md"]
  
  confluence:
    - space_key: "DEV"
      include_patterns: ["Architecture/*", "API/*"]
  
  jira:
    - project_key: "PROJ"
      include_issue_types: ["Story", "Epic", "Bug"]

# Performance for team use
chunk_size: 800
batch_size: 50
max_concurrent_requests: 10
enable_file_conversion: true
```

```bash
# .env
QDRANT_URL=http://qdrant-server:6333
QDRANT_COLLECTION_NAME=team_knowledge
OPENAI_API_KEY=sk-proj-your_key
REPO_TOKEN=ghp_your_github_token
CONFLUENCE_URL=https://company.atlassian.net
CONFLUENCE_TOKEN=your_confluence_token
CONFLUENCE_EMAIL=team@company.com
JIRA_URL=https://company.atlassian.net
JIRA_TOKEN=your_jira_token
JIRA_EMAIL=team@company.com
```

### 📚 Documentation Team

**Goal**: Centralize and search documentation across platforms

```yaml
# config.yaml
sources:
  confluence:
    - space_key: "DOCS"
      include_attachments: true
      include_patterns: ["*"]
  
  local_files:
    - path: "./legacy-docs"
      include_patterns: ["**/*.pdf", "**/*.docx", "**/*.md"]
  
  public_docs:
    - url: "https://api-docs.example.com"
      css_selector: ".content"
      max_pages: 100

# Optimized for document processing
enable_file_conversion: true
chunk_size: 1200
chunk_overlap: 300
max_file_size: 52428800  # 50MB for large documents
```

### 🔬 Research Team

**Goal**: Index and search research materials and data

```yaml
# config.yaml
sources:
  local_files:
    - path: "./research-papers"
      include_patterns: ["**/*.pdf", "**/*.txt", "**/*.csv"]
      max_file_size: 104857600  # 100MB for datasets
    
    - path: "./notebooks"
      include_patterns: ["**/*.ipynb", "**/*.py"]
  
  git:
    - url: "https://github.com/research-org/analysis-tools.git"
      include_patterns: ["**/*.py", "**/*.md", "**/*.ipynb"]

# Research-optimized settings
chunk_size: 1500
chunk_overlap: 400
enable_file_conversion: true
batch_size: 20  # Slower processing for large files
```

### 🏢 Enterprise Deployment

**Goal**: Scalable, secure deployment for large organization

```yaml
# config.yaml
sources:
  git:
    - url: "https://github.com/enterprise/platform.git"
      branch: "main"
      include_patterns: ["**/*.py", "**/*.js", "**/*.md"]
    - url: "https://github.com/enterprise/services.git"
      branch: "main"
      include_patterns: ["**/*.py", "**/*.md"]
  
  confluence:
    - space_key: "ARCH"
    - space_key: "DOCS"
    - space_key: "PROC"
  
  jira:
    - project_key: "PLAT"
    - project_key: "SERV"

# Enterprise performance settings
chunk_size: 1000
batch_size: 100
max_concurrent_requests: 20
enable_caching: true
cache_ttl_hours: 24

# Error handling
retry_attempts: 5
retry_delay: 2
timeout_seconds: 60
```

```bash
# .env
QDRANT_URL=https://qdrant-cluster.company.com
QDRANT_API_KEY=your_enterprise_api_key
QDRANT_COLLECTION_NAME=enterprise_knowledge
OPENAI_API_KEY=sk-proj-enterprise_key
LOG_LEVEL=INFO
LOG_FILE=/var/log/qdrant-loader/app.log
STATE_DB_PATH=/data/qdrant-loader/state.db
```

## 🔧 Configuration Validation

### Validate Configuration

```bash
# Display and validate configuration
qdrant-loader --workspace . config

# Validate project configurations
qdrant-loader project --workspace . validate

# Check project status
qdrant-loader project --workspace . status
```

### Common Validation Errors

#### Missing Required Settings

```bash
# Error: Missing QDRANT_URL
export QDRANT_URL=http://localhost:6333

# Error: Missing OPENAI_API_KEY
export OPENAI_API_KEY=sk-proj-your_key

# Error: Invalid collection name
export QDRANT_COLLECTION_NAME=valid_collection_name
```

#### Invalid Configuration Syntax

```yaml
# ❌ Invalid YAML syntax
sources:
  git:
    - url: "https://github.com/org/repo.git"
      branch: main  # Missing quotes
      include_patterns:
        - "**/*.md"
        - "**/*.py"

# ✅ Correct YAML syntax
sources:
  git:
    - url: "https://github.com/org/repo.git"
      branch: "main"  # Quoted string
      include_patterns:
        - "**/*.md"
        - "**/*.py"
```

## 🎯 Configuration Best Practices

### 1. Environment-Specific Configuration

Use different configurations for different environments:

```bash
# Development
cp config.dev.yaml config.yaml
cp .env.dev .env

# Production
cp config.prod.yaml config.yaml
cp .env.prod .env
```

### 2. Secure Credential Management

```bash
# Use environment variables for sensitive data
export OPENAI_API_KEY=$(cat /secure/openai-key.txt)
export CONFLUENCE_TOKEN=$(vault kv get -field=token secret/confluence)

# Never commit credentials to version control
echo ".env" >> .gitignore
echo "*.key" >> .gitignore
```

### 3. Performance Tuning

```yaml
# Start with conservative settings
chunk_size: 800
batch_size: 20
max_concurrent_requests: 5

# Monitor and adjust based on:
# - Available memory
# - Network bandwidth
# - API rate limits
# - Processing speed requirements
```

### 4. Monitoring and Logging

```bash
# Enable appropriate logging
export LOG_LEVEL=INFO
export LOG_FILE=/var/log/qdrant-loader/app.log

# Monitor project status
qdrant-loader project --workspace . status
```

## 🔍 Advanced Configuration Patterns

### Multi-Environment Setup

```yaml
# config.yaml with environment variables
sources:
  git:
    - url: "${GIT_REPO_URL}"
      branch: "${GIT_BRANCH:-main}"
      include_patterns: 
        - "**/*.md"
        - "**/*.py"

chunk_size: ${CHUNK_SIZE:-1000}
batch_size: ${BATCH_SIZE:-50}
```

### Conditional Configuration

```yaml
# Different settings based on environment
sources:
  git:
    - url: "https://github.com/org/repo.git"
      branch: "main"
      # Only process recent files in development
      max_age_days: ${MAX_AGE_DAYS:-30}
      # Smaller files in development
      max_file_size: ${MAX_FILE_SIZE:-1048576}
```

### Template-Based Configuration

```yaml
# Base configuration template
_defaults: &defaults
  chunk_size: 1000
  chunk_overlap: 200
  enable_file_conversion: true

# Apply defaults to sources
sources:
  git:
    - <<: *defaults
      url: "https://github.com/org/repo1.git"
    - <<: *defaults
      url: "https://github.com/org/repo2.git"
```

## 🧪 Testing Configuration

### Configuration Testing Workflow

```bash
# 1. Validate configuration syntax
qdrant-loader --workspace . config

# 2. Validate project configurations
qdrant-loader project --workspace . validate

# 3. Check project status
qdrant-loader project --workspace . status

# 4. Initialize workspace
qdrant-loader --workspace . init

# 5. Process data
qdrant-loader --workspace . ingest
```

### Performance Testing

```bash
# Monitor resource usage during processing
top -p $(pgrep -f qdrant-loader)

# Check project status
qdrant-loader project --workspace . status

# Measure processing time
time qdrant-loader --workspace . ingest
```

## 📚 Related Documentation

- **[Environment Variables](./environment-variables.md)** - Complete environment variable reference
- **[Security Considerations](./security-considerations.md)** - Security best practices
- **[Data Sources](../detailed-guides/data-sources/)** - Source-specific configuration
- **[Troubleshooting](../troubleshooting/)** - Common configuration issues

## 🆘 Getting Help

### Configuration Issues

- **[Common Issues](../troubleshooting/common-issues.md)** - Frequent configuration problems
- **[Performance Issues](../troubleshooting/performance-issues.md)** - Performance tuning help
- **[GitHub Issues](https://github.com/martin-papy/qdrant-loader/issues)** - Report configuration bugs

### Community Support

- **[GitHub Discussions](https://github.com/martin-papy/qdrant-loader/discussions)** - Ask configuration questions
- **[Configuration Examples](https://github.com/martin-papy/qdrant-loader/tree/main/examples)** - Real-world configuration examples

---

**Ready to configure QDrant Loader?** Start with the [Environment Variables](./environment-variables.md) guide for complete setup instructions.
