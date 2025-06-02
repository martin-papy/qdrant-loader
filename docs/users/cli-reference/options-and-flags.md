# Options and Flags Reference

This reference documents all command-line options and flags available in QDrant Loader. Each option includes detailed descriptions, examples, and usage patterns based on the actual implementation.

## 🎯 Overview

QDrant Loader provides a focused set of command-line options that control configuration, logging, and workspace management. The CLI is designed for simplicity and reliability.

### Available Commands

- **`init`** - Initialize QDrant collection
- **`ingest`** - Process and load data from sources
- **`config`** - Display current configuration
- **`project list`** - List all configured projects
- **`project status`** - Show project status
- **`project validate`** - Validate project configurations

## 🔧 Global Options

These options are available for the main `qdrant-loader` command:

### `--log-level`

Set the logging level for all operations.

```bash
# Set logging level
qdrant-loader --log-level DEBUG init
qdrant-loader --log-level INFO ingest
qdrant-loader --log-level WARNING config
qdrant-loader --log-level ERROR project list
qdrant-loader --log-level CRITICAL project status
```

**Options**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
**Default**: `INFO`

### `--version`

Show version information.

```bash
# Show version
qdrant-loader --version
```

### `--help`

Show help information.

```bash
# Global help
qdrant-loader --help

# Command-specific help
qdrant-loader init --help
qdrant-loader ingest --help
qdrant-loader config --help
qdrant-loader project --help
```

## 📁 Configuration Options

These options control how QDrant Loader finds and loads configuration files:

### `--workspace`

Specify workspace directory containing `config.yaml` and `.env` files. All output will be stored in this directory.

```bash
# Use current directory as workspace
qdrant-loader --workspace . init

# Use specific workspace directory
qdrant-loader --workspace /path/to/workspace ingest

# Use relative workspace path
qdrant-loader --workspace ./my-workspace config
```

**Type**: Path to directory
**Auto-discovery**: Looks for `config.yaml` and `.env` in the workspace directory

### `--config`

Specify path to configuration file (alternative to workspace mode).

```bash
# Use specific config file
qdrant-loader --config /path/to/config.yaml init

# Use config file with custom .env
qdrant-loader --config config.yaml --env production.env ingest
```

**Type**: Path to existing YAML file
**Note**: Cannot be used with `--workspace`

### `--env`

Specify path to environment file (alternative to workspace mode).

```bash
# Use specific .env file
qdrant-loader --env /path/to/.env init

# Use with custom config
qdrant-loader --config config.yaml --env .env.production ingest
```

**Type**: Path to existing .env file
**Note**: Cannot be used with `--workspace`

## 🚀 Command-Specific Options

### `init` Command Options

#### `--force`

Force reinitialization of existing collection.

```bash
# Force recreate collection
qdrant-loader --workspace . init --force

# Normal initialization (fails if collection exists)
qdrant-loader --workspace . init
```

**Type**: Flag (no value)
**Default**: `false`

### `ingest` Command Options

#### `--project`

Process specific project only.

```bash
# Ingest specific project
qdrant-loader --workspace . ingest --project my-project

# Ingest all projects (default)
qdrant-loader --workspace . ingest
```

**Type**: String (project ID)

#### `--source-type`

Process specific source type only.

```bash
# Process only Git sources
qdrant-loader --workspace . ingest --source-type git

# Process only Confluence sources
qdrant-loader --workspace . ingest --source-type confluence

# Process specific source type within project
qdrant-loader --workspace . ingest --project my-project --source-type git
```

**Type**: String (source type identifier)
**Examples**: `git`, `confluence`, `jira`, `local`

#### `--source`

Process specific source only.

```bash
# Process specific source
qdrant-loader --workspace . ingest --source my-repo

# Process specific source within project and type
qdrant-loader --workspace . ingest --project my-project --source-type git --source my-repo
```

**Type**: String (source name)

#### `--profile` / `--no-profile`

Run ingestion under cProfile for performance analysis.

```bash
# Enable profiling (saves to profile.out)
qdrant-loader --workspace . ingest --profile

# Disable profiling (default)
qdrant-loader --workspace . ingest --no-profile
```

**Type**: Flag
**Default**: `--no-profile`
**Output**: Creates `profile.out` file for analysis

### Project Command Options

#### `--project-id`

Specify project ID for project-specific operations.

```bash
# Show status for specific project
qdrant-loader project --workspace . status --project-id my-project

# Validate specific project
qdrant-loader project --workspace . validate --project-id my-project
```

**Type**: String (project ID)
**Available for**: `status`, `validate` commands

#### `--format`

Specify output format for project commands.

```bash
# Table format (default)
qdrant-loader project --workspace . list --format table

# JSON format
qdrant-loader project --workspace . list --format json
qdrant-loader project --workspace . status --format json
```

**Type**: Choice
**Options**: `table`, `json`
**Default**: `table`
**Available for**: `list`, `status` commands

## 📋 Option Combinations and Patterns

### Workspace Mode (Recommended)

```bash
# Initialize workspace
qdrant-loader --workspace . init

# Ingest all data
qdrant-loader --workspace . ingest

# Check configuration
qdrant-loader --workspace . config

# List projects
qdrant-loader project --workspace . list
```

### Traditional Mode

```bash
# Use specific config files
qdrant-loader --config config.yaml --env .env init
qdrant-loader --config config.yaml --env .env ingest
qdrant-loader --config config.yaml --env .env config
```

### Development Workflow

```bash
# Debug mode with verbose logging
qdrant-loader --log-level DEBUG --workspace . init --force
qdrant-loader --log-level DEBUG --workspace . ingest --project my-project

# Production mode with minimal logging
qdrant-loader --log-level WARNING --workspace . ingest
```

### Project-Specific Operations

```bash
# Work with specific project
qdrant-loader --workspace . ingest --project backend-docs
qdrant-loader project --workspace . status --project-id backend-docs

# Work with specific source type
qdrant-loader --workspace . ingest --source-type git
qdrant-loader --workspace . ingest --project backend-docs --source-type confluence
```

## ⚠️ Important Notes

### Option Validation

- `--workspace` cannot be used with `--config` or `--env`
- `--config` and `--env` must be used together (if not using workspace mode)
- Project filtering options (`--project`, `--source-type`, `--source`) only work with `ingest` command

### Configuration Discovery

**Workspace Mode:**

1. Looks for `config.yaml` in workspace directory
2. Looks for `.env` in workspace directory
3. Creates workspace structure if needed

**Traditional Mode:**

1. Uses specified `--config` file
2. Uses specified `--env` file (optional)
3. Falls back to `config.yaml` in current directory if no `--config` specified

### Error Handling

- Invalid option combinations show clear error messages
- Missing configuration files are reported with helpful suggestions
- Database directory creation is prompted interactively

## 🔗 Related Documentation

- **[CLI Commands Reference](./commands.md)** - Complete command documentation
- **[Scripting and Automation](./scripting-automation.md)** - Automation examples
- **[Configuration Reference](../configuration/config-file-reference.md)** - Configuration options
- **[Troubleshooting](../troubleshooting/common-issues.md)** - Common CLI issues

---

**Accurate CLI options reference!** ✅

This reference documents only the actual implemented options and flags, ensuring accuracy and reliability for all QDrant Loader users.
