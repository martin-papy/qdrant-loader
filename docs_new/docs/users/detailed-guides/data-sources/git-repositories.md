# Git Repositories

Connect QDrant Loader to Git repositories to index source code, documentation, commit messages, and project history. This guide covers setup for GitHub, GitLab, Bitbucket, and self-hosted Git servers.

## 🎯 What Gets Processed

When you connect a Git repository, QDrant Loader can process:

- **Source code files** - Python, JavaScript, Java, C++, and more
- **Documentation** - Markdown, reStructuredText, plain text files
- **Configuration files** - YAML, JSON, TOML, XML
- **Commit messages** - Git history and metadata
- **README files** - Project documentation and guides
- **Issue templates** - GitHub/GitLab issue and PR templates

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

#### GitHub App (Enterprise)

For organizations, consider using a GitHub App:

```bash
export GITHUB_APP_ID=your_app_id
export GITHUB_APP_PRIVATE_KEY_PATH=/path/to/private-key.pem
export GITHUB_APP_INSTALLATION_ID=your_installation_id
```

### GitLab

#### Personal Access Token

1. **Create a Personal Access Token**:
   - Go to GitLab Settings → Access Tokens
   - Create token with `read_repository` scope
   - Copy the token

2. **Set environment variable**:

   ```bash
   export GITLAB_TOKEN=glpat_your_gitlab_token_here
   export GITLAB_URL=https://gitlab.com  # or your GitLab instance URL
   ```

### Bitbucket

#### App Password

1. **Create an App Password**:
   - Go to Bitbucket Settings → App passwords
   - Create password with `Repositories: Read` permission
   - Copy the password

2. **Set environment variables**:

   ```bash
   export BITBUCKET_USERNAME=your_username
   export BITBUCKET_APP_PASSWORD=your_app_password
   ```

### Self-Hosted Git

For self-hosted Git servers with HTTPS:

```bash
export GIT_USERNAME=your_username
export GIT_PASSWORD=your_password
# or
export GIT_TOKEN=your_access_token
```

For SSH access:

```bash
export GIT_SSH_KEY_PATH=/path/to/ssh/private/key
export GIT_SSH_PASSPHRASE=your_passphrase  # if key is encrypted
```

## ⚙️ Configuration

### Basic Configuration

```yaml
sources:
  git:
    - url: "https://github.com/your-org/your-repo.git"
      branch: "main"
      include_patterns:
        - "**/*.md"
        - "**/*.py"
        - "**/*.js"
      exclude_patterns:
        - "**/node_modules/**"
        - "**/.git/**"
        - "**/build/**"
```

### Advanced Configuration

```yaml
sources:
  git:
    - url: "https://github.com/your-org/frontend.git"
      branch: "main"
      # File filtering
      include_patterns:
        - "src/**/*.js"
        - "src/**/*.jsx"
        - "docs/**/*.md"
        - "README.md"
      exclude_patterns:
        - "**/node_modules/**"
        - "**/dist/**"
        - "**/*.test.js"
      
      # Size and age limits
      max_file_size: 1048576  # 1MB
      max_age_days: 365       # Only files modified in last year
      
      # Git-specific options
      include_commit_messages: true
      max_commits: 1000
      commit_message_pattern: "^(feat|fix|docs):"
      
      # Processing options
      follow_symlinks: false
      include_binary_files: false
      
      # Performance settings
      clone_depth: 100        # Shallow clone
      enable_lfs: false       # Git LFS support
```

### Multiple Repositories

```yaml
sources:
  git:
    # Frontend repository
    - url: "https://github.com/your-org/frontend.git"
      branch: "main"
      include_patterns: ["src/**/*.js", "docs/**/*.md"]
      
    # Backend repository
    - url: "https://github.com/your-org/backend.git"
      branch: "develop"
      include_patterns: ["**/*.py", "**/*.md"]
      
    # Documentation repository
    - url: "https://github.com/your-org/docs.git"
      branch: "main"
      include_patterns: ["**/*.md", "**/*.rst"]
```

## 🎯 Configuration Options

### Repository Settings

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `url` | string | Repository URL (HTTPS or SSH) | Required |
| `branch` | string | Branch to process | `main` |
| `tag` | string | Specific tag to process | None |
| `commit` | string | Specific commit SHA | None |

