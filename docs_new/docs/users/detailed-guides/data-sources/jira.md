# JIRA

Connect QDrant Loader to JIRA to index project tickets, issues, requirements, and project management data. This guide covers setup for both JIRA Cloud and JIRA Data Center.

## 🎯 What Gets Processed

When you connect to JIRA, QDrant Loader can process:

- **Issue content** - Summaries, descriptions, and comments
- **Issue metadata** - Status, priority, assignee, labels, components
- **Custom fields** - Project-specific fields and values
- **Attachments** - Files attached to issues
- **Issue history** - Status changes and field updates
- **Project information** - Project descriptions and metadata
- **Sprint data** - Agile sprint information and planning

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
   export JIRA_URL=https://your-domain.atlassian.net
   export JIRA_EMAIL=your-email@company.com
   export JIRA_TOKEN=your_api_token_here
   ```

#### OAuth 2.0 (Enterprise)

For enterprise setups with OAuth:

```bash
export JIRA_URL=https://your-domain.atlassian.net
export JIRA_CLIENT_ID=your_oauth_client_id
export JIRA_CLIENT_SECRET=your_oauth_client_secret
export JIRA_REDIRECT_URI=your_redirect_uri
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
   export JIRA_URL=https://jira.your-company.com
   export JIRA_TOKEN=your_personal_access_token
   ```

#### Basic Authentication

For older Data Center versions:

```bash
export JIRA_URL=https://jira.your-company.com
export JIRA_USERNAME=your_username
export JIRA_PASSWORD=your_password
```

## ⚙️ Configuration

### Basic Configuration

```yaml
sources:
  jira:
    - url: "${JIRA_URL}"
      username: "${JIRA_EMAIL}"
      token: "${JIRA_TOKEN}"
      projects:
        - "PROJ"
        - "DEV"
        - "DOCS"
      include_attachments: true
      include_comments: true
```

### Advanced Configuration

```yaml
sources:
  jira:
    - url: "${JIRA_URL}"
      username: "${JIRA_EMAIL}"
      token: "${JIRA_TOKEN}"
      
      # Project filtering
      projects:
        - "PROJ"
        - "DEV"
      exclude_projects:
        - "ARCHIVE"
        - "TEST"
      
      # Issue filtering
      issue_types:
        - "Story"
        - "Epic"
        - "Bug"
        - "Task"
      exclude_issue_types:
        - "Sub-task"
      
      # Status filtering
      statuses:
        - "To Do"
        - "In Progress"
        - "Done"
      exclude_statuses:
        - "Cancelled"
        - "Duplicate"
      
      # JQL filtering
      jql_filter: 'project = "PROJ" AND created >= -30d'
      
      # Content options
      include_attachments: true
      include_comments: true
      include_worklogs: false
      include_history: true
      max_history_entries: 10
      
      # Custom fields
      include_custom_fields: true
      custom_field_mapping:
        "customfield_10001": "story_points"
        "customfield_10002": "epic_link"
        "customfield_10003": "sprint"
      
      # File filtering for attachments
      attachment_patterns:
        - "**/*.pdf"
        - "**/*.docx"
        - "**/*.png"
        - "**/*.jpg"
      max_attachment_size: 10485760  # 10MB
      
      # Performance settings
      max_concurrent_issues: 5
      request_timeout: 30
      retry_attempts: 3
      enable_caching: true
```

### Multiple JIRA Instances

```yaml
sources:
  jira:
    # Production JIRA Cloud
    - url: "https://company.atlassian.net"
      username: "${JIRA_EMAIL}"
      token: "${JIRA_TOKEN}"
      projects: ["PROD", "RELEASE"]
      
    # Development JIRA Data Center
    - url: "https://dev-jira.company.com"
      username: "${DEV_JIRA_USERNAME}"
      token: "${DEV_JIRA_TOKEN}"
      projects: ["DEV", "RESEARCH"]
