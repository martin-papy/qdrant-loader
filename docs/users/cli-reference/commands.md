# CLI Commands Reference

This comprehensive reference covers all QDrant Loader commands with detailed examples, use cases, and practical scenarios. The QDrant Loader CLI provides essential commands for data ingestion, configuration management, and project administration.

## 🎯 Overview

QDrant Loader provides a focused command-line interface for data ingestion and management. Commands are organized into logical groups for different aspects of the system.

### Available Commands

```text
📊 Data Management - init, ingest
🔧 Configuration - config (includes project information)
```

## 📊 Data Management Commands

### `qdrant-loader init`

Initialize QDrant collection and prepare for data ingestion.

#### Basic Usage

```bash
# Initialize QDrant collection with workspace
qdrant-loader init --workspace .

# Initialize with specific configuration
qdrant-loader init --config production.yaml --env production.env
```

#### Advanced Options

```bash
# Force reinitialization (recreate collection)
qdrant-loader init --workspace . --force

# Initialize with debug logging
qdrant-loader init --workspace . --log-level DEBUG

# Initialize with custom configuration files
qdrant-loader init --config /path/to/config.yaml --env /path/to/.env
```

#### Options for Init Command

- `--workspace PATH` - Workspace directory containing config.yaml and .env files
- `--config PATH` - Path to configuration file
- `--env PATH` - Path to environment file
- `--force` - Force reinitialization of existing collection
- `--log-level LEVEL` - Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

#### Workspace Mode

```bash
# Initialize in workspace mode (recommended)
mkdir my-workspace && cd my-workspace

# Download configuration templates
curl -o config.yaml https://raw.githubusercontent.com/martin-papy/qdrant-loader/main/packages/qdrant-loader/conf/config.template.yaml
curl -o .env https://raw.githubusercontent.com/martin-papy/qdrant-loader/main/packages/qdrant-loader/conf/.env.template

# Edit configuration files with your settings
# Then initialize
qdrant-loader init --workspace .
```

### `qdrant-loader ingest`

Process and load data from configured sources into QDrant.

#### Basic Ingestion Usage

```bash
# Ingest all configured sources with workspace
qdrant-loader ingest --workspace .

# Ingest with specific configuration
qdrant-loader ingest --config production.yaml --env production.env
```

#### Source Filtering

```bash
# Ingest specific project
qdrant-loader ingest --workspace . --project my-project

# Ingest specific source type from all projects
qdrant-loader ingest --workspace . --source-type git

# Ingest specific source type from specific project
qdrant-loader ingest --workspace . --project my-project --source-type confluence

# Ingest specific source from specific project
qdrant-loader ingest --workspace . --project my-project --source-type git --source my-repo
```

#### Advanced Ingestion Options

```bash
# Ingest with debug logging
qdrant-loader ingest --workspace . --log-level DEBUG

# Ingest with performance profiling
qdrant-loader ingest --workspace . --profile

# Force full re-ingestion (bypass change detection)
qdrant-loader ingest --workspace . --force

# Combine options
qdrant-loader ingest --workspace . --project my-project --source-type git --force --profile
```

#### Options for Ingest Command

- `--workspace PATH` - Workspace directory containing config.yaml and .env files
- `--config PATH` - Path to configuration file
- `--env PATH` - Path to environment file
- `--project TEXT` - Project ID to process
- `--source-type TEXT` - Source type to process (e.g., confluence, jira, git)
- `--source TEXT` - Source name to process
- `--log-level LEVEL` - Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `--profile / --no-profile` - Run under cProfile and save output to 'profile.out' for performance analysis
- `--force` - Force processing of all documents, bypassing change detection

#### Source Types

The following source types are supported:

- **`git`** - Git repositories
- **`confluence`** - Confluence Cloud/Data Center
- **`jira`** - JIRA Cloud/Data Center
- **`localfile`** - Local files and directories
- **`publicdocs`** - Public documentation websites

## 🔧 Configuration Commands

### `qdrant-loader config`

Display current configuration and validate settings.

#### Basic Configuration Usage

```bash
# Show configuration with workspace
qdrant-loader config --workspace .

# Show configuration with specific files
qdrant-loader config --config custom-config.yaml --env custom.env
```

#### Configuration Display

```bash
# Display configuration in JSON format
qdrant-loader config --workspace .

# Display with debug logging to see configuration loading process
qdrant-loader config --workspace . --log-level DEBUG

# Display configuration from specific files
qdrant-loader config --config /etc/qdrant-loader/config.yaml --env /etc/qdrant-loader/.env
```

#### Options for Config Command

- `--workspace PATH` - Workspace directory containing config.yaml and .env files
- `--config PATH` - Path to configuration file
- `--env PATH` - Path to environment file
- `--log-level LEVEL` - Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

