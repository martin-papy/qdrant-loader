# QDrant Loader Client Usage Guide

This comprehensive guide covers all aspects of using the QDrant Loader ecosystem, including both the core loader and MCP server components.

## 📦 Installation

### Package Installation

```bash
# Install core loader only
pip install qdrant-loader

# Install MCP server only
pip install qdrant-loader-mcp-server

# Install both packages
pip install qdrant-loader qdrant-loader-mcp-server

# Development installation from source
git clone https://github.com/martin-papy/qdrant-loader.git
cd qdrant-loader
pip install -e packages/qdrant-loader[dev]
pip install -e packages/qdrant-loader-mcp-server[dev]
```

## Configuration

### Quick Start with Templates

The QDrant Loader uses a YAML-based configuration system. Get started quickly using the provided templates:

```bash
# Copy the configuration template
cp config.template.yaml config.yaml

# Copy the environment template (optional)
cp .env.template .env

# Edit the files with your settings
nano config.yaml
nano .env
```

### Configuration Files

The system uses two main files:

1. **`config.yaml`** - Main configuration (structure, sources, settings)
2. **`.env`** - Environment variables (API keys, tokens, sensitive data)

### Key Configuration Concepts

- **Global Settings**: QDrant connection, chunking, embedding, and processing settings
- **Source Configurations**: Define what data sources to ingest (Confluence, JIRA, Git, local files)
- **Environment Variables**: Use `${VAR_NAME}` syntax in config.yaml to reference .env values
- **Multiple Environments**: Use different .env files for dev/staging/production

### Required Configuration

At minimum, you need to configure:

1. **QDrant connection** in the global.qdrant section
2. **OpenAI API key** for embeddings (in .env file)
3. **At least one source** to ingest data from

See `config.template.yaml` for the complete structure and available options.

### Environment Variable Substitution

You can reference environment variables anywhere in your `config.yaml` using the `${VAR_NAME}` syntax. The system will automatically substitute any `${VAR_NAME}` pattern it finds with the corresponding environment variable value.

```yaml
global:
  qdrant:
    url: "${QDRANT_URL}"
    api_key: "${QDRANT_API_KEY}"
    collection_name: "${QDRANT_COLLECTION_NAME}"
  
  chunking:
    chunk_size: "${CHUNK_SIZE}"  # Works with any environment variable
  
sources:
  confluence:
    my_space:
      base_url: "${CONFLUENCE_URL}"
      space_key: "${CONFLUENCE_SPACE_KEY}"
```

Then define them in your `.env` file or system environment:

```bash
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_api_key
QDRANT_COLLECTION_NAME=documents
CHUNK_SIZE=500
CONFLUENCE_URL=https://mycompany.atlassian.net/wiki
CONFLUENCE_SPACE_KEY=MYSPACE
```

**Important Notes:**

- Environment variables can be defined in `.env` files or system environment
- If a referenced variable doesn't exist, a warning is logged but processing continues
- The substitution works recursively throughout the entire configuration
- `$HOME` is also automatically expanded to the user's home directory

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
qdrant-loader ingest --source-type localfile  # Ingest only local files

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

### Command Options

#### Initialize Command

```bash
# Initialize with custom config file
qdrant-loader init --config custom_config.yaml

# Initialize with custom environment file
qdrant-loader init --config config.yaml --env custom.env

# Force reinitialization (recreates collection)
qdrant-loader init --force

# Initialize with debug logging
qdrant-loader init --log-level DEBUG
```

#### Ingest Command

```bash
# Ingest with custom config file
qdrant-loader ingest --config custom_config.yaml

# Ingest with custom environment file
qdrant-loader ingest --config config.yaml --env production.env

# Ingest specific source type and source
qdrant-loader ingest --source-type confluence --source my-space

# Ingest with profiling enabled
qdrant-loader ingest --profile

# Ingest with debug logging
qdrant-loader ingest --log-level DEBUG
```

#### Config Command

```bash
# Display config with custom config file
qdrant-loader config --config custom_config.yaml

# Display config with custom environment file
qdrant-loader config --config config.yaml --env staging.env

# Display config with debug logging
qdrant-loader config --log-level DEBUG
```

### Common Options

