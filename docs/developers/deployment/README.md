# Deployment Documentation

This section provides comprehensive deployment documentation for QDrant Loader, covering production deployment strategies, environment setup, monitoring, and performance optimization. All examples are verified against the actual implementation.

## 🎯 Deployment Overview

QDrant Loader can be deployed in various environments and configurations to meet different scale and reliability requirements:

### 🚀 Deployment Options

QDrant Loader supports the following deployment patterns:

- **Local Installation** - Direct Python package installation for development and small-scale use
- **PyPI Package Deployment** - Official package distribution via PyPI
- **Workspace-Based Deployment** - Organized multi-project configurations
- **MCP Server Deployment** - Optional server component for AI assistant integration

### 🏗️ Architecture Patterns

```text
┌─────────────────────────────────────────────────────────────┐
│                    QDrant Loader Deployment                 │
├─────────────────────────────────────────────────────────────┤
│  CLI Tool           │  MCP Server (Optional)                │
│  ┌───────────────┐  │  ┌─────────────────────────────────┐  │
│  │ qdrant-loader │  │  │ mcp-qdrant-loader               │  │
│  │               │  │  │ (AI Assistant Integration)     │  │
│  │ - init        │  │  │                                 │  │
│  │ - ingest      │  │  │ - semantic_search               │  │
│  │ - config      │  │  │ - hierarchy_search              │  │
│  │ - project     │  │  │ - attachment_search             │  │
│  └───────────────┘  │  └─────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                    External Dependencies                    │
│  ┌───────────────┐  │  ┌─────────────────────────────────┐  │
│  │ QDrant        │  │  │ OpenAI API                      │  │
│  │ Vector DB     │  │  │ (Embeddings)                    │  │
│  └───────────────┘  │  └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start Deployment

### Single Server Setup

```bash
# Create deployment directory
mkdir qdrant-loader-deployment
cd qdrant-loader-deployment

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install QDrant Loader
pip install qdrant-loader qdrant-loader-mcp-server

# Create workspace structure
mkdir -p {data,logs}

# Create configuration files
cat > config.yaml << EOF
global_config:
  qdrant:
    url: "http://localhost:6333"
    collection_name: "documents"
  openai:
    api_key: "${OPENAI_API_KEY}"
  state_management:
    state_db_path: "./data/state.db"

projects:
  docs:
    display_name: "Documentation"
    sources:
      git:
        main-docs:
          base_url: "https://github.com/company/docs"
          branch: "main"
          token: "${REPO_TOKEN}"
EOF

# Create environment file
cat > .env << EOF
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=documents
OPENAI_API_KEY=your-openai-key
REPO_TOKEN=your-github-token
EOF

# Initialize and start
qdrant-loader --workspace . init
qdrant-loader --workspace . ingest
```

### Production Environment Setup

```bash
# Create production user
sudo useradd -m -s /bin/bash qdrant-loader
sudo su - qdrant-loader

# Setup application directory
mkdir -p /opt/qdrant-loader/{data,logs}
cd /opt/qdrant-loader

# Install Python and dependencies
python -m venv venv
source venv/bin/activate
pip install qdrant-loader qdrant-loader-mcp-server

# Setup configuration (see Configuration section below)
# Edit config.yaml and .env with your settings

# Initialize workspace
qdrant-loader --workspace /opt/qdrant-loader init
```

## 🖥️ Environment Setup

### System Requirements

#### Minimum Requirements

- **CPU**: 2 cores
- **RAM**: 4 GB
- **Storage**: 10 GB available space
- **Python**: 3.12 or higher
- **Network**: Internet access for API calls

#### Recommended Requirements

- **CPU**: 4+ cores
- **RAM**: 8+ GB
- **Storage**: 50+ GB SSD
- **Python**: 3.12+
- **Network**: High-speed internet connection

### Operating System Support

| OS | Support Level | Notes |
|---|---|---|
| **Ubuntu 20.04+** | ✅ Fully Supported | Recommended for production |
| **CentOS 8+** | ✅ Fully Supported | Enterprise environments |
| **macOS 12+** | ✅ Fully Supported | Development and testing |
| **Windows 10+** | ✅ Fully Supported | Development environments |

### Dependencies

#### System Dependencies

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev git curl

# CentOS/RHEL
sudo yum install -y python3.12 python3.12-venv python3.12-devel git curl

# macOS (with Homebrew)
brew install python@3.12 git curl
```

