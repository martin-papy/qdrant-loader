# Environment Variables Reference

This comprehensive reference covers all environment variables used by QDrant Loader and its MCP server. Environment variables provide a secure and flexible way to configure your QDrant Loader installation.

## 🎯 Overview

Environment variables are the recommended way to configure sensitive information like API keys and connection strings. They take precedence over configuration files and provide a secure way to manage credentials across different environments.

### Configuration Priority

```text
1. Command-line arguments    (highest priority)
2. Environment variables     ← This guide
3. Configuration file
4. Default values           (lowest priority)
```

## 🔧 Core Configuration

### QDrant Database Connection

#### QDRANT_URL

- **Description**: URL of your QDrant database instance
- **Required**: Yes
- **Format**: `http://host:port` or `https://host:port`
- **Examples**:

  ```bash
  # Local QDrant instance
  export QDRANT_URL="http://localhost:6333"
  
  # QDrant Cloud
  export QDRANT_URL="https://your-cluster.qdrant.io"
  
  # Custom port
  export QDRANT_URL="http://qdrant.company.com:6333"
  ```

#### QDRANT_API_KEY

- **Description**: API key for QDrant Cloud or secured instances
- **Required**: Only for QDrant Cloud or secured instances
- **Format**: String
- **Examples**:

  ```bash
  # QDrant Cloud API key
  export QDRANT_API_KEY="your-qdrant-cloud-api-key"
  
  # Self-hosted with authentication
  export QDRANT_API_KEY="your-custom-api-key"
  ```

#### QDRANT_COLLECTION_NAME

- **Description**: Name of the QDrant collection to use
- **Required**: No (defaults to "documents")
- **Format**: String (alphanumeric, underscores, hyphens)
- **Examples**:

  ```bash
  # Default collection
  export QDRANT_COLLECTION_NAME="documents"
  
  # Project-specific collection
  export QDRANT_COLLECTION_NAME="my_project_docs"
  
  # Environment-specific collection
  export QDRANT_COLLECTION_NAME="production_knowledge_base"
  ```

#### QDRANT_TIMEOUT

- **Description**: Timeout for QDrant operations in seconds
- **Required**: No (defaults to 30)
- **Format**: Integer
- **Examples**:

  ```bash
  # Default timeout
  export QDRANT_TIMEOUT="30"
  
  # Longer timeout for large operations
  export QDRANT_TIMEOUT="120"
  
  # Shorter timeout for fast networks
  export QDRANT_TIMEOUT="10"
  ```

### OpenAI Configuration

#### OPENAI_API_KEY

- **Description**: OpenAI API key for embeddings generation
- **Required**: Yes
- **Format**: String starting with "sk-"
- **Examples**:

  ```bash
  # OpenAI API key
  export OPENAI_API_KEY="sk-your-openai-api-key"
  ```

#### OPENAI_MODEL

- **Description**: OpenAI embedding model to use
- **Required**: No (defaults to "text-embedding-3-small")
- **Format**: String
- **Examples**:

  ```bash
  # Default model (recommended)
  export OPENAI_MODEL="text-embedding-3-small"
  
  # Higher quality model
  export OPENAI_MODEL="text-embedding-3-large"
  
  # Legacy model
  export OPENAI_MODEL="text-embedding-ada-002"
  ```

#### OPENAI_BATCH_SIZE

- **Description**: Number of texts to process in each API call
- **Required**: No (defaults to 100)
- **Format**: Integer (1-2048)
- **Examples**:

  ```bash
  # Default batch size
  export OPENAI_BATCH_SIZE="100"
  
  # Larger batches for efficiency
  export OPENAI_BATCH_SIZE="500"
  
  # Smaller batches for rate limiting
  export OPENAI_BATCH_SIZE="50"
  ```

#### OPENAI_MAX_RETRIES

- **Description**: Maximum number of retries for failed API calls
- **Required**: No (defaults to 3)
- **Format**: Integer
- **Examples**:

  ```bash
  # Default retries
  export OPENAI_MAX_RETRIES="3"
  
  # More retries for unreliable networks
  export OPENAI_MAX_RETRIES="5"
  
  # Fewer retries for fast failure
  export OPENAI_MAX_RETRIES="1"
  ```

## 📊 Data Source Configuration

### Git Repository Settings

#### GIT_USERNAME

