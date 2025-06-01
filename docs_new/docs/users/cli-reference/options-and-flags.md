# Options and Flags Reference

This comprehensive reference documents all command-line options, flags, and parameters available in QDrant Loader. Each option includes detailed descriptions, examples, and usage patterns for effective command-line usage.

## 🎯 Overview

QDrant Loader supports a rich set of command-line options that control every aspect of its behavior. Options can be categorized by their function and scope.

### Option Categories

```
🔧 Global Options      - Apply to all commands
📊 Data Options        - Control data processing
🔍 Search Options      - Configure search behavior
📁 Collection Options  - Manage collections
🌐 Network Options     - Network and connectivity
🔐 Security Options    - Authentication and security
📈 Performance Options - Optimization and tuning
```

## 🔧 Global Options

### Configuration Options

#### `--config`, `-c`

Specify configuration file path.

```bash
# Use specific configuration file
qdrant-loader --config production.yaml status

# Multiple configuration files (merged in order)
qdrant-loader --config base.yaml --config override.yaml load

# Configuration from URL
qdrant-loader --config https://config.company.com/qdrant.yaml status
```

**Default**: Auto-discovery (`./qdrant-loader.yaml`, `~/.qdrant-loader.yaml`, etc.)

#### `--env`

Set environment for configuration.

```bash
# Use production environment
qdrant-loader --env production load

# Use development environment
qdrant-loader --env development serve --dev

# Use custom environment
qdrant-loader --env staging config validate
```

**Default**: `development`

#### `--workspace`, `-w`

Specify workspace name.

```bash
# Use specific workspace
qdrant-loader --workspace team-docs status

# Switch to workspace
qdrant-loader --workspace production load

# Create and use workspace
qdrant-loader --workspace new-project init
```

**Default**: Current workspace or `default`

### Output Options

#### `--verbose`, `-v`

Enable verbose output.

```bash
# Verbose output
qdrant-loader -v load

# Extra verbose (debug level)
qdrant-loader -vv search "API docs"

# Maximum verbosity
qdrant-loader -vvv config validate
```

**Levels**: `-v` (INFO), `-vv` (DEBUG), `-vvv` (TRACE)

#### `--quiet`, `-q`

Suppress output.

```bash
# Quiet mode (errors only)
qdrant-loader -q load

# Silent mode (no output)
qdrant-loader -qq backup
```

**Levels**: `-q` (warnings+), `-qq` (errors only)

#### `--output`, `-o`

Specify output format.

```bash
# JSON output
qdrant-loader search "docs" --output json

# YAML output
qdrant-loader config show --output yaml

# Table output (default for most commands)
qdrant-loader status --output table

# CSV output
qdrant-loader collection stats --output csv
```

**Options**: `table`, `json`, `yaml`, `csv`, `text`

#### `--no-color`

Disable colored output.

```bash
# Disable colors (useful for scripts)
qdrant-loader --no-color status

# Force colors (override detection)
qdrant-loader --color status
```

### Help and Version

#### `--help`, `-h`

Show help information.

```bash
# Global help
qdrant-loader --help

# Command-specific help
qdrant-loader load --help

# Subcommand help
qdrant-loader config show --help
```

#### `--version`

Show version information.

```bash
# Show version
qdrant-loader --version

# Detailed version info
qdrant-loader --version --verbose
```

## 📊 Data Processing Options

### Source Options

#### `--source`, `-s`

Specify data source type.

```bash
# Single source
qdrant-loader load --source git

# Multiple sources
qdrant-loader load --source git,confluence,local

# All configured sources
qdrant-loader load --source all
```

**Options**: `git`, `confluence`, `jira`, `local`, `public`, `all`

#### `--url`

Specify source URL.

```bash
# Git repository URL
qdrant-loader load --source git --url https://github.com/company/docs

# Confluence base URL
qdrant-loader load --source confluence --url https://company.atlassian.net

# Public documentation URL
qdrant-loader load --source public --url https://docs.example.com
```

#### `--path`

Specify local file path.

```bash
# Single directory
qdrant-loader load --source local --path /path/to/docs

# Multiple paths
qdrant-loader load --source local --path "/docs,/guides,/api"

# Relative path
qdrant-loader load --source local --path ./documentation
```

#### `--recursive`, `-r`

Process directories recursively.

```bash
# Recursive processing
qdrant-loader load --source local --path /docs --recursive

# Non-recursive (current directory only)
qdrant-loader load --source local --path /docs --no-recursive
```

