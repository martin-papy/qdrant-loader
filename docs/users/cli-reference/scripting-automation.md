# Scripting and Automation

This guide shows how to automate QDrant Loader operations using shell scripts, cron jobs, CI/CD pipelines, and monitoring systems. Whether you're building simple maintenance scripts or complex automation workflows, this guide provides practical examples and best practices.

## 🎯 Overview

Automation is essential for maintaining up-to-date knowledge bases, ensuring data quality, and reducing manual overhead. QDrant Loader's CLI is designed to be automation-friendly with proper exit codes, structured output, and robust error handling.

### Automation Categories

```
📅 Scheduled Tasks     - Cron jobs, periodic updates
🔄 CI/CD Integration   - GitHub Actions, GitLab CI
📊 Monitoring Scripts  - Health checks, alerting
🛠️ Maintenance Tasks  - Cleanup, optimization, backup
🔧 Deployment Scripts  - Setup, configuration, updates
```

## 📅 Scheduled Automation

### Basic Cron Jobs

#### Daily Data Updates

```bash
#!/bin/bash
# daily-update.sh - Daily knowledge base update

set -euo pipefail

# Configuration
LOG_FILE="/var/log/qdrant-loader/daily-update.log"
CONFIG_FILE="/etc/qdrant-loader/production.yaml"
BACKUP_DIR="/var/backups/qdrant-loader"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log "ERROR: $1"
    exit 1
}

# Main update process
main() {
    log "Starting daily update process"
    
    # Check system health
    if ! qdrant-loader --config "$CONFIG_FILE" health --quiet; then
        error_exit "Health check failed"
    fi
    
    # Create backup before update
    log "Creating backup"
    qdrant-loader --config "$CONFIG_FILE" backup \
        --output "$BACKUP_DIR/backup-$(date +%Y%m%d).tar.gz" \
        --quiet || error_exit "Backup failed"
    
    # Update data sources
    log "Updating data sources"
    qdrant-loader --config "$CONFIG_FILE" update \
        --all-sources \
        --progress \
        --log-file "$LOG_FILE" || error_exit "Update failed"
    
    # Optimize collections
    log "Optimizing collections"
    qdrant-loader --config "$CONFIG_FILE" optimize \
        --all \
        --quiet || error_exit "Optimization failed"
    
    # Clean up old data
    log "Cleaning up old data"
    qdrant-loader --config "$CONFIG_FILE" clean \
        --temp \
        --logs --older-than 7d \
        --quiet || error_exit "Cleanup failed"
    
    log "Daily update completed successfully"
}

# Run main function
main "$@"
```

#### Crontab Configuration

```bash
# /etc/crontab - System cron configuration

# Daily update at 2 AM
0 2 * * * qdrant-loader /opt/qdrant-loader/scripts/daily-update.sh

# Hourly incremental updates during business hours
0 9-17 * * 1-5 qdrant-loader /opt/qdrant-loader/scripts/hourly-update.sh

# Weekly full optimization on Sundays at 3 AM
0 3 * * 0 qdrant-loader /opt/qdrant-loader/scripts/weekly-maintenance.sh

# Monthly backup cleanup on first day of month at 4 AM
0 4 1 * * qdrant-loader /opt/qdrant-loader/scripts/cleanup-backups.sh
```

### Advanced Scheduled Scripts

#### Intelligent Update Script

