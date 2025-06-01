# Security Considerations

This guide covers security best practices, configuration options, and considerations for deploying QDrant Loader in production environments. Security is critical when handling sensitive documents and API keys.

## 🎯 Overview

QDrant Loader handles sensitive data including API keys, documents, and search queries. Proper security configuration protects your data, credentials, and infrastructure from unauthorized access and potential threats.

### Security Areas

```
🔐 Credential Management - API keys, tokens, certificates
🌐 Network Security     - TLS, proxies, firewalls, VPNs
🛡️ Access Control      - Authentication, authorization, RBAC
📊 Data Protection     - Encryption, anonymization, retention
🔍 Audit & Monitoring  - Logging, alerting, compliance
🚨 Threat Protection   - Rate limiting, input validation
```

## 🔐 Credential Management

### API Key Security

```yaml
# qdrant-loader.yaml - Secure credential management
security:
  credentials:
    # Credential storage backend
    storage: "keyring"  # environment, file, keyring, vault
    
    # Encryption settings
    encryption:
      enabled: true
      algorithm: "AES-256-GCM"
      key_derivation: "PBKDF2"
      iterations: 100000
    
    # Key rotation
    rotation:
      enabled: true
      interval: 2592000  # 30 days
      auto_rotate: false  # Manual rotation for production
    
    # Credential validation
    validation:
      enabled: true
      check_interval: 3600  # 1 hour
      fail_on_invalid: true

# Secure credential configuration
credentials:
  openai:
    # Use environment variable (recommended)
    api_key: "${OPENAI_API_KEY}"
    
    # Validate key format
    validation:
      format: "sk-[a-zA-Z0-9]{48}"
      test_endpoint: true
  
  qdrant:
    # QDrant Cloud API key
    api_key: "${QDRANT_API_KEY}"
    
    # Connection security
    tls:
      enabled: true
      verify_certificates: true
      min_version: "TLSv1.2"
  
  confluence:
    # Use API tokens, not passwords
    api_token: "${CONFLUENCE_API_TOKEN}"
    
    # Token permissions validation
    validation:
      required_permissions:
        - "read"
        - "search"
  
  jira:
    api_token: "${JIRA_API_TOKEN}"
    
    # Scope validation
    validation:
      required_scopes:
        - "read:jira-work"
        - "read:jira-user"

# Environment variables for secure credential management
# OPENAI_API_KEY=sk-your-secure-openai-key
# QDRANT_API_KEY=your-secure-qdrant-key
# CONFLUENCE_API_TOKEN=your-secure-confluence-token
# JIRA_API_TOKEN=your-secure-jira-token
```

### Credential Storage Options

#### Environment Variables (Recommended)

```bash
# .env - Secure environment file (chmod 600)
# Never commit this file to version control

# OpenAI API Key
OPENAI_API_KEY=sk-your-openai-api-key-here

# QDrant Configuration
QDRANT_URL=https://your-qdrant-cluster.qdrant.io
QDRANT_API_KEY=your-qdrant-api-key

# Atlassian Credentials
CONFLUENCE_BASE_URL=https://company.atlassian.net
CONFLUENCE_USERNAME=service-account@company.com
CONFLUENCE_API_TOKEN=your-confluence-api-token

JIRA_BASE_URL=https://company.atlassian.net
JIRA_USERNAME=service-account@company.com
JIRA_API_TOKEN=your-jira-api-token

# Git Credentials
GIT_USERNAME=service-account
GIT_TOKEN=your-git-personal-access-token

# Security settings
QDRANT_LOADER_TLS_VERIFY=true
QDRANT_LOADER_LOG_LEVEL=INFO
```

#### System Keyring Integration

```yaml
# qdrant-loader.yaml - Keyring integration
security:
  credentials:
    storage: "keyring"
    
    keyring:
      # Keyring backend
      backend: "system"  # system, file, memory
      
      # Service name for keyring entries
      service_name: "qdrant-loader"
      
      # Encryption for file-based keyring
      encryption:
        enabled: true
        password_prompt: true

# Store credentials in keyring
# qdrant-loader keyring set openai_api_key
# qdrant-loader keyring set qdrant_api_key
# qdrant-loader keyring set confluence_api_token
```

