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
global:
  # Global settings for all projects
  qdrant: {}
  embedding: {}
  chunking: {}
  state_management: {}
  file_conversion: {}

projects:
  # Project definitions
  project-1:
    project_id: "project-1"
    display_name: "Project One"
    description: "Project description"
    sources: {}
  project-2:
    project_id: "project-2"
    display_name: "Project Two"
    description: "Another project"
    sources: {}
```

### Configuration Priority

```text
1. Command-line arguments (highest priority)
2. Environment variables
3. Configuration file ← This guide
4. Default values (lowest priority)
```

## 📁 Basic Configuration File

### Minimal Configuration

```yaml
# config.yaml - Minimal multi-project configuration
global:
  qdrant:
    url: "http://localhost:6333"
    collection_name: "documents"
  # New unified LLM configuration (provider-agnostic)
  llm:
    provider: ${LLM_PROVIDER}              # openai | ollama | openai_compat | custom
    base_url: ${LLM_BASE_URL}              # e.g. https://api.openai.com/v1, http://localhost:11434/v1
    api_key: ${LLM_API_KEY}                # optional for local providers like Ollama
    models:
      embeddings: ${LLM_EMBEDDING_MODEL}   # e.g. text-embedding-3-small | nomic-embed-text | bge-small-en-v1.5
      chat: ${LLM_CHAT_MODEL}              # e.g. gpt-4o-mini | llama3.1:8b-instruct
    tokenizer: cl100k_base                 # cl100k_base | none
    embeddings:
      vector_size: 1536                    # set according to chosen embedding model

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
          file_types:
            - "*.md"
            - "*.txt"
```

### Complete Configuration Template

```yaml
# config.yaml - Complete multi-project configuration template (abridged)
global:
  qdrant:
    url: "http://localhost:6333"
    api_key: "${QDRANT_API_KEY}"
    collection_name: "documents"
  llm:
    provider: ${LLM_PROVIDER}
    base_url: ${LLM_BASE_URL}
    api_key: ${LLM_API_KEY}
    headers: {}
    models:
      embeddings: ${LLM_EMBEDDING_MODEL}
      chat: ${LLM_CHAT_MODEL}
    tokenizer: cl100k_base
    request:
      timeout_s: 30
      max_retries: 3
      backoff_s_min: 1
      backoff_s_max: 30
    rate_limits:
      rpm: 1800
      tpm: 2000000
      concurrency: 5
    embeddings:
      vector_size: 1536
  chunking:
    chunk_size: 1500
    chunk_overlap: 200
    max_chunks_per_document: 500
    strategies:
      default:
        min_chunk_size: 100
        enable_semantic_analysis: true
        enable_entity_extraction: true
      html:
        simple_parsing_threshold: 100000
        max_html_size_for_parsing: 500000
        max_sections_to_process: 200
        max_chunk_size_for_nlp: 20000
        preserve_semantic_structure: true
      code:
        max_file_size_for_ast: 75000
        max_elements_to_process: 800
        max_recursion_depth: 8
        max_element_size: 20000
        enable_ast_parsing: true
        enable_dependency_analysis: true
      json:
        max_json_size_for_parsing: 1000000
        max_objects_to_process: 200
        max_chunk_size_for_nlp: 20000
        max_recursion_depth: 5
        max_array_items_per_chunk: 50
        max_object_keys_to_process: 100
        enable_schema_inference: true
      markdown:
        min_content_length_for_nlp: 100
        min_word_count_for_nlp: 20
        min_line_count_for_nlp: 3
        min_section_size: 500
        max_chunks_per_section: 1000
        max_overlap_percentage: 0.25
        max_workers: 4
        estimation_buffer: 0.2
        words_per_minute_reading: 200
        header_analysis_threshold_h1: 3
        header_analysis_threshold_h3: 8
        enable_hierarchical_metadata: true
  semantic_analysis:
    num_topics: 3
    lda_passes: 10
    spacy_model: "en_core_web_md"
  state_management:
    database_path: "${STATE_DB_PATH}"
    table_prefix: "qdrant_loader_"
    connection_pool:
      size: 5
      timeout: 30
  file_conversion:
    max_file_size: 52428800
    conversion_timeout: 300
    markitdown:
      enable_llm_descriptions: false
      llm_model: "gpt-4o"
      llm_endpoint: "https://api.openai.com/v1"
      llm_api_key: "${OPENAI_API_KEY}"

