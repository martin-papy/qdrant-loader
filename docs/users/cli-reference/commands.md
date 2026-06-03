# CLI Commands Reference

This comprehensive reference covers all QDrant Loader commands with detailed examples, use cases, and practical scenarios. The QDrant Loader CLI provides essential commands for data ingestion, configuration management, and project administration.

## 🎯 Overview

QDrant Loader provides a focused command-line interface for data ingestion and management. Commands are organized into logical groups for different aspects of the system.

### Available Commands

```text
🚀 Setup          - setup (interactive config generation)
📊 Data Management - init, ingest
🔧 Configuration  - config (includes project information)
```

## 🚀 Setup Command

### `qdrant-loader setup`

Interactive setup wizard that generates `config.yaml` and `.env` files for your workspace. This is the fastest way to get started with QDrant Loader.

#### Basic Usage

```bash
# Interactive mode — prompts for workspace folder and setup mode
qdrant-loader setup

# Quick start with defaults (localfile source pointing to ./docs)
qdrant-loader setup --output-dir ./my-workspace --mode default

# Interactive wizard with source selection
qdrant-loader setup --output-dir ./my-workspace --mode normal

# Full control over global settings and multi-project config
qdrant-loader setup --output-dir ./my-workspace --mode advanced
```

#### Options

- `--output-dir PATH` - Directory to write `config.yaml` and `.env` files to. If omitted, you are prompted interactively.
- `--mode [default|normal|advanced]` - Setup mode. If omitted, a TUI selector is shown.

#### Setup Modes

| Mode         | Description                                                                                                            | Best For               |
| ------------ | ---------------------------------------------------------------------------------------------------------------------- | ---------------------- |
| **default**  | Creates a localfile source pointing to `<workspace>/docs/` with no prompts                                             | Quick start, testing   |
| **normal**   | Interactive wizard — prompts for Qdrant URL, API keys, and data sources (git, confluence, jira, publicdocs, localfile) | Most users             |
| **advanced** | Full control — configure embedding model, vector size, chunking, reranking, and multi-project setup                    | Production deployments |

#### What Gets Generated

```text
<output-dir>/
├── config.yaml    # Configuration with your selected sources
├── .env           # Environment variables (API keys, credentials)
└── docs/          # (default mode only) Directory for local documents
```

All source configurations include `enable_file_conversion: true` by default, enabling automatic conversion of PDF, DOCX, XLSX, and other binary formats.

#### Examples

```bash
# Set up a workspace for ingesting local documentation
qdrant-loader setup --output-dir ./docs-workspace --mode default
cd docs-workspace
# Place your documents in the docs/ folder, then:
qdrant-loader init --workspace .
qdrant-loader ingest --workspace .

# Set up with Confluence and Git sources
qdrant-loader setup --output-dir ./team-kb --mode normal
# Follow the prompts to configure each source

# Advanced multi-project setup
qdrant-loader setup --output-dir ./production --mode advanced
# Configure embedding model, chunking strategy, and multiple projects
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

## 💼 Service Management Commands

### `qdrant-loader serve`

Run the QDrant Loader as a background service with automatic job scheduling and processing.

#### Basic Usage

```bash
# Run with workspace (finds config.yaml automatically)
qdrant-loader serve --workspace .

# Run with explicit configuration files
qdrant-loader serve --config config.yaml --env .env

# Run with debug logging
qdrant-loader serve --log-level DEBUG
```

#### Options for Serve Command

- `--workspace PATH` - Workspace directory containing config.yaml and .env files
- `--config PATH` - Path to configuration file
- `--env PATH` - Path to environment file
- `--log-level LEVEL` - Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Default: INFO

#### How It Works

The `serve` command:

1. **Loads configuration** from workspace or specified config files
2. **Initializes job queue** in the state database
3. **Starts scheduler** that periodically creates incremental pull jobs based on configured interval
4. **Launches worker pool** using `global.workers.runtime` settings from config
5. **Monitors gracefully** for SIGTERM/SIGINT signals for clean shutdown

#### Job Processing Flow

```
┌─────────────────────────────────────────────┐
│  Scheduler                                   │
│  (runs every N seconds)                      │
└─────────┬───────────────────────────────────┘
          │
          ├─→ Creates INCREMENTAL_PULL jobs
          │   for each configured source
          │
