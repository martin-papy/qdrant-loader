# JIRA Data Center Support

This document explains how to configure QDrant Loader to work with both JIRA Cloud and JIRA Data Center/Server deployments.

## Overview

QDrant Loader now supports both JIRA Cloud and JIRA Data Center/Server deployments with secure authentication methods:

- **JIRA Cloud**: Uses API tokens with email-based basic authentication
- **JIRA Data Center/Server**: Uses Personal Access Tokens (PATs) for secure authentication

## Configuration

### JIRA Cloud

For JIRA Cloud instances (typically `*.atlassian.net`):

```yaml
jira:
  my-cloud-project:
    base_url: "https://mycompany.atlassian.net"
    deployment_type: "cloud"
    project_key: "MYPROJ"
    token: "${JIRA_TOKEN}"  # API token from id.atlassian.com
    email: "${JIRA_EMAIL}"  # Your Atlassian account email
    page_size: 50
    requests_per_minute: 60
```

**Environment Variables:**

```bash
JIRA_TOKEN=your_api_token_from_atlassian_account
JIRA_EMAIL=your.email@company.com
```

**How to get Cloud API Token:**

1. Go to <https://id.atlassian.com/manage/api-tokens>
2. Click "Create API token"
3. Give it a label and create
4. Copy the token (you won't see it again)

### JIRA Data Center with Personal Access Token (Recommended)

For JIRA Data Center/Server with Personal Access Tokens:

```yaml
jira:
  my-datacenter-project:
    base_url: "https://jira.mycompany.com"
    deployment_type: "datacenter"
    project_key: "MYPROJ"
    token: "${JIRA_PAT}"  # Personal Access Token from JIRA
    page_size: 50
    requests_per_minute: 60
```

**Environment Variables:**

```bash
JIRA_PAT=your_personal_access_token
```

**How to get Data Center Personal Access Token:**

1. Log into your JIRA Data Center instance
2. Go to your Profile → Settings → Personal Access Tokens
3. Click "Create token"
4. Set name and optional expiry
5. Copy the token (you won't see it again)

## Deployment Type Detection

The `deployment_type` field can be set to:

- `"cloud"` - For JIRA Cloud instances
- `"datacenter"` - For JIRA Data Center instances
- `"server"` - Legacy, treated same as datacenter

If not specified, it defaults to `"cloud"`. The system can also auto-detect deployment type based on URL patterns (`.atlassian.net` indicates Cloud).

## Authentication Methods Summary

| Deployment Type | Authentication Method | Required Fields | Environment Variables |
|----------------|----------------------|----------------|----------------------|
| Cloud | API Token + Email | `token`, `email` | `JIRA_TOKEN`, `JIRA_EMAIL` |
| Data Center | Personal Access Token | `token` | `JIRA_TOKEN` or `JIRA_PAT` |

## Features Supported

### Issue Processing

- **Complete issue data**: Summary, description, status, priority, labels
- **User information**: Reporter, assignee with proper handling of different user formats
- **Comments**: All issue comments with author and timestamp information
- **Attachments**: Metadata for all issue attachments
- **Relationships**: Parent/child relationships, subtasks, and linked issues
- **Custom fields**: Support for project-specific custom fields

### Data Center Specific Features

- **User field compatibility**: Handles different user identifier formats between Cloud (`accountId`) and Data Center (`name`/`key`)
- **Authentication headers**: Uses Bearer token authentication for secure PAT access
- **API compatibility**: Works with both modern and legacy JIRA Data Center APIs
- **Rate limiting**: Respects Data Center instance rate limits

## Troubleshooting

### Common Issues

1. **401 Unauthorized with Data Center**
   - Check if you're using the correct authentication method
   - For PAT: Ensure the token is valid and not expired
   - Verify the token has appropriate permissions for the project

2. **"User data missing required identifier" error**
   - This typically occurs when user data format differs between deployments
   - The connector automatically handles this by falling back to `name` or `key` fields

3. **Token not found errors**
   - Ensure environment variables are set correctly
   - Check that the token hasn't expired (Data Center PATs can have expiry dates)

4. **Project access denied**
   - Verify the user associated with the PAT has access to the specified project
   - Check project permissions in JIRA administration

### Debugging

Enable debug logging to see authentication details:

```bash
qdrant-loader ingest --source-type jira --log-level DEBUG --config config.yaml
```

This will show:

- Which authentication method is being used (Cloud vs Data Center)
- Whether Bearer token or Basic auth is configured
- Request details for failed authentication
- User parsing information for different deployment types

## Migration from Cloud to Data Center

If you're migrating from Cloud to Data Center:

1. Update the `base_url` to your Data Center instance
2. Set `deployment_type: "datacenter"`
3. Create a Personal Access Token and use `token` field
4. Remove the `email` field (not needed for Data Center)
5. Update environment variables accordingly

## Security Considerations

- **Personal Access Tokens** are secure and can be revoked individually
- **Tokens can expire** - check your Data Center PAT settings for expiry dates
- **Least privilege** - ensure tokens/users only have access to required projects
- **Environment variables** - never commit tokens to version control
- **Project permissions** - verify appropriate read permissions for issue data

## API Differences

The connector automatically handles API differences between Cloud and Data Center:

- **Authentication headers**: Bearer tokens for Data Center PATs, Basic auth for Cloud
- **User data format**: Handles `accountId` (Cloud) vs `name`/`key` (Data Center)
- **API endpoints**: Uses the same REST API v2 endpoints for both deployments
- **Content format**: Handles both Cloud and Data Center response formats

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
  jira:
    # Cloud instance
    support-cloud:
      base_url: "https://mycompany.atlassian.net"
      deployment_type: "cloud"
      project_key: "SUPPORT"
      token: "${JIRA_CLOUD_TOKEN}"
      email: "${JIRA_CLOUD_EMAIL}"
      page_size: 50
      requests_per_minute: 60
    
    # Data Center with PAT
    engineering-dc:
      base_url: "https://jira.internal.company.com"
      deployment_type: "datacenter"
      project_key: "ENG"
      token: "${JIRA_DC_PAT}"
      page_size: 100
      requests_per_minute: 120
```

```bash
# .env
JIRA_CLOUD_TOKEN=ATATT3xFfGF0...
JIRA_CLOUD_EMAIL=user@company.com
JIRA_DC_PAT=NjY4NjY4NjY4...
```

## Performance Considerations

### Data Center Optimizations

- **Higher rate limits**: Data Center instances typically support higher request rates
- **Larger page sizes**: Can often handle larger page sizes for bulk operations
- **Direct network access**: Internal network access may provide better performance
- **Batch processing**: Optimized for processing large numbers of issues

### Recommended Settings

For **JIRA Cloud**:

```yaml
page_size: 50
requests_per_minute: 60
```

For **JIRA Data Center**:

```yaml
page_size: 100
requests_per_minute: 120
```

## Incremental Updates

Both Cloud and Data Center support incremental updates:

- **Change detection**: Tracks last update time for each issue
- **Efficient queries**: Uses JQL to filter issues by update date
- **State management**: Maintains sync state between runs
- **Selective processing**: Only processes changed issues

Example incremental sync:

```bash
# Initial full sync
qdrant-loader ingest --source-type jira

# Subsequent incremental syncs
qdrant-loader ingest --source-type jira  # Automatically detects changes
```
