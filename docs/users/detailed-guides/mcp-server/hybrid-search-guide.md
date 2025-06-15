# Hybrid Search Guide

This guide provides comprehensive documentation for the hybrid search capabilities in the Qdrant Loader MCP Server, including query parameters, result schemas, usage patterns, and error handling.

## Table of Contents

1. [Overview](#overview)
2. [Search Modes](#search-modes)
3. [MCP Tool Interfaces](#mcp-tool-interfaces)
4. [Query Parameters](#query-parameters)
5. [Result Schema](#result-schema)
6. [Fusion Strategies](#fusion-strategies)
7. [Error Handling](#error-handling)
8. [Usage Examples](#usage-examples)
9. [Performance Considerations](#performance-considerations)
10. [Troubleshooting](#troubleshooting)

## Overview

The hybrid search system combines multiple search approaches to provide comprehensive and relevant results:

- **Vector Search**: Semantic similarity using OpenAI embeddings
- **Keyword Search**: Traditional text-based search with BM25 scoring
- **Graph Search**: Knowledge graph traversal using Neo4j and Graphiti
- **Result Fusion**: Advanced algorithms to combine and rank results

### Architecture

```text
Query → [Vector Search] → [Keyword Search] → [Graph Search] → [Fusion Engine] → [Reranking] → Results
```

## Search Modes

The system supports four search modes:

### 1. Vector Only (`vector_only`)

- Uses only semantic vector search
- Best for: Conceptual queries, finding similar content
- Performance: Fast, requires OpenAI API

### 2. Graph Only (`graph_only`)

- Uses only knowledge graph search
- Best for: Relationship queries, entity-focused searches
- Performance: Moderate, requires Neo4j/Graphiti

### 3. Hybrid (`hybrid`)

- Combines vector, keyword, and graph search
- Best for: Comprehensive search with balanced results
- Performance: Slower but most comprehensive

### 4. Auto (`auto`)

- Automatically selects the best mode based on query analysis
- Best for: General-purpose search when unsure of optimal mode
- Performance: Variable based on selected mode

## MCP Tool Interfaces

### Basic Search Tool

The `search` tool provides hybrid search capabilities with backward compatibility.

**Tool Name**: `search`

**Parameters**:

- `query` (required): Search query text
- `source_types` (optional): Filter by source types (`git`, `confluence`, `jira`, `documentation`, `localfile`)
- `project_ids` (optional): Filter by project IDs
- `limit` (optional): Maximum results (default: 5)

**Hybrid Parameters** (optional):

- `mode`: Search mode (`vector_only`, `graph_only`, `hybrid`, `auto`)
- `vector_weight`: Weight for vector results (0.0-1.0)
- `keyword_weight`: Weight for keyword results (0.0-1.0)
- `graph_weight`: Weight for graph results (0.0-1.0)
- `fusion_strategy`: Result fusion strategy (see [Fusion Strategies](#fusion-strategies))

### Hierarchy Search Tool

Enhanced Confluence search with hierarchy awareness.

**Tool Name**: `hierarchy_search`

**Additional Parameters**:

- `hierarchy_filter`: Filter by hierarchy properties
- `organize_by_hierarchy`: Group results by hierarchy structure

### Attachment Search Tool

Specialized search for file attachments.

**Tool Name**: `attachment_search`

**Additional Parameters**:

- `attachment_filter`: Filter by attachment properties
- `include_content`: Include attachment content in search

## Query Parameters

### Weight Parameters

When using hybrid search, you can control the influence of each search component:

```json
{
  "vector_weight": 0.5,    // 50% influence from semantic similarity
  "keyword_weight": 0.3,   // 30% influence from keyword matching
  "graph_weight": 0.2      // 20% influence from graph relationships
}
```

**Rules**:

- All weights must be between 0.0 and 1.0
- If all three weights are specified, they should sum to 1.0
- If only some weights are specified, the system will normalize them

### Mode Selection Guidelines

| Query Type | Recommended Mode | Reason |
|------------|------------------|---------|
| "What is machine learning?" | `vector_only` | Conceptual query benefits from semantic search |
| "Files related to user authentication" | `graph_only` | Relationship-focused query |
| "How to implement JWT tokens" | `hybrid` | Combines concepts and implementation details |
| "Show me recent changes" | `auto` | Let system decide based on query analysis |

## Result Schema

### Basic Result Structure

```json
{
  "content": [
    {
      "type": "text",
      "text": "Found 3 results:\n\nScore: 0.85\nText: Implementation details...\nSource: confluence - Authentication Guide\n🏗️ Project: web-app\n📍 Path: Development > Security > Authentication\n(https://confluence.example.com/auth-guide)"
    }
  ],
  "isError": false
}
```

### Result Components

Each result includes:

- **Score**: Relevance score (0.0-1.0)
- **Text**: Content excerpt
- **Source**: Source type and title
- **Project Info**: Project context (🏗️)
- **Hierarchy Path**: Navigation breadcrumb (📍)
- **URL**: Direct link to source
- **Metadata**: Additional context (attachments, children, etc.)

### Enhanced Result Information

For enhanced search results, additional metadata is available:

- **Search Type**: Which search components contributed
- **Component Scores**: Individual scores from vector, keyword, and graph search
- **Fusion Strategy**: Strategy used to combine results
- **Debug Info**: Performance and ranking details

## Fusion Strategies

The system supports seven fusion strategies for combining search results:

### 1. Weighted Sum (`weighted_sum`)

- **Description**: Simple weighted average of component scores
- **Best for**: Balanced results with predictable scoring
- **Performance**: Fast

### 2. Reciprocal Rank Fusion (`reciprocal_rank_fusion`)

- **Description**: Combines rankings using reciprocal rank formula
- **Best for**: When ranking order is more important than absolute scores
- **Performance**: Fast

### 3. Maximal Marginal Relevance (`maximal_marginal_relevance`)

- **Description**: Balances relevance with diversity to reduce redundancy
- **Best for**: Diverse result sets, avoiding duplicate content
- **Performance**: Moderate

### 4. Graph Enhanced Weighted (`graph_enhanced_weighted`)

- **Description**: Weighted sum with graph centrality boosting
- **Best for**: Emphasizing important entities and relationships
- **Performance**: Moderate

### 5. Confidence Adaptive (`confidence_adaptive`)

- **Description**: Adapts weights based on component confidence scores
- **Best for**: Queries where component reliability varies
- **Performance**: Moderate

### 6. Multi-Stage (`multi_stage`)

- **Description**: Multi-pass fusion with progressive refinement
- **Best for**: Complex queries requiring sophisticated ranking
- **Performance**: Slower but most sophisticated

### 7. Context Aware (`context_aware`)

- **Description**: Considers query context and user feedback
- **Best for**: Personalized or context-sensitive search
- **Performance**: Moderate

## Error Handling

The system provides robust error handling with specific error types and recovery strategies.

### Error Types

#### 1. Qdrant Connection Error (`QDRANT_CONNECTION_ERROR`)

- **Cause**: Cannot connect to Qdrant vector database
- **Recovery**: Check Qdrant server status and network connectivity
- **Fallback**: None (vector search unavailable)

#### 2. Qdrant Query Error (`QDRANT_QUERY_ERROR`)

- **Cause**: Invalid query or Qdrant server error
- **Recovery**: Retry with simplified query parameters
- **Fallback**: Graph-only search if available

#### 3. Neo4j Connection Error (`NEO4J_CONNECTION_ERROR`)

- **Cause**: Cannot connect to Neo4j graph database
- **Recovery**: Check Neo4j server status
- **Fallback**: Vector and keyword search continue to work

#### 4. Neo4j Query Error (`NEO4J_QUERY_ERROR`)

- **Cause**: Invalid Cypher query or Neo4j server error
- **Recovery**: Retry with simplified graph query
- **Fallback**: Vector-only search

#### 5. Graphiti Error (`GRAPHITI_ERROR`)

- **Cause**: Graphiti knowledge graph operation failed
- **Recovery**: Check Graphiti configuration
- **Fallback**: Basic hybrid search without knowledge graph

#### 6. OpenAI Embedding Error (`OPENAI_EMBEDDING_ERROR`)

- **Cause**: Failed to generate text embeddings
- **Recovery**: Check OpenAI API key and quota
- **Fallback**: Keyword and graph search only

#### 7. Search Configuration Error (`SEARCH_CONFIG_ERROR`)

- **Cause**: Invalid search parameters
- **Recovery**: Fix parameter values
- **Fallback**: None (user must correct parameters)

#### 8. Fusion Strategy Error (`FUSION_STRATEGY_ERROR`)

- **Cause**: Result fusion algorithm failed
- **Recovery**: Retry with default fusion strategy
- **Fallback**: Return unfused results

### Error Response Format

```json
{
  "jsonrpc": "2.0",
  "id": "request-123",
  "error": {
    "code": -32603,
    "message": "Vector database connection failed",
    "data": {
      "error_code": "QDRANT_CONNECTION_ERROR",
      "message": "Failed to connect to Qdrant server",
      "details": {
        "qdrant_url": "http://localhost:6333",
        "original_error": "Connection refused",
        "error_type": "ConnectionError"
      },
      "recoverable": true,
      "suggestion": "Please check if Qdrant server is running and accessible"
    }
  }
}
```

### Graceful Degradation

The system implements graceful degradation:

1. **Enhanced → Basic**: Falls back to basic hybrid search if enhanced features fail
2. **Hybrid → Vector**: Falls back to vector-only if graph components fail
3. **Vector → Error**: Returns error if vector search fails (required component)

## Usage Examples

### Basic Search

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "search",
    "arguments": {
      "query": "user authentication implementation",
      "limit": 5
    }
  },
  "id": "search-1"
}
```

### Hybrid Search with Custom Weights

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "search",
    "arguments": {
      "query": "JWT token validation",
      "mode": "hybrid",
      "vector_weight": 0.4,
      "keyword_weight": 0.4,
      "graph_weight": 0.2,
      "fusion_strategy": "reciprocal_rank_fusion",
      "limit": 10
    }
  },
  "id": "search-2"
}
```

### Hierarchy Search with Filtering

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "hierarchy_search",
    "arguments": {
      "query": "API documentation",
      "hierarchy_filter": {
        "depth": 2,
        "parent_title": "Development Guide"
      },
      "organize_by_hierarchy": true,
      "mode": "hybrid",
      "limit": 15
    }
  },
  "id": "search-3"
}
```

### Attachment Search

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "attachment_search",
    "arguments": {
      "query": "database schema",
      "attachment_filter": {
        "file_types": ["sql", "json"],
        "size_range": {"min": 1024, "max": 1048576}
      },
      "mode": "vector_only",
      "limit": 8
    }
  },
  "id": "search-4"
}
```

## Performance Considerations

### Search Mode Performance

| Mode | Speed | Accuracy | Resource Usage |
|------|-------|----------|----------------|
| `vector_only` | Fast | High for semantic queries | Low (OpenAI API only) |
| `graph_only` | Moderate | High for relationship queries | Moderate (Neo4j/Graphiti) |
| `hybrid` | Slower | Highest overall | High (all components) |
| `auto` | Variable | Adaptive | Variable |

### Optimization Tips

1. **Use appropriate limits**: Start with smaller limits (5-10) for faster responses
2. **Choose specific modes**: Use `vector_only` or `graph_only` when appropriate
3. **Filter by source types**: Reduce search space with `source_types` parameter
4. **Project filtering**: Use `project_ids` to limit scope
5. **Cache results**: The system includes built-in caching for repeated queries

### Fusion Strategy Performance

| Strategy | Speed | Quality | Use Case |
|----------|-------|---------|----------|
| `weighted_sum` | Fastest | Good | General purpose |
| `reciprocal_rank_fusion` | Fast | Good | Ranking-focused |
| `maximal_marginal_relevance` | Moderate | High diversity | Avoiding duplicates |
| `multi_stage` | Slowest | Highest | Complex queries |

## Troubleshooting

### Common Issues

#### 1. No Results Returned

**Symptoms**: Search returns empty results
**Causes**:

- Query too specific
- Filters too restrictive
- No indexed content matching query

**Solutions**:

- Broaden query terms
- Remove or relax filters
- Check if content is properly indexed

#### 2. Poor Result Quality

**Symptoms**: Irrelevant results returned
**Causes**:

- Inappropriate search mode
- Suboptimal weight configuration
- Wrong fusion strategy

**Solutions**:

- Try different search modes
- Adjust weight parameters
- Experiment with fusion strategies

#### 3. Slow Performance

**Symptoms**: Search takes too long
**Causes**:

- Complex fusion strategy
- Large result limits
- Multiple search components

**Solutions**:

- Use simpler fusion strategies
- Reduce result limits
- Use specific search modes instead of hybrid

#### 4. Connection Errors

**Symptoms**: Database connection failures
**Causes**:

- Service unavailability
- Network issues
- Configuration problems

**Solutions**:

- Check service status
- Verify network connectivity
- Review configuration settings

### Debug Information

Enable debug logging to get detailed information about:

- Search component performance
- Fusion strategy execution
- Error details and stack traces
- Cache hit/miss statistics

### Support

For additional support:

1. Check server logs for detailed error information
2. Verify all required services are running
3. Test with simpler queries to isolate issues
4. Review configuration settings
5. Contact system administrators for infrastructure issues
