# Common Issues Guide

This guide covers the most frequently encountered issues when using QDrant Loader, along with step-by-step solutions and prevention strategies. Whether you're experiencing installation problems, data loading issues, or search difficulties, this guide provides practical solutions.

## 🎯 Quick Issue Identification

### Symptom Checker

```
❌ Installation fails          → See [Installation Issues](#installation-issues)
❌ Can't connect to QDrant     → See [Connection Problems](./connection-problems.md)
❌ Data not loading            → See [Data Loading Issues](#data-loading-issues)
❌ Search returns no results   → See [Search Issues](#search-issues)
❌ Slow performance            → See [Performance Issues](./performance-issues.md)
❌ MCP server not working      → See [MCP Server Issues](#mcp-server-issues)
❌ Configuration errors        → See [Configuration Issues](#configuration-issues)
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
source qdrant-env/bin/activate  # On Windows: qdrant-env\Scripts\activate
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

- Load command completes but no vectors in collection
- "0 documents processed" message
- Empty search results

**Diagnostic Steps:**

```bash
# Check source accessibility
qdrant-loader config test --source git
qdrant-loader config test --source confluence

# Verify configuration
qdrant-loader config validate

# Check collection status
qdrant-loader status --collection your_collection --detailed

# Test with verbose logging
qdrant-loader load --source local --path ./test --verbose
```

**Common Causes & Solutions:**

1. **Incorrect file patterns:**

```yaml
# Problem: Too restrictive patterns
include_patterns:
  - "*.md"  # Only markdown files

# Solution: Broader patterns
include_patterns:
  - "*.md"
  - "*.txt"
  - "*.rst"
  - "docs/**/*"
```

2. **Authentication issues:**

```bash
# Check credentials
echo $CONFLUENCE_API_TOKEN
echo $GITHUB_TOKEN

# Test authentication
curl -u "$CONFLUENCE_USERNAME:$CONFLUENCE_API_TOKEN" \
  "$CONFLUENCE_URL/rest/api/content"
```

3. **Path issues:**

```bash
# Check if path exists and is accessible
ls -la /path/to/documents
find /path/to/documents -name "*.md" | head -5

# Use absolute paths
qdrant-loader load --source local --path "$(pwd)/docs"
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

# Use force reload
qdrant-loader load --source local --path ./docs --force

# Check exclude patterns
qdrant-loader config show | grep -A 5 exclude_patterns
```

### Issue: Duplicate content

**Symptoms:**

- Same content appears multiple times in search
- Higher than expected vector count
- Duplicate detection warnings

**Solutions:**

```bash
# Enable duplicate detection
qdrant-loader load --source local --path ./docs --deduplicate

# Clean existing duplicates
qdrant-loader optimize --collection your_collection --remove-duplicates

# Check for multiple sources pointing to same content
qdrant-loader config show | grep -A 10 data_sources
```

## 🔍 Search Issues

### Issue: No search results

**Symptoms:**

- Search returns empty results
- "No matches found" for obvious queries
- Search works for some terms but not others

**Diagnostic Steps:**

```bash
# Check collection has data
qdrant-loader status --collection your_collection

# Test basic search
qdrant-loader search "test" --collection your_collection --limit 10

# Check with different similarity thresholds
qdrant-loader search "your query" --threshold 0.5
qdrant-loader search "your query" --threshold 0.3

# Test exact text search
qdrant-loader search "exact phrase from document" --collection your_collection
```

**Common Solutions:**

1. **Lower similarity threshold:**

```bash
# Default threshold might be too high
qdrant-loader search "query" --threshold 0.4
```

2. **Check embedding model:**

```yaml
# Ensure consistent embedding model
openai:
  model: "text-embedding-3-small"  # Use same model for indexing and search
```

3. **Verify collection name:**

```bash
# List available collections
qdrant-loader collection list

# Search in correct collection
qdrant-loader search "query" --collection correct_collection_name
```

### Issue: Poor search quality

**Symptoms:**

- Irrelevant results returned
- Good content not found
- Inconsistent search quality

**Solutions:**

```bash
# Optimize collection
qdrant-loader optimize --collection your_collection

# Rebuild with better chunking
qdrant-loader load --source local --path ./docs --chunk-size 800 --chunk-overlap 200 --force

# Use semantic search with filters
qdrant-loader search "query" --filter "content_type:documentation"

# Try different search strategies
qdrant-loader search "query" --strategy hybrid
```

## ⚙️ Configuration Issues

### Issue: Configuration validation fails

**Symptoms:**

- `qdrant-loader config validate` fails
- YAML parsing errors
- Missing required fields

**Solutions:**

```bash
# Check YAML syntax
python -c "import yaml; yaml.safe_load(open('qdrant-loader.yaml'))"

# Validate against schema
qdrant-loader config validate --verbose

# Use example configuration
qdrant-loader config init --example

