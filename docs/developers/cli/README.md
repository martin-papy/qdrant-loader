# CLI Reference

This document provides comprehensive reference for the QDrant Loader command-line interface (CLI) and MCP server.

## 📋 Table of Contents

- [Main CLI Commands](#-main-cli-commands)
- [MCP Server CLI](#-mcp-server-cli)
- [Configuration](#-configuration)
- [Exit Codes](#exit-codes)
- [Advanced Usage](#-advanced-usage-patterns)
- [Troubleshooting](#-troubleshooting)

## 🚀 Main CLI Commands

The QDrant Loader provides several commands for managing data ingestion and project operations.

### Command Overview

```bash
qdrant-loader [COMMAND] [OPTIONS]

Commands:
  init              Initialize a new QDrant collection
  ingest            Ingest data from configured sources
  config            Display current configuration
  project           Project management commands

Global Options:
  --help           Show help message
  --version        Show version information
```

### `init` - Initialize Collection

Initialize a new QDrant collection with the configured settings.

```bash
qdrant-loader init [OPTIONS]

Options:
  --force          Force initialization even if collection exists
  --help           Show help for this command
```

**Examples:**

```bash
# Initialize new collection
qdrant-loader init

# Force re-initialization (overwrites existing collection)
qdrant-loader init --force
```

### `ingest` - Data Ingestion

Ingest data from configured sources into the QDrant collection.

```bash
qdrant-loader ingest [OPTIONS]

Options:
  --project PATH        Path to project configuration directory
  --source-type TYPE    Type of source to ingest (git, confluence, etc.)
  --source PATH         Specific source path or identifier
  --profile NAME        Configuration profile to use
  --help               Show help for this command
```

**Examples:**

```bash
# Ingest all configured sources
qdrant-loader ingest

# Ingest from specific project
qdrant-loader ingest --project /path/to/project

# Ingest specific source type
qdrant-loader ingest --source-type git

# Ingest with specific profile
qdrant-loader ingest --profile production
```

### `config` - Configuration Display

Display the current configuration in JSON format.

```bash
qdrant-loader config

Options:
  --help           Show help for this command
```

**Example:**

```bash
# Show current configuration
qdrant-loader config
```

### `project` - Project Management

Manage QDrant Loader projects and their status.

#### `project list` - List Projects

```bash
qdrant-loader project list [OPTIONS]

Options:
  --format FORMAT      Output format (table, json, yaml)
  --help              Show help for this command
```

#### `project status` - Project Status

```bash
qdrant-loader project status [OPTIONS]

Options:
  --project-id ID     Specific project ID to check
  --format FORMAT     Output format (table, json, yaml)
  --help             Show help for this command
```

#### `project validate` - Validate Project

```bash
qdrant-loader project validate [OPTIONS]

Options:
  --project-id ID     Project ID to validate
  --help             Show help for this command
```

**Examples:**

```bash
# List all projects
qdrant-loader project list

# List projects in JSON format
qdrant-loader project list --format json

# Check status of specific project
qdrant-loader project status --project-id my-project

# Validate project configuration
qdrant-loader project validate --project-id my-project
```

## 🔧 Configuration

The CLI uses configuration files and environment variables for settings.

### Configuration Files

The CLI looks for configuration in the following order:

1. `config.yaml` in current directory
2. `~/.qdrant-loader/config.yaml`
3. Environment variables

### Environment Variables

```bash
# QDrant Connection
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your-api-key

# Collection Settings
QDRANT_COLLECTION_NAME=documents

# Processing Settings
CHUNK_SIZE=1000
BATCH_SIZE=50
MAX_CONCURRENT_REQUESTS=10
```

### Exit Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 0 | Success | Command completed successfully |
| 1 | General Error | Unspecified error occurred |
| 2 | Configuration Error | Invalid configuration or missing required settings |
| 3 | Connection Error | Failed to connect to QDrant or data sources |
| 4 | Authentication Error | Invalid credentials for data sources |
| 5 | Processing Error | Error during data processing or ingestion |

## 🤖 MCP Server CLI

### Command Overview

The MCP server provides a single command for starting the Model Context Protocol server.

```bash
mcp-qdrant-loader [OPTIONS]

Options:
  --log-level LEVEL    Logging level (DEBUG, INFO, WARNING, ERROR)
  --config PATH        Configuration file path
  --help               Show help message
  --version            Show version information
```

### Basic Usage

```bash
# Start MCP server with default settings
mcp-qdrant-loader

# Start with custom configuration
mcp-qdrant-loader --config custom-config.yaml

# Start with debug logging
mcp-qdrant-loader --log-level DEBUG
```

### MCP Server Configuration

The MCP server uses the same configuration files as the main CLI tool:

```yaml
# config.yaml
qdrant:
  url: "http://localhost:6333"
  collection_name: "documents"

mcp_server:
  search_limit: 10
  enable_hierarchy_search: true
  enable_attachment_search: true
```

### Integration with AI Tools

#### Cursor IDE Integration

```json
{
  "mcpServers": {
    "qdrant-loader": {
      "command": "mcp-qdrant-loader",
      "args": ["--log-level", "INFO"]
    }
  }
}
```

#### Claude Desktop Integration

```json
{
  "mcpServers": {
    "qdrant-loader": {
      "command": "mcp-qdrant-loader",
      "args": ["--config", "/path/to/config.yaml"],
      "env": {
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

## 🔧 Advanced Usage Patterns

### Automation and Scripting

#### CI/CD Integration

```bash
#!/bin/bash
# ci-ingest.sh - Automated ingestion script

set -e

# Initialize if needed
echo "Initializing QDrant collection..."
qdrant-loader init --force

# Run ingestion
echo "Starting data ingestion..."
qdrant-loader ingest

# Check project status
echo "Ingestion completed. Checking status:"
qdrant-loader project list
```

#### Configuration Management

```bash
# Use different configurations for different environments
qdrant-loader --config config.dev.yaml ingest
qdrant-loader --config config.staging.yaml ingest
qdrant-loader --config config.prod.yaml ingest
```

### Error Handling and Debugging

#### Configuration Validation

```bash
# Display current configuration
qdrant-loader config

# Validate project configuration
qdrant-loader project validate --project-id my-project
```

## 🔍 Troubleshooting

### Common Issues

#### Connection Problems

```bash
# Check current configuration
qdrant-loader config

# Verify project status
qdrant-loader project status
```

#### Configuration Issues

```bash
# Display configuration to verify settings
qdrant-loader config

# Validate specific project
qdrant-loader project validate --project-id my-project
```

### Debug Commands

```bash
# Show current configuration
qdrant-loader config

# List all projects with details
qdrant-loader project list --format json

# Check specific project status
qdrant-loader project status --project-id my-project --format json
```

## 📚 Related Documentation

### Core Documentation

- **[Configuration Reference](../configuration/)** - Complete configuration options
- **[Architecture Overview](../architecture/)** - System design and components
- **[Extension Guide](../extending/)** - How to extend functionality

### User Guides

- **[Getting Started](../../getting-started/)** - Quick start guide
- **[Configuration Guide](../../users/configuration/)** - User configuration reference
- **[Troubleshooting](../../users/troubleshooting/)** - Common issues and solutions

## 🆘 Getting Help

### CLI Support

- **[GitHub Issues](https://github.com/martin-papy/qdrant-loader/issues)** - Report CLI bugs
- **[GitHub Discussions](https://github.com/martin-papy/qdrant-loader/discussions)** - Ask CLI questions
- **[CLI Examples](https://github.com/martin-papy/qdrant-loader/tree/main/examples/cli)** - Real-world usage examples

### Contributing to CLI

- **[Contributing Guide](../../CONTRIBUTING.md)** - How to contribute
- **[CLI Design Guidelines](../extending/cli-design-guidelines.md)** - CLI design principles
- **[Testing Guide](../testing/)** - Testing CLI functionality

---

**Ready to use the CLI?** Start with the basic commands above or check out the [Configuration Reference](../configuration/) for detailed configuration options.