```

## 🎯 Configuration Options

### Connection Settings

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `url` | string | JIRA base URL | Required |
| `username` | string | Username or email | Required |
| `token` | string | API token or password | Required |
| `verify_ssl` | bool | Verify SSL certificates | `true` |

### Project and Issue Filtering

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `projects` | list | Project keys to include | All accessible |
| `exclude_projects` | list | Project keys to exclude | `[]` |
| `issue_types` | list | Issue types to include | All types |
| `exclude_issue_types` | list | Issue types to exclude | `[]` |
| `statuses` | list | Issue statuses to include | All statuses |
| `exclude_statuses` | list | Issue statuses to exclude | `[]` |
| `jql_filter` | string | JQL query for advanced filtering | None |

### Content Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `include_attachments` | bool | Process issue attachments | `true` |
| `include_comments` | bool | Include issue comments | `true` |
| `include_worklogs` | bool | Include work log entries | `false` |
| `include_history` | bool | Include issue history | `false` |
| `max_history_entries` | int | Maximum history entries per issue | `10` |

### Custom Fields

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `include_custom_fields` | bool | Process custom fields | `true` |
| `custom_field_mapping` | dict | Map custom field IDs to names | `{}` |
| `exclude_custom_fields` | list | Custom field IDs to exclude | `[]` |

### Attachment Processing

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `attachment_patterns` | list | File patterns to include | `["**/*"]` |
| `max_attachment_size` | int | Maximum file size in bytes | `10485760` |
| `download_attachments` | bool | Download and process files | `true` |

### Performance Settings

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `max_concurrent_issues` | int | Concurrent issue requests | `5` |
| `request_timeout` | int | Request timeout in seconds | `30` |
| `retry_attempts` | int | Number of retry attempts | `3` |
| `enable_caching` | bool | Cache issues locally | `true` |

## 🚀 Usage Examples

### Software Development Team

```yaml
sources:
  jira:
    - url: "${JIRA_URL}"
      username: "${JIRA_EMAIL}"
      token: "${JIRA_TOKEN}"
      
      # Development projects
      projects:
        - "DEV"       # Main development
        - "BUG"       # Bug tracking
        - "FEAT"      # Feature requests
      
      # Focus on active work
      issue_types:
        - "Story"
        - "Epic"
        - "Bug"
        - "Task"
      statuses:
        - "To Do"
        - "In Progress"
        - "In Review"
        - "Done"
      
      # Include comprehensive data
      include_attachments: true
      include_comments: true
      include_history: true
      
      # Map important custom fields
      custom_field_mapping:
        "customfield_10001": "story_points"
        "customfield_10002": "epic_link"
        "customfield_10003": "sprint"
        "customfield_10004": "team"
      
      # JQL for recent activity
      jql_filter: 'updated >= -7d'
```

### Product Management

```yaml
sources:
  jira:
    - url: "${JIRA_URL}"
      username: "${JIRA_EMAIL}"
      token: "${JIRA_TOKEN}"
      
      # Product projects
      projects:
        - "PROD"      # Product backlog
        - "EPIC"      # Epic tracking
        - "REQ"       # Requirements
      
      # Focus on planning items
      issue_types:
        - "Epic"
        - "Story"
        - "Requirement"
        - "Initiative"
      
      # Include all content for context
      include_attachments: true
      include_comments: true
      include_worklogs: true
      
      # Product-specific fields
      custom_field_mapping:
        "customfield_10005": "business_value"
        "customfield_10006": "customer_impact"
        "customfield_10007": "release_target"
      
      # Focus on active planning
      jql_filter: 'status != "Cancelled" AND status != "Duplicate"'