- **Description**: Username for Git authentication
- **Required**: Only for private repositories
- **Format**: String
- **Examples**:

  ```bash
  # GitHub username
  export GIT_USERNAME="your-github-username"
  
  # GitLab username
  export GIT_USERNAME="your-gitlab-username"
  ```

#### GIT_TOKEN

- **Description**: Personal access token for Git authentication
- **Required**: Only for private repositories
- **Format**: String
- **Examples**:

  ```bash
  # GitHub personal access token
  export GIT_TOKEN="ghp_your-github-token"
  
  # GitLab personal access token
  export GIT_TOKEN="glpat-your-gitlab-token"
  ```

#### GIT_CLONE_DEPTH

- **Description**: Depth for Git clone operations
- **Required**: No (defaults to 1)
- **Format**: Integer
- **Examples**:

  ```bash
  # Shallow clone (default)
  export GIT_CLONE_DEPTH="1"
  
  # Full history
  export GIT_CLONE_DEPTH="0"
  
  # Last 10 commits
  export GIT_CLONE_DEPTH="10"
  ```

### Confluence Configuration

#### CONFLUENCE_BASE_URL

- **Description**: Base URL of your Confluence instance
- **Required**: Only when using Confluence
- **Format**: URL
- **Examples**:

  ```bash
  # Atlassian Cloud
  export CONFLUENCE_BASE_URL="https://company.atlassian.net"
  
  # Self-hosted Confluence
  export CONFLUENCE_BASE_URL="https://confluence.company.com"
  ```

#### CONFLUENCE_USERNAME

- **Description**: Confluence username or email
- **Required**: Only when using Confluence
- **Format**: String
- **Examples**:

  ```bash
  # Email address
  export CONFLUENCE_USERNAME="user@company.com"
  
  # Username
  export CONFLUENCE_USERNAME="john.doe"
  ```

#### CONFLUENCE_API_TOKEN

- **Description**: Confluence API token
- **Required**: Only when using Confluence
- **Format**: String
- **Examples**:

  ```bash
  # Confluence API token
  export CONFLUENCE_API_TOKEN="your-confluence-api-token"
  ```

#### CONFLUENCE_SPACES

- **Description**: Comma-separated list of Confluence spaces to index
- **Required**: No (defaults to all accessible spaces)
- **Format**: Comma-separated strings
- **Examples**:

  ```bash
  # Single space
  export CONFLUENCE_SPACES="DOCS"
  
  # Multiple spaces
  export CONFLUENCE_SPACES="DOCS,TECH,SUPPORT"
  
  # All spaces (default)
  # export CONFLUENCE_SPACES=""
  ```

### JIRA Configuration

#### JIRA_BASE_URL

- **Description**: Base URL of your JIRA instance
- **Required**: Only when using JIRA
- **Format**: URL
- **Examples**:

  ```bash
  # Atlassian Cloud
  export JIRA_BASE_URL="https://company.atlassian.net"
  
  # Self-hosted JIRA
  export JIRA_BASE_URL="https://jira.company.com"
  ```

#### JIRA_USERNAME

- **Description**: JIRA username or email
- **Required**: Only when using JIRA
- **Format**: String
- **Examples**:

  ```bash
  # Email address
  export JIRA_USERNAME="user@company.com"
  
  # Username
  export JIRA_USERNAME="john.doe"
  ```

#### JIRA_API_TOKEN

- **Description**: JIRA API token
- **Required**: Only when using JIRA
- **Format**: String
- **Examples**:

  ```bash
  # JIRA API token
  export JIRA_API_TOKEN="your-jira-api-token"
  ```

#### JIRA_PROJECTS

- **Description**: Comma-separated list of JIRA projects to index
- **Required**: No (defaults to all accessible projects)
- **Format**: Comma-separated strings
- **Examples**:

  ```bash
  # Single project
  export JIRA_PROJECTS="PROJ"
  
  # Multiple projects
  export JIRA_PROJECTS="PROJ,DOCS,SUPPORT"
  
  # All projects (default)
  # export JIRA_PROJECTS=""
  ```

## ⚙️ Processing Configuration

### Text Processing

#### QDRANT_LOADER_CHUNK_SIZE

- **Description**: Maximum size of text chunks in tokens
- **Required**: No (defaults to 1000)
- **Format**: Integer
- **Examples**:

  ```bash
  # Default chunk size
  export QDRANT_LOADER_CHUNK_SIZE="1000"
  
  # Larger chunks for better context
  export QDRANT_LOADER_CHUNK_SIZE="1500"
  
  # Smaller chunks for faster processing
  export QDRANT_LOADER_CHUNK_SIZE="500"
  ```

