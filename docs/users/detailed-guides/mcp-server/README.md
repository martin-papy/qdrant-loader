# MCP Server Guide

This page is the MCP hub. Detailed instructions are split into dedicated pages to avoid duplicate setup content.

## What MCP gives you

- Semantic search in your ingested knowledge base
- Hierarchy-aware retrieval for structured docs
- Attachment-focused search
- Integration with Cursor, Windsurf, Claude Desktop, and other MCP clients

## Canonical pages

- Setup and client integration: [setup-and-integration.md](./setup-and-integration.md)
- Tool capabilities and examples: [search-capabilities.md](./search-capabilities.md)
- Tool-specific references:
  - [attachment-search.md](./attachment-search.md)
  - [hierarchy-search.md](./hierarchy-search.md)

## Prerequisites

- Ingestion completed at least once with `qdrant-loader ingest`
- QDrant reachable from your MCP runtime
- LLM provider configured

Configuration references:

- [../../configuration/llm-provider-guide.md](../../configuration/llm-provider-guide.md)
- [../../configuration/environment-variables.md](../../configuration/environment-variables.md)

## Quick run

```bash
mcp-qdrant-loader
```

For production transport and worker tuning, use [setup-and-integration.md](./setup-and-integration.md).
