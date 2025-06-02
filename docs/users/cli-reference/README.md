# Command Line Interface (CLI) Reference

QDrant Loader provides a comprehensive command-line interface for managing data ingestion, configuration, and project management. This section covers all available commands, options, and usage patterns.

## 🎯 CLI Overview

The `qdrant-loader` command is your primary interface for:

- **Data ingestion** - Loading content from configured sources
- **Configuration management** - Viewing and validating settings
- **Project management** - Managing multi-project configurations
- **Troubleshooting** - Debugging and testing configurations

## 🚀 Quick Reference

### Essential Commands

```bash
# Initialize QDrant collection
qdrant-loader --workspace . init

# Load data from all configured sources
qdrant-loader --workspace . ingest

# View configuration
qdrant-loader --workspace . config

# List all projects
qdrant-loader project --workspace . list

# Get help
qdrant-loader --help
```

### Common Options

| Option | Short | Description | Example |
|--------|-------|-------------|---------|
| `--workspace` | | Workspace directory | `--workspace /path/to/workspace` |
| `--config` | | Configuration file | `--config custom-config.yaml` |
| `--env` | | Environment file | `--env production.env` |
| `--log-level` | | Set logging level | `--log-level DEBUG` |

## 📚 Command Categories

### 🔧 Available Commands

Complete reference for all available commands:

- **`init`** - Initialize QDrant collection and workspace
- **`ingest`** - Process and load data from sources
- **`config`** - View current configuration
- **`project list`** - List all configured projects
- **`project status`** - Show project status and statistics
- **`project validate`** - Validate project configurations

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

# 6. Check project status
qdrant-loader project --workspace . status
```

### Development Workflow

```bash
# Validate project configurations
qdrant-loader project --workspace . validate

# Process with verbose logging
qdrant-loader --workspace . --log-level DEBUG ingest

# Check project list
qdrant-loader project --workspace . list
```

### Production Workflow

```bash
# Use specific configuration files
qdrant-loader --config /etc/qdrant-loader/config.yaml \
              --env /etc/qdrant-loader/.env \
              ingest

# Process specific project
qdrant-loader --workspace . ingest --project my-project

# Process specific source type
qdrant-loader --workspace . ingest --source-type git

# Force full re-processing
qdrant-loader --workspace . init --force
qdrant-loader --workspace . ingest
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
| `--log-level LEVEL` | Set logging level | `INFO` | `--log-level DEBUG` |

### Processing Options (for ingest command)

| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `--project` | Process specific project | All projects | `--project my-project` |
| `--source-type` | Process specific source type | All types | `--source-type git` |
| `--source` | Process specific source | All sources | `--source my-repo` |
| `--profile` | Enable performance profiling | False | `--profile` |

## 🎯 Command Examples

### Initialization

```bash
# Basic initialization
qdrant-loader --workspace . init

# Force reinitialization (recreate collection)
qdrant-loader --workspace . init --force
```

### Data Ingestion

```bash
# Basic ingestion (all projects)
qdrant-loader --workspace . ingest

# Ingest specific project
qdrant-loader --workspace . ingest --project my-project

# Ingest specific source type from all projects
qdrant-loader --workspace . ingest --source-type git

# Ingest specific source type from specific project
qdrant-loader --workspace . ingest --project my-project --source-type confluence

# Ingest specific source from specific project
qdrant-loader --workspace . ingest --project my-project --source-type git --source my-repo

# Force full re-ingestion
qdrant-loader --workspace . init --force
qdrant-loader --workspace . ingest
```

### Project Management

```bash
# List all projects
qdrant-loader project --workspace . list

# List projects in JSON format
qdrant-loader project --workspace . list --format json

# Show status for all projects
qdrant-loader project --workspace . status

# Show status for specific project
qdrant-loader project --workspace . status --project-id my-project

# Validate all project configurations
qdrant-loader project --workspace . validate

# Validate specific project
qdrant-loader project --workspace . validate --project-id my-project
```

### Configuration Management

```bash
# View current configuration
qdrant-loader --workspace . config

# View configuration with specific files
qdrant-loader --config custom-config.yaml --env custom.env config
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
  qdrant-loader --workspace . ingest --source-type localfile
fi
```

### Error Handling

```bash
# Robust processing with error handling
if ! qdrant-loader project --workspace . validate; then
  echo "Configuration validation failed"
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

# Debug specific project
qdrant-loader --workspace . --log-level DEBUG ingest --project my-project
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

# Enable profiling
qdrant-loader --workspace . ingest --profile
```

### Configuration Validation

```bash
# Validate all project configurations
qdrant-loader project --workspace . validate

# Validate specific project
qdrant-loader project --workspace . validate --project-id my-project

# Check project status
qdrant-loader project --workspace . status --format json
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

### Using Exit Codes in Scripts

```bash
#!/bin/bash

# Check exit codes and handle errors
qdrant-loader project --workspace . validate
case $? in
  0) echo "Configuration valid" ;;
  2) echo "Configuration error"; exit 1 ;;
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
qdrant-loader project --workspace . list

# JSON output for scripting
qdrant-loader project --workspace . list --format json
qdrant-loader project --workspace . status --format json

# Configuration output
qdrant-loader --workspace . config
```

### Logging Output

```bash
# Debug logging
qdrant-loader --workspace . --log-level DEBUG ingest

# Info logging (default)
qdrant-loader --workspace . --log-level INFO ingest

# Warning and error only
qdrant-loader --workspace . --log-level WARNING ingest
```

## 🔧 Shell Integration

### Aliases and Functions

```bash
# Useful aliases
alias ql='qdrant-loader --workspace .'
alias qli='qdrant-loader --workspace . ingest'
alias qlp='qdrant-loader project --workspace .'
alias qlc='qdrant-loader --workspace . config'

# Useful functions
function ql-quick() {
  qdrant-loader project --workspace . validate && \
  qdrant-loader --workspace . ingest
}

function ql-status() {
  qdrant-loader project --workspace . status
}
```

## 📚 Related Documentation

- **[Configuration Reference](../configuration/)** - Configuration file options
- **[Troubleshooting](../troubleshooting/)** - Common CLI issues and solutions

## 🆘 Getting Help

### Built-in Help

```bash
# General help
qdrant-loader --help

# Command-specific help
qdrant-loader ingest --help
qdrant-loader project --help
qdrant-loader project list --help
```

### Community Support

- **[GitHub Issues](https://github.com/martin-papy/qdrant-loader/issues)** - Report CLI bugs
- **[GitHub Discussions](https://github.com/martin-papy/qdrant-loader/discussions)** - Ask CLI questions

---

**Master the QDrant Loader CLI!** 🚀

This comprehensive CLI provides everything you need to manage your knowledge base ingestion and processing. Start with the basic commands and gradually explore the advanced features as your needs grow.