```bash
#!/bin/bash
# intelligent-update.sh - Smart update with change detection

set -euo pipefail

CONFIG_FILE="${CONFIG_FILE:-/etc/qdrant-loader/production.yaml}"
LOG_FILE="${LOG_FILE:-/var/log/qdrant-loader/intelligent-update.log}"
LOCK_FILE="/var/run/qdrant-loader-update.lock"

# Lock management
acquire_lock() {
    if [ -f "$LOCK_FILE" ]; then
        local pid=$(cat "$LOCK_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo "Update already running (PID: $pid)"
            exit 1
        else
            echo "Removing stale lock file"
            rm -f "$LOCK_FILE"
        fi
    fi
    echo $$ > "$LOCK_FILE"
}

release_lock() {
    rm -f "$LOCK_FILE"
}

# Cleanup on exit
trap release_lock EXIT

# Check for changes before updating
check_changes() {
    local source="$1"
    
    case "$source" in
        git)
            # Check for new commits
            qdrant-loader --config "$CONFIG_FILE" status \
                --source git --check-changes --quiet
            ;;
        confluence)
            # Check for modified pages
            qdrant-loader --config "$CONFIG_FILE" status \
                --source confluence --check-changes --quiet
            ;;
        jira)
            # Check for updated issues
            qdrant-loader --config "$CONFIG_FILE" status \
                --source jira --check-changes --quiet
            ;;
        *)
            # Default: always update
            return 0
            ;;
    esac
}

# Update specific source if changes detected
update_source() {
    local source="$1"
    
    echo "Checking for changes in $source..."
    if check_changes "$source"; then
        echo "Changes detected in $source, updating..."
        qdrant-loader --config "$CONFIG_FILE" update \
            --source "$source" \
            --progress \
            --log-file "$LOG_FILE"
        return $?
    else
        echo "No changes detected in $source, skipping"
        return 0
    fi
}

# Main function
main() {
    acquire_lock
    
    echo "Starting intelligent update process"
    
    # Check each configured source
    local sources=("git" "confluence" "jira" "local")
    local updated=false
    
    for source in "${sources[@]}"; do
        if update_source "$source"; then
            updated=true
        fi
    done
    
    # Optimize only if data was updated
    if [ "$updated" = true ]; then
        echo "Data was updated, running optimization..."
        qdrant-loader --config "$CONFIG_FILE" optimize --quiet
    else
        echo "No data updates, skipping optimization"
    fi
    
    echo "Intelligent update completed"
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
    paths: ['docs/**', 'README.md', 'api/**']
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
        pip install qdrant-loader
    
    - name: Configure QDrant Loader
      env:
        QDRANT_URL: ${{ secrets.QDRANT_URL }}
        QDRANT_API_KEY: ${{ secrets.QDRANT_API_KEY }}
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      run: |
        # Create configuration
        cat > qdrant-loader.yaml << EOF
        qdrant:
          url: "${QDRANT_URL}"
          api_key: "${QDRANT_API_KEY}"
          collection_name: "github_docs"
        
        openai:
          api_key: "${OPENAI_API_KEY}"
        
        data_sources:
          git:
            repositories:
              - url: "${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}"
                branch: "main"
                include_patterns:
                  - "docs/**/*.md"
                  - "README.md"
                  - "api/**/*.yaml"
        EOF
    
    - name: Update knowledge base
      run: |
        # Load documentation
        qdrant-loader load --source git --progress
        
        # Optimize collection
        qdrant-loader optimize --collection github_docs
    
    - name: Verify update
      run: |
        # Check status
        qdrant-loader status --detailed
        
        # Test search functionality
        qdrant-loader search "installation guide" --limit 3
    
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
    
    - name: Setup QDrant Loader
      run: pip install qdrant-loader
    
    - name: Deploy to ${{ matrix.environment }}
      env:
        QDRANT_URL: ${{ secrets.QDRANT_URL }}
        QDRANT_API_KEY: ${{ secrets.QDRANT_API_KEY }}
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        CONFLUENCE_BASE_URL: ${{ secrets.CONFLUENCE_BASE_URL }}
        CONFLUENCE_USERNAME: ${{ secrets.CONFLUENCE_USERNAME }}
        CONFLUENCE_API_TOKEN: ${{ secrets.CONFLUENCE_API_TOKEN }}
      run: |
        # Use environment-specific configuration
        qdrant-loader --config configs/${{ matrix.environment }}.yaml load --all-sources
        
        # Run health check
        qdrant-loader health --detailed
        
        # Start MCP server
        qdrant-loader mcp-server start --daemon
```

### GitLab CI

#### Continuous Documentation Integration

