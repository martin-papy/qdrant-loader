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
├── config.yaml # Main configuration file
├── .env # Environment variables
├── state.db # Processing state (auto-generated)
└── logs/ # Log files (optional)
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
# Required - OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Required - QDrant Configuration
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=documents
QDRANT_API_KEY=your_qdrant_api_key_here # Optional: for QDrant Cloud

# Optional - Git Authentication
REPO_TOKEN=your_github_token_here

# Optional - Confluence Configuration
CONFLUENCE_TOKEN=your_confluence_token_here
CONFLUENCE_EMAIL=your_confluence_email_here

# Optional - Jira Configuration
JIRA_TOKEN=your_jira_token_here
JIRA_EMAIL=your_jira_email_here
```

### 3. Basic Multi-Project Configuration

Edit `config.yaml`:

```yaml
# Global configuration shared across all projects
global:
  qdrant:
    url: "${QDRANT_URL}"
    collection_name: "${QDRANT_COLLECTION_NAME}"
  embedding:
    model: "text-embedding-3-small"
    api_key: "${OPENAI_API_KEY}"
  chunking:
    chunk_size: 1500
    chunk_overlap: 200

# Multi-project configuration
projects:
  my-project:
    project_id: "my-project"
    display_name: "My Documentation Project"
    description: "Company documentation and code"
    sources:
      git:
        docs-repo:
          base_url: "https://github.com/your-org/your-repo.git"
          branch: "main"
          include_paths:
            - "docs/**"
            - "README.md"
          file_types:
            - "*.md"
            - "*.py"
          enable_file_conversion: true
      localfile:
        local-docs:
          base_url: "file://./docs"
          include_paths:
            - "**/*.md"
            - "**/*.pdf"
          enable_file_conversion: true
```

## 📚 Configuration Sections

### 🔧 [Environment Variables](./environment-variables.md)

Complete reference for all environment variables including:

- **QDrant connection settings** - URL, API keys, collection configuration
- **Authentication credentials** - API tokens for data sources
- **Processing options** - Embedding models, file conversion settings

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
global:
  qdrant:
    url: "${QDRANT_URL}"
    collection_name: "${QDRANT_COLLECTION_NAME}"
  embedding:
    model: "text-embedding-3-small"
    api_key: "${OPENAI_API_KEY}"
    batch_size: 50
  chunking:
    chunk_size: 800
    chunk_overlap: 150

projects:
  dev-team:
    project_id: "dev-team"
    display_name: "Development Team Knowledge"
    description: "Code repositories, documentation, and project management"
    sources:
      git:
        main-app:
          base_url: "https://github.com/company/main-app.git"
          branch: "main"
          include_paths:
            - "src/**"
            - "docs/**"
          file_types:
            - "*.py"
            - "*.md"
          token: "${REPO_TOKEN}"
          enable_file_conversion: true
      confluence:
        dev-space:
          base_url: "https://company.atlassian.net/wiki"
          space_key: "DEV"
          token: "${CONFLUENCE_TOKEN}"
          email: "${CONFLUENCE_EMAIL}"
          enable_file_conversion: true
          download_attachments: true
      jira:
        project-tracker:
          base_url: "https://company.atlassian.net"
          project_key: "PROJ"
          token: "${JIRA_TOKEN}"
          email: "${JIRA_EMAIL}"
          enable_file_conversion: true
          download_attachments: true
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
global:
  qdrant:
    url: "${QDRANT_URL}"
    collection_name: "${QDRANT_COLLECTION_NAME}"
  embedding:
    model: "text-embedding-3-small"
    api_key: "${OPENAI_API_KEY}"
  chunking:
    chunk_size: 1200
    chunk_overlap: 300
  file_conversion:
    max_file_size: 52428800 # 50MB for large documents

projects:
  documentation:
    project_id: "documentation"
    display_name: "Documentation Hub"
    description: "Centralized documentation across platforms"
    sources:
      confluence:
        docs-space:
          base_url: "https://company.atlassian.net/wiki"
          space_key: "DOCS"
          token: "${CONFLUENCE_TOKEN}"
          email: "${CONFLUENCE_EMAIL}"
          enable_file_conversion: true
          download_attachments: true
      localfile:
        legacy-docs:
          base_url: "file://./legacy-docs"
          include_paths:
            - "**/*.pdf"
            - "**/*.docx"
            - "**/*.md"
          enable_file_conversion: true
      publicdocs:
        api-docs:
          base_url: "https://api-docs.example.com"
          selectors:
            content: ".content"
          enable_file_conversion: true
```