**Default**: `true` for most sources

### Filtering Options

#### `--include`

Include files matching patterns.

```bash
# Include specific file types
qdrant-loader load --include "*.md,*.rst,*.txt"

# Include specific directories
qdrant-loader load --include "docs/**,guides/**"

# Complex patterns
qdrant-loader load --include "**/*.{md,rst,pdf}"
```

#### `--exclude`

Exclude files matching patterns.

```bash
# Exclude common files
qdrant-loader load --exclude "*.log,node_modules/,__pycache__/"

# Exclude drafts and temporary files
qdrant-loader load --exclude "draft/*,*.tmp,*.backup"

# Exclude by size
qdrant-loader load --exclude-size ">10MB"
```

#### `--filter`

Apply content filters.

```bash
# Filter by metadata
qdrant-loader search "docs" --filter "source:confluence AND space:TECH"

# Filter by date
qdrant-loader search "guide" --filter "created_at:>2024-01-01"

# Complex filters
qdrant-loader search "API" --filter "(source:git OR source:confluence) AND type:documentation"
```

### Processing Options

#### `--chunk-size`

Set text chunk size in tokens.

```bash
# Custom chunk size
qdrant-loader load --chunk-size 1500

# Small chunks for better precision
qdrant-loader load --chunk-size 500

# Large chunks for better context
qdrant-loader load --chunk-size 2000
```

**Default**: `1000`

#### `--chunk-overlap`

Set overlap between chunks in tokens.

```bash
# Custom overlap
qdrant-loader load --chunk-overlap 300

# No overlap
qdrant-loader load --chunk-overlap 0

# Large overlap for continuity
qdrant-loader load --chunk-overlap 500
```

**Default**: `200`

#### `--batch-size`

Set processing batch size.

```bash
# Large batches for efficiency
qdrant-loader load --batch-size 500

# Small batches for memory constraints
qdrant-loader load --batch-size 50

# Custom batch size for specific sources
qdrant-loader load --source confluence --batch-size 100
```

**Default**: `100`

#### `--parallel-workers`

Set number of parallel workers.

```bash
# Use all CPU cores
qdrant-loader load --parallel-workers 0

# Specific number of workers
qdrant-loader load --parallel-workers 4

# Single-threaded processing
qdrant-loader load --parallel-workers 1
```

**Default**: CPU count

## 🔍 Search Options

### Search Type Options

#### `--type`

Specify search type.

```bash
# Semantic search (vector similarity)
qdrant-loader search "API documentation" --type semantic

# Keyword search (text matching)
qdrant-loader search "docker kubernetes" --type keyword

# Hybrid search (combined)
qdrant-loader search "deployment guide" --type hybrid
```

**Options**: `semantic`, `keyword`, `hybrid`
**Default**: `hybrid`

#### `--limit`, `-l`

Limit number of results.

```bash
# Limit results
qdrant-loader search "docs" --limit 5

# No limit (return all matches)
qdrant-loader search "guide" --limit 0

# Large result set
qdrant-loader search "API" --limit 50
```

**Default**: `10`

#### `--threshold`

Set similarity threshold.

```bash
# High precision (fewer, more relevant results)
qdrant-loader search "docs" --threshold 0.9

# Low precision (more results, less strict)
qdrant-loader search "guide" --threshold 0.6

# Default threshold
qdrant-loader search "API" --threshold 0.7
```

**Default**: `0.7`

### Search Scope Options

#### `--collection`

Search in specific collection.

```bash
# Single collection
qdrant-loader search "docs" --collection team_docs

# Multiple collections
qdrant-loader search "API" --collection "backend_docs,frontend_docs"

# All collections
qdrant-loader search "guide" --collection all
```

#### `--project`

Search in specific project (multi-project workspaces).

```bash
# Single project
qdrant-loader search "docs" --project backend

# Multiple projects
qdrant-loader search "API" --project "backend,frontend"

# Current project
qdrant-loader search "guide" --project current
```

#### `--scope`

Define search scope.

```bash
# Current workspace only
qdrant-loader search "docs" --scope current

# All accessible collections
qdrant-loader search "API" --scope accessible

# Global search
qdrant-loader search "guide" --scope all
```

**Options**: `current`, `accessible`, `all`

### Search Output Options

#### `--snippets`

Include content snippets in results.

