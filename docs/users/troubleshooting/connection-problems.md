# Connection Problems Guide

This guide helps you diagnose and resolve connection issues with QDrant Loader, including QDrant instance connectivity, API authentication problems, network configuration issues, and firewall restrictions. Whether you're having trouble connecting to QDrant, external APIs, or data sources, this guide provides systematic troubleshooting steps.

## 🎯 Connection Issue Types

### Quick Diagnosis

```text
🔌 Can't connect to QDrant → See [QDrant Connection Issues](#qdrant-connection-issues)
🔑 Authentication failures → See [Authentication Problems](#authentication-problems)
🌐 Network timeouts → See [Network Issues](#network-issues)
🛡️ Firewall blocking → See [Firewall Problems](#firewall-problems)
📡 API connection errors → See [External API Issues](#external-api-issues)
🔒 SSL/TLS problems → See [SSL/TLS Issues](#ssltls-issues)
```

## 🔌 QDrant Connection Issues

### Issue: Cannot connect to QDrant instance

**Symptoms:**

- `Connection refused` errors
- `Connection timeout` messages
- `Host unreachable` errors
- QDrant operations fail immediately

**Diagnostic Steps:**

```bash
# Test basic connectivity
ping your-qdrant-instance.com
telnet your-qdrant-instance.com 6333

# Check QDrant health endpoint
curl -v "$QDRANT_URL/health"

# Test with different protocols
curl -v "http://your-qdrant-instance.com:6333/health"
curl -v "https://your-qdrant-instance.com:6333/health"

# Check DNS resolution
nslookup your-qdrant-instance.com
dig your-qdrant-instance.com
```

**Common Solutions:**

1. **Verify QDrant URL format:**

```bash
# Correct URL formats
export QDRANT_URL="http://localhost:6333"
export QDRANT_URL="https://your-instance.qdrant.cloud"
export QDRANT_URL="http://192.168.1.100:6333"

# Test configuration
qdrant-loader config --workspace .
```

1. **Check QDrant instance status:**

```bash
# For local QDrant
docker ps | grep qdrant
docker logs qdrant-container

# For cloud QDrant
curl -s "$QDRANT_URL/health" | jq
```

1. **Verify port accessibility:**

```bash
# Check if port is open
nmap -p 6333 your-qdrant-instance.com
nc -zv your-qdrant-instance.com 6333

# Check local firewall
sudo ufw status
sudo iptables -L
```

### Issue: QDrant connection drops frequently

**Symptoms:**

- Intermittent connection failures
- Operations succeed sometimes, fail others
- "Connection reset by peer" errors
- Timeout errors during long operations

**Solutions:**

Configure connection settings in your workspace configuration:

```yaml
# config.yaml
global:
  qdrant:
    url: "${QDRANT_URL}"
    api_key: "${QDRANT_API_KEY}"
    timeout: 60
    max_retries: 5
    retry_delay: 2
```

### Issue: QDrant authentication fails

**Symptoms:**

- `401 Unauthorized` errors
- `403 Forbidden` responses
- "Invalid API key" messages
- Authentication required errors

**Solutions:**

```bash
# Check API key format
echo $QDRANT_API_KEY | wc -c  # Should be reasonable length
echo $QDRANT_API_KEY | head -c 10  # Check first few characters

# Test authentication manually
curl -H "api-key: $QDRANT_API_KEY" "$QDRANT_URL/collections"

# Verify API key in configuration
qdrant-loader config --workspace .

# Check environment variables
env | grep QDRANT
```

## 🔑 Authentication Problems

### Issue: OpenAI API authentication fails

**Symptoms:**

- `401 Unauthorized` from OpenAI
- "Invalid API key" errors
- Embedding generation fails
- Rate limit errors

**Diagnostic Steps:**

