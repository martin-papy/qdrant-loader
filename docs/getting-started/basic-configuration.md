# Basic Configuration

This guide covers only the starter configuration pattern.

For complete options and provider-specific details, use canonical references under user configuration docs.

## Goals

- Define one reusable global configuration
- Add one project with one source
- Validate settings before first ingest

## Step 1. Create .env

```bash
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=my_documents

LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your-openai-key
LLM_EMBEDDING_MODEL=text-embedding-3-small
LLM_CHAT_MODEL=gpt-4o-mini
```

## Step 2. Create config.yaml

```yaml
global:
  qdrant:
    url: "${QDRANT_URL}"
    collection_name: "${QDRANT_COLLECTION_NAME}"
  llm:
    provider: "${LLM_PROVIDER}"
    base_url: "${LLM_BASE_URL}"
    api_key: "${LLM_API_KEY}"
    models:
      embeddings: "${LLM_EMBEDDING_MODEL}"
      chat: "${LLM_CHAT_MODEL}"
    embeddings:
      vector_size: 1536
  chunking:
    chunk_size: 1500
    chunk_overlap: 200

projects:
  default:
    project_id: "default"
    display_name: "Default Project"
    sources:
      localfile:
        docs:
          base_url: "file://./docs"
          include_paths:
            - "**/*.md"
```

## Step 3. Validate and ingest

```bash
qdrant-loader init --workspace .
qdrant-loader ingest --workspace .
```

## What to customize next

- Add more sources (Git/Confluence/Jira): [Data Sources Guide](../users/detailed-guides/data-sources/)
- Tune chunking and global settings: [Configuration Reference](../users/configuration/config-file-reference.md)
- Configure provider-specific LLM details: [LLM Provider Guide](../users/configuration/llm-provider-guide.md)
- Full variable reference: [Environment Variables Reference](../users/configuration/environment-variables.md)
- Workspace and config loading modes: [Workspace Mode](../users/configuration/workspace-mode.md)
- Secure credentials and file permissions: [Security Considerations](../users/configuration/security-considerations.md)
- Validation and common config errors: [Troubleshooting](../users/troubleshooting/)
- Multi-environment setup patterns: [Common Workflows](../users/workflows/common-workflows.md)
- Performance tuning guidance: [Performance Issues](../users/troubleshooting/performance-issues.md)