#### QDRANT_LOADER_CHUNK_OVERLAP

- **Description**: Overlap between chunks in tokens
- **Required**: No (defaults to 200)
- **Format**: Integer
- **Examples**:

  ```bash
  # Default overlap
  export QDRANT_LOADER_CHUNK_OVERLAP="200"
  
  # More overlap for continuity
  export QDRANT_LOADER_CHUNK_OVERLAP="400"
  
  # Less overlap for efficiency
  export QDRANT_LOADER_CHUNK_OVERLAP="100"
  ```

#### QDRANT_LOADER_MAX_FILE_SIZE

- **Description**: Maximum file size to process
- **Required**: No (defaults to "50MB")
- **Format**: String with unit (KB, MB, GB)
- **Examples**:

  ```bash
  # Default size limit
  export QDRANT_LOADER_MAX_FILE_SIZE="50MB"
  
  # Larger files
  export QDRANT_LOADER_MAX_FILE_SIZE="200MB"
  
  # Smaller files only
  export QDRANT_LOADER_MAX_FILE_SIZE="10MB"
  ```

### File Processing

#### QDRANT_LOADER_SUPPORTED_FORMATS

- **Description**: Comma-separated list of supported file formats
- **Required**: No (defaults to common formats)
- **Format**: Comma-separated file extensions
- **Examples**:

  ```bash
  # Default formats
  export QDRANT_LOADER_SUPPORTED_FORMATS="md,txt,pdf,docx,pptx,xlsx"
  
  # Text only
  export QDRANT_LOADER_SUPPORTED_FORMATS="md,txt,rst"
  
  # All supported formats
  export QDRANT_LOADER_SUPPORTED_FORMATS="md,txt,pdf,docx,pptx,xlsx,html,json,yaml,csv"
  ```

#### QDRANT_LOADER_EXCLUDE_PATTERNS

- **Description**: Comma-separated list of patterns to exclude
- **Required**: No
- **Format**: Comma-separated glob patterns
- **Examples**:

  ```bash
  # Common exclusions
  export QDRANT_LOADER_EXCLUDE_PATTERNS="*.log,node_modules/,__pycache__/"
  
  # Development exclusions
  export QDRANT_LOADER_EXCLUDE_PATTERNS="*.log,*.tmp,.git/,build/,dist/"
  
  # Custom exclusions
  export QDRANT_LOADER_EXCLUDE_PATTERNS="private/,draft/,*.backup"
  ```

## 🤖 MCP Server Configuration

### Server Settings

#### MCP_SERVER_LOG_LEVEL

- **Description**: Log level for MCP server
- **Required**: No (defaults to "INFO")
- **Format**: String (DEBUG, INFO, WARNING, ERROR)
- **Examples**:

  ```bash
  # Default logging
  export MCP_SERVER_LOG_LEVEL="INFO"
  
  # Debug logging
  export MCP_SERVER_LOG_LEVEL="DEBUG"
  
  # Minimal logging
  export MCP_SERVER_LOG_LEVEL="WARNING"
  ```

#### MCP_SERVER_MAX_RESULTS

- **Description**: Maximum number of search results to return
- **Required**: No (defaults to 10)
- **Format**: Integer
- **Examples**:

  ```bash
  # Default results
  export MCP_SERVER_MAX_RESULTS="10"
  
  # More results
  export MCP_SERVER_MAX_RESULTS="20"
  
  # Fewer results for speed
  export MCP_SERVER_MAX_RESULTS="5"
  ```

#### MCP_SERVER_TIMEOUT

- **Description**: Timeout for MCP server operations in seconds
- **Required**: No (defaults to 30)
- **Format**: Integer
- **Examples**:

  ```bash
  # Default timeout
  export MCP_SERVER_TIMEOUT="30"
  
  # Longer timeout for complex searches
  export MCP_SERVER_TIMEOUT="60"
  
  # Shorter timeout for responsiveness
  export MCP_SERVER_TIMEOUT="10"
  ```

### Search Configuration

#### MCP_SERVER_SIMILARITY_THRESHOLD

- **Description**: Minimum similarity score for search results
- **Required**: No (defaults to 0.7)
- **Format**: Float (0.0-1.0)
- **Examples**:

  ```bash
  # Default threshold
  export MCP_SERVER_SIMILARITY_THRESHOLD="0.7"
  
  # Higher precision
  export MCP_SERVER_SIMILARITY_THRESHOLD="0.8"
  
  # Lower precision, more results
  export MCP_SERVER_SIMILARITY_THRESHOLD="0.6"
  ```

