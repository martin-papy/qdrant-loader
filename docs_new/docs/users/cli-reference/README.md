# Command Line Interface (CLI) Reference

QDrant Loader provides a comprehensive command-line interface for managing data ingestion, configuration, and monitoring. This section covers all available commands, options, and usage patterns.

## 🎯 CLI Overview

The `qdrant-loader` command is your primary interface for:

- **Data ingestion** - Loading content from configured sources
- **Configuration management** - Validating and testing settings
- **Status monitoring** - Checking processing status and statistics
- **Troubleshooting** - Debugging and testing connections

## 🚀 Quick Reference

### Essential Commands

```bash
# Initialize QDrant collection
qdrant-loader --workspace . init

# Load data from all configured sources
qdrant-loader --workspace . ingest

# Check processing status
qdrant-loader --workspace . status

# View configuration
qdrant-loader --workspace . config

# Get help
qdrant-loader --help
```

### Common Options

| Option | Short | Description | Example |
|--------|-------|-------------|---------|
| `--workspace` | `-w` | Workspace directory | `--workspace /path/to/workspace` |
| `--config` | `-c` | Configuration file | `--config custom-config.yaml` |
| `--env` | `-e` | Environment file | `--env production.env` |
| `--verbose` | `-v` | Verbose output | `--verbose` |
| `--dry-run` | `-n` | Show what would be done | `--dry-run` |

## 📚 Command Categories

### 🔧 [Commands Reference](./commands.md)

Complete reference for all available commands:

- **`init`** - Initialize QDrant collection and workspace
- **`ingest`** - Process and load data from sources
- **`status`** - Check processing status and statistics
- **`config`** - View and validate configuration
- **`test-connections`** - Test data source connectivity
- **`validate`** - Validate configuration syntax
- **`stats`** - View detailed processing statistics

### 🤖 [Scripting and Automation](./scripting-automation.md)

Using QDrant Loader in scripts and automated workflows:

- **Batch processing** - Processing multiple workspaces
- **CI/CD integration** - Automated data updates
- **Monitoring scripts** - Health checks and alerts
- **Error handling** - Robust automation patterns

## 🎯 Usage Patterns

### Basic Workflow

```bash
# 1. Set up workspace
mkdir my-workspace && cd my-workspace

# 2. Download configuration templates
curl -o config.yaml https://raw.githubusercontent.com/martin-papy/qdrant-loader/main/packages/qdrant-loader/conf/config.template.yaml
curl -o .env https://raw.githubusercontent.com/martin-papy/qdrant-loader/main/packages/qdrant-loader/conf/.env.template

# 3. Edit configuration files
# Edit config.yaml and .env with your settings

# 4. Initialize collection
qdrant-loader --workspace . init

# 5. Load data
qdrant-loader --workspace . ingest

# 6. Check status
qdrant-loader --workspace . status
```

### Development Workflow

```bash
# Validate configuration before processing
qdrant-loader --workspace . validate

# Test data source connections
qdrant-loader --workspace . test-connections

# Dry run to see what would be processed
qdrant-loader --workspace . --dry-run ingest

# Process with verbose logging
qdrant-loader --workspace . --verbose ingest

# Check detailed statistics
qdrant-loader --workspace . stats --verbose
```

### Production Workflow

```bash
# Use specific configuration files
qdrant-loader --config /etc/qdrant-loader/config.yaml \
              --env /etc/qdrant-loader/.env \
              ingest

# Log to file
qdrant-loader --workspace /data/qdrant-workspace \
              --log-file /var/log/qdrant-loader.log \
              ingest

# Process specific sources only
qdrant-loader --workspace . ingest --sources git,confluence

# Force full re-processing
qdrant-loader --workspace . ingest --force
```

## 🔧 Global Options

### Workspace and Configuration

| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `--workspace PATH` | Workspace directory | Current directory | `--workspace /data/workspace` |
| `--config FILE` | Configuration file | `config.yaml` | `--config prod-config.yaml` |
| `--env FILE` | Environment file | `.env` | `--env production.env` |

### Output and Logging

| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `--verbose` | Enable verbose output | False | `--verbose` |
| `--quiet` | Suppress non-error output | False | `--quiet` |
| `--log-level LEVEL` | Set logging level | `INFO` | `--log-level DEBUG` |
| `--log-file FILE` | Log to file | None | `--log-file app.log` |
| `--no-color` | Disable colored output | False | `--no-color` |

### Processing Options

| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `--dry-run` | Show what would be done | False | `--dry-run` |
| `--force` | Force full re-processing | False | `--force` |
| `--sources LIST` | Process specific sources | All | `--sources git,confluence` |
| `--limit N` | Limit number of items | None | `--limit 100` |

## 🎯 Command Examples

### Initialization

```bash
# Basic initialization
qdrant-loader --workspace . init

# Initialize with custom collection name
qdrant-loader --workspace . init --collection-name my_docs

# Initialize and create collection if it doesn't exist
qdrant-loader --workspace . init --create-collection

# Initialize with specific vector size
qdrant-loader --workspace . init --vector-size 1536
```

### Data Ingestion

```bash
# Basic ingestion
qdrant-loader --workspace . ingest

# Ingest specific sources
qdrant-loader --workspace . ingest --sources git
qdrant-loader --workspace . ingest --sources git,confluence,jira

# Ingest with limits
qdrant-loader --workspace . ingest --limit 50

# Force full re-ingestion
qdrant-loader --workspace . ingest --force

# Dry run to see what would be processed
qdrant-loader --workspace . --dry-run ingest
```

### Status and Monitoring

```bash
# Basic status
qdrant-loader --workspace . status

# Detailed status with statistics
qdrant-loader --workspace . status --verbose

# Status for specific sources
qdrant-loader --workspace . status --sources git

# Processing statistics
qdrant-loader --workspace . stats

# Detailed statistics
qdrant-loader --workspace . stats --verbose
```

### Configuration Management

```bash
# View current configuration
qdrant-loader --workspace . config

# Validate configuration
qdrant-loader --workspace . validate

# Test data source connections
qdrant-loader --workspace . test-connections

# Test specific sources
qdrant-loader --workspace . test-connections --sources confluence,jira
```

## 🔍 Advanced Usage

### Environment Variable Overrides

```bash
# Override configuration with environment variables
QDRANT_URL=http://prod-qdrant:6333 \
QDRANT_COLLECTION_NAME=prod_docs \
qdrant-loader --workspace . ingest

# Use different OpenAI API key
OPENAI_API_KEY=sk-proj-production-key \
qdrant-loader --workspace . ingest
```

### Multiple Workspaces

```bash
# Process multiple workspaces
for workspace in /data/workspaces/*/; do
  echo "Processing $workspace"
  qdrant-loader --workspace "$workspace" ingest
done

# Parallel processing of workspaces
find /data/workspaces -maxdepth 1 -type d | \
  xargs -I {} -P 4 qdrant-loader --workspace {} ingest
```

### Conditional Processing

```bash
# Only process if configuration changed
if [ config.yaml -nt state.db ]; then
  qdrant-loader --workspace . ingest
fi

# Process based on time
if [ $(find . -name "*.md" -mtime -1 | wc -l) -gt 0 ]; then
  qdrant-loader --workspace . ingest --sources local_files
fi
```

### Error Handling

```bash
# Robust processing with error handling
if ! qdrant-loader --workspace . validate; then
  echo "Configuration validation failed"
  exit 1
fi

if ! qdrant-loader --workspace . test-connections; then
  echo "Connection test failed"
  exit 1
fi

if ! qdrant-loader --workspace . ingest; then
  echo "Ingestion failed"
  exit 1
fi

echo "Processing completed successfully"
```

## 🧪 Testing and Debugging

### Debug Mode

```bash
# Enable debug logging
qdrant-loader --workspace . --log-level DEBUG ingest

# Debug with file output
qdrant-loader --workspace . \
              --log-level DEBUG \
              --log-file debug.log \
              ingest

# Debug specific components
DEBUG_COMPONENTS=git,confluence \
qdrant-loader --workspace . --verbose ingest
```

### Performance Testing

