# Environment Variables Reference

This reference covers the environment variables actually used by QDrant Loader and its MCP server. Environment variables provide a secure way to configure credentials and basic settings.

## 🎯 Overview

Environment variables are used primarily for sensitive information like API keys and connection strings. They are substituted into configuration files using `${VARIABLE_NAME}` syntax.

### Configuration Priority

```text
1. Command-line arguments    (highest priority)
2. Environment variables     ← This guide
3. Configuration file
4. Default values           (lowest priority)
```

## 🔧 Core Environment Variables

Based on the actual codebase implementation, these are the environment variables that are actually used:

### QDrant Database Connection

#### QDRANT_URL

- **Description**: URL of your QDrant database instance
- **Required**: Yes (when used in config files)
- **Format**: `http://host:port` or `https://host:port`
- **Usage**: Referenced in configuration files as `${QDRANT_URL}`
- **Examples**:

  ```bash
  # Local QDrant instance
  export QDRANT_URL="http://localhost:6333"
  
  # QDrant Cloud
  export QDRANT_URL="https://your-cluster.qdrant.io"
  ```

#### QDRANT_API_KEY

- **Description**: API key for QDrant Cloud or secured instances
- **Required**: Only for QDrant Cloud or secured instances
- **Format**: String
- **Usage**: Referenced in configuration files as `${QDRANT_API_KEY}`
- **Examples**:

  ```bash
  # QDrant Cloud API key
  export QDRANT_API_KEY="your-qdrant-cloud-api-key"
  ```

#### QDRANT_COLLECTION_NAME

- **Description**: Name of the QDrant collection to use
- **Required**: Yes (when used in config files)
- **Format**: String (alphanumeric, underscores, hyphens)
- **Usage**: Referenced in configuration files as `${QDRANT_COLLECTION_NAME}`
- **Examples**:

  ```bash
  # Default collection
  export QDRANT_COLLECTION_NAME="documents"
  
  # Project-specific collection
  export QDRANT_COLLECTION_NAME="my_project_docs"
  ```

### OpenAI Configuration

#### OPENAI_API_KEY

- **Description**: OpenAI API key for embeddings generation
- **Required**: Yes (when using OpenAI models)
- **Format**: String starting with "sk-"
- **Usage**: Referenced in configuration files as `${OPENAI_API_KEY}`
- **Examples**:

  ```bash
  # OpenAI API key
  export OPENAI_API_KEY="sk-your-openai-api-key"
  ```

### State Management

#### STATE_DB_PATH

- **Description**: Path to SQLite database file for state management
- **Required**: No (defaults to ":memory:" in workspace mode)
- **Format**: File path or ":memory:"
- **Usage**: Referenced in configuration files as `${STATE_DB_PATH}`
- **Examples**:

  ```bash
  # File-based database
  export STATE_DB_PATH="/path/to/state.db"
  
  # In-memory database (default)
  export STATE_DB_PATH=":memory:"
  ```

## 📊 Data Source Configuration

### Git Repository Settings

#### REPO_TOKEN / DOCS_REPO_TOKEN / CODE_REPO_TOKEN

- **Description**: Personal access tokens for Git authentication
- **Required**: Only for private repositories
- **Format**: String (GitHub: ghp_*, GitLab: glpat-*)
- **Usage**: Referenced in configuration files as `${REPO_TOKEN}`, `${DOCS_REPO_TOKEN}`, or `${CODE_REPO_TOKEN}`
- **Examples**:

  ```bash
  # GitHub personal access token
  export REPO_TOKEN="ghp_your-github-token"
  export DOCS_REPO_TOKEN="ghp_your-docs-token"
  export CODE_REPO_TOKEN="ghp_your-code-token"
  ```

#### REPO_URL / CODE_REPO_URL

- **Description**: Git repository URLs
- **Required**: When using git sources
- **Format**: Git URL
- **Usage**: Referenced in configuration files as `${REPO_URL}` or `${CODE_REPO_URL}`
- **Examples**:

  ```bash
  # Repository URLs
  export REPO_URL="https://github.com/org/repo.git"
  export CODE_REPO_URL="https://github.com/org/code-repo.git"
  ```

