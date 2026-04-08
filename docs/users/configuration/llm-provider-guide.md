# LLM Provider Guide

This is the canonical source for LLM provider configuration.

## Required fields

Set these values in `.env` and reference them from `config.yaml`:

```bash
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your-api-key
LLM_EMBEDDING_MODEL=text-embedding-3-small
LLM_CHAT_MODEL=gpt-4o-mini
```

```yaml
global:
  llm:
    provider: "${LLM_PROVIDER}"
    base_url: "${LLM_BASE_URL}"
    api_key: "${LLM_API_KEY}"
    models:
      embeddings: "${LLM_EMBEDDING_MODEL}"
      chat: "${LLM_CHAT_MODEL}"
    embeddings:
      vector_size: 1536
```

## Provider profiles

### OpenAI

```bash
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-your-openai-key
LLM_EMBEDDING_MODEL=text-embedding-3-small
LLM_CHAT_MODEL=gpt-4o-mini
```

### Azure OpenAI

```bash
LLM_PROVIDER=azure_openai
LLM_BASE_URL=https://<resource>.openai.azure.com
LLM_API_KEY=your-azure-key
LLM_API_VERSION=2024-05-01-preview
LLM_EMBEDDING_MODEL=<embedding-deployment-name>
LLM_CHAT_MODEL=<chat-deployment-name>
```

Notes:

- Use the resource root in `LLM_BASE_URL`.
- Use deployment names for `LLM_*_MODEL` values.

### Ollama

```bash
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=dummy
LLM_EMBEDDING_MODEL=nomic-embed-text
LLM_CHAT_MODEL=llama3.1:8b-instruct
```

Notes:

- If your deployment uses native Ollama APIs, keep model names valid for your server.
- For local/no-auth setups, `LLM_API_KEY` may be ignored by backend logic.

### OpenAI-compatible endpoint

```bash
LLM_PROVIDER=openai_compat
LLM_BASE_URL=https://your-endpoint.example.com/v1
LLM_API_KEY=your-endpoint-key
LLM_EMBEDDING_MODEL=your-embedding-model
LLM_CHAT_MODEL=your-chat-model
```

## Vector size mapping

Set `global.llm.embeddings.vector_size` to match embedding output dimension.

Common examples:

- `text-embedding-3-small` -> `1536`
- `text-embedding-3-large` -> `3072`
- Ollama models vary by model; verify before collection creation

## Legacy compatibility

`OPENAI_API_KEY` is still supported in some flows, but canonical config should use `LLM_API_KEY`.

## Related references

- Variables: [Environment Variables Reference](./environment-variables.md)
- YAML schema: [Configuration File Reference](./config-file-reference.md)
- Security: [Security Considerations](./security-considerations.md)