```bash
# Time processing
time qdrant-loader --workspace . ingest

# Monitor resource usage
top -p $(pgrep -f qdrant-loader) &
qdrant-loader --workspace . ingest

# Memory usage tracking
/usr/bin/time -v qdrant-loader --workspace . ingest
```

### Connection Testing

```bash
# Test all connections
qdrant-loader --workspace . test-connections

# Test specific source types
qdrant-loader --workspace . test-connections --sources git
qdrant-loader --workspace . test-connections --sources confluence,jira

# Test with verbose output
qdrant-loader --workspace . --verbose test-connections
```

## 🔄 Exit Codes

QDrant Loader uses standard exit codes:

| Code | Meaning | Description |
|------|---------|-------------|
| `0` | Success | Command completed successfully |
| `1` | General error | Command failed due to an error |
| `2` | Configuration error | Invalid configuration or missing settings |
| `3` | Connection error | Failed to connect to data sources or QDrant |
| `4` | Processing error | Error during data processing |
| `5` | Validation error | Configuration validation failed |

### Using Exit Codes in Scripts

```bash
#!/bin/bash

# Check exit codes and handle errors
qdrant-loader --workspace . validate
case $? in
  0) echo "Configuration valid" ;;
  2) echo "Configuration error"; exit 1 ;;
  5) echo "Validation failed"; exit 1 ;;
  *) echo "Unknown error"; exit 1 ;;
esac

qdrant-loader --workspace . ingest
if [ $? -eq 0 ]; then
  echo "Ingestion successful"
else
  echo "Ingestion failed with exit code $?"
  exit 1
fi
```

## 📊 Output Formats

### Standard Output

```bash
# Human-readable output (default)
qdrant-loader --workspace . status

# JSON output for scripting
qdrant-loader --workspace . status --format json

# CSV output for analysis
qdrant-loader --workspace . stats --format csv

# YAML output
qdrant-loader --workspace . config --format yaml
```

### Logging Output

```bash
# Structured logging
qdrant-loader --workspace . --log-format json ingest

# Traditional logging
qdrant-loader --workspace . --log-format text ingest

# Custom log format
qdrant-loader --workspace . \
              --log-format "%(asctime)s [%(levelname)s] %(message)s" \
              ingest
```

## 🔧 Shell Integration

### Bash Completion

```bash
# Enable bash completion
eval "$(qdrant-loader --completion bash)"

# Add to .bashrc for permanent completion
echo 'eval "$(qdrant-loader --completion bash)"' >> ~/.bashrc
```

### Aliases and Functions

```bash
# Useful aliases
alias ql='qdrant-loader --workspace .'
alias qli='qdrant-loader --workspace . ingest'
alias qls='qdrant-loader --workspace . status'
alias qlc='qdrant-loader --workspace . config'

# Useful functions
function ql-quick() {
  qdrant-loader --workspace . validate && \
  qdrant-loader --workspace . ingest
}

function ql-status() {
  qdrant-loader --workspace . status --verbose
}
```

## 📚 Related Documentation

- **[Commands Reference](./commands.md)** - Detailed command documentation
- **[Scripting and Automation](./scripting-automation.md)** - Automation patterns and examples
- **[Configuration Reference](../configuration/)** - Configuration file options
- **[Troubleshooting](../troubleshooting/)** - Common CLI issues and solutions

## 🆘 Getting Help

### Built-in Help

```bash
# General help
qdrant-loader --help

# Command-specific help
qdrant-loader ingest --help
qdrant-loader status --help
qdrant-loader config --help

# Show version
qdrant-loader --version
```

### Community Support

- **[GitHub Issues](https://github.com/martin-papy/qdrant-loader/issues)** - Report CLI bugs
- **[GitHub Discussions](https://github.com/martin-papy/qdrant-loader/discussions)** - Ask questions
- **[CLI Examples](https://github.com/martin-papy/qdrant-loader/tree/main/examples/cli)** - Real-world usage examples

---

**Ready to use the CLI?** Start with the [Commands Reference](./commands.md) for detailed command documentation or check out [Scripting and Automation](./scripting-automation.md) for advanced usage patterns.