#### MCP_SERVER_CACHE_ENABLED

- **Description**: Enable caching for search results
- **Required**: No (defaults to false)
- **Format**: Boolean (true/false)
- **Examples**:

  ```bash
  # Enable caching
  export MCP_SERVER_CACHE_ENABLED="true"
  
  # Disable caching
  export MCP_SERVER_CACHE_ENABLED="false"
  ```

#### MCP_SERVER_CACHE_TTL

- **Description**: Cache time-to-live in seconds
- **Required**: No (defaults to 300)
- **Format**: Integer
- **Examples**:

  ```bash
  # Default cache duration (5 minutes)
  export MCP_SERVER_CACHE_TTL="300"
  
  # Longer cache (1 hour)
  export MCP_SERVER_CACHE_TTL="3600"
  
  # Shorter cache (1 minute)
  export MCP_SERVER_CACHE_TTL="60"
  ```

## 📝 Logging and Monitoring

### Logging Configuration

#### QDRANT_LOADER_LOG_LEVEL

- **Description**: Log level for QDrant Loader
- **Required**: No (defaults to "INFO")
- **Format**: String (DEBUG, INFO, WARNING, ERROR)
- **Examples**:

  ```bash
  # Default logging
  export QDRANT_LOADER_LOG_LEVEL="INFO"
  
  # Debug logging
  export QDRANT_LOADER_LOG_LEVEL="DEBUG"
  
  # Error logging only
  export QDRANT_LOADER_LOG_LEVEL="ERROR"
  ```

#### QDRANT_LOADER_LOG_FILE

- **Description**: Path to log file
- **Required**: No (defaults to console only)
- **Format**: File path
- **Examples**:

  ```bash
  # Log to file
  export QDRANT_LOADER_LOG_FILE="/var/log/qdrant-loader.log"
  
  # Log to user directory
  export QDRANT_LOADER_LOG_FILE="~/.qdrant-loader/logs/app.log"
  
  # Console only (default)
  # export QDRANT_LOADER_LOG_FILE=""
  ```

#### QDRANT_LOADER_LOG_FORMAT

- **Description**: Log message format
- **Required**: No (defaults to standard format)
- **Format**: String with format specifiers
- **Examples**:

  ```bash
  # Default format
  export QDRANT_LOADER_LOG_FORMAT="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  
  # Simple format
  export QDRANT_LOADER_LOG_FORMAT="%(levelname)s: %(message)s"
  
  # Detailed format
  export QDRANT_LOADER_LOG_FORMAT="%(asctime)s [%(process)d] %(levelname)s %(name)s: %(message)s"
  ```

### Performance Monitoring

#### QDRANT_LOADER_METRICS_ENABLED

- **Description**: Enable performance metrics collection
- **Required**: No (defaults to false)
- **Format**: Boolean (true/false)
- **Examples**:

  ```bash
  # Enable metrics
  export QDRANT_LOADER_METRICS_ENABLED="true"
  
  # Disable metrics
  export QDRANT_LOADER_METRICS_ENABLED="false"
  ```

#### QDRANT_LOADER_METRICS_PORT

- **Description**: Port for metrics endpoint
- **Required**: No (defaults to 9090)
- **Format**: Integer
- **Examples**:

  ```bash
  # Default metrics port
  export QDRANT_LOADER_METRICS_PORT="9090"
  
  # Custom port
  export QDRANT_LOADER_METRICS_PORT="8080"
  ```

## 🔒 Security Configuration

### API Key Management

#### Best Practices for API Keys

```bash
# ✅ Good: Use environment variables
export OPENAI_API_KEY="sk-your-key-here"

# ❌ Bad: Hardcode in scripts
OPENAI_API_KEY="sk-your-key-here"  # Don't do this!

# ✅ Good: Use .env files (not committed to git)
echo "OPENAI_API_KEY=sk-your-key-here" >> .env

# ✅ Good: Use secure credential storage
# macOS Keychain, Windows Credential Manager, etc.
```

#### Environment-Specific Keys

```bash
# Development environment
export OPENAI_API_KEY="sk-dev-key-here"
export QDRANT_URL="http://localhost:6333"

# Production environment
export OPENAI_API_KEY="sk-prod-key-here"
export QDRANT_URL="https://prod-qdrant.company.com"
export QDRANT_API_KEY="prod-qdrant-api-key"
```