#### HashiCorp Vault Integration

```yaml
# qdrant-loader.yaml - Vault integration
security:
  credentials:
    storage: "vault"
    
    vault:
      # Vault server URL
      url: "https://vault.company.com"
      
      # Authentication method
      auth_method: "token"  # token, userpass, ldap, aws, gcp
      
      # Token authentication
      token: "${VAULT_TOKEN}"
      
      # Secret paths
      secret_paths:
        openai_api_key: "secret/qdrant-loader/openai"
        qdrant_api_key: "secret/qdrant-loader/qdrant"
        confluence_api_token: "secret/qdrant-loader/confluence"
      
      # TLS configuration
      tls:
        verify: true
        ca_cert: "/etc/ssl/certs/vault-ca.pem"
      
      # Token renewal
      token_renewal:
        enabled: true
        threshold: 300  # Renew 5 minutes before expiry
```

### API Key Best Practices

```bash
#!/bin/bash
# secure-setup.sh - Secure credential setup script

# Set secure file permissions
chmod 600 .env
chmod 600 qdrant-loader.yaml

# Validate API key formats
validate_openai_key() {
    if [[ ! $OPENAI_API_KEY =~ ^sk-[a-zA-Z0-9]{48}$ ]]; then
        echo "❌ Invalid OpenAI API key format"
        exit 1
    fi
    echo "✅ OpenAI API key format valid"
}

# Test API key functionality
test_api_keys() {
    echo "Testing API key connectivity..."
    
    # Test OpenAI API
    curl -s -H "Authorization: Bearer $OPENAI_API_KEY" \
         https://api.openai.com/v1/models > /dev/null
    if [ $? -eq 0 ]; then
        echo "✅ OpenAI API key working"
    else
        echo "❌ OpenAI API key failed"
        exit 1
    fi
    
    # Test QDrant connection
    qdrant-loader config test
    if [ $? -eq 0 ]; then
        echo "✅ QDrant connection working"
    else
        echo "❌ QDrant connection failed"
        exit 1
    fi
}

# Rotate API keys (manual process)
rotate_api_keys() {
    echo "🔄 API Key Rotation Checklist:"
    echo "1. Generate new OpenAI API key"
    echo "2. Generate new QDrant API key (if using QDrant Cloud)"
    echo "3. Generate new Confluence API token"
    echo "4. Generate new JIRA API token"
    echo "5. Update environment variables"
    echo "6. Test new keys"
    echo "7. Revoke old keys"
}

# Run validations
validate_openai_key
test_api_keys
```

## 🌐 Network Security

### TLS/SSL Configuration

```yaml
# qdrant-loader.yaml - TLS/SSL security
security:
  tls:
    # Global TLS settings
    enabled: true
    
    # Minimum TLS version
    min_version: "TLSv1.2"
    
    # Certificate verification
    verify_certificates: true
    
    # Custom CA bundle
    ca_bundle: "/etc/ssl/certs/ca-certificates.crt"
    
    # Client certificates
    client_cert:
      enabled: false
      cert_file: "/etc/ssl/certs/client.pem"
      key_file: "/etc/ssl/private/client-key.pem"
    
    # Cipher suites
    cipher_suites:
      - "ECDHE-RSA-AES256-GCM-SHA384"
      - "ECDHE-RSA-AES128-GCM-SHA256"
      - "ECDHE-RSA-AES256-SHA384"
    
    # HSTS (HTTP Strict Transport Security)
    hsts:
      enabled: true
      max_age: 31536000  # 1 year
      include_subdomains: true

# Service-specific TLS configuration
services:
  qdrant:
    tls:
      verify: true
      ca_bundle: "/etc/ssl/certs/qdrant-ca.pem"
  
  openai:
    tls:
      verify: true
      # Use system CA bundle
  
  confluence:
    tls:
      verify: true
      # Custom certificate for self-hosted
      ca_bundle: "/etc/ssl/certs/confluence-ca.pem"
  
  jira:
    tls:
      verify: true
      ca_bundle: "/etc/ssl/certs/jira-ca.pem"

# Environment variables for TLS
# QDRANT_LOADER_TLS_VERIFY=true
# QDRANT_LOADER_TLS_MIN_VERSION=TLSv1.2
# QDRANT_LOADER_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
```

