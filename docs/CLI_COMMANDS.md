# QDrant Loader CLI Commands

This document provides comprehensive documentation for all available CLI commands in QDrant Loader.

## Table of Contents

1. [Global Options](#global-options)
2. [Core Commands](#core-commands)
3. [Project Management Commands](#project-management-commands)
4. [Configuration Options](#configuration-options)
5. [Examples](#examples)

## Global Options

All commands support these global options:

- `--log-level [debug|info|warning|error|critical]`: Set the logging level (default: info)
- `--version`: Show the version and exit
- `--help`: Show help message and exit

## Core Commands

### `init`

Initialize the QDrant collection and database.

```bash
qdrant-loader init [OPTIONS]
```

**Options:**

- `--workspace PATH`: Workspace directory containing config.yaml and .env files
- `--config PATH`: Path to config file
- `--env PATH`: Path to .env file
- `--force`: Force reinitialization of collection
- `--log-level [debug|info|warning|error|critical]`: Set the logging level

**Examples:**

```bash
# Initialize with default config.yaml
qdrant-loader init

# Initialize with custom config
qdrant-loader init --config /path/to/config.yaml

# Force reinitialize (deletes existing data)
qdrant-loader init --force

# Initialize with workspace
qdrant-loader init --workspace /path/to/workspace
```

### `ingest`

Ingest documents from configured sources.

```bash
qdrant-loader ingest [OPTIONS]
```

**Options:**

- `--workspace PATH`: Workspace directory containing config.yaml and .env files
- `--config PATH`: Path to config file
- `--env PATH`: Path to .env file
- `--source-type TEXT`: Source type to process (e.g., confluence, jira, git)
- `--source TEXT`: Source name to process
- `--log-level [debug|info|warning|error|critical]`: Set the logging level
- `--profile/--no-profile`: Run under cProfile for performance analysis

**Examples:**

```bash
# Ingest all configured sources
qdrant-loader ingest

# Ingest specific source type
qdrant-loader ingest --source-type git

# Ingest specific source
qdrant-loader ingest --source-type git --source my-repo

# Ingest with profiling
qdrant-loader ingest --profile
```

### `config`

Display current configuration.

```bash
qdrant-loader config [OPTIONS]
```

**Options:**

- `--workspace PATH`: Workspace directory containing config.yaml and .env files
- `--config PATH`: Path to config file
- `--env PATH`: Path to .env file
- `--log-level [debug|info|warning|error|critical]`: Set the logging level

**Examples:**

```bash
# Display current configuration
qdrant-loader config

# Display configuration from specific file
qdrant-loader config --config /path/to/config.yaml
```

## Project Management Commands

The `project` command group provides comprehensive project management functionality for multi-project setups.

### `project list`

List all configured projects.

```bash
qdrant-loader project list [OPTIONS]
```

**Options:**

- `--workspace PATH`: Workspace directory containing config.yaml and .env files
- `--config PATH`: Path to config file
- `--env PATH`: Path to .env file
- `--format [table|json]`: Output format (default: table)

**Examples:**

```bash
# List projects in table format
qdrant-loader project list

# List projects in JSON format
qdrant-loader project list --format json

# List projects from specific config
qdrant-loader project list --config /path/to/config.yaml
```

**Sample Output (Table):**

```
                                    Configured Projects                                     
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┓
┃ Project ID   ┃ Display Name ┃ Description                 ┃ Collection         ┃ Sources ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━┩
│ project-1    │ Project One  │ First project               │ main_collection    │       3 │
│ project-2    │ Project Two  │ Second project              │ main_collection    │       2 │
└──────────────┴──────────────┴─────────────────────────────┴────────────────────┴─────────┘
```

**Sample Output (JSON):**

```json
[
  {
    "project_id": "project-1",
    "display_name": "Project One",
    "description": "First project",
    "collection_name": "main_collection",
    "source_count": 3
  },
  {
    "project_id": "project-2",
    "display_name": "Project Two", 
    "description": "Second project",
    "collection_name": "main_collection",
    "source_count": 2
  }
]
```

### `project status`

Show detailed project status including document counts and ingestion history.

```bash
qdrant-loader project status [OPTIONS]
```

**Options:**

- `--workspace PATH`: Workspace directory containing config.yaml and .env files
- `--config PATH`: Path to config file
- `--env PATH`: Path to .env file
- `--project-id TEXT`: Specific project ID to check status for
- `--format [table|json]`: Output format (default: table)

**Examples:**

```bash
# Show status for all projects
qdrant-loader project status

# Show status for specific project
qdrant-loader project status --project-id my-project

# Show status in JSON format
qdrant-loader project status --format json
```

**Sample Output:**

```
╭───────────────────────────────────────── Project: project-1 ──────────────────────────────────────────╮
│ Project ID: project-1                                                                                 │
│ Display Name: Project One                                                                             │
│ Description: First project                                                                            │
│ Collection: main_collection                                                                           │
│ Sources: 3                                                                                            │
│ Documents: N/A (requires database)                                                                    │
│ Latest Ingestion: N/A (requires database)                                                             │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### `project validate`

Validate project configurations.

```bash
qdrant-loader project validate [OPTIONS]
```

**Options:**

- `--workspace PATH`: Workspace directory containing config.yaml and .env files
- `--config PATH`: Path to config file
- `--env PATH`: Path to .env file
- `--project-id TEXT`: Specific project ID to validate

**Examples:**

```bash
# Validate all projects
qdrant-loader project validate

# Validate specific project
qdrant-loader project validate --project-id my-project
```

**Sample Output:**

```
✓ Project 'project-1' is valid (3 sources)
✓ Project 'project-2' is valid (2 sources)

All projects are valid!
```

**Error Output:**

```
✗ Project 'project-3' has errors:
  • Missing source_type for repo-1
  • Missing source for confluence-space

Some projects have validation errors.
```

## Configuration Options

### Workspace Mode

Use `--workspace` to specify a directory containing both `config.yaml` and `.env` files:

```bash
qdrant-loader --workspace /path/to/workspace <command>
```

This is the recommended approach for organized project setups.

### Traditional Mode

Specify config and env files separately:

```bash
qdrant-loader --config /path/to/config.yaml --env /path/to/.env <command>
```

### Configuration Precedence

1. Command-line options (`--workspace`, `--config`, `--env`)
2. Environment variables
3. Default files in current directory (`config.yaml`, `.env`)

## Examples

### Basic Workflow

```bash
# 1. Initialize the system
qdrant-loader init --config my-config.yaml

# 2. List configured projects
qdrant-loader project list --config my-config.yaml

# 3. Validate project configurations
qdrant-loader project validate --config my-config.yaml

# 4. Check project status
qdrant-loader project status --config my-config.yaml

# 5. Ingest documents
qdrant-loader ingest --config my-config.yaml
```

### Multi-Project Workflow

```bash
# Set up workspace
mkdir my-workspace
cd my-workspace

# Create config.yaml and .env files
# ... (configure your projects)

# Initialize with workspace
qdrant-loader init --workspace .

# List all projects
qdrant-loader project list --workspace .

# Validate specific project
qdrant-loader project validate --workspace . --project-id project-1

# Ingest specific project sources
qdrant-loader ingest --workspace . --source-type git --source project-1-repo
```

### Development Workflow

```bash
# Validate configuration before ingestion
qdrant-loader project validate --config dev-config.yaml

# Run with debug logging
qdrant-loader --log-level debug ingest --config dev-config.yaml

# Profile performance
qdrant-loader ingest --config dev-config.yaml --profile

# Check status after ingestion
qdrant-loader project status --config dev-config.yaml --format json
```

## Error Handling

All commands provide detailed error messages and appropriate exit codes:

- **Exit Code 0**: Success
- **Exit Code 1**: General error (configuration, validation, etc.)
- **Exit Code 2**: Command-line usage error

Common error scenarios:

1. **Missing Configuration**: Ensure `config.yaml` exists or specify `--config`
2. **Invalid Project ID**: Use `project list` to see available projects
3. **Database Connection**: Check database path and permissions
4. **QDrant Connection**: Verify QDrant URL and API key in configuration

## Tips and Best Practices

1. **Use Workspace Mode**: Organize your configuration files in a dedicated workspace directory
2. **Validate First**: Always run `project validate` before ingestion
3. **Check Status**: Use `project status` to monitor ingestion progress
4. **JSON Output**: Use `--format json` for programmatic processing
5. **Logging**: Use `--log-level debug` for troubleshooting
6. **Profiling**: Use `--profile` to identify performance bottlenecks

For more information, see the main documentation or use `--help` with any command.
