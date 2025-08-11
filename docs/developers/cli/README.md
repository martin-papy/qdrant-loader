# CLI Development Guide
This document provides comprehensive reference for developing with the QDrant Loader command-line interface (CLI) and MCP server. All commands, options, and examples are verified against the actual implementation.
## 📋 Table of Contents
- [Main CLI Commands](#-main-cli-commands)
- [MCP Server CLI](#-mcp-server-cli)
- [Configuration](#-configuration)
- [Exit Codes](#exit-codes)
- [Development Patterns](#-development-patterns)
- [Testing](#-testing)
## 🚀 Main CLI Commands
The QDrant Loader provides a focused set of commands for data ingestion and project management.
### Command Overview
```bash
qdrant-loader [GLOBAL_OPTIONS] [COMMAND] [COMMAND_OPTIONS]
Commands:
  init              Initialize QDrant collection
  ingest            Ingest data from configured sources
  config            Display current configuration
  project           Project management commands (list, status, validate)
Global Options:
  --log-level LEVEL    Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  --help              Show help message
  --version           Show version information
```
### Global Configuration Options
All commands support these configuration options:
```bash
# Workspace mode (recommended)
--workspace PATH        # Workspace directory containing config.yaml and .env
# Traditional mode (alternative)
--config PATH          # Path to configuration file
--env PATH             # Path to environment file
```
**Note**: `--workspace` cannot be used with `--config` or `--env` options.
### `init` - Initialize Collection
Initialize QDrant collection with configured settings.
```bash
qdrant-loader [GLOBAL_OPTIONS] init [OPTIONS]
Options:
  --force             Force reinitialization of existing collection
  --help              Show help for this command
```
**Examples:**
```bash
# Workspace mode (recommended)
\1 init --workspace .
# Force re-initialization
\1 init --workspace . --force
# Traditional mode
qdrant-loader --config config.yaml --env .env init
# With debug logging
qdrant-loader --log-level DEBUG --workspace . init
```
### `ingest` - Data Ingestion
Process and load data from configured sources into QDrant.
```bash
qdrant-loader [GLOBAL_OPTIONS] ingest [OPTIONS]
Options:
  --project ID         Process specific project only
  --source-type TYPE   Process specific source type (git, confluence, jira, localfile, publicdocs)
  --source NAME        Process specific source name
  --profile            Enable performance profiling (saves to profile.out)
  --help              Show help for this command
```
**Examples:**
```bash
# Ingest all configured sources
\1 ingest --workspace .
# Ingest specific project
\1 ingest --workspace . --project my-project
# Ingest specific source type from all projects
\1 ingest --workspace . --source-type git
# Ingest specific source type from specific project
\1 ingest --workspace . --project my-project --source-type confluence
# Ingest specific source from specific project
\1 ingest --workspace . --project my-project --source-type git --source my-repo
# Enable performance profiling
\1 ingest --workspace . --profile
# With debug logging
qdrant-loader --log-level DEBUG --workspace . ingest
```
### `config` - Configuration Display
Display current configuration in JSON format.
```bash
qdrant-loader [GLOBAL_OPTIONS] config
Options:
  --help              Show help for this command
```
**Examples:**
```bash
# Show current configuration
\1 config --workspace .
# Traditional mode
qdrant-loader --config config.yaml --env .env config
# With debug logging to see configuration loading process
qdrant-loader --log-level DEBUG --workspace . config
```
### `project` - Project Management
Manage QDrant Loader projects and their status.
#### `project list` - List Projects
```bash
qdrant-loader project [GLOBAL_OPTIONS] list [OPTIONS]
Options:
  --format FORMAT     Output format (table, json)
  --help              Show help for this command
```
#### `project status` - Project Status
```bash
qdrant-loader project [GLOBAL_OPTIONS] status [OPTIONS]
Options:
  --project-id ID     Specific project ID to check
  --format FORMAT     Output format (table, json)
  --help              Show help for this command
```
#### `project validate` - Validate Project
```bash
qdrant-loader project [GLOBAL_OPTIONS] validate [OPTIONS]
Options:
  --project-id ID     Project ID to validate
  --help              Show help for this command
```
**Examples:**
```bash
# List all projects
qdrant-loader project --workspace . list
# List projects in JSON format
qdrant-loader project --workspace . list --format json
# Check status of all projects
qdrant-loader project --workspace . status
# Check status of specific project
qdrant-loader project --workspace . status --project-id my-project
# Validate all project configurations
qdrant-loader project --workspace . validate
# Validate specific project
qdrant-loader project --workspace . validate --project-id my-project
```
## 🤖 MCP Server CLI
The MCP server provides a single command for starting the Model Context Protocol server.
### Command Overview
```bash
mcp-qdrant-loader [OPTIONS]
Options:
  --log-level LEVEL   Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  --config PATH       Configuration file path (currently not implemented)
  --help              Show help message
  --version           Show version information
```
### Basic Usage
```bash
# Start MCP server with default settings
mcp-qdrant-loader
# Start with debug logging
mcp-qdrant-loader --log-level DEBUG
# Show version
mcp-qdrant-loader --version
# Show help
mcp-qdrant-loader --help
```
### MCP Server Configuration
The MCP server uses environment variables for configuration (not config files):
```bash
# Required
QDRANT_URL=http://localhost:6333
OPENAI_API_KEY=your-openai-api-key
# Optional
QDRANT_API_KEY=your-qdrant-cloud-api-key
QDRANT_COLLECTION_NAME=documents
MCP_LOG_LEVEL=INFO
MCP_LOG_FILE=/path/to/mcp.log
MCP_DISABLE_CONSOLE_LOGGING=true  # Recommended for Cursor
```
### Integration with AI Tools
#### Cursor IDE Integration
```json
{
  "mcpServers": {
    "qdrant-loader": {
      "command": "mcp-qdrant-loader",
      "args": ["--log-level", "INFO"],
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "OPENAI_API_KEY": "your_openai_key",
        "MCP_DISABLE_CONSOLE_LOGGING": "true"
      }
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
      "args": [],
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "OPENAI_API_KEY": "your_openai_key",
        "QDRANT_COLLECTION_NAME": "documents"
      }
    }
  }
}
```
## 🔧 Configuration
### Workspace Mode (Recommended)
The CLI uses workspace mode for better organization:
```bash
# Workspace structure
my-workspace/
├── config.yaml          # Main configuration
├── .env                 # Environment variables
├── logs/                # Log files
│   └── qdrant-loader.log
├── data/                # State database
│   └── state.db
└── metrics/             # Performance metrics
```
### Configuration Files
The CLI looks for configuration in this order:
1. **Workspace mode**: `--workspace` directory containing `config.yaml` and `.env`
2. **Traditional mode**: `--config` and `--env` files
3. **Default**: `config.yaml` in current directory
### Environment Variables
```bash
# QDrant Connection
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your-api-key
QDRANT_COLLECTION_NAME=documents
# OpenAI API
OPENAI_API_KEY=your-openai-api-key
# State Management
STATE_DB_PATH=./state/state.db
# Source-specific credentials
GITHUB_TOKEN=your-github-token
CONFLUENCE_TOKEN=your-confluence-token
CONFLUENCE_EMAIL=your-email@company.com
JIRA_TOKEN=your-jira-token
JIRA_EMAIL=your-email@company.com
```
## Exit Codes
| Code | Meaning | Description |
|------|---------|-------------|
| 0 | Success | Command completed successfully |
| 1 | General Error | Unspecified error occurred |
| 2 | Configuration Error | Invalid configuration or missing required settings |
| 3 | Connection Error | Failed to connect to QDrant or data sources |
| 4 | Authentication Error | Invalid credentials for data sources |
| 5 | Processing Error | Error during data processing or ingestion |
## 🔧 Development Patterns
### Automation and Scripting
#### Basic Automation Script
```bash
#!/bin/bash
# automation-example.sh - Basic automation pattern
set -euo pipefail
WORKSPACE_DIR="${WORKSPACE_DIR:-$(pwd)}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"
# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}
# Validate configuration
log "Validating configuration..."
if ! \1 config --workspace "$WORKSPACE_DIR" >/dev/null 2>&1; then
    log "ERROR: Configuration validation failed"
    exit 2
fi
# Validate projects
log "Validating projects..."
if ! qdrant-loader project --workspace "$WORKSPACE_DIR" validate; then
    log "ERROR: Project validation failed"
    exit 2
fi
# Initialize collection
log "Initializing QDrant collection..."
qdrant-loader --log-level "$LOG_LEVEL" --workspace "$WORKSPACE_DIR" init
# Run ingestion
log "Starting data ingestion..."
qdrant-loader --log-level "$LOG_LEVEL" --workspace "$WORKSPACE_DIR" ingest
# Check final status
log "Checking project status..."
qdrant-loader project --workspace "$WORKSPACE_DIR" status
log "Automation completed successfully"
```
#### Project-Specific Processing
```bash
#!/bin/bash
# project-processing.sh - Process specific projects
WORKSPACE_DIR="${1:-$(pwd)}"
PROJECT_ID="${2:-}"
if [ -n "$PROJECT_ID" ]; then
    echo "Processing project: $PROJECT_ID"
    # Validate specific project
    qdrant-loader project --workspace "$WORKSPACE_DIR" validate --project-id "$PROJECT_ID"
    # Process specific project
    \1 ingest --workspace "$WORKSPACE_DIR" --project "$PROJECT_ID"
    # Check project status
    qdrant-loader project --workspace "$WORKSPACE_DIR" status --project-id "$PROJECT_ID"
else
    echo "Processing all projects"
    # Get list of projects
    PROJECTS=$(qdrant-loader project --workspace "$WORKSPACE_DIR" list --format json | jq -r '.[].project_id')
    for project in $PROJECTS; do
        echo "Processing project: $project"
        \1 ingest --workspace "$WORKSPACE_DIR" --project "$project"
    done
fi
```
### Error Handling and Debugging
#### Configuration Validation
```bash
# Check configuration syntax
\1 config --workspace .
# Validate all projects
qdrant-loader project --workspace . validate
# Validate specific project with debug output
qdrant-loader --log-level DEBUG project --workspace . validate --project-id my-project
```
#### Debug Commands
```bash
# Show current configuration with debug logging
qdrant-loader --log-level DEBUG --workspace . config
# List all projects with detailed output
qdrant-loader project --workspace . list --format json
# Check specific project status with JSON output
qdrant-loader project --workspace . status --project-id my-project --format json
# Run ingestion with debug logging and profiling
qdrant-loader --log-level DEBUG --workspace . ingest --profile
```
## 🧪 Testing
### CLI Testing Patterns
#### Configuration Testing
```bash
#!/bin/bash
# test-config.sh - Test configuration validity
test_config() {
    local workspace_dir="$1"
    echo "Testing configuration in: $workspace_dir"
    # Test configuration loading
    if \1 config --workspace "$workspace_dir" >/dev/null 2>&1; then
        echo "✅ Configuration is valid"
    else
        echo "❌ Configuration is invalid"
        return 1
    fi
    # Test project validation
    if qdrant-loader project --workspace "$workspace_dir" validate; then
        echo "✅ All projects are valid"
    else
        echo "❌ Project validation failed"
        return 1
    fi
}
# Test multiple workspace configurations
test_config "./test-workspace-1"
test_config "./test-workspace-2"
```
#### Integration Testing
```bash
#!/bin/bash
# integration-test.sh - Full integration test
set -euo pipefail
WORKSPACE_DIR="./test-workspace"
TEST_PROJECT="test-project"
# Setup test workspace
mkdir -p "$WORKSPACE_DIR"
cp config.test.yaml "$WORKSPACE_DIR/config.yaml"
cp .env.test "$WORKSPACE_DIR/.env"
# Test initialization
echo "Testing initialization..."
\1 init --workspace "$WORKSPACE_DIR" --force
# Test ingestion
echo "Testing ingestion..."
\1 ingest --workspace "$WORKSPACE_DIR" --project "$TEST_PROJECT"
# Test project commands
echo "Testing project commands..."
qdrant-loader project --workspace "$WORKSPACE_DIR" list
qdrant-loader project --workspace "$WORKSPACE_DIR" status --project-id "$TEST_PROJECT"
# Cleanup
rm -rf "$WORKSPACE_DIR"
echo "✅ Integration test completed"
```
### MCP Server Testing
```bash
#!/bin/bash
# test-mcp-server.sh - Test MCP server functionality
# Set required environment variables
export QDRANT_URL="http://localhost:6333"
export OPENAI_API_KEY="test-key"
export QDRANT_COLLECTION_NAME="test-collection"
# Test server startup
echo "Testing MCP server startup..."
timeout 5s mcp-qdrant-loader --log-level DEBUG || echo "Server started successfully"
# Test with JSON-RPC message
echo "Testing search functionality..."
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"search","arguments":{"query":"test","limit":1}}}' | \
    timeout 5s mcp-qdrant-loader 2>/dev/null || echo "Search test completed"
```
## 📚 Related Documentation
### Core Documentation
- **[Architecture Overview](../architecture/)** - System design and components
- **[Configuration Reference](../../users/configuration/)** - Configuration options
- **[Extension Guide](../extending/)** - How to extend functionality
### User Guides
- **[CLI Reference](../../users/cli-reference/)** - Complete CLI reference
- **[Getting Started](../../getting-started/)** - Quick start guide
- **[Troubleshooting](../../users/troubleshooting/)** - Common issues and solutions
## 🆘 Getting Help
### CLI Support
- **[GitHub Issues](https://github.com/martin-papy/qdrant-loader/issues)** - Report CLI bugs
- **[GitHub Discussions](https://github.com/martin-papy/qdrant-loader/discussions)** - Ask CLI questions
### Contributing to CLI
- **[Contributing Guide](/docs/CONTRIBUTING.md)** - How to contribute
- **[Testing Guide](../testing/)** - Testing CLI functionality
---
**Ready to develop with the CLI?** Start with the basic commands above or check out the [Architecture Overview](../architecture/) for detailed system design information.
