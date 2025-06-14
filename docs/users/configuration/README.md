# Configuration Reference

This section provides comprehensive documentation for configuring QDrant Loader. Learn how to set up data sources, optimize performance, configure security, and customize behavior for your specific needs.

## 🎯 Configuration Overview

QDrant Loader supports two configuration approaches:

### 🆕 **Three-File Configuration (Recommended)**
- **`connectivity.yaml`** - Database connections, LLM providers, authentication, and endpoints
- **`projects.yaml`** - Project definitions, data sources, and project-specific settings
- **`fine-tuning.yaml`** - Processing parameters, performance tuning, and algorithm settings
- **`.env`** - Environment variables for credentials and system settings

### 📄 **Single-File Configuration (Legacy)**
- **`config.yaml`** - All configuration in one file (still supported for backward compatibility)
- **`.env`** - Environment variables for credentials and system settings

## 📁 Configuration Structure

### Three-File Structure (Recommended)

```text
your-workspace/
├── connectivity.yaml    # Database & service connections
├── projects.yaml       # Project definitions & data sources
├── fine-tuning.yaml    # Performance & processing settings
├── .env               # Environment variables
├── state.db          # Processing state (auto-generated)
└── logs/             # Log files (optional)
```

### Legacy Single-File Structure

```text
your-workspace/
├── config.yaml        # All configuration (legacy)
├── .env              # Environment variables
├── state.db         # Processing state (auto-generated)
└── logs/            # Log files (optional)
```

## 🚀 Quick Configuration

### Option 1: Three-File Setup (Recommended)

```bash
# Download three-file configuration templates
curl -o connectivity.yaml https://raw.githubusercontent.com/martin-papy/qdrant-loader/main/packages/qdrant-loader/conf/connectivity.template.yaml
curl -o projects.yaml https://raw.githubusercontent.com/martin-papy/qdrant-loader/main/packages/qdrant-loader/conf/projects.template.yaml
curl -o fine-tuning.yaml https://raw.githubusercontent.com/martin-papy/qdrant-loader/main/packages/qdrant-loader/conf/fine-tuning.template.yaml
curl -o .env https://raw.githubusercontent.com/martin-papy/qdrant-loader/main/packages/qdrant-loader/conf/.env.template
```

### Option 2: Single-File Setup (Legacy)

```bash
# Download single-file configuration template
curl -o config.yaml https://raw.githubusercontent.com/martin-papy/qdrant-loader/main/packages/qdrant-loader/conf/config.template.yaml
curl -o .env https://raw.githubusercontent.com/martin-papy/qdrant-loader/main/packages/qdrant-loader/conf/.env.template
```

## 🔧 Three-File Configuration Details

### 1. Connectivity Configuration (`connectivity.yaml`)

Manages all external service connections and authentication:

```yaml
# Database connections
qdrant:
  url: "http://localhost:6333"
  api_key: "${QDRANT_API_KEY}"
  collection_name: "documents"

# Embedding services
embedding:
  endpoint: "https://api.openai.com/v1"
  api_key: "${OPENAI_API_KEY}"
  model: "text-embedding-3-small"

# Graph database (for Graphiti features)
neo4j:
  uri: "bolt://localhost:7687"
  username: "${NEO4J_USERNAME}"
  password: "${NEO4J_PASSWORD}"

# External service authentication
authentication:
  git:
    github_token: "${GITHUB_TOKEN}"
  confluence:
    token: "${CONFLUENCE_TOKEN}"
    email: "${CONFLUENCE_EMAIL}"
  jira:
    token: "${JIRA_TOKEN}"
    email: "${JIRA_EMAIL}"
```

### 2. Projects Configuration (`projects.yaml`)

Defines your data sources and project structure:

