# Troubleshooting Guide

Welcome to the QDrant Loader troubleshooting guide! This section provides comprehensive solutions for common issues, performance problems, and error messages you might encounter. Whether you're a new user or an experienced developer, these guides will help you quickly identify and resolve problems.

## 🎯 Quick Problem Identification

### Symptom Checker

Use this quick reference to identify your issue and jump to the right solution:

```text
❌ Installation fails → [Common Issues](./common-issues.md#installation-issues)
🔌 Can't connect to QDrant → [Connection Problems](./connection-problems.md#qdrant-connection-issues)
🔑 Authentication errors → [Connection Problems](./connection-problems.md#authentication-problems)
📊 Data won't load → [Common Issues](./common-issues.md#data-loading-issues)
🔍 Search returns no results → [Common Issues](./common-issues.md#search-issues)
🐌 Everything is slow → [Performance Issues](./performance-issues.md)
💾 High memory usage → [Performance Issues](./performance-issues.md#memory-issues)
🌐 Network timeouts → [Connection Problems](./connection-problems.md#network-issues)
🛡️ Firewall blocking → [Connection Problems](./connection-problems.md#firewall-problems)
📁 File permission errors → [Error Messages](./error-messages-reference.md#file-system-errors)
⚙️ Configuration problems → [Error Messages](./error-messages-reference.md#configuration-errors)
```

### Error Message Lookup

Got a specific error message? Look it up directly:

```bash
# Search for your error message in documentation
grep -r "your error message" docs/users/troubleshooting/

# Or check the comprehensive error reference
# See: Error Messages Reference → [specific error category]
```

## Troubleshooting Guides

### 🔧 [Common Issues](./common-issues.md)

**Start here for most problems!** Covers the most frequently encountered issues with step-by-step solutions.

**What's covered:**

- Installation and setup problems
- Data loading issues
- Search and query problems
- Configuration errors
- Quick fixes and workarounds

**Best for:** New users, general problems, first-time setup issues

---

### 🚀 [Performance Issues](./performance-issues.md)

Comprehensive guide for diagnosing and resolving performance problems.

**What's covered:**

- Slow data loading optimization
- Search performance tuning
- Memory usage optimization
- CPU and resource management
- Network performance issues
- Advanced optimization strategies

**Best for:** Large datasets, production environments, performance optimization

---

### 🔌 [Connection Problems](./connection-problems.md)

Detailed solutions for connectivity and network-related issues.

**What's covered:**

- QDrant instance connectivity
- API authentication problems
- Network configuration issues
- Firewall and proxy problems
- SSL/TLS certificate issues
- Advanced connection troubleshooting

**Best for:** Network issues, authentication problems, enterprise environments

---

### 📖 [Error Messages Reference](./error-messages-reference.md)

Comprehensive reference for all error messages with exact solutions.

**What's covered:**

- Complete error message catalog
- Detailed explanations and causes
- Step-by-step solutions
- Error codes and exit codes
- Prevention strategies

**Best for:** Specific error messages, debugging, development

## 🚨 Emergency Quick Fixes

### When Everything Fails

```bash
# 1. Check basic configuration
qdrant-loader config --workspace .

# 2. Validate project configuration
qdrant-loader config --workspace .

# 3. Check system resources
free -h
df -h
ps aux | grep qdrant-loader

# 4. Reinitialize collection (WARNING: This will delete existing data)
qdrant-loader init --workspace . --force
```

### Critical System Recovery

```bash
# Test network connectivity
ping 8.8.8.8
curl -v https://api.openai.com/v1/models

# Test QDrant connectivity
curl -v "$QDRANT_URL/health"

# Check environment variables
env | grep -E "(QDRANT|OPENAI|CONFLUENCE|JIRA)"

# Verify workspace structure
ls -la config.yaml .env
```

## 🔍 Diagnostic Tools

### Built-in Diagnostics

```bash
# Check current configuration
qdrant-loader config --workspace .

# List all projects
qdrant-loader config --workspace .

# Check project status
qdrant-loader config --workspace .

# Validate configuration
qdrant-loader config --workspace .

# Test with debug logging
qdrant-loader config --workspace . --log-level DEBUG
```

### Manual Diagnostics

```bash
# Check system resources
htop
iostat -x 1
free -h
df -h

# Network diagnostics
ping your-qdrant-instance.com
traceroute your-qdrant-instance.com
nslookup your-qdrant-instance.com

# Service status
systemctl status qdrant  # If using systemd
docker ps | grep qdrant  # If using Docker
```

## 📊 Problem Categories

### By Frequency (Most Common First)

