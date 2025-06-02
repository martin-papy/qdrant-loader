# Scripting and Automation

This guide shows how to automate QDrant Loader operations using shell scripts, cron jobs, CI/CD pipelines, and monitoring systems. All examples use only the actual implemented CLI commands and options.

## 🎯 Overview

Automation is essential for maintaining up-to-date knowledge bases and reducing manual overhead. QDrant Loader's CLI is designed to be automation-friendly with proper exit codes, structured output, and robust error handling.

### Available Commands for Automation

- **`init`** - Initialize QDrant collection
- **`ingest`** - Process and load data from sources
- **`config`** - Display current configuration
- **`project list`** - List all configured projects
- **`project status`** - Show project status
- **`project validate`** - Validate project configurations

### Automation Categories

```
📅 Scheduled Tasks     - Cron jobs, periodic updates
🔄 CI/CD Integration   - GitHub Actions, GitLab CI
📊 Monitoring Scripts  - Health checks, status monitoring
🛠️ Maintenance Tasks  - Regular ingestion, validation
🔧 Deployment Scripts  - Setup, configuration management
```

## 📅 Scheduled Automation

### Basic Cron Jobs

#### Daily Data Ingestion

```bash
#!/bin/bash
# daily-ingest.sh - Daily knowledge base update

set -euo pipefail

# Configuration
WORKSPACE_DIR="/opt/qdrant-loader/workspace"
LOG_FILE="/var/log/qdrant-loader/daily-ingest.log"
LOCK_FILE="/var/run/qdrant-loader-ingest.lock"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log "ERROR: $1"
    cleanup
    exit 1
}

# Lock management
acquire_lock() {
    if [ -f "$LOCK_FILE" ]; then
        local pid=$(cat "$LOCK_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            log "Ingestion already running (PID: $pid)"
            exit 1
        else
            log "Removing stale lock file"
            rm -f "$LOCK_FILE"
        fi
    fi
    echo $$ > "$LOCK_FILE"
}

cleanup() {
    rm -f "$LOCK_FILE"
}

trap cleanup EXIT

# Main ingestion process
main() {
    log "Starting daily ingestion process"
    
    acquire_lock
    
    # Change to workspace directory
    cd "$WORKSPACE_DIR" || error_exit "Cannot access workspace directory"
    
    # Validate configuration
    log "Validating configuration"
    if ! qdrant-loader --workspace . config >/dev/null 2>&1; then
        error_exit "Configuration validation failed"
    fi
    
    # Run ingestion with detailed logging
    log "Starting data ingestion"
    if qdrant-loader --log-level INFO --workspace . ingest; then
        log "Data ingestion completed successfully"
    else
        error_exit "Data ingestion failed"
    fi
    
    # Validate projects after ingestion
    log "Validating projects"
    if qdrant-loader project --workspace . validate; then
        log "Project validation passed"
    else
        log "WARNING: Project validation failed"
    fi
    
    log "Daily ingestion process completed"
}

main "$@"
```

#### Crontab Configuration

```bash
# /etc/crontab - System cron configuration

# Daily ingestion at 2 AM
0 2 * * * qdrant-loader /opt/qdrant-loader/scripts/daily-ingest.sh

# Hourly project status check during business hours
0 9-17 * * 1-5 qdrant-loader /opt/qdrant-loader/scripts/status-check.sh

# Weekly configuration validation on Sundays at 1 AM
0 1 * * 0 qdrant-loader /opt/qdrant-loader/scripts/weekly-validation.sh
```

### Advanced Scheduled Scripts

#### Intelligent Project-Based Ingestion

