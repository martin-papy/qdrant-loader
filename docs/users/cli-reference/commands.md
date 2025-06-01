# CLI Commands Reference

This comprehensive reference covers all QDrant Loader commands with detailed examples, use cases, and practical scenarios. Whether you're a power user or building automation, this guide provides everything you need to master the command-line interface.

## 🎯 Overview

QDrant Loader provides a rich command-line interface for data ingestion, management, and monitoring. Commands are organized into logical groups for different aspects of the system.

### Command Categories

```
📊 Data Management    - load, update, delete, status
🔧 Configuration     - config, init, validate
🔍 Search & Query    - search, find, explore
📁 Collection Ops    - collection, workspace
🔌 MCP Server        - mcp-server, serve
🛠️ Maintenance      - clean, optimize, backup
📈 Monitoring        - logs, metrics, health
```

## 📊 Data Management Commands

### `qdrant-loader load`

Load data from configured sources into QDrant.

#### Basic Usage

```bash
# Load all configured data sources
qdrant-loader load

# Load specific data source
qdrant-loader load --source git

# Load with custom configuration
qdrant-loader load --config production.yaml

# Load specific repository
qdrant-loader load --source git --url https://github.com/company/docs
```

#### Advanced Options

```bash
# Load with custom collection
qdrant-loader load --collection my_docs --source confluence

# Load with filtering
qdrant-loader load --source git --include "*.md,*.rst" --exclude "node_modules/"

# Load with custom chunk size
qdrant-loader load --chunk-size 1500 --chunk-overlap 300

# Force reload (ignore existing data)
qdrant-loader load --force --source confluence

# Dry run (show what would be loaded)
qdrant-loader load --dry-run --source git

# Load with progress tracking
qdrant-loader load --verbose --progress

# Load in background
qdrant-loader load --background --log-file /var/log/qdrant-loader.log
```

#### Source-Specific Loading

```bash
# Git repositories
qdrant-loader load --source git \
  --url https://github.com/company/docs \
  --branch main \
  --include "docs/**/*.md"

# Confluence spaces
qdrant-loader load --source confluence \
  --spaces "DOCS,TECH" \
  --include-attachments

# JIRA projects
qdrant-loader load --source jira \
  --projects "PROJ,DOCS" \
  --issue-types "Story,Bug,Task"

# Local files
qdrant-loader load --source local \
  --path /path/to/docs \
  --recursive \
  --include "*.pdf,*.docx"

# Public documentation
qdrant-loader load --source public \
  --url https://docs.example.com \
  --depth 3
```

#### Batch Operations

```bash
# Load multiple sources
qdrant-loader load --sources git,confluence,local

# Load with custom batch size
qdrant-loader load --batch-size 200 --parallel-workers 8

# Load with rate limiting
qdrant-loader load --rate-limit 10 --source confluence

# Load with retry configuration
qdrant-loader load --max-retries 5 --retry-delay 2
```

### `qdrant-loader update`

Update existing data with incremental changes.

#### Basic Usage

```bash
# Update all sources (incremental)
qdrant-loader update

# Update specific source
qdrant-loader update --source git

# Update with change detection
qdrant-loader update --detect-changes --source confluence

# Update modified files only
qdrant-loader update --modified-only --since "2024-01-01"
```

#### Advanced Update Options

```bash
# Update with conflict resolution
qdrant-loader update --conflict-resolution merge --source git

# Update with custom timestamp
qdrant-loader update --since "2024-01-15T10:00:00Z"

# Update specific collection
qdrant-loader update --collection team_docs --source confluence

# Update with validation
qdrant-loader update --validate --source git

# Selective update by pattern
qdrant-loader update --include "*.md" --exclude "draft/*"
```

### `qdrant-loader delete`

Remove data from QDrant collections.

#### Basic Usage

```bash
# Delete by source
qdrant-loader delete --source git

# Delete by collection
qdrant-loader delete --collection old_docs

# Delete by filter
qdrant-loader delete --filter "source:confluence AND space:OLD"

# Delete by date range
qdrant-loader delete --before "2024-01-01"
```

#### Advanced Deletion

```bash
# Delete with confirmation
qdrant-loader delete --collection temp_docs --confirm

# Delete with backup
qdrant-loader delete --backup-before --collection old_docs

# Soft delete (mark as deleted)
qdrant-loader delete --soft --filter "status:archived"

# Delete by metadata
qdrant-loader delete --metadata "project:discontinued"

# Bulk delete with pattern
qdrant-loader delete --pattern "temp_*" --collections
```

### `qdrant-loader status`

Show system and data status.

#### Basic Usage