### 🔬 Research Team

**Goal**: Index and search research materials and data

```yaml
# config.yaml
global:
  qdrant:
    url: "${QDRANT_URL}"
    collection_name: "${QDRANT_COLLECTION_NAME}"
  embedding:
    model: "text-embedding-3-small"
    api_key: "${OPENAI_API_KEY}"
    batch_size: 20 # Slower processing for large files
  chunking:
    chunk_size: 1500
    chunk_overlap: 400
  file_conversion:
    max_file_size: 104857600 # 100MB for datasets

projects:
  research:
    project_id: "research"
    display_name: "Research Materials"
    description: "Research papers, datasets, and analysis tools"
    sources:
      localfile:
        research-papers:
          base_url: "file://./research-papers"
          include_paths:
            - "**/*.pdf"
            - "**/*.txt"
            - "**/*.csv"
          enable_file_conversion: true
        notebooks:
          base_url: "file://./notebooks"
          include_paths:
            - "**/*.ipynb"
            - "**/*.py"
          enable_file_conversion: true
      git:
        analysis-tools:
          base_url: "https://github.com/research-org/analysis-tools.git"
          include_paths:
            - "**/*.py"
            - "**/*.md"
            - "**/*.ipynb"
          token: "${REPO_TOKEN}"
          enable_file_conversion: true
```

### 🏢 Enterprise Deployment

**Goal**: Scalable, secure deployment for large organization

```yaml
# config.yaml
global:
  qdrant:
    url: "${QDRANT_URL}"
    api_key: "${QDRANT_API_KEY}"
    collection_name: "${QDRANT_COLLECTION_NAME}"
  embedding:
    model: "text-embedding-3-small"
    api_key: "${OPENAI_API_KEY}"
    batch_size: 100
  chunking:
    chunk_size: 1500
    chunk_overlap: 200

projects:
  enterprise-platform:
    project_id: "enterprise-platform"
    display_name: "Enterprise Platform"
    description: "Platform code, architecture, and documentation"
    sources:
      git:
        platform-repo:
          base_url: "https://github.com/enterprise/platform.git"
          branch: "main"
          include_paths:
            - "**/*.py"
            - "**/*.js"
            - "**/*.md"
          token: "${REPO_TOKEN}"
          enable_file_conversion: true
        services-repo:
          base_url: "https://github.com/enterprise/services.git"
          branch: "main"
          include_paths:
            - "**/*.py"
            - "**/*.md"
          token: "${REPO_TOKEN}"
          enable_file_conversion: true
      confluence:
        architecture:
          base_url: "https://enterprise.atlassian.net/wiki"
          space_key: "ARCH"
          token: "${CONFLUENCE_TOKEN}"
          email: "${CONFLUENCE_EMAIL}"
          enable_file_conversion: true
          download_attachments: true
        documentation:
          base_url: "https://enterprise.atlassian.net/wiki"
          space_key: "DOCS"
          token: "${CONFLUENCE_TOKEN}"
          email: "${CONFLUENCE_EMAIL}"
          enable_file_conversion: true
          download_attachments: true
      jira:
        platform-issues:
          base_url: "https://enterprise.atlassian.net"
          project_key: "PLAT"
          token: "${JIRA_TOKEN}"
          email: "${JIRA_EMAIL}"
          enable_file_conversion: true
          download_attachments: true
        services-issues:
          base_url: "https://enterprise.atlassian.net"
          project_key: "SERV"
          token: "${JIRA_TOKEN}"
          email: "${JIRA_EMAIL}"
          enable_file_conversion: true
          download_attachments: true
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
# Display current configuration
qdrant-loader config --workspace .

# Validate project configurations
qdrant-loader project validate --workspace .

# Check project status
qdrant-loader project status --workspace .

# List all projects
qdrant-loader project list --workspace .
```

### Common Validation Errors

