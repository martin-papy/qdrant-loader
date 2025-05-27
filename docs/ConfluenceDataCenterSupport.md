# Confluence Data Center Support

This document explains how to configure QDrant Loader to work with both Confluence Cloud and Confluence Data Center/Server deployments.

## Overview

QDrant Loader now supports both Confluence Cloud and Confluence Data Center/Server deployments with secure authentication methods:

- **Confluence Cloud**: Uses API tokens with email-based basic authentication
- **Confluence Data Center/Server**: Uses Personal Access Tokens (PATs) for secure authentication

## Configuration

### Confluence Cloud

For Confluence Cloud instances (typically `*.atlassian.net`):

```yaml
confluence:
  my-cloud-space:
    base_url: "https://mycompany.atlassian.net/wiki"
    deployment_type: "cloud"
    space_key: "MYSPACE"
    content_types:
      - "page"
      - "blogpost"
    token: "${CONFLUENCE_TOKEN}"  # API token from id.atlassian.com
    email: "${CONFLUENCE_EMAIL}"  # Your Atlassian account email
```

**Environment Variables:**

```bash
CONFLUENCE_TOKEN=your_api_token_from_atlassian_account
CONFLUENCE_EMAIL=your.email@company.com
```

**How to get Cloud API Token:**

1. Go to <https://id.atlassian.com/manage/api-tokens>
2. Click "Create API token"
3. Give it a label and create
4. Copy the token (you won't see it again)

### Confluence Data Center with Personal Access Token (Recommended)

For Confluence Data Center/Server with Personal Access Tokens:

```yaml
confluence:
  my-datacenter-space:
    base_url: "https://confluence.mycompany.com"
    deployment_type: "datacenter"
    space_key: "MYSPACE"
    content_types:
      - "page"
      - "blogpost"
    token: "${CONFLUENCE_PAT}"  # Personal Access Token from Confluence
```

**Environment Variables:**

```bash
CONFLUENCE_PAT=your_personal_access_token
```

**How to get Data Center Personal Access Token:**

1. Log into your Confluence Data Center instance
2. Go to your Profile → Settings → Personal Access Tokens
3. Click "Create token"
4. Set name and optional expiry
5. Copy the token (you won't see it again)

## Deployment Type Detection

The `deployment_type` field can be set to:

- `"cloud"` - For Confluence Cloud instances
- `"datacenter"` - For Confluence Data Center instances
- `"server"` - Legacy, treated same as datacenter

If not specified, it defaults to `"cloud"`.

## Authentication Methods Summary

| Deployment Type | Authentication Method | Required Fields | Environment Variables |
|----------------|----------------------|----------------|----------------------|
| Cloud | API Token + Email | `token`, `email` | `CONFLUENCE_TOKEN`, `CONFLUENCE_EMAIL` |
| Data Center | Personal Access Token | `token` | `CONFLUENCE_TOKEN` or `CONFLUENCE_PAT` |

## Troubleshooting

### Common Issues

1. **401 Unauthorized with Data Center**
   - Check if you're using the correct authentication method
   - For PAT: Ensure the token is valid and not expired

2. **"Basic authentication with passwords is deprecated" error**
   - This typically means you're trying to use Cloud authentication against a Data Center instance
   - Set `deployment_type: "datacenter"` and use a Personal Access Token

3. **Token not found errors**
   - Ensure environment variables are set correctly
   - Check that the token hasn't expired (Data Center PATs can have expiry dates)

### Debugging

Enable debug logging to see authentication details:

```bash
qdrant-loader ingest --log-level DEBUG --config config.yaml
```

This will show:

- Which authentication method is being used
- Whether auth headers or session auth is configured
- Request details for failed authentication

## Migration from Cloud to Data Center

If you're migrating from Cloud to Data Center:

1. Update the `base_url` to your Data Center instance
2. Set `deployment_type: "datacenter"`
3. Create a Personal Access Token and use `token` field
4. Update environment variables accordingly

## Security Considerations

- **Personal Access Tokens** are secure and can be revoked individually
- **Tokens can expire** - check your Data Center PAT settings for expiry dates
- **Least privilege** - ensure tokens/users only have access to required spaces
- **Environment variables** - never commit tokens to version control

## API Differences

The connector automatically handles API differences between Cloud and Data Center:

- **Authentication headers**: Bearer tokens for Data Center PATs, Basic auth for others
- **API endpoints**: Uses the same REST API endpoints for both deployments
- **Content format**: Handles both Cloud and Data Center content formats

## Example Complete Configuration

```yaml
# config.yaml
global:
  chunking:
    chunk_size: 500
    chunk_overlap: 50
  embedding:
    model: "text-embedding-3-small"
    batch_size: 100
  state_management:
    database_path: "state.db"

sources:
  confluence:
    # Cloud instance
    marketing-cloud:
      base_url: "https://mycompany.atlassian.net/wiki"
      deployment_type: "cloud"
      space_key: "MARKETING"
      token: "${CONFLUENCE_CLOUD_TOKEN}"
      email: "${CONFLUENCE_CLOUD_EMAIL}"
    
    # Data Center with PAT
    engineering-dc:
      base_url: "https://confluence.internal.company.com"
      deployment_type: "datacenter"
      space_key: "ENG"
      token: "${CONFLUENCE_DC_PAT}"
    

```

```bash
# .env
CONFLUENCE_CLOUD_TOKEN=ATATT3xFfGF0...
CONFLUENCE_CLOUD_EMAIL=user@company.com
CONFLUENCE_DC_PAT=NjY4NjY4NjY4...

```