┌─────────▼───────────────────────────────────┐
│  Job Queue (SQLite)                          │
│  - pending jobs                              │
│  - running jobs                              │
│  - completed/failed jobs                     │
└─────────┬───────────────────────────────────┘
          │
          ├─→ Workers claim jobs
          │   (bounded concurrency)
          │
┌─────────▼───────────────────────────────────┐
│  Worker Pool (configurable workers)          │
│  - Process documents from sources            │
│  - Generate embeddings                       │
│  - Index into QDrant                         │
└─────────────────────────────────────────────┘
```

#### Worker Runtime Tuning

`qdrant-loader serve` reads worker runtime knobs from `global.workers.runtime`:

- `worker_count` - Number of concurrent queue workers.
- `lease_seconds` - Visibility lease duration when claiming a job.
- `max_attempts` - Maximum claim attempts before marking a job failed.
- `retry_backoff_base_seconds` - Exponential retry base (0 disables backoff).

When the queue is empty, workers wait on queue notifications instead of 1-second
polling, and still wake up on `lease_seconds` timeout to reclaim expired running
jobs.

#### Examples

```bash
# Basic service — ingest documents on schedule
qdrant-loader serve --workspace my-project

# Production setup with debug logging
qdrant-loader serve --workspace /opt/qdrant-loader --log-level INFO

# Development with explicit files
qdrant-loader serve --config dev.yaml --env dev.env
```

#### Graceful Shutdown

- **Ctrl+C** (SIGINT) - Stop accepting new jobs, wait for in-flight jobs to complete
- **kill -TERM** (SIGTERM) - Same as Ctrl+C
- All running jobs complete before shutdown
- Job state is persisted to database for recovery on restart

---

## 💼 Job Administration Commands

### `qdrant-loader jobs`

Inspect and manage the job queue. These commands help you monitor, debug, and manually control jobs without restarting the service.

#### Job Status Overview

Jobs have these statuses:

- **pending** - Waiting to be processed
- **running** - Currently being processed by a worker
- **done** - Successfully completed
- **failed** - Encountered an error during processing

### `qdrant-loader jobs list`

List jobs in the queue with optional filtering.

#### Basic Usage

```bash
# List all jobs
qdrant-loader jobs list

# List only pending jobs
qdrant-loader jobs list --status pending

# List completed jobs
qdrant-loader jobs list --status done

# List failed jobs
qdrant-loader jobs list --status failed
```

#### Options for Jobs List Command

- `--workspace PATH` - Workspace directory (defaults to current directory)
- `--config PATH` - Path to configuration file
- `--env PATH` - Path to environment file
- `--status [pending|running|done|failed]` - Filter by job status
- `--limit N` - Maximum number of jobs to display (default: 50)
- `--json` - Output results as JSON for scripting

#### Examples

```bash
# Check how many jobs are waiting to be processed
qdrant-loader jobs list --status pending

# Count pending jobs programmatically
qdrant-loader jobs list --status pending --json | jq length

# Monitor running jobs
qdrant-loader jobs list --status running

# Review recently completed jobs
qdrant-loader jobs list --status done --limit 10
```

### `qdrant-loader jobs trigger`

Manually enqueue an ingestion job for a specific source.

#### Basic Usage

```bash
# Trigger an incremental pull job
qdrant-loader jobs trigger --source-type git --source my-repo --mode incremental --project my-project

# Trigger for a specific project
qdrant-loader jobs trigger --source-type git --source my-repo --mode incremental --project my-project

# Trigger a full reprocessing job (bulk)
qdrant-loader jobs trigger --source-type git --source my-repo --mode bulk --project my-project
```

#### Options for Jobs Trigger Command

- `--workspace PATH` - Workspace directory (defaults to current directory)
- `--config PATH` - Path to configuration file
- `--env PATH` - Path to environment file
- `--source-type TEXT` - Source type (git, confluence, jira, etc.) - **Required**
- `--source TEXT` - Source name - **Required**
- `--mode [bulk|incremental]` - Job mode. Default: incremental
- `--project TEXT` - Project ID - **Required**

#### Source Types

- **git** - Git repositories
- **confluence** - Confluence Cloud/Data Center
- **jira** - JIRA Cloud/Data Center
- **localfile** - Local file systems
- **publicdocs** - Public documentation

#### Examples

```bash
# Manually trigger a Git repo pull outside the normal schedule
qdrant-loader jobs trigger --source-type git --source my-repo --mode incremental --project my-project

