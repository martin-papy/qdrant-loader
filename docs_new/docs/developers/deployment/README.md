# Deployment Guide

This section provides comprehensive deployment documentation for QDrant Loader, covering production deployment strategies, environment setup, monitoring, and performance optimization.

## 🎯 Deployment Overview

QDrant Loader can be deployed in various environments and configurations to meet different scale and reliability requirements:

### 🚀 Deployment Options

- **[Environment Setup](./environment-setup.md)** - Setting up production environments
- **[Monitoring and Observability](./monitoring.md)** - Logging, metrics, alerting, and health checks
- **[Performance Tuning](./performance-tuning.md)** - Optimization for production workloads

### 🏗️ Architecture Patterns

QDrant Loader supports multiple deployment architectures:

```
┌─────────────────────────────────────────────────────────────┐
│                    Deployment Options                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Single    │  │ Multi-Node  │  │   Cloud     │         │
│  │   Server    │  │   Setup     │  │   Hosted    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Local     │  │   Virtual   │  │   Managed   │         │
│  │ Development │  │   Machines  │  │  Services   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                             │
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
pip install -e packages/qdrant-loader[dev]
pip install -e packages/qdrant-loader-mcp-server[dev]

# Create configuration
mkdir config
cp packages/qdrant-loader/conf/config.template.yaml config/config.yaml
cp packages/qdrant-loader/conf/.env.template config/.env

# Edit configuration files
# config/.env: Add your API keys and configuration
# config/config.yaml: Configure your data sources

# Initialize and start
qdrant-loader --workspace config init
qdrant-loader --workspace config ingest
```

### Production Environment Setup

```bash
# Create production user
sudo useradd -m -s /bin/bash qdrant-loader
sudo su - qdrant-loader

# Setup application directory
mkdir -p /opt/qdrant-loader/{config,data,logs}
cd /opt/qdrant-loader

# Install Python and dependencies
python -m venv venv
source venv/bin/activate
pip install qdrant-loader qdrant-loader-mcp-server

# Setup configuration
cp config.template.yaml config/config.yaml
cp .env.template config/.env
# Edit configuration files

# Setup systemd service (as root)
sudo cp qdrant-loader.service /etc/systemd/system/
sudo systemctl enable qdrant-loader
sudo systemctl start qdrant-loader
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
cat > /opt/qdrant-loader/config/.env << EOF
# QDrant Configuration
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=documents
QDRANT_API_KEY=

# OpenAI Configuration
OPENAI_API_KEY=sk-proj-your-production-key

# Data Source Credentials
REPO_TOKEN=ghp_your-github-token
CONFLUENCE_URL=https://your-domain.atlassian.net
CONFLUENCE_TOKEN=your-confluence-token
CONFLUENCE_EMAIL=your-email@domain.com

# Application Settings
LOG_LEVEL=INFO
LOG_FILE=/opt/qdrant-loader/logs/app.log
STATE_DB_PATH=/opt/qdrant-loader/data/state.db

# Performance Settings
CHUNK_SIZE=1000
BATCH_SIZE=50
MAX_CONCURRENT_REQUESTS=10
EOF
```

### Configuration File

```yaml
# /opt/qdrant-loader/config/config.yaml
sources:
  git:
    - url: "https://github.com/your-org/repo.git"
      branch: "main"
      include_patterns:
        - "**/*.md"
        - "**/*.py"
        - "**/*.rst"
  
  confluence:
    - url: "${CONFLUENCE_URL}"
      username: "${CONFLUENCE_EMAIL}"
      token: "${CONFLUENCE_TOKEN}"
      spaces:
        - "DOCS"
        - "TECH"

chunk_size: 1000
batch_size: 50
enable_file_conversion: true
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

# Check QDrant Loader status
if qdrant-loader --workspace "$WORKSPACE" status > /dev/null 2>&1; then
    log "QDrant Loader: HEALTHY"
    exit 0
else
    log "QDrant Loader: UNHEALTHY"
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
# Monitor QDrant Loader status
qdrant-loader --workspace /opt/qdrant-loader/config status --detailed --watch

# Monitor log files
tail -f /opt/qdrant-loader/logs/app.log

# Monitor system services
systemctl status qdrant-loader
systemctl status mcp-qdrant-loader
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
# Run multiple ingestion processes
qdrant-loader --workspace /opt/qdrant-loader/config ingest --sources git &
qdrant-loader --workspace /opt/qdrant-loader/config ingest --sources confluence &
qdrant-loader --workspace /opt/qdrant-loader/config ingest --sources jira &
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
export CHUNK_SIZE=2000
export BATCH_SIZE=100
export MAX_CONCURRENT_REQUESTS=20

# Optimize for high-CPU systems
qdrant-loader ingest --max-workers 16
```

## 📚 Deployment Documentation

### Detailed Deployment Guides

- **[Environment Setup](./environment-setup.md)** - Complete environment setup guide
- **[Monitoring and Observability](./monitoring.md)** - Comprehensive monitoring setup
- **[Performance Tuning](./performance-tuning.md)** - Production optimization guide

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

**Ready to deploy?** Start with [Environment Setup](./environment-setup.md) for detailed setup instructions or jump to [Monitoring and Observability](./monitoring.md) for production monitoring. Don't forget to check [Performance Tuning](./performance-tuning.md) for optimization tips.