All commands support:

- `--log-level LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `--config FILE`: Specify custom config file (defaults to config.yaml)
- `--env FILE`: Specify custom environment file (defaults to .env)

## Advanced Usage

### Multiple Environment Configurations

You can maintain different configurations for different environments:

```bash
# Development environment
qdrant-loader ingest --config config.yaml --env .env.dev

# Staging environment
qdrant-loader ingest --config config.yaml --env .env.staging

# Production environment
qdrant-loader ingest --config config.yaml --env .env.prod
```

### Configuration Validation

The system validates your configuration on startup and provides helpful error messages:

```bash
# Test configuration without running ingestion
qdrant-loader config --config config.yaml --env .env
```

### Custom Configuration Paths

```bash
# Use configuration files from different directories
qdrant-loader ingest --config /path/to/config.yaml --env /path/to/.env
```

## Troubleshooting

### Common Issues

1. **Configuration Validation Errors**
   - Check YAML syntax in config.yaml
   - Ensure all required fields are present
   - Verify environment variable references

2. **Connection Issues**
   - Verify your QDrant URL in the configuration
   - Check network connectivity
   - Ensure the QDrant server is running

3. **Authentication Problems**
   - Verify all required API keys are set in .env file
   - Check token permissions
   - Ensure environment variables are properly loaded

4. **Missing Environment Variables**
   - Check that referenced environment variables exist
   - Verify .env file is in the correct location
   - Ensure environment variable names match exactly

### Error Messages

Common error messages and their solutions:

- `QDRANT_CONNECTION_ERROR`: Check QDrant server status and connection details in config.yaml
- `MISSING_API_KEY`: Verify required API keys are set in .env file
- `INVALID_CONFIG`: Review and fix configuration file syntax
- `MISSING_QDRANT_CONFIG`: Ensure qdrant section is present in global configuration
- `ENVIRONMENT_VARIABLE_NOT_FOUND`: Check that referenced environment variables exist

### Configuration Debugging

```bash
# Display the loaded configuration to debug issues
qdrant-loader config --log-level DEBUG

# Check specific configuration sections
qdrant-loader config --config config.yaml --env .env
```

## Best Practices

1. **Configuration Management**
   - Keep sensitive data in .env files, not in config.yaml
   - Use version control for config.yaml but exclude .env files
   - Document all custom configurations
   - Use environment variable substitution for deployment flexibility

2. **Security**
   - Never commit .env files or API keys to version control
   - Use different .env files for different environments
   - Regularly rotate API keys and tokens
   - Set appropriate file permissions on .env files

3. **Performance Optimization**
   - Adjust chunking size based on content type
   - Use appropriate batch sizes for embeddings
   - Monitor memory usage during large ingestions
   - Configure appropriate timeouts for file conversion

4. **Environment Management**
   - Use separate configurations for dev/staging/production
   - Test configuration changes in development first
   - Maintain configuration documentation

## Migration from Environment Variables

If you're migrating from the old environment variable approach  (i.e.from v0.3.0b2 and bellow ):

1. **Create config.yaml** with the qdrant section:

   ```yaml
   global:
     qdrant:
       url: "${QDRANT_URL}"
       api_key: "${QDRANT_API_KEY}"
       collection_name: "${QDRANT_COLLECTION_NAME}"
   ```

2. **Move sensitive data** to .env file:

   ```bash
   QDRANT_URL=http://localhost:6333
   QDRANT_API_KEY=your_api_key
   QDRANT_COLLECTION_NAME=documents
   ```

3. **Update your commands** to use config files:

   ```bash
   qdrant-loader ingest --config config.yaml --env .env
   ```

## Additional CLI Examples

```bash
# Ingest only local files with custom config
qdrant-loader ingest --source-type localfile --config my_config.yaml

# Ingest a specific localfile source with staging environment
qdrant-loader ingest --source-type localfile --source my-local-files --env .env.staging

# Run with performance profiling and debug logging
qdrant-loader ingest --profile --log-level DEBUG

# Initialize with force flag and custom environment
qdrant-loader init --force --config config.yaml --env .env.prod

# Display configuration for troubleshooting
qdrant-loader config --config config.yaml --env .env --log-level DEBUG
```
