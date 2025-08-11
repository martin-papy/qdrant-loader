# Git Repositories
Connect QDrant Loader to Git repositories to index source code, documentation, and project files. This guide covers setup for GitHub, GitLab, Bitbucket, and self-hosted Git servers.
## 🎯 What Gets Processed
When you connect a Git repository, QDrant Loader can process:
- **Source code files** - Python, JavaScript, Java, C++, and more
- **Documentation** - Markdown, reStructuredText, plain text files
- **Configuration files** - YAML, JSON, TOML, XML
- **README files** - Project documentation and guides
- **Any text-based files** - Based on your file type configuration
## 🔧 Authentication Setup
### GitHub
#### Personal Access Token (Recommended)
1. **Create a Personal Access Token**:
   - Go to GitHub Settings → Developer settings → Personal access tokens
   - Click "Generate new token (classic)"
   - Select scopes: `repo` (for private repos) or `public_repo` (for public repos only)
   - Copy the token (starts with `ghp_`)
2. **Set environment variable**:
   ```bash
   export REPO_TOKEN=ghp_your_github_token_here
   ```
### GitLab
#### Personal Access Token
1. **Create a Personal Access Token**:
   - Go to GitLab Settings → Access Tokens
   - Create token with `read_repository` scope
   - Copy the token
2. **Set environment variable**:
   ```bash
   export REPO_TOKEN=glpat_your_gitlab_token_here
   ```