```yaml
projects:
  my-project:
    project_id: "my-project"
    display_name: "My Documentation Project"
    description: "Project description"
    
    sources:
      git:
        my-repo:
          base_url: "https://github.com/your-org/your-repo.git"
          branch: "main"
          include_paths:
            - "**/*.md"
            - "**/*.py"
          token: "${REPO_TOKEN}"
      
      confluence:
        company-wiki:
          base_url: "https://company.atlassian.net/wiki"
          space_key: "DOCS"
          token: "${CONFLUENCE_TOKEN}"
          email: "${CONFLUENCE_EMAIL}"
```

### 3. Fine-Tuning Configuration (`fine-tuning.yaml`)

Controls processing behavior and performance:

```yaml
# Text processing
chunking:
  chunk_size: 1500
  chunk_overlap: 200
  respect_boundaries: true

# Performance settings
processing:
  batch_size: 100
  max_concurrent_requests: 10
  timeout_seconds: 300

# File conversion
file_conversion:
  max_file_size: 52428800  # 50MB
  conversion_timeout: 300
  enable_llm_descriptions: false

# Caching
caching:
  embeddings:
    enabled: true
    ttl_hours: 168  # 1 week
  file_content:
    enabled: true
    ttl_hours: 24
```

## 🔄 Configuration Loading Behavior

### Automatic Detection

QDrant Loader automatically detects your configuration approach:

1. **Three-File Mode**: If `connectivity.yaml`, `projects.yaml`, or `fine-tuning.yaml` exist
2. **Legacy Mode**: If only `config.yaml` exists
3. **Selective Loading**: Load only specific domains (e.g., connectivity + projects)

### Domain Loading

You can load specific configuration domains:

```python
# Load all domains
settings = Settings.from_multi_file("/path/to/config")

# Load specific domains only
settings = Settings.from_multi_file(
    "/path/to/config", 
    domains={'connectivity', 'projects'}
)
```

### Environment Variable Support

All configuration files support environment variable substitution:

```yaml
# In any configuration file
api_key: "${OPENAI_API_KEY}"
url: "${QDRANT_URL:-http://localhost:6333}"  # With default value
```

## 📚 Configuration Sections

### 🔧 [Environment Variables](./environment-variables.md)

Complete reference for all environment variables including:

- **QDrant connection settings** - URL, API keys, collection configuration
- **Authentication credentials** - API tokens for data sources
- **Processing options** - Embedding models, file conversion settings
- **Performance tuning** - Memory limits, concurrency settings

### 📄 [Config File Reference](./config-file-reference.md)

Detailed documentation for configuration file options:

- **Three-file configuration** - Domain-specific settings and structure
- **Legacy single-file configuration** - Backward compatibility reference
- **Configuration validation** - Schema and validation rules
- **Migration guide** - Moving from single-file to three-file setup

### 🔒 [Security Considerations](./security-considerations.md)

Security best practices and configuration:

- **API key management** - Secure storage and rotation
- **Access control** - Permissions and authentication
- **Data privacy** - Handling sensitive information
- **Network security** - TLS, firewalls, and secure connections

## 🎯 Configuration by Use Case

### 👨‍💻 Software Development Team

**Goal**: Integrate code repositories, documentation, and project management

#### Three-File Approach

**connectivity.yaml**:
```yaml
qdrant:
  url: "http://qdrant-server:6333"
  collection_name: "team_knowledge"

embedding:
  endpoint: "https://api.openai.com/v1"
  api_key: "${OPENAI_API_KEY}"
  model: "text-embedding-3-small"

authentication:
  git:
    github_token: "${REPO_TOKEN}"
  confluence:
    token: "${CONFLUENCE_TOKEN}"
    email: "team@company.com"
  jira:
    token: "${JIRA_TOKEN}"
    email: "team@company.com"
```

**projects.yaml**:
```yaml
projects:
  main-app:
    project_id: "main-app"
    display_name: "Main Application"
    description: "Core application code and documentation"
    
    sources:
      git:
        main-repo:
          base_url: "https://github.com/company/main-app.git"
          branch: "main"
          include_paths: ["src/**/*.py", "docs/**/*.md"]
      
      confluence:
        dev-space:
          base_url: "https://company.atlassian.net/wiki"
          space_key: "DEV"
          include_patterns: ["Architecture/*", "API/*"]
      
      jira:
        project-tickets:
          base_url: "https://company.atlassian.net"
          project_key: "PROJ"
          include_issue_types: ["Story", "Epic", "Bug"]
```

