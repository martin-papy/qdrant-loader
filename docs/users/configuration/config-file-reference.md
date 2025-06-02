# Configuration File Reference

This comprehensive reference covers all configuration options available in QDrant Loader's YAML configuration files. QDrant Loader uses a **multi-project configuration structure** that allows you to organize multiple data sources into logical projects within a single workspace.

## 🎯 Overview

QDrant Loader supports YAML configuration files for managing settings in a structured, version-controllable format. The configuration follows a **multi-project architecture** where:

- **Global settings** apply to all projects (embedding, chunking, state management)
- **Project-specific settings** define data sources and project metadata
- **All projects** share the same QDrant collection for unified search

### Configuration Structure

```yaml
# Multi-project configuration structure
global_config:          # Global settings for all projects
  qdrant: {...}         # QDrant connection settings
  embedding: {...}      # Embedding model configuration
  chunking: {...}       # Text chunking settings
  state_management: {...} # State database settings
  file_conversion: {...} # File conversion settings

projects:               # Project definitions
  project-1:            # Project ID
    project_id: "project-1"
    display_name: "Project One"
    description: "Project description"
    sources: {...}      # Project-specific data sources
  project-2: {...}      # Additional projects
```

### Configuration Priority

```text
1. Command-line arguments    (highest priority)
2. Environment variables
3. Configuration file        ← This guide
4. Default values           (lowest priority)
```

## 📁 Basic Configuration File

### Minimal Configuration

```yaml
# config.yaml - Minimal multi-project configuration
global_config:
  qdrant:
    url: "http://localhost:6333"
    collection_name: "documents"
  
  embedding:
    endpoint: "https://api.openai.com/v1"
    api_key: "${OPENAI_API_KEY}"
    model: "text-embedding-3-small"

projects:
  my-project:
    project_id: "my-project"
    display_name: "My Project"
    description: "Basic project setup"
    sources:
      git:
        my-repo:
          base_url: "https://github.com/user/repo.git"
          branch: "main"
          token: "${REPO_TOKEN}"
```

### Complete Configuration Template

```yaml
# config.yaml - Complete multi-project configuration template
global_config:
  # QDrant vector database configuration
  qdrant:
    url: "http://localhost:6333"
    api_key: "${QDRANT_API_KEY}"  # Optional: for QDrant Cloud
    collection_name: "documents"
  
  # Embedding model configuration
  embedding:
    endpoint: "https://api.openai.com/v1"
    api_key: "${OPENAI_API_KEY}"
    model: "text-embedding-3-small"
    batch_size: 100
    vector_size: 1536
    max_tokens_per_request: 8000
    max_tokens_per_chunk: 8000
  
  # Text chunking configuration
  chunking:
    chunk_size: 1500
    chunk_overlap: 200
  
  # State management configuration
  state_management:
    database_path: "${STATE_DB_PATH}"
    table_prefix: "qdrant_loader_"
    connection_pool:
      size: 5
      timeout: 30
  
  # File conversion configuration
  file_conversion:
    max_file_size: 52428800  # 50MB
    conversion_timeout: 300  # 5 minutes
    markitdown:
      enable_llm_descriptions: false
      llm_model: "gpt-4o"
      llm_endpoint: "https://api.openai.com/v1"
      llm_api_key: "${OPENAI_API_KEY}"

# Multi-project configuration
projects:
  # Example project: Documentation
  docs-project:
    project_id: "docs-project"
    display_name: "Documentation Project"
    description: "Company documentation and guides"
    
    sources:
      # Git repository sources
      git:
        docs-repo:
          base_url: "https://github.com/company/docs.git"
          branch: "main"
          include_paths: ["docs/**", "README.md"]
          exclude_paths: ["docs/archive/**"]
          file_types: ["*.md", "*.rst", "*.txt"]
          max_file_size: 1048576  # 1MB
          token: "${DOCS_REPO_TOKEN}"
          enable_file_conversion: true
      
      # Confluence sources
      confluence:
        company-wiki:
          base_url: "https://company.atlassian.net/wiki"
          deployment_type: "cloud"
          space_key: "DOCS"
          content_types: ["page", "blogpost"]
          include_labels: []
          exclude_labels: []
          token: "${CONFLUENCE_TOKEN}"
          email: "${CONFLUENCE_EMAIL}"
          enable_file_conversion: true
          download_attachments: true
  
  # Example project: Support Knowledge Base
  support-project:
    project_id: "support-project"
    display_name: "Support Knowledge Base"
    description: "Customer support documentation and tickets"
    
    sources:
      # JIRA sources
      jira:
        support-tickets:
          base_url: "https://company.atlassian.net"
          deployment_type: "cloud"
          project_key: "SUPPORT"
          requests_per_minute: 60
          page_size: 50
          token: "${JIRA_TOKEN}"
          email: "${JIRA_EMAIL}"
          enable_file_conversion: true
          download_attachments: true
      
      # Local file sources
      localfile:
        support-docs:
          base_url: "file:///path/to/support/docs"
          include_paths: ["**/*.md", "**/*.pdf"]
          exclude_paths: ["tmp/**", "archive/**"]
          file_types: ["*.md", "*.pdf", "*.txt"]
          max_file_size: 52428800  # 50MB
          enable_file_conversion: true
```

