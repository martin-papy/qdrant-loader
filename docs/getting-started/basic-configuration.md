# Basic Configuration

This guide covers only the starter configuration pattern.

For complete options and provider-specific details, use canonical references under user configuration docs.

## 📖 Overview

QDrant Loader uses a flexible configuration system that supports:

- **Environment variables** for credentials and basic settings
- **Configuration files** for detailed project and source configuration
- **Workspace mode** for organized project management
- **Multiple environments** (development, staging, production)

## 🎯 Goals

- Define one reusable global configuration
- Add one project with one source
- Validate settings before first ingest

## 🔧 Configuration Methods

### Configuration Priority

QDrant Loader uses this priority order (highest to lowest):

```text
1. Command-line arguments (--workspace, --config, --env)
2. Environment variables (QDRANT_URL, LLM_API_KEY, etc.)
3. Configuration file (config.yaml)
4. Default values (built-in defaults)
```

### Workspace Mode vs. Traditional Mode

| Workspace Mode (Recommended)   | Traditional Mode           |
| ------------------------------ | -------------------------- |
| Organized directory structure  | Individual config files    |
| Auto-discovery of config files | Manual file specification  |
| Built-in logging and metrics   | Manual setup required      |
| Good for: All use cases        | Good for: Simple scripts   |
| 5 minutes to configure         | 10-15 minutes to configure |

## 🚀 Quick Setup (Workspace Mode)

### Step 1. Create .env

```bash
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=my_documents

LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your-openai-key
LLM_EMBEDDING_MODEL=text-embedding-3-small
LLM_CHAT_MODEL=gpt-4o-mini
```

### Step 2. Create config.yaml

```yaml
global:
  qdrant:
    url: "${QDRANT_URL}"
    collection_name: "${QDRANT_COLLECTION_NAME}"
  llm:
    provider: "${LLM_PROVIDER}"
    base_url: "${LLM_BASE_URL}"
    api_key: "${LLM_API_KEY}"
    models:
      embeddings: "${LLM_EMBEDDING_MODEL}"
      chat: "${LLM_CHAT_MODEL}"
    embeddings:
      vector_size: 1536
  chunking:
    chunk_size: 1500
    chunk_overlap: 200

projects:
  default:
    project_id: "default"
    display_name: "Default Project"
    sources:
      localfile:
        docs:
          base_url: "file://./docs"
          include_paths:
            - "**/*.md"
```

### Step 3. Validate and ingest

```bash
qdrant-loader init --workspace .
qdrant-loader ingest --workspace .
```

## 🎯 Common Configuration Scenarios

> **Note**: For full `llm` configuration (models, embeddings, vector_size), see Quick Setup → Step 2 above. The scenarios below show only the unique parts for each use case.

### Scenario 1: Personal Knowledge Base

**Use Case**: Index personal documents, notes, and bookmarks

```yaml
global:
  qdrant:
    url: "${QDRANT_URL}"
    collection_name: "personal_knowledge"

projects:
  personal:
    project_id: "personal"
    display_name: "Personal Knowledge Base"
    description: "Personal documents and notes"
    sources:
      localfile:
        documents:
          base_url: "file://~/Documents"
          include_paths:
            - "**/*.md"
            - "**/*.txt"
            - "**/*.pdf"
          file_types:
            - "*.md"
            - "*.txt"
            - "*.pdf"
          enable_file_conversion: true
      git:
        notes:
          base_url: "https://github.com/username/notes.git"
          branch: "main"
          include_paths:
            - "**/*.md"
          file_types:
            - "*.md"
          token: "${GITHUB_TOKEN}"
```

---

### Scenario 2: Team Documentation Hub

**Use Case**: Centralize team documentation from multiple sources

