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

QDrant Loader uses environment variables for all credential management. This is the **only supported method** for storing API keys and tokens.

```bash
# .env - Secure environment file (chmod 600)
# Never commit this file to version control

# OpenAI API Key (Required)
OPENAI_API_KEY=sk-your-openai-api-key

# QDrant Configuration
QDRANT_URL=https://your-qdrant-cluster.qdrant.io
QDRANT_API_KEY=your-qdrant-api-key
QDRANT_COLLECTION_NAME=documents

# Atlassian Credentials (if using Confluence/Jira)
CONFLUENCE_URL=https://company.atlassian.net
CONFLUENCE_EMAIL=service-account@company.com
CONFLUENCE_TOKEN=your-confluence-api-token

JIRA_URL=https://company.atlassian.net
JIRA_EMAIL=service-account@company.com
JIRA_TOKEN=your-jira-api-token

# Git Credentials (if using Git repositories)
REPO_TOKEN=your-git-personal-access-token
REPO_URL=https://github.com/your-org/your-repo

# State Database Path
STATE_DB_PATH=./state.db

# MCP Server Logging (Optional)
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
    if [[ ! $OPENAI_API_KEY =~ ^sk-[a-zA-Z0-9-_]{48,}$ ]]; then
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

# Run validations
validate_openai_key
test_connections
```

## 🌐 Network Security

### TLS/SSL Configuration

QDrant Loader automatically uses HTTPS for all external API connections:

- **OpenAI API**: Always uses HTTPS
- **QDrant Cloud**: Uses HTTPS by default
- **Confluence/Jira**: Uses HTTPS for cloud instances
- **Git repositories**: Uses HTTPS for cloning

```bash
# Environment variables for secure connections
# These are handled automatically by the application
export QDRANT_URL="https://your-qdrant-cluster.qdrant.io"  # Use HTTPS
export CONFLUENCE_URL="https://company.atlassian.net"      # Use HTTPS
export JIRA_URL="https://company.atlassian.net"           # Use HTTPS
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

The MCP server has basic security considerations:

```json
{
  "mcpServers": {
    "qdrant-loader": {
      "command": "mcp-qdrant-loader",
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

### Rate Limiting

QDrant Loader implements basic rate limiting for API calls:

- **OpenAI API**: Built-in rate limiting with exponential backoff
- **Confluence/Jira**: Basic rate limiting to respect API limits
- **Git operations**: No specific rate limiting

The rate limiting is implemented in the embedding service and connectors but is not user-configurable.

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
chmod 600 qdrant-loader.yaml     # Configuration file
chmod 700 ~/.qdrant-loader/      # Application directory
chmod 600 state.db               # State database
```

## 🔍 Monitoring and Logging

### Application Logging

QDrant Loader provides basic logging capabilities:

```bash
# Set logging level
export LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR

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

# 4. Use HTTPS URLs
QDRANT_URL=https://your-qdrant-cluster.qdrant.io
CONFLUENCE_URL=https://company.atlassian.net
JIRA_URL=https://company.atlassian.net
```

#### Development Environment

```bash
# Development security considerations
# 1. Use separate API keys for development
OPENAI_API_KEY=sk-dev-your-development-key

# 2. Use local QDrant instance
QDRANT_URL=http://localhost:6333

# 3. Use test data collections
QDRANT_COLLECTION_NAME=dev_documents

# 4. Enable debug logging
LOG_LEVEL=DEBUG
MCP_LOG_LEVEL=DEBUG
```

## 🔧 Security Configuration Examples

### Minimal Security Configuration

```bash
# .env - Minimal secure configuration
OPENAI_API_KEY=sk-your-openai-api-key
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=documents
STATE_DB_PATH=./state.db
LOG_LEVEL=INFO
```

### Production Security Configuration

```bash
# .env - Production secure configuration
OPENAI_API_KEY=sk-your-production-openai-key
QDRANT_URL=https://your-qdrant-cluster.qdrant.io
QDRANT_API_KEY=your-production-qdrant-api-key
QDRANT_COLLECTION_NAME=production_documents

# Atlassian (if used)
CONFLUENCE_URL=https://company.atlassian.net
CONFLUENCE_EMAIL=qdrant-loader-service@company.com
CONFLUENCE_TOKEN=your-production-confluence-token

JIRA_URL=https://company.atlassian.net
JIRA_EMAIL=qdrant-loader-service@company.com
JIRA_TOKEN=your-production-jira-token

# Git (if used)
REPO_TOKEN=your-production-git-token
REPO_URL=https://github.com/company/docs

# State and logging
STATE_DB_PATH=/secure/path/state.db
LOG_LEVEL=INFO

# MCP Server (if used)
MCP_LOG_LEVEL=INFO
MCP_LOG_FILE=/secure/path/logs/mcp.log
MCP_DISABLE_CONSOLE_LOGGING=true
```

## 🔗 Related Documentation

- **[Environment Variables Reference](./environment-variables.md)** - Complete environment variable list
- **[Configuration File Reference](./config-file-reference.md)** - Configuration file structure
- **[MCP Server Setup](../detailed-guides/mcp-server/setup-and-integration.md)** - MCP server security

## 📋 Security Checklist

### Pre-Deployment Security

- [ ] **API keys** stored in environment variables only
- [ ] **File permissions** set correctly (600 for .env)
- [ ] **HTTPS URLs** used for all external services
- [ ] **Service accounts** created with minimal permissions
- [ ] **Secrets** excluded from version control (.env in .gitignore)
- [ ] **API key formats** validated
- [ ] **Connectivity** tested with validation scripts

### Runtime Security

- [ ] **Environment variables** properly configured
- [ ] **Log files** secured with appropriate permissions
- [ ] **API usage** monitored through provider dashboards
- [ ] **State database** backed up regularly
- [ ] **Application logs** reviewed for errors

### Operational Security

- [ ] **API usage** monitored for unexpected spikes
- [ ] **Access reviews** conducted for service accounts
- [ ] **Security updates** applied to dependencies
- [ ] **Documentation** kept current

---

**Security configuration complete!** 🔒

Your QDrant Loader deployment follows security best practices within the application's current capabilities. Regular security reviews and updates ensure ongoing protection of your data and credentials.