projects:
  docs-project:
    project_id: "docs-project"
    display_name: "Documentation Project"
    description: "Company documentation and guides"
    sources:
      git:
        docs-repo:
          base_url: "https://github.com/company/docs.git"
          branch: "main"
          include_paths:
            - "docs/**"
            - "README.md"
          exclude_paths:
            - "docs/archive/**"
          file_types:
            - "*.md"
            - "*.rst"
            - "*.txt"
          max_file_size: 1048576
          depth: 1
          token: "${DOCS_REPO_TOKEN}"
          enable_file_conversion: true
      confluence:
        company-wiki:
          base_url: "https://company.atlassian.net/wiki"
          deployment_type: "cloud"
          space_key: "DOCS"
          content_types:
            - "page"
            - "blogpost"
          include_labels: []
          exclude_labels: []
          token: "${CONFLUENCE_TOKEN}"
          email: "${CONFLUENCE_EMAIL}"
          enable_file_conversion: true
          download_attachments: true
  support-project:
    project_id: "support-project"
    display_name: "Support Knowledge Base"
    description: "Customer support documentation and tickets"
    sources:
      jira:
        support-tickets:
          base_url: "https://company.atlassian.net"
          deployment_type: "cloud"
          project_key: "SUPPORT"
          requests_per_minute: 60
          page_size: 100
          issue_types:
            - "Bug"
            - "Story"
            - "Task"
          include_statuses:
            - "Open"
            - "In Progress"
            - "Done"
          token: "${JIRA_TOKEN}"
          email: "${JIRA_EMAIL}"
          enable_file_conversion: true
          download_attachments: true
      localfile:
        support-docs:
          base_url: "file:///path/to/support/docs"
          include_paths:
            - "**/*.md"
            - "**/*.pdf"
          exclude_paths:
            - "tmp/**"
            - "archive/**"
          file_types:
            - "*.md"
            - "*.pdf"
            - "*.txt"
          max_file_size: 52428800
          enable_file_conversion: true
```

## 🔧 Detailed Configuration Sections

### Global Configuration (`global`)

#### QDrant Database Configuration

```yaml
global:
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

#### LLM Configuration (Unified)

```yaml
global:
  llm:
    # Required: Provider and endpoint
    provider: ${LLM_PROVIDER}
    base_url: ${LLM_BASE_URL}
    api_key: ${LLM_API_KEY}
    # Required: Models
    models:
      embeddings: ${LLM_EMBEDDING_MODEL}
      chat: ${LLM_CHAT_MODEL}
    # Optional: Tokenizer and policies
    tokenizer: cl100k_base
    request:
      timeout_s: 30
      max_retries: 3
    embeddings:
      vector_size: 1536

> Deprecation: `global.embedding.*` is still honored but will be removed in a future release. Migrate to `global.llm.*`.
```

**Required Fields:**

- `endpoint` - API endpoint URL
- `api_key` - API key (use environment variable)

#### Chunking Configuration