```

### Support Team

```yaml
sources:
  jira:
    - url: "${JIRA_URL}"
      username: "${JIRA_EMAIL}"
      token: "${JIRA_TOKEN}"
      
      # Support projects
      projects:
        - "SUP"       # Customer support
        - "INC"       # Incidents
        - "KB"        # Knowledge base
      
      # Support-focused issue types
      issue_types:
        - "Bug"
        - "Support Request"
        - "Incident"
        - "Problem"
      
      # Include customer communications
      include_comments: true
      include_attachments: true
      
      # Support-specific fields
      custom_field_mapping:
        "customfield_10008": "customer"
        "customfield_10009": "severity"
        "customfield_10010": "resolution_time"
      
      # Recent issues for trending analysis
      jql_filter: 'created >= -30d'
```

## 🔍 Advanced Features

### JQL-Based Filtering

```yaml
sources:
  jira:
    - url: "${JIRA_URL}"
      username: "${JIRA_EMAIL}"
      token: "${JIRA_TOKEN}"
      
      # Complex JQL queries
      jql_filter: |
        project in ("DEV", "PROD") AND 
        status in ("To Do", "In Progress", "Done") AND 
        created >= -90d AND 
        labels not in ("internal", "deprecated")
```

### Sprint and Agile Data

```yaml
sources:
  jira:
    - url: "${JIRA_URL}"
      username: "${JIRA_EMAIL}"
      token: "${JIRA_TOKEN}"
      projects: ["AGILE"]
      
      # Include agile-specific data
      include_sprint_data: true
      include_board_data: true
      max_sprints_per_board: 10
      
      # Agile custom fields
      custom_field_mapping:
        "customfield_10003": "sprint"
        "customfield_10001": "story_points"
        "customfield_10020": "epic_link"
```

### Historical Analysis

```yaml
sources:
  jira:
    - url: "${JIRA_URL}"
      username: "${JIRA_EMAIL}"
      token: "${JIRA_TOKEN}"
      projects: ["PROJ"]
      
      # Include comprehensive history
      include_history: true
      max_history_entries: 50
      include_changelog: true
      
      # Track field changes
      track_field_changes:
        - "status"
        - "assignee"
        - "priority"
        - "story_points"
      
      # Long-term analysis
      jql_filter: 'created >= -365d'
```

### Performance Optimization

```yaml
sources:
  jira:
    - url: "${JIRA_URL}"
      username: "${JIRA_EMAIL}"
      token: "${JIRA_TOKEN}"
      projects: ["LARGE"]
      
      # Optimize for large projects
      max_concurrent_issues: 10
      batch_size: 100
      
      # Enable aggressive caching
      enable_caching: true
      cache_ttl_hours: 12
      
      # Limit scope
      max_issues_per_project: 5000
      jql_filter: 'updated >= -30d'
```

## 🧪 Testing and Validation

### Test JIRA Connection

```bash
# Test JIRA connectivity
qdrant-loader --workspace . test-connections --sources jira

# Validate JIRA configuration
qdrant-loader --workspace . validate --sources jira

# List accessible projects
qdrant-loader --workspace . list-projects --sources jira

# Test JQL query
qdrant-loader --workspace . test-jql --sources jira --query 'project = "PROJ"'

# Dry run to see what would be processed
qdrant-loader --workspace . --dry-run ingest --sources jira
```

### Debug JIRA Processing

```bash
# Enable verbose logging
qdrant-loader --workspace . --verbose ingest --sources jira

# Process specific projects only
qdrant-loader --workspace . ingest --sources jira --projects PROJ,DEV

# Check processing status
qdrant-loader --workspace . status --sources jira --detailed
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

# For Data Center, test with username/password
curl -u "username:password" \
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

#### JQL Query Issues

**Problem**: `Invalid JQL query` or `JQL syntax error`

**Solutions**:

```bash
# Test JQL query manually
curl -u "your-email:your-token" \
  "https://your-domain.atlassian.net/rest/api/2/search" \
  -G -d "jql=project = PROJ"

# Validate JQL syntax
curl -u "your-email:your-token" \
  "https://your-domain.atlassian.net/rest/api/2/jql/parse" \
  -X POST -H "Content-Type: application/json" \
  -d '{"queries": ["project = PROJ AND status = \"To Do\""]}'
```