```yaml
# .gitlab-ci.yml
stages:
  - validate
  - update
  - deploy

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  paths:
    - .cache/pip/

validate-config:
  stage: validate
  image: python:3.11
  script:
    - pip install qdrant-loader
    - qdrant-loader config validate --config production.yaml
  only:
    - merge_requests
    - main

update-knowledge-base:
  stage: update
  image: python:3.11
  script:
    - pip install qdrant-loader
    - |
      # Configure environment
      export QDRANT_URL="$QDRANT_URL"
      export QDRANT_API_KEY="$QDRANT_API_KEY"
      export OPENAI_API_KEY="$OPENAI_API_KEY"
      
      # Update knowledge base
      qdrant-loader --config production.yaml update --all-sources
      
      # Optimize and clean
      qdrant-loader optimize
      qdrant-loader clean --temp --logs --older-than 7d
  only:
    - main
    - schedules

deploy-mcp-server:
  stage: deploy
  image: python:3.11
  script:
    - pip install qdrant-loader
    - qdrant-loader mcp-server start --daemon --config production.yaml
  only:
    - main
  environment:
    name: production
    url: https://mcp-server.company.com
```

## 📊 Monitoring and Alerting

### Health Check Scripts

#### Comprehensive Health Monitor

```bash
#!/bin/bash
# health-monitor.sh - Comprehensive system health monitoring

set -euo pipefail

CONFIG_FILE="${CONFIG_FILE:-/etc/qdrant-loader/production.yaml}"
ALERT_WEBHOOK="${ALERT_WEBHOOK:-}"
LOG_FILE="/var/log/qdrant-loader/health-monitor.log"

# Health check functions
check_qdrant_connection() {
    echo "Checking QDrant connection..."
    if ! qdrant-loader --config "$CONFIG_FILE" status --check-connections --quiet; then
        return 1
    fi
    echo "✅ QDrant connection OK"
    return 0
}

check_openai_connection() {
    echo "Checking OpenAI connection..."
    if ! timeout 30 qdrant-loader --config "$CONFIG_FILE" config test --connections openai --quiet; then
        return 1
    fi
    echo "✅ OpenAI connection OK"
    return 0
}

check_mcp_server() {
    echo "Checking MCP server..."
    if ! qdrant-loader mcp-server status --quiet; then
        return 1
    fi
    echo "✅ MCP server OK"
    return 0
}

check_data_freshness() {
    echo "Checking data freshness..."
    local last_update
    last_update=$(qdrant-loader status --recent --limit 1 --output json | jq -r '.[0].timestamp // empty')
    
    if [ -z "$last_update" ]; then
        echo "❌ No recent updates found"
        return 1
    fi
    
    local update_age
    update_age=$(( $(date +%s) - $(date -d "$last_update" +%s) ))
    
    # Alert if data is older than 24 hours
    if [ "$update_age" -gt 86400 ]; then
        echo "❌ Data is stale (last update: $last_update)"
        return 1
    fi
    
    echo "✅ Data freshness OK (last update: $last_update)"
    return 0
}

check_collection_health() {
    echo "Checking collection health..."
    local collections
    collections=$(qdrant-loader collection list --output json)
    
    if [ "$(echo "$collections" | jq 'length')" -eq 0 ]; then
        echo "❌ No collections found"
        return 1
    fi
    
    # Check each collection
    while IFS= read -r collection; do
        local name
        name=$(echo "$collection" | jq -r '.name')
        
        local count
        count=$(echo "$collection" | jq -r '.vector_count // 0')
        
        if [ "$count" -eq 0 ]; then
            echo "❌ Collection $name is empty"
            return 1
        fi
        
        echo "✅ Collection $name OK ($count vectors)"
    done < <(echo "$collections" | jq -c '.[]')
    
    return 0
}

# Alert function
send_alert() {
    local message="$1"
    local severity="${2:-warning}"
    
    echo "ALERT [$severity]: $message" | tee -a "$LOG_FILE"
    
    if [ -n "$ALERT_WEBHOOK" ]; then
        curl -X POST "$ALERT_WEBHOOK" \
            -H "Content-Type: application/json" \
            -d "{\"text\":\"QDrant Loader Alert [$severity]: $message\"}" \
            --silent --show-error || true
    fi
}

# Main health check
main() {
    echo "Starting health check at $(date)"
    
    local failed_checks=()
    
    # Run all health checks
    if ! check_qdrant_connection; then
        failed_checks+=("QDrant connection")
    fi
    
    if ! check_openai_connection; then
        failed_checks+=("OpenAI connection")
    fi
    
    if ! check_mcp_server; then
        failed_checks+=("MCP server")
    fi
    
    if ! check_data_freshness; then
        failed_checks+=("Data freshness")
    fi
    
    if ! check_collection_health; then
        failed_checks+=("Collection health")
    fi
    
    # Report results
    if [ ${#failed_checks[@]} -eq 0 ]; then
        echo "✅ All health checks passed"
        exit 0
    else
        local message="Health check failures: $(IFS=', '; echo "${failed_checks[*]}")"
        send_alert "$message" "critical"
        exit 1
    fi
}

main "$@"
```