### Confluence Configuration

#### CONFLUENCE_URL / CONFLUENCE_BASE_URL

- **Description**: Base URL of your Confluence instance
- **Required**: Only when using Confluence
- **Format**: URL
- **Usage**: Referenced in configuration files as `${CONFLUENCE_URL}` or `${CONFLUENCE_BASE_URL}`
- **Examples**:

  ```bash
  # Atlassian Cloud
  export CONFLUENCE_URL="https://company.atlassian.net"
  export CONFLUENCE_BASE_URL="https://company.atlassian.net"
  ```

#### CONFLUENCE_TOKEN

- **Description**: Confluence API token
- **Required**: Only when using Confluence
- **Format**: String
- **Usage**: Referenced in configuration files as `${CONFLUENCE_TOKEN}`
- **Examples**:

  ```bash
  # Confluence API token
  export CONFLUENCE_TOKEN="your-confluence-api-token"
  ```

#### CONFLUENCE_EMAIL

- **Description**: Confluence user email
- **Required**: Only when using Confluence Cloud
- **Format**: Email address
- **Usage**: Referenced in configuration files as `${CONFLUENCE_EMAIL}`
- **Examples**:

  ```bash
  # Email address
  export CONFLUENCE_EMAIL="user@company.com"
  ```

#### CONFLUENCE_SPACE_KEY

- **Description**: Confluence space key to process
- **Required**: When using Confluence sources
- **Format**: String (space key)
- **Usage**: Referenced in configuration files as `${CONFLUENCE_SPACE_KEY}`
- **Examples**:

  ```bash
  # Space key
  export CONFLUENCE_SPACE_KEY="DOCS"
  ```

#### CONFLUENCE_PAT

- **Description**: Confluence Personal Access Token (for Data Center/Server)
- **Required**: Alternative to token/email for Data Center
- **Format**: String
- **Usage**: Referenced in configuration files as `${CONFLUENCE_PAT}`
- **Examples**:

  ```bash
  # Personal Access Token
  export CONFLUENCE_PAT="your-confluence-personal-access-token"
  ```

### JIRA Configuration

#### JIRA_URL / JIRA_BASE_URL

- **Description**: Base URL of your JIRA instance
- **Required**: Only when using JIRA
- **Format**: URL
- **Usage**: Referenced in configuration files as `${JIRA_URL}` or `${JIRA_BASE_URL}`
- **Examples**:

  ```bash
  # Atlassian Cloud
  export JIRA_URL="https://company.atlassian.net"
  export JIRA_BASE_URL="https://company.atlassian.net"
  ```

#### JIRA_TOKEN

- **Description**: JIRA API token
- **Required**: Only when using JIRA
- **Format**: String
- **Usage**: Referenced in configuration files as `${JIRA_TOKEN}`
- **Examples**:

  ```bash
  # JIRA API token
  export JIRA_TOKEN="your-jira-api-token"
  ```

#### JIRA_EMAIL

- **Description**: JIRA user email
- **Required**: Only when using JIRA Cloud
- **Format**: Email address
- **Usage**: Referenced in configuration files as `${JIRA_EMAIL}`
- **Examples**:

  ```bash
  # Email address
  export JIRA_EMAIL="user@company.com"
  ```

#### JIRA_PROJECT_KEY

- **Description**: JIRA project key to process
- **Required**: When using JIRA sources
- **Format**: String (project key)
- **Usage**: Referenced in configuration files as `${JIRA_PROJECT_KEY}`
- **Examples**:

  ```bash
  # Project key
  export JIRA_PROJECT_KEY="PROJ"
  ```

#### JIRA_PAT

- **Description**: JIRA Personal Access Token (for Data Center/Server)
- **Required**: Alternative to token/email for Data Center
- **Format**: String
- **Usage**: Referenced in configuration files as `${JIRA_PAT}`
- **Examples**:

  ```bash
  # Personal Access Token
  export JIRA_PAT="your-jira-personal-access-token"
  ```

## 🤖 MCP Server Configuration

The MCP server uses these environment variables directly (not through configuration files):

