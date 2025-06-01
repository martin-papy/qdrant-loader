# Connection Problems Guide

This guide helps you diagnose and resolve connection issues with QDrant Loader, including QDrant instance connectivity, API authentication problems, network configuration issues, and firewall restrictions. Whether you're having trouble connecting to QDrant, external APIs, or data sources, this guide provides systematic troubleshooting steps.

## 🎯 Connection Issue Types

### Quick Diagnosis

```
🔌 Can't connect to QDrant      → See [QDrant Connection Issues](#qdrant-connection-issues)
🔑 Authentication failures      → See [Authentication Problems](#authentication-problems)
🌐 Network timeouts            → See [Network Issues](#network-issues)
🛡️ Firewall blocking          → See [Firewall Problems](#firewall-problems)
📡 API connection errors       → See [External API Issues](#external-api-issues)
🔒 SSL/TLS problems           → See [SSL/TLS Issues](#ssltls-issues)
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

# Test connection
qdrant-loader config test --connection qdrant
```

2. **Check QDrant instance status:**

```bash
# For local QDrant
docker ps | grep qdrant
docker logs qdrant-container

# For cloud QDrant
curl -s "$QDRANT_URL/health" | jq
```

3. **Verify port accessibility:**

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

```bash
# Increase connection timeout
qdrant-loader config set qdrant.timeout 60

# Enable connection retry
qdrant-loader config set qdrant.max_retries 5
qdrant-loader config set qdrant.retry_delay 2

# Use connection pooling
qdrant-loader config set qdrant.connection_pool_size 10
```

**Configuration for unstable connections:**

```yaml
qdrant:
  url: "${QDRANT_URL}"
  api_key: "${QDRANT_API_KEY}"
  timeout: 60
  max_retries: 5
  retry_delay: 2
  connection_pool_size: 10
  keep_alive: true
  
  # Circuit breaker for failing connections
  circuit_breaker:
    failure_threshold: 5
    recovery_timeout: 30
    half_open_max_calls: 3
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
qdrant-loader config show | grep -A 2 qdrant

# Test with explicit API key
qdrant-loader status --qdrant-api-key "your-api-key-here"
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
# Check OpenAI API key
echo $OPENAI_API_KEY | wc -c  # Should be around 51 characters
echo $OPENAI_API_KEY | grep -E "^sk-"  # Should start with sk-

# Test OpenAI API directly
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  "https://api.openai.com/v1/models"

# Check API usage and limits
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  "https://api.openai.com/v1/usage"
```

**Solutions:**

```bash
# Verify API key is set correctly
export OPENAI_API_KEY="sk-your-actual-key-here"

# Test with QDrant Loader
qdrant-loader config test --connection openai

# Check for rate limiting
qdrant-loader load --source local --path ./small-test --rate-limit 10
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
echo $CONFLUENCE_API_TOKEN | wc -c

# Test Confluence API manually
curl -u "$CONFLUENCE_USERNAME:$CONFLUENCE_API_TOKEN" \
  "$CONFLUENCE_URL/rest/api/content?limit=1"

# Verify base URL format
echo $CONFLUENCE_URL  # Should be like https://company.atlassian.net

# Test with QDrant Loader
qdrant-loader config test --source confluence
```

**Confluence authentication configuration:**

```yaml
data_sources:
  confluence:
    base_url: "${CONFLUENCE_URL}"
    username: "${CONFLUENCE_USERNAME}"
    api_token: "${CONFLUENCE_API_TOKEN}"
    
    # Authentication troubleshooting
    auth_method: "basic"  # or "bearer" for some setups
    verify_ssl: true
    timeout: 30
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

# Test repository access
qdrant-loader config test --source git --url "https://github.com/user/repo"

# Use explicit credentials
qdrant-loader load --source git \
  --url "https://github.com/user/repo" \
  --git-token "$GITHUB_TOKEN"
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

```bash
# Increase timeouts globally
export QDRANT_LOADER_TIMEOUT=120

# Configure per-operation timeouts
qdrant-loader load --source local --path ./docs --timeout 300

# Use compression to reduce bandwidth
qdrant-loader load --source git --url repo --compression gzip
```

**Network optimization configuration:**

```yaml
network:
  timeout: 120
  connect_timeout: 30
  read_timeout: 60
  max_retries: 3
  retry_delay: 5
  compression: true
  keep_alive: true
  
  # Proxy configuration if needed
  proxy:
    http: "http://proxy.company.com:8080"
    https: "https://proxy.company.com:8080"
    no_proxy: "localhost,127.0.0.1,.local"
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