#### Performance Monitoring

```bash
#!/bin/bash
# performance-monitor.sh - Monitor performance metrics

set -euo pipefail

CONFIG_FILE="${CONFIG_FILE:-/etc/qdrant-loader/production.yaml}"
METRICS_FILE="/var/log/qdrant-loader/metrics.json"

# Collect metrics
collect_metrics() {
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    # System metrics
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    local memory_usage=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
    local disk_usage=$(df / | tail -1 | awk '{print $5}' | cut -d'%' -f1)
    
    # QDrant Loader metrics
    local search_latency=$(qdrant-loader metrics --metric search_latency --output json | jq -r '.search_latency.avg // 0')
    local collection_count=$(qdrant-loader collection list --output json | jq 'length')
    local total_vectors=$(qdrant-loader status --collections --stats --output json | jq '[.[] | .vector_count] | add')
    
    # Create metrics JSON
    cat > "$METRICS_FILE" << EOF
{
  "timestamp": "$timestamp",
  "system": {
    "cpu_usage": $cpu_usage,
    "memory_usage": $memory_usage,
    "disk_usage": $disk_usage
  },
  "qdrant_loader": {
    "search_latency_ms": $search_latency,
    "collection_count": $collection_count,
    "total_vectors": $total_vectors
  }
}
EOF
    
    echo "Metrics collected at $timestamp"
}

# Check thresholds and alert
check_thresholds() {
    local cpu_threshold=80
    local memory_threshold=85
    local disk_threshold=90
    local latency_threshold=1000
    
    local cpu_usage=$(jq -r '.system.cpu_usage' "$METRICS_FILE")
    local memory_usage=$(jq -r '.system.memory_usage' "$METRICS_FILE")
    local disk_usage=$(jq -r '.system.disk_usage' "$METRICS_FILE")
    local search_latency=$(jq -r '.qdrant_loader.search_latency_ms' "$METRICS_FILE")
    
    # Check CPU
    if (( $(echo "$cpu_usage > $cpu_threshold" | bc -l) )); then
        echo "WARNING: High CPU usage: ${cpu_usage}%"
    fi
    
    # Check memory
    if (( $(echo "$memory_usage > $memory_threshold" | bc -l) )); then
        echo "WARNING: High memory usage: ${memory_usage}%"
    fi
    
    # Check disk
    if [ "$disk_usage" -gt "$disk_threshold" ]; then
        echo "WARNING: High disk usage: ${disk_usage}%"
    fi
    
    # Check search latency
    if (( $(echo "$search_latency > $latency_threshold" | bc -l) )); then
        echo "WARNING: High search latency: ${search_latency}ms"
    fi
}

# Main function
main() {
    collect_metrics
    check_thresholds
}

main "$@"
```

## 🛠️ Maintenance Automation

### Automated Backup System