```bash
# Check LLM API key (new unified approach)
echo $LLM_API_KEY | wc -c  # Should be around 51 characters for OpenAI
echo $LLM_API_KEY | grep -E "^sk-"  # Should start with sk- for OpenAI

# Check legacy OpenAI API key (still supported)
echo $OPENAI_API_KEY | wc -c
echo $OPENAI_API_KEY | grep -E "^sk-"

# Test LLM API directly
curl -H "Authorization: Bearer $LLM_API_KEY" \
  "https://api.openai.com/v1/models"

# Test legacy OpenAI API (still supported)
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  "https://api.openai.com/v1/models"

# Check API usage and limits
curl -H "Authorization: Bearer $LLM_API_KEY" \
  "https://api.openai.com/v1/usage"
```

**Solutions:**

```bash
# Verify API key is set correctly (new unified approach)
export LLM_API_KEY="sk-your-actual-key-here"
export OPENAI_API_KEY="sk-your-actual-key-here"  # Legacy support

# Check configuration
qdrant-loader config --workspace .

# Test with debug logging
qdrant-loader ingest --workspace . --log-level DEBUG
```

### Issue: Confluence authentication fails

**Symptoms:**

- `401 Unauthorized` from Confluence
- "Authentication required" errors
- Cannot access Confluence spaces
- API token rejected

**Solutions:**

```bash
# Check Confluence credentials
echo $CONFLUENCE_USERNAME
echo $CONFLUENCE_TOKEN | wc -c

# Test Confluence API manually
curl -u "$CONFLUENCE_USERNAME:$CONFLUENCE_TOKEN" \
  "$CONFLUENCE_URL/rest/api/content?limit=1"

# Verify base URL format
echo $CONFLUENCE_URL  # Should be like https://company.atlassian.net

# Check project configuration
qdrant-loader config --workspace .
```

**Confluence authentication configuration:**

```yaml
# config.yaml
projects:
  my-project:
    sources:
      confluence:
        my-confluence:
          base_url: "${CONFLUENCE_URL}"
          deployment_type: "cloud"  # or "datacenter"
          space_key: "MYSPACE"
          email: "${CONFLUENCE_USERNAME}"
          token: "${CONFLUENCE_TOKEN}"
```

### Issue: Git repository authentication fails

**Symptoms:**

- `403 Forbidden` when cloning repositories
- "Authentication failed" for private repos
- SSH key errors
- Token authentication rejected

**Solutions:**

```bash
# For HTTPS with token
git clone https://token:$GITHUB_TOKEN@github.com/user/repo.git

# For SSH
ssh-add ~/.ssh/id_rsa
ssh -T git@github.com

# Check project configuration
qdrant-loader config --workspace .
```

**Git authentication configuration:**

```yaml
# config.yaml
projects:
  my-project:
    sources:
      git:
        my-repo:
          base_url: "https://github.com/user/repo"
          branch: "main"
          token: "${GITHUB_TOKEN}"
```

## 🌐 Network Issues

### Issue: Network timeouts

**Symptoms:**

- Operations timeout after long delays
- "Connection timed out" errors
- Slow response times
- Intermittent failures

**Diagnostic Steps:**

```bash
# Test network latency
ping -c 10 your-qdrant-instance.com

# Check network path
traceroute your-qdrant-instance.com
mtr your-qdrant-instance.com

# Test bandwidth
curl -w "@curl-format.txt" -o /dev/null -s "$QDRANT_URL/health"

# Monitor network usage
iftop -i eth0
nethogs
```

**Solutions:**

Configure timeouts in your workspace configuration:

```yaml
# config.yaml
global:
  qdrant:
    url: "${QDRANT_URL}"
    api_key: "${QDRANT_API_KEY}"
    timeout: 120
  llm:
    provider: "openai"
    base_url: "https://api.openai.com/v1"
    api_key: "${LLM_API_KEY}"
    models:
      embeddings: "text-embedding-3-small"
      chat: "gpt-4o-mini"
    request:
      timeout_s: 60
    embeddings:
      vector_size: 1536
```

### Issue: DNS resolution problems

**Symptoms:**

- "Name or service not known" errors
- "Host not found" messages
- Inconsistent connectivity
- Works with IP but not hostname

**Solutions:**

