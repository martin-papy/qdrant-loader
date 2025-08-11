# Security Considerations
This guide covers security best practices and considerations for deploying QDrant Loader in production environments. Security is critical when handling sensitive documents and API keys.
## 🎯 Overview
QDrant Loader handles sensitive data including API keys, documents, and search queries. While the application doesn't include built-in advanced security features, proper configuration and deployment practices can protect your data, credentials, and infrastructure.
### Security Areas
```
🔐 Credential Management - API keys and tokens
🌐 Network Security     - HTTPS connections
📊 Data Protection     - Secure data handling
🔍 Monitoring          - Basic logging capabilities
🚨 Best Practices      - Configuration and usage security
```
## 🔐 Credential Management
### Environment Variables (Primary Method)
QDrant Loader uses environment variables for all credential management. Environment variables are used both directly by the MCP server and for substitution in YAML configuration files using `${VARIABLE_NAME}` syntax.
```bash
# .env - Secure environment file (chmod 600)
# Never commit this file to version control
# OpenAI API Key (Required)
OPENAI_API_KEY=sk-your-openai-api-key
# QDrant Configuration
QDRANT_API_KEY=your-qdrant-api-key
# Git Credentials (if using Git repositories)
REPO_TOKEN=your-git-personal-access-token
# Confluence Configuration (if using Confluence)
CONFLUENCE_TOKEN=your-confluence-api-token
CONFLUENCE_EMAIL=your-confluence-email@company.com
# For Confluence Data Center/Server (alternative to token/email)
CONFLUENCE_PAT=your-confluence-personal-access-token
# Jira Configuration (if using Jira)
JIRA_TOKEN=your-jira-api-token
JIRA_EMAIL=your-jira-email@company.com
# For Jira Data Center/Server (alternative to token/email)
JIRA_PAT=your-jira-personal-access-token
# MCP Server Configuration (Optional)
MCP_LOG_LEVEL=INFO
MCP_LOG_FILE=/path/to/logs/mcp.log
MCP_DISABLE_CONSOLE_LOGGING=true
```
### API Key Security Best Practices
```bash
#!/bin/bash
# validate-keys.sh - Basic API key validation
# Validate OpenAI API key format
validate_openai_key() {
    if [[ ! $OPENAI_API_KEY =~ ^sk-[a-zA-Z0-9-_]{20,}$ ]]; then
        echo "❌ Invalid OpenAI API key format"
        exit 1
    fi
    echo "✅ OpenAI API key format valid"
}
# Test API connectivity
test_connections() {
    echo "Testing API connectivity..."
    # Test OpenAI API
    curl -s -H "Authorization: Bearer $OPENAI_API_KEY" \
         https://api.openai.com/v1/models > /dev/null
    if [ $? -eq 0 ]; then
        echo "✅ OpenAI API key working"
    else
        echo "❌ OpenAI API key failed"
        exit 1
    fi
}
# Validate configuration using QDrant Loader CLI
validate_config() {
    echo "Validating QDrant Loader configuration..."
    # Validate workspace configuration
    \1 project \3 --workspace \2
    if [ $? -eq 0 ]; then
        echo "✅ Configuration valid"
    else
        echo "❌ Configuration validation failed"
        exit 1
    fi
}
# Run validations
validate_openai_key
test_connections
validate_config
```
## 🌐 Network Security
### TLS/SSL Configuration
QDrant Loader automatically uses HTTPS for all external API connections:
- **OpenAI API**: Always uses HTTPS
- **QDrant Cloud**: Uses HTTPS by default
- **Confluence/Jira**: Uses HTTPS for cloud instances (configured in config.yaml)
- **Git repositories**: Uses HTTPS for cloning
URLs are configured in the YAML configuration file, not environment variables:
```yaml
# config.yaml - Use HTTPS URLs for security
global_config:
  qdrant:
    url: "https://your-qdrant-cluster.qdrant.io"  # Use HTTPS
projects:
  my-project:
    sources:
      confluence:
        wiki:
          base_url: "https://company.atlassian.net/wiki"  # Use HTTPS
      jira:
        project:
          base_url: "https://company.atlassian.net"       # Use HTTPS
```
### Required Network Access
Ensure outbound access to required services:
```bash
# Required outbound connections
# OpenAI API
api.openai.com:443
# QDrant Cloud (if using)
*.qdrant.io:443
# Atlassian Cloud (if using)
*.atlassian.net:443
# GitHub (if using)
github.com:443
api.github.com:443
# GitLab (if using)
gitlab.com:443
```
## 🛡️ Access Control
### MCP Server Security
The MCP server uses environment variables for configuration. For Cursor integration:
```json
{
  "mcpServers": {
    "qdrant-loader": {
      "command": "/path/to/venv/bin/mcp-qdrant-loader",
      "env": {
        "QDRANT_URL": "https://your-qdrant-cluster.qdrant.io",
        "QDRANT_API_KEY": "your-secure-api-key",
        "OPENAI_API_KEY": "sk-your-secure-openai-key",
        "QDRANT_COLLECTION_NAME": "documents",
        "MCP_LOG_LEVEL": "INFO",
        "MCP_LOG_FILE": "/secure/path/logs/mcp.log",
        "MCP_DISABLE_CONSOLE_LOGGING": "true"
      }
    }
  }
}
```
**Critical MCP Security Notes:**
- **Always set `MCP_DISABLE_CONSOLE_LOGGING=true`** for Cursor integration to prevent JSON-RPC interference
- **Use full path to the MCP server binary** for security and reliability
- **Use `MCP_LOG_FILE`** for debugging when console logging is disabled
### Rate Limiting
QDrant Loader implements rate limiting for external API calls:
- **OpenAI API**: Built-in rate limiting (500ms minimum interval between requests) with exponential backoff retry logic
- **Confluence API**: No built-in rate limiting (uses standard HTTP requests)
- **Jira API**: Configurable rate limiting (default: 60 requests per minute) with async rate limit control
- **Git operations**: No specific rate limiting
**Jira Rate Limiting Configuration:**
```yaml
jira:
  my-project:
    requests_per_minute: 60  # Configurable rate limit
```
The rate limiting is implemented in the embedding service and Jira connector. OpenAI rate limiting is not user-configurable, while Jira rate limiting can be adjusted per project.
## 📊 Data Protection
### Data Handling
QDrant Loader processes documents with the following security considerations:
1. **Temporary Storage**: Documents are processed in memory when possible
2. **State Database**: Uses SQLite for tracking processing state
3. **Embeddings**: Sent to OpenAI API for processing
4. **Vector Storage**: Stored in QDrant database
### Data Flow Security
```
Local Files → Memory → OpenAI API → QDrant Database
     ↓              ↓         ↓           ↓
  File System   Temporary   External    Vector DB
  Permissions   Processing   Service     Storage
```
### File Permissions
```bash
# Secure file permissions for QDrant Loader files
chmod 600 .env                    # Environment variables
chmod 600 config.yaml             # Configuration file
chmod 700 ~/.qdrant-loader/       # Application directory (if used)
chmod 600 state.db                # State database
# For workspace mode (recommended)
chmod 700 /path/to/workspace       # Workspace directory
chmod 600 /path/to/workspace/.env  # Workspace environment file
chmod 600 /path/to/workspace/config.yaml  # Workspace configuration
```
### Workspace Mode Security
QDrant Loader supports **workspace mode** (recommended) which provides better organization and security:
**Benefits:**
- **Isolated configuration** per workspace/project
- **Automatic path management** for databases and logs
- **Built-in security** for workspace directory structure
- **Version control friendly** (exclude .env, include config.yaml)
**Workspace Security Setup:**
```bash
# Create secure workspace
mkdir /secure/path/my-workspace
cd /secure/path/my-workspace
chmod 700 .
# Create configuration files
touch .env config.yaml
chmod 600 .env config.yaml
# Run in workspace mode
\1 project \3 --workspace \2
\1 ingest --workspace .
```
**Important:** In workspace mode, `state_management.database_path` in config.yaml is ignored for security - the state database is automatically placed in the workspace directory.
## 🔍 Monitoring and Logging
### Application Logging
QDrant Loader provides basic logging capabilities:
```bash
# MCP Server logging
export MCP_LOG_LEVEL=INFO
export MCP_LOG_FILE=/path/to/logs/mcp.log
export MCP_DISABLE_CONSOLE_LOGGING=true  # Required for Cursor integration
```
### Monitoring API Usage
Monitor API usage through provider dashboards:
- **OpenAI**: Monitor usage in OpenAI dashboard
- **QDrant Cloud**: Monitor usage in QDrant console
- **Confluence/Jira**: Monitor API usage in Atlassian admin
## 🚨 Security Best Practices
### Configuration Security
#### Production Environment
```bash
# Production security checklist
# 1. Use dedicated service accounts
CONFLUENCE_EMAIL=qdrant-loader-service@company.com
JIRA_EMAIL=qdrant-loader-service@company.com
# 2. Use minimal permissions
# - Confluence: Read-only access to required spaces
# - Jira: Read-only access to required projects
# - Git: Read-only repository access
# 3. Secure file permissions
chmod 600 .env
chmod 600 config.yaml
# 4. Use HTTPS URLs in config.yaml
# global_config:
#   qdrant:
#     url: "https://your-qdrant-cluster.qdrant.io"
```
#### Development Environment
```bash
# Development security considerations
# 1. Use separate API keys for development
OPENAI_API_KEY=sk-dev-your-development-key
# 2. Use test data collections in config.yaml
# global_config:
#   qdrant:
#     url: "http://localhost:6333"
#     collection_name: "dev_documents"
# 3. Enable debug logging for MCP server
MCP_LOG_LEVEL=DEBUG
```
## 🔧 Security Configuration Examples
### Minimal Security Configuration
```bash
# .env - Minimal secure configuration
OPENAI_API_KEY=sk-your-openai-api-key
```
```yaml
# config.yaml - Minimal secure configuration
global_config:
  qdrant:
    url: "http://localhost:6333"
    collection_name: "documents"
  embedding:
    endpoint: "https://api.openai.com/v1"
    api_key: "${OPENAI_API_KEY}"
    model: "text-embedding-3-small"
projects:
  default-project:
    project_id: "default-project"
    display_name: "Default Project"
    sources: {}
```
### Production Security Configuration
```bash
# .env - Production secure configuration
OPENAI_API_KEY=sk-your-production-openai-key
QDRANT_API_KEY=your-production-qdrant-api-key
# Confluence (if used)
CONFLUENCE_EMAIL=qdrant-loader-service@company.com
CONFLUENCE_TOKEN=your-production-confluence-token
# Jira (if used)
JIRA_EMAIL=qdrant-loader-service@company.com
JIRA_TOKEN=your-production-jira-token
# Git (if used)
REPO_TOKEN=your-production-git-token
# MCP Server (if used)
MCP_LOG_LEVEL=INFO
MCP_LOG_FILE=/secure/path/logs/mcp.log
MCP_DISABLE_CONSOLE_LOGGING=true
```
```yaml
# config.yaml - Production secure configuration
global_config:
  qdrant:
    url: "https://your-qdrant-cluster.qdrant.io"
    api_key: "${QDRANT_API_KEY}"
    collection_name: "production_documents"
  embedding:
    endpoint: "https://api.openai.com/v1"
    api_key: "${OPENAI_API_KEY}"
    model: "text-embedding-3-small"
  state_management:
    database_path: "/secure/path/state.db"
projects:
  knowledge-base:
    project_id: "knowledge-base"
    display_name: "Company Knowledge Base"
    sources:
      confluence:
        company-wiki:
          base_url: "https://company.atlassian.net/wiki"
          deployment_type: "cloud"
          space_key: "DOCS"
          email: "${CONFLUENCE_EMAIL}"
          token: "${CONFLUENCE_TOKEN}"
      jira:
        support-project:
          base_url: "https://company.atlassian.net"
          deployment_type: "cloud"
          project_key: "SUPPORT"
          email: "${JIRA_EMAIL}"
          token: "${JIRA_TOKEN}"
      git:
        docs-repo:
          base_url: "https://github.com/company/docs.git"
          branch: "main"
          token: "${REPO_TOKEN}"
          file_types: ["*.md", "*.rst"]
```
## 🔗 Related Documentation
- **[Environment Variables Reference](./environment-variables.md)** - Complete environment variable list
- **[Configuration File Reference](./config-file-reference.md)** - Configuration file structure
- **[MCP Server Setup](../detailed-guides/mcp-server/setup-and-integration.md)** - MCP server security
## 📋 Security Checklist
### Pre-Deployment Security
- [ ] **API keys** stored in environment variables only
- [ ] **File permissions** set correctly (600 for .env and config.yaml, 700 for workspace)
- [ ] **HTTPS URLs** used for all external services in config.yaml
- [ ] **Service accounts** created with minimal permissions
- [ ] **Secrets** excluded from version control (.env in .gitignore)
- [ ] **API key formats** validated with validation scripts
- [ ] **Configuration** validated using `qdrant-loader project validate`
- [ ] **Workspace mode** used for production deployments
- [ ] **MCP server logging** configured properly for AI IDE integration
### Runtime Security
- [ ] **Environment variables** properly configured and loaded
- [ ] **Log files** secured with appropriate permissions (600)
- [ ] **API usage** monitored through provider dashboards
- [ ] **State database** backed up regularly (auto-managed in workspace mode)
- [ ] **Application logs** reviewed for errors and security issues
- [ ] **MCP server** functioning properly with secure logging configuration
- [ ] **Workspace directory** permissions maintained (700)
### Operational Security
- [ ] **API usage** monitored for unexpected spikes or rate limit violations
- [ ] **Access reviews** conducted for service accounts and API tokens
- [ ] **Security updates** applied to QDrant Loader and Python dependencies
- [ ] **Configuration drift** monitored using `qdrant-loader project validate`
- [ ] **Documentation** kept current with actual implementation
- [ ] **Backup and recovery** procedures tested for workspace data
---
**Security configuration complete!** 🔒
Your QDrant Loader deployment follows security best practices within the application's current capabilities. Regular security reviews and updates ensure ongoing protection of your data and credentials.
