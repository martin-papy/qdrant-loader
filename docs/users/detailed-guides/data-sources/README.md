# Data Sources
QDrant Loader supports multiple data sources to help you index and search across all your organization's knowledge. This guide provides an overview of all supported sources and links to detailed configuration guides.
## 🎯 Supported Data Sources
### 📁 [Git Repositories](git-repositories.md)
Connect to Git repositories across multiple platforms to index code, documentation, and project files.
**Supported Platforms:**
- GitHub (github.com, GitHub Enterprise)
- GitLab (gitlab.com, self-hosted GitLab)
- Bitbucket (bitbucket.org, Bitbucket Server)
- Azure DevOps / TFS
- Self-hosted Git servers
**What Gets Processed:**
- Source code files (Python, JavaScript, Java, C++, etc.)
- Documentation (README, Markdown, reStructuredText)
- Configuration files (YAML, JSON, TOML)
- Project metadata and commit history
**Key Features:**
- Multiple authentication methods (SSH keys, tokens, passwords)
- Branch and tag filtering
- File type and path filtering
- Commit history processing
- Large repository optimization
---
### 🏢 [Confluence](confluence.md)
Index team documentation, knowledge bases, and collaborative content from Confluence Cloud and Data Center.
**Supported Versions:**
- Confluence Cloud (atlassian.com)
- Confluence Data Center / Server
**What Gets Processed:**
- Page content and hierarchy
- Attachments (PDFs, Office docs, images)
- Comments and discussions
- Page metadata (authors, dates, labels)
- Space information
**Key Features:**
- API token and OAuth authentication
- Space and page filtering
- Attachment processing with file conversion
- Version history tracking
- Bulk export support
---
### 🎫 [JIRA](jira.md)
Process project tickets, issues, requirements, and project management data from JIRA Cloud and Data Center.
**Supported Versions:**
- JIRA Cloud (atlassian.com)
- JIRA Data Center / Server
**What Gets Processed:**
- Issue content (summaries, descriptions, comments)
- Issue metadata (status, priority, assignee, labels)
- Custom fields and project-specific data
- Attachments and linked content
- Sprint and agile planning data
**Key Features:**
- API token and OAuth authentication
- JQL (JIRA Query Language) filtering
- Project and issue type filtering
- Custom field processing
- Agile workflow support
---
### 📂 [Local Files](local-files.md)
Process documents, research materials, archives, and any file-based content from your local file system.
**Supported File Types:**
- Documents (PDF, Word, PowerPoint, Excel)
- Text files (Markdown, plain text, reStructuredText)
- Code files (Python, JavaScript, Java, C++, etc.)
- Images (with OCR text extraction)
- Audio files (with transcription)
- Archives (ZIP, TAR, 7Z with extraction)
**What Gets Processed:**
- File content with format-specific conversion
- File metadata (creation date, author, size)
- Directory structure and organization
- Archive contents (recursive processing)
**Key Features:**
- 20+ file format support via MarkItDown
- OCR for image text extraction
- Audio transcription
- Archive extraction and processing
- Flexible file filtering patterns
---
### 🌐 [Public Documentation](public-docs.md)
Crawl and index public documentation websites, API references, and external knowledge sources.
**Supported Content Types:**
- API documentation (REST APIs, OpenAPI specs)
- Technical documentation (framework docs, tutorials)
- Knowledge bases (public wikis, help centers)
- Blog posts and release notes
- Static documentation sites
**What Gets Processed:**
- Web page content with CSS selector targeting
- Multi-page documentation sites
- Versioned documentation
- Code examples and API references
- Structured content extraction
**Key Features:**
- Respectful web crawling with rate limiting
- CSS selector-based content extraction
- JavaScript rendering for dynamic content
- Version-aware processing
- Comprehensive URL filtering
---
## 🔧 File Conversion
All data sources that handle files benefit from QDrant Loader's comprehensive [file conversion capabilities](../file-conversion/):
### Supported Formats
- **Documents**: PDF, Word, PowerPoint, Excel, OpenDocument
- **Text**: Markdown, reStructuredText, plain text, LaTeX
- **Images**: JPEG, PNG, GIF, TIFF (with OCR)
- **Audio**: MP3, WAV, M4A (with transcription)
- **Data**: JSON, CSV, XML, YAML
- **Archives**: ZIP, TAR, 7-Zip, RAR
### Advanced Features
- **OCR Text Extraction**: Extract text from images and scanned documents
- **Audio Transcription**: Convert speech to text using Whisper
- **Password Protection**: Handle encrypted files and archives
- **Metadata Extraction**: Preserve file metadata and properties
- **Batch Processing**: Efficient processing of large file collections
## ⚙️ Configuration Overview
### Multi-Project Configuration Structure
QDrant Loader uses a multi-project configuration structure. Here's the basic format:
```yaml
# Global configuration
global_config:
  qdrant:
    url: "${QDRANT_URL}"
    api_key: "${QDRANT_API_KEY}"
    collection_name: "${QDRANT_COLLECTION_NAME}"
  openai:
    api_key: "${OPENAI_API_KEY}"
# Project configurations
projects:
  my-project:
    project_id: "my-project"
    display_name: "My Project"
    description: "Project description"
    sources:
      # Git repositories
      git:
        company-docs:
          source_type: "git"
          source: "company-docs"
          base_url: "https://github.com/company/docs"
          branch: "main"
          token: "${GITHUB_TOKEN}"
      # Confluence spaces
      confluence:
        tech-docs:
          source_type: "confluence"
          source: "tech-docs"
          base_url: "${CONFLUENCE_URL}"
          space_key: "TECH"
          token: "${CONFLUENCE_TOKEN}"
          email: "${CONFLUENCE_EMAIL}"
      # JIRA projects
      jira:
        support:
          source_type: "jira"
          source: "support"
          base_url: "${JIRA_URL}"
          project_key: "SUP"
          token: "${JIRA_TOKEN}"
          email: "${JIRA_EMAIL}"
      # Local documentation
      localfile:
        local-docs:
          source_type: "localfile"
          source: "local-docs"
          base_url: "file:///docs/internal"
          include_paths: ["**/*.md", "**/*.pdf"]
      # Public API docs
      publicdocs:
        api-docs:
          source_type: "publicdocs"
          source: "api-docs"
          base_url: "https://api.example.com/docs"
          content_selector: ".api-content"
          include_paths: ["/docs/**"]
```
### Environment Variables
```bash
# QDrant configuration
export QDRANT_URL="https://your-qdrant-instance.com"
export QDRANT_API_KEY="your-qdrant-api-key"
export QDRANT_COLLECTION_NAME="documents"
# OpenAI configuration
export OPENAI_API_KEY="sk-your-openai-api-key"
# Git authentication
export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"
export GITLAB_TOKEN="glpat-xxxxxxxxxxxx"
# Confluence authentication
export CONFLUENCE_URL="https://company.atlassian.net/wiki"
export CONFLUENCE_EMAIL="user@company.com"
export CONFLUENCE_TOKEN="ATATT3xFfGF0xxxxxxxxxxxx"
# JIRA authentication
export JIRA_URL="https://company.atlassian.net"
export JIRA_EMAIL="user@company.com"
export JIRA_TOKEN="ATATT3xFfGF0xxxxxxxxxxxx"
```
## 🚀 Quick Start Examples
### Development Team
```yaml
projects:
  dev-team:
    project_id: "dev-team"
    display_name: "Development Team"
    description: "Source code and development documentation"
    sources:
      # Source code repositories
      git:
        backend:
          source_type: "git"
          source: "backend"
          base_url: "https://github.com/company/backend"
          include_paths: ["**/*.py", "**/*.md"]
          branch: "main"
          token: "${GITHUB_TOKEN}"
        frontend:
          source_type: "git"
          source: "frontend"
          base_url: "https://github.com/company/frontend"
          include_paths: ["**/*.js", "**/*.ts", "**/*.md"]
          branch: "main"
          token: "${GITHUB_TOKEN}"
      # Technical documentation
      confluence:
        dev-docs:
          source_type: "confluence"
          source: "dev-docs"
          base_url: "${CONFLUENCE_URL}"
          space_key: "DEV"
          token: "${CONFLUENCE_TOKEN}"
          email: "${CONFLUENCE_EMAIL}"
      # Development tickets
      jira:
        dev-issues:
          source_type: "jira"
          source: "dev-issues"
          base_url: "${JIRA_URL}"
          project_key: "DEV"
          token: "${JIRA_TOKEN}"
          email: "${JIRA_EMAIL}"
```
### Documentation Team
```yaml
projects:
  docs-team:
    project_id: "docs-team"
    display_name: "Documentation Team"
    description: "All documentation sources"
    sources:
      # Documentation repositories
      git:
        docs-repo:
          source_type: "git"
          source: "docs-repo"
          base_url: "https://github.com/company/docs"
          include_paths: ["**/*.md", "**/*.rst"]
          branch: "main"
          token: "${GITHUB_TOKEN}"
      # Knowledge base
      confluence:
        knowledge-base:
          source_type: "confluence"
          source: "knowledge-base"
          base_url: "${CONFLUENCE_URL}"
          space_key: "KB"
          token: "${CONFLUENCE_TOKEN}"
          email: "${CONFLUENCE_EMAIL}"
          download_attachments: true
      # Legacy documents
      localfile:
        legacy-docs:
          source_type: "localfile"
          source: "legacy-docs"
          base_url: "file:///docs/legacy"
          include_paths: ["**/*.pdf", "**/*.docx"]
      # External API documentation
      publicdocs:
        external-api:
          source_type: "publicdocs"
          source: "external-api"
          base_url: "https://docs.external-api.com"
          content_selector: ".documentation"
```
### Research Team
```yaml
projects:
  research-team:
    project_id: "research-team"
    display_name: "Research Team"
    description: "Research papers and datasets"
    sources:
      # Research repositories
      git:
        research-papers:
          source_type: "git"
          source: "research-papers"
          base_url: "https://github.com/research/papers"
          include_paths: ["**/*.tex", "**/*.bib", "**/*.md"]
          branch: "main"
          token: "${GITHUB_TOKEN}"
      # Research papers and datasets
      localfile:
        papers:
          source_type: "localfile"
          source: "papers"
          base_url: "file:///research/papers"
          include_paths: ["**/*.pdf", "**/*.tex"]
        datasets:
          source_type: "localfile"
          source: "datasets"
          base_url: "file:///research/datasets"
          include_paths: ["**/*.csv", "**/*.json"]
      # Project tracking
      jira:
        research-projects:
          source_type: "jira"
          source: "research-projects"
          base_url: "${JIRA_URL}"
          project_key: "RESEARCH"
          token: "${JIRA_TOKEN}"
          email: "${JIRA_EMAIL}"
          process_attachments: true
```
## 🧪 Configuration Management
### Basic Commands
```bash
# Show current configuration
\1 config --workspace .
# Initialize collection (one-time setup)
\1 init --workspace .
# Ingest data from all configured sources
\1 ingest --workspace .
# Force full re-ingestion
\1 init --workspace . --force
\1 ingest --workspace .
```
### Project Management
```bash
# List all configured projects
qdrant-loader project list --workspace .
# Show project status
qdrant-loader project status --workspace .
# Show specific project status
qdrant-loader project status --workspace . --project-id my-project
# Validate project configurations
qdrant-loader project validate --workspace .
# Validate specific project
qdrant-loader project validate --workspace . --project-id my-project
```
### Selective Processing
```bash
# Process specific project
\1 ingest --workspace . --project my-project
# Process specific source type from all projects
\1 ingest --workspace . --source-type git
# Process specific source type from specific project
\1 ingest --workspace . --project my-project --source-type git
# Process specific source from specific project
\1 ingest --workspace . --project my-project --source-type git --source my-repo
```
## 📊 Monitoring and Management
### Configuration Validation
```bash
# Validate all project configurations
qdrant-loader project validate --workspace .
# Validate specific project
qdrant-loader project validate --workspace . --project-id my-project
# Show configuration in JSON format
qdrant-loader project list --workspace . --format json
qdrant-loader project status --workspace . --format json
```
### Performance Optimization
```yaml
# Global performance settings in config.yaml
global_config:
  # File conversion settings
  file_conversion:
    markitdown:
      enable_llm_descriptions: false  # Disable for better performance
  # Processing settings
  processing:
    max_concurrent_sources: 3
    max_concurrent_files: 5
    batch_size: 100
# Source-specific optimization
projects:
  my-project:
    sources:
      git:
        large-repo:
          source_type: "git"
          source: "large-repo"
          base_url: "https://github.com/large-repo"
          # Optimize for large repositories
          max_file_size: 10485760  # 10MB
          exclude_paths: ["**/node_modules/**", "**/target/**"]
      localfile:
        large-dataset:
          source_type: "localfile"
          source: "large-dataset"
          base_url: "file:///large-dataset"
          # Optimize for many files
          max_file_size: 52428800  # 50MB
          include_paths: ["**/*.md", "**/*.txt"]
```
## 🔧 Troubleshooting
### Common Issues
#### Authentication Problems
**Problem**: `401 Unauthorized` or `403 Forbidden` errors
**Solutions**:
1. Verify API tokens and credentials in environment variables
2. Check token permissions and scopes
3. Ensure URLs are correct (include `/wiki` for Confluence)
4. Test authentication manually with curl
#### Configuration Issues
**Problem**: Configuration validation errors
**Solutions**:
1. Check YAML syntax and indentation
2. Verify all required fields are present
3. Ensure source_type and source fields match
4. Validate environment variable references
#### Performance Issues
**Problem**: Slow processing or timeouts
**Solutions**:
1. Reduce concurrent operations in global_config
2. Filter content more aggressively with include/exclude patterns
3. Increase max_file_size limits if needed
4. Process projects individually
#### Content Not Found
**Problem**: Expected content not being processed
**Solutions**:
1. Check include_paths and exclude_paths patterns
2. Verify source permissions and access
3. Use verbose logging: `--log-level DEBUG`
4. Validate configuration with `project validate`
### Getting Help
```bash
# Enable verbose logging for debugging
\1 ingest --workspace . --log-level DEBUG
# Check configuration syntax
qdrant-loader project validate --workspace .
# View project information
qdrant-loader project status --workspace .
# Show help for commands
qdrant-loader --help
qdrant-loader project --help
qdrant-loader ingest --help
```
## 📚 Detailed Guides
Each data source has comprehensive documentation covering:
- **Setup and Authentication** - Step-by-step configuration
- **Configuration Options** - Complete parameter reference
- **Usage Examples** - Real-world scenarios and patterns
- **Advanced Features** - Power user capabilities
- **Troubleshooting** - Common issues and solutions
- **Best Practices** - Optimization and security recommendations
### 📖 Individual Source Guides
- **[Git Repositories](git-repositories.md)** - Complete Git integration guide
- **[Confluence](confluence.md)** - Confluence Cloud and Data Center setup
- **[JIRA](jira.md)** - JIRA Cloud and Data Center configuration
- **[Local Files](local-files.md)** - File system processing guide
- **[Public Documentation](public-docs.md)** - Web crawling and content extraction
- **[File Conversion](../file-conversion/)** - Format support and conversion options
---
**Ready to connect your data sources?** Choose the sources that match your organization's tools and follow the detailed guides for step-by-step setup instructions.