### Proxy and Firewall Configuration

```yaml
security:
  network:
    # Proxy configuration
    proxy:
      # HTTP proxy
      http: "http://proxy.company.com:8080"
      
      # HTTPS proxy
      https: "https://proxy.company.com:8080"
      
      # No proxy for internal services
      no_proxy:
        - "localhost"
        - "127.0.0.1"
        - "*.internal.company.com"
        - "10.0.0.0/8"
        - "192.168.0.0/16"
      
      # Proxy authentication
      auth:
        username: "${PROXY_USERNAME}"
        password: "${PROXY_PASSWORD}"
      
      # Proxy SSL verification
      verify_ssl: true
    
    # Firewall rules (documentation)
    firewall:
      outbound_rules:
        # OpenAI API
        - destination: "api.openai.com"
          port: 443
          protocol: "HTTPS"
        
        # QDrant Cloud
        - destination: "*.qdrant.io"
          port: 443
          protocol: "HTTPS"
        
        # Atlassian Cloud
        - destination: "*.atlassian.net"
          port: 443
          protocol: "HTTPS"
        
        # GitHub
        - destination: "github.com"
          port: 443
          protocol: "HTTPS"
        
        # GitLab
        - destination: "gitlab.com"
          port: 443
          protocol: "HTTPS"
      
      inbound_rules:
        # MCP Server (if exposed)
        - source: "internal_network"
          port: 8080
          protocol: "HTTP"
    
    # Rate limiting
    rate_limiting:
      enabled: true
      
      # Global rate limits
      global:
        requests_per_minute: 1000
        burst_capacity: 100
      
      # Per-service rate limits
      services:
        openai:
          requests_per_minute: 60
          tokens_per_minute: 150000
        
        confluence:
          requests_per_minute: 100
        
        jira:
          requests_per_minute: 100
        
        git:
          requests_per_minute: 60
    
    # IP allowlisting
    ip_allowlist:
      enabled: false
      
      # Allowed IP ranges
      allowed_ranges:
        - "10.0.0.0/8"
        - "192.168.0.0/16"
        - "172.16.0.0/12"
      
      # Blocked IP ranges
      blocked_ranges:
        - "0.0.0.0/0"  # Block all by default
```

## 🛡️ Access Control

### Authentication and Authorization

```yaml
# qdrant-loader.yaml - Access control
security:
  access_control:
    # Enable access control
    enabled: true
    
    # Authentication methods
    authentication:
      # API key authentication
      api_key:
        enabled: true
        header_name: "X-API-Key"
        key: "${MCP_SERVER_API_KEY}"
      
      # JWT authentication
      jwt:
        enabled: false
        secret: "${JWT_SECRET}"
        algorithm: "HS256"
        expiry: 3600  # 1 hour
      
      # OAuth 2.0
      oauth2:
        enabled: false
        provider: "company-sso"
        client_id: "${OAUTH_CLIENT_ID}"
        client_secret: "${OAUTH_CLIENT_SECRET}"
        scopes: ["read", "search"]
    
    # Authorization
    authorization:
      # Role-based access control
      rbac:
        enabled: true
        
        # Role definitions
        roles:
          admin:
            permissions: ["*"]
            collections: ["*"]
          
          user:
            permissions: ["read", "search"]
            collections: ["public_*", "team_*"]
          
          readonly:
            permissions: ["read"]
            collections: ["public_*"]
      
      # Collection-level permissions
      collections:
        "public_docs":
          read: ["*"]
          write: ["admin", "editor"]
        
        "private_docs":
          read: ["admin", "user"]
          write: ["admin"]
        
        "team_docs":
          read: ["team_member"]
          write: ["team_lead"]
    
    # Session management
    sessions:
      # Session timeout
      timeout: 3600  # 1 hour
      
      # Session storage
      storage: "memory"  # memory, redis, database
      
      # Session security
      security:
        secure_cookies: true
        http_only: true
        same_site: "strict"

# User management
users:
  # User database
  database: "file"  # file, ldap, database
  
  # File-based user database
  file:
    path: "/etc/qdrant-loader/users.yaml"
    encryption: true
  
  # LDAP integration
  ldap:
    server: "ldap://ldap.company.com"
    base_dn: "ou=users,dc=company,dc=com"
    bind_dn: "cn=service,ou=services,dc=company,dc=com"
    bind_password: "${LDAP_PASSWORD}"
    
    # User attributes
    attributes:
      username: "uid"
      email: "mail"
      groups: "memberOf"
    
    # Group mapping
    group_mapping:
      "cn=admins,ou=groups,dc=company,dc=com": "admin"
      "cn=users,ou=groups,dc=company,dc=com": "user"
```