```yaml
global:
  qdrant:
    url: "${QDRANT_URL}"
    collection_name: "team_docs"

projects:
  team-docs:
    project_id: "team-docs"
    display_name: "Team Documentation"
    description: "Centralized team documentation"
    sources:
      git:
        main-repo:
          base_url: "${TEAM_REPO_URL}"
          branch: "main"
          include_paths:
            - "docs/**"
            - "wiki/**"
            - "README.md"
          file_types:
            - "*.md"
            - "*.rst"
          token: "${TEAM_REPO_TOKEN}"
      confluence:
        team-space:
          base_url: "${CONFLUENCE_URL}"
          space_key: "TEAM"
          deployment_type: "cloud"
          token: "${CONFLUENCE_TOKEN}"
          email: "${CONFLUENCE_EMAIL}"
      jira:
        team-project:
          base_url: "${JIRA_URL}"
          project_key: "TEAM"
          deployment_type: "cloud"
          token: "${JIRA_TOKEN}"
          email: "${JIRA_EMAIL}"
```

---

### Scenario 3: Development Team Setup

**Use Case**: Code documentation and development resources

```yaml
global:
  qdrant:
    url: "${QDRANT_URL}"
    collection_name: "dev_docs"

projects:
  frontend:
    project_id: "frontend"
    display_name: "Frontend Documentation"
    description: "React frontend application docs"
    sources:
      git:
        frontend-repo:
          base_url: "${FRONTEND_REPO_URL}"
          branch: "main"
          include_paths:
            - "src/**"
            - "docs/**"
            - "README.md"
          file_types:
            - "*.md"
            - "*.js"
            - "*.ts"
            - "*.jsx"
            - "*.tsx"
          token: "${REPO_TOKEN}"
  backend:
    project_id: "backend"
    display_name: "Backend Documentation"
    description: "API and backend documentation"
    sources:
      git:
        backend-repo:
          base_url: "${BACKEND_REPO_URL}"
          branch: "main"
          include_paths:
            - "src/**"
            - "docs/**"
            - "API.md"
          file_types:
            - "*.md"
            - "*.py"
            - "*.yaml"
            - "*.json"
          token: "${REPO_TOKEN}"
```

### Common Configuration Issues

Common issues you might encounter during setup:

- **Invalid YAML Syntax** — `yaml.scanner.ScannerError` (indentation, special characters)
- **Missing Environment Variables** — `KeyError: 'LLM_API_KEY'` or `KeyError: 'OPENAI_API_KEY'`
- **Connection Failures** — `ConnectionError: Unable to connect to QDrant`
- **Invalid Project Structure** — `Legacy configuration format detected`
- **Environment Variables Not Loaded** — Literal `${VAR_NAME}` in configuration

For detailed solutions and troubleshooting steps, see [Configuration Issues](../users/troubleshooting/common-issues.md#configuration-issues) in the full troubleshooting guide.

## 📋 Configuration Checklist

- [ ] **Environment variables** set for all credentials
- [ ] **Configuration file** created with multi-project structure
- [ ] **QDrant connection** tested successfully
- [ ] **LLM provider** configured and tested (OpenAI, Azure OpenAI, Ollama, etc.)
- [ ] **Projects** defined with appropriate sources
- [ ] **File permissions** secured (600 for .env files)
- [ ] **Workspace structure** created if using workspace mode
- [ ] **Performance settings** tuned for your dataset size
- [ ] **Source configurations** validated for each project
- [ ] **Backup strategy** for configuration files

## 🔗 What to customize next

- Add more sources (Git/Confluence/Jira): [Data Sources Guide](../users/detailed-guides/data-sources/)
- Tune chunking and global settings: [Configuration Reference](../users/configuration/config-file-reference.md)
- Configure provider-specific LLM details: [LLM Provider Guide](../users/configuration/llm-provider-guide.md)
- Full variable reference: [Environment Variables Reference](../users/configuration/environment-variables.md)
- Workspace and config loading modes: [Workspace Mode](../users/configuration/workspace-mode.md)
- Secure credentials and file permissions: [Security Considerations](../users/configuration/security-considerations.md)
- Validation and common config errors: [Troubleshooting](../users/troubleshooting/)
- Multi-environment setup patterns: [Common Workflows](../users/workflows/common-workflows.md)
- Performance tuning guidance: [Performance Issues](../users/troubleshooting/performance-issues.md)