```bash
#!/bin/bash
# backup-system.sh - Automated backup with rotation

set -euo pipefail

CONFIG_FILE="${CONFIG_FILE:-/etc/qdrant-loader/production.yaml}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/qdrant-loader}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
S3_BUCKET="${S3_BUCKET:-}"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Generate backup filename
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/qdrant-loader-backup-$BACKUP_DATE.tar.gz"

# Create backup
create_backup() {
    echo "Creating backup: $BACKUP_FILE"
    
    if ! qdrant-loader --config "$CONFIG_FILE" backup --output "$BACKUP_FILE"; then
        echo "ERROR: Backup creation failed"
        exit 1
    fi
    
    echo "Backup created successfully: $BACKUP_FILE"
    
    # Verify backup
    if [ ! -f "$BACKUP_FILE" ] || [ ! -s "$BACKUP_FILE" ]; then
        echo "ERROR: Backup file is missing or empty"
        exit 1
    fi
    
    local backup_size=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "Backup size: $backup_size"
}

# Upload to S3 if configured
upload_to_s3() {
    if [ -n "$S3_BUCKET" ]; then
        echo "Uploading backup to S3: $S3_BUCKET"
        
        local s3_key="backups/$(basename "$BACKUP_FILE")"
        
        if command -v aws >/dev/null 2>&1; then
            aws s3 cp "$BACKUP_FILE" "s3://$S3_BUCKET/$s3_key"
            echo "Backup uploaded to S3: s3://$S3_BUCKET/$s3_key"
        else
            echo "WARNING: AWS CLI not found, skipping S3 upload"
        fi
    fi
}

# Clean old backups
cleanup_old_backups() {
    echo "Cleaning up backups older than $RETENTION_DAYS days"
    
    find "$BACKUP_DIR" -name "qdrant-loader-backup-*.tar.gz" -mtime +$RETENTION_DAYS -delete
    
    # Clean S3 backups if configured
    if [ -n "$S3_BUCKET" ] && command -v aws >/dev/null 2>&1; then
        local cutoff_date=$(date -d "$RETENTION_DAYS days ago" +%Y-%m-%d)
        aws s3 ls "s3://$S3_BUCKET/backups/" | while read -r line; do
            local file_date=$(echo "$line" | awk '{print $1}')
            local file_name=$(echo "$line" | awk '{print $4}')
            
            if [[ "$file_date" < "$cutoff_date" ]]; then
                aws s3 rm "s3://$S3_BUCKET/backups/$file_name"
                echo "Deleted old S3 backup: $file_name"
            fi
        done
    fi
}

# Main function
main() {
    echo "Starting backup process at $(date)"
    
    create_backup
    upload_to_s3
    cleanup_old_backups
    
    echo "Backup process completed at $(date)"
}

main "$@"
```

### Automated Optimization

```bash
#!/bin/bash
# optimize-system.sh - Automated optimization and maintenance

set -euo pipefail

CONFIG_FILE="${CONFIG_FILE:-/etc/qdrant-loader/production.yaml}"
LOG_FILE="/var/log/qdrant-loader/optimization.log"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Check if optimization is needed
needs_optimization() {
    local collection="$1"
    
    # Get collection stats
    local stats=$(qdrant-loader collection info "$collection" --output json)
    local vector_count=$(echo "$stats" | jq -r '.vector_count // 0')
    local deleted_count=$(echo "$stats" | jq -r '.deleted_count // 0')
    
    # Calculate deletion ratio
    if [ "$vector_count" -gt 0 ]; then
        local deletion_ratio=$(echo "scale=2; $deleted_count / $vector_count" | bc)
        
        # Optimize if more than 10% deleted vectors
        if (( $(echo "$deletion_ratio > 0.1" | bc -l) )); then
            return 0
        fi
    fi
    
    return 1
}

# Optimize collections
optimize_collections() {
    log "Starting collection optimization"
    
    local collections=$(qdrant-loader collection list --output json | jq -r '.[].name')
    
    while IFS= read -r collection; do
        if needs_optimization "$collection"; then
            log "Optimizing collection: $collection"
            
            if qdrant-loader collection optimize "$collection" --quiet; then
                log "Successfully optimized collection: $collection"
            else
                log "ERROR: Failed to optimize collection: $collection"
            fi
        else
            log "Collection $collection does not need optimization"
        fi
    done <<< "$collections"
}

# Clean temporary data
clean_temporary_data() {
    log "Cleaning temporary data"
    
    # Clean cache
    qdrant-loader clean --cache --quiet
    
    # Clean old logs
    qdrant-loader clean --logs --older-than 7d --quiet
    
    # Clean temporary files
    qdrant-loader clean --temp --quiet
    
    log "Temporary data cleanup completed"
}

# Update statistics
update_statistics() {
    log "Updating collection statistics"
    
    qdrant-loader collection stats --all --update --quiet
    
    log "Statistics update completed"
}

# Main optimization process
main() {
    log "Starting optimization process"
    
    # Check system health before optimization
    if ! qdrant-loader health --quiet; then
        log "ERROR: System health check failed, aborting optimization"
        exit 1
    fi
    
    optimize_collections
    clean_temporary_data
    update_statistics
    
    log "Optimization process completed successfully"
}

main "$@"
```