### Other Git Providers
For other Git providers (Bitbucket, self-hosted), use their respective token systems:
```bash
export REPO_TOKEN=your_access_token_here
```
## ⚙️ Configuration
QDrant Loader uses a **project-based configuration structure**. Each project can have multiple Git repository sources.
### Basic Configuration
```yaml
projects:
  my-project:
    display_name: "My Code Project"
    description: "Source code and documentation"
    collection_name: "my-code"
    sources:
      git:
        main-repo:
          base_url: "https://github.com/your-org/your-repo.git"
          branch: "main"
          token: "${REPO_TOKEN}"
          include_paths:
            - "docs/**"
            - "src/**"
            - "README.md"
          exclude_paths:
            - "node_modules/**"
            - "build/**"
          file_types:
            - "*.md"
            - "*.py"
            - "*.js"
          max_file_size: 1048576  # 1MB
          depth: 1
          enable_file_conversion: true
```
### Advanced Configuration
```yaml
projects:
  development:
    display_name: "Development Project"
    description: "Multiple repositories for development"
    collection_name: "dev-docs"
    sources:
      git:
        # Frontend repository
        frontend-repo:
          base_url: "https://github.com/your-org/frontend.git"
          branch: "main"
          token: "${REPO_TOKEN}"
          include_paths:
            - "src/**"
            - "docs/**"
            - "README.md"
          exclude_paths:
            - "node_modules/**"
            - "dist/**"
            - "build/**"
          file_types:
            - "*.js"
            - "*.jsx"
            - "*.ts"
            - "*.tsx"
            - "*.md"
          max_file_size: 1048576
          depth: 1
          enable_file_conversion: true
        # Backend repository
        backend-repo:
          base_url: "https://github.com/your-org/backend.git"
          branch: "main"
          token: "${REPO_TOKEN}"
          include_paths:
            - "src/**"
            - "docs/**"
            - "README.md"
          exclude_paths:
            - "__pycache__/**"
            - "venv/**"
            - ".pytest_cache/**"
          file_types:
            - "*.py"
            - "*.md"
            - "*.yaml"
            - "*.json"
          max_file_size: 1048576
          depth: 1
          enable_file_conversion: true
```
### Multiple Repositories
```yaml
projects:
  multi-repo:
    display_name: "Multi-Repository Project"
    description: "Documentation from multiple repositories"
    collection_name: "multi-repo-docs"
    sources:
      git:
        # Documentation repository
        docs-repo:
          base_url: "https://github.com/your-org/docs.git"
          branch: "main"
          token: "${REPO_TOKEN}"
          include_paths:
            - "docs/**"
            - "README.md"
          exclude_paths: []
          file_types:
            - "*.md"
            - "*.rst"
            - "*.txt"
          max_file_size: 1048576
          depth: 1
          enable_file_conversion: true
        # API documentation
        api-docs:
          base_url: "https://github.com/your-org/api-docs.git"
          branch: "main"
          token: "${REPO_TOKEN}"
          include_paths:
            - "**/*.md"
            - "**/*.yaml"
          exclude_paths:
            - "archive/**"
          file_types:
            - "*.md"
            - "*.yaml"
            - "*.json"
          max_file_size: 1048576
          depth: 1
          enable_file_conversion: true
```
## 🎯 Configuration Options
### Required Settings
| Option | Type | Description | Example |
|--------|------|-------------|---------|
| `base_url` | string | Repository URL (HTTPS or SSH) | `https://github.com/org/repo.git` |
| `branch` | string | Branch to process | `main` |
| `token` | string | Authentication token | `${REPO_TOKEN}` |
| `file_types` | list | File extensions to process | `["*.md", "*.py"]` |
### Path Filtering
| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `include_paths` | list | Glob patterns for paths to include | `[]` (all) |
| `exclude_paths` | list | Glob patterns for paths to exclude | `[]` |
### Processing Options
| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `max_file_size` | int | Maximum file size in bytes | `1048576` (1MB) |
| `depth` | int | Repository clone depth | `1` |
| `enable_file_conversion` | bool | Enable file conversion for attachments | `true` |
## 🚀 Usage Examples
### Software Development Team
```yaml
projects:
  dev-team:
    display_name: "Development Team"
    description: "Source code and technical documentation"
    collection_name: "dev-code"
    sources:
      git:
        # Main application repository
        main-app:
          base_url: "https://github.com/company/main-app.git"
          branch: "main"
          token: "${REPO_TOKEN}"
          include_paths:
            - "src/**"
            - "docs/**"
            - "README.md"
            - "CHANGELOG.md"
          exclude_paths:
            - "tests/**"
            - "node_modules/**"
            - "__pycache__/**"
          file_types:
            - "*.py"
            - "*.js"
            - "*.ts"
            - "*.md"
            - "*.yaml"
          max_file_size: 1048576
          depth: 1
          enable_file_conversion: true
        # Shared libraries
        shared-libs:
          base_url: "https://github.com/company/shared-libs.git"
          branch: "main"
          token: "${REPO_TOKEN}"
          include_paths:
            - "lib/**"
            - "docs/**"
          exclude_paths:
            - "tests/**"
          file_types:
            - "*.py"
            - "*.js"
            - "*.md"
          max_file_size: 524288  # 512KB
          depth: 1
          enable_file_conversion: true
```
### Documentation Team
```yaml
projects:
  docs-team:
    display_name: "Documentation Team"
    description: "All documentation repositories"
    collection_name: "documentation"
    sources:
      git:
        # Main documentation
        main-docs:
          base_url: "https://github.com/company/documentation.git"
          branch: "main"
          token: "${REPO_TOKEN}"
          include_paths:
            - "docs/**"
            - "guides/**"
            - "README.md"
          exclude_paths:
            - "archive/**"
          file_types:
            - "*.md"
            - "*.rst"
            - "*.txt"
          max_file_size: 1048576
          depth: 1
          enable_file_conversion: true
        # API documentation
        api-docs:
          base_url: "https://github.com/company/api-docs.git"
          branch: "main"
          token: "${REPO_TOKEN}"
          include_paths:
            - "**/*.md"
            - "**/*.yaml"
          exclude_paths: []
          file_types:
            - "*.md"
            - "*.yaml"
            - "*.json"
          max_file_size: 1048576
          depth: 1
          enable_file_conversion: true
```
### Research Team
```yaml
projects:
  research-team:
    display_name: "Research Team"
    description: "Research code and documentation"
    collection_name: "research"
    sources:
      git:
        # Analysis tools
        analysis-tools:
          base_url: "https://github.com/research-org/analysis-tools.git"
          branch: "main"
          token: "${REPO_TOKEN}"
          include_paths:
            - "src/**"
            - "notebooks/**"
            - "docs/**"
            - "README.md"
          exclude_paths:
            - "data/**"
            - "output/**"
          file_types:
            - "*.py"
            - "*.ipynb"
            - "*.md"
            - "*.txt"
          max_file_size: 2097152  # 2MB for notebooks
          depth: 1
          enable_file_conversion: true
```
## 🧪 Testing and Validation
### Initialize and Test Configuration
```bash
# Initialize the project (creates collection if needed)
\1 init --workspace .
# Test ingestion with your Git configuration
\1 ingest --workspace . --project my-project
# Check project status
\1 project \3 --workspace \2 --project-id my-project
# List all configured projects
\1 project \3 --workspace \2
# Validate project configuration
\1 project \3 --workspace \2 --project-id my-project
```
### Debug Git Processing
```bash
# Enable debug logging
\1 ingest --workspace . --log-level DEBUG --project my-project
# Process specific project only
\1 ingest --workspace . --project my-project
# Process specific source within a project
\1 ingest --workspace . --project my-project --source-type git --source main-repo
```
## 🔧 Troubleshooting
### Common Issues
#### Authentication Failures
**Problem**: `Authentication failed` or `Permission denied`
**Solutions**:
```bash
# Check token validity for GitHub
curl -H "Authorization: token $REPO_TOKEN" https://api.github.com/user
# Check token validity for GitLab
curl -H "Authorization: Bearer $REPO_TOKEN" https://gitlab.com/api/v4/user
# Test repository access manually
git clone https://github.com/org/repo.git /tmp/test-repo
```
**Check your configuration**:
- Ensure the `token` is set correctly via environment variable
- For private repositories, ensure the token has appropriate permissions
- Verify the repository URL is correct and accessible
#### Repository Access Issues
**Problem**: `Repository not found` or `No permission to access repository`
**Solutions**:
1. **Verify repository URL**:
   - Ensure the URL is correct and includes `.git` extension
   - Check if the repository is public or private
   - Verify you have access to the repository