1. **Configuration Issues** (40%)
   - Environment variables not set
   - Invalid YAML syntax
   - Missing required fields
   - → [Error Messages Reference](./error-messages-reference.md#configuration-errors)

2. **Connection Problems** (25%)
   - QDrant instance not accessible
   - Authentication failures
   - Network timeouts
   - → [Connection Problems](./connection-problems.md)

3. **Data Loading Issues** (20%)
   - No documents found
   - File processing errors
   - Memory limitations
   - → [Common Issues](./common-issues.md#data-loading-issues)

4. **Performance Problems** (10%)
   - Slow loading or search
   - High resource usage
   - Timeout errors
   - → [Performance Issues](./performance-issues.md)

5. **Other Issues** (5%)
   - File permissions
   - SSL/TLS problems
   - Specific error messages
   - → [Error Messages Reference](./error-messages-reference.md)

### By User Type

#### **New Users**

- Start with [Common Issues](./common-issues.md)
- Focus on installation and basic setup
- Use quick fixes and simple solutions

#### **Developers**

- Check [Error Messages Reference](./error-messages-reference.md)
- Use diagnostic tools and detailed logging
- Implement error handling and monitoring

#### **System Administrators**

- Review [Performance Issues](./performance-issues.md)
- Focus on [Connection Problems](./connection-problems.md)
- Implement monitoring and alerting

#### **Enterprise Users**

- Emphasize [Connection Problems](./connection-problems.md) for proxy/firewall issues
- Review [Performance Issues](./performance-issues.md) for optimization
- Implement comprehensive monitoring

## 🛠️ Troubleshooting Methodology

### Step-by-Step Approach

1. **Identify the Problem**
   - What exactly is failing?
   - When did it start failing?
   - What changed recently?

2. **Gather Information**
   - Check error messages
   - Review logs
   - Test basic connectivity

3. **Apply Solutions**
   - Start with simple fixes
   - Test after each change
   - Document what works

4. **Verify Resolution**
   - Test the original use case
   - Monitor for recurrence
   - Update documentation

### Diagnostic Commands

```bash
# Basic configuration check
qdrant-loader config --workspace .

# Project validation
qdrant-loader config --workspace .

# Project status check
qdrant-loader config --workspace .

# Debug mode for detailed logging
qdrant-loader ingest --workspace . --log-level DEBUG
```

## 📈 Monitoring and Prevention

### Proactive Monitoring

```bash
# Regular configuration validation
qdrant-loader config --workspace .

# Check project status regularly
qdrant-loader config --workspace .

# Monitor system resources
watch -n 30 'free -h && df -h'
```

### Prevention Strategies

1. **Regular Health Checks**

   ```bash
   # Daily configuration validation script
   qdrant-loader config --workspace . >> daily-health.log 2>&1
   ```

2. **Configuration Validation**

   ```bash
   # Validate before deployment
   qdrant-loader config --workspace .
   ```

3. **System Monitoring**

   ```bash
   # Monitor system resources
   free -h
   df -h
   ps aux | grep qdrant-loader
   ```

4. **Backup Strategy**

   ```bash
   # Backup configuration files
   cp config.yaml config.yaml.backup
   cp .env .env.backup
   ```

## 🔗 Getting Additional Help

### Community Resources

- **GitHub Issues**: [Report bugs and get help](https://github.com/martin-papy/qdrant-loader/issues)
- **Discussions**: [Community Q&A and tips](https://github.com/martin-papy/qdrant-loader/discussions)
- **Documentation**: [Complete documentation](../../)

### Professional Support

- **Enterprise Support**: Contact your support representative
- **Consulting Services**: Professional implementation assistance
- **Training**: Workshops and training sessions

### Before Asking for Help

1. **Check this troubleshooting guide** - Most issues are covered here
2. **Search existing issues** - Your problem might already be solved
3. **Gather diagnostic information**:

   ```bash
   # Collect configuration and status information
   qdrant-loader config --workspace . > diagnostics.txt
   qdrant-loader config --workspace . >> diagnostics.txt
   qdrant-loader config --workspace . >> diagnostics.txt
   qdrant-loader config --workspace . >> diagnostics.txt 2>&1
   ```

4. **Provide clear details**:
   - Exact error messages
   - Steps to reproduce
   - System information
   - Configuration (sanitized)

## 📋 Troubleshooting Checklist

### Pre-Troubleshooting Checklist

- [ ] Read the error message carefully
- [ ] Check if QDrant instance is running
- [ ] Verify environment variables are set
- [ ] Test basic network connectivity
- [ ] Check available system resources
- [ ] Review recent configuration changes

### Post-Solution Checklist

- [ ] Verify the issue is completely resolved
- [ ] Test related functionality
- [ ] Document the solution for future reference
- [ ] Update monitoring if needed
- [ ] Share solution with team if applicable

## 🎯 Quick Reference Cards

### Connection Issues Quick Card

```bash
# Test QDrant connection
curl -v "$QDRANT_URL/health"

# Test LLM API
curl -H "Authorization: Bearer $LLM_API_KEY" "https://api.openai.com/v1/models"

# Check environment variables
env | grep -E "(QDRANT|OPENAI|CONFLUENCE|JIRA)"

# Test configuration
qdrant-loader config --workspace .
```

### Performance Issues Quick Card

```bash
# Check system resources
free -h
df -h
top

# Monitor QDrant Loader process
ps aux | grep qdrant-loader

# Check project status
qdrant-loader config --workspace .

# Use debug logging for performance analysis
qdrant-loader ingest --workspace . --log-level DEBUG --profile
```

### Data Loading Quick Card

```bash
# Check source accessibility
ls -la /path/to/docs

# Validate configuration
qdrant-loader config --workspace .

# Check project configuration
qdrant-loader config --workspace .

# Load with verbose output
qdrant-loader ingest --workspace . --log-level DEBUG
```

### Configuration Issues Quick Card

```bash
# Display current configuration
qdrant-loader config --workspace .

# Validate all projects
qdrant-loader config --workspace .

# List configured projects
qdrant-loader config --workspace .

# Check specific project
qdrant-loader config --workspace . --project-id PROJECT_ID
```

---

**Need immediate help?** Start with the [Common Issues Guide](./common-issues.md) for quick solutions to the most frequent problems.

**Got a specific error?** Jump directly to the [Error Messages Reference](./error-messages-reference.md) for detailed explanations and solutions.

**Performance problems?** Check the [Performance Issues Guide](./performance-issues.md) for optimization strategies.

**Connection troubles?** See the [Connection Problems Guide](./connection-problems.md) for network and authentication solutions.