#### Python Dependencies

```bash
# Core dependencies are automatically installed
pip install qdrant-loader qdrant-loader-mcp-server

# Optional development dependencies
pip install qdrant-loader[dev] qdrant-loader-mcp-server[dev]
```

### QDrant Database Setup

#### Local QDrant Installation

```bash
# Using Docker (recommended)
docker run -p 6333:6333 -p 6334:6334 \
    -v $(pwd)/qdrant_storage:/qdrant/storage:z \
    qdrant/qdrant

# Using binary installation
wget https://github.com/qdrant/qdrant/releases/latest/download/qdrant-x86_64-unknown-linux-gnu.tar.gz
tar xzf qdrant-x86_64-unknown-linux-gnu.tar.gz
./qdrant
```

#### Cloud QDrant Setup

```bash
# QDrant Cloud configuration
export QDRANT_URL="https://your-cluster.qdrant.io"
export QDRANT_API_KEY="your-api-key"
export QDRANT_COLLECTION_NAME="documents"
```

## 🔧 Configuration Management

### Environment Variables

```bash
# Production environment variables
cat > /opt/qdrant-loader/.env << EOF
# QDrant Configuration
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=documents
QDRANT_API_KEY=your-api-key

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key

# Data Source Credentials
REPO_TOKEN=your-github-token
CONFLUENCE_TOKEN=your-confluence-token
CONFLUENCE_EMAIL=your-email@domain.com
JIRA_TOKEN=your-jira-token
JIRA_EMAIL=your-email@domain.com

# Application Settings
STATE_DB_PATH=./data/state.db
EOF
```

### Configuration File

```yaml
# /opt/qdrant-loader/config.yaml
global_config:
  qdrant:
    url: "${QDRANT_URL}"
    api_key: "${QDRANT_API_KEY}"
    collection_name: "${QDRANT_COLLECTION_NAME}"
  openai:
    api_key: "${OPENAI_API_KEY}"
  state_management:
    state_db_path: "${STATE_DB_PATH}"
  chunking:
    chunk_size: 1200
    chunk_overlap: 300
  file_conversion:
    max_file_size: "100MB"
    conversion_timeout: 300

projects:
  production:
    project_id: "production"
    display_name: "Production Documentation"
    description: "Production documentation and knowledge base"
    
    sources:
      git:
        docs-repo:
          source_type: "git"
          source: "docs-repo"
          base_url: "https://github.com/company/docs"
          branch: "main"
          token: "${REPO_TOKEN}"
          include_paths: ["**/*.md", "**/*.rst"]
      
      confluence:
        company-wiki:
          source_type: "confluence"
          source: "company-wiki"
          base_url: "https://company.atlassian.net/wiki"
          deployment_type: "cloud"
          space_key: "DOCS"
          token: "${CONFLUENCE_TOKEN}"
          email: "${CONFLUENCE_EMAIL}"
```

## 🔄 Service Management

### Systemd Service

```ini
# /etc/systemd/system/qdrant-loader.service
[Unit]
Description=QDrant Loader Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=qdrant-loader
Group=qdrant-loader
WorkingDirectory=/opt/qdrant-loader
Environment=PATH=/opt/qdrant-loader/venv/bin
ExecStart=/opt/qdrant-loader/venv/bin/qdrant-loader --workspace /opt/qdrant-loader/config ingest
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### MCP Server Service

```ini
# /etc/systemd/system/mcp-qdrant-loader.service
[Unit]
Description=QDrant Loader MCP Server
After=network.target
Wants=network.target

[Service]
Type=simple
User=qdrant-loader
Group=qdrant-loader
WorkingDirectory=/opt/qdrant-loader
Environment=PATH=/opt/qdrant-loader/venv/bin
ExecStart=/opt/qdrant-loader/venv/bin/mcp-qdrant-loader --workspace /opt/qdrant-loader/config
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Service Management Commands