## 🔧 Detailed Configuration Sections

### Global Configuration (`global_config`)

#### QDrant Database Configuration

```yaml
global_config:
  qdrant:
    # Required: URL of your QDrant database instance
    url: "http://localhost:6333"
    
    # Optional: API key for QDrant Cloud or secured instances
    api_key: "${QDRANT_API_KEY}"
    
    # Required: Name of the QDrant collection (shared by all projects)
    collection_name: "documents"
```

**Required Fields:**

- `url` - QDrant instance URL
- `collection_name` - Collection name for all projects

**Optional Fields:**

- `api_key` - API key for QDrant Cloud (use environment variable)

#### Embedding Configuration

```yaml
global_config:
  embedding:
    # Required: OpenAI API endpoint
    endpoint: "https://api.openai.com/v1"
    
    # Required: OpenAI API key
    api_key: "${OPENAI_API_KEY}"
    
    # Optional: Embedding model (default: "text-embedding-3-small")
    model: "text-embedding-3-small"
    
    # Optional: Batch size for API calls (default: 100)
    batch_size: 100
    
    # Optional: Vector dimension (default: 1536)
    vector_size: 1536
    
    # Optional: Maximum tokens per API request (default: 8000)
    max_tokens_per_request: 8000
    
    # Optional: Maximum tokens per chunk (default: 8000)
    max_tokens_per_chunk: 8000
```

**Required Fields:**

- `endpoint` - OpenAI API endpoint URL
- `api_key` - OpenAI API key (use environment variable)

#### Chunking Configuration

```yaml
global_config:
  chunking:
    # Optional: Maximum size of text chunks in tokens (default: 1500)
    chunk_size: 1500
    
    # Optional: Overlap between chunks in tokens (default: 200)
    chunk_overlap: 200
```

#### State Management Configuration

```yaml
global_config:
  state_management:
    # Required: Path to SQLite database file
    database_path: "${STATE_DB_PATH}"
    
    # Optional: Prefix for database tables (default: "qdrant_loader_")
    table_prefix: "qdrant_loader_"
    
    # Optional: Connection pool settings
    connection_pool:
      size: 5      # Maximum connections (default: 5)
      timeout: 30  # Connection timeout in seconds (default: 30)
```

#### File Conversion Configuration

```yaml
global_config:
  file_conversion:
    # Optional: Maximum file size for conversion in bytes (default: 50MB)
    max_file_size: 52428800
    
    # Optional: Timeout for conversion operations in seconds (default: 300)
    conversion_timeout: 300
    
    # Optional: MarkItDown specific settings
    markitdown:
      # Enable LLM integration for image descriptions (default: false)
      enable_llm_descriptions: false
      
      # LLM model for image descriptions (default: "gpt-4o")
      llm_model: "gpt-4o"
      
      # LLM endpoint (default: "https://api.openai.com/v1")
      llm_endpoint: "https://api.openai.com/v1"
      
      # API key for LLM service (required when enable_llm_descriptions is true)
      llm_api_key: "${OPENAI_API_KEY}"
```

### Project Configuration (`projects`)

#### Project Structure

```yaml
projects:
  project-id:                    # Unique project identifier
    project_id: "project-id"     # Must match the key above
    display_name: "Project Name" # Human-readable name
    description: "Description"   # Optional project description
    sources:                     # Project-specific data sources
      # Source configurations go here
```

**Required Fields:**

- `project_id` - Unique identifier (must match YAML key)
- `display_name` - Human-readable project name

**Optional Fields:**

- `description` - Project description
- `sources` - Data source configurations (can be empty)

#### Data Source Types

QDrant Loader supports five data source types:

##### Git Repository Sources

```yaml
sources:
  git:
    source-name:
      # Required: Repository URL
      base_url: "https://github.com/user/repo.git"
      
      # Optional: Branch to process (default: "main")
      branch: "main"
      
      # Optional: Paths to include (glob patterns)
      include_paths:
        - "docs/**"
        - "README.md"
      
      # Optional: Paths to exclude (glob patterns)
      exclude_paths:
        - "node_modules/**"
        - ".git/**"
      
      # Optional: File extensions to process
      file_types:
        - "*.md"
        - "*.rst"
        - "*.txt"
      
      # Optional: Maximum file size in bytes (default: 1MB)
      max_file_size: 1048576
      
      # Optional: Maximum directory depth (default: unlimited)
      depth: 10
      
      # Optional: GitHub token for private repositories
      token: "${REPO_TOKEN}"
      
      # Optional: Enable file conversion (default: false)
      enable_file_conversion: true
```