### MCP Server Security

```yaml
mcp_server:
  security:
    # Server security
    server:
      # Bind address (localhost for security)
      host: "127.0.0.1"
      
      # Port configuration
      port: 8080
      
      # Enable HTTPS
      https:
        enabled: false
        cert_file: "/etc/ssl/certs/mcp-server.pem"
        key_file: "/etc/ssl/private/mcp-server-key.pem"
    
    # Request security
    requests:
      # Maximum request size
      max_size: "10MB"
      
      # Request timeout
      timeout: 30
      
      # Rate limiting per client
      rate_limit:
        requests_per_minute: 60
        burst_capacity: 10
      
      # Input validation
      validation:
        enabled: true
        max_query_length: 1000
        allowed_characters: "alphanumeric_space_punctuation"
    
    # CORS configuration
    cors:
      enabled: true
      
      # Allowed origins
      allowed_origins:
        - "http://localhost:3000"
        - "https://cursor.sh"
        - "https://windsurf.codeium.com"
      
      # Allowed methods
      allowed_methods: ["GET", "POST"]
      
      # Allowed headers
      allowed_headers: ["Content-Type", "Authorization"]
      
      # Credentials support
      allow_credentials: false
    
    # Security headers
    headers:
      # Content Security Policy
      csp: "default-src 'self'; script-src 'none'; object-src 'none';"
      
      # X-Frame-Options
      frame_options: "DENY"
      
      # X-Content-Type-Options
      content_type_options: "nosniff"
      
      # Referrer Policy
      referrer_policy: "strict-origin-when-cross-origin"
```

## 📊 Data Protection

### Data Encryption

```yaml
# qdrant-loader.yaml - Data encryption
security:
  encryption:
    # Encryption at rest
    at_rest:
      enabled: true
      
      # Encryption algorithm
      algorithm: "AES-256-GCM"
      
      # Key management
      key_management:
        provider: "local"  # local, kms, vault
        
        # Local key management
        local:
          key_file: "/etc/qdrant-loader/encryption.key"
          key_rotation: true
          rotation_interval: 2592000  # 30 days
        
        # AWS KMS
        kms:
          region: "us-east-1"
          key_id: "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
        
        # HashiCorp Vault
        vault:
          url: "https://vault.company.com"
          mount_path: "transit"
          key_name: "qdrant-loader"
    
    # Encryption in transit
    in_transit:
      enabled: true
      
      # Force HTTPS
      force_https: true
      
      # TLS configuration
      tls:
        min_version: "TLSv1.2"
        cipher_suites: ["ECDHE-RSA-AES256-GCM-SHA384"]
    
    # Field-level encryption
    field_level:
      enabled: false
      
      # Encrypted fields
      fields:
        - "content"
        - "metadata.sensitive_data"
      
      # Encryption key per field
      per_field_keys: true

# Data anonymization
data_protection:
  anonymization:
    enabled: false
    
    # PII detection
    pii_detection:
      enabled: true
      
      # PII patterns
      patterns:
        email: "\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b"
        phone: "\\b\\d{3}-\\d{3}-\\d{4}\\b"
        ssn: "\\b\\d{3}-\\d{2}-\\d{4}\\b"
        credit_card: "\\b\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}\\b"
    
    # Anonymization methods
    methods:
      redaction: true
      masking: true
      tokenization: false
    
    # Anonymization rules
    rules:
      email:
        method: "masking"
        pattern: "***@***.***"
      
      phone:
        method: "redaction"
        replacement: "[PHONE_REDACTED]"
  
  # Data retention
  retention:
    enabled: true
    
    # Default retention period
    default_period: 2592000  # 30 days
    
    # Collection-specific retention
    collections:
      "logs": 604800  # 7 days
      "temp_data": 86400  # 1 day
      "archive": 31536000  # 1 year
    
    # Automatic cleanup
    auto_cleanup: true
    cleanup_schedule: "daily"
```