```bash
# Include snippets
qdrant-loader search "docs" --snippets

# Custom snippet length
qdrant-loader search "API" --snippets --snippet-length 300

# No snippets
qdrant-loader search "guide" --no-snippets
```

#### `--show-metadata`

Include metadata in results.

```bash
# Show all metadata
qdrant-loader search "docs" --show-metadata

# Show specific metadata fields
qdrant-loader search "API" --metadata-fields "source,created_at,author"

# Hide metadata
qdrant-loader search "guide" --no-metadata
```

#### `--export`

Export search results.

```bash
# Export to JSON
qdrant-loader search "docs" --export results.json

# Export to CSV
qdrant-loader search "API" --export results.csv --output csv

# Export with metadata
qdrant-loader search "guide" --export results.json --show-metadata
```

## 📁 Collection Options

### Collection Management

#### `--collection`

Specify collection name.

```bash
# Work with specific collection
qdrant-loader status --collection team_docs

# Create collection
qdrant-loader collection create --collection new_docs

# Delete collection
qdrant-loader collection delete --collection old_docs
```

#### `--description`

Set collection description.

```bash
# Create with description
qdrant-loader collection create my_docs --description "My documentation collection"

# Update description
qdrant-loader collection update my_docs --description "Updated description"
```

#### `--vector-size`

Set vector dimension.

```bash
# Custom vector size
qdrant-loader collection create docs --vector-size 1536

# Auto-detect from model
qdrant-loader collection create docs --vector-size auto
```

**Default**: Auto-detected from embedding model

### Collection Operations

#### `--force`

Force operation without confirmation.

```bash
# Force reload data
qdrant-loader load --force

# Force delete collection
qdrant-loader collection delete old_docs --force

# Force overwrite
qdrant-loader collection restore backup.json --force
```

#### `--backup-before`

Create backup before operation.

```bash
# Backup before deletion
qdrant-loader collection delete old_docs --backup-before

# Backup before major update
qdrant-loader load --force --backup-before
```

#### `--confirm`

Require explicit confirmation.

```bash
# Require confirmation for deletion
qdrant-loader collection delete old_docs --confirm

# Skip confirmation (dangerous)
qdrant-loader collection delete old_docs --no-confirm
```

## 🌐 Network Options

### Connection Options

#### `--timeout`

Set operation timeout.

```bash
# Custom timeout (seconds)
qdrant-loader load --timeout 120

# No timeout
qdrant-loader load --timeout 0

# Short timeout for quick operations
qdrant-loader status --timeout 5
```

**Default**: `30` seconds

#### `--retries`

Set retry attempts.

```bash
# Custom retry count
qdrant-loader load --retries 5

# No retries
qdrant-loader load --retries 0

# Maximum retries
qdrant-loader load --retries 10
```

**Default**: `3`

#### `--rate-limit`

Set rate limiting.

```bash
# Limit requests per second
qdrant-loader load --source confluence --rate-limit 5

# No rate limiting
qdrant-loader load --rate-limit 0

# Conservative rate limiting
qdrant-loader load --source jira --rate-limit 2
```

### Proxy Options

#### `--proxy`

Set HTTP proxy.

```bash
# HTTP proxy
qdrant-loader load --proxy http://proxy.company.com:8080

# HTTPS proxy
qdrant-loader load --proxy https://proxy.company.com:8080

# Proxy with authentication
qdrant-loader load --proxy http://user:pass@proxy.company.com:8080
```

#### `--no-proxy`

Bypass proxy for specific hosts.

```bash
# Bypass proxy for localhost
qdrant-loader load --no-proxy localhost,127.0.0.1

# Bypass proxy for internal hosts
qdrant-loader load --no-proxy "*.internal.company.com"
```

## 🔐 Security Options

### Authentication Options

#### `--api-key`

Override API key.

```bash
# Custom OpenAI API key
qdrant-loader load --api-key sk-custom-key

# QDrant API key
qdrant-loader status --qdrant-api-key custom-qdrant-key
```

#### `--token`

Set authentication token.

```bash
# Git token
qdrant-loader load --source git --token ghp_custom_token

# Confluence token
qdrant-loader load --source confluence --token custom_confluence_token
```

#### `--username`

Set username for authentication.

```bash
# Git username
qdrant-loader load --source git --username custom_user

# Confluence username
qdrant-loader load --source confluence --username user@company.com
```

### Security Options

#### `--insecure`

Disable SSL verification.

```bash
# Disable SSL verification (development only)
qdrant-loader load --insecure

# Force SSL verification
qdrant-loader load --secure
```