2. **Check authentication**:
   ```bash
   # Test manual clone
   git clone https://github.com/org/repo.git /tmp/test-clone
   ```
3. **Verify token permissions**:
   - For GitHub: Ensure token has `repo` scope for private repos
   - For GitLab: Ensure token has `read_repository` scope
#### Configuration Issues
**Problem**: Configuration validation errors
**Solutions**:
1. **Verify project structure**:
   ```yaml
   projects:
     your-project:  # Project ID
       sources:
         git:
           source-name:  # Source name
             base_url: "..."
             # ... other settings
   ```
2. **Check required fields**:
   - `base_url`: Must be a valid Git repository URL
   - `branch`: Must be a valid branch name
   - `token`: Must be set via environment variable
   - `file_types`: Must be a non-empty list
3. **Validate file patterns**:
   ```yaml
   file_types:
     - "*.md"    # Correct
     - "*.py"    # Correct
   include_paths:
     - "docs/**" # Correct glob pattern
     - "src/**"  # Correct glob pattern
   ```
#### Large Repository Performance
**Problem**: Processing takes too long or uses too much memory
**Solutions**:
1. **Filter paths aggressively**:
   ```yaml
   git:
     large-repo:
       include_paths:
         - "docs/**"
         - "README.md"
       exclude_paths:
         - "node_modules/**"
         - "build/**"
         - "dist/**"
         - ".git/**"
   ```
2. **Limit file types**:
   ```yaml
   git:
     focused-repo:
       file_types:
         - "*.md"
         - "*.py"
       # Skip binary files, images, etc.
   ```
3. **Set file size limits**:
   ```yaml
   git:
     size-limited:
       max_file_size: 524288  # 512KB
   ```
#### File Processing Errors
**Problem**: Some files fail to process
**Solutions**:
1. **Check file size limits**:
   ```yaml
   git:
     repo-with-limits:
       max_file_size: 1048576  # 1MB
   ```
2. **Verify file types**:
   ```yaml
   git:
     text-only:
       file_types:
         - "*.md"
         - "*.txt"
         - "*.py"
         - "*.js"
       # Avoid binary files
   ```
3. **Check file paths**:
   - Ensure include/exclude patterns are correct
   - Verify files exist in the specified paths
### Debugging Commands
```bash
# Check Git configuration
git config --list
# Test repository access manually
git clone https://github.com/org/repo.git /tmp/test-repo
# Check file patterns locally
find /tmp/test-repo -name "*.py" | head -10
# Verify authentication
curl -H "Authorization: token $REPO_TOKEN" \
  https://api.github.com/repos/org/repo
```
## 📊 Monitoring and Processing
### Check Processing Status
```bash
# View project status
\1 project \3 --workspace \2
# Check specific project
\1 project \3 --workspace \2 --project-id my-project
# List all projects
\1 project \3 --workspace \2
```
### Configuration Management
```bash
# View current configuration
\1 config --workspace .
# Validate all projects
\1 project \3 --workspace \2
```
## 🔄 Best Practices
### Repository Organization
1. **Use specific branches** - Process stable branches like `main` or `release`
2. **Filter aggressively** - Only include files you need to search
3. **Set size limits** - Avoid processing very large files
4. **Exclude build artifacts** - Skip generated files and dependencies
### Path Filtering
1. **Include specific paths**:
   ```yaml
   include_paths:
     - "docs/**"
     - "src/**"
     - "README.md"
   ```
2. **Exclude unnecessary paths**:
   ```yaml
   exclude_paths:
     - "node_modules/**"
     - "build/**"
     - "dist/**"
     - "__pycache__/**"
     - ".git/**"
   ```
### File Type Selection
1. **Focus on text files**:
   ```yaml
   file_types:
     - "*.md"
     - "*.py"
     - "*.js"
     - "*.yaml"
     - "*.json"
   ```
2. **Avoid binary files** - They don't provide searchable content
### Performance Optimization
1. **Use shallow clones** - Set `depth: 1` for faster cloning
2. **Limit file sizes** - Set reasonable `max_file_size` limits
3. **Process incrementally** - Run regular updates rather than full reprocessing
4. **Monitor resources** - Watch memory and disk usage during processing
### Security Considerations
1. **Use minimal permissions** - Grant only necessary repository access
2. **Rotate tokens regularly** - Update access tokens periodically
3. **Secure token storage** - Store tokens in environment variables
4. **Audit access** - Monitor which repositories are being accessed
5. **Use environment variables** - Never commit tokens to version control
## 📚 Related Documentation
- **[Configuration Reference](../../configuration/)** - Complete configuration options
- **[File Conversion](../file-conversion/)** - Processing different file types found in repositories
- **[Troubleshooting](../../troubleshooting/)** - Common issues and solutions
- **[MCP Server](../mcp-server/)** - Using processed Git content with AI tools
- **[Project Management](../../cli-reference/)** - Managing multiple projects
---
**Ready to connect your Git repositories?** Start with the basic configuration above and customize based on your specific needs and repository structure.