```bash
#!/bin/bash
# project-ingest.sh - Smart project-based ingestion

set -euo pipefail

WORKSPACE_DIR="${WORKSPACE_DIR:-/opt/qdrant-loader/workspace}"
LOG_FILE="${LOG_FILE:-/var/log/qdrant-loader/project-ingest.log}"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Get list of projects
get_projects() {
    cd "$WORKSPACE_DIR"
    qdrant-loader project --workspace . list --format json | jq -r '.[].project_id'
}

# Ingest specific project
ingest_project() {
    local project_id="$1"
    
    log "Processing project: $project_id"
    
    # Check project status first
    if ! qdrant-loader project --workspace . status --project-id "$project_id" --format json >/dev/null 2>&1; then
        log "WARNING: Project $project_id status check failed, skipping"
        return 1
    fi
    
    # Run ingestion for specific project
    if qdrant-loader --log-level INFO --workspace . ingest --project "$project_id"; then
        log "Successfully ingested project: $project_id"
        return 0
    else
        log "ERROR: Failed to ingest project: $project_id"
        return 1
    fi
}

# Main function
main() {
    log "Starting project-based ingestion"
    
    cd "$WORKSPACE_DIR" || {
        log "ERROR: Cannot access workspace directory: $WORKSPACE_DIR"
        exit 1
    }
    
    # Get list of projects
    local projects
    if ! projects=$(get_projects); then
        log "ERROR: Failed to get project list"
        exit 1
    fi
    
    if [ -z "$projects" ]; then
        log "No projects found"
        exit 0
    fi
    
    # Process each project
    local success_count=0
    local total_count=0
    
    while IFS= read -r project_id; do
        if [ -n "$project_id" ]; then
            total_count=$((total_count + 1))
            if ingest_project "$project_id"; then
                success_count=$((success_count + 1))
            fi
        fi
    done <<< "$projects"
    
    log "Project ingestion completed: $success_count/$total_count projects successful"
    
    if [ "$success_count" -eq "$total_count" ]; then
        exit 0
    else
        exit 1
    fi
}

main "$@"
```

## 🔄 CI/CD Integration

### GitHub Actions

#### Automated Documentation Updates

```yaml
# .github/workflows/update-knowledge-base.yml
name: Update Knowledge Base

on:
  push:
    branches: [main]
    paths: ['docs/**', 'README.md']
  schedule:
    # Run daily at 6 AM UTC
    - cron: '0 6 * * *'
  workflow_dispatch:

jobs:
  update-knowledge-base:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout repository
      uses: actions/checkout@v4
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install QDrant Loader
      run: |
        pip install -e packages/qdrant-loader
    
    - name: Setup workspace
      env:
        QDRANT_URL: ${{ secrets.QDRANT_URL }}
        QDRANT_API_KEY: ${{ secrets.QDRANT_API_KEY }}
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      run: |
        # Create workspace directory
        mkdir -p workspace
        cd workspace
        
        # Create configuration
        cat > config.yaml << EOF
        qdrant:
          url: "${QDRANT_URL}"
          api_key: "${QDRANT_API_KEY}"
          collection_name: "github_docs"
        
        openai:
          api_key: "${OPENAI_API_KEY}"
        
        projects:
          github_docs:
            display_name: "GitHub Documentation"
            description: "Documentation from GitHub repository"
            collection_name: "github_docs"
            sources:
              git:
                main_repo:
                  url: "${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}"
                  branch: "main"
                  include_patterns:
                    - "docs/**/*.md"
                    - "README.md"
        EOF
        
        # Create .env file
        cat > .env << EOF
        QDRANT_URL=${QDRANT_URL}
        QDRANT_API_KEY=${QDRANT_API_KEY}
        OPENAI_API_KEY=${OPENAI_API_KEY}
        EOF
    
    - name: Initialize collection
      run: |
        cd workspace
        qdrant-loader --workspace . init --force
    
    - name: Update knowledge base
      run: |
        cd workspace
        qdrant-loader --log-level INFO --workspace . ingest
    
    - name: Verify update
      run: |
        cd workspace
        # Check configuration
        qdrant-loader --workspace . config
        
        # List projects
        qdrant-loader project --workspace . list
        
        # Check project status
        qdrant-loader project --workspace . status --format json
    
    - name: Notify on failure
      if: failure()
      uses: 8398a7/action-slack@v3
      with:
        status: failure
        webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

#### Multi-Environment Deployment

```yaml
# .github/workflows/deploy-knowledge-base.yml
name: Deploy Knowledge Base

on:
  release:
    types: [published]

jobs:
  deploy:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        environment: [staging, production]
    
    environment: ${{ matrix.environment }}
    
    steps:
    - name: Checkout
      uses: actions/checkout@v4
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install QDrant Loader
      run: |
        pip install -e packages/qdrant-loader
        pip install -e packages/qdrant-loader-mcp-server
    
    - name: Deploy to ${{ matrix.environment }}
      env:
        QDRANT_URL: ${{ secrets.QDRANT_URL }}
        QDRANT_API_KEY: ${{ secrets.QDRANT_API_KEY }}
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      run: |
        # Setup workspace with environment-specific configuration
        mkdir -p workspace
        cp configs/${{ matrix.environment }}/config.yaml workspace/
        cp configs/${{ matrix.environment }}/.env workspace/
        
        cd workspace
        
        # Initialize collection
        qdrant-loader --workspace . init --force
        
        # Load all data
        qdrant-loader --log-level INFO --workspace . ingest
        
        # Validate deployment
        qdrant-loader project --workspace . validate