## 🔧 Deployment Automation

### Environment Setup Script

```bash
#!/bin/bash
# setup-environment.sh - Automated environment setup

set -euo pipefail

ENVIRONMENT="${1:-development}"
INSTALL_DIR="${INSTALL_DIR:-/opt/qdrant-loader}"
CONFIG_DIR="${CONFIG_DIR:-/etc/qdrant-loader}"
LOG_DIR="${LOG_DIR:-/var/log/qdrant-loader}"
USER="${USER:-qdrant-loader}"

# Create system user
create_user() {
    if ! id "$USER" &>/dev/null; then
        echo "Creating system user: $USER"
        useradd --system --home-dir "$INSTALL_DIR" --shell /bin/bash "$USER"
    fi
}

# Create directories
create_directories() {
    echo "Creating directories"
    
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "/var/backups/qdrant-loader"
    
    chown -R "$USER:$USER" "$INSTALL_DIR"
    chown -R "$USER:$USER" "$LOG_DIR"
    chown -R "$USER:$USER" "/var/backups/qdrant-loader"
}

# Install QDrant Loader
install_qdrant_loader() {
    echo "Installing QDrant Loader"
    
    # Install Python and pip if not present
    if ! command -v python3 &>/dev/null; then
        apt-get update
        apt-get install -y python3 python3-pip
    fi
    
    # Install QDrant Loader
    pip3 install qdrant-loader
    
    # Verify installation
    qdrant-loader --version
}

# Setup configuration
setup_configuration() {
    echo "Setting up configuration for $ENVIRONMENT"
    
    # Copy environment-specific configuration
    if [ -f "configs/$ENVIRONMENT.yaml" ]; then
        cp "configs/$ENVIRONMENT.yaml" "$CONFIG_DIR/qdrant-loader.yaml"
        chown "$USER:$USER" "$CONFIG_DIR/qdrant-loader.yaml"
        chmod 600 "$CONFIG_DIR/qdrant-loader.yaml"
    else
        echo "WARNING: No configuration found for environment: $ENVIRONMENT"
    fi
}

# Setup systemd service
setup_systemd_service() {
    echo "Setting up systemd service"
    
    cat > /etc/systemd/system/qdrant-loader-mcp.service << EOF
[Unit]
Description=QDrant Loader MCP Server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/local/bin/qdrant-loader mcp-server start --config $CONFIG_DIR/qdrant-loader.yaml
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable qdrant-loader-mcp
}

# Setup cron jobs
setup_cron_jobs() {
    echo "Setting up cron jobs"
    
    # Create cron file for qdrant-loader user
    cat > "/var/spool/cron/crontabs/$USER" << EOF
# QDrant Loader automated tasks

# Daily update at 2 AM
0 2 * * * /opt/qdrant-loader/scripts/daily-update.sh

# Hourly health check
0 * * * * /opt/qdrant-loader/scripts/health-monitor.sh

# Weekly optimization on Sundays at 3 AM
0 3 * * 0 /opt/qdrant-loader/scripts/weekly-optimization.sh

# Daily backup at 1 AM
0 1 * * * /opt/qdrant-loader/scripts/backup-system.sh
EOF
    
    chown "$USER:crontab" "/var/spool/cron/crontabs/$USER"
    chmod 600 "/var/spool/cron/crontabs/$USER"
}

# Main setup function
main() {
    echo "Setting up QDrant Loader environment: $ENVIRONMENT"
    
    create_user
    create_directories
    install_qdrant_loader
    setup_configuration
    setup_systemd_service
    setup_cron_jobs
    
    echo "Environment setup completed successfully"
    echo "Next steps:"
    echo "1. Configure environment variables in $CONFIG_DIR/qdrant-loader.yaml"
    echo "2. Start the MCP server: systemctl start qdrant-loader-mcp"
    echo "3. Load initial data: qdrant-loader load --all-sources"
}

main "$@"
```