### File Filtering

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `include_patterns` | list | Glob patterns for files to include | `["**/*"]` |
| `exclude_patterns` | list | Glob patterns for files to exclude | `[]` |
| `max_file_size` | int | Maximum file size in bytes | `10485760` (10MB) |
| `max_age_days` | int | Only process files modified within N days | None |

### Git-Specific Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `include_commit_messages` | bool | Process commit messages | `false` |
| `max_commits` | int | Maximum number of commits to process | `1000` |
| `commit_message_pattern` | string | Regex pattern for commit messages | None |
| `clone_depth` | int | Shallow clone depth | None (full clone) |
| `enable_lfs` | bool | Enable Git LFS support | `false` |

### Processing Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `follow_symlinks` | bool | Follow symbolic links | `false` |
| `include_binary_files` | bool | Process binary files | `false` |
| `preserve_file_structure` | bool | Maintain directory structure in metadata | `true` |

## 🚀 Usage Examples

### Software Development Team

```yaml
sources:
  git:
    # Main application repository
    - url: "https://github.com/company/main-app.git"
      branch: "main"
      include_patterns:
        - "src/**/*.py"
        - "src/**/*.js"
        - "docs/**/*.md"
        - "README.md"
        - "CHANGELOG.md"
      exclude_patterns:
        - "**/tests/**"
        - "**/node_modules/**"
        - "**/__pycache__/**"
      include_commit_messages: true
      max_commits: 500
      
    # Shared libraries
    - url: "https://github.com/company/shared-libs.git"
      branch: "main"
      include_patterns:
        - "**/*.py"
        - "**/*.md"
      max_file_size: 524288  # 512KB
```

### Documentation Team

```yaml
sources:
  git:
    # Documentation repository
    - url: "https://github.com/company/documentation.git"
      branch: "main"
      include_patterns:
        - "**/*.md"
        - "**/*.rst"
        - "**/*.txt"
        - "**/*.yaml"  # OpenAPI specs
      include_commit_messages: true
      commit_message_pattern: "^(docs|content):"
      
    # Website repository
    - url: "https://github.com/company/website.git"
      branch: "main"
      include_patterns:
        - "content/**/*.md"
        - "docs/**/*.md"
```

### Research Team

```yaml
sources:
  git:
    # Research code repository
    - url: "https://github.com/research-org/analysis-tools.git"
      branch: "main"
      include_patterns:
        - "**/*.py"
        - "**/*.ipynb"  # Jupyter notebooks
        - "**/*.md"
        - "**/*.txt"
        - "data/**/*.csv"
      max_file_size: 5242880  # 5MB for data files
      
    # Paper repository
    - url: "https://github.com/research-org/papers.git"
      branch: "main"
      include_patterns:
        - "**/*.md"
        - "**/*.tex"
        - "**/*.bib"
```

## 🔍 Advanced Features

### Branch and Tag Processing

```yaml
sources:
  git:
    # Process specific branch
    - url: "https://github.com/org/repo.git"
      branch: "develop"
      
    # Process specific tag
    - url: "https://github.com/org/repo.git"
      tag: "v1.2.0"
      
    # Process specific commit
    - url: "https://github.com/org/repo.git"
      commit: "abc123def456"
```

### Commit Message Processing

```yaml
sources:
  git:
    - url: "https://github.com/org/repo.git"
      include_commit_messages: true
      max_commits: 1000
      # Only include commits matching pattern
      commit_message_pattern: "^(feat|fix|docs|refactor):"
      # Include commit metadata
      include_commit_metadata: true
```

### Performance Optimization

```yaml
sources:
  git:
    - url: "https://github.com/org/large-repo.git"
      # Shallow clone for faster processing
      clone_depth: 50
      
      # Limit file processing
      max_file_size: 1048576  # 1MB
      max_files_per_commit: 100
      
      # Parallel processing
      max_concurrent_files: 10
      
      # Caching
      enable_local_cache: true
      cache_ttl_hours: 24
```

### Monorepo Support

```yaml
sources:
  git:
    # Process different parts of a monorepo
    - url: "https://github.com/org/monorepo.git"
      branch: "main"
      include_patterns: ["frontend/**/*"]
      exclude_patterns: ["frontend/node_modules/**"]
      
    - url: "https://github.com/org/monorepo.git"
      branch: "main"
      include_patterns: ["backend/**/*"]
      exclude_patterns: ["backend/__pycache__/**"]
      
    - url: "https://github.com/org/monorepo.git"
      branch: "main"
      include_patterns: ["docs/**/*", "README.md"]
```

## 🧪 Testing and Validation