### Data Loss Prevention

```yaml
security:
  dlp:
    # Data Loss Prevention
    enabled: true
    
    # Content scanning
    content_scanning:
      enabled: true
      
      # Scan patterns
      patterns:
        # Sensitive data patterns
        api_keys: "sk-[a-zA-Z0-9]{48}"
        aws_keys: "AKIA[0-9A-Z]{16}"
        private_keys: "-----BEGIN PRIVATE KEY-----"
        passwords: "password\\s*[:=]\\s*['\"][^'\"]+['\"]"
      
      # Actions on detection
      actions:
        api_keys: "block"
        aws_keys: "block"
        private_keys: "block"
        passwords: "alert"
    
    # File type restrictions
    file_restrictions:
      # Blocked file types
      blocked_types:
        - ".exe"
        - ".bat"
        - ".sh"
        - ".ps1"
      
      # Maximum file size
      max_file_size: "100MB"
      
      # Virus scanning
      virus_scanning:
        enabled: false
        engine: "clamav"
    
    # Data classification
    classification:
      enabled: true
      
      # Classification levels
      levels:
        public: 0
        internal: 1
        confidential: 2
        restricted: 3
      
      # Auto-classification rules
      rules:
        - pattern: "confidential"
          level: "confidential"
        - pattern: "internal use only"
          level: "internal"
```

## 🔍 Audit and Monitoring

### Security Logging

```yaml
# qdrant-loader.yaml - Security logging
security:
  logging:
    # Security event logging
    security_events:
      enabled: true
      
      # Log level for security events
      level: "INFO"
      
      # Security log file
      file: "/var/log/qdrant-loader/security.log"
      
      # Log format
      format: "json"  # json, text
      
      # Events to log
      events:
        - "authentication_success"
        - "authentication_failure"
        - "authorization_failure"
        - "api_key_usage"
        - "configuration_change"
        - "data_access"
        - "error_events"
    
    # Audit logging
    audit:
      enabled: true
      
      # Audit log file
      file: "/var/log/qdrant-loader/audit.log"
      
      # Audit events
      events:
        - "user_login"
        - "user_logout"
        - "search_query"
        - "document_access"
        - "configuration_change"
        - "admin_action"
      
      # Log retention
      retention: 2592000  # 30 days
      
      # Log rotation
      rotation:
        enabled: true
        max_size: "100MB"
        backup_count: 10
    
    # SIEM integration
    siem:
      enabled: false
      
      # Syslog forwarding
      syslog:
        enabled: false
        server: "siem.company.com"
        port: 514
        protocol: "UDP"
        facility: "local0"
      
      # Splunk forwarding
      splunk:
        enabled: false
        url: "https://splunk.company.com:8088"
        token: "${SPLUNK_TOKEN}"
        index: "qdrant_loader"

# Monitoring and alerting
monitoring:
  security:
    # Security metrics
    metrics:
      enabled: true
      
      # Metrics to track
      track:
        - "failed_authentications"
        - "unauthorized_access_attempts"
        - "api_key_usage"
        - "suspicious_queries"
        - "error_rates"
    
    # Security alerts
    alerts:
      enabled: true
      
      # Alert thresholds
      thresholds:
        failed_auth_rate: 10  # per minute
        unauthorized_access: 5  # per minute
        error_rate: 0.1  # 10%
        suspicious_queries: 5  # per minute
      
      # Alert channels
      channels:
        email:
          enabled: true
          recipients: ["security@company.com"]
        
        slack:
          enabled: true
          webhook: "${SECURITY_SLACK_WEBHOOK}"
        
        pagerduty:
          enabled: false
          integration_key: "${PAGERDUTY_KEY}"
```

