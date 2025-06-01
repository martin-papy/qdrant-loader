# CLI Documentation

This section provides comprehensive documentation for QDrant Loader's command-line interface, including all commands, options, and usage patterns for both the core loader and MCP server.

## 🎯 CLI Overview

QDrant Loader provides two main command-line interfaces:

### 📚 CLI Tools

- **`qdrant-loader`** - Core data ingestion and management tool
- **`mcp-qdrant-loader`** - Model Context Protocol server for AI tool integration

### 🔧 Design Principles

1. **Simplicity** - Intuitive commands with sensible defaults
2. **Flexibility** - Multiple configuration options and modes
3. **Feedback** - Clear progress indicators and error messages
4. **Automation** - Scriptable commands for CI/CD integration

## 🚀 Quick Start

### Installation

```bash
# Install both packages
pip install -e packages/qdrant-loader[dev]
pip install -e packages/qdrant-loader-mcp-server[dev]

# Verify installation
qdrant-loader --version
mcp-qdrant-loader --version
```

### Basic Usage

```bash
# Initialize QDrant collection
qdrant-loader init

# Load data from configured sources
qdrant-loader ingest

# Check processing status
qdrant-loader status

# Start MCP server
mcp-qdrant-loader
```

## 📚 QDrant Loader CLI

### Command Overview

| Command | Purpose | Example |
|---------|---------|---------|
| `init` | Initialize QDrant collection | `qdrant-loader init` |
| `ingest` | Process and load data | `qdrant-loader ingest` |
| `status` | Show processing status | `qdrant-loader status` |
| `config` | Display configuration | `qdrant-loader config` |

### Global Options

```bash
qdrant-loader [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS]

Global Options:
  --config PATH          Configuration file path (default: config.yaml)
  --env PATH            Environment file path (default: .env)
  --workspace PATH      Workspace directory (auto-discovers config files)
  --log-level LEVEL     Logging level (DEBUG, INFO, WARNING, ERROR)
  --help                Show help message
  --version             Show version information
```

### Configuration Modes

#### Workspace Mode (Recommended)

```bash
# Create workspace directory
mkdir my-qdrant-workspace
cd my-qdrant-workspace

# Copy configuration templates
cp packages/qdrant-loader/conf/config.template.yaml config.yaml
cp packages/qdrant-loader/conf/.env.template .env

# Use workspace mode - automatically finds config files
qdrant-loader --workspace . init
qdrant-loader --workspace . ingest
```

#### Individual Files Mode

```bash
# Specify configuration files individually
qdrant-loader --config config.yaml --env .env init
qdrant-loader --config config.yaml --env .env ingest
```

### Commands Reference

#### `init` Command

Initialize QDrant collection and prepare for data ingestion.

```bash
qdrant-loader init [OPTIONS]

Options:
  --force               Force recreation of existing collection
  --collection NAME     Override collection name from config
  --vector-size SIZE    Override vector size (default: 1536)

Examples:
  qdrant-loader init
  qdrant-loader init --force
  qdrant-loader init --collection my_docs --vector-size 1536
```

#### `ingest` Command

Process and load data from configured sources.

```bash
qdrant-loader ingest [OPTIONS]

Options:
  --sources SOURCE      Specific sources to process (can be repeated)
  --force-refresh       Force reprocessing of all documents
  --batch-size SIZE     Override batch size for processing
  --max-workers NUM     Maximum number of worker processes

Examples:
  qdrant-loader ingest
  qdrant-loader ingest --sources git --sources confluence
  qdrant-loader ingest --force-refresh
  qdrant-loader ingest --batch-size 100 --max-workers 4
```

#### `status` Command

Display current processing status and statistics.

```bash
qdrant-loader status [OPTIONS]

Options:
  --detailed            Show detailed per-source statistics
  --json                Output in JSON format
  --watch               Continuously monitor status (refresh every 5s)

Examples:
  qdrant-loader status
  qdrant-loader status --detailed
  qdrant-loader status --json
  qdrant-loader status --watch
```

#### `config` Command

Display current configuration and validate settings.

```bash
qdrant-loader config [OPTIONS]

Options:
  --validate            Validate configuration without showing values
  --show-secrets        Include sensitive values in output (use with caution)
  --format FORMAT       Output format (yaml, json, table)

Examples:
  qdrant-loader config
  qdrant-loader config --validate
  qdrant-loader config --format json
```

### Environment Variables

