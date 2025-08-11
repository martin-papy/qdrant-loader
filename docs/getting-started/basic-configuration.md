# Basic Configuration
This guide walks you through configuring QDrant Loader for your specific needs. After completing this guide, you'll have a customized setup ready for your data sources and use cases.
## 🎯 Overview
QDrant Loader uses a flexible configuration system that supports:
- **Environment variables** for credentials and basic settings
- **Configuration files** for detailed project and source configuration
- **Workspace mode** for organized project management
- **Multiple environments** (development, staging, production)
## 🔧 Configuration Methods
### Configuration Priority
QDrant Loader uses this priority order (highest to lowest):
```text
1. Command-line arguments (--workspace, --config, --env)
2. Environment variables (QDRANT_URL, OPENAI_API_KEY, etc.)
3. Configuration file (config.yaml)
4. Default values (built-in defaults)
```
### Workspace Mode vs. Traditional Mode
| Workspace Mode (Recommended) | Traditional Mode |
|------------------------------|------------------|
| Organized directory structure | Individual config files |
| Auto-discovery of config files | Manual file specification |
| Built-in logging and metrics | Manual setup required |
| Good for: All use cases | Good for: Simple scripts |
| 5 minutes to configure | 10-15 minutes to configure |
## 🚀 Quick Setup (Workspace Mode)
### Create Workspace
```bash
# Create workspace directory
mkdir my-qdrant-workspace
cd my-qdrant-workspace
# Create environment variables file
cat > .env << EOF
# Required - QDrant Database
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=my_documents
# Required - OpenAI API
OPENAI_API_KEY=your-openai-api-key
# Optional - QDrant Cloud (if using cloud)
QDRANT_API_KEY=your-qdrant-cloud-api-key
EOF
```
### Create Basic Configuration
```bash
# Create basic multi-project configuration
cat > config.yaml << EOF
# Global configuration shared across all projects
global: qdrant: url: "\${QDRANT_URL}" api_key: "\${QDRANT_API_KEY}" collection_name: "\${QDRANT_COLLECTION_NAME}" openai: api_key: "\${OPENAI_API_KEY}" model: "text-embedding-3-small"
# Project definitions
projects: default: project_id: "default" display_name: "My Project" description: "Default project for getting started" sources: localfile: docs: base_url: "file://." include_paths: ["*.md", "*.txt"] file_types: ["*.md", "*.txt"]
EOF
```
### Initialize and Test
```bash
# Initialize QDrant collectionqdrant-loader init --workspace .
# Display current configurationqdrant-loader config --workspace .
# Check project status
qdrant-loader project status --workspace .
```
## ⚙️ Advanced Setup (Multi-Project Configuration)
### Configuration File Structure
The actual configuration uses a multi-project structure:
```yaml
# config.yaml - Multi-project configuration
# Global configuration shared across all projects
global: # QDrant Database Configuration qdrant: url: "${QDRANT_URL}" api_key: "${QDRANT_API_KEY}" # Optional, for QDrant Cloud collection_name: "${QDRANT_COLLECTION_NAME}" timeout: 30 # OpenAI Configuration openai: api_key: "${OPENAI_API_KEY}" model: "text-embedding-3-small" batch_size: 100 max_retries: 3 timeout: 30 # Processing Configuration processing: chunk_size: 1500 chunk_overlap: 200 min_chunk_size: 100 max_file_size: 52428800 # 50MB # State Management state_management: database_path: "${STATE_DB_PATH}" table_prefix: "qdrant_loader_" # File Conversion file_conversion: max_file_size: 52428800 # 50MB conversion_timeout: 300 markitdown: enable_llm_descriptions: false llm_model: "gpt-4o" llm_api_key: "${OPENAI_API_KEY}"
# Project definitions
projects: # Documentation project docs-project: project_id: "docs-project" display_name: "Documentation Project" description: "Company documentation and guides" sources: # Git repositories git: docs-repo: base_url: "https://github.com/example/docs.git" branch: "main" include_paths: ["docs/**", "README.md"] exclude_paths: ["node_modules/**", ".git/**"] file_types: ["*.md", "*.rst", "*.txt"] token: "${DOCS_REPO_TOKEN}" enable_file_conversion: true # Local files localfile: local-docs: base_url: "file:///path/to/local/files" include_paths: ["docs/**", "README.md"] exclude_paths: ["tmp/**", "archive/**"] file_types: ["*.md", "*.txt", "*.pdf"] enable_file_conversion: true # Knowledge base project kb-project: project_id: "kb-project" display_name: "Knowledge Base" description: "Internal knowledge base and wiki" sources: # Confluence confluence: company-confluence: base_url: "https://company.atlassian.net" space_key: "KB" deployment_type: "cloud" token: "${CONFLUENCE_TOKEN}" email: "${CONFLUENCE_EMAIL}" enable_file_conversion: true download_attachments: true # JIRA jira: support-project: base_url: "https://company.atlassian.net" deployment_type: "cloud" project_key: "SUPPORT" token: "${JIRA_TOKEN}" email: "${JIRA_EMAIL}" enable_file_conversion: true download_attachments: true
```
### Validate Configuration
```bash
# Display current configurationqdrant-loader config --workspace .
# Check project status and validate connections
qdrant-loader project status --workspace .
# List all configured projects
qdrant-loader project list --workspace .
```
## 🎯 Common Configuration Scenarios
### Scenario 1: Personal Knowledge Base
**Use Case**: Index personal documents, notes, and bookmarks
```yaml
global: qdrant: url: "${QDRANT_URL}" collection_name: "personal_knowledge" openai: api_key: "${OPENAI_API_KEY}" processing: chunk_size: 800
projects: personal: project_id: "personal" display_name: "Personal Knowledge Base" description: "Personal documents and notes" sources: localfile: documents: base_url: "file://~/Documents" include_paths: ["**/*.md", "**/*.txt", "**/*.pdf"] file_types: ["*.md", "*.txt", "*.pdf"] enable_file_conversion: true git: notes: base_url: "https://github.com/username/notes.git" branch: "main" include_paths: ["**/*.md"] file_types: ["*.md"] token: "${GITHUB_TOKEN}"
```
### Scenario 2: Team Documentation Hub
**Use Case**: Centralize team documentation from multiple sources
```yaml
global: qdrant: collection_name: "team_docs" openai: api_key: "${OPENAI_API_KEY}"
projects: team-docs: project_id: "team-docs" display_name: "Team Documentation" description: "Centralized team documentation" sources: git: main-repo: base_url: "${TEAM_REPO_URL}" branch: "main" include_paths: ["docs/**", "wiki/**", "README.md"] file_types: ["*.md", "*.rst"] token: "${TEAM_REPO_TOKEN}" confluence: team-space: base_url: "${CONFLUENCE_URL}" space_key: "TEAM" deployment_type: "cloud" token: "${CONFLUENCE_TOKEN}" email: "${CONFLUENCE_EMAIL}" jira: team-project: base_url: "${JIRA_URL}" project_key: "TEAM" deployment_type: "cloud" token: "${JIRA_TOKEN}" email: "${JIRA_EMAIL}"
```
### Scenario 3: Development Team Setup
**Use Case**: Code documentation and development resources
```yaml
global: qdrant: collection_name: "dev_docs" processing: chunk_size: 1200 max_file_size: 104857600 # 100MB
projects: frontend: project_id: "frontend" display_name: "Frontend Documentation" description: "React frontend application docs" sources: git: frontend-repo: base_url: "${FRONTEND_REPO_URL}" branch: "main" include_paths: ["src/**", "docs/**", "README.md"] file_types: ["*.md", "*.js", "*.ts", "*.jsx", "*.tsx"] token: "${REPO_TOKEN}" backend: project_id: "backend" display_name: "Backend Documentation" description: "API and backend documentation" sources: git: backend-repo: base_url: "${BACKEND_REPO_URL}" branch: "main" include_paths: ["src/**", "docs/**", "API.md"] file_types: ["*.md", "*.py", "*.yaml", "*.json"] token: "${REPO_TOKEN}"
```
## 🔐 Security Configuration
### Environment Variables for Credentials
```bash
# .env file - never commit to version control
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your-qdrant-cloud-api-key
QDRANT_COLLECTION_NAME=my_documents
OPENAI_API_KEY=sk-your-openai-api-key
# Git authentication
GITHUB_TOKEN=ghp_your-github-token
REPO_TOKEN=your-personal-access-token
# Confluence authentication (Cloud)
CONFLUENCE_URL=https://company.atlassian.net
CONFLUENCE_TOKEN=your-confluence-api-token
CONFLUENCE_EMAIL=your-email@company.com
# JIRA authentication (Cloud)
JIRA_URL=https://company.atlassian.net
JIRA_TOKEN=your-jira-api-token
JIRA_EMAIL=your-email@company.com
# For Data Center/Server deployments
CONFLUENCE_PAT=your-personal-access-token
JIRA_PAT=your-personal-access-token
```
### Secure Configuration Practices
```yaml
# config.yaml - safe to commit (no secrets)
global: qdrant: url: "${QDRANT_URL}" api_key: "${QDRANT_API_KEY}" # Reference environment variable openai: api_key: "${OPENAI_API_KEY}" # Reference environment variable
projects: example: sources: confluence: space: base_url: "${CONFLUENCE_URL}" token: "${CONFLUENCE_TOKEN}" email: "${CONFLUENCE_EMAIL}"
```
### File Permissions
```bash
# Secure configuration files
chmod 600 .env
chmod 644 config.yaml
# Secure workspace directory
chmod 700 logs/
chmod 700 metrics/
```
## 🌍 Multi-Environment Setup
### Development Environment
```yaml
# config-dev.yaml
global: qdrant: url: "http://localhost:6333" collection_name: "dev_docs" processing: chunk_size: 500 # Smaller for faster testing
projects: dev-project: project_id: "dev-project" display_name: "Development Project" description: "Development environment testing" sources: localfile: test-docs: base_url: "file://./test-data" include_paths: ["**/*.md"] file_types: ["*.md"]
```
### Production Environment
```yaml
# config-prod.yaml
global: qdrant: url: "${QDRANT_PROD_URL}" api_key: "${QDRANT_PROD_API_KEY}" collection_name: "production_docs" processing: chunk_size: 1200 max_file_size: 104857600 # 100MB
projects: prod-project: project_id: "prod-project" display_name: "Production Project" description: "Production documentation" sources: git: prod-repo: base_url: "${PROD_REPO_URL}" token: "${PROD_REPO_TOKEN}" confluence: prod-space: base_url: "${CONFLUENCE_PROD_URL}" token: "${CONFLUENCE_PROD_TOKEN}"
```
### Using Different Configurations
```bash
# Use specific configuration file
qdrant-loader --config config-dev.yaml --env .env.dev init
qdrant-loader --config config-prod.yaml --env .env.prod ingest
# Use workspace mode with different environmentsqdrant-loader init --workspace ./dev-workspaceqdrant-loader ingest --workspace ./prod-workspace
```
## 🔧 Performance Tuning
### For Large Datasets
```yaml
global: processing: chunk_size: 1500 # Larger chunks for better context chunk_overlap: 400 # More overlap for continuity max_file_size: 209715200 # 200MB openai: batch_size: 200 # Larger batches for efficiency
```
### For Fast Ingestion
```yaml
global: processing: chunk_size: 800 # Smaller chunks process faster chunk_overlap: 100 # Less overlap for speed openai: batch_size: 500 # Maximum batch size max_retries: 1 # Fewer retries for speed timeout: 10 # Shorter timeout
```
### For Memory Efficiency
```yaml
global: processing: chunk_size: 500 # Smaller chunks use less memory max_file_size: 10485760 # 10MB openai: batch_size: 50 # Smaller batches
```
## ✅ Configuration Validation
### Test Your Configuration
```bash
# Display current configurationqdrant-loader config --workspace .
# Check project status and connections
qdrant-loader project status --workspace .
# List all projects
qdrant-loader project list --workspace .
# Validate specific project
qdrant-loader project validate --workspace . --project-id my-project
```
### Common Configuration Issues
#### 1. Invalid YAML Syntax
**Error**: `yaml.scanner.ScannerError`
**Solution**:
```bash
# Check YAML syntax
python -c "import yaml; yaml.safe_load(open('config.yaml'))"
# Use proper indentation (2 spaces)
# Use quotes for strings with special characters
```
#### 2. Missing Environment Variables
**Error**: `KeyError: 'OPENAI_API_KEY'`
**Solution**:
```bash
# Check environment variables
env | grep QDRANT
env | grep OPENAI
# Set missing variables
export OPENAI_API_KEY="your-key-here"
```
#### 3. Connection Failures
**Error**: `ConnectionError: Unable to connect to QDrant`
**Solution**:
```bash
# Test QDrant connection
curl http://localhost:6333/health
# Check configurationqdrant-loader config --workspace .
```
#### 4. Invalid Project Structure
**Error**: `Legacy configuration format detected`
**Solution**: Update to multi-project format:
```yaml
# OLD (legacy) - not supported
sources: git: my-repo: {...}
# NEW (multi-project) - required
projects: default: project_id: "default" display_name: "My Project" sources: git: my-repo: {...}
```
## 📋 Configuration Checklist
- [ ] **Environment variables** set for all credentials
- [ ] **Configuration file** created with multi-project structure
- [ ] **QDrant connection** tested successfully
- [ ] **OpenAI API** key configured and tested
- [ ] **Projects** defined with appropriate sources
- [ ] **File permissions** secured (600 for .env files)
- [ ] **Workspace structure** created if using workspace mode
- [ ] **Performance settings** tuned for your dataset size
- [ ] **Source configurations** validated for each project
- [ ] **Backup strategy** for configuration files
## 🔗 Next Steps
With your configuration complete:
1. **Core Concepts** - Summarized inline in Getting Started
2. **[User Guides](../users/)** - Explore specific features and workflows
3. **[Data Source Guides](../users/detailed-guides/data-sources/)** - Configure specific connectors
4. **[MCP Server Setup](../users/detailed-guides/mcp-server/)** - Set up AI tool integration
5. **[CLI Reference](../users/cli-reference/)** - Learn all available commands
---
**Configuration Complete!** 🎉
Your QDrant Loader is now configured with the proper multi-project structure. You can start ingesting documents and using the search capabilities with your AI tools.