### Compliance and Governance

```yaml
security:
  compliance:
    # Compliance frameworks
    frameworks:
      - "SOC2"
      - "GDPR"
      - "HIPAA"
      - "ISO27001"
    
    # GDPR compliance
    gdpr:
      enabled: true
      
      # Data subject rights
      data_subject_rights:
        # Right to access
        access: true
        
        # Right to rectification
        rectification: true
        
        # Right to erasure
        erasure: true
        
        # Right to portability
        portability: true
      
      # Consent management
      consent:
        required: true
        granular: true
        withdrawable: true
      
      # Data processing records
      processing_records:
        enabled: true
        file: "/var/log/qdrant-loader/gdpr.log"
    
    # Data governance
    governance:
      # Data classification
      classification:
        enabled: true
        default_level: "internal"
      
      # Data lineage
      lineage:
        enabled: true
        track_sources: true
        track_transformations: true
      
      # Data quality
      quality:
        enabled: true
        validation_rules: true
        quality_metrics: true
```

## 🚨 Threat Protection

### Input Validation and Sanitization

```yaml
security:
  input_validation:
    # Query validation
    queries:
      # Maximum query length
      max_length: 1000
      
      # Allowed characters
      allowed_chars: "alphanumeric_space_punctuation"
      
      # Blocked patterns
      blocked_patterns:
        - "script"
        - "javascript"
        - "eval"
        - "exec"
        - "system"
      
      # SQL injection protection
      sql_injection:
        enabled: true
        patterns:
          - "union\\s+select"
          - "drop\\s+table"
          - "delete\\s+from"
          - "insert\\s+into"
    
    # File upload validation
    file_uploads:
      # Maximum file size
      max_size: "100MB"
      
      # Allowed file types
      allowed_types:
        - "text/plain"
        - "text/markdown"
        - "application/pdf"
        - "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
      
      # File content scanning
      content_scanning:
        enabled: true
        scan_for_malware: true
        scan_for_secrets: true
    
    # API parameter validation
    api_parameters:
      # Parameter length limits
      max_param_length: 1000
      
      # Parameter count limits
      max_param_count: 50
      
      # Type validation
      strict_typing: true

# Rate limiting and DDoS protection
protection:
  rate_limiting:
    # Global rate limits
    global:
      enabled: true
      requests_per_minute: 1000
      burst_capacity: 100
    
    # Per-IP rate limits
    per_ip:
      enabled: true
      requests_per_minute: 60
      burst_capacity: 10
      
      # IP-based blocking
      auto_block:
        enabled: true
        threshold: 100  # requests per minute
        block_duration: 3600  # 1 hour
    
    # Per-user rate limits
    per_user:
      enabled: true
      requests_per_minute: 120
      burst_capacity: 20
  
  # DDoS protection
  ddos:
    enabled: true
    
    # Traffic analysis
    analysis:
      enabled: true
      window_size: 300  # 5 minutes
      threshold_multiplier: 5
    
    # Mitigation strategies
    mitigation:
      # Challenge-response
      challenge_response: true
      
      # Traffic shaping
      traffic_shaping: true
      
      # Blackholing
      blackhole: false
```

## 🔧 Security Configuration Examples

### Production Security Configuration