### Network Security

#### QDRANT_LOADER_TLS_VERIFY

- **Description**: Verify TLS certificates
- **Required**: No (defaults to true)
- **Format**: Boolean (true/false)
- **Examples**:

  ```bash
  # Verify certificates (recommended)
  export QDRANT_LOADER_TLS_VERIFY="true"
  
  # Skip verification (development only)
  export QDRANT_LOADER_TLS_VERIFY="false"
  ```

#### QDRANT_LOADER_PROXY

- **Description**: HTTP proxy for outbound connections
- **Required**: No
- **Format**: URL
- **Examples**:

  ```bash
  # HTTP proxy
  export QDRANT_LOADER_PROXY="http://proxy.company.com:8080"
  
  # HTTPS proxy
  export QDRANT_LOADER_PROXY="https://proxy.company.com:8080"
  
  # Proxy with authentication
  export QDRANT_LOADER_PROXY="http://user:pass@proxy.company.com:8080"
  ```

## 📋 Environment File Templates

### Basic .env Template

```bash
# .env - Basic configuration
# Copy this template and fill in your values

# Required: QDrant Database
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=documents

# Required: OpenAI API
OPENAI_API_KEY=sk-your-openai-api-key

# Optional: QDrant Cloud
# QDRANT_API_KEY=your-qdrant-cloud-api-key

# Optional: Logging
QDRANT_LOADER_LOG_LEVEL=INFO
```

### Development .env Template

```bash
# .env.development - Development environment
# Copy this template for development setup

# QDrant Database (local)
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=dev_documents
QDRANT_TIMEOUT=30

# OpenAI API (development key)
OPENAI_API_KEY=sk-your-dev-openai-api-key
OPENAI_MODEL=text-embedding-3-small
OPENAI_BATCH_SIZE=50

# Processing (faster for development)
QDRANT_LOADER_CHUNK_SIZE=500
QDRANT_LOADER_CHUNK_OVERLAP=100
QDRANT_LOADER_MAX_FILE_SIZE=10MB

# Logging (debug level)
QDRANT_LOADER_LOG_LEVEL=DEBUG
MCP_SERVER_LOG_LEVEL=DEBUG

# MCP Server (development settings)
MCP_SERVER_MAX_RESULTS=5
MCP_SERVER_TIMEOUT=10
MCP_SERVER_CACHE_ENABLED=false
```

### Production .env Template

```bash
# .env.production - Production environment
# Copy this template for production setup

# QDrant Database (production)
QDRANT_URL=https://your-qdrant-cluster.qdrant.io
QDRANT_API_KEY=your-production-qdrant-api-key
QDRANT_COLLECTION_NAME=production_documents
QDRANT_TIMEOUT=60

# OpenAI API (production key)
OPENAI_API_KEY=sk-your-prod-openai-api-key
OPENAI_MODEL=text-embedding-3-small
OPENAI_BATCH_SIZE=200
OPENAI_MAX_RETRIES=5

# Processing (optimized for production)
QDRANT_LOADER_CHUNK_SIZE=1200
QDRANT_LOADER_CHUNK_OVERLAP=300
QDRANT_LOADER_MAX_FILE_SIZE=100MB

# Data Sources (production credentials)
CONFLUENCE_BASE_URL=https://company.atlassian.net
CONFLUENCE_USERNAME=service-account@company.com
CONFLUENCE_API_TOKEN=your-confluence-api-token

JIRA_BASE_URL=https://company.atlassian.net
JIRA_USERNAME=service-account@company.com
JIRA_API_TOKEN=your-jira-api-token

# Logging (production level)
QDRANT_LOADER_LOG_LEVEL=INFO
QDRANT_LOADER_LOG_FILE=/var/log/qdrant-loader/app.log
MCP_SERVER_LOG_LEVEL=INFO

# MCP Server (production settings)
MCP_SERVER_MAX_RESULTS=15
MCP_SERVER_TIMEOUT=30
MCP_SERVER_CACHE_ENABLED=true
MCP_SERVER_CACHE_TTL=600
MCP_SERVER_SIMILARITY_THRESHOLD=0.75

# Security (production)
QDRANT_LOADER_TLS_VERIFY=true

# Monitoring (production)
QDRANT_LOADER_METRICS_ENABLED=true
QDRANT_LOADER_METRICS_PORT=9090
```