```

### GitLab CI

#### Continuous Documentation Integration

```yaml
# .gitlab-ci.yml
stages:
  - validate
  - ingest
  - verify

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"
  WORKSPACE_DIR: "workspace"

cache:
  paths:
    - .cache/pip/

before_script:
  - pip install -e packages/qdrant-loader

validate-config:
  stage: validate
  script:
    - mkdir -p $WORKSPACE_DIR
    - cp configs/production/config.yaml $WORKSPACE_DIR/
    - cp configs/production/.env $WORKSPACE_DIR/
    - cd $WORKSPACE_DIR
    - qdrant-loader --workspace . config
    - qdrant-loader project --workspace . validate
  only:
    - merge_requests
    - main

ingest-data:
  stage: ingest
  script:
    - mkdir -p $WORKSPACE_DIR
    - cp configs/production/config.yaml $WORKSPACE_DIR/
    - cp configs/production/.env $WORKSPACE_DIR/
    - cd $WORKSPACE_DIR
    - qdrant-loader --workspace . init --force
    - qdrant-loader --log-level INFO --workspace . ingest
  only:
    - main
    - schedules

verify-deployment:
  stage: verify
  script:
    - cd $WORKSPACE_DIR
    - qdrant-loader project --workspace . list --format json
    - qdrant-loader project --workspace . status --format json
  only:
    - main
```

## 📊 Monitoring and Health Checks

### Health Check Scripts

#### Basic Health Monitor

```bash
#!/bin/bash
# health-check.sh - Basic system health monitoring

set -euo pipefail

WORKSPACE_DIR="${WORKSPACE_DIR:-/opt/qdrant-loader/workspace}"
LOG_FILE="/var/log/qdrant-loader/health-check.log"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Health check functions
check_configuration() {
    log "Checking configuration..."
    cd "$WORKSPACE_DIR"
    
    if qdrant-loader --workspace . config >/dev/null 2>&1; then
        log "✅ Configuration OK"
        return 0
    else
        log "❌ Configuration check failed"
        return 1
    fi
}

check_projects() {
    log "Checking projects..."
    cd "$WORKSPACE_DIR"
    
    # Get project count
    local project_count
    if project_count=$(qdrant-loader project --workspace . list --format json | jq 'length' 2>/dev/null); then
        if [ "$project_count" -gt 0 ]; then
            log "✅ Found $project_count projects"
            
            # Validate projects
            if qdrant-loader project --workspace . validate >/dev/null 2>&1; then
                log "✅ Project validation passed"
                return 0
            else
                log "❌ Project validation failed"
                return 1
            fi
        else
            log "❌ No projects found"
            return 1
        fi
    else
        log "❌ Failed to get project list"
        return 1
    fi
}

check_mcp_server() {
    log "Checking MCP server..."
    
    # Check if MCP server package is installed
    if python -c "import qdrant_loader_mcp_server" 2>/dev/null; then
        log "✅ MCP server package available"
        return 0
    else
        log "❌ MCP server package not available"
        return 1
    fi
}