### Core MCP Settings

#### MCP_LOG_LEVEL

- **Description**: Log level for MCP server
- **Required**: No (defaults to "INFO")
- **Format**: String (DEBUG, INFO, WARNING, ERROR)
- **Usage**: Used directly by MCP server
- **Examples**:

  ```bash
  # Default logging
  export MCP_LOG_LEVEL="INFO"
  
  # Debug logging
  export MCP_LOG_LEVEL="DEBUG"
  ```

#### MCP_LOG_FILE

- **Description**: Path to MCP server log file
- **Required**: No (defaults to console only)
- **Format**: File path
- **Usage**: Used directly by MCP server
- **Examples**:

  ```bash
  # Log to file
  export MCP_LOG_FILE="/var/log/mcp-server.log"
  ```

#### MCP_DISABLE_CONSOLE_LOGGING

- **Description**: Disable console logging for MCP server
- **Required**: No (defaults to false)
- **Format**: Boolean string ("true"/"false")
- **Usage**: Used directly by MCP server
- **Examples**:

  ```bash
  # Disable console logging
  export MCP_DISABLE_CONSOLE_LOGGING="true"
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

# Optional: State Management
# STATE_DB_PATH=/path/to/state.db
```

### Development .env Template

```bash
# .env.development - Development environment

# QDrant Database (local)
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=dev_documents

# OpenAI API (development key)
OPENAI_API_KEY=sk-your-dev-openai-api-key

# State Management (in-memory for development)
STATE_DB_PATH=:memory:

# Git Repository (if using)
REPO_TOKEN=ghp_your-github-token
REPO_URL=https://github.com/org/repo.git

# MCP Server (development settings)
MCP_LOG_LEVEL=DEBUG
MCP_LOG_FILE=/tmp/mcp-dev.log
```

### Production .env Template

```bash
# .env.production - Production environment

# QDrant Database (production)
QDRANT_URL=https://your-qdrant-cluster.qdrant.io
QDRANT_API_KEY=your-production-qdrant-api-key
QDRANT_COLLECTION_NAME=production_documents

# OpenAI API (production key)
OPENAI_API_KEY=sk-your-prod-openai-api-key

# State Management (persistent database)
STATE_DB_PATH=/var/lib/qdrant-loader/state.db

# Data Sources (production credentials)
CONFLUENCE_URL=https://company.atlassian.net
CONFLUENCE_TOKEN=your-confluence-api-token
CONFLUENCE_EMAIL=service-account@company.com
CONFLUENCE_SPACE_KEY=DOCS

JIRA_URL=https://company.atlassian.net
JIRA_TOKEN=your-jira-api-token
JIRA_EMAIL=service-account@company.com
JIRA_PROJECT_KEY=PROJ

REPO_TOKEN=ghp_your-production-github-token
REPO_URL=https://github.com/company/docs.git

# MCP Server (production settings)
MCP_LOG_LEVEL=INFO
MCP_LOG_FILE=/var/log/qdrant-loader/mcp.log
MCP_DISABLE_CONSOLE_LOGGING=true
```

## 🔧 Environment Management

### Loading Environment Variables

#### Using .env Files

```bash
# Load from .env file
set -a  # automatically export all variables
source .env
set +a  # stop automatically exporting

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
env $(cat .env.production | xargs) qdrant-loader --workspace . config
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
qdrant-loader --workspace . config
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
  "CONFLUENCE_URL"
  "JIRA_URL"
  "REPO_TOKEN"
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

## 📋 Environment Variables Checklist

- [ ] **Core variables** set (QDRANT_URL, OPENAI_API_KEY, QDRANT_COLLECTION_NAME)
- [ ] **Data source credentials** configured for your sources
- [ ] **MCP server settings** configured if using MCP server
- [ ] **Environment file** created and secured (chmod 600)
- [ ] **Variables validated** with test commands
- [ ] **Configuration tested** with `qdrant-loader --workspace . config`

---

**Environment configuration complete!** 🎉

Your QDrant Loader is now configured via environment variables. This provides a secure way to manage credentials while keeping sensitive information out of configuration files.