```yaml
global:
  chunking:
    # Optional: Maximum size of text chunks in characters (default: 1500)
    chunk_size: 1500
    # Optional: Overlap between chunks in characters (default: 200)
    chunk_overlap: 200
    # Optional: Maximum chunks per document - safety limit (default: 500)
    max_chunks_per_document: 500
    # Optional: Strategy-specific configurations for different content types
    strategies:
      default:
        min_chunk_size: 100
        enable_semantic_analysis: true
        enable_entity_extraction: true
      html:
        simple_parsing_threshold: 100000
        max_html_size_for_parsing: 500000
        max_sections_to_process: 200
        max_chunk_size_for_nlp: 20000
        preserve_semantic_structure: true
      code:
        max_file_size_for_ast: 75000
        max_elements_to_process: 800
        max_recursion_depth: 8
        max_element_size: 20000
        enable_ast_parsing: true
        enable_dependency_analysis: true
      json:
        max_json_size_for_parsing: 1000000
        max_objects_to_process: 200
        max_chunk_size_for_nlp: 20000
        max_recursion_depth: 5
        max_array_items_per_chunk: 50
        max_object_keys_to_process: 100
        enable_schema_inference: true
      markdown:
        min_content_length_for_nlp: 100
        min_word_count_for_nlp: 20
        min_line_count_for_nlp: 3
        min_section_size: 500
        max_chunks_per_section: 1000
        max_overlap_percentage: 0.25
        max_workers: 4
        estimation_buffer: 0.2
        words_per_minute_reading: 200
        header_analysis_threshold_h1: 3
        header_analysis_threshold_h3: 8
        enable_hierarchical_metadata: true
```

**Strategy-Specific Configuration Details:**

The `strategies` section allows you to fine-tune how different content types are processed:

**Default Strategy (Text Files):**

- `min_chunk_size`: Prevents creation of very small chunks that may lack context
- `enable_semantic_analysis`: Controls topic extraction and semantic analysis
- `enable_entity_extraction`: Controls named entity recognition processing

**HTML Strategy:**

- `simple_parsing_threshold`: Files below this size use simple text extraction
- `max_html_size_for_parsing`: Maximum size for complex HTML parsing before fallback
- `max_sections_to_process`: Limits processing to prevent infinite loops on malformed HTML
- `max_chunk_size_for_nlp`: Maximum chunk size for semantic analysis
- `preserve_semantic_structure`: Maintains HTML structure relationships in chunks

**Code Strategy:**

- `max_file_size_for_ast`: Maximum file size for Abstract Syntax Tree parsing
- `max_elements_to_process`: Limits code elements to prevent excessive processing time
- `max_recursion_depth`: Controls AST traversal depth for nested code structures
- `max_element_size`: Maximum size for individual code elements (functions, classes)
- `enable_ast_parsing`: Toggle AST-based code analysis vs simple text splitting
- `enable_dependency_analysis`: Extract import/dependency relationships

**JSON Strategy:**

- `max_json_size_for_parsing`: Maximum JSON file size for structured parsing
- `max_objects_to_process`: Limits number of JSON objects to prevent memory issues
- `max_chunk_size_for_nlp`: Maximum chunk size for semantic processing
- `max_recursion_depth`: Controls nested structure traversal depth
- `max_array_items_per_chunk`: Groups array items for better context
- `max_object_keys_to_process`: Limits object key processing for large objects
- `enable_schema_inference`: Automatically detect and extract JSON schema information

**Markdown Strategy:**

- `min_content_length_for_nlp`: Minimum content length required for NLP processing
- `min_word_count_for_nlp`: Minimum word count required for semantic analysis
- `min_line_count_for_nlp`: Minimum line count required for complex text processing
- `min_section_size`: Minimum section size before merging with adjacent sections
- `max_chunks_per_section`: Safety limit to prevent runaway chunking on large sections
- `max_overlap_percentage`: Maximum overlap between adjacent chunks (0.25 = 25%)
- `max_workers`: Number of parallel threads for processing large documents
- `estimation_buffer`: Buffer factor for chunk count estimation accuracy
- `words_per_minute_reading`: Reading speed for estimated reading time calculation
- `header_analysis_threshold_h1`: H1 header count threshold for split level decisions
- `header_analysis_threshold_h3`: H3 header count threshold for split level decisions
- `enable_hierarchical_metadata`: Extract section relationships and breadcrumb navigation

#### Semantic Analysis Configuration

```yaml
global:
  semantic_analysis:
    # Optional: Number of topics to extract using LDA (default: 3)
    num_topics: 3
    # Optional: Number of passes for LDA training (default: 10)
    lda_passes: 10
    # Optional: spaCy model for text processing (default: "en_core_web_md")
    spacy_model: "en_core_web_md"
```

