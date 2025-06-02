# Deployment Guide

This guide covers deploying QDrant Loader in production environments, focusing on practical deployment strategies that align with the actual architecture and capabilities of the system. QDrant Loader is primarily a CLI tool with an optional MCP server component.

## 🎯 Deployment Overview

QDrant Loader supports the following deployment patterns:

- **Local Installation** - Direct Python package installation for development and small-scale use
- **PyPI Package Deployment** - Official package distribution via PyPI
- **Workspace-Based Deployment** - Organized multi-project configurations
- **MCP Server Deployment** - Optional server component for AI assistant integration

### Architecture Overview

```
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

## 📦 Package Installation

### PyPI Installation

QDrant Loader is distributed as two separate packages on PyPI:

```bash
# Install the main CLI tool
pip install qdrant-loader

# Install the MCP server (optional)
pip install qdrant-loader-mcp-server
```

### Development Installation

For development or customization:

```bash
# Clone the repository
git clone https://github.com/your-org/qdrant-loader.git
cd qdrant-loader

# Install in development mode
pip install -e packages/qdrant-loader[dev]
pip install -e packages/qdrant-loader-mcp-server[dev]
```

## 🏗️ Production Deployment

### Environment Setup

Create a production environment with proper configuration:

```bash
# Create workspace directory
mkdir /opt/qdrant-loader
cd /opt/qdrant-loader

# Create workspace structure
mkdir -p {data,logs}

# Create configuration files
cat > config.yaml << EOF
global_config:
  qdrant:
    url: "${QDRANT_URL}"
    api_key: "${QDRANT_API_KEY}"
    collection_name: "${QDRANT_COLLECTION_NAME}"
  openai:
    api_key: "${OPENAI_API_KEY}"
  state_management:
    state_db_path: "./data/state.db"

projects:
  production:
    display_name: "Production Documentation"
    sources:
      git:
        - base_url: "https://github.com/company/docs"
          branch: "main"
          token: "${REPO_TOKEN}"
EOF

# Create environment file
cat > .env << EOF
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your-api-key
QDRANT_COLLECTION_NAME=documents
OPENAI_API_KEY=your-openai-key
REPO_TOKEN=your-github-token
EOF
```

### Systemd Service

Create a systemd service for automated ingestion:

```ini
# /etc/systemd/system/qdrant-loader.service
[Unit]
Description=QDrant Loader Ingestion Service
After=network.target

[Service]
Type=oneshot
User=qdrant-loader
Group=qdrant-loader
WorkingDirectory=/opt/qdrant-loader
Environment=PATH=/opt/qdrant-loader/venv/bin
ExecStart=/opt/qdrant-loader/venv/bin/qdrant-loader --workspace /opt/qdrant-loader ingest
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Create a timer for scheduled execution:

```ini
# /etc/systemd/system/qdrant-loader.timer
[Unit]
Description=Run QDrant Loader every 6 hours
Requires=qdrant-loader.service

[Timer]
OnCalendar=*-*-* 00,06,12,18:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start the timer:

```bash
sudo systemctl enable qdrant-loader.timer
sudo systemctl start qdrant-loader.timer
```

### MCP Server Deployment

Deploy the MCP server for AI assistant integration:

```bash
# Create MCP server service
cat > /etc/systemd/system/mcp-qdrant-loader.service << EOF
[Unit]
Description=QDrant Loader MCP Server
After=network.target

[Service]
Type=simple
User=qdrant-loader
Group=qdrant-loader
WorkingDirectory=/opt/qdrant-loader
Environment=PATH=/opt/qdrant-loader/venv/bin
Environment=QDRANT_URL=http://localhost:6333
Environment=QDRANT_API_KEY=your-api-key
Environment=QDRANT_COLLECTION_NAME=documents
Environment=OPENAI_API_KEY=your-openai-key
ExecStart=/opt/qdrant-loader/venv/bin/mcp-qdrant-loader
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
sudo systemctl enable mcp-qdrant-loader.service
sudo systemctl start mcp-qdrant-loader.service
```

## 🔄 CI/CD Integration

### GitHub Actions

The project includes actual GitHub Actions workflows for testing and publishing:

#### Test Workflow (`.github/workflows/test.yml`)

The test workflow runs comprehensive tests for both packages:

```yaml
name: Test and Coverage