# Check for common issues
grep -n "api_key.*:" qdrant-loader.yaml  # Check for exposed secrets
```

**Common Configuration Problems:**

1. **YAML indentation:**

```yaml
# Wrong indentation
qdrant:
url: "http://localhost:6333"

# Correct indentation
qdrant:
  url: "http://localhost:6333"
```

2. **Missing environment variables:**

```bash
# Check required variables
env | grep -E "(QDRANT|OPENAI|CONFLUENCE)"

# Set missing variables
export QDRANT_API_KEY="your-key-here"
```

3. **Invalid URLs:**

```yaml
# Ensure URLs are complete and accessible
qdrant:
  url: "https://your-qdrant-instance.com"  # Include protocol
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

# Use explicit config
qdrant-loader load --qdrant-url "https://your-instance.com" --qdrant-api-key "your-key"

# Debug variable expansion
qdrant-loader config show --expand-vars
```

## 🔌 MCP Server Issues

### Issue: MCP server won't start

**Symptoms:**

- Server fails to start
- Port already in use errors
- Permission denied errors

**Solutions:**

```bash
# Check if port is available
netstat -tlnp | grep :3000

# Use different port
qdrant-loader mcp-server start --port 3001

# Check permissions
sudo qdrant-loader mcp-server start --port 80  # If needed

# Start with verbose logging
qdrant-loader mcp-server start --verbose
```

### Issue: AI tools can't connect to MCP server

**Symptoms:**

- Connection refused errors in AI tools
- MCP server running but not accessible
- Authentication failures

**Solutions:**

```bash
# Check server status
qdrant-loader mcp-server status

# Test connection
curl http://localhost:3000/health

# Check firewall settings
sudo ufw status
sudo ufw allow 3000

# Verify MCP configuration in AI tool
cat ~/.config/cursor/mcp-settings.json
```

### Issue: Search not working through MCP

**Symptoms:**

- MCP server connected but search fails
- Empty results through AI tools
- Direct CLI search works but MCP doesn't

**Solutions:**

```bash
# Check MCP server logs
qdrant-loader mcp-server logs

# Test MCP search directly
curl -X POST http://localhost:3000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "limit": 5}'

# Restart MCP server
qdrant-loader mcp-server restart

# Check collection access
qdrant-loader mcp-server status --collections
```

## 🚨 Emergency Procedures

### Complete System Reset

If you're experiencing multiple issues and need a fresh start:

```bash
# 1. Stop all services
qdrant-loader mcp-server stop

# 2. Backup important data
qdrant-loader backup --collection your_collection --output backup.tar.gz

# 3. Clean installation
pip uninstall qdrant-loader
pip install qdrant-loader

# 4. Reset configuration
mv qdrant-loader.yaml qdrant-loader.yaml.backup
qdrant-loader config init

# 5. Test basic functionality
qdrant-loader config test
qdrant-loader load --source local --path ./test-docs --dry-run

# 6. Restore data if needed
qdrant-loader collection restore --input backup.tar.gz
```

### Data Recovery

If you've lost data or corrupted your collection:

```bash
# Check for automatic backups
ls -la ~/.qdrant-loader/backups/

# Restore from backup
qdrant-loader collection restore --input latest-backup.tar.gz

# Rebuild from source
qdrant-loader load --source git --force --collection recovered_collection

# Verify data integrity
qdrant-loader status --collection recovered_collection --detailed
```

## 📞 Getting Help

### Before Asking for Help

1. **Check logs:**

```bash
qdrant-loader --verbose load --source local --path ./docs
tail -f ~/.qdrant-loader/logs/qdrant-loader.log
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
# Create test data
mkdir test-docs
echo "# Test Document" > test-docs/test.md

# Test loading
qdrant-loader load --source local --path test-docs --dry-run
```

### Support Channels

- **GitHub Issues**: [Report bugs and feature requests](https://github.com/company/qdrant-loader/issues)
- **Documentation**: [Check latest documentation](https://docs.qdrant-loader.com)
- **Community**: [Join discussions](https://discord.gg/qdrant-loader)

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

## Logs
```

[Paste relevant logs here]

```

## Configuration
```yaml
[Paste relevant configuration]
```

```

## 🔗 Related Documentation

- **[Performance Issues](./performance-issues.md)** - Performance troubleshooting
- **[Connection Problems](./connection-problems.md)** - Network and connectivity issues
- **[Error Messages Reference](./error-messages-reference.md)** - Detailed error explanations
- **[Configuration Reference](../configuration/config-file-reference.md)** - Configuration options
- **[CLI Reference](../cli/commands-reference.md)** - Command-line interface

---

**Most common issues resolved!** 🎉

This guide covers the majority of issues users encounter. For specific error messages, check the [Error Messages Reference](./error-messages-reference.md), and for performance-related problems, see the [Performance Issues Guide](./performance-issues.md).