**fine-tuning.yaml**:
```yaml
chunking:
  chunk_size: 800
  chunk_overlap: 150

processing:
  batch_size: 50
  max_concurrent_requests: 10

file_conversion:
  enabled: true
  max_file_size: 52428800
```

### 📚 Documentation Team

**Goal**: Centralize and search documentation across platforms

#### Three-File Approach

**connectivity.yaml**:
```yaml
qdrant:
  url: "http://localhost:6333"
  collection_name: "docs_knowledge"

embedding:
  endpoint: "https://api.openai.com/v1"
  api_key: "${OPENAI_API_KEY}"
  model: "text-embedding-3-large"

authentication:
  confluence:
    token: "${CONFLUENCE_TOKEN}"
    email: "${CONFLUENCE_EMAIL}"
```

**projects.yaml**:
```yaml
projects:
  documentation:
    project_id: "documentation"
    display_name: "Company Documentation"
    description: "All company documentation and guides"
    
    sources:
      confluence:
        docs-space:
          base_url: "https://company.atlassian.net/wiki"
          space_key: "DOCS"
          include_attachments: true
      
      localfile:
        legacy-docs:
          base_url: "file://./legacy-docs"
          include_paths: ["**/*.pdf", "**/*.docx", "**/*.md"]
      
      public_docs:
        api-docs:
          base_url: "https://api-docs.example.com"
          css_selector: ".content"
          max_pages: 100
```

**fine-tuning.yaml**:
```yaml
chunking:
  chunk_size: 1200
  chunk_overlap: 300

file_conversion:
  enabled: true
  max_file_size: 104857600  # 100MB for large documents
  conversion_timeout: 600

processing:
  batch_size: 20  # Slower processing for large files
```

## 🔄 Migration from Single-File to Three-File

### Automatic Migration

QDrant Loader can automatically migrate your existing `config.yaml`:

```bash
# The system will automatically detect and use config.yaml if three-file configs don't exist
qdrant-loader --workspace . ingest
```

### Manual Migration

1. **Split your existing config.yaml**:
   - Move database/service connections → `connectivity.yaml`
   - Move project definitions → `projects.yaml`  
   - Move performance settings → `fine-tuning.yaml`

2. **Use the templates as guides**:
   ```bash
   # Download templates to see the structure
   curl -o connectivity.template.yaml https://raw.githubusercontent.com/martin-papy/qdrant-loader/main/packages/qdrant-loader/conf/connectivity.template.yaml
   curl -o projects.template.yaml https://raw.githubusercontent.com/martin-papy/qdrant-loader/main/packages/qdrant-loader/conf/projects.template.yaml
   curl -o fine-tuning.template.yaml https://raw.githubusercontent.com/martin-papy/qdrant-loader/main/packages/qdrant-loader/conf/fine-tuning.template.yaml
   ```

3. **Test your configuration**:
   ```bash
   # Validate the new configuration
   qdrant-loader --workspace . validate-config
   ```

## 🎯 Benefits of Three-File Configuration

### ✅ **Advantages**

- **🔧 Modular**: Separate concerns for easier management
- **👥 Team-friendly**: Different team members can manage different domains
- **🔒 Security**: Isolate sensitive connection details
- **⚡ Performance**: Load only required configuration domains
- **📝 Maintainable**: Smaller, focused configuration files
- **🔄 Flexible**: Mix and match configuration approaches

### 📄 **When to Use Single-File**

- **Simple setups**: Single project with basic requirements
- **Legacy systems**: Existing configurations that work well
- **Quick prototyping**: Fast setup for testing
- **Minimal complexity**: When domain separation isn't needed

Choose the approach that best fits your team's needs and complexity requirements!

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