#### `--ca-bundle`

Specify CA certificate bundle.

```bash
# Custom CA bundle
qdrant-loader load --ca-bundle /etc/ssl/certs/custom-ca.pem

# System CA bundle
qdrant-loader load --ca-bundle system
```

## 📈 Performance Options

### Processing Performance

#### `--memory-limit`

Set memory usage limit.

```bash
# Memory limit in MB
qdrant-loader load --memory-limit 2048

# Memory limit in GB
qdrant-loader load --memory-limit 4GB

# No memory limit
qdrant-loader load --memory-limit 0
```

#### `--cache-size`

Set cache size.

```bash
# Cache size in MB
qdrant-loader load --cache-size 512

# Large cache
qdrant-loader load --cache-size 2GB

# Disable cache
qdrant-loader load --cache-size 0
```

#### `--optimize`

Enable optimization.

```bash
# Enable all optimizations
qdrant-loader load --optimize

# Specific optimizations
qdrant-loader load --optimize memory,speed

# Disable optimizations
qdrant-loader load --no-optimize
```

### Progress and Monitoring

#### `--progress`

Show progress information.

```bash
# Show progress bar
qdrant-loader load --progress

# Detailed progress
qdrant-loader load --progress --verbose

# No progress display
qdrant-loader load --no-progress
```

#### `--stats`

Show statistics.

```bash
# Show processing statistics
qdrant-loader load --stats

# Detailed statistics
qdrant-loader status --stats --detailed

# Export statistics
qdrant-loader load --stats --export-stats stats.json
```

## 🔄 Operational Options

### Execution Options

#### `--dry-run`

Show what would be done without executing.

```bash
# Dry run for load operation
qdrant-loader load --dry-run

# Dry run for deletion
qdrant-loader delete --collection old_docs --dry-run

# Dry run with detailed output
qdrant-loader clean --all --dry-run --verbose
```

#### `--background`

Run operation in background.

```bash
# Background processing
qdrant-loader load --background

# Background with log file
qdrant-loader load --background --log-file /var/log/qdrant-loader.log

# Background with PID file
qdrant-loader load --background --pid-file /var/run/qdrant-loader.pid
```

#### `--interactive`

Enable interactive mode.

```bash
# Interactive search
qdrant-loader search --interactive

# Interactive configuration
qdrant-loader config --interactive

# Interactive cleanup
qdrant-loader clean --interactive
```

### Logging Options

#### `--log-level`

Set logging level.

```bash
# Debug logging
qdrant-loader load --log-level DEBUG

# Error logging only
qdrant-loader load --log-level ERROR

# Custom logging
qdrant-loader load --log-level INFO
```

**Options**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

#### `--log-file`

Specify log file.

```bash
# Log to file
qdrant-loader load --log-file /var/log/qdrant-loader.log

# Log to stdout (default)
qdrant-loader load --log-file -

# No logging
qdrant-loader load --log-file /dev/null
```

## 📋 Option Combinations and Patterns

### Common Combinations

```bash
# Production load with monitoring
qdrant-loader load \
  --config production.yaml \
  --verbose \
  --progress \
  --stats \
  --log-file /var/log/qdrant-loader.log

# Development search with debugging
qdrant-loader search "API docs" \
  --verbose \
  --show-metadata \
  --snippets \
  --output json

# Maintenance with safety
qdrant-loader clean \
  --dry-run \
  --backup-before \
  --confirm \
  --verbose

# Batch processing with optimization
qdrant-loader load \
  --batch-size 500 \
  --parallel-workers 8 \
  --memory-limit 4GB \
  --optimize
```

### Environment-Specific Patterns

```bash
# Development
qdrant-loader --env development --verbose load --source local

# Testing
qdrant-loader --env testing --dry-run load --all-sources

# Production
qdrant-loader --env production --quiet --log-file /var/log/app.log load
```

## 🔗 Related Documentation

- **[CLI Commands Reference](./commands.md)** - Complete command documentation
- **[Scripting and Automation](./scripting-automation.md)** - Automation examples
- **[Configuration Reference](../configuration/config-file-reference.md)** - Configuration options
- **[Troubleshooting](../troubleshooting/common-issues.md)** - Common CLI issues

---

**CLI options mastery achieved!** 🎉

This comprehensive options reference provides detailed documentation for every command-line flag and parameter, enabling precise control over QDrant Loader's behavior for any use case.
