# Command Line Interface (CLI) Reference

QDrant Loader provides a comprehensive command-line interface for managing data ingestion, configuration, and project management. This section covers all available commands, options, and usage patterns.

## 🎯 CLI Overview

The `qdrant-loader` command is your primary interface for:

- **Data ingestion** - Loading content from configured sources
- **Configuration management** - Viewing and validating settings (includes project information)
- **Collection management** - Initializing QDrant collections
- **Troubleshooting** - Debugging and testing configurations

## 🚀 Quick Reference

### Essential Commands

```bash
# Initialize QDrant collection
qdrant-loader init --workspace .

# Load data from all configured sources
qdrant-loader ingest --workspace .

# View configuration and project information
qdrant-loader config --workspace .

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
- **`config`** - View current configuration (includes all project information and validation)

### 🤖 Scripting and Automation (coming later)

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
qdrant-loader init --workspace .

# 5. Load data
qdrant-loader ingest --workspace .

# 6. Check configuration and project status
qdrant-loader config --workspace .
```

### Development Workflow

```bash
# Validate configuration (includes all projects)
qdrant-loader config --workspace .

# Process with verbose logging
qdrant-loader ingest --workspace . --log-level DEBUG

# Check configuration and project information
qdrant-loader config --workspace .
```

### Production Workflow

```bash
# Use specific configuration files
qdrant-loader ingest --config /etc/qdrant-loader/config.yaml --env /etc/qdrant-loader/.env

# Process specific project
qdrant-loader ingest --workspace . --project my-project

# Process specific source type
qdrant-loader ingest --workspace . --source-type git

# Force full re-processing
qdrant-loader init --workspace . --force
qdrant-loader ingest --workspace .
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
qdrant-loader init --workspace .

# Force reinitialization (recreate collection)
qdrant-loader init --workspace . --force
```

### Data Ingestion

```bash
# Basic ingestion (all projects)
qdrant-loader ingest --workspace .

# Ingest specific project
qdrant-loader ingest --workspace . --project my-project

# Ingest specific source type from all projects
qdrant-loader ingest --workspace . --source-type git

# Ingest specific source type from specific project
qdrant-loader ingest --workspace . --project my-project --source-type confluence

# Ingest specific source from specific project
qdrant-loader ingest --workspace . --project my-project --source-type git --source my-repo

# Force full re-ingestion
qdrant-loader init --workspace . --force
qdrant-loader ingest --workspace .
```

### Configuration and Project Information

> **Note**: Dedicated project management commands (`project list`, `project status`, `project validate`) are not currently available. All project information is accessible through the `config` command.

```bash
# Display all configuration and project information
qdrant-loader config --workspace .

# Display configuration with debug logging
qdrant-loader config --workspace . --log-level DEBUG

# Use specific configuration files
qdrant-loader config --config custom-config.yaml --env custom.env
```

## 🔍 Advanced Usage

### Environment Variable Overrides

```bash
# Override configuration with environment variables
QDRANT_URL=http://prod-qdrant:6333 \
QDRANT_COLLECTION_NAME=prod_docs \
qdrant-loader ingest --workspace .

# Use different LLM configuration
LLM_PROVIDER=openai \
LLM_API_KEY=sk-proj-production-key \
LLM_EMBEDDING_MODEL=text-embedding-3-small \
qdrant-loader ingest --workspace .
```

### Multiple Workspaces

```bash
# Process multiple workspaces
for workspace in /data/workspaces/*/; do
  echo "Processing $workspace"
  qdrant-loader ingest --workspace "$workspace"
done

# Parallel processing of workspaces
find /data/workspaces -maxdepth 1 -type d | xargs -I {} -P 4 qdrant-loader ingest --workspace {}
```

### Conditional Processing

```bash
# Only process if configuration changed
if [ config.yaml -nt data/qdrant-loader.db ]; then
  qdrant-loader ingest --workspace .
fi

# Process based on time
if [ $(find . -name "*.md" -mtime -1 | wc -l) -gt 0 ]; then
  qdrant-loader ingest --workspace . --source-type localfile
fi
```

### Error Handling

```bash
# Robust processing with error handling
if ! qdrant-loader config --workspace .; then
  echo "Configuration validation failed"
  exit 1
fi

if ! qdrant-loader ingest --workspace .; then
  echo "Ingestion failed"
  exit 1
fi

echo "Processing completed successfully"
```

## 🧪 Testing and Debugging

### Debug Mode

```bash
# Enable debug logging
qdrant-loader ingest --workspace . --log-level DEBUG

# Debug specific project
qdrant-loader ingest --workspace . --log-level DEBUG --project my-project
```

### Performance Testing

```bash
# Time processing
time qdrant-loader ingest --workspace .

# Monitor resource usage
top -p $(pgrep -f qdrant-loader) &
qdrant-loader ingest --workspace .

# Memory usage tracking
/usr/bin/time -v qdrant-loader ingest --workspace .

# Enable profiling
qdrant-loader ingest --workspace . --profile
```

### Configuration Validation

```bash
# Validate configuration (includes all projects)
qdrant-loader config --workspace .

# Display configuration with debug logging
qdrant-loader config --workspace . --log-level DEBUG
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
qdrant-loader config --workspace .
case $? in
  0) echo "Configuration valid" ;;
  2) echo "Configuration error"; exit 1 ;;
  *) echo "Unknown error"; exit 1 ;;
esac

qdrant-loader ingest --workspace .
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
qdrant-loader config --workspace .

# Configuration with debug information
qdrant-loader config --workspace . --log-level DEBUG
```

### Logging Output

```bash
# Debug logging
qdrant-loader ingest --workspace . --log-level DEBUG

# Info logging (default)
qdrant-loader ingest --workspace . --log-level INFO

# Warning and error only
qdrant-loader ingest --workspace . --log-level WARNING
```

## 🔧 Shell Integration

### Aliases and Functions

```bash
# Useful aliases
alias ql='qdrant-loader --workspace .'
alias qli='qdrant-loader ingest --workspace .'
alias qlp='qdrant-loader config --workspace .'
alias qlc='qdrant-loader config --workspace .'

# Useful functions
function ql-quick() {
  qdrant-loader config --workspace . && \
  qdrant-loader ingest --workspace .
}

function ql-status() {
  qdrant-loader config --workspace .
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
qdrant-loader init --help
qdrant-loader ingest --help
qdrant-loader config --help
```

### Community Support

- **[GitHub Issues](https://github.com/martin-papy/qdrant-loader/issues)** - Report CLI bugs
- **[GitHub Discussions](https://github.com/martin-papy/qdrant-loader/discussions)** - Ask CLI questions

---

**Master the QDrant Loader CLI!** 🚀

This comprehensive CLI provides everything you need to manage your knowledge base ingestion and processing. Start with the basic commands and gradually explore the advanced features as your needs grow.