**Proxy configuration:**

```yaml
network:
  proxy:
    http: "${HTTP_PROXY}"
    https: "${HTTPS_PROXY}"
    no_proxy: "${NO_PROXY}"
    
    # Proxy authentication
    username: "${PROXY_USERNAME}"
    password: "${PROXY_PASSWORD}"
    
    # SSL verification
    verify_ssl: false  # Only if corporate proxy intercepts SSL
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

# Use different endpoint if available
export OPENAI_API_BASE="https://api.openai.com/v1"

# Configure rate limiting
qdrant-loader load --source local --path ./docs --rate-limit 10 --batch-size 5
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

# Use appropriate API version
qdrant-loader config set confluence.api_version "cloud"  # or "server"
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
# Temporary: Disable SSL verification (NOT for production)
export PYTHONHTTPSVERIFY=0
qdrant-loader config set verify_ssl false

# Update certificates
sudo apt-get update && sudo apt-get install ca-certificates
# or
brew install ca-certificates

# Use specific certificate bundle
export SSL_CERT_FILE="/path/to/certificates.pem"
export REQUESTS_CA_BUNDLE="/path/to/certificates.pem"
```

**SSL configuration:**

```yaml
network:
  ssl:
    verify: true
    cert_file: "/path/to/client.crt"
    key_file: "/path/to/client.key"
    ca_bundle: "/path/to/ca-bundle.crt"
    
    # For self-signed certificates (development only)
    verify_hostname: false
    check_hostname: false
```

## 🔧 Advanced Connection Troubleshooting

### Connection pooling issues

**Symptoms:**

- "Connection pool exhausted" errors
- Slow connection establishment
- Resource leaks
- Performance degradation

**Solutions:**

```yaml
# Optimize connection pooling
qdrant:
  connection_pool_size: 20
  connection_pool_maxsize: 50
  connection_pool_block: false
  connection_timeout: 30
  
  # Connection lifecycle
  pool_pre_ping: true
  pool_recycle: 3600
  pool_reset_on_return: "commit"
```

### Load balancer issues

**Symptoms:**

- Inconsistent responses
- Session affinity problems
- Health check failures
- Timeout variations

**Solutions:**

```bash
# Test different endpoints
curl -v "$QDRANT_URL/health"
curl -v "$QDRANT_URL/collections"

# Check load balancer configuration
# Ensure health checks are properly configured
# Verify session affinity settings
# Check timeout configurations
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

# 5. Test with minimal configuration
qdrant-loader config test --minimal
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
    qdrant-loader config validate
fi

# Test OpenAI API
if ! curl -s --max-time 10 "https://api.openai.com/v1/models" >/dev/null; then
    echo "🔄 OpenAI API connection failed"
fi

# Restart MCP server
echo "🔄 Restarting MCP server..."
qdrant-loader mcp-server restart

echo "✅ Connection recovery completed"
```

## 📊 Connection Monitoring

### Continuous monitoring setup

```bash
# Monitor connection health
qdrant-loader monitor connections --interval 60 --alert-on-failure

# Log connection metrics
qdrant-loader monitor connections --log-file connection-health.log

# Set up alerts
qdrant-loader alert create \
  --metric "connection_failures" \
  --threshold 3 \
  --action "restart_mcp_server"
```

### Connection health dashboard

```bash
# Create connection dashboard
qdrant-loader dashboard create --type connections --port 8080

# Monitor key metrics:
# - Connection success rate
# - Response times
# - Error rates
# - Retry attempts
```

## 🔗 Related Documentation

- **[Common Issues](./common-issues.md)** - General troubleshooting
- **[Performance Issues](./performance-issues.md)** - Performance optimization
- **[Error Messages Reference](./error-messages-reference.md)** - Detailed error explanations
- **[Security Considerations](../configuration/security-considerations.md)** - Security configuration
- **[Network Configuration](../configuration/advanced-settings.md#network-settings)** - Advanced network settings

---

**Connection problems resolved!** 🔌

This guide covers comprehensive connection troubleshooting. For specific error messages, check the [Error Messages Reference](./error-messages-reference.md), and for performance-related connection issues, see the [Performance Issues Guide](./performance-issues.md).
