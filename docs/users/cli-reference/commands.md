# CLI Commands Reference

This comprehensive reference covers all QDrant Loader commands with detailed examples, use cases, and practical scenarios. The QDrant Loader CLI provides essential commands for data ingestion, configuration management, and project administration.

## 🎯 Overview

QDrant Loader provides a focused command-line interface for data ingestion and management. Commands are organized into logical groups for different aspects of the system.

### Available Commands

```
📊 Data Management    - init, ingest
🔧 Configuration     - config
📁 Project Management - project list, project status, project validate
```

## 📊 Data Management Commands

### `qdrant-loader init`

Initialize QDrant collection and prepare for data ingestion.

#### Basic Usage

```bash
# Initialize QDrant collection
qdrant-loader init

# Initialize with workspace
qdrant-loader --workspace . init

# Initialize with specific configuration
qdrant-loader --config production.yaml --env production.env init
```

#### Advanced Options

```bash
# Force reinitialization (recreate collection)
qdrant-loader --workspace . init --force

# Initialize with debug logging
qdrant-loader --workspace . --log-level DEBUG init

# Initialize with custom configuration files
qdrant-loader --config /path/to/config.yaml --env /path/to/.env init
```

#### Workspace Mode

```bash
# Initialize in workspace mode (recommended)
mkdir my-workspace && cd my-workspace

# Download configuration templates
curl -o config.yaml https://raw.githubusercontent.com/martin-papy/qdrant-loader/main/packages/qdrant-loader/conf/config.template.yaml
curl -o .env https://raw.githubusercontent.com/martin-papy/qdrant-loader/main/packages/qdrant-loader/conf/.env.template

# Edit configuration files with your settings
# Then initialize
qdrant-loader --workspace . init
```

### `qdrant-loader ingest`

Process and load data from configured sources into QDrant.

#### Basic Usage

```bash
# Ingest all configured sources
qdrant-loader ingest

# Ingest with workspace
qdrant-loader --workspace . ingest

# Ingest with specific configuration
qdrant-loader --config production.yaml --env production.env ingest
```

#### Source Filtering

```bash
# Ingest specific project
qdrant-loader --workspace . ingest --project my-project

# Ingest specific source type from all projects
qdrant-loader --workspace . ingest --source-type git

# Ingest specific source type from specific project
qdrant-loader --workspace . ingest --project my-project --source-type confluence

# Ingest specific source from specific project
qdrant-loader --workspace . ingest --project my-project --source-type git --source my-repo
```

#### Advanced Options

```bash
# Ingest with debug logging
qdrant-loader --workspace . --log-level DEBUG ingest

# Ingest with performance profiling
qdrant-loader --workspace . ingest --profile

# Force full re-ingestion
qdrant-loader --workspace . init --force
qdrant-loader --workspace . ingest
```

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

#### Basic Usage

```bash
# Show current configuration
qdrant-loader config

# Show configuration with workspace
qdrant-loader --workspace . config

# Show configuration with specific files
qdrant-loader --config custom-config.yaml --env custom.env config
```

#### Configuration Display

```bash
# Display configuration in JSON format
qdrant-loader --workspace . config

# Display with debug logging to see configuration loading process
qdrant-loader --workspace . --log-level DEBUG config

# Display configuration from specific files
qdrant-loader --config /etc/qdrant-loader/config.yaml --env /etc/qdrant-loader/.env config
```

#### Configuration Validation

The `config` command automatically validates the configuration and will show any errors or warnings. Use this to troubleshoot configuration issues:

```bash
# Validate configuration without processing
qdrant-loader --workspace . config

# Validate specific configuration files
qdrant-loader --config test-config.yaml --env test.env config
```

## 📁 Project Management Commands

### `qdrant-loader project list`

List all configured projects in the workspace.

#### Basic Usage

```bash
# List all projects
qdrant-loader project --workspace . list

# List projects with specific configuration
qdrant-loader project --config config.yaml --env .env list
```

#### Output Formats

```bash
# List projects in table format (default)
qdrant-loader project --workspace . list

# List projects in JSON format
qdrant-loader project --workspace . list --format json

# List projects in JSON format for scripting
qdrant-loader project --workspace . list --format json | jq '.[] | .project_id'
```

#### Project Information

The list command shows:

- **Project ID** - Unique identifier for the project
- **Display Name** - Human-readable project name
- **Description** - Project description
- **Collection** - QDrant collection name used
- **Sources** - Number of configured data sources

### `qdrant-loader project status`

Show project status including configuration and statistics.

#### Basic Usage

```bash
# Show status for all projects
qdrant-loader project --workspace . status

# Show status for specific project
qdrant-loader project --workspace . status --project-id my-project
```

#### Output Formats

```bash
# Show status in table format (default)
qdrant-loader project --workspace . status

# Show status in JSON format
qdrant-loader project --workspace . status --format json

# Show status for specific project in JSON
qdrant-loader project --workspace . status --project-id my-project --format json
```

#### Status Information

The status command shows:

- **Project ID** - Unique identifier
- **Display Name** - Human-readable name
- **Description** - Project description
- **Collection** - QDrant collection name
- **Sources** - Number of configured sources
- **Documents** - Document count (requires database)
- **Latest Ingestion** - Last ingestion timestamp (requires database)

### `qdrant-loader project validate`

Validate project configurations for correctness.

#### Basic Usage

```bash
# Validate all projects
qdrant-loader project --workspace . validate

# Validate specific project
qdrant-loader project --workspace . validate --project-id my-project
```

#### Validation Process

```bash
# Validate with debug output
qdrant-loader project --workspace . --log-level DEBUG validate

# Validate specific project with detailed output
qdrant-loader project --workspace . validate --project-id my-project
```

#### Validation Checks

The validate command checks:

- **Configuration syntax** - YAML structure and required fields
- **Source configurations** - Required fields for each source type
- **Project structure** - Valid project definitions
- **Collection names** - Valid QDrant collection naming

## 🔧 Global Options

All commands support these global options:

### Configuration Options

```bash
# Workspace mode (recommended)
--workspace PATH          # Workspace directory containing config.yaml and .env

# Individual file mode
--config PATH             # Path to configuration file
--env PATH                # Path to environment file

# Logging
--log-level LEVEL         # Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
```

### Help and Version

```bash
# Get help
qdrant-loader --help                    # General help
qdrant-loader init --help               # Command-specific help
qdrant-loader project --help            # Project command help
qdrant-loader project list --help       # Subcommand help

# Get version
qdrant-loader --version                 # Show version information
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
qdrant-loader project --workspace . validate

# 5. Initialize collection
qdrant-loader --workspace . init

# 6. Ingest data
qdrant-loader --workspace . ingest
```

### Development Workflow

```bash
# Check project configuration
qdrant-loader project --workspace . list

# Validate before processing
qdrant-loader project --workspace . validate

# Process with debug logging
qdrant-loader --workspace . --log-level DEBUG ingest

# Check project status
qdrant-loader project --workspace . status
```

### Production Workflow

```bash
# Use specific configuration files
qdrant-loader --config /etc/qdrant-loader/config.yaml \
              --env /etc/qdrant-loader/.env \
              ingest

# Process specific project
qdrant-loader --workspace . ingest --project production-docs

# Process specific source type
qdrant-loader --workspace . ingest --source-type git

# Full refresh workflow
qdrant-loader --workspace . init --force
qdrant-loader --workspace . ingest
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