```bash
# Enable and start services
sudo systemctl enable qdrant-loader
sudo systemctl enable mcp-qdrant-loader
sudo systemctl start qdrant-loader
sudo systemctl start mcp-qdrant-loader

# Check status
sudo systemctl status qdrant-loader
sudo systemctl status mcp-qdrant-loader

# View logs
sudo journalctl -u qdrant-loader -f
sudo journalctl -u mcp-qdrant-loader -f

# Restart services
sudo systemctl restart qdrant-loader
sudo systemctl restart mcp-qdrant-loader
```

## 📊 Monitoring and Observability

### Log Management

#### Log Configuration

```python
# logging.yaml
version: 1
formatters:
  default:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  json:
    format: '{"timestamp": "%(asctime)s", "logger": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}'

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: json
    stream: ext://sys.stdout
  
  file:
    class: logging.handlers.RotatingFileHandler
    level: DEBUG
    formatter: default
    filename: /opt/qdrant-loader/logs/app.log
    maxBytes: 10485760  # 10MB
    backupCount: 5

loggers:
  qdrant_loader:
    level: DEBUG
    handlers: [console, file]
    propagate: false

root:
  level: INFO
  handlers: [console]
```

#### Log Rotation

```bash
# /etc/logrotate.d/qdrant-loader
/opt/qdrant-loader/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 qdrant-loader qdrant-loader
    postrotate
        systemctl reload qdrant-loader
    endscript
}
```

### Health Monitoring

#### Health Check Script

```bash
#!/bin/bash
# /opt/qdrant-loader/bin/health-check.sh

set -e

WORKSPACE="/opt/qdrant-loader/config"
LOG_FILE="/opt/qdrant-loader/logs/health-check.log"

# Function to log with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Check QDrant Loader configuration
if qdrant-loader --workspace "$WORKSPACE" config >/dev/null 2>&1; then
    log "QDrant Loader: HEALTHY - Configuration valid"
    exit 0
else
    log "QDrant Loader: UNHEALTHY - Configuration invalid"
    exit 1
fi
```

#### Cron Job for Health Checks

```bash
# Add to crontab
*/5 * * * * /opt/qdrant-loader/bin/health-check.sh
```

### Performance Monitoring

#### System Metrics

```bash
# Monitor system resources
htop
iostat -x 1
free -h
df -h
```

#### Application Metrics

```bash
# Check project status
qdrant-loader project --workspace /opt/qdrant-loader/config list

# Check project status with JSON output
qdrant-loader project --workspace /opt/qdrant-loader/config status --format json

# Monitor system services
systemctl status qdrant-loader
systemctl status mcp-qdrant-loader
```

### Prometheus Metrics

QDrant Loader includes built-in Prometheus metrics support:

```python
# Available metrics (from prometheus_metrics.py)
INGESTED_DOCUMENTS = Counter("qdrant_ingested_documents_total", "Total number of documents ingested")
CHUNKING_DURATION = Histogram("qdrant_chunking_duration_seconds", "Time spent chunking documents")
EMBEDDING_DURATION = Histogram("qdrant_embedding_duration_seconds", "Time spent embedding chunks")
UPSERT_DURATION = Histogram("qdrant_upsert_duration_seconds", "Time spent upserting to Qdrant")
CHUNK_QUEUE_SIZE = Gauge("qdrant_chunk_queue_size", "Current size of the chunk queue")
EMBED_QUEUE_SIZE = Gauge("qdrant_embed_queue_size", "Current size of the embedding queue")
CPU_USAGE = Gauge("qdrant_cpu_usage_percent", "CPU usage percent")
MEMORY_USAGE = Gauge("qdrant_memory_usage_percent", "Memory usage percent")
```

## 🔒 Security Configuration

### File Permissions

```bash
# Set proper file permissions
sudo chown -R qdrant-loader:qdrant-loader /opt/qdrant-loader
sudo chmod 750 /opt/qdrant-loader
sudo chmod 640 /opt/qdrant-loader/config/.env
sudo chmod 644 /opt/qdrant-loader/config/config.yaml
sudo chmod 755 /opt/qdrant-loader/bin/health-check.sh
```