```bash
# Check DNS configuration
cat /etc/resolv.conf
nslookup your-qdrant-instance.com

# Try different DNS servers
nslookup your-qdrant-instance.com 8.8.8.8
nslookup your-qdrant-instance.com 1.1.1.1

# Use IP address temporarily
export QDRANT_URL="http://192.168.1.100:6333"

# Clear DNS cache
sudo systemctl restart systemd-resolved
# or
sudo dscacheutil -flushcache  # macOS
```

## 🛡️ Firewall Problems

### Issue: Firewall blocking connections

**Symptoms:**

- "Connection refused" errors
- Timeouts on specific ports
- Works locally but not remotely
- Selective connectivity issues

**Diagnostic Steps:**

```bash
# Check local firewall
sudo ufw status verbose
sudo iptables -L -n

# Test port accessibility
nmap -p 6333 your-qdrant-instance.com
telnet your-qdrant-instance.com 6333

# Check from different networks
# Try from different machines/networks
```

**Solutions:**

```bash
# Open required ports (local firewall)
sudo ufw allow 6333
sudo ufw allow out 6333

# For iptables
sudo iptables -A INPUT -p tcp --dport 6333 -j ACCEPT
sudo iptables -A OUTPUT -p tcp --dport 6333 -j ACCEPT

# Check corporate firewall
# Contact network administrator for:
# - Outbound HTTPS (443) access
# - Custom ports (6333 for QDrant)
# - API endpoints (api.openai.com, etc.)
```

### Issue: Corporate proxy blocking

**Symptoms:**

- Works at home but not at office
- SSL certificate errors
- Proxy authentication required
- Specific domains blocked

**Solutions:**

```bash
# Configure proxy settings
export HTTP_PROXY="http://proxy.company.com:8080"
export HTTPS_PROXY="https://proxy.company.com:8080"
export NO_PROXY="localhost,127.0.0.1,.local"

# With authentication
export HTTP_PROXY="http://username:password@proxy.company.com:8080"

# Test proxy connectivity
curl --proxy "$HTTP_PROXY" -v "https://api.openai.com/v1/models"
```

## 📡 External API Issues

### Issue: OpenAI API connectivity problems

**Symptoms:**

- Cannot reach OpenAI API
- SSL handshake failures
- Rate limiting errors
- Regional restrictions

**Solutions:**

```bash
# Test OpenAI API connectivity
curl -v "https://api.openai.com/v1/models"

# Check for rate limiting
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  "https://api.openai.com/v1/usage"

# Test with debug logging
qdrant-loader ingest --workspace . --log-level DEBUG
```

### Issue: Confluence API connectivity

**Symptoms:**

- Cannot reach Confluence instance
- API version incompatibility
- Cloud vs Server API differences
- Rate limiting from Confluence

**Solutions:**

```bash
# Test Confluence API version
curl "$CONFLUENCE_URL/rest/api/content?limit=1"

# Check API capabilities
curl "$CONFLUENCE_URL/rest/api/space"

# Verify project configuration
qdrant-loader config --workspace .
```

### Issue: JIRA API connectivity

**Symptoms:**

- Cannot reach JIRA instance
- API authentication failures
- Rate limiting from JIRA
- Project access denied

**Solutions:**

```bash
# Test JIRA API connectivity
curl -u "$JIRA_EMAIL:$JIRA_TOKEN" \
  "$JIRA_URL/rest/api/2/project"

# Check project access
curl -u "$JIRA_EMAIL:$JIRA_TOKEN" \
  "$JIRA_URL/rest/api/2/project/PROJECTKEY"

# Verify project configuration
qdrant-loader config --workspace .
```

**JIRA authentication configuration:**

```yaml
# config.yaml
projects:
  my-project:
    sources:
      jira:
        my-jira:
          base_url: "${JIRA_URL}"
          deployment_type: "cloud"  # or "datacenter"
          project_key: "MYPROJECT"
          email: "${JIRA_EMAIL}"
          token: "${JIRA_TOKEN}"
```

## 🔒 SSL/TLS Issues

### Issue: SSL certificate problems

**Symptoms:**

