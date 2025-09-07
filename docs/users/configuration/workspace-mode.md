# Workspace Mode Configuration

This guide covers how to configure QDrant Loader using workspace mode, which provides organized directory structure and simplified configuration management for your projects.

## 🎯 Overview

Workspace mode in QDrant Loader provides a structured approach to organizing your configuration files, logs, and metrics in a dedicated directory. It automatically discovers configuration files and creates necessary subdirectories for organized project management.

### What Workspace Mode Provides

```text
📁 Workspace Directory
├── config.yaml         # Main configuration file
├── .env                 # Environment variables (optional)
├── logs/                # Application logs
│   └── qdrant-loader.log
├── metrics/             # Performance metrics
└── data/                # State database
    └── qdrant-loader.db
```

### Benefits of Workspace Mode

- **Auto-discovery**: Automatically finds `config.yaml` and `.env` files
- **Organized structure**: Creates dedicated directories for logs and metrics
- **Simplified commands**: No need to specify config file paths
- **Consistent layout**: Standardized project organization

## 🏗️ Setting Up Workspace Mode

### Create Workspace Directory

```bash
# Create workspace directory
mkdir my-qdrant-workspace
cd my-qdrant-workspace

# Copy configuration template
cp packages/qdrant-loader/conf/config.template.yaml config.yaml
cp packages/qdrant-loader/conf/.env.template .env
```

### Basic Configuration Structure

QDrant Loader uses a **multi-project configuration** structure where all projects share a single Qdrant collection but are isolated through project metadata:

```yaml
# config.yaml - Multi-project configuration
global:
  qdrant:
    url: "http://localhost:6333"
    api_key: null # Optional for Qdrant Cloud
    collection_name: "my_documents" # Shared by all projects
  llm:
    provider: "openai"
    base_url: "https://api.openai.com/v1"
    api_key: "${LLM_API_KEY}"
    models:
      embeddings: "text-embedding-3-small"
      chat: "gpt-4o-mini"
    embeddings:
      vector_size: 1536

projects:
  docs-project:
    project_id: "docs-project"
    display_name: "Documentation Project"
    description: "Company documentation"
    sources:
      git:
        docs-repo:
          base_url: "https://github.com/company/docs"
          branch: "main"
          include_paths:
            - "docs/**"
            - "*.md"
          token: "${GITHUB_TOKEN}"

  wiki-project:
    project_id: "wiki-project"
    display_name: "Wiki Project"
    description: "Internal wiki content"
    sources:
      confluence:
        company-wiki:
          base_url: "https://company.atlassian.net/wiki"
          space_key: "WIKI"
          token: "${CONFLUENCE_TOKEN}"
          email: "${CONFLUENCE_EMAIL}"
```

### Environment Variables

```bash
# .env file
# Required - QDrant Database
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your-qdrant-cloud-key # Optional

# Required - LLM Provider (new unified approach)
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your-openai-api-key
LLM_EMBEDDING_MODEL=text-embedding-3-small
LLM_CHAT_MODEL=gpt-4o-mini

# Legacy (still supported)
OPENAI_API_KEY=your-openai-api-key

# Optional - Source credentials
GITHUB_TOKEN=your-github-token
CONFLUENCE_TOKEN=your-confluence-token
CONFLUENCE_EMAIL=your-email@company.com
```

## ⚙️ Workspace Commands

### Initialize Workspace

```bash
# Initialize collection and prepare workspace
qdrant-loader init --workspace .

# Force recreation of existing collection
qdrant-loader init --workspace . --force
```

### Ingest Data

```bash
# Process all projects and sources
qdrant-loader ingest --workspace .

# Process specific project
qdrant-loader ingest --workspace . --project docs-project

# Process specific source type across all projects
qdrant-loader ingest --workspace . --source-type git

# Process specific source type from specific project
qdrant-loader ingest --workspace . --project docs-project --source-type git

# Process specific source from specific project
qdrant-loader ingest --workspace . --project docs-project --source-type git --source docs-repo

# Force processing of all documents (bypass change detection)
qdrant-loader ingest --workspace . --force
```