#### Rate Limiting

**Problem**: `429 Too Many Requests`

**Solutions**:

```yaml
sources:
  jira:
    - url: "${JIRA_URL}"
      username: "${JIRA_EMAIL}"
      token: "${JIRA_TOKEN}"
      
      # Reduce concurrent requests
      max_concurrent_issues: 2
      request_delay: 1.0
      
      # Increase timeout
      request_timeout: 60
      retry_attempts: 5
```

#### Large Project Performance

**Problem**: Processing takes too long or times out

**Solutions**:

```yaml
sources:
  jira:
    - url: "${JIRA_URL}"
      username: "${JIRA_EMAIL}"
      token: "${JIRA_TOKEN}"
      
      # Limit scope with JQL
      jql_filter: 'project = "PROJ" AND updated >= -30d'
      
      # Optimize processing
      include_attachments: false
      include_history: false
      max_concurrent_issues: 3
      
      # Batch processing
      batch_size: 50
```

#### Custom Field Issues

**Problem**: Custom fields not appearing or incorrect values

**Solutions**:

```bash
# List all custom fields
curl -u "your-email:your-token" \
  "https://your-domain.atlassian.net/rest/api/2/field" | \
  jq '.[] | select(.custom == true) | {id: .id, name: .name}'

# Check specific issue fields
curl -u "your-email:your-token" \
  "https://your-domain.atlassian.net/rest/api/2/issue/PROJ-123?expand=names"
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
  "https://domain.atlassian.net/rest/api/2/issue/PROJ-123?expand=changelog"
```

## 📊 Monitoring and Metrics

### Processing Statistics

```bash
# View JIRA processing statistics
qdrant-loader --workspace . stats --sources jira

# Check project-specific statistics
qdrant-loader --workspace . stats --sources jira --projects PROJ

# Monitor processing progress
qdrant-loader --workspace . status --sources jira --watch
```

### Performance Metrics

Monitor these metrics for JIRA processing:

- **Issues processed per minute** - Processing throughput
- **API request rate** - Requests per second to JIRA
- **Error rate** - Percentage of failed issue requests
- **Attachment download time** - Time to download and process files
- **Memory usage** - Peak memory during processing
- **JQL query performance** - Time to execute complex queries

## 🔄 Best Practices

### Project Organization

1. **Use descriptive project keys** - Make projects easy to identify
2. **Organize with components** - Use components for categorization
3. **Apply consistent labeling** - Use labels for cross-project categorization
4. **Archive completed projects** - Move old projects to archive status

### Performance Optimization

1. **Use targeted JQL queries** - Filter data at the source
2. **Limit attachment processing** - Set reasonable size limits
3. **Use incremental updates** - Process only recent changes
4. **Enable caching** - Cache issue data for repeated runs

### Security Considerations

1. **Use API tokens** - Prefer tokens over passwords
2. **Limit token scope** - Grant minimal necessary permissions
3. **Rotate tokens regularly** - Update tokens periodically
4. **Monitor access** - Track which projects are being accessed

### Data Quality

1. **Maintain consistent issue types** - Use standard issue type schemes
2. **Use structured descriptions** - Follow description templates
3. **Keep custom fields current** - Remove unused custom fields
4. **Regular data cleanup** - Archive or close old issues

## 📚 Related Documentation

- **[File Conversion](../file-conversion/)** - Processing JIRA attachments
- **[Configuration Reference](../../configuration/)** - Complete configuration options
- **[Troubleshooting](../../troubleshooting/)** - Common issues and solutions
- **[MCP Server](../mcp-server/)** - Using processed JIRA content with AI tools

---

**Ready to connect your JIRA instance?** Start with the basic configuration above and customize based on your project structure and workflow needs.