```bash
# Overall system status
qdrant-loader status

# Detailed status
qdrant-loader status --detailed

# Status for specific collection
qdrant-loader status --collection team_docs

# Status with metrics
qdrant-loader status --metrics
```

#### Status Information

```bash
# Connection status
qdrant-loader status --check-connections

# Data source status
qdrant-loader status --sources

# Collection statistics
qdrant-loader status --collections --stats

# Recent activity
qdrant-loader status --recent --limit 10

# Health check
qdrant-loader status --health

# Performance metrics
qdrant-loader status --performance
```

## 🔧 Configuration Commands

### `qdrant-loader config`

Manage configuration settings.

#### Configuration Display

```bash
# Show current configuration
qdrant-loader config show

# Show configuration with sources
qdrant-loader config show --sources

# Show specific section
qdrant-loader config show --section qdrant

# Show effective configuration (merged)
qdrant-loader config show --effective

# Show configuration as JSON
qdrant-loader config show --format json

# Show sensitive values (masked by default)
qdrant-loader config show --show-secrets
```

#### Configuration Validation

```bash
# Validate configuration
qdrant-loader config validate

# Validate specific file
qdrant-loader config validate --file production.yaml

# Test configuration connectivity
qdrant-loader config test

# Test specific connections
qdrant-loader config test --connections qdrant,openai

# Validate and fix common issues
qdrant-loader config validate --fix
```

#### Configuration Management

```bash
# Set configuration value
qdrant-loader config set qdrant.collection_name new_collection

# Get configuration value
qdrant-loader config get openai.model

# Unset configuration value
qdrant-loader config unset qdrant.api_key

# Reset to defaults
qdrant-loader config reset --section processing

# Export configuration
qdrant-loader config export --output current-config.yaml

# Import configuration
qdrant-loader config import --input new-config.yaml
```

### `qdrant-loader init`

Initialize new QDrant Loader projects.

#### Project Initialization

```bash
# Initialize basic project
qdrant-loader init

# Initialize with template
qdrant-loader init --template single-project

# Initialize for specific environment
qdrant-loader init --env production

# Initialize with custom name
qdrant-loader init --name "My Knowledge Base"

# Initialize with data sources
qdrant-loader init --sources git,confluence
```

#### Template Options

```bash
# Available templates
qdrant-loader init --list-templates

# Single project template
qdrant-loader init --template single-project \
  --name "Documentation Hub" \
  --sources git,confluence

# Multi-project template
qdrant-loader init --template multi-project \
  --projects "frontend,backend,mobile"

# Team workspace template
qdrant-loader init --template team-workspace \
  --team-name "Engineering Team"

# Custom template
qdrant-loader init --template custom \
  --template-file /path/to/template.yaml
```

## 🔍 Search & Query Commands

### `qdrant-loader search`

Search through your knowledge base.

#### Basic Search

```bash
# Simple search
qdrant-loader search "API documentation"

# Search with limit
qdrant-loader search "deployment guide" --limit 5

# Search in specific collection
qdrant-loader search "authentication" --collection backend_docs

# Search with similarity threshold
qdrant-loader search "database setup" --threshold 0.8
```

#### Advanced Search

```bash
# Semantic search
qdrant-loader search "How to deploy the application" \
  --type semantic \
  --limit 10

# Keyword search
qdrant-loader search "docker kubernetes" \
  --type keyword \
  --operator AND

# Hybrid search
qdrant-loader search "API rate limiting" \
  --type hybrid \
  --semantic-weight 0.7 \
  --keyword-weight 0.3

# Search with filters
qdrant-loader search "configuration" \
  --filter "source:confluence AND space:DOCS"

# Search with metadata
qdrant-loader search "testing" \
  --metadata "project:backend,type:guide"
```

#### Search Output Options

```bash
# JSON output
qdrant-loader search "API docs" --output json

# Detailed results
qdrant-loader search "setup guide" --detailed

# Show snippets
qdrant-loader search "installation" --snippets --snippet-length 200

# Show metadata
qdrant-loader search "configuration" --show-metadata

# Export results
qdrant-loader search "troubleshooting" --export results.json

# Interactive search
qdrant-loader search --interactive
```

### `qdrant-loader find`

Find specific documents or content.

#### Document Finding

```bash
# Find by filename
qdrant-loader find --filename "README.md"

# Find by path pattern
qdrant-loader find --path "docs/**/*.md"

# Find by content type
qdrant-loader find --type pdf

# Find by source
qdrant-loader find --source confluence --space DOCS

# Find by date range
qdrant-loader find --after "2024-01-01" --before "2024-02-01"
```

#### Advanced Finding