## 📋 Automation Best Practices

### Error Handling and Logging

```bash
#!/bin/bash
# robust-script-template.sh - Template for robust automation scripts

set -euo pipefail

# Configuration
SCRIPT_NAME="$(basename "$0")"
LOG_FILE="/var/log/qdrant-loader/${SCRIPT_NAME%.sh}.log"
LOCK_FILE="/var/run/${SCRIPT_NAME%.sh}.lock"
MAX_RETRIES=3
RETRY_DELAY=5

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

# Retry mechanism
retry_command() {
    local cmd="$1"
    local retries=0
    
    while [ $retries -lt $MAX_RETRIES ]; do
        if eval "$cmd"; then
            return 0
        else
            retries=$((retries + 1))
            if [ $retries -lt $MAX_RETRIES ]; then
                log_warn "Command failed, retrying in ${RETRY_DELAY}s (attempt $retries/$MAX_RETRIES)"
                sleep $RETRY_DELAY
            fi
        fi
    done
    
    return 1
}

# Setup trap for cleanup
trap cleanup EXIT

# Main function template
main() {
    log_info "Starting $SCRIPT_NAME"
    
    acquire_lock
    
    # Your automation logic here
    if retry_command "qdrant-loader status --health"; then
        log_info "Health check passed"
    else
        error_exit "Health check failed after $MAX_RETRIES attempts"
    fi
    
    log_info "$SCRIPT_NAME completed successfully"
}

main "$@"
```

### Configuration Management

```bash
#!/bin/bash
# config-manager.sh - Centralized configuration management

set -euo pipefail

CONFIG_REPO="${CONFIG_REPO:-git@github.com:company/qdrant-loader-configs.git}"
CONFIG_DIR="/etc/qdrant-loader"
BACKUP_DIR="/var/backups/qdrant-loader-configs"

# Update configurations from repository
update_configs() {
    local environment="$1"
    
    echo "Updating configurations for environment: $environment"
    
    # Clone or update config repository
    if [ -d "$BACKUP_DIR/.git" ]; then
        cd "$BACKUP_DIR"
        git pull origin main
    else
        git clone "$CONFIG_REPO" "$BACKUP_DIR"
    fi
    
    # Copy environment-specific configuration
    if [ -f "$BACKUP_DIR/environments/$environment.yaml" ]; then
        cp "$BACKUP_DIR/environments/$environment.yaml" "$CONFIG_DIR/qdrant-loader.yaml"
        chmod 600 "$CONFIG_DIR/qdrant-loader.yaml"
        
        # Validate configuration
        if qdrant-loader config validate --config "$CONFIG_DIR/qdrant-loader.yaml"; then
            echo "Configuration updated and validated successfully"
        else
            echo "ERROR: Configuration validation failed"
            exit 1
        fi
    else
        echo "ERROR: Configuration not found for environment: $environment"
        exit 1
    fi
}

# Deploy configuration
deploy_config() {
    local environment="$1"
    
    update_configs "$environment"
    
    # Restart services if needed
    if systemctl is-active --quiet qdrant-loader-mcp; then
        echo "Restarting MCP server with new configuration"
        systemctl restart qdrant-loader-mcp
    fi
    
    echo "Configuration deployment completed"
}

# Main function
main() {
    local command="${1:-update}"
    local environment="${2:-production}"
    
    case "$command" in
        update)
            update_configs "$environment"
            ;;
        deploy)
            deploy_config "$environment"
            ;;
        *)
            echo "Usage: $0 {update|deploy} [environment]"
            exit 1
            ;;
    esac
}

main "$@"
```

## 🔗 Related Documentation

- **[CLI Commands Reference](./commands.md)** - Complete command documentation
- **[Options and Flags Reference](./options-and-flags.md)** - Detailed flag documentation
- **[Configuration Reference](../configuration/config-file-reference.md)** - Configuration options
- **[Troubleshooting](../troubleshooting/common-issues.md)** - Common automation issues

---

**Automation mastery achieved!** 🎉

This comprehensive automation guide provides everything you need to build robust, reliable automation for QDrant Loader operations, from simple scheduled tasks to complex CI/CD pipelines and monitoring systems.