### Team .env Template

```bash
# .env.team - Team/shared environment
# Copy this template for team setups

# QDrant Database (shared instance)
QDRANT_URL=http://qdrant.team.local:6333
QDRANT_COLLECTION_NAME=team_knowledge
QDRANT_TIMEOUT=45

# OpenAI API (team key)
OPENAI_API_KEY=sk-your-team-openai-api-key
OPENAI_MODEL=text-embedding-3-small
OPENAI_BATCH_SIZE=100

# Data Sources (team credentials)
CONFLUENCE_BASE_URL=https://team.atlassian.net
CONFLUENCE_USERNAME=${USER}@company.com
CONFLUENCE_API_TOKEN=your-personal-confluence-token
CONFLUENCE_SPACES=TEAM,DOCS,TECH

GIT_USERNAME=${USER}
GIT_TOKEN=your-personal-git-token

# Processing (balanced for team use)
QDRANT_LOADER_CHUNK_SIZE=1000
QDRANT_LOADER_CHUNK_OVERLAP=200
QDRANT_LOADER_MAX_FILE_SIZE=50MB

# Logging (team level)
QDRANT_LOADER_LOG_LEVEL=INFO
MCP_SERVER_LOG_LEVEL=INFO

# MCP Server (team settings)
MCP_SERVER_MAX_RESULTS=10
MCP_SERVER_TIMEOUT=30
MCP_SERVER_CACHE_ENABLED=true
MCP_SERVER_CACHE_TTL=300
```

## 🔧 Environment Management

### Loading Environment Variables

#### Using .env Files

```bash
# Load from .env file
set -a  # automatically export all variables
source .env
set +a  # stop automatically exporting

# Or use dotenv (if installed)
python -m dotenv run qdrant-loader status

# Or use direnv (if installed)
echo "source .env" > .envrc
direnv allow
```

#### Using Environment-Specific Files

```bash
# Load development environment
source .env.development

# Load production environment
source .env.production

# Load with prefix
env $(cat .env.production | xargs) qdrant-loader status
```

### Validation and Testing

#### Check Environment Variables

```bash
# Check if required variables are set
if [ -z "$QDRANT_URL" ]; then
  echo "Error: QDRANT_URL not set"
  exit 1
fi

if [ -z "$OPENAI_API_KEY" ]; then
  echo "Error: OPENAI_API_KEY not set"
  exit 1
fi

# Test configuration
qdrant-loader config show
qdrant-loader config test
```

#### Environment Variable Script

```bash
#!/bin/bash
# check-env.sh - Validate environment variables

required_vars=(
  "QDRANT_URL"
  "OPENAI_API_KEY"
  "QDRANT_COLLECTION_NAME"
)

optional_vars=(
  "QDRANT_API_KEY"
  "CONFLUENCE_BASE_URL"
  "JIRA_BASE_URL"
)

echo "Checking required environment variables..."
for var in "${required_vars[@]}"; do
  if [ -z "${!var}" ]; then
    echo "❌ $var is not set"
    exit 1
  else
    echo "✅ $var is set"
  fi
done

echo "Checking optional environment variables..."
for var in "${optional_vars[@]}"; do
  if [ -z "${!var}" ]; then
    echo "⚠️  $var is not set (optional)"
  else
    echo "✅ $var is set"
  fi
done

echo "Environment validation complete!"
```

## 🔗 Related Documentation

- **[Configuration File Reference](./config-file-reference.md)** - YAML configuration options
- **[Basic Configuration](../getting-started/basic-configuration.md)** - Getting started with configuration
- **[Security Considerations](./security-considerations.md)** - Security best practices
- **[Advanced Settings](./advanced-settings.md)** - Performance tuning options

## 📋 Environment Variables Checklist

- [ ] **Core variables** set (QDRANT_URL, OPENAI_API_KEY, QDRANT_COLLECTION_NAME)
- [ ] **Data source credentials** configured for your sources
- [ ] **Processing settings** tuned for your use case
- [ ] **MCP server settings** configured for AI tools
- [ ] **Logging configuration** appropriate for your environment
- [ ] **Security settings** properly configured
- [ ] **Environment file** created and secured (chmod 600)
- [ ] **Variables validated** with test commands
- [ ] **Documentation** updated with your specific settings

---

**Environment configuration complete!** 🎉

Your QDrant Loader is now configured via environment variables. This provides a secure, flexible way to manage configuration across different environments while keeping sensitive information like API keys secure.