```bash
# Find with regex
qdrant-loader find --pattern "api.*guide" --regex

# Find duplicates
qdrant-loader find --duplicates --similarity 0.9

# Find orphaned documents
qdrant-loader find --orphaned

# Find by size
qdrant-loader find --min-size 1KB --max-size 1MB

# Find by language
qdrant-loader find --language python --type code
```

### `qdrant-loader explore`

Explore and analyze your knowledge base.

#### Content Exploration

```bash
# Explore collections
qdrant-loader explore --collections

# Explore data sources
qdrant-loader explore --sources

# Explore content types
qdrant-loader explore --content-types

# Explore topics
qdrant-loader explore --topics --limit 20

# Explore similar documents
qdrant-loader explore --similar "API documentation" --limit 10
```

#### Analytics and Insights

```bash
# Content statistics
qdrant-loader explore --stats

# Source distribution
qdrant-loader explore --distribution --by source

# Content freshness
qdrant-loader explore --freshness

# Popular content
qdrant-loader explore --popular --period 30d

# Content gaps
qdrant-loader explore --gaps --topics
```

## 📁 Collection & Workspace Commands

### `qdrant-loader collection`

Manage QDrant collections.

#### Collection Operations

```bash
# List collections
qdrant-loader collection list

# Create collection
qdrant-loader collection create my_docs \
  --description "My documentation collection"

# Delete collection
qdrant-loader collection delete old_docs --confirm

# Rename collection
qdrant-loader collection rename old_name new_name

# Copy collection
qdrant-loader collection copy source_docs backup_docs
```

#### Collection Management

```bash
# Show collection info
qdrant-loader collection info team_docs

# Collection statistics
qdrant-loader collection stats --all

# Optimize collection
qdrant-loader collection optimize team_docs

# Backup collection
qdrant-loader collection backup team_docs \
  --output team_docs_backup.json

# Restore collection
qdrant-loader collection restore \
  --input team_docs_backup.json \
  --collection team_docs_restored

# Merge collections
qdrant-loader collection merge source1,source2 target
```

### `qdrant-loader workspace`

Manage workspace configurations.

#### Workspace Operations

```bash
# Show workspace status
qdrant-loader workspace status

# List workspaces
qdrant-loader workspace list

# Switch workspace
qdrant-loader workspace switch production

# Create workspace
qdrant-loader workspace create development \
  --template single-project

# Delete workspace
qdrant-loader workspace delete old_workspace --confirm
```

#### Workspace Management

```bash
# Add project to workspace
qdrant-loader workspace add-project backend \
  --collection backend_docs \
  --sources git,confluence

# Remove project
qdrant-loader workspace remove-project old_project

# Workspace backup
qdrant-loader workspace backup \
  --output workspace_backup.yaml

# Workspace restore
qdrant-loader workspace restore \
  --input workspace_backup.yaml

# Workspace sync
qdrant-loader workspace sync --all-projects
```

## 🔌 MCP Server Commands

### `qdrant-loader mcp-server`

Manage the MCP server for AI integration.

#### Server Operations

```bash
# Start MCP server
qdrant-loader mcp-server start

# Start with custom port
qdrant-loader mcp-server start --port 8080

# Start in background
qdrant-loader mcp-server start --daemon

# Stop MCP server
qdrant-loader mcp-server stop

# Restart MCP server
qdrant-loader mcp-server restart

# Server status
qdrant-loader mcp-server status
```

#### Server Configuration

```bash
# Show server config
qdrant-loader mcp-server config

# Test server connectivity
qdrant-loader mcp-server test

# Server logs
qdrant-loader mcp-server logs --tail 100

# Server metrics
qdrant-loader mcp-server metrics

# Install for Cursor
qdrant-loader mcp-server install-cursor

# Install for Windsurf
qdrant-loader mcp-server install-windsurf
```

### `qdrant-loader serve`

Alternative server command for development.

```bash
# Serve in development mode
qdrant-loader serve --dev

# Serve with auto-reload
qdrant-loader serve --reload

# Serve with debug logging
qdrant-loader serve --debug

# Serve on specific interface
qdrant-loader serve --host 0.0.0.0 --port 8080
```

## 🛠️ Maintenance Commands

### `qdrant-loader clean`

Clean up data and optimize storage.

#### Cleanup Operations

```bash
# Clean temporary files
qdrant-loader clean --temp

# Clean cache
qdrant-loader clean --cache

# Clean logs
qdrant-loader clean --logs --older-than 30d

# Clean orphaned data
qdrant-loader clean --orphaned

# Full cleanup
qdrant-loader clean --all --confirm
```

#### Advanced Cleanup