#### Missing Required Settings

```bash
# Error: Missing QDRANT_URL
export QDRANT_URL=http://localhost:6333

# Error: Missing OPENAI_API_KEY
export OPENAI_API_KEY=your_openai_api_key

# Error: Missing collection name
export QDRANT_COLLECTION_NAME=documents
```

#### Invalid Configuration Syntax

```yaml
# ❌ Invalid YAML syntax - Missing quotes
projects:
  my-project:
    project_id: my-project # Missing quotes
    sources:
      git:
        repo:
          base_url: https://github.com/org/repo.git # Missing quotes
          branch: main # Missing quotes

# ✅ Correct YAML syntax
projects:
  my-project:
    project_id: "my-project" # Quoted string
    sources:
      git:
        repo:
          base_url: "https://github.com/org/repo.git" # Quoted string
          branch: "main" # Quoted string
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
# Monitor project status
qdrant-loader project status --workspace .

# Use debug logging for troubleshooting
qdrant-loader config --log-level DEBUG --workspace .
```

## 🔍 Advanced Configuration Patterns

### Multi-Environment Setup

```yaml
# config.yaml with environment variables
global:
  qdrant:
    url: "${QDRANT_URL}"
    collection_name: "${QDRANT_COLLECTION_NAME}"
  embedding:
    model: "${EMBEDDING_MODEL:-text-embedding-3-small}"
    api_key: "${OPENAI_API_KEY}"
    batch_size: ${BATCH_SIZE:-50}
  chunking:
    chunk_size: ${CHUNK_SIZE:-1500}
    chunk_overlap: ${CHUNK_OVERLAP:-200}

projects:
  main-project:
    project_id: "main-project"
    display_name: "Main Project"
    sources:
      git:
        repo:
          base_url: "${GIT_REPO_URL}"
          branch: "${GIT_BRANCH:-main}"
          include_paths:
            - "**/*.md"
            - "**/*.py"
          token: "${REPO_TOKEN}"
          enable_file_conversion: true
```

### Conditional Configuration

```yaml
# Different settings based on environment
global:
  qdrant:
    url: "${QDRANT_URL}"
    collection_name: "${QDRANT_COLLECTION_NAME}"
  embedding:
    api_key: "${OPENAI_API_KEY}"
  file_conversion:
    max_file_size: ${MAX_FILE_SIZE:-52428800} # 50MB default

projects:
  main-project:
    project_id: "main-project"
    sources:
      git:
        repo:
          base_url: "https://github.com/org/repo.git"
          branch: "main"
          max_file_size: ${MAX_FILE_SIZE:-1048576} # Smaller files in development
          token: "${REPO_TOKEN}"
          enable_file_conversion: true
```

### Template-Based Configuration

```yaml
# Base configuration template
_git_defaults: &git_defaults
  branch: "main"
  enable_file_conversion: true
  include_paths:
    - "**/*.md"
    - "**/*.py"
  token: "${REPO_TOKEN}"

global:
  qdrant:
    url: "${QDRANT_URL}"
    collection_name: "${QDRANT_COLLECTION_NAME}"
  embedding:
    api_key: "${OPENAI_API_KEY}"
  chunking:
    chunk_size: 1500
    chunk_overlap: 200

projects:
  multi-repo:
    project_id: "multi-repo"
    sources:
      git:
        repo1:
          <<: *git_defaults
          base_url: "https://github.com/org/repo1.git"
        repo2:
          <<: *git_defaults
          base_url: "https://github.com/org/repo2.git"
```

## 🧪 Testing Configuration

### Configuration Testing Workflow

```bash
# 1. Display current configuration
qdrant-loader config --workspace .

# 2. Validate project configurations
qdrant-loader project validate --workspace .

# 3. List all projects
qdrant-loader project list --workspace .

# 4. Check project status
qdrant-loader project status --workspace .

# 5. Initialize QDrant collection
qdrant-loader init --workspace .

# 6. Process data
qdrant-loader ingest --workspace .
```

### Performance Testing

```bash
# Monitor resource usage during processing
top -p $(pgrep -f qdrant-loader)

# Check project status
qdrant-loader project status --workspace .

# Measure processing time
time qdrant-loader ingest --workspace .
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