- "SSL certificate verify failed" errors
- "Certificate has expired" messages
- "Hostname doesn't match certificate"
- SSL handshake failures

**Diagnostic Steps:**

```bash
# Check certificate details
openssl s_client -connect your-qdrant-instance.com:443 -servername your-qdrant-instance.com

# Check certificate expiration
echo | openssl s_client -connect your-qdrant-instance.com:443 2>/dev/null | openssl x509 -noout -dates

# Test with curl
curl -vvv "https://your-qdrant-instance.com"
```

**Solutions:**

```bash
# Update certificates
sudo apt-get update && sudo apt-get install ca-certificates
# or
brew install ca-certificates

# Use specific certificate bundle
export SSL_CERT_FILE="/path/to/certificates.pem"
export REQUESTS_CA_BUNDLE="/path/to/certificates.pem"

# For development only (NOT for production)
export PYTHONHTTPSVERIFY=0
```

## 🚨 Emergency Connection Recovery

### When all connections fail

```bash
# 1. Check basic network connectivity
ping 8.8.8.8
ping google.com

# 2. Restart network services
sudo systemctl restart networking
sudo systemctl restart NetworkManager

# 3. Clear DNS cache
sudo systemctl restart systemd-resolved

# 4. Reset network configuration
sudo dhclient -r && sudo dhclient

# 5. Test configuration
qdrant-loader config --workspace .
```

### Connection recovery script

```bash
#!/bin/bash
# connection-recovery.sh - Automated connection recovery
set -euo pipefail

echo "🔧 Starting connection recovery..."

# Test basic connectivity
if ! ping -c 1 8.8.8.8 >/dev/null 2>&1; then
  echo "❌ No internet connectivity"
  exit 1
fi

# Test DNS resolution
if ! nslookup google.com >/dev/null 2>&1; then
  echo "🔄 Restarting DNS services..."
  sudo systemctl restart systemd-resolved
fi

# Test QDrant connectivity
if ! curl -s --max-time 10 "$QDRANT_URL/health" >/dev/null; then
  echo "🔄 QDrant connection failed, checking configuration..."
  qdrant-loader config --workspace .
fi

# Test OpenAI API
if ! curl -s --max-time 10 "https://api.openai.com/v1/models" >/dev/null; then
  echo "🔄 OpenAI API connection failed"
fi

echo "✅ Connection recovery completed"
```

## 📊 Connection Monitoring

### Basic monitoring

```bash
# Check project status
qdrant-loader config --workspace .

# Test configuration
qdrant-loader config --workspace .

# Validate projects
qdrant-loader config --workspace .

# Monitor system resources
top -p $(pgrep -f qdrant-loader)
```

### Environment verification

```bash
# Check all required environment variables
env | grep -E "(QDRANT|OPENAI|CONFLUENCE|JIRA)"

# Test basic connectivity
curl -s "$QDRANT_URL/health"
curl -s "https://api.openai.com/v1/models"

# Verify workspace configuration
qdrant-loader config --workspace .
```

### Connection testing workflow

```bash
# 1. Validate configuration
qdrant-loader config --workspace .

# 2. Check environment variables
env | grep -E "(QDRANT|OPENAI|CONFLUENCE|JIRA)"

# 3. Test external connectivity
curl -s "$QDRANT_URL/health"
curl -s "https://api.openai.com/v1/models"

# 4. Test with debug logging
qdrant-loader ingest --workspace . --log-level DEBUG --project test-project

# 5. Check project status
qdrant-loader config --workspace .
```

## 🔗 Related Documentation

- **[Common Issues](./common-issues.md)** - General troubleshooting
- **[Performance Issues](./performance-issues.md)** - Performance optimization
- **[Error Messages Reference](./error-messages-reference.md)** - Detailed error explanations
- **[Security Considerations](../configuration/security-considerations.md)** - Security configuration

---

**Connection problems resolved!** 🔌

This guide covers comprehensive connection troubleshooting. For specific error messages, check the [Error Messages Reference](./error-messages-reference.md), and for performance-related connection issues, see the [Performance Issues Guide](./performance-issues.md).