##### Confluence Sources

```yaml
sources:
  confluence:
    source-name:
      # Required: Confluence instance URL
      base_url: "https://company.atlassian.net/wiki"
      
      # Required: Deployment type
      deployment_type: "cloud"  # Options: cloud, datacenter, server
      
      # Required: Space key to process
      space_key: "DOCS"
      
      # Optional: Content types to process (default: ["page"])
      content_types:
        - "page"
        - "blogpost"
      
      # Optional: Include only content with these labels
      include_labels: []
      
      # Optional: Exclude content with these labels
      exclude_labels: []
      
      # Required for Cloud: API token
      token: "${CONFLUENCE_TOKEN}"
      
      # Required for Cloud: User email
      email: "${CONFLUENCE_EMAIL}"
      
      # Optional: Enable file conversion (default: false)
      enable_file_conversion: true
      
      # Optional: Download and process attachments (default: false)
      download_attachments: true
```

##### JIRA Sources

```yaml
sources:
  jira:
    source-name:
      # Required: JIRA instance URL
      base_url: "https://company.atlassian.net"
      
      # Required: Deployment type
      deployment_type: "cloud"  # Options: cloud, datacenter, server
      
      # Required: Project key to process
      project_key: "PROJ"
      
      # Optional: Rate limit for API calls (default: 60)
      requests_per_minute: 60
      
      # Optional: Number of issues per API request (default: 50)
      page_size: 50
      
      # Required for Cloud: API token
      token: "${JIRA_TOKEN}"
      
      # Required for Cloud: User email
      email: "${JIRA_EMAIL}"
      
      # Optional: Enable file conversion (default: false)
      enable_file_conversion: true
      
      # Optional: Download and process attachments (default: false)
      download_attachments: true
```

##### Local File Sources

```yaml
sources:
  localfile:
    source-name:
      # Required: Base directory path (must use file:// prefix)
      base_url: "file:///path/to/files"
      
      # Optional: Paths to include (glob patterns)
      include_paths:
        - "docs/**"
        - "*.md"
      
      # Optional: Paths to exclude (glob patterns)
      exclude_paths:
        - "tmp/**"
        - ".*"  # Hidden files
      
      # Optional: File extensions to process
      file_types:
        - "*.md"
        - "*.pdf"
        - "*.txt"
      
      # Optional: Maximum file size in bytes (default: 50MB)
      max_file_size: 52428800
      
      # Optional: Enable file conversion (default: false)
      enable_file_conversion: true
```

##### Public Documentation Sources

```yaml
sources:
  publicdocs:
    source-name:
      # Required: Base URL of documentation site
      base_url: "https://docs.example.com"
      
      # Optional: Documentation version (default: "latest")
      version: "1.0"
      
      # Optional: Content type (default: "html")
      content_type: "html"
      
      # Optional: URL path pattern
      path_pattern: "/docs/{version}/**"
      
      # Optional: Paths to exclude
      exclude_paths:
        - "/api/**"
        - "/internal/**"
      
      # Optional: CSS selectors for content extraction
      selectors:
        content: "article.main-content"  # Main content selector
        remove:                          # Elements to remove
          - "nav"
          - "header"
          - "footer"
        code_blocks: "pre code, .code"   # Code block selectors
      
      # Optional: Enable file conversion (default: false)
      enable_file_conversion: true
      
      # Optional: Download and process attachments (default: false)
      download_attachments: true
      
      # Optional: Attachment selectors
      attachment_selectors:
        - "a[href$='.pdf']"
        - "a[href$='.docx']"
```

## 🔧 Configuration Management

### Using Configuration Files

#### Workspace Mode (Recommended)

```bash
# Create workspace directory
mkdir my-workspace && cd my-workspace

# Download configuration templates
curl -o config.yaml https://raw.githubusercontent.com/martin-papy/qdrant-loader/main/packages/qdrant-loader/conf/config.template.yaml
curl -o .env https://raw.githubusercontent.com/martin-papy/qdrant-loader/main/packages/qdrant-loader/conf/.env.template

# Edit configuration files
# Then use workspace mode
qdrant-loader --workspace . init
qdrant-loader --workspace . ingest
```

#### Traditional Mode

```bash
# Use specific configuration files
qdrant-loader --config /path/to/config.yaml --env /path/to/.env init
qdrant-loader --config /path/to/config.yaml --env /path/to/.env ingest
```

### Configuration Validation

#### Validate Configuration

```bash
# Validate all project configurations
qdrant-loader project --workspace . validate

# Validate specific project
qdrant-loader project --workspace . validate --project-id my-project

# View current configuration
qdrant-loader --workspace . config
```

