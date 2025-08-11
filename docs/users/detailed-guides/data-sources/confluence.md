# Confluence
Connect QDrant Loader to Confluence to index team documentation, knowledge bases, and collaborative content. This guide covers setup for both Confluence Cloud and Confluence Data Center.
## 🎯 What Gets Processed
When you connect to Confluence, QDrant Loader can process:
- **Page content** - All text content from Confluence pages
- **Page hierarchy** - Parent/child relationships between pages
- **Attachments** - Files attached to pages (PDFs, Office docs, images)
- **Comments** - Page comments and discussions
- **Page metadata** - Authors, creation dates, labels, versions
- **Space information** - Space descriptions and metadata
## 🔧 Authentication Setup
### Confluence Cloud
#### API Token (Recommended)
1. **Create an API Token**: - Go to [Atlassian Account Settings](https://id.atlassian.com/manage-profile/security/api-tokens) - Click "Create API token" - Give it a descriptive name like "QDrant Loader" - Copy the token
2. **Set environment variables**: ```bash export CONFLUENCE_URL=https://your-domain.atlassian.net/wiki export CONFLUENCE_EMAIL=your-email@company.com export CONFLUENCE_TOKEN=your_api_token_here ```
### Confluence Data Center
#### Personal Access Token
1. **Create a Personal Access Token**: - Go to Confluence → Settings → Personal Access Tokens - Click "Create token" - Set appropriate permissions: `READ` for spaces and pages - Copy the token
2. **Set environment variables**: ```bash export CONFLUENCE_URL=https://confluence.your-company.com export CONFLUENCE_TOKEN=your_personal_access_token ```
## ⚙️ Configuration
QDrant Loader uses a **project-based configuration structure**. Each project can have multiple Confluence sources.
### Basic Configuration
```yaml
projects: my-project: display_name: "My Documentation Project" description: "Company documentation and knowledge base" collection_name: "my-docs" sources: confluence: company-wiki: base_url: "${CONFLUENCE_URL}" deployment_type: "cloud" # or "datacenter" space_key: "DOCS" email: "${CONFLUENCE_EMAIL}" # Required for Cloud token: "${CONFLUENCE_TOKEN}" content_types: - "page" - "blogpost" include_labels: [] exclude_labels: [] enable_file_conversion: true download_attachments: true
```
### Advanced Configuration
```yaml
projects: documentation: display_name: "Documentation Hub" description: "All company documentation sources" collection_name: "docs-hub" sources: confluence: # Main documentation space main-docs: base_url: "${CONFLUENCE_URL}" deployment_type: "cloud" space_key: "DOCS" email: "${CONFLUENCE_EMAIL}" token: "${CONFLUENCE_TOKEN}" content_types: - "page" - "blogpost" include_labels: [] exclude_labels: - "draft" - "obsolete" enable_file_conversion: true download_attachments: true # Technical documentation space tech-docs: base_url: "${CONFLUENCE_URL}" deployment_type: "cloud" space_key: "TECH" email: "${CONFLUENCE_EMAIL}" token: "${CONFLUENCE_TOKEN}" content_types: - "page" include_labels: - "api" - "architecture" exclude_labels: - "deprecated" enable_file_conversion: true download_attachments: true
```
### Multiple Confluence Instances
```yaml
projects: multi-confluence: display_name: "Multi-Instance Documentation" description: "Documentation from multiple Confluence instances" collection_name: "multi-docs" sources: confluence: # Cloud instance cloud-wiki: base_url: "https://company.atlassian.net/wiki" deployment_type: "cloud" space_key: "DOCS" email: "${CONFLUENCE_EMAIL}" token: "${CONFLUENCE_TOKEN}" content_types: ["page", "blogpost"] include_labels: [] exclude_labels: [] enable_file_conversion: true download_attachments: true # Data Center instance datacenter-wiki: base_url: "https://internal-confluence.company.com" deployment_type: "datacenter" space_key: "INTERNAL" token: "${CONFLUENCE_PAT}" content_types: ["page"] include_labels: [] exclude_labels: [] enable_file_conversion: true download_attachments: true
```
## 🎯 Configuration Options
### Required Settings
| Option | Type | Description | Example |
|--------|------|-------------|---------|
| `base_url` | string | Confluence base URL | `https://company.atlassian.net/wiki` |
| `deployment_type` | string | Deployment type: `cloud`, `datacenter`, or `server` | `cloud` |
| `space_key` | string | Confluence space key to process | `DOCS` |
| `token` | string | API token or Personal Access Token | `${CONFLUENCE_TOKEN}` |
### Cloud-Specific Settings
| Option | Type | Description | Required for Cloud |
|--------|------|-------------|-------------------|
| `email` | string | Email associated with Confluence account | Yes |
### Content Filtering
| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `content_types` | list | Content types to process | `["page", "blogpost"]` |
| `include_labels` | list | Only process content with these labels | `[]` (all) |
| `exclude_labels` | list | Skip content with these labels | `[]` |
### File Processing
| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `enable_file_conversion` | bool | Enable file conversion for attachments | `true` |
| `download_attachments` | bool | Download and process attachments | `true` |
## 🚀 Usage Examples
### Documentation Team
```yaml
projects: docs-team: display_name: "Documentation Team" description: "All documentation spaces" collection_name: "documentation" sources: confluence: user-guides: base_url: "${CONFLUENCE_URL}" deployment_type: "cloud" space_key: "GUIDES" email: "${CONFLUENCE_EMAIL}" token: "${CONFLUENCE_TOKEN}" content_types: ["page"] include_labels: ["published"] exclude_labels: ["draft", "archive"] enable_file_conversion: true download_attachments: true api-docs: base_url: "${CONFLUENCE_URL}" deployment_type: "cloud" space_key: "API" email: "${CONFLUENCE_EMAIL}" token: "${CONFLUENCE_TOKEN}" content_types: ["page", "blogpost"] include_labels: ["api", "reference"] exclude_labels: ["deprecated"] enable_file_conversion: true download_attachments: true
```
### Software Development Team
```yaml
projects: dev-team: display_name: "Development Team" description: "Technical documentation and architecture" collection_name: "dev-docs" sources: confluence: architecture: base_url: "${CONFLUENCE_URL}" deployment_type: "cloud" space_key: "ARCH" email: "${CONFLUENCE_EMAIL}" token: "${CONFLUENCE_TOKEN}" content_types: ["page"] include_labels: ["architecture", "design"] exclude_labels: ["obsolete"] enable_file_conversion: true download_attachments: true development: base_url: "${CONFLUENCE_URL}" deployment_type: "cloud" space_key: "DEV" email: "${CONFLUENCE_EMAIL}" token: "${CONFLUENCE_TOKEN}" content_types: ["page", "blogpost"] include_labels: ["development", "guidelines"] exclude_labels: ["draft"] enable_file_conversion: true download_attachments: true
```
## 🧪 Testing and Validation
### Initialize and Test Configuration
```bash
# Initialize the project (creates collection if needed)qdrant-loader init --workspace .
# Test ingestion with your Confluence configurationqdrant-loader ingest --workspace . --project my-project
# Check project statusqdrant-loader project --workspace --project-id my-project
# List all configured projectsqdrant-loader project --workspace # Validate project configurationqdrant-loader project --workspace --project-id my-project
```
### Debug Confluence Processing
```bash
# Enable debug loggingqdrant-loader ingest --workspace . --log-level DEBUG --project my-project
# Process specific project onlyqdrant-loader ingest --workspace . --project my-project
# Process specific source within a projectqdrant-loader ingest --workspace . --project my-project --source-type confluence --source company-wiki
```
## 🔧 Troubleshooting
### Common Issues
#### Authentication Failures
**Problem**: `401 Unauthorized` or `403 Forbidden`
**Solutions**:
```bash
# Test API token manually for Cloud
curl -u "your-email@company.com:your-api-token" \ "https://your-domain.atlassian.net/wiki/rest/api/space"
# Test Personal Access Token for Data Center
curl -H "Authorization: Bearer your-personal-access-token" \ "https://confluence.company.com/rest/api/space"
```
**Check your configuration**:
- Ensure `deployment_type` matches your Confluence instance
- For Cloud: verify both `email` and `token` are set
- For Data Center: verify `token` (Personal Access Token) is set
- Ensure the token has appropriate permissions
#### Space Access Issues
**Problem**: `Space not found` or `No permission to access space`
**Solutions**:
```bash
# List accessible spaces for Cloud
curl -u "your-email:your-token" \ "https://your-domain.atlassian.net/wiki/rest/api/space" | jq '.results[].key'
# List accessible spaces for Data Center
curl -H "Authorization: Bearer your-token" \ "https://confluence.company.com/rest/api/space" | jq '.results[].key'
```
**Check your configuration**:
- Verify the `space_key` exists and is accessible
- Ensure your account has read permissions for the space
- Check that the space key is correct (case-sensitive)
#### Configuration Issues
**Problem**: Configuration validation errors
**Solutions**:
1. **Verify project structure**: ```yaml projects: your-project: # Project ID sources: confluence: source-name: # Source name base_url: "..." # ... other settings ```
2. **Check required fields**: - `base_url`: Must include `/wiki` for Cloud instances - `deployment_type`: Must be `cloud`, `datacenter`, or `server` - `space_key`: Must be a valid space key - `token`: Must be set via environment variable or directly
3. **Validate environment variables**: ```bash echo $CONFLUENCE_URL echo $CONFLUENCE_EMAIL echo $CONFLUENCE_TOKEN ```
#### Rate Limiting
**Problem**: `429 Too Many Requests`
**Solutions**:
The Confluence connector automatically handles rate limiting, but you can:
1. **Check your API usage** in Atlassian Admin Console
2. **Reduce concurrent processing** by processing fewer projects simultaneously
3. **Contact your Confluence administrator** if limits are too restrictive
#### Large Space Performance
**Problem**: Processing takes too long or times out
**Solutions**:
1. **Filter content with labels**: ```yaml confluence: large-space: space_key: "LARGE" include_labels: ["important", "current"] exclude_labels: ["archive", "deprecated"] ```
2. **Process specific content types**: ```yaml confluence: pages-only: space_key: "DOCS" content_types: ["page"] # Skip blogposts ```
3. **Disable attachment processing temporarily**: ```yaml confluence: no-attachments: space_key: "DOCS" download_attachments: false ```
### Debugging Commands
```bash
# Check Confluence API connectivity
curl -u "email:token" "https://domain.atlassian.net/wiki/rest/api/space" | jq '.size'
# List pages in a space
curl -u "email:token" \ "https://domain.atlassian.net/wiki/rest/api/space/DOCS/content/page" | \ jq '.results[].title'
# Check specific page content
curl -u "email:token" \ "https://domain.atlassian.net/wiki/rest/api/content/PAGE_ID?expand=body.storage"
```
## 📊 Monitoring and Processing
### Check Processing Status
```bash
# View project statusqdrant-loader project --workspace # Check specific projectqdrant-loader project --workspace --project-id my-project
# List all projectsqdrant-loader project --workspace ```
### Configuration Management
```bash
# View current configurationqdrant-loader config --workspace .
# Validate all projectsqdrant-loader project --workspace ```
## 🔄 Best Practices
### Content Organization
1. **Use descriptive space keys** - Make spaces easy to identify
2. **Apply consistent labeling** - Use labels for categorization and filtering
3. **Organize with page hierarchy** - Use parent/child relationships
4. **Archive old content** - Move outdated content to archive spaces
### Configuration Management
1. **Use environment variables** - Keep sensitive data out of config files
2. **Organize by teams/purposes** - Create separate projects for different use cases
3. **Filter content appropriately** - Use labels to include/exclude content
4. **Test configurations** - Validate before running full ingestion
### Security Considerations
1. **Use API tokens** - Prefer tokens over passwords
2. **Limit token scope** - Grant minimal necessary permissions
3. **Rotate tokens regularly** - Update tokens periodically
4. **Monitor access** - Track which content is being accessed
5. **Use environment variables** - Never commit tokens to version control
### Performance Optimization
1. **Filter aggressively** - Only process content you need
2. **Use appropriate labels** - Filter by labels to reduce processing
3. **Process incrementally** - Run regular updates rather than full reprocessing
4. **Monitor resource usage** - Watch memory and network usage during processing
## 📚 Related Documentation
- **[Configuration Reference](../../configuration/)** - Complete configuration options
- **[File Conversion](../file-conversion/)** - Processing Confluence attachments
- **[Troubleshooting](../../troubleshooting/)** - Common issues and solutions
- **[MCP Server](../mcp-server/)** - Using processed Confluence content with AI tools
- **[Project Management](../../cli-reference/)** - Managing multiple projects
---
**Ready to connect your Confluence instance?** Start with the basic configuration above and customize based on your space structure and content needs.