#### State Management Configuration

```yaml
global:
  state_management:
    # Required: Path to SQLite database file
    # Supports environment variable expansion (e.g., $HOME, ${STATE_DB_PATH})
    # Special values: ":memory:" for in-memory database
    database_path: "${STATE_DB_PATH}"
    # Optional: Prefix for database tables (default: "qdrant_loader_")
    table_prefix: "qdrant_loader_"
    # Optional: Connection pool settings
    connection_pool:
      size: 5     # Maximum connections (default: 5)
      timeout: 30 # Connection timeout in seconds (default: 30)
```

**Path Validation Notes:**

- Supports environment variable expansion including `$HOME`
- Automatically creates parent directories if they don't exist
- Validates directory permissions before use
- Special handling for in-memory databases (`:memory:`)

#### File Conversion Configuration

```yaml
global:
  file_conversion:
    # Optional: Maximum file size for conversion in bytes (default: 50MB)
    # Range: 0 < max_file_size ≤ 100MB (104857600)
    max_file_size: 52428800
    # Optional: Timeout for conversion operations in seconds (default: 300)
    # Range: 0 < conversion_timeout ≤ 3600 seconds
    conversion_timeout: 300
    # Optional: MarkItDown specific settings
    markitdown:
      enable_llm_descriptions: false
      llm_model: "gpt-4o"
      llm_endpoint: "https://api.openai.com/v1"
      llm_api_key: "${OPENAI_API_KEY}"
```

### Project Configuration (`projects`)

#### Project Structure

```yaml
projects:
  project-id:
    # Unique project identifier
    project_id: "project-id"  # Must match the key above
    display_name: "Project Name"
    description: "Description"
    sources:
      # Project-specific data sources
      # Source configurations go here
```

#### Data Source Types

##### Git Repository Sources

```yaml
sources:
  git:
    source-name:
      base_url: "https://github.com/user/repo.git"
      token: "${REPO_TOKEN}"
      file_types:
        - "*.md"
        - "*.rst"
        - "*.txt"
      branch: "main"
      include_paths:
        - "docs/**"
        - "README.md"
      exclude_paths:
        - "node_modules/**"
        - ".git/**"
      max_file_size: 1048576
      depth: 1
      enable_file_conversion: true
```

##### Confluence Sources

```yaml
sources:
  confluence:
    source-name:
      base_url: "https://company.atlassian.net/wiki"
      deployment_type: "cloud"
      space_key: "DOCS"
      token: "${CONFLUENCE_TOKEN}"
      email: "${CONFLUENCE_EMAIL}"
      content_types:
        - "page"
        - "blogpost"
      include_labels: []
      exclude_labels: []
      enable_file_conversion: true
      download_attachments: true
```

##### JIRA Sources

```yaml
sources:
  jira:
    source-name:
      base_url: "https://company.atlassian.net"
      deployment_type: "cloud"
      project_key: "PROJ"
      token: "${JIRA_TOKEN}"
      email: "${JIRA_EMAIL}"
      requests_per_minute: 60
      page_size: 100
      issue_types:
        - "Bug"
        - "Story"
        - "Task"
      include_statuses:
        - "Open"
        - "In Progress"
        - "Done"
      enable_file_conversion: true
      download_attachments: true
```

##### Local File Sources

```yaml
sources:
  localfile:
    source-name:
      base_url: "file:///path/to/files"
      include_paths:
        - "docs/**"
        - "*.md"
      exclude_paths:
        - "tmp/**"
        - ".*"  # Hidden files
      file_types:
        - "*.md"
        - "*.pdf"
        - "*.txt"
      max_file_size: 1048576
      enable_file_conversion: true
```

##### Public Documentation Sources

