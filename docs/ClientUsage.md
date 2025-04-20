# QDrant Loader Client Usage Guide

This guide provides comprehensive documentation for using the QDrant Loader client.

## Installation

```bash
pip install qdrant-loader
```

## Configuration

### Environment Variables

Required variables:

- `QDRANT_URL`: URL of your QDrant instance (local or cloud). http:// is mandatory except for localhost/127.0.0.1
- `QDRANT_COLLECTION_NAME`: Name of the collection to use
- `QDRANT_API_KEY`: API key for authentication (required but can be empty for local instances)
- `OPENAI_API_KEY`: API key for OpenAI embeddings

Optional variables (required only for specific sources):

- Git: `REPO_TOKEN`, `REPO_URL`
- Confluence: `CONFLUENCE_URL`, `CONFLUENCE_SPACE_KEY`, `CONFLUENCE_TOKEN`, `CONFLUENCE_EMAIL`
- JIRA: `JIRA_URL`, `JIRA_PROJECT_KEY`, `JIRA_TOKEN`, `JIRA_EMAIL`

### Configuration File

The `config.yaml` file controls the ingestion pipeline behavior. Key settings include:

```yaml
global:
  chunking:
    size: 500
    overlap: 50
  embedding:
    model: text-embedding-3-small
    batch_size: 100
  logging:
    level: INFO
    format: json
    file: qdrant-loader.log

sources:
  jira:
    my_project:
      base_url: "https://your-domain.atlassian.net"
      project_key: "PROJ"
      issue_types:
        - "Documentation"
        - "Technical Spec"
      include_statuses:
        - "Done"
        - "Approved"
```

## Command Line Interface

### Basic Commands

```bash
# Show help and available commands
qdrant-loader --help

# Initialize the QDrant collection
qdrant-loader init

# Run ingestion for all sources
qdrant-loader ingest
```

### Source-Specific Commands

```bash
# Run ingestion for specific source types
qdrant-loader ingest --source-type confluence  # Ingest only Confluence
qdrant-loader ingest --source-type git        # Ingest only Git
qdrant-loader ingest --source-type publicdocs # Ingest only public docs
qdrant-loader ingest --source-type jira       # Ingest only JIRA

# Run ingestion for specific sources
qdrant-loader ingest --source-type confluence --source my-space
qdrant-loader ingest --source-type git --source my-repo
qdrant-loader ingest --source-type jira --source my-project
```

### Utility Commands

```bash
# Show current configuration
qdrant-loader config

# Show version information
qdrant-loader --version
```

### Common Options

All commands support:

- `--log-level LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `--config FILE`: Specify custom config file (defaults to config.yaml)

## Advanced Usage

### Custom Configuration

You can specify a custom configuration file using the `--config` option:

```bash
qdrant-loader ingest --config custom_config.yaml
```

### Logging Configuration

The logging level can be adjusted using the `--log-level` option:

```bash
qdrant-loader ingest --log-level DEBUG
```

## Troubleshooting

### Common Issues

1. **Connection Issues**
   - Verify your QDrant URL and API key
   - Check network connectivity
   - Ensure the QDrant server is running

2. **Authentication Problems**
   - Verify all required API keys are set
   - Check token permissions
   - Ensure environment variables are properly set

3. **Configuration Errors**
   - Validate your config.yaml file
   - Check for missing required fields
   - Verify source-specific configurations

### Error Messages

Common error messages and their solutions:

- `QDRANT_CONNECTION_ERROR`: Check QDrant server status and connection details
- `MISSING_API_KEY`: Verify all required API keys are set in environment variables
- `INVALID_CONFIG`: Review and fix configuration file syntax

## Best Practices

1. **Configuration Management**
   - Use environment variables for sensitive data
   - Keep configuration files in version control
   - Document all custom configurations

2. **Performance Optimization**
   - Adjust chunking size based on content type
   - Use appropriate batch sizes for embeddings
   - Monitor memory usage during large ingestions

3. **Security**
   - Never commit API keys or tokens
   - Use secure methods for storing credentials
   - Regularly rotate API keys and tokens
