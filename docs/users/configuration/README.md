# Configuration Reference

This section provides comprehensive documentation for configuring QDrant Loader. Learn how to set up data sources, optimize performance, configure security, and customize behavior for your specific needs.

## Start here

1. Environment variables: [Environment Variables Reference](./environment-variables.md)
2. LLM providers and model mapping: [LLM Provider Guide](./llm-provider-guide.md)
3. Full YAML schema: [Configuration File Reference](./config-file-reference.md)
4. Security practices: [Security Considerations](./security-considerations.md)
5. Runtime flags and setup modes: [CLI Commands](../cli-reference/commands.md)
6. Workspace-vs-traditional config loading: [Workspace Mode](./workspace-mode.md)

## Choose your path

- New workspace in minutes: use [Quick Start](../../getting-started/quick-start.md)
- Minimal first config: use [Basic Configuration](../../getting-started/basic-configuration.md)
- Team or production rollout: use [Configuration File Reference](./config-file-reference.md) and [Security Considerations](./security-considerations.md)
- Troubleshoot config or env issues: use [Troubleshooting](../troubleshooting/)

## Quick baseline

Use this minimal pair as a baseline and then extend from references above.

### .env

```bash
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=documents

LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your-openai-key
LLM_EMBEDDING_MODEL=text-embedding-3-small
LLM_CHAT_MODEL=gpt-4o-mini
```

### config.yaml

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

projects:
  default:
    project_id: "default"
    display_name: "Default"
    sources:
      localfile:
        docs:
          base_url: "file://./docs"
          include_paths:
            - "**/*.md"
```

## Notes

- Keep provider-specific details only in [LLM Provider Guide](./llm-provider-guide.md).
- Keep all variable definitions only in [Environment Variables Reference](./environment-variables.md).
- Keep schema-level field details only in [Configuration File Reference](./config-file-reference.md).

## Quick validation checklist

- [ ] `qdrant-loader config --workspace .` loads without errors
- [ ] Required env vars are set for your chosen provider
- [ ] At least one project and one source are configured
- [ ] QDrant URL and collection name are valid