```bash
# Clean by collection
qdrant-loader clean --collection temp_docs

# Clean by source
qdrant-loader clean --source git --removed-files

# Clean duplicates
qdrant-loader clean --duplicates --similarity 0.95

# Clean with dry run
qdrant-loader clean --dry-run --all

# Clean with backup
qdrant-loader clean --backup-before --orphaned
```

### `qdrant-loader optimize`

Optimize performance and storage.

#### Optimization Operations

```bash
# Optimize all collections
qdrant-loader optimize

# Optimize specific collection
qdrant-loader optimize --collection team_docs

# Optimize indexes
qdrant-loader optimize --indexes

# Optimize storage
qdrant-loader optimize --storage --vacuum

# Optimize with statistics
qdrant-loader optimize --stats
```

### `qdrant-loader backup`

Backup data and configurations.

#### Backup Operations

```bash
# Full backup
qdrant-loader backup --output full_backup.tar.gz

# Backup collections only
qdrant-loader backup --collections --output collections_backup.json

# Backup configuration
qdrant-loader backup --config --output config_backup.yaml

# Incremental backup
qdrant-loader backup --incremental --since last_backup

# Backup to cloud
qdrant-loader backup --s3 s3://my-bucket/backups/
```

## 📈 Monitoring Commands

### `qdrant-loader logs`

View and manage logs.

#### Log Viewing

```bash
# View recent logs
qdrant-loader logs

# Tail logs
qdrant-loader logs --tail --lines 100

# Filter logs by level
qdrant-loader logs --level ERROR --since 1h

# Filter logs by component
qdrant-loader logs --component mcp-server

# Search logs
qdrant-loader logs --search "authentication failed"

# Export logs
qdrant-loader logs --export logs_export.json --since 24h
```

### `qdrant-loader metrics`

View performance metrics.

#### Metrics Display

```bash
# Current metrics
qdrant-loader metrics

# Historical metrics
qdrant-loader metrics --history --period 24h

# Specific metrics
qdrant-loader metrics --metric search_latency,memory_usage

# Metrics export
qdrant-loader metrics --export metrics.json

# Real-time metrics
qdrant-loader metrics --watch --interval 5s
```

### `qdrant-loader health`

Check system health.

#### Health Checks

```bash
# Overall health
qdrant-loader health

# Detailed health check
qdrant-loader health --detailed

# Component health
qdrant-loader health --components qdrant,openai,mcp-server

# Health with remediation
qdrant-loader health --fix

# Health monitoring
qdrant-loader health --monitor --interval 60s
```

## 🔗 Command Chaining and Automation

### Pipeline Operations

```bash
# Load and optimize
qdrant-loader load --source git && qdrant-loader optimize

# Update and backup
qdrant-loader update && qdrant-loader backup --incremental

# Clean and optimize
qdrant-loader clean --temp && qdrant-loader optimize --indexes

# Full maintenance pipeline
qdrant-loader update && \
qdrant-loader clean --orphaned && \
qdrant-loader optimize && \
qdrant-loader backup --incremental
```

### Conditional Operations

```bash
# Load if not exists
qdrant-loader status --collection docs || qdrant-loader load --source git

# Update if changed
if qdrant-loader status --check-changes; then
  qdrant-loader update --source confluence
fi

# Backup before major operations
qdrant-loader backup --quick && qdrant-loader load --force
```

## 📋 Command Reference Quick Guide

### Essential Commands

```bash
# Get started
qdrant-loader init
qdrant-loader config validate
qdrant-loader load

# Daily operations
qdrant-loader status
qdrant-loader update
qdrant-loader search "query"

# Maintenance
qdrant-loader clean --temp
qdrant-loader optimize
qdrant-loader backup

# MCP Server
qdrant-loader mcp-server start
qdrant-loader mcp-server status
```

### Common Patterns

```bash
# Development workflow
qdrant-loader init --template single-project
qdrant-loader load --source local --path ./docs
qdrant-loader mcp-server start --dev

# Production deployment
qdrant-loader config validate --env production
qdrant-loader load --all-sources
qdrant-loader mcp-server start --daemon

# Maintenance routine
qdrant-loader update --all-sources
qdrant-loader clean --cache --logs
qdrant-loader optimize --all
qdrant-loader backup --incremental
```

## 🔗 Related Documentation

- **[Options and Flags Reference](./options-and-flags.md)** - Detailed flag documentation
- **[Scripting and Automation](./scripting-automation.md)** - Automation examples and scripts
- **[Configuration Reference](../configuration/config-file-reference.md)** - Configuration options
- **[Troubleshooting](../troubleshooting/common-issues.md)** - Common command issues

---

**CLI mastery achieved!** 🎉

This comprehensive command reference provides everything you need to use QDrant Loader effectively from the command line, whether for daily operations, automation, or advanced workflows.
