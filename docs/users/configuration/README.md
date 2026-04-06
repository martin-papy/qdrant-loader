# Configuration Reference

This section defines the canonical configuration entry points.

## Start here

1. Environment variables: [environment-variables.md](./environment-variables.md)
2. LLM providers and model mapping: [llm-provider-guide.md](./llm-provider-guide.md)
3. Full YAML schema: [config-file-reference.md](./config-file-reference.md)
4. Security practices: [security-considerations.md](./security-considerations.md)

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

- Keep provider-specific details only in [llm-provider-guide.md](./llm-provider-guide.md).
- Keep all variable definitions only in [environment-variables.md](./environment-variables.md).
- Keep schema-level field details only in [config-file-reference.md](./config-file-reference.md).