# Trigger for a specific project
qdrant-loader jobs trigger --source-type confluence --source team-space --mode incremental --project documentation

# Bulk pull (reprocess everything)
qdrant-loader jobs trigger --source-type git --source my-repo --mode bulk --project my-project
```

#### Bulk vs Incremental

- `--mode incremental`: Runs normal incremental logic (uses ingestion state to detect changed/new content).
- `--mode bulk`: Forces full reprocessing for the selected source and project (bypasses change detection).

Use `bulk` when:

- You changed chunking/embedding settings and want full re-index.
- You suspect stale state in the state database.
- You need a one-time backfill after connector/config changes.

#### Do You Need Config Changes for Bulk?

- No special `workers` config is required for manual `jobs trigger --mode bulk`.
- You still need a valid source in `projects.<project_id>.sources` that matches:
  - `--project`
  - `--source-type`
  - `--source`
- `global.workers.schedules.incremental_pull` is only for periodic scheduler behavior in `serve` mode.

#### How to Test Bulk Mode

```bash
# 1) Ensure service is running
qdrant-loader serve --config config.yaml --env .env

# 2) Trigger one bulk job for your source
qdrant-loader jobs trigger --config config.yaml --env .env \
  --source-type confluence --source AUTO-Confluence-project-1 \
  --mode bulk --project Jira-test

# 3) Monitor lifecycle
qdrant-loader jobs list --config config.yaml --env .env --status pending
qdrant-loader jobs list --config config.yaml --env .env --status running
qdrant-loader jobs list --config config.yaml --env .env --status done
qdrant-loader jobs list --config config.yaml --env .env --status failed
```

### `qdrant-loader jobs retry`

Retry a failed job by resetting it to pending status.

Retry preserves `attempts` history; it does not reset attempts to zero.

#### Basic Usage

```bash
# Retry job with ID 5
qdrant-loader jobs retry 5

# Verify before retrying
qdrant-loader jobs list --status failed
qdrant-loader jobs retry 5
```

#### Options for Jobs Retry Command

- `--workspace PATH` - Workspace directory (defaults to current directory)
- `--config PATH` - Path to configuration file
- `--env PATH` - Path to environment file
- `JOB_ID` - Job identifier (required, positional argument)

#### Examples

```bash
# Find and retry failed jobs
qdrant-loader jobs list --status failed --json | jq '.[0].id'
qdrant-loader jobs retry 42

# Retry multiple jobs
for job_id in 41 42 43; do
  qdrant-loader jobs retry $job_id
done
```

### `qdrant-loader jobs cancel`

Cancel a pending job.

#### Basic Usage

```bash
# Cancel job with ID 5
qdrant-loader jobs cancel 5

# Cancel with confirmation
qdrant-loader jobs list --status running
qdrant-loader jobs cancel 10
```

#### Options for Jobs Cancel Command

- `--workspace PATH` - Workspace directory (defaults to current directory)
- `--config PATH` - Path to configuration file
- `--env PATH` - Path to environment file
- `JOB_ID` - Job identifier (required, positional argument)

#### Examples

```bash
# Cancel a running job
qdrant-loader jobs list --status running
qdrant-loader jobs cancel 42

# Cancel all pending jobs for a source (requires scripting)
qdrant-loader jobs list --status pending --json | \
  jq '.[] | select(.type=="INCREMENTAL_PULL" and .payload.source=="my-repo") | .id' | \
  xargs -I {} qdrant-loader jobs cancel {}
```

---

## 🔄 Exit Codes

All commands use standard exit codes:

| Code | Meaning             | Description                                 |
| ---- | ------------------- | ------------------------------------------- |
| `0`  | Success             | Command completed successfully              |
| `1`  | General error       | Command failed due to an error              |
| `2`  | Configuration error | Invalid configuration or missing settings   |
| `3`  | Connection error    | Failed to connect to data sources or QDrant |
| `4`  | Processing error    | Error during data processing                |

## 📚 Related Documentation

- **[CLI Reference Overview](./README.md)** - CLI overview and quick reference
- **[Configuration Reference](../configuration/)** - Configuration file options
- **[Troubleshooting](../troubleshooting/)** - Common CLI issues and solutions

---

**Ready to use the commands?** Start with `qdrant-loader --help` to explore the available options, or follow the [Getting Started Guide](../../getting-started/) for a complete walkthrough.
