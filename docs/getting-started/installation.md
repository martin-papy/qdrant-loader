# Installation Guide
This guide walks you through installing QDrant Loader and its MCP server on your system. Choose the installation method that best fits your needs.
## 📋 Overview
QDrant Loader consists of two main packages:
- **`qdrant-loader`** - Core data ingestion and processing tool
- **`qdrant-loader-mcp-server`** - Model Context Protocol server for AI tool integration
Both packages can be installed independently, but most users will want both for the complete experience.
## 🔧 Prerequisites
### System Requirements
| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **Python** | 3.12+ | 3.12+ |
| **Memory** | 4GB RAM | 8GB+ RAM |
| **Storage** | 2GB free | 10GB+ free |
| **OS** | Windows 10+, macOS 10.15+, Linux | Latest versions |
### Required Services
#### QDrant Vector Database
QDrant Loader requires a QDrant instance to store vectors and metadata.
**Option 1: Docker**
```bash
# Start QDrant with Docker
docker run -p 6333:6333 -p 6334:6334 \ -v $(pwd)/qdrant_storage:/qdrant/storage:z \ qdrant/qdrant
```
**Option 2: QDrant Cloud**
1. Sign up at [QDrant Cloud](https://cloud.qdrant.io/)
2. Create a cluster
3. Note your cluster URL and API key
**Option 3: Local Installation**
Follow the [QDrant installation guide](https://qdrant.tech/documentation/guides/installation/) for your platform.
#### OpenAI API Access
QDrant Loader uses OpenAI for embeddings generation.
1. Create an account at [OpenAI](https://platform.openai.com/)
2. Generate an API key
3. Ensure you have sufficient credits/quota
### Development Tools (Optional)
For development or advanced usage:
```bash
# Git for repository cloning
git --version
# Docker for containerized services
docker --version
# Node.js for some AI tools integration
node --version
```
## 🚀 Installation Methods
### Method 1: pip Install (Recommended)
This is the easiest method for most users.
#### Install Core Package
```bash
# Install the core QDrant Loader
pip install qdrant-loader
# Verify installation
qdrant-loader --version
```
#### Install MCP Server
```bash
# Install the MCP server package
pip install qdrant-loader-mcp-server
# Verify installation
mcp-qdrant-loader --version
```
#### Install Both Packages
```bash
# Install both packages at once
pip install qdrant-loader qdrant-loader-mcp-server
# Or install with all optional dependencies
pip install qdrant-loader[all] qdrant-loader-mcp-server[all]
```
### Method 2: Development Installation
For contributors or users who want the latest features:
```bash
# Clone the repository
git clone https://github.com/martin-papy/qdrant-loader.git
cd qdrant-loader
# Create virtual environment
python -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate
# Install in development mode
pip install -e packages/qdrant-loader[dev]
pip install -e packages/qdrant-loader-mcp-server[dev]
# Verify installation
qdrant-loader --version
mcp-qdrant-loader --version
```
### Method 3: Virtual Environment (Isolated)
For users who want to keep QDrant Loader isolated:
```bash
# Create dedicated virtual environment
python -m venv qdrant-loader-env
source qdrant-loader-env/bin/activate # On Windows: qdrant-loader-env\Scripts\activate
# Install packages
pip install qdrant-loader qdrant-loader-mcp-server
# Create activation script for future use
echo "source $(pwd)/qdrant-loader-env/bin/activate" > activate-qdrant-loader.sh
chmod +x activate-qdrant-loader.sh
```
## 🔍 Platform-Specific Instructions
### Windows
#### Using Command Prompt
```cmd
# Install Python 3.12+ from python.org
# Open Command Prompt as Administrator
# Install packages
pip install qdrant-loader qdrant-loader-mcp-server
# Verify installation
qdrant-loader --version
```
#### Using PowerShell
```powershell
# Install packages
pip install qdrant-loader qdrant-loader-mcp-server
# Add to PATH if needed
$env:PATH += ";C:\Users\YourUsername\AppData\Local\Programs\Python\Python312\Scripts"
# Verify installation
qdrant-loader --version
```
#### Using Windows Subsystem for Linux (WSL)
```bash
# In WSL terminal
pip install qdrant-loader qdrant-loader-mcp-server
# Verify installation
qdrant-loader --version
```
### macOS
#### Using Terminal
```bash
# Install with pip
pip install qdrant-loader qdrant-loader-mcp-server
# If you get permission errors, use:
pip install --user qdrant-loader qdrant-loader-mcp-server
# Verify installation
qdrant-loader --version
```
#### Using Homebrew Python
```bash
# If using Homebrew Python
brew install python@3.12
pip3 install qdrant-loader qdrant-loader-mcp-server
# Verify installation
qdrant-loader --version
```
### Linux
#### Ubuntu/Debian
```bash
# Update package list
sudo apt update
# Install Python 3.12+ if not available
sudo apt install python3.12 python3.12-pip python3.12-venv
# Install packages
pip3 install qdrant-loader qdrant-loader-mcp-server
# Verify installation
qdrant-loader --version
```
#### CentOS/RHEL/Fedora
```bash
# Install Python 3.12+ if not available
sudo dnf install python3.12 python3.12-pip
# Install packages
pip3 install qdrant-loader qdrant-loader-mcp-server
# Verify installation
qdrant-loader --version
```
#### Arch Linux
```bash
# Install Python if needed
sudo pacman -S python python-pip
# Install packages
pip install qdrant-loader qdrant-loader-mcp-server
# Verify installation
qdrant-loader --version
```
## ✅ Verification
### Test Core Installation
```bash
# Check version
qdrant-loader --version
# Check help
qdrant-loader --help
# Test configuration display
qdrant-loader config
```
### Test MCP Server Installation
```bash
# Check version
mcp-qdrant-loader --version
# Test server startup (Ctrl+C to stop)
mcp-qdrant-loader
# Check help for available options
mcp-qdrant-loader --help
```
### Test Integration
```bash
# Test QDrant connection and basic functionality
qdrant-loader project status
# For basic testing, you would typically:
# 1. Set up a workspace with config.yaml and .env
# 2. Initialize the collection:\1init --workspace .
# 3. Run ingestion:\1ingest --workspace .
```
## 🔧 Configuration Setup
After installation, you'll need to configure QDrant Loader:
### Quick Configuration
```bash
# Create configuration directory and files manually
mkdir -p ~/.qdrant-loader
# Copy template configuration files from the repository or create them manually
# See the configuration examples below
```
### Environment Variables
Create a `.env` file or set environment variables:
```bash
# Required
export QDRANT_URL="http://localhost:6333"
export OPENAI_API_KEY="your-openai-api-key"
# Optional
export QDRANT_API_KEY="your-qdrant-api-key" # For QDrant Cloud
export QDRANT_COLLECTION_NAME="documents"
```
### Configuration File
Create `config.yaml` in your workspace or `~/.qdrant-loader/config.yaml`:
```yaml
# Basic configuration
qdrant: url: "${QDRANT_URL}" collection_name: "${QDRANT_COLLECTION_NAME}"
openai: api_key: "${OPENAI_API_KEY}" model: "text-embedding-3-small"
# Data sources
sources: git: enabled: true confluence: enabled: false local: enabled: true
```
## 🔧 Troubleshooting Installation
### Common Issues
#### Python Version Issues
**Problem**: `qdrant-loader requires Python 3.12+`
**Solution**:
```bash
# Check Python version
python --version
# Install Python 3.12+ from python.org or your package manager
# Use specific version if multiple installed
python3.12 -m pip install qdrant-loader
```
#### Permission Errors
**Problem**: `Permission denied` during installation
**Solution**:
```bash
# Use user installation
pip install --user qdrant-loader qdrant-loader-mcp-server
# Or use virtual environment
python -m venv venv
source venv/bin/activate
pip install qdrant-loader qdrant-loader-mcp-server
```
#### Command Not Found
**Problem**: `qdrant-loader: command not found`
**Solution**:
```bash
# Check if installed
pip list | grep qdrant-loader
# Find installation path
python -m pip show qdrant-loader
# Add to PATH (example for Linux/macOS)
export PATH="$HOME/.local/bin:$PATH"
# For permanent fix, add to ~/.bashrc or ~/.zshrc
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```
#### QDrant Connection Issues
**Problem**: Cannot connect to QDrant
**Solution**:
```bash
# Check if QDrant is running
curl http://localhost:6333/health
# Start QDrant with Docker
docker run -p 6333:6333 qdrant/qdrant
# Check configuration
qdrant-loader config
```
#### OpenAI API Issues
**Problem**: OpenAI API authentication errors
**Solution**:
```bash
# Check API key is set
echo $OPENAI_API_KEY
# Test API key
curl -H "Authorization: Bearer $OPENAI_API_KEY" \ https://api.openai.com/v1/models
# Set API key
export OPENAI_API_KEY="your-actual-api-key"
```
### Getting Help
If you encounter issues not covered here:
1. **Check the logs**: `qdrant-loader --verbose`
2. **Verify configuration**: `qdrant-loader config`
3. **Search existing issues**: [GitHub Issues](https://github.com/martin-papy/qdrant-loader/issues)
4. **Create new issue**: Include error messages and system info
## 🔄 Updating
### Update to Latest Version
```bash
# Update core package
pip install --upgrade qdrant-loader
# Update MCP server
pip install --upgrade qdrant-loader-mcp-server
# Update both
pip install --upgrade qdrant-loader qdrant-loader-mcp-server
```
### Development Updates
```bash
# For development installations
cd qdrant-loader
git pull origin main
pip install -e packages/qdrant-loader[dev]
pip install -e packages/qdrant-loader-mcp-server[dev]
```
## 🔗 Next Steps
After successful installation:
1. **[Quick Start Guide](./quick-start.md)** - Get up and running in 5 minutes
2. **Core Concepts** - Key concepts are summarized inline in Getting Started
3. **[Basic Configuration](./basic-configuration.md)** - Set up your first data sources
4. **[User Guides](../users/)** - Explore detailed feature documentation
## 📋 Installation Checklist
- [ ] **Python 3.12+** installed and accessible
- [ ] **QDrant database** running (Docker, Cloud, or local)
- [ ] **OpenAI API key** obtained and configured
- [ ] **qdrant-loader** package installed
- [ ] **qdrant-loader-mcp-server** package installed
- [ ] **Installation verified** with version commands
- [ ] **Basic configuration** created
- [ ] **QDrant connection** tested
- [ ] **Ready for Quick Start** guide
---
**Installation complete!** 🎉
You're now ready to start using QDrant Loader. Continue with the [Quick Start Guide](./quick-start.md) to ingest your first documents and set up AI tool integration.