# Main health check
main() {
    log "Starting health check"
    
    local failed_checks=()
    
    # Check workspace directory
    if [ ! -d "$WORKSPACE_DIR" ]; then
        log "❌ Workspace directory not found: $WORKSPACE_DIR"
        exit 1
    fi
    
    # Run health checks
    if ! check_configuration; then
        failed_checks+=("Configuration")
    fi
    
    if ! check_projects; then
        failed_checks+=("Projects")
    fi
    
    if ! check_mcp_server; then
        failed_checks+=("MCP Server")
    fi
    
    # Report results
    if [ ${#failed_checks[@]} -eq 0 ]; then
        log "✅ All health checks passed"
        exit 0
    else
        local message="Health check failures: $(IFS=', '; echo "${failed_checks[*]}")"
        log "❌ $message"
        exit 1
    fi
}

main "$@"
```

#### Status Monitoring Script

```bash
#!/bin/bash
# status-monitor.sh - Monitor project status and generate reports

set -euo pipefail

WORKSPACE_DIR="${WORKSPACE_DIR:-/opt/qdrant-loader/workspace}"
REPORT_FILE="/var/log/qdrant-loader/status-report.json"

# Generate status report
generate_report() {
    cd "$WORKSPACE_DIR"
    
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    # Get project list
    local projects
    if projects=$(qdrant-loader project --workspace . list --format json 2>/dev/null); then
        # Get detailed status for each project
        local detailed_status
        detailed_status=$(qdrant-loader project --workspace . status --format json 2>/dev/null)
        
        # Create report
        jq -n \
            --arg timestamp "$timestamp" \
            --argjson projects "$projects" \
            --argjson status "$detailed_status" \
            '{
                timestamp: $timestamp,
                project_count: ($projects | length),
                projects: $projects,
                status: $status
            }' > "$REPORT_FILE"
        
        echo "Status report generated: $REPORT_FILE"
        return 0
    else
        echo "Failed to generate status report"
        return 1
    fi
}

# Main function
main() {
    echo "Generating status report..."
    
    if [ ! -d "$WORKSPACE_DIR" ]; then
        echo "ERROR: Workspace directory not found: $WORKSPACE_DIR"
        exit 1
    fi
    
    if generate_report; then
        echo "Status monitoring completed successfully"
        exit 0
    else
        echo "Status monitoring failed"
        exit 1
    fi
}

main "$@"
```

## 🛠️ Maintenance Scripts

### Configuration Management

```bash
#!/bin/bash
# config-manager.sh - Configuration management and validation

set -euo pipefail

WORKSPACE_DIR="${WORKSPACE_DIR:-/opt/qdrant-loader/workspace}"
BACKUP_DIR="/var/backups/qdrant-loader"

# Backup current configuration
backup_config() {
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local backup_file="$BACKUP_DIR/config_backup_$timestamp.tar.gz"
    
    echo "Creating configuration backup..."
    
    mkdir -p "$BACKUP_DIR"
    
    if tar -czf "$backup_file" -C "$WORKSPACE_DIR" config.yaml .env 2>/dev/null; then
        echo "Configuration backed up to: $backup_file"
        return 0
    else
        echo "Failed to create configuration backup"
        return 1
    fi
}

# Validate configuration
validate_config() {
    echo "Validating configuration..."
    
    cd "$WORKSPACE_DIR"
    
    # Check configuration syntax
    if qdrant-loader --workspace . config >/dev/null 2>&1; then
        echo "✅ Configuration syntax valid"
    else
        echo "❌ Configuration syntax invalid"
        return 1
    fi
    
    # Validate projects
    if qdrant-loader project --workspace . validate; then
        echo "✅ Project configuration valid"
        return 0
    else
        echo "❌ Project configuration invalid"
        return 1
    fi
}

# Deploy new configuration
deploy_config() {
    local config_source="$1"
    
    echo "Deploying configuration from: $config_source"
    
    # Backup current configuration
    if ! backup_config; then
        echo "Failed to backup current configuration"
        return 1
    fi
    
    # Copy new configuration
    if [ -f "$config_source/config.yaml" ]; then
        cp "$config_source/config.yaml" "$WORKSPACE_DIR/"
    else
        echo "ERROR: config.yaml not found in $config_source"
        return 1
    fi
    
    if [ -f "$config_source/.env" ]; then
        cp "$config_source/.env" "$WORKSPACE_DIR/"
    fi
    
    # Validate new configuration
    if validate_config; then
        echo "Configuration deployed and validated successfully"
        return 0
    else
        echo "Configuration validation failed, consider rolling back"
        return 1
    fi
}

# Main function
main() {
    local command="${1:-validate}"
    local source="${2:-}"
    
    case "$command" in
        backup)
            backup_config
            ;;
        validate)
            validate_config
            ;;
        deploy)
            if [ -z "$source" ]; then
                echo "Usage: $0 deploy <config_source_directory>"
                exit 1
            fi
            deploy_config "$source"
            ;;
        *)
            echo "Usage: $0 {backup|validate|deploy} [source]"
            exit 1
            ;;
    esac
}

main "$@"
```

## 📋 Automation Best Practices

### Error Handling Template

```bash
#!/bin/bash
# robust-automation-template.sh - Template for robust automation scripts

set -euo pipefail

# Configuration
SCRIPT_NAME="$(basename "$0")"
LOG_FILE="/var/log/qdrant-loader/${SCRIPT_NAME%.sh}.log"
LOCK_FILE="/var/run/${SCRIPT_NAME%.sh}.lock"
WORKSPACE_DIR="${WORKSPACE_DIR:-/opt/qdrant-loader/workspace}"

