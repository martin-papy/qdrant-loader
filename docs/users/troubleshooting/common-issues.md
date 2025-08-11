# Common Issues Guide
This guide covers the most frequently encountered issues when using QDrant Loader, along with step-by-step solutions and prevention strategies. Whether you're experiencing installation problems, data loading issues, or configuration difficulties, this guide provides practical solutions.
## 🎯 Quick Issue Identification
### Symptom Checker
```
❌ Installation fails → See [Installation Issues](#installation-issues)
❌ Can't connect to QDrant → See [Connection Problems](./connection-problems.md)
❌ Data not loading → See [Data Loading Issues](#data-loading-issues)
❌ Configuration errors → See [Configuration Issues](#configuration-issues)
❌ MCP server not working → See [MCP Server Issues](#mcp-server-issues)
❌ Slow performance → See [Performance Issues](./performance-issues.md)
```
## 🔧 Installation Issues
### Issue: pip install fails
**Symptoms:**
- `pip install qdrant-loader` fails with dependency errors
- Package not found errors
- Permission denied errors
**Solutions:**
```bash
# Solution 1: Update pip and try again
pip install --upgrade pip
pip install qdrant-loader
# Solution 2: Use virtual environment
python -m venv qdrant-env
source qdrant-env/bin/activate # On Windows: qdrant-env\Scripts\activate
pip install qdrant-loader
# Solution 3: Install with user flag
pip install --user qdrant-loader
# Solution 4: Force reinstall
pip install --force-reinstall qdrant-loader
```
**Prevention:**
- Always use virtual environments
- Keep pip updated
- Check Python version compatibility (3.8+)
### Issue: Command not found after installation
**Symptoms:**
- `qdrant-loader: command not found`
- Package installed but CLI not available
**Solutions:**
```bash
# Check if package is installed
pip list | grep qdrant-loader
# Find installation path
python -c "import qdrant_loader; print(qdrant_loader.__file__)"
# Add to PATH (if needed)
export PATH="$HOME/.local/bin:$PATH"
# Or use python -m
python -m qdrant_loader --help
```
### Issue: Import errors
**Symptoms:**
- `ModuleNotFoundError: No module named 'qdrant_loader'`
- Import errors for dependencies
**Solutions:**
```bash
# Check Python environment
which python
python --version
# Reinstall with dependencies
pip install --upgrade qdrant-loader[all]
# Check for conflicting packages
pip check
# Clean install
pip uninstall qdrant-loader
pip install qdrant-loader
```
## 📊 Data Loading Issues
### Issue: No data loaded from source
**Symptoms:**
- Ingest command completes but no vectors in collection
- "0 documents processed" message
- Empty search results through MCP server
**Diagnostic Steps:**
```bash
# Check current configurationqdrant-loader config --workspace .
# Validate project configuration
qdrant-loader project validate --workspace .
# Check project status
qdrant-loader project status --workspace .
# Test with debug loggingqdrant-loader ingest --workspace . --log-level DEBUG
```
**Common Causes & Solutions:**
1. **Incorrect file patterns:**
```yaml
# Problem: Too restrictive patterns in project configuration
projects: my-project: sources: localfile: my-docs: include_paths: - "*.md" # Only markdown files
# Solution: Broader patterns
projects: my-project: sources: localfile: my-docs: include_paths: - "*.md" - "*.txt" - "*.rst" - "docs/**/*"
```
2. **Authentication issues:**
```bash
# Check credentials
echo $QDRANT_API_KEY
echo $OPENAI_API_KEY
echo $CONFLUENCE_TOKEN
echo $JIRA_TOKEN
# Test QDrant connection
curl -H "api-key: $QDRANT_API_KEY" "$QDRANT_URL/health"
# Test OpenAI API
curl -H "Authorization: Bearer $OPENAI_API_KEY" "https://api.openai.com/v1/models"
```
3. **Path issues:**
```bash
# Check if path exists and is accessible
ls -la /path/to/documents
find /path/to/documents -name "*.md" | head -5
# Use absolute paths in configuration
projects: my-project: sources: localfile: my-docs: base_url: "file:///absolute/path/to/docs"
```
### Issue: Partial data loading
**Symptoms:**
- Some files processed, others skipped
- Inconsistent loading results
- Warning messages about skipped files
**Solutions:**
```bash
# Check file permissions
find ./docs -name "*.md" ! -readable
# Check file encoding
file -i ./docs/*.md
# Force reinitialization and reloadqdrant-loader init --workspace . --forceqdrant-loader ingest --workspace .
# Check exclude patterns in configurationqdrant-loader config --workspace . | grep -A 5 exclude_paths
```
### Issue: Duplicate content
**Symptoms:**
- Same content appears multiple times in search
- Higher than expected vector count
- Multiple sources pointing to same content
**Solutions:**
```bash
# Check for overlapping sources in configurationqdrant-loader config --workspace .
# Review project configuration for duplicate sources
qdrant-loader project list --workspace .
# Reinitialize collection to clean duplicatesqdrant-loader init --workspace . --forceqdrant-loader ingest --workspace .
```
## ⚙️ Configuration Issues
### Issue: Configuration validation fails
**Symptoms:**
- `qdrant-loader project validate` fails
- YAML parsing errors
- Missing required fields
**Solutions:**
```bash
# Check YAML syntax
python -c "import yaml; yaml.safe_load(open('config.yaml'))"
# Validate project configuration
qdrant-loader project validate --workspace .
# Check current configurationqdrant-loader config --workspace .
# Validate specific project
qdrant-loader project validate --workspace . --project-id my-project
```
**Common Configuration Problems:**
1. **YAML indentation:**
```yaml
# Wrong indentation
global:
qdrant: url: "http://localhost:6333"
# Correct indentation
global: qdrant: url: "http://localhost:6333"
```
2. **Missing environment variables:**
```bash
# Check required variables
env | grep -E "(QDRANT|OPENAI|CONFLUENCE|JIRA)"
# Set missing variables
export QDRANT_API_KEY="your-key-here"
export OPENAI_API_KEY="your-key-here"
```
3. **Invalid URLs:**
```yaml
# Ensure URLs are complete and accessible
global: qdrant: url: "https://your-qdrant-instance.com" # Include protocol
```
### Issue: Environment variables not loaded
**Symptoms:**
- Configuration uses literal `${VAR_NAME}` instead of values
- Authentication failures
- Connection errors
**Solutions:**
```bash
# Check environment variables
echo $QDRANT_API_KEY
echo $OPENAI_API_KEY
# Load from .env file
export $(cat .env | xargs)
# Check if .env file exists in workspace
ls -la .env
# Verify configuration loads environment variablesqdrant-loader config --workspace .
```
### Issue: Project configuration errors
**Symptoms:**
- Projects not found or recognized
- Invalid project structure
- Missing required project fields
**Solutions:**
```bash
# List all configured projects
qdrant-loader project list --workspace .
# Check project status
qdrant-loader project status --workspace .
# Validate specific project
qdrant-loader project validate --workspace . --project-id my-project
# Check project configuration structureqdrant-loader config --workspace . | grep -A 20 projects
```
## 🔌 MCP Server Issues
### Issue: MCP server won't start
**Symptoms:**
- Server fails to start
- Import errors when starting MCP server
- Permission denied errors
**Solutions:**
```bash
# Check if MCP server package is installed
pip list | grep qdrant-loader-mcp-server
# Install MCP server package
pip install qdrant-loader-mcp-server
# Start MCP server with debug logging
MCP_LOG_LEVEL=DEBUG mcp-qdrant-loader
# Check environment variables for MCP server
env | grep MCP
```
### Issue: AI tools can't connect to MCP server
**Symptoms:**
- Connection refused errors in AI tools
- MCP server running but not accessible
- Configuration issues in AI tools
**Solutions:**
```bash
# Check MCP server configuration in AI tool
# For Cursor, check: ~/.cursor/mcp_settings.json
# Verify MCP server is running
ps aux | grep mcp-qdrant-loader
# Test MCP server manually
echo '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}' | mcp-qdrant-loader
# Check MCP server logs
tail -f ~/.qdrant-loader/logs/mcp-server.log
```
### Issue: Search not working through MCP
**Symptoms:**
- MCP server connected but search fails
- Empty results through AI tools
- MCP tools not available
**Solutions:**
```bash
# Verify workspace configurationqdrant-loader config --workspace .
# Check project status
qdrant-loader project status --workspace .
# Ensure data is loadedqdrant-loader ingest --workspace .
# Restart MCP server with proper workspace
cd /path/to/workspace
mcp-qdrant-loader
```
## 🚨 Emergency Procedures
### Complete System Reset
If you're experiencing multiple issues and need a fresh start:
```bash
# 1. Backup configuration files
cp config.yaml config.yaml.backup
cp .env .env.backup
# 2. Clean installation
pip uninstall qdrant-loader qdrant-loader-mcp-server
pip install qdrant-loader qdrant-loader-mcp-server
# 3. Validate configuration
qdrant-loader project validate --workspace .
# 4. Test basic functionalityqdrant-loader config --workspace .
qdrant-loader project list --workspace .
# 5. Reinitialize and reload dataqdrant-loader init --workspace . --forceqdrant-loader ingest --workspace .
```
### Data Recovery
If you've lost data or corrupted your collection:
```bash
# Check current project status
qdrant-loader project status --workspace .
# Reinitialize collectionqdrant-loader init --workspace . --force
# Reload all data from sourcesqdrant-loader ingest --workspace .
# Verify data is loaded
qdrant-loader project status --workspace .
```
## 📞 Getting Help
### Before Asking for Help
1. **Check logs with debug mode:**
```bashqdrant-loader ingest --workspace . --log-level DEBUG
```
2. **Gather system information:**
```bash
qdrant-loader --version
python --version
pip list | grep qdrant
uname -a
```
3. **Test minimal example:**
```bash
# Create test workspace
mkdir test-workspace && cd test-workspace
# Create minimal configuration
cat > config.yaml << EOF
global: qdrant: url: "${QDRANT_URL}" api_key: "${QDRANT_API_KEY}" openai: api_key: "${OPENAI_API_KEY}"
projects: test-project: display_name: "Test Project" collection_name: "test_collection" sources: localfile: test-docs: base_url: "file://./test-docs" include_paths: ["*.md"]
EOF
# Create test data
mkdir test-docs
echo "# Test Document" > test-docs/test.md
# Test loadingqdrant-loader init --workspace .qdrant-loader ingest --workspace .
```
### Support Channels
- **GitHub Issues**: [Report bugs and feature requests](https://github.com/martin-papy/qdrant-loader/issues)
- **Documentation**: [Check latest documentation](../../README.md)
- **Discussions**: [Community Q&A](https://github.com/martin-papy/qdrant-loader/discussions)
### Issue Report Template
```markdown
## Issue Description
Brief description of the problem
## Environment
- OS: [e.g., Ubuntu 22.04]
- Python: [e.g., 3.11.5]
- QDrant Loader: [e.g., 1.2.3]
- QDrant: [e.g., 1.7.0]
## Steps to Reproduce
1. Step one
2. Step two
3. Step three
## Expected Behavior
What you expected to happen
## Actual Behavior
What actually happened
## Configuration
```yaml
[Paste relevant configuration (sanitized)]
```
## Logs
```
[Paste relevant logs here]
```
## Commands Used
```bash
# List the exact commands you ranqdrant-loader config --workspace .
qdrant-loader project validate --workspace .
```
```
## 🔗 Related Documentation
- **[Performance Issues](./performance-issues.md)** - Performance troubleshooting
- **[Connection Problems](./connection-problems.md)** - Network and connectivity issues
- **[Error Messages Reference](./error-messages-reference.md)** - Detailed error explanations
- **[Configuration Reference](../configuration/config-file-reference.md)** - Configuration options
- **[CLI Reference](../cli-reference/commands.md)** - Command-line interface
---
**Most common issues resolved!** 🎉
This guide covers the majority of issues users encounter. For specific error messages, check the [Error Messages Reference](./error-messages-reference.md), and for performance-related problems, see the [Performance Issues Guide](./performance-issues.md).
