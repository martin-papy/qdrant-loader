# Environment Variables Reference
This reference covers the environment variables actually used by QDrant Loader and its MCP server. Environment variables provide a secure way to configure credentials and basic settings.
## 🎯 Overview
QDrant Loader uses environment variables in two ways:
1. **Direct usage** - Variables read directly by the application code
2. **Config substitution** - Variables substituted into YAML configuration files using `${VARIABLE_NAME}` syntax
### Configuration Priority
```text
1. Command-line arguments (highest priority)
2. Environment variables ← This guide
3. Configuration file
4. Default values (lowest priority)
```
## 🔧 Environment Variables Used Directly by Code
These environment variables are read directly by the application code:
### QDrant Database Connection (MCP Server)
#### QDRANT_URL
- **Description**: URL of your QDrant database instance
- **Used by**: MCP server configuration
- **Required**: No (defaults to "http://localhost:6333")
- **Format**: `http://host:port` or `https://host:port`
- **Examples**: ```bash export QDRANT_URL="http://localhost:6333" export QDRANT_URL="https://your-cluster.qdrant.io" ```
#### QDRANT_API_KEY
- **Description**: API key for QDrant Cloud or secured instances
- **Used by**: MCP server configuration
- **Required**: No (only for secured QDrant instances)
- **Format**: String
- **Examples**: ```bash export QDRANT_API_KEY="your-qdrant-cloud-api-key" ```
#### QDRANT_COLLECTION_NAME
- **Description**: Name of the QDrant collection to use
- **Used by**: MCP server configuration
- **Required**: No (defaults to "documents")
- **Format**: String (alphanumeric, underscores, hyphens)
- **Examples**: ```bash export QDRANT_COLLECTION_NAME="documents" export QDRANT_COLLECTION_NAME="my_project_docs" ```
### OpenAI Configuration
#### OPENAI_API_KEY
- **Description**: OpenAI API key for embeddings and file conversion
- **Used by**: MCP server configuration, file conversion fallback
- **Required**: Yes (when using OpenAI models)
- **Format**: String starting with "sk-"
- **Examples**: ```bash export OPENAI_API_KEY="sk-your-openai-api-key" ```
### Data Source Authentication
#### CONFLUENCE_TOKEN
- **Description**: Confluence API token for authentication
- **Used by**: Confluence connector when not specified in config
- **Required**: No (fallback only)
- **Format**: String
- **Examples**: ```bash export CONFLUENCE_TOKEN="your-confluence-api-token" ```
#### CONFLUENCE_EMAIL
- **Description**: Confluence user email for Cloud authentication
- **Used by**: Confluence connector when not specified in config
- **Required**: No (fallback only)
- **Format**: Email address
- **Examples**: ```bash export CONFLUENCE_EMAIL="user@company.com" ```
#### JIRA_TOKEN
- **Description**: JIRA API token for authentication
- **Used by**: JIRA connector when not specified in config
- **Required**: No (fallback only)
- **Format**: String
- **Examples**: ```bash export JIRA_TOKEN="your-jira-api-token" ```
#### JIRA_EMAIL
- **Description**: JIRA user email for Cloud authentication
- **Used by**: JIRA connector when not specified in config
- **Required**: No (fallback only)
- **Format**: Email address
- **Examples**: ```bash export JIRA_EMAIL="user@company.com" ```
### MCP Server Logging
#### MCP_LOG_LEVEL
- **Description**: Log level for MCP server
- **Used by**: MCP server logging configuration
- **Required**: No (defaults to "INFO")
- **Format**: String (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **Examples**: ```bash export MCP_LOG_LEVEL="INFO" export MCP_LOG_LEVEL="DEBUG" ```
#### MCP_LOG_FILE
- **Description**: Path to MCP server log file
- **Used by**: MCP server logging configuration
- **Required**: No (console only if not set)
- **Format**: File path
- **Examples**: ```bash export MCP_LOG_FILE="/var/log/mcp-server.log" export MCP_LOG_FILE="./logs/mcp.log" ```
#### MCP_DISABLE_CONSOLE_LOGGING
- **Description**: Disable console logging for MCP server
- **Used by**: MCP server logging configuration
- **Required**: No (defaults to false)
- **Format**: Boolean string ("true"/"false")
- **Examples**: ```bash export MCP_DISABLE_CONSOLE_LOGGING="true" ```
### Development/Release Variables
#### GITHUB_TOKEN
- **Description**: GitHub token for release automation
- **Used by**: Release script
- **Required**: No (only for releases)
- **Format**: String (ghp_* or github_pat_*)
- **Examples**: ```bash export GITHUB_TOKEN="ghp_your-github-token" ```
## 📝 Environment Variables for Config File Substitution
These variables are substituted into YAML configuration files using `${VARIABLE_NAME}` syntax. They are not read directly by the code but can be used in config files:
### Common Substitution Variables
Any environment variable can be used for substitution in config files. Common examples include:
- `STATE_DB_PATH` - Database path for state management
- `REPO_TOKEN` - Git repository tokens
- `CONFLUENCE_URL` - Confluence base URLs
- `CONFLUENCE_SPACE_KEY` - Confluence space keys
- `CONFLUENCE_PAT` - Confluence Personal Access Tokens
- `JIRA_URL` - JIRA base URLs
- `JIRA_PROJECT_KEY` - JIRA project keys
- `JIRA_PAT` - JIRA Personal Access Tokens
**Example config usage:**
```yaml
global_config: state_management: database_path: "${STATE_DB_PATH}"
sources: confluence: my-wiki: base_url: "${CONFLUENCE_URL}" space_key: "${CONFLUENCE_SPACE_KEY}" token: "${CONFLUENCE_TOKEN}"
```
## 📋 Environment File Templates
### Basic .env Template
```bash
# .env - Basic configuration for MCP server
# Required for MCP server
OPENAI_API_KEY=sk-your-openai-api-key
# QDrant configuration (defaults shown)
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=documents
# QDRANT_API_KEY=your-qdrant-cloud-api-key
# MCP Server logging (optional)
MCP_LOG_LEVEL=INFO
# MCP_LOG_FILE=./logs/mcp.log
# MCP_DISABLE_CONSOLE_LOGGING=true
```
### Development .env Template
```bash
# .env.development - Development environment
# Core requirements
OPENAI_API_KEY=sk-your-dev-openai-api-key
# QDrant (local development)
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=dev_documents
# MCP Server (development settings)
MCP_LOG_LEVEL=DEBUG
MCP_LOG_FILE=./logs/mcp-dev.log
# Config file substitution variables (examples)
STATE_DB_PATH=:memory:
REPO_TOKEN=ghp_your-github-token
CONFLUENCE_URL=https://company.atlassian.net
CONFLUENCE_TOKEN=your-confluence-token
CONFLUENCE_EMAIL=dev@company.com
JIRA_URL=https://company.atlassian.net
JIRA_TOKEN=your-jira-token
JIRA_EMAIL=dev@company.com
```
### Production .env Template
```bash
# .env.production - Production environment
# Core requirements
OPENAI_API_KEY=sk-your-prod-openai-api-key
# QDrant (production)
QDRANT_URL=https://your-qdrant-cluster.qdrant.io
QDRANT_API_KEY=your-production-qdrant-api-key
QDRANT_COLLECTION_NAME=production_documents
# MCP Server (production settings)
MCP_LOG_LEVEL=INFO
MCP_LOG_FILE=/var/log/qdrant-loader/mcp.log
MCP_DISABLE_CONSOLE_LOGGING=true
# Config file substitution variables
STATE_DB_PATH=/var/lib/qdrant-loader/state.db
REPO_TOKEN=ghp_your-production-github-token
CONFLUENCE_URL=https://company.atlassian.net
CONFLUENCE_TOKEN=your-confluence-api-token
CONFLUENCE_EMAIL=service-account@company.com
CONFLUENCE_SPACE_KEY=DOCS
JIRA_URL=https://company.atlassian.net
JIRA_TOKEN=your-jira-api-token
JIRA_EMAIL=service-account@company.com
JIRA_PROJECT_KEY=PROJ
# Release automation (if needed)
GITHUB_TOKEN=ghp_your-production-github-token
```
## 🔧 Environment Management
### Loading Environment Variables
#### Using .env Files
```bash
# Load from .env file
set -a # automatically export all variables
source .env
set +a # stop automatically exporting
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
env $(cat .env.production | xargs)qdrant-loader config --workspace .
```
### Validation and Testing
#### Check Required Variables for MCP Server
```bash
# Check if MCP server variables are set
if [ -z "$OPENAI_API_KEY" ]; then echo "Error: OPENAI_API_KEY not set (required for MCP server)" exit 1
fi
echo "✅ OPENAI_API_KEY is set"
# Optional variables with defaults
echo "QDRANT_URL: ${QDRANT_URL:-http://localhost:6333 (default)}"
echo "QDRANT_COLLECTION_NAME: ${QDRANT_COLLECTION_NAME:-documents (default)}"
echo "MCP_LOG_LEVEL: ${MCP_LOG_LEVEL:-INFO (default)}"
```
#### Environment Variable Validation Script
```bash
#!/bin/bash
# check-env.sh - Validate environment variables
echo "=== Core Variables (directly used by code) ==="
# Required for MCP server
if [ -z "$OPENAI_API_KEY" ]; then echo "❌ OPENAI_API_KEY is not set (required for MCP server)" exit 1
else echo "✅ OPENAI_API_KEY is set"
fi
# Optional with defaults
echo "✅ QDRANT_URL: ${QDRANT_URL:-http://localhost:6333 (default)}"
echo "✅ QDRANT_COLLECTION_NAME: ${QDRANT_COLLECTION_NAME:-documents (default)}"
echo "✅ MCP_LOG_LEVEL: ${MCP_LOG_LEVEL:-INFO (default)}"
# Optional without defaults
optional_vars=("QDRANT_API_KEY" "CONFLUENCE_TOKEN" "CONFLUENCE_EMAIL" "JIRA_TOKEN" "JIRA_EMAIL" "MCP_LOG_FILE" "MCP_DISABLE_CONSOLE_LOGGING")
echo ""
echo "=== Optional Variables ==="
for var in "${optional_vars[@]}"; do if [ -z "${!var}" ]; then echo "⚠️ $var is not set (optional)" else echo "✅ $var is set" fi
done
echo ""
echo "Environment validation complete!"
```
## 🔗 Related Documentation
- **[Configuration File Reference](./config-file-reference.md)** - YAML configuration options and substitution
- **[Basic Configuration](../../getting-started/basic-configuration.md)** - Getting started guide
- **[MCP Server Setup](../detailed-guides/mcp-server/setup-and-integration.md)** - MCP server configuration
## 📋 Environment Variables Checklist
### For MCP Server Usage:
- [ ] **OPENAI_API_KEY** set (required)
- [ ] **QDRANT_URL** configured (optional, defaults to localhost)
- [ ] **QDRANT_COLLECTION_NAME** set (optional, defaults to "documents")
- [ ] **MCP logging variables** configured if needed
### For QDrant Loader Configuration:
- [ ] **Config file substitution variables** set as needed
- [ ] **Data source credentials** configured (Confluence, JIRA, Git)
- [ ] **Environment file** created and secured (chmod 600)
- [ ] **Variables validated** with test commands
---
**Environment configuration complete!** 🎉
Your QDrant Loader environment variables are now accurately configured. Remember that most variables are used for config file substitution rather than direct code usage.