### Firewall Configuration

```bash
# Ubuntu/Debian (ufw)
sudo ufw allow ssh
sudo ufw allow 6333/tcp  # QDrant HTTP
sudo ufw allow 6334/tcp  # QDrant gRPC
sudo ufw enable

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-port=6333/tcp
sudo firewall-cmd --permanent --add-port=6334/tcp
sudo firewall-cmd --reload
```

### SSL/TLS Configuration

```bash
# Generate SSL certificates for QDrant
openssl req -x509 -newkey rsa:4096 -keyout qdrant-key.pem -out qdrant-cert.pem -days 365 -nodes

# Configure QDrant with SSL
# Add to QDrant configuration
```

## 🚀 Scaling Strategies

### Horizontal Scaling

#### Multiple Worker Processes

```bash
# Run multiple ingestion processes for different projects
qdrant-loader --workspace /opt/qdrant-loader/config ingest --project project1 &
qdrant-loader --workspace /opt/qdrant-loader/config ingest --project project2 &
qdrant-loader --workspace /opt/qdrant-loader/config ingest --project project3 &
wait
```

#### Load Balancing

```bash
# Use nginx for load balancing MCP servers
# /etc/nginx/sites-available/qdrant-loader
upstream mcp_servers {
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
    server 127.0.0.1:8003;
}

server {
    listen 80;
    server_name qdrant-loader.example.com;
    
    location / {
        proxy_pass http://mcp_servers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Vertical Scaling

#### Resource Optimization

```bash
# Optimize for high-memory systems
# Configure larger chunk sizes in config.yaml:
# global_config:
#   chunking:
#     chunk_size: 2000
#     chunk_overlap: 400

# Run ingestion with specific project
qdrant-loader --workspace /opt/qdrant-loader/config ingest --project high-priority
```

## 📚 Deployment Documentation

### Detailed Deployment Guides

- **[Environment Setup](#environment-setup)** - Complete environment setup guide
- **[Monitoring and Observability](#monitoring-and-observability)** - Comprehensive monitoring setup
- **[Performance Optimization](#performance-optimization)** - Production optimization guide

### Best Practices

1. **Use virtual environments** - Isolate Python dependencies
2. **Implement health checks** - Monitor application health
3. **Monitor everything** - Comprehensive observability
4. **Plan for scale** - Design for growth
5. **Secure by default** - File permissions, firewall, SSL
6. **Automate deployments** - Use scripts and configuration management

### Deployment Checklist

- [ ] System requirements met
- [ ] Dependencies installed
- [ ] Configuration files created and validated
- [ ] Environment variables set
- [ ] QDrant database accessible
- [ ] Services configured and started
- [ ] Health checks implemented
- [ ] Monitoring and logging configured
- [ ] Security measures applied
- [ ] Backup and recovery tested
- [ ] Documentation updated

## 🆘 Getting Help

### Deployment Support

- **[GitHub Issues](https://github.com/martin-papy/qdrant-loader/issues)** - Report deployment issues
- **[GitHub Discussions](https://github.com/martin-papy/qdrant-loader/discussions)** - Ask deployment questions
- **[Deployment Examples](https://github.com/martin-papy/qdrant-loader/tree/main/examples/deployment)** - Reference configurations

### Community Resources

- **[Configuration Examples](https://github.com/martin-papy/qdrant-loader/wiki/Configuration)** - Community configurations
- **[Deployment Guides](https://github.com/martin-papy/qdrant-loader/wiki/Deployment)** - Community deployment guides

---

**Ready to deploy?** Start with [Environment Setup](#environment-setup) for detailed setup instructions or jump to [Monitoring and Observability](#monitoring-and-observability) for production monitoring. Don't forget to check [Performance Optimization](#performance-optimization) for optimization tips.

### Performance Optimization

Configure chunking and processing parameters in your workspace configuration:

```yaml
# config.yaml - Performance tuning
global_config:
  chunking:
    chunk_size: 1200
    chunk_overlap: 300
  file_conversion:
    max_file_size: "100MB"
    conversion_timeout: 300
```
