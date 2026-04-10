# <img src="/assets/icons/library/note-icon.svg" width="32" alt="MCP icon"> MCP Server Guide

This page is the MCP hub. Detailed instructions are split into dedicated pages to avoid duplicate setup content.

## <img src="/assets/icons/library/rocket-icon.svg" width="32" alt="Rocket icon"> What MCP gives you

- Semantic search in your ingested knowledge base
- Hierarchy-aware retrieval for structured docs
- Attachment-focused search
- Integration with Cursor, Windsurf, Claude Desktop, and other MCP clients

## <img src="/assets/icons/library/setting-icon.svg" width="32" alt="Client config"> Client configuration links

- Cursor, Windsurf, Claude Desktop setup: [Setup & Integration Guide](./setup-and-integration.md)
- Search tool capabilities and parameters: [Search Capabilities & Examples](./search-capabilities.md)
- Attachment-specific search details: [Attachment Search Guide](./attachment-search.md)
- Hierarchy-specific search details: [Hierarchy Search Guide](./hierarchy-search.md)
- Install and platform notes: [Installation Guide](../../../getting-started/installation.md)

## <img src="/assets/icons/library/target-icon.svg" width="32" alt="Target icon"> Prerequisites

- Ingestion completed at least once with `qdrant-loader ingest`
- QDrant reachable from your MCP runtime
- LLM provider configured

Configuration references:

- **[LLM Provider Guide](../../configuration/llm-provider-guide.md)** - Provider-specific setup for embeddings/chat compatibility with MCP.
- **[Environment Variables Reference](../../configuration/environment-variables.md)** - Required runtime variables for authentication, logging, and server behavior.

## <img src="../../../assets/icons/library/thunder-icon.svg" width="32" alt="Thunder icon"> Quick run

```bash
mcp-qdrant-loader
```

For production transport and worker tuning, use [Setup & Integration Guide](./setup-and-integration.md).

## <img src="/assets/icons/library/search-icon.svg" width="32" alt="Search strategy"> Multi-Tool Search Strategies

### Complete feature investigation

1. Start with **Semantic Search** to understand the topic.
2. Use **Hierarchy Search** to explore document structure.
3. Apply **Relationship Analysis** to map dependencies.
4. Use **Conflict Detection** to identify inconsistencies.

### Documentation quality audit

1. Use **Hierarchy Search** for structure and gap analysis.
2. Use **Conflict Detection** for inconsistency checks.
3. Use **Similarity Detection** to review duplication.
4. Use **Complementary Content** to assess completeness.

### Implementation planning

1. Use **Semantic Search** for patterns and examples.
2. Use **Complementary Content** for supporting references.
3. Use **Relationship Analysis** for dependency understanding.
4. Use **Clustering** to organize related materials.

## <img src="/assets/icons/library/rocket-icon.svg" width="32" alt="Performance"> Performance Optimization

### Search efficiency

- Use specific queries instead of broad terms.
- Apply source/type filters when appropriate.
- Use practical limits for cross-document analysis.

### Result quality

- Provide context in your query.
- Prefer natural language for semantic retrieval.
- Combine tools to improve coverage and precision.

## <img src="/assets/icons/library/search-icon.svg" width="32" alt="Validation icon"> Quick validation

In Cursor/Claude/Windsurf, ask a simple query like:

"Find setup notes for QDrant Loader in my ingested docs"

If the tool returns results from your indexed content, MCP integration is working.

## <img src="/assets/icons/library/test-tube-icon.svg" width="32" alt="Checklist"> Integration Checklist

### Setup requirements

- [ ] **QDrant Loader** installed and configured
- [ ] **Documents ingested** into QDrant
- [ ] **MCP server package** installed
- [ ] **AI tool** with MCP support (Cursor/Windsurf/Claude)
- [ ] **LLM API key** configured

### Configuration

- [ ] MCP server added to client config
- [ ] Environment variables set correctly
- [ ] Collection name matches ingested content
- [ ] Connection verified from AI tool

### Functionality testing

- [ ] Basic semantic search works
- [ ] Hierarchy search navigates structure
- [ ] Attachment search returns expected files
- [ ] Cross-document analysis returns relationships
- [ ] Performance is acceptable for daily usage

### Team deployment

- [ ] Configuration standardized across team
- [ ] Best practices documented and shared
- [ ] Security considerations reviewed
- [ ] Troubleshooting procedures documented

## <img src="/assets/icons/library/wrench-icon.svg" width="32" alt="Troubleshooting icon"> Troubleshooting paths

- MCP setup/runtime issues: [Setup & Integration Guide](./setup-and-integration.md)
- Search behavior and tool semantics: [Search Capabilities & Examples](./search-capabilities.md)
- General configuration issues: [Troubleshooting Guide](../../troubleshooting/)