```bash
# QDrant Configuration
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=documents
QDRANT_API_KEY=your-api-key

# OpenAI Configuration
OPENAI_API_KEY=sk-proj-your-key-here

# Data Source Credentials
REPO_TOKEN=ghp_your-github-token
CONFLUENCE_URL=https://your-domain.atlassian.net
CONFLUENCE_TOKEN=your-confluence-token
CONFLUENCE_EMAIL=your-email@domain.com

# Application Settings
LOG_LEVEL=INFO
LOG_FILE=qdrant-loader.log
STATE_DB_PATH=state.db

# Performance Settings
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

The MCP server provides a single command with various options for different deployment scenarios.

```bash
mcp-qdrant-loader [OPTIONS]

Options:
  --workspace PATH      Workspace directory path (required)
  --host HOST          Host to bind to (default: localhost)
  --port PORT          Port to bind to (default: auto-assigned)
  --log-level LEVEL    Logging level (DEBUG, INFO, WARNING, ERROR)
  --config PATH        Configuration file path
  --help               Show help message
  --version            Show version information
```

### Basic Usage

```bash
# Start MCP server with workspace
mcp-qdrant-loader --workspace /path/to/workspace

# Start with custom configuration
mcp-qdrant-loader --workspace . --config custom-config.yaml

# Start with debug logging
mcp-qdrant-loader --workspace . --log-level DEBUG
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
      "args": ["--workspace", "/path/to/your/workspace"]
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
      "args": ["--workspace", "/path/to/your/workspace"],
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

# Setup workspace
export WORKSPACE_DIR="/opt/qdrant-workspace"
cd "$WORKSPACE_DIR"

# Initialize if needed
if ! qdrant-loader --workspace . status > /dev/null 2>&1; then
    echo "Initializing QDrant collection..."
    qdrant-loader --workspace . init
fi

# Run ingestion
echo "Starting data ingestion..."
qdrant-loader --workspace . ingest --batch-size 100

# Check status
echo "Ingestion completed. Final status:"
qdrant-loader --workspace . status --detailed
```

#### Monitoring Script

```bash
#!/bin/bash
# monitor.sh - Continuous monitoring

while true; do
    clear
    echo "QDrant Loader Status - $(date)"
    echo "================================"
    qdrant-loader --workspace . status --detailed
    sleep 30
done
```

### Configuration Management

#### Environment-Specific Configs

```bash
# Development
qdrant-loader --config config.dev.yaml --env .env.dev ingest

# Staging
qdrant-loader --config config.staging.yaml --env .env.staging ingest

# Production
qdrant-loader --config config.prod.yaml --env .env.prod ingest
```

#### Dynamic Configuration

```bash
# Override specific settings
QDRANT_COLLECTION_NAME=test_docs qdrant-loader ingest

# Use different batch size for large datasets
qdrant-loader ingest --batch-size 200 --max-workers 8
```

### Error Handling and Debugging

#### Verbose Logging

```bash
# Enable debug logging
qdrant-loader --log-level DEBUG ingest

# Log to file
qdrant-loader --log-level INFO ingest 2>&1 | tee ingestion.log
```

#### Configuration Validation

```bash
# Validate configuration before running
qdrant-loader config --validate

# Check specific source connectivity
qdrant-loader status --detailed
```

## 📊 Performance Optimization

### Batch Processing

```bash
# Optimize for large datasets
qdrant-loader ingest --batch-size 200 --max-workers 8

# Optimize for memory-constrained environments
qdrant-loader ingest --batch-size 25 --max-workers 2
```

### Selective Processing

```bash
# Process only specific sources
qdrant-loader ingest --sources git --sources confluence

# Force refresh of specific content
qdrant-loader ingest --force-refresh --sources git
```

## 🔍 Troubleshooting

### Common Issues

#### Connection Problems

```bash
# Test QDrant connectivity
qdrant-loader status

# Validate configuration
qdrant-loader config --validate
```

#### Authentication Issues

```bash
# Check environment variables
qdrant-loader config --show-secrets

# Test with debug logging
qdrant-loader --log-level DEBUG ingest --sources confluence
```

#### Performance Issues

```bash
# Monitor processing with detailed status
qdrant-loader status --watch --detailed

# Adjust batch size and workers
qdrant-loader ingest --batch-size 50 --max-workers 4
```

### Debug Commands

```bash
# Show full configuration
qdrant-loader config --format json

# Test individual sources
qdrant-loader ingest --sources git --log-level DEBUG

# Monitor real-time status
qdrant-loader status --watch
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