```yaml
sources:
  publicdocs:
    source-name:
      base_url: "https://docs.example.com"
      version: "1.0"
      content_type: "html"  # Options: html, markdown, rst
      path_pattern: "/docs/{version}/**"
      exclude_paths:
        - "/api/**"
        - "/internal/**"
      selectors:
        content: "article.main-content"
        remove:
          - "nav"
          - "header"
          - "footer"
          - ".sidebar"
        code_blocks: "pre code"
      enable_file_conversion: true
      download_attachments: true
      attachment_selectors:
        - "a[href$='.pdf']"
        - "a[href$='.doc']"
        - "a[href$='.docx']"
        - "a[href$='.xls']"
        - "a[href$='.xlsx']"
        - "a[href$='.ppt']"
        - "a[href$='.pptx']"
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
qdrant-loader init --workspace .
qdrant-loader ingest --workspace .
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
# Display current configuration
qdrant-loader config --workspace .

# Validate project configurations
qdrant-loader project validate --workspace .

# Check project status
qdrant-loader project status --workspace .

# List all projects
qdrant-loader project list --workspace .
```

#### Project Management

```bash
# List all configured projects
qdrant-loader project list --workspace .

# Show project status
qdrant-loader project status --workspace .

# Show status for specific project
qdrant-loader project status --workspace . --project-id my-project
```

## 📋 Environment Variables

Configuration files support environment variable substitution using `${VARIABLE_NAME}` syntax:

### Required Environment Variables

```bash
# QDrant Configuration
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=documents
QDRANT_API_KEY=your_api_key # Optional: for QDrant Cloud

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
global:
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
          file_types:
            - "*.md"
            - "*.rst"
          enable_file_conversion: true
```

### Multi-Project Setup

```yaml
global:
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
    max_chunks_per_document: 500
    strategies:
      default:
        min_chunk_size: 100
        enable_semantic_analysis: true
        enable_entity_extraction: true
      html:
        simple_parsing_threshold: 100000
        max_html_size_for_parsing: 500000
        max_sections_to_process: 200
        max_chunk_size_for_nlp: 20000
        preserve_semantic_structure: true
      code:
        max_file_size_for_ast: 75000
        max_elements_to_process: 800
        max_recursion_depth: 8
        max_element_size: 20000
        enable_ast_parsing: true
        enable_dependency_analysis: true
      json:
        max_json_size_for_parsing: 1000000
        max_objects_to_process: 200
        max_chunk_size_for_nlp: 20000
        max_recursion_depth: 5
        max_array_items_per_chunk: 50
        max_object_keys_to_process: 100
        enable_schema_inference: true
      markdown:
        min_content_length_for_nlp: 100
        min_word_count_for_nlp: 20
        min_line_count_for_nlp: 3
        min_section_size: 500
        max_chunks_per_section: 1000
        max_overlap_percentage: 0.25
        max_workers: 4
        estimation_buffer: 0.2
        words_per_minute_reading: 200
        header_analysis_threshold_h1: 3
        header_analysis_threshold_h3: 8
        enable_hierarchical_metadata: true
  state_management:
    database_path: "${STATE_DB_PATH}"
  file_conversion:
    max_file_size: 52428800
    markitdown:
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
          include_paths:
            - "docs/**"
            - "README.md"
          token: "${DOCS_REPO_TOKEN}"
          file_types:
            - "*.md"
            - "*.rst"
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
          include_paths:
            - "**/*.md"
            - "**/*.pdf"
          file_types:
            - "*.md"
            - "*.pdf"
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
- [ ] **Required fields** provided (Git token, Confluence email/token, etc.)
- [ ] **File conversion settings** configured if processing non-text files
- [ ] **Configuration validated** with `qdrant-loader project validate`
- [ ] **Projects listed** with `qdrant-loader project list`
- [ ] **File permissions** set appropriately (chmod 600 for sensitive configs)
- [ ] **Version control** configured (exclude `.env` files)

---

**Multi-project configuration complete!** 🎉

Your QDrant Loader is now configured using the multi-project structure. This provides organized, scalable configuration management while maintaining unified search across all your projects through a shared QDrant collection.