# Logging functions
log() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*" | tee -a "$LOG_FILE"
}

log_info() { log "INFO" "$@"; }
log_warn() { log "WARN" "$@"; }
log_error() { log "ERROR" "$@"; }

# Error handling
error_exit() {
    log_error "$1"
    cleanup
    exit 1
}

# Cleanup function
cleanup() {
    if [ -f "$LOCK_FILE" ]; then
        rm -f "$LOCK_FILE"
    fi
}

# Lock management
acquire_lock() {
    if [ -f "$LOCK_FILE" ]; then
        local pid=$(cat "$LOCK_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            error_exit "Script already running (PID: $pid)"
        else
            log_warn "Removing stale lock file"
            rm -f "$LOCK_FILE"
        fi
    fi
    echo $$ > "$LOCK_FILE"
}

# Setup trap for cleanup
trap cleanup EXIT

# Validate environment
validate_environment() {
    if [ ! -d "$WORKSPACE_DIR" ]; then
        error_exit "Workspace directory not found: $WORKSPACE_DIR"
    fi
    
    if [ ! -f "$WORKSPACE_DIR/config.yaml" ]; then
        error_exit "Configuration file not found: $WORKSPACE_DIR/config.yaml"
    fi
}

# Main function template
main() {
    log_info "Starting $SCRIPT_NAME"
    
    acquire_lock
    validate_environment
    
    cd "$WORKSPACE_DIR"
    
    # Your automation logic here using actual CLI commands:
    # - qdrant-loader --workspace . init [--force]
    # - qdrant-loader --workspace . ingest [--project PROJECT] [--source-type TYPE] [--source SOURCE]
    # - qdrant-loader --workspace . config
    # - qdrant-loader project --workspace . list [--format json]
    # - qdrant-loader project --workspace . status [--project-id PROJECT] [--format json]
    # - qdrant-loader project --workspace . validate [--project-id PROJECT]
    
    log_info "$SCRIPT_NAME completed successfully"
}

main "$@"
```

### Environment-Specific Configuration

```bash
#!/bin/bash
# environment-setup.sh - Setup environment-specific configurations

set -euo pipefail

ENVIRONMENT="${1:-development}"
BASE_DIR="/opt/qdrant-loader"
WORKSPACE_DIR="$BASE_DIR/workspace"

setup_environment() {
    local env="$1"
    
    echo "Setting up environment: $env"
    
    # Create workspace directory
    mkdir -p "$WORKSPACE_DIR"
    
    # Copy environment-specific configuration
    if [ -f "$BASE_DIR/configs/$env/config.yaml" ]; then
        cp "$BASE_DIR/configs/$env/config.yaml" "$WORKSPACE_DIR/"
        echo "Copied configuration for $env environment"
    else
        echo "ERROR: Configuration not found for environment: $env"
        exit 1
    fi
    
    # Copy environment file if it exists
    if [ -f "$BASE_DIR/configs/$env/.env" ]; then
        cp "$BASE_DIR/configs/$env/.env" "$WORKSPACE_DIR/"
        echo "Copied environment file for $env environment"
    fi
    
    # Set appropriate permissions
    chmod 600 "$WORKSPACE_DIR/config.yaml"
    if [ -f "$WORKSPACE_DIR/.env" ]; then
        chmod 600 "$WORKSPACE_DIR/.env"
    fi
    
    # Validate configuration
    cd "$WORKSPACE_DIR"
    if qdrant-loader --workspace . config >/dev/null 2>&1; then
        echo "Configuration validated successfully"
    else
        echo "ERROR: Configuration validation failed"
        exit 1
    fi
    
    echo "Environment setup completed for: $env"
}

main() {
    if [ $# -eq 0 ]; then
        echo "Usage: $0 <environment>"
        echo "Available environments: development, staging, production"
        exit 1
    fi
    
    setup_environment "$1"
}

main "$@"
```

## 🔗 Related Documentation

- **[CLI Commands Reference](./commands.md)** - Complete command documentation
- **[Options and Flags Reference](./options-and-flags.md)** - Detailed flag documentation
- **[Configuration Reference](../configuration/config-file-reference.md)** - Configuration options
- **[Troubleshooting](../troubleshooting/common-issues.md)** - Common automation issues

---

**Reliable automation achieved!** ✅

This automation guide provides practical, tested examples using only the actual QDrant Loader CLI commands and options, ensuring your automation scripts will work reliably in production environments.