```yaml
# qdrant-loader-secure.yaml - Production security configuration
security:
  # Credential management
  credentials:
    storage: "vault"
    encryption:
      enabled: true
      algorithm: "AES-256-GCM"
    rotation:
      enabled: true
      interval: 2592000  # 30 days

  # Network security
  tls:
    enabled: true
    min_version: "TLSv1.2"
    verify_certificates: true
  
  # Access control
  access_control:
    enabled: true
    authentication:
      api_key:
        enabled: true
    authorization:
      rbac:
        enabled: true

  # Data protection
  encryption:
    at_rest:
      enabled: true
      algorithm: "AES-256-GCM"
    in_transit:
      enabled: true
      force_https: true

  # Logging and monitoring
  logging:
    security_events:
      enabled: true
      level: "INFO"
    audit:
      enabled: true
      retention: 2592000  # 30 days

  # Threat protection
  input_validation:
    queries:
      max_length: 1000
      blocked_patterns: ["script", "eval", "exec"]
  
  rate_limiting:
    global:
      enabled: true
      requests_per_minute: 1000
    per_ip:
      enabled: true
      requests_per_minute: 60

# MCP Server security
mcp_server:
  security:
    server:
      host: "127.0.0.1"  # Localhost only
      port: 8080
    
    requests:
      max_size: "10MB"
      timeout: 30
      rate_limit:
        requests_per_minute: 60
    
    cors:
      enabled: true
      allowed_origins: ["https://cursor.sh"]
```

### Development Security Configuration

```yaml
# qdrant-loader-dev.yaml - Development security configuration
security:
  # Relaxed for development
  credentials:
    storage: "environment"
    validation:
      enabled: true

  # TLS optional for local development
  tls:
    enabled: false  # Local development only
    verify_certificates: false

  # Basic access control
  access_control:
    enabled: false  # Disabled for development

  # Minimal encryption
  encryption:
    at_rest:
      enabled: false
    in_transit:
      enabled: false

  # Development logging
  logging:
    security_events:
      enabled: true
      level: "DEBUG"
    audit:
      enabled: false

  # Relaxed validation
  input_validation:
    queries:
      max_length: 5000  # Longer for testing
  
  rate_limiting:
    global:
      enabled: false  # Disabled for development

# MCP Server development settings
mcp_server:
  security:
    server:
      host: "0.0.0.0"  # Allow external connections
      port: 8080
    
    cors:
      enabled: true
      allowed_origins: ["*"]  # Allow all origins for development
```

## 🔗 Related Documentation

- **[Environment Variables Reference](./environment-variables.md)** - Secure environment variable management
- **[Configuration File Reference](./config-file-reference.md)** - Configuration file security
- **[Advanced Settings](./advanced-settings.md)** - Performance and security optimization
- **[Getting Help](../troubleshooting/getting-help.md)** - Security incident reporting

## 📋 Security Checklist

### Pre-Deployment Security

- [ ] **API keys** stored securely (environment variables or keyring)
- [ ] **TLS/SSL** enabled for all external connections
- [ ] **Certificate verification** enabled
- [ ] **Strong passwords** used for all accounts
- [ ] **Multi-factor authentication** enabled where possible
- [ ] **Network access** restricted (firewalls, VPNs)
- [ ] **File permissions** set correctly (600 for config files)
- [ ] **Secrets** excluded from version control

### Runtime Security

- [ ] **Access control** configured appropriately
- [ ] **Rate limiting** enabled
- [ ] **Input validation** configured
- [ ] **Security logging** enabled
- [ ] **Monitoring** and alerting configured
- [ ] **Regular security updates** applied
- [ ] **Backup and recovery** procedures tested
- [ ] **Incident response** plan documented

### Compliance and Governance

- [ ] **Data classification** implemented
- [ ] **Retention policies** configured
- [ ] **Audit logging** enabled
- [ ] **Compliance requirements** met
- [ ] **Privacy policies** implemented
- [ ] **Data subject rights** supported
- [ ] **Security training** completed
- [ ] **Regular security assessments** conducted

---

**Security configuration complete!** 🔒

Your QDrant Loader deployment is now secured with industry best practices. Regular security reviews and updates ensure ongoing protection of your data and infrastructure.