### Test Repository Connection

```bash
# Test Git repository access
qdrant-loader --workspace . test-connections --sources git

# Validate Git configuration
qdrant-loader --workspace . validate --sources git

# Dry run to see what files would be processed
qdrant-loader --workspace . --dry-run ingest --sources git
```

### Debug Git Processing

```bash
# Enable verbose logging
qdrant-loader --workspace . --verbose ingest --sources git

# Process only Git sources
qdrant-loader --workspace . ingest --sources git

# Check processing status
qdrant-loader --workspace . status --sources git
```

## 🔧 Troubleshooting

### Common Issues

#### Authentication Failures

**Problem**: `Authentication failed` or `Permission denied`

**Solutions**:

```bash
# Check token validity
curl -H "Authorization: token $REPO_TOKEN" https://api.github.com/user

# Verify token scopes
curl -H "Authorization: token $REPO_TOKEN" -I https://api.github.com/user

# For private repositories, ensure 'repo' scope is enabled
```

#### Large Repository Performance

**Problem**: Processing takes too long or uses too much memory

**Solutions**:

```yaml
sources:
  git:
    - url: "https://github.com/org/large-repo.git"
      # Use shallow clone
      clone_depth: 100
      
      # Limit file sizes
      max_file_size: 1048576  # 1MB
      
      # Filter files more aggressively
      include_patterns: ["**/*.md", "**/*.py"]
      exclude_patterns: 
        - "**/node_modules/**"
        - "**/build/**"
        - "**/dist/**"
        - "**/*.log"
```

#### Rate Limiting

**Problem**: `API rate limit exceeded`

**Solutions**:

```yaml
# Add rate limiting configuration
sources:
  git:
    - url: "https://github.com/org/repo.git"
      # Slow down requests
      request_delay: 1.0
      max_concurrent_requests: 2
      
      # Use authenticated requests (higher rate limits)
      # Ensure REPO_TOKEN is set
```

#### File Processing Errors

**Problem**: Some files fail to process

**Solutions**:

```yaml
sources:
  git:
    - url: "https://github.com/org/repo.git"
      # Skip binary files
      include_binary_files: false
      
      # Set size limits
      max_file_size: 1048576
      
      # Skip problematic file types
      exclude_patterns:
        - "**/*.bin"
        - "**/*.exe"
        - "**/*.so"
        - "**/*.dll"
```

### Debugging Commands

```bash
# Check Git configuration
git config --list

# Test repository access manually
git clone https://github.com/org/repo.git /tmp/test-repo

# Check file patterns
find /tmp/test-repo -name "*.py" | head -10

# Verify authentication
curl -H "Authorization: token $REPO_TOKEN" \
  https://api.github.com/repos/org/repo
```

## 📊 Monitoring and Metrics

### Processing Statistics

```bash
# View processing statistics
qdrant-loader --workspace . stats --sources git

# Check last processing time
qdrant-loader --workspace . status --sources git --verbose
```

### Performance Metrics

Monitor these metrics for Git processing:

- **Clone time** - Time to clone/update repository
- **File processing rate** - Files processed per second
- **Memory usage** - Peak memory during processing
- **Error rate** - Percentage of files that failed to process

## 🔄 Best Practices

### Repository Organization

1. **Use specific branches** - Process stable branches like `main` or `release`
2. **Filter aggressively** - Only include files you need to search
3. **Set size limits** - Avoid processing very large files
4. **Exclude build artifacts** - Skip generated files and dependencies

### Performance Optimization

1. **Use shallow clones** - Set `clone_depth` for large repositories
2. **Enable caching** - Cache repository data locally
3. **Batch processing** - Process multiple repositories in parallel
4. **Monitor resources** - Watch memory and disk usage

### Security Considerations

1. **Use minimal permissions** - Grant only necessary repository access
2. **Rotate tokens regularly** - Update access tokens periodically
3. **Secure token storage** - Store tokens in environment variables or secure vaults
4. **Audit access** - Monitor which repositories are being accessed

## 📚 Related Documentation

- **[File Conversion](../file-conversion/)** - Processing different file types found in repositories
- **[Configuration Reference](../../configuration/)** - Complete configuration options
- **[Troubleshooting](../../troubleshooting/)** - Common issues and solutions
- **[MCP Server](../mcp-server/)** - Using processed Git content with AI tools

---

**Ready to connect your Git repositories?** Start with the basic configuration above and customize based on your specific needs and repository structure.