#### Project Management

```bash
# List all configured projects
qdrant-loader project --workspace . list

# Show project status
qdrant-loader project --workspace . status

# Show status for specific project
qdrant-loader project --workspace . status --project-id my-project
```

## 📋 Environment Variables

Configuration files support environment variable substitution using `${VARIABLE_NAME}` syntax:

### Required Environment Variables

```bash
# QDrant Configuration
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=documents
QDRANT_API_KEY=your_api_key  # Optional: for QDrant Cloud

# Embedding Configuration
OPENAI_API_KEY=your_openai_key

# State Management
STATE_DB_PATH=./state.db
```

### Source-Specific Environment Variables

```bash
# Git Repositories
REPO_TOKEN=your_github_token

# Confluence (Cloud)
CONFLUENCE_TOKEN=your_confluence_token
CONFLUENCE_EMAIL=your_email

# JIRA (Cloud)
JIRA_TOKEN=your_jira_token
JIRA_EMAIL=your_email
```

## 🎯 Configuration Examples

### Single Project Setup

```yaml
global_config:
  qdrant:
    url: "${QDRANT_URL}"
    collection_name: "${QDRANT_COLLECTION_NAME}"
  
  embedding:
    endpoint: "https://api.openai.com/v1"
    api_key: "${OPENAI_API_KEY}"
    model: "text-embedding-3-small"
  
  state_management:
    database_path: "${STATE_DB_PATH}"

projects:
  main:
    project_id: "main"
    display_name: "Main Project"
    description: "Primary documentation project"
    
    sources:
      git:
        docs:
          base_url: "https://github.com/company/docs.git"
          branch: "main"
          token: "${REPO_TOKEN}"
          enable_file_conversion: true
```

### Multi-Project Setup

```yaml
global_config:
  qdrant:
    url: "${QDRANT_URL}"
    collection_name: "${QDRANT_COLLECTION_NAME}"
  
  embedding:
    endpoint: "https://api.openai.com/v1"
    api_key: "${OPENAI_API_KEY}"
    model: "text-embedding-3-small"
  
  chunking:
    chunk_size: 1500
    chunk_overlap: 200
  
  state_management:
    database_path: "${STATE_DB_PATH}"
  
  file_conversion:
    max_file_size: 52428800
    enable_llm_descriptions: false

projects:
  documentation:
    project_id: "documentation"
    display_name: "Documentation"
    description: "Technical documentation and guides"
    
    sources:
      git:
        docs-repo:
          base_url: "https://github.com/company/docs.git"
          branch: "main"
          include_paths: ["docs/**", "README.md"]
          token: "${DOCS_REPO_TOKEN}"
          enable_file_conversion: true
      
      confluence:
        tech-wiki:
          base_url: "https://company.atlassian.net/wiki"
          deployment_type: "cloud"
          space_key: "TECH"
          token: "${CONFLUENCE_TOKEN}"
          email: "${CONFLUENCE_EMAIL}"
          enable_file_conversion: true
  
  support:
    project_id: "support"
    display_name: "Customer Support"
    description: "Support documentation and tickets"
    
    sources:
      jira:
        support-tickets:
          base_url: "https://company.atlassian.net"
          deployment_type: "cloud"
          project_key: "SUPPORT"
          token: "${JIRA_TOKEN}"
          email: "${JIRA_EMAIL}"
          enable_file_conversion: true
      
      localfile:
        support-docs:
          base_url: "file:///path/to/support/docs"
          include_paths: ["**/*.md", "**/*.pdf"]
          file_types: ["*.md", "*.pdf"]
          enable_file_conversion: true
```

## 🔗 Related Documentation

- **[Environment Variables Reference](./environment-variables.md)** - Environment variable configuration
- **[Basic Configuration](../../getting-started/basic-configuration.md)** - Getting started with configuration
- **[Data Sources](../detailed-guides/data-sources/)** - Source-specific configuration guides
- **[Workspace Mode](./workspace-mode.md)** - Workspace configuration details

## 📋 Configuration Checklist

- [ ] **Global configuration** completed (qdrant, embedding, state_management)
- [ ] **Environment variables** configured in `.env` file
- [ ] **Project definitions** created with unique project IDs
- [ ] **Data source credentials** configured for your sources
- [ ] **File conversion settings** configured if processing non-text files
- [ ] **Configuration validated** with `qdrant-loader project validate`
- [ ] **Projects listed** with `qdrant-loader project list`
- [ ] **File permissions** set appropriately (chmod 600 for sensitive configs)
- [ ] **Version control** configured (exclude `.env` files)

---

**Multi-project configuration complete!** 🎉

Your QDrant Loader is now configured using the multi-project structure. This provides organized, scalable configuration management while maintaining unified search across all your projects through a shared QDrant collection.