#### Configuration Validation

The `config` command automatically validates the configuration and will show any errors or warnings. Use this to troubleshoot configuration issues:

```bash
# Validate configuration without processing
qdrant-loader config --workspace .

# Validate specific configuration files
qdrant-loader config --config test-config.yaml --env test.env
```

## 📁 Project Information (via Config Command)

> **Note**: Dedicated project management commands (`project list`, `project status`, `project validate`) are not currently available in the CLI. All project information is accessible through the `config` command.

### Project Information Display

The `qdrant-loader config` command displays comprehensive project information including:

#### Basic Project Information Usage

```bash
# Display all projects and their configuration
qdrant-loader config --workspace .

# Display configuration with specific files
qdrant-loader config --config config.yaml --env .env
```

#### Project Information Included

The config command shows:

- **Project ID** - Unique identifier for each project
- **Display Name** - Human-readable project name  
- **Description** - Project description
- **Collection** - QDrant collection name used
- **Sources** - Configured data sources for each project
- **Configuration Status** - Validation results for each project

#### Configuration Validation

The `config` command automatically validates all project configurations:

```bash
# Validate all project configurations
qdrant-loader config --workspace .

# Validate with debug output for troubleshooting
qdrant-loader config --workspace . --log-level DEBUG
```

#### Validation Checks Performed

The config command validates:

- **Configuration syntax** - YAML structure and required fields
- **Source configurations** - Required fields for each source type  
- **Project structure** - Valid project definitions
- **Collection names** - Valid QDrant collection naming
- **Environment variables** - Required variables are set

## ⚙️ Common Options

Most commands support these common options:

### Configuration Options

```bash
# Workspace mode (recommended)
--workspace PATH # Workspace directory containing config.yaml and .env

# Individual file mode
--config PATH # Path to configuration file
--env PATH # Path to environment file

# Logging
--log-level LEVEL # Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
```

### Help and Version

```bash
# Get help
qdrant-loader --help # General help
qdrant-loader init --help # Command-specific help
qdrant-loader config --help # Configuration command help

# Get version
qdrant-loader --version # Show version information
```

## 🎯 Common Workflows

### Initial Setup

```bash
# 1. Create workspace
mkdir my-qdrant-workspace && cd my-qdrant-workspace

# 2. Get configuration templates
curl -o config.yaml https://raw.githubusercontent.com/martin-papy/qdrant-loader/main/packages/qdrant-loader/conf/config.template.yaml
curl -o .env https://raw.githubusercontent.com/martin-papy/qdrant-loader/main/packages/qdrant-loader/conf/.env.template

# 3. Edit configuration files
# Edit config.yaml and .env with your settings

# 4. Validate configuration
qdrant-loader config --workspace .

# 5. Initialize collection
qdrant-loader init --workspace .

# 6. Ingest data
qdrant-loader ingest --workspace .
```

### Development Workflow

```bash
# Check project configuration
qdrant-loader config --workspace .

# Validate before processing
qdrant-loader config --workspace .

# Process with debug logging
qdrant-loader ingest --workspace . --log-level DEBUG

# Check project status
qdrant-loader config --workspace .
```

### Production Workflow

```bash
# Use specific configuration files
qdrant-loader ingest --config /etc/qdrant-loader/config.yaml \
  --env /etc/qdrant-loader/.env

# Process specific project
qdrant-loader ingest --workspace . --project production-docs

# Process specific source type
qdrant-loader ingest --workspace . --source-type git

# Full refresh workflow
qdrant-loader init --workspace . --force
qdrant-loader ingest --workspace .
```

### Performance Analysis

```bash
# Profile ingestion performance
qdrant-loader ingest --workspace . --profile

# Force full re-processing for benchmarking
qdrant-loader ingest --workspace . --force --profile

# Process specific project with profiling
qdrant-loader ingest --workspace . --project my-project --profile
```

## 🔄 Exit Codes

All commands use standard exit codes:

| Code | Meaning | Description |
|------|---------|-------------|
| `0` | Success | Command completed successfully |
| `1` | General error | Command failed due to an error |
| `2` | Configuration error | Invalid configuration or missing settings |
| `3` | Connection error | Failed to connect to data sources or QDrant |
| `4` | Processing error | Error during data processing |

## 📚 Related Documentation

- **[CLI Reference Overview](./README.md)** - CLI overview and quick reference
- **[Configuration Reference](../configuration/)** - Configuration file options
- **[Troubleshooting](../troubleshooting/)** - Common CLI issues and solutions

---

**Ready to use the commands?** Start with `qdrant-loader --help` to explore the available options, or follow the [Getting Started Guide](../../getting-started/) for a complete walkthrough.
