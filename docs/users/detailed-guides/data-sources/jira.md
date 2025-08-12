# JIRA

Connect QDrant Loader to JIRA to index project tickets, issues, requirements, and project management data. This guide covers setup for both JIRA Cloud and JIRA Data Center.

## 🎯 What Gets Processed

When you connect to JIRA, QDrant Loader can process:

- **Issue content** - Summaries, descriptions, and comments
- **Issue metadata** - Status, priority, assignee, labels, components
- **Attachments** - Files attached to issues (when enabled)
- **Project information** - Project descriptions and metadata

## 🔧 Authentication Setup

### JIRA Cloud

#### API Token (Recommended)

1. **Create an API Token**:
   - Go to [Atlassian Account Settings](https://id.atlassian.com/manage-profile/security/api-tokens)
   - Click "Create API token"
   - Give it a descriptive name like "QDrant Loader"
   - Copy the token

2. **Set environment variables**:

```bash
export JIRA_TOKEN=your_api_token_here
export JIRA_EMAIL=your-email@company.com
```

### JIRA Data Center

#### Personal Access Token

1. **Create a Personal Access Token**:
   - Go to JIRA → Settings → Personal Access Tokens
   - Click "Create token"
   - Set appropriate permissions: `READ` for projects and issues
   - Copy the token

2. **Set environment variables**:

```bash
export JIRA_TOKEN=your_personal_access_token
```

## ⚙️ Configuration

### Basic Configuration

```yaml
global:
  qdrant:
    url: "http://localhost:6333"
    collection_name: "documents"
  openai:
    api_key: "${OPENAI_API_KEY}"

projects:
  my-project:
    sources:
      jira:
        my-jira:
          base_url: "https://your-domain.atlassian.net"
          deployment_type: "cloud"
          project_key: "PROJ"
          token: "${JIRA_TOKEN}"
          email: "${JIRA_EMAIL}"
          download_attachments: true
```

### Advanced Configuration

```yaml
global:
  qdrant:
    url: "http://localhost:6333"
    collection_name: "documents"
  openai:
    api_key: "${OPENAI_API_KEY}"

projects:
  my-project:
    sources:
      jira:
        my-jira:
          base_url: "https://your-domain.atlassian.net"
          deployment_type: "cloud"
          project_key: "PROJ"
          token: "${JIRA_TOKEN}"
          email: "${JIRA_EMAIL}"
          
          # Rate limiting
          requests_per_minute: 60
          page_size: 50
          
          # Attachment handling
          download_attachments: true
          
          # Issue filtering
          issue_types:
            - "Story"
            - "Epic"
            - "Bug"
            - "Task"
          include_statuses:
            - "To Do"
            - "In Progress"
            - "Done"
          
          # File conversion (requires global file_conversion config)
          enable_file_conversion: true
```

### Multiple JIRA Instances

```yaml
global:
  qdrant:
    url: "http://localhost:6333"
    collection_name: "documents"
  openai:
    api_key: "${OPENAI_API_KEY}"

projects:
  my-project:
    sources:
      jira:
        # Production JIRA Cloud
        prod-jira:
          base_url: "https://company.atlassian.net"
          deployment_type: "cloud"
          project_key: "PROD"
          token: "${JIRA_TOKEN}"
          email: "${JIRA_EMAIL}"
        
        # Development JIRA Data Center
        dev-jira:
          base_url: "https://dev-jira.company.com"
          deployment_type: "datacenter"
          project_key: "DEV"
          token: "${DEV_JIRA_TOKEN}"
```

## 🎯 Configuration Options

### Validator Requirements

- `email` + `token` required for `deployment_type: cloud`
- `token` required for `deployment_type: datacenter`
- `requests_per_minute` default: `60`
- `page_size` default: `100`
- Empty `issue_types` / `include_statuses` means all

### Connection Settings

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `base_url` | string | JIRA base URL | Required |
| `deployment_type` | string | Deployment type: "cloud", "datacenter", or "server" | `"cloud"` |
| `project_key` | string | Project key to process | Required |
| `token` | string | API token or Personal Access Token | Required |
| `email` | string | Email (required for Cloud) | Required for Cloud |

### Processing Settings

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `requests_per_minute` | int | Rate limit for API calls | `60` |
| `page_size` | int | Number of issues per API request | `100` |
| `download_attachments` | bool | Download and process issue attachments | `false` |
| `enable_file_conversion` | bool | Enable file conversion for attachments | `false` |

### Issue Filtering

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `issue_types` | list | Issue types to include | All types |
| `include_statuses` | list | Issue statuses to include | All statuses |

## 🚀 Usage Examples

### Software Development Team

```yaml
global:
  qdrant:
    url: "http://localhost:6333"
    collection_name: "dev-docs"
  openai:
    api_key: "${OPENAI_API_KEY}"

projects:
  development:
    sources:
      jira:
        dev-project:
          base_url: "https://company.atlassian.net"
          deployment_type: "cloud"
          project_key: "DEV"
          token: "${JIRA_TOKEN}"
          email: "${JIRA_EMAIL}"
          
          # Focus on active work
          issue_types:
            - "Story"
            - "Epic"
            - "Bug"
            - "Task"
          include_statuses:
            - "To Do"
            - "In Progress"
            - "In Review"
            - "Done"
          
          # Include attachments for documentation
          download_attachments: true
          enable_file_conversion: true
```

### Product Management

```yaml
global:
  qdrant:
    url: "http://localhost:6333"
    collection_name: "product-docs"
  openai:
    api_key: "${OPENAI_API_KEY}"

projects:
  product:
    sources:
      jira:
        product-backlog:
          base_url: "https://company.atlassian.net"
          deployment_type: "cloud"
          project_key: "PROD"
          token: "${JIRA_TOKEN}"
          email: "${JIRA_EMAIL}"
          
          # Focus on planning items
          issue_types:
            - "Epic"
            - "Story"
            - "Initiative"
          
          # Include all content for context
          download_attachments: true
          enable_file_conversion: true
```

### Support Team

```yaml
global:
  qdrant:
    url: "http://localhost:6333"
    collection_name: "support-docs"
  openai:
    api_key: "${OPENAI_API_KEY}"

projects:
  support:
    sources:
      jira:
        support-tickets:
          base_url: "https://company.atlassian.net"
          deployment_type: "cloud"
          project_key: "SUP"
          token: "${JIRA_TOKEN}"
          email: "${JIRA_EMAIL}"
          
          # Support-focused issue types
          issue_types:
            - "Bug"
            - "Support Request"
            - "Incident"
            - "Problem"
          
          # Include customer communications
          download_attachments: true
```

## 🧪 Testing and Validation

### Initialize and Configure

```bash
# Initialize workspace
qdrant-loader init --workspace .

# Configure the project
qdrant-loader config --workspace .
```

### Validate Configuration

```bash
# Validate project configuration
qdrant-loader project --workspace .

# Check project status
qdrant-loader project --workspace .

# List all projects
qdrant-loader project --workspace .
```

### Process JIRA Data

```bash
# Process all configured sources
qdrant-loader ingest --workspace .

# Process specific project
qdrant-loader ingest --workspace . --project my-project

# Process with verbose logging
qdrant-loader ingest --workspace . --log-level debug
```

## 🔧 Troubleshooting

### Common Issues

#### Authentication Failures

**Problem**: `401 Unauthorized` or `403 Forbidden`

**Solutions**:

```bash
# Test API token manually
curl -u "your-email@company.com:your-api-token" \
  "https://your-domain.atlassian.net/rest/api/2/myself"

# Check project permissions
curl -u "your-email@company.com:your-api-token" \
  "https://your-domain.atlassian.net/rest/api/2/project"

# For Data Center, test with Personal Access Token
curl -H "Authorization: Bearer your-token" \
  "https://jira.company.com/rest/api/2/myself"
```

#### Project Access Issues

**Problem**: `Project not found` or `No permission to access project`

**Solutions**:

```bash
# List accessible projects
curl -u "your-email:your-token" \
  "https://your-domain.atlassian.net/rest/api/2/project" | jq '.[].key'

# Check specific project permissions
curl -u "your-email:your-token" \
  "https://your-domain.atlassian.net/rest/api/2/project/PROJ"
```

#### Rate Limiting

**Problem**: `429 Too Many Requests`

**Solutions**:

```yaml
projects:
  my-project:
    sources:
      jira:
        my-jira:
          base_url: "https://company.atlassian.net"
          deployment_type: "cloud"
          project_key: "PROJ"
          token: "${JIRA_TOKEN}"
          email: "${JIRA_EMAIL}"
          
          # Reduce request rate
          requests_per_minute: 30
          page_size: 25
```

#### Large Project Performance

**Problem**: Processing takes too long or times out

**Solutions**:

```yaml
projects:
  my-project:
    sources:
      jira:
        my-jira:
          base_url: "https://company.atlassian.net"
          deployment_type: "cloud"
          project_key: "PROJ"
          token: "${JIRA_TOKEN}"
          email: "${JIRA_EMAIL}"
          
          # Optimize processing
          download_attachments: false
          page_size: 25
          requests_per_minute: 30
          
          # Filter to reduce scope
          issue_types:
            - "Story"
            - "Bug"
          include_statuses:
            - "Open"
            - "In Progress"
```

### Debugging Commands

```bash
# Check JIRA API version
curl -u "email:token" "https://domain.atlassian.net/rest/api/2/serverInfo"

# List issues in a project
curl -u "email:token" \
  "https://domain.atlassian.net/rest/api/2/search?jql=project=PROJ&maxResults=5" | \
  jq '.issues[].key'

# Check issue details
curl -u "email:token" \
  "https://domain.atlassian.net/rest/api/2/issue/PROJ-123"
```

## 📊 Monitoring and Performance

### Check Processing Status

```bash
# Check project status
qdrant-loader project --workspace .

# Check specific project
qdrant-loader project --workspace . --project-id my-project

# List all projects
qdrant-loader project --workspace .
```

### Performance Optimization

Monitor these aspects for JIRA processing:

- **Issues processed per minute** - Processing throughput
- **API request rate** - Requests per second to JIRA
- **Error rate** - Percentage of failed issue requests
- **Attachment download time** - Time to download and process files
- **Memory usage** - Peak memory during processing

## 🔄 Best Practices

### Project Organization

1. **Use descriptive project keys** - Make projects easy to identify
2. **Organize with components** - Use components for categorization
3. **Apply consistent labeling** - Use labels for cross-project categorization
4. **Archive completed projects** - Move old projects to archive status

### Performance Best Practices

1. **Filter issue types** - Process only relevant issue types
2. **Limit attachment processing** - Set `download_attachments: false` for large projects
3. **Use appropriate page sizes** - Balance between API calls and memory usage
4. **Respect rate limits** - Configure `requests_per_minute` appropriately

### Security Considerations

1. **Use API tokens** - Prefer tokens over passwords
2. **Limit token scope** - Grant minimal necessary permissions
3. **Rotate tokens regularly** - Update tokens periodically
4. **Monitor access** - Track which projects are being accessed

### Data Quality

1. **Maintain consistent issue types** - Use standard issue type schemes
2. **Use structured descriptions** - Follow description templates
3. **Regular data cleanup** - Archive or close old issues

## 📚 Related Documentation

- **[File Conversion](../file-conversion/)** - Processing JIRA attachments
- **[Configuration Reference](../../configuration/)** - Complete configuration options
- **[Troubleshooting](../../troubleshooting/)** - Common issues and solutions
- **[MCP Server](../mcp-server/)** - Using processed JIRA content with AI tools

---

**Ready to connect your JIRA instance?** Start with the basic configuration above and customize based on your project structure and workflow needs.