on:
  push:
    branches: [ main, develop, feature/*, bugfix/*, release/* ]
  pull_request:
    branches: [ main, develop, feature/*, bugfix/*, release/* ]

jobs:
  test-loader:
    name: Test QDrant Loader
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install system dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y ffmpeg
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e packages/qdrant-loader[dev]
      - name: Run tests
        run: |
          cd packages/qdrant-loader
          python -m pytest tests/ --cov=src --cov-report=xml --cov-report=html -v

  test-mcp-server:
    name: Test MCP Server
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e packages/qdrant-loader[dev]
          pip install -e packages/qdrant-loader-mcp-server[dev]
      - name: Run MCP server tests
        run: |
          cd packages/qdrant-loader-mcp-server
          python -m pytest tests/ --cov=src --cov-report=xml --cov-report=html -v
```

#### Publish Workflow (`.github/workflows/publish.yml`)

The publish workflow automatically publishes packages to PyPI on release:

```yaml
name: Publish Packages to PyPI

on:
  release:
    types: [created]

jobs:
  determine-package:
    name: Determine which package to publish
    runs-on: ubuntu-latest
    outputs:
      publish-loader: ${{ steps.check.outputs.publish-loader }}
      publish-mcp-server: ${{ steps.check.outputs.publish-mcp-server }}
    steps:
      - name: Check release tag
        id: check
        run: |
          if [[ "${{ github.event.release.tag_name }}" == qdrant-loader-mcp-server-* ]]; then
            echo "publish-mcp-server=true" >> $GITHUB_OUTPUT
          elif [[ "${{ github.event.release.tag_name }}" == qdrant-loader-* ]]; then
            echo "publish-loader=true" >> $GITHUB_OUTPUT
          fi

  publish-loader:
    name: Publish QDrant Loader to PyPI
    runs-on: ubuntu-latest
    needs: determine-package
    if: needs.determine-package.outputs.publish-loader == 'true'
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Build package
        run: |
          cd packages/qdrant-loader
          python -m build
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          packages-dir: packages/qdrant-loader/dist/
```

#### Documentation Workflow (`.github/workflows/docs.yml`)

The project also includes a documentation workflow for maintaining documentation quality.

### Custom Deployment Script

Create a deployment script for your environment:

```bash
#!/bin/bash
# deploy.sh

set -e

WORKSPACE_DIR="/opt/qdrant-loader"
VENV_DIR="$WORKSPACE_DIR/venv"

echo "Deploying QDrant Loader..."

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Upgrade pip and install packages
pip install --upgrade pip
pip install qdrant-loader qdrant-loader-mcp-server

# Initialize workspace if needed
cd "$WORKSPACE_DIR"
if [ ! -f "config.yaml" ]; then
    qdrant-loader --workspace . init
fi

# Test configuration
qdrant-loader --workspace . config

# Restart services
sudo systemctl restart qdrant-loader.timer
sudo systemctl restart mcp-qdrant-loader.service

echo "Deployment completed successfully!"
```

## 📊 Monitoring

### Prometheus Metrics

QDrant Loader includes built-in Prometheus metrics support. The following metrics are available:

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

Enable metrics in your ingestion pipeline:

```bash
# Run with metrics enabled (starts server on port 8001)
qdrant-loader --workspace . ingest --enable-metrics
```

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'qdrant-loader'
    static_configs:
      - targets: ['localhost:8001']
    metrics_path: /metrics
    scrape_interval: 30s
```

### Log Monitoring

QDrant Loader uses structured logging. Configure log aggregation:

```bash
# View logs
journalctl -u qdrant-loader.service -f

# View MCP server logs
journalctl -u mcp-qdrant-loader.service -f

# Check workspace logs (if configured)
tail -f /opt/qdrant-loader/logs/qdrant-loader.log
```

## 🔒 Security Considerations

### Environment Variables

Store sensitive configuration in environment variables:

```bash
# /etc/environment or systemd environment files
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your-secure-api-key
OPENAI_API_KEY=your-openai-api-key
REPO_TOKEN=your-github-token
```

### File Permissions

Secure your workspace directory:

```bash
# Create dedicated user
sudo useradd -r -s /bin/false qdrant-loader

# Set proper ownership and permissions
sudo chown -R qdrant-loader:qdrant-loader /opt/qdrant-loader
sudo chmod 750 /opt/qdrant-loader
sudo chmod 640 /opt/qdrant-loader/.env
sudo chmod 644 /opt/qdrant-loader/config.yaml
```

### Network Security

- Run QDrant with authentication enabled
- Use HTTPS for external API connections
- Restrict network access to QDrant and MCP server ports
- Use firewall rules to limit access

## 🔧 Configuration Management

### Workspace Structure

Organize your production workspace:

```
/opt/qdrant-loader/
├── config.yaml          # Main configuration
├── .env                 # Environment variables
├── data/               # State database and cache
│   └── state.db
├── logs/               # Application logs (optional)
└── venv/               # Python virtual environment
```

### Multi-Environment Setup

Manage multiple environments:

```bash
# Development
/opt/qdrant-loader-dev/

# Staging
/opt/qdrant-loader-staging/

# Production
/opt/qdrant-loader-prod/
```

Each with its own configuration and data isolation.

## 🚀 Scaling Considerations

### Horizontal Scaling

For large-scale deployments:

1. **Multiple Instances**: Run separate instances for different projects
2. **Load Distribution**: Use different QDrant collections for different data sets
3. **Scheduled Processing**: Stagger ingestion times to avoid resource conflicts

### Performance Optimization

Configure processing parameters in your workspace configuration:

```yaml
# config.yaml - Performance tuning
global_config:
  processing:
    max_chunk_workers: 10
    max_embed_workers: 4
    max_upsert_workers: 4
    queue_size: 1000
    upsert_batch_size: 100
```

## 🔗 Related Documentation

- **[Configuration Reference](../users/configuration/config-file-reference.md)** - Configuration options
- **[CLI Reference](../users/cli-reference/README.md)** - Command-line interface
- **[MCP Server Guide](../users/detailed-guides/mcp-server/README.md)** - MCP server setup
- **[Security Considerations](../users/configuration/security-considerations.md)** - Security best practices

---

**Ready to deploy?** Start with a local installation, configure your workspace, and gradually scale up based on your needs. The modular architecture allows for flexible deployment strategies that can grow with your requirements.
