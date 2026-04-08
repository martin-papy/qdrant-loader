# MCP Server Guide

This page is the MCP hub. Detailed instructions are split into dedicated pages to avoid duplicate setup content.

## What MCP gives you

- Semantic search in your ingested knowledge base
- Hierarchy-aware retrieval for structured docs
- Attachment-focused search
- Integration with Cursor, Windsurf, Claude Desktop, and other MCP clients

## Canonical pages

- Setup and client integration: [Setup & Integration Guide](./setup-and-integration.md)
- Tool capabilities and examples: [Search Capabilities & Examples](./search-capabilities.md)
- Tool-specific references:
  - **[Attachment Search Guide](./attachment-search.md)**
  - **[Hierarchy Search Guide](./hierarchy-search.md)**

## Prerequisites

- Ingestion completed at least once with `qdrant-loader ingest`
- QDrant reachable from your MCP runtime
- LLM provider configured

Configuration references:

- **[LLM Provider Guide](../../configuration/llm-provider-guide.md)**
- **[Environment Variables Reference](../../configuration/environment-variables.md)**

## Quick run

```bash
mcp-qdrant-loader
```

For production transport and worker tuning, use [Setup & Integration Guide](./setup-and-integration.md).