### Configuration Management

```bash
# Show current configuration
qdrant-loader config --workspace .

# Note: Project-specific commands are not currently available in the CLI
# The config command shows all configured projects and their status
```

## 📁 Project Management

### Project Structure

Each project in the configuration has:

- **project_id**: Unique identifier used for filtering and metadata
- **display_name**: Human-readable name for the project
- **description**: Brief description of the project's purpose
- **sources**: Configuration for data sources (git, confluence, jira, etc.)

### Project Management via Configuration

```bash
# View all configured projects and their settings
qdrant-loader config --workspace .

# Note: Dedicated project management commands (list, status, validate) 
# are not currently implemented in the CLI. Project information is 
# displayed through the config command.
```

### Project Isolation

Projects are isolated through metadata, not separate collections:

- All projects use the same Qdrant collection
- Each document includes `project_id` in metadata
- Search can be filtered by project through the MCP server
- Simplifies collection management and enables cross-project search

## 🔍 Data Source Configuration

### Supported Source Types

#### Git Repositories

```yaml
sources:
  git:
    repo-name:
      base_url: "https://github.com/user/repo"
      branch: "main"
      include_paths:
        - "docs/**"
        - "*.md"
      exclude_paths:
        - "node_modules/**"
      file_types:
        - "*.md"
        - "*.rst"
        - "*.txt"
      token: "${GITHUB_TOKEN}"
      enable_file_conversion: true
```

#### Confluence

```yaml
sources:
  confluence:
    wiki-name:
      base_url: "https://company.atlassian.net/wiki"
      deployment_type: "cloud"
      space_key: "DOCS"
      content_types:
        - "page"
        - "blogpost"
      token: "${CONFLUENCE_TOKEN}"
      email: "${CONFLUENCE_EMAIL}"
      enable_file_conversion: true
      download_attachments: true
```

#### JIRA

```yaml
sources:
  jira:
    project-name:
      base_url: "https://company.atlassian.net"
      deployment_type: "cloud"
      project_key: "PROJ"
      token: "${JIRA_TOKEN}"
      email: "${JIRA_EMAIL}"
      enable_file_conversion: true
      download_attachments: true
```

#### Local Files

```yaml
sources:
  localfile:
    local-docs:
      base_url: "file:///path/to/files"
      include_paths:
        - "docs/**"
      exclude_paths:
        - "tmp/**"
      file_types:
        - "*.md"
        - "*.txt"
      max_file_size: 1048576 # 1MB
      enable_file_conversion: true
```

#### Public Documentation

```yaml
sources:
  publicdocs:
    docs-site:
      base_url: "https://docs.example.com"
      version: "1.0"
      content_type: "html"
      path_pattern: "/docs/{version}/**"
      selectors:
        content: "article.main-content"
        remove:
          - "nav"
          - "header"
          - "footer"
      enable_file_conversion: true
      download_attachments: true
```

## 🔧 Advanced Configuration

### Global Settings

```yaml
global:
  # Processing configuration
  processing:
    chunk_size: 1500
    chunk_overlap: 200
  
  # LLM configuration (new unified approach)
  llm:
    provider: "openai"
    base_url: "https://api.openai.com/v1"
    api_key: "${LLM_API_KEY}"
    models:
      embeddings: "text-embedding-3-small"
      chat: "gpt-4o-mini"
    request:
      batch_size: 100
      timeout_s: 30
      max_retries: 3
    embeddings:
      vector_size: 1536
  
  # File conversion settings
  file_conversion:
    max_file_size: 52428800 # 50MB
    conversion_timeout: 300 # 5 minutes
    markitdown:
      enable_llm_descriptions: false
      llm_model: "gpt-4o"
      llm_api_key: "${LLM_API_KEY}"
```

### State Management

Workspace mode automatically manages the state database:

```yaml
global:
  state_management:
    database_path: "${STATE_DB_PATH}" # Ignored in workspace mode
    table_prefix: "qdrant_loader_"
    connection_pool:
      size: 5
      timeout: 30
```

In workspace mode, the state database is automatically created as `qdrant-loader.db` in the `data/` directory within the workspace.

## 📊 Workspace Structure

### Directory Layout

```text
my-qdrant-workspace/
├── config.yaml                              # Main configuration
├── .env                                     # Environment variables
├── logs/                                    # Application logs
│   └── qdrant-loader.log
├── metrics/                                 # Performance metrics
│   └── ingestion_metrics_YYYYMMDD_HHMMSS.json
└── data/
    └── qdrant-loader.db                     # Processing state database
```

### Log Files

Workspace mode automatically configures logging:

- **Location**: `logs/qdrant-loader.log`
- **Format**: Structured logging with timestamps
- **Rotation**: Automatic log rotation (if configured)

### Metrics

Performance metrics are stored in the `metrics/` directory:

- **Ingestion metrics**: Processing statistics and performance data
- **Error tracking**: Failed operations and retry attempts
- **Resource usage**: Memory and processing time metrics

## 🔗 MCP Server Integration

The MCP server uses environment variables for configuration and does not currently support workspace mode directly. You need to configure it using environment variables:

```json
{
  "mcpServers": {
    "qdrant-loader": {
      "command": "mcp-qdrant-loader",
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "QDRANT_API_KEY": "your-api-key",
        "QDRANT_COLLECTION_NAME": "my_documents",
        "LLM_API_KEY": "your-openai-key",
        "OPENAI_API_KEY": "your-openai-key",
        "MCP_DISABLE_CONSOLE_LOGGING": "true"
      }
    }
  }
}
```

### MCP Server Environment Variables

The MCP server requires these environment variables:

- **QDRANT_URL**: URL of your QDrant instance (required)
- **QDRANT_API_KEY**: API key for QDrant authentication (optional)
- **QDRANT_COLLECTION_NAME**: Name of the collection to use (default: "documents")
- **LLM_API_KEY**: LLM API key for embeddings (required, new unified approach)
- **OPENAI_API_KEY**: OpenAI API key for embeddings (legacy support, still required if LLM_API_KEY not set)
- **MCP_DISABLE_CONSOLE_LOGGING**: Set to "true" to disable console logging (recommended for Cursor)
- **MCP_LOG_LEVEL**: Logging level (optional, default: "INFO")
- **MCP_LOG_FILE**: Log file path (optional)

### Current Limitations

- The MCP server does not support the `--workspace` flag
- Configuration must be done through environment variables
- The `--config` option exists in the CLI but is not currently implemented
- Project-aware search filtering is not yet available in the MCP server

### Future Workspace Integration

Workspace mode support for the MCP server is planned for future releases, which would allow:

- Automatic discovery of workspace configuration
- Project-aware search capabilities
- Simplified configuration through workspace files

## 🚀 Getting Started Checklist

- [ ] **Create workspace directory** and navigate to it
- [ ] **Copy configuration template** to `config.yaml`
- [ ] **Create environment file** with required credentials
- [ ] **Configure projects** with your data sources
- [ ] **Initialize collection** with `qdrant-loader init --workspace .`
- [ ] **Ingest data** with `qdrant-loader ingest --workspace .`
- [ ] **Verify setup** with `qdrant-loader config --workspace .`
- [ ] **Test search** through MCP server integration

## 🔗 Related Documentation

- **[Configuration File Reference](./config-file-reference.md)** - Complete YAML configuration options
- **[Environment Variables Reference](./environment-variables.md)** - Environment variable configuration
- **[CLI Reference](../cli-reference/README.md)** - Command-line interface documentation
- **[MCP Server Setup](../detailed-guides/mcp-server/setup-and-integration.md)** - MCP server integration guide

---

**Workspace mode provides organized, scalable configuration management for your QDrant Loader projects.** 🎉

This structured approach simplifies project management while maintaining flexibility for complex multi-source configurations.
