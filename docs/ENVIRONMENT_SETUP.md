# Environment Setup Guide

This guide explains how to configure environment variables and manage secrets for the QDrant Loader application.

## Quick Start

1. **Copy the environment template:**
   ```bash
   cp .env.template .env
   ```

2. **Edit the `.env` file** with your specific configuration values

3. **Never commit `.env` to version control** - it contains sensitive information

## Environment Files

### `.env.template`
- Template file with all available configuration options
- Safe to commit to version control
- Contains documentation and examples for each variable

### `.env`
- Your actual environment configuration
- **NEVER commit this file**
- Contains sensitive API keys and passwords
- Automatically loaded by Docker Compose

### `docker.env.example`
- Legacy example file for Docker-specific variables
- Use `.env.template` instead for new setups

## Configuration Categories

### Database Configuration

#### QDrant Vector Database
```bash
QDRANT_URL=http://qdrant:6333
QDRANT__SERVICE__HTTP_PORT=6333
QDRANT__SERVICE__GRPC_PORT=6334
```

#### Neo4j Graph Database
```bash
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-secure-password-here

# Memory settings (adjust based on your system)
NEO4J_HEAP_INITIAL=512m
NEO4J_HEAP_MAX=2G
NEO4J_PAGECACHE=1G
```

### AI/ML API Keys

The application supports multiple AI providers. Configure the ones you plan to use:

```bash
# OpenAI (for GPT models and embeddings)
OPENAI_API_KEY=sk-your-openai-api-key-here

# Anthropic (for Claude models)
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key-here

# Cohere (for embeddings)
COHERE_API_KEY=your-cohere-api-key-here

# Hugging Face (for open-source models)
HUGGINGFACE_API_KEY=hf_your-huggingface-api-key-here
```

### Security Configuration

```bash
# JWT Secret for authentication (generate a secure random string)
JWT_SECRET=your-jwt-secret-here

# API Rate Limiting
RATE_LIMIT_PER_MINUTE=100

# CORS Origins
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

## Secrets Management

### Development Environment

For development, using `.env` files is sufficient. Ensure:

1. **Never commit `.env` files**
2. **Use strong passwords** for database credentials
3. **Rotate API keys** regularly
4. **Use different credentials** for development vs production

### Production Environment

For production deployments, consider these security practices:

#### Docker Secrets
```yaml
# docker-compose.prod.yml
services:
  qdrant-loader:
    secrets:
      - neo4j_password
      - openai_api_key
    environment:
      - NEO4J_PASSWORD_FILE=/run/secrets/neo4j_password
      - OPENAI_API_KEY_FILE=/run/secrets/openai_api_key

secrets:
  neo4j_password:
    file: ./secrets/neo4j_password.txt
  openai_api_key:
    file: ./secrets/openai_api_key.txt
```

#### External Secret Management
- **AWS Secrets Manager**
- **Azure Key Vault**
- **Google Secret Manager**
- **HashiCorp Vault**
- **Kubernetes Secrets**

#### Environment Variable Injection
```bash
# From external secret management
export NEO4J_PASSWORD=$(aws secretsmanager get-secret-value --secret-id neo4j-password --query SecretString --output text)
export OPENAI_API_KEY=$(vault kv get -field=api_key secret/openai)
```

## Variable Precedence

Docker Compose resolves environment variables in this order (highest to lowest priority):

1. **Compose file environment section**
2. **Shell environment variables**
3. **Environment files (.env)**
4. **Dockerfile ENV instructions**

## Validation

### Required Variables
The application will fail to start if these variables are missing:
- `QDRANT_URL`
- `NEO4J_URI`
- `NEO4J_USER`
- `NEO4J_PASSWORD`

### Optional Variables
These have sensible defaults but can be customized:
- `MCP_SERVER_PORT` (default: 3000)
- `LOG_LEVEL` (default: INFO)
- `NEO4J_HEAP_MAX` (default: 2G)

## Troubleshooting

### Common Issues

1. **Service connection failures**
   - Check database URLs and ports
   - Verify network connectivity between containers

2. **Authentication errors**
   - Verify username/password combinations
   - Check API key validity and permissions

3. **Memory issues**
   - Adjust Neo4j heap settings based on available RAM
   - Monitor container resource usage

### Debugging Environment Variables

```bash
# Check loaded environment in container
docker-compose exec qdrant-loader env | grep -E "(QDRANT|NEO4J|OPENAI)"

# Validate Docker Compose configuration
docker-compose config

# Check service logs for environment-related errors
docker-compose logs qdrant-loader
```

## Best Practices

1. **Use descriptive variable names**
2. **Group related variables together**
3. **Provide sensible defaults where possible**
4. **Document all variables in `.env.template`**
5. **Validate required variables at startup**
6. **Use secrets management in production**
7. **Rotate credentials regularly**
8. **Monitor for credential leaks in logs**

## Migration Guide

### From docker.env.example to .env.template

1. Copy your existing values from `docker.env.example`
2. Use `.env.template` as the base for your new `.env` file
3. Update variable names to match the new structure
4. Remove the old `docker.env.example` file

### Adding New Variables

1. Add to `.env.template` with documentation
2. Update Docker Compose files if needed
3. Update this documentation
4. Test with default values 