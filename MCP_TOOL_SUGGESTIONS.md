# MCP Tool Suggestions & Implementation Guide

## Current Status: LLM Capabilities

**✅ YES - The system has LLM capabilities:**

1. **LLM Provider Abstraction** (`qdrant-loader-core`)
   - Supports OpenAI, Azure OpenAI, Ollama, custom endpoints
   - Unified `ChatClient` and `EmbeddingsClient` interfaces
   - Configured via `global.llm` in config.yaml

2. **Current LLM Usage:**
   - ✅ **Embeddings**: OpenAI/LLM for vector embeddings (required)
   - ✅ **Conflict Detection**: Optional LLM validation for document conflicts
   - ✅ **Chat Completions**: Available via `ChatClient` from core provider

3. **LLM NOT Currently Used For:**
   - ❌ Query expansion/refinement (uses spaCy instead)
   - ❌ Result explanation/justification
   - ❌ Reranking (placeholder - identity function)
   - ❌ Query intent classification (uses spaCy NLP)

**LLM Access Pattern:**
```python
# From codebase
from qdrant_loader_core.llm.providers import LLMProvider
provider = LLMProvider.from_settings(settings)
chat_client = provider.chat()  # Available for LLM-based tools
```

---

## Current 10 Tools Status

### ✅ Complete Tools (8/10)

1. **`search`** - Universal semantic search
   - Status: ✅ Fully implemented
   - Features: Vector + keyword hybrid search, filtering, caching

2. **`hierarchy_search`** - Structure-aware search
   - Status: ✅ Fully implemented
   - Features: Confluence hierarchy navigation, parent-child relationships

3. **`attachment_search`** - File attachment search
   - Status: ✅ Fully implemented
   - Features: File type filtering, content extraction, parent document context

4. **`analyze_relationships`** - Document relationship analysis
   - Status: ✅ Fully implemented
   - Features: Multi-metric similarity, relationship types, confidence scores

5. **`find_similar_documents`** - Similarity detection
   - Status: ✅ Fully implemented
   - Features: Multi-metric comparison, similarity thresholds, reason explanations

6. **`detect_document_conflicts`** - Conflict detection
   - Status: ✅ Fully implemented
   - Features: Vector similarity + optional LLM validation, contradiction detection

7. **`find_complementary_content`** - Complementary content discovery
   - Status: ✅ Fully implemented
   - Features: Gap analysis, recommendation scoring, context-aware suggestions

8. **`cluster_documents`** - Document clustering
   - Status: ✅ Fully implemented
   - Features: Multiple clustering strategies, theme extraction, relationship mapping

### ⚠️ Placeholders/Incomplete (2/10)

9. **`expand_cluster`** - Cluster expansion for lazy loading
   - **Status**: 🔴 **PLACEHOLDER**
   - **Location**: `intelligence_handler.py:747`
   - **Issue**: Returns message saying "cluster expansion requires re-running clustering operation"
   - **Current Behavior**: No cluster caching/persistence; must re-cluster to expand
   - **Fix Needed**: Implement cluster data persistence/caching layer

10. **`expand_document`** - Document expansion for lazy loading
    - **Status**: 🟡 **WORKAROUND IMPLEMENTATION**
    - **Location**: `search_handler.py:417`
    - **Issue**: Uses search query `document_id:{id}` instead of direct Qdrant point retrieval
    - **Current Behavior**: Works but inefficient (searches then filters for exact match)
    - **Fix Needed**: Use Qdrant's direct point retrieval API (`retrieve()` method)

### Additional Incomplete Component

- **`HybridReranker`** - Reranking component
  - **Status**: 🔴 **PLACEHOLDER**
  - **Location**: `search/hybrid/components/reranking.py:12`
  - **Issue**: Identity function (returns results unchanged)
  - **Current Behavior**: Pipeline supports reranking but doesn't actually rerank
  - **Fix Needed**: Implement LLM-based or cross-encoder reranking

---

## Suggested New Tools

### 🔥 High Priority (Immediate Value)

#### 1. `refine_query` / `expand_query`

**Purpose**: Intelligent query expansion and refinement

**Use Cases**:
- "Find authentication docs" → expands to "auth, login, credentials, OAuth, JWT, SSO"
- "API documentation" → expands to "REST API, endpoints, swagger, OpenAPI"
- Multi-language support: "authentication" → "autenticación, authentification"

**Implementation**:
```python
async def refine_query(query: str, expansion_type: str = "semantic") -> dict:
    """
    expansion_type: "semantic" | "synonym" | "multilingual" | "llm"
    """
    if expansion_type == "llm":
        # Use LLM to expand query
        prompt = f"Expand this search query with related terms: {query}"
        expanded = await chat_client.chat(messages=[{"role": "user", "content": prompt}])
        return {"original": query, "expanded": expanded, "terms": extract_terms(expanded)}
    elif expansion_type == "semantic":
        # Use embedding similarity to find related terms
        # Query existing documents for similar terms
        pass
```

**LLM Required**: ✅ Yes (for semantic expansion)
**Complexity**: Medium
**Value**: High (improves search recall)

---

#### 2. `explain_results` / `result_justification`

**Purpose**: Explain why specific results were returned for a query

**Use Cases**:
- "Why is document X relevant to query Y?"
- "What makes this result match my search?"
- Transparency in search results

**Implementation**:
```python
async def explain_result(query: str, document_id: str) -> dict:
    # Get document
    doc = await search_engine.get_document(document_id)
    
    # Use LLM to explain relevance
    prompt = f"""
    Query: {query}
    Document: {doc.text[:1000]}
    
    Explain why this document is relevant to the query.
    Highlight specific passages, concepts, or keywords that match.
    """
    explanation = await chat_client.chat(messages=[{"role": "user", "content": prompt}])
    
    return {
        "document_id": document_id,
        "query": query,
        "explanation": explanation,
        "matching_passages": extract_passages(doc, query),
        "similarity_score": calculate_similarity(query, doc)
    }
```

**LLM Required**: ✅ Yes
**Complexity**: Low-Medium
**Value**: High (improves trust and transparency)

---

#### 3. `conversational_search` / `contextual_search`

**Purpose**: Multi-turn search with conversation history

**Use Cases**:
- User: "Find authentication docs"
- User: "What about the API version?" (follow-up)
- User: "Show me examples" (follow-up)

**Implementation**:
```python
class ConversationContext:
    def __init__(self):
        self.history: list[dict] = []
        self.current_topic: str = ""
        self.previous_results: list = []
    
    async def search_with_context(self, query: str, context: ConversationContext) -> dict:
        # Rewrite query with context
        if context.history:
            rewritten_query = await self._rewrite_query_with_context(query, context)
        else:
            rewritten_query = query
        
        # Perform search
        results = await search_engine.search(rewritten_query)
        
        # Update context
        context.history.append({"query": query, "results": results})
        context.current_topic = extract_topic(query)
        
        return {"results": results, "rewritten_query": rewritten_query, "context_used": bool(context.history)}
    
    async def _rewrite_query_with_context(self, query: str, context: ConversationContext) -> str:
        prompt = f"""
        Previous conversation:
        {format_history(context.history[-3:])}
        
        Current query: {query}
        
        Rewrite the current query to include context from previous questions.
        """
        rewritten = await chat_client.chat(messages=[{"role": "user", "content": prompt}])
        return rewritten
```

**LLM Required**: ✅ Yes (for query rewriting)
**Complexity**: Medium
**Value**: High (better UX for iterative exploration)

---

#### 4. `temporal_search` / `time_filtered_search`

**Purpose**: Filter and rank by temporal information

**Use Cases**:
- "Find documentation updated in last 6 months"
- "Show me recent changes to API"
- "What's the latest version of this spec?"

**Implementation**:
```python
async def temporal_search(
    query: str,
    date_range: dict = None,  # {"start": "2024-01-01", "end": "2024-12-31"}
    sort_by: str = "recent"  # "recent" | "oldest" | "relevance"
) -> dict:
    # Extract date metadata from documents
    # Filter by date range
    # Rank by temporal relevance
    results = await search_engine.search(query, limit=100)
    
    if date_range:
        filtered = filter_by_date(results, date_range)
    else:
        filtered = results
    
    if sort_by == "recent":
        sorted_results = sort_by_date(filtered, descending=True)
    elif sort_by == "oldest":
        sorted_results = sort_by_date(filtered, descending=False)
    else:
        sorted_results = filtered  # Keep relevance ranking
    
    return {
        "results": sorted_results,
        "date_range_applied": date_range,
        "temporal_metadata": extract_temporal_info(sorted_results)
    }
```

**LLM Required**: ❌ No (metadata filtering)
**Complexity**: Low-Medium
**Value**: Medium-High (important for documentation freshness)

---

### 📊 Medium Priority (Nice to Have)

#### 5. `batch_search`

**Purpose**: Search multiple queries in parallel

**Use Cases**:
- Process multiple questions at once
- Compare results across queries
- Bulk search operations

**Implementation**:
```python
async def batch_search(queries: list[str], limit_per_query: int = 5) -> dict:
    # Execute searches in parallel
    tasks = [search_engine.search(q, limit=limit_per_query) for q in queries]
    results_list = await asyncio.gather(*tasks)
    
    return {
        "queries": queries,
        "results": [
            {"query": q, "results": r, "count": len(r)}
            for q, r in zip(queries, results_list)
        ],
        "total_results": sum(len(r) for r in results_list)
    }
```

**LLM Required**: ❌ No
**Complexity**: Low
**Value**: Medium (efficiency improvement)

---

#### 6. `search_analytics` / `search_metrics`

**Purpose**: Track search patterns and quality metrics

**Use Cases**:
- "What are users searching for most?"
- "Which queries return no results?"
- "What's the average result quality?"

**Implementation**:
```python
class SearchAnalytics:
    def __init__(self):
        self.query_log: list[dict] = []
        self.result_quality: dict = {}
    
    async def get_analytics(
        self,
        time_range: dict = None,
        metrics: list[str] = ["popular_queries", "no_result_queries", "avg_result_count"]
    ) -> dict:
        # Aggregate query logs
        # Calculate metrics
        return {
            "popular_queries": self._get_popular_queries(time_range),
            "no_result_queries": self._get_no_result_queries(time_range),
            "avg_result_count": self._get_avg_result_count(time_range),
            "query_trends": self._get_query_trends(time_range)
        }
```

**LLM Required**: ❌ No
**Complexity**: Medium
**Value**: Medium (insights for improvement)

---

#### 7. `relevance_feedback`

**Purpose**: Learn from user feedback to improve ranking

**Use Cases**:
- User marks result as "relevant" or "not relevant"
- System learns preferences
- Future searches improve based on feedback

**Implementation**:
```python
class RelevanceFeedback:
    def __init__(self):
        self.feedback_store: dict = {}  # query -> {doc_id: feedback}
    
    async def submit_feedback(
        self,
        query: str,
        document_id: str,
        feedback: str  # "relevant" | "not_relevant" | "somewhat_relevant"
    ) -> dict:
        # Store feedback
        if query not in self.feedback_store:
            self.feedback_store[query] = {}
        self.feedback_store[query][document_id] = feedback
        
        # Update ranking weights (optional)
        await self._update_ranking_weights(query, document_id, feedback)
        
        return {"status": "feedback_recorded", "query": query, "document_id": document_id}
    
    async def search_with_feedback(self, query: str) -> dict:
        # Get base results
        results = await search_engine.search(query)
        
        # Adjust scores based on feedback
        if query in self.feedback_store:
            feedback = self.feedback_store[query]
            for result in results:
                if result.document_id in feedback:
                    if feedback[result.document_id] == "relevant":
                        result.score *= 1.2  # Boost
                    elif feedback[result.document_id] == "not_relevant":
                        result.score *= 0.5  # Penalize
        
        return {"results": sorted(results, key=lambda x: x.score, reverse=True)}
```

**LLM Required**: ❌ No (but could use for learning patterns)
**Complexity**: Medium-High
**Value**: Medium (long-term improvement)

---

#### 8. `citation_tracker` / `source_attribution`

**Purpose**: Track information sources and citation chains

**Use Cases**:
- "Show me the source chain for this information"
- "What documents reference this document?"
- "Trace back to original source"

**Implementation**:
```python
async def get_citation_chain(document_id: str, direction: str = "both") -> dict:
    """
    direction: "forward" | "backward" | "both"
    """
    # Build citation graph
    # Forward: documents that reference this one
    # Backward: documents this one references
    
    doc = await search_engine.get_document(document_id)
    
    # Extract citations/references from document
    citations = extract_citations(doc.text)
    
    # Find referenced documents
    referenced_docs = []
    for citation in citations:
        ref_doc = await search_engine.find_document_by_citation(citation)
        if ref_doc:
            referenced_docs.append(ref_doc)
    
    # Find documents that reference this one
    referencing_docs = await search_engine.find_documents_referencing(document_id)
    
    return {
        "document_id": document_id,
        "citations": citations,
        "referenced_documents": referenced_docs,
        "referencing_documents": referencing_docs,
        "citation_graph": build_graph(document_id, referenced_docs, referencing_docs)
    }
```

**LLM Required**: ❌ No (but could use for citation extraction)
**Complexity**: Medium
**Value**: Medium (useful for research/documentation)

---

### 🚀 Advanced/Nice-to-Have

#### 9. `multi_modal_search`

**Purpose**: Search across text + images (if images are indexed)

**Use Cases**:
- "Find diagrams showing architecture"
- "Show me screenshots of the UI"
- "Find images with text about authentication"

**Implementation**:
```python
async def multi_modal_search(
    query: str,
    modalities: list[str] = ["text", "image"]  # "text" | "image" | "both"
) -> dict:
    # Text search
    text_results = await search_engine.search(query, filter_by_type="text")
    
    # Image search (if image embeddings available)
    if "image" in modalities:
        image_results = await search_engine.search_images(query)
    else:
        image_results = []
    
    # Combine results
    return {
        "text_results": text_results,
        "image_results": image_results,
        "combined_results": merge_results(text_results, image_results)
    }
```

**LLM Required**: ❌ No (but needs image embeddings)
**Complexity**: High (requires image embedding pipeline)
**Value**: Low-Medium (depends on image indexing)

---

#### 10. `query_classification` / `intent_detection`

**Purpose**: Classify query intent and route to appropriate strategy

**Use Cases**:
- "How do I..." → how-to intent → tutorial-focused search
- "What is..." → factual intent → definition-focused search
- "Why doesn't..." → troubleshooting intent → error-focused search

**Implementation**:
```python
async def classify_query_intent(query: str) -> dict:
    prompt = f"""
    Classify this search query into one of these intents:
    - factual: Seeking definitions, facts, explanations
    - how_to: Seeking instructions, tutorials, guides
    - troubleshooting: Seeking solutions to problems, errors
    - comparison: Seeking comparisons between options
    - code_example: Seeking code samples, implementations
    
    Query: {query}
    
    Return JSON: {{"intent": "...", "confidence": 0.0-1.0, "reasoning": "..."}}
    """
    
    response = await chat_client.chat(messages=[{"role": "user", "content": prompt}])
    classification = parse_json(response)
    
    # Route to appropriate search strategy
    if classification["intent"] == "how_to":
        # Use tutorial-focused search
        results = await search_engine.search(query, boost_tutorials=True)
    elif classification["intent"] == "troubleshooting":
        # Use error-focused search
        results = await search_engine.search(query, boost_error_docs=True)
    else:
        results = await search_engine.search(query)
    
    return {
        "intent": classification["intent"],
        "confidence": classification["confidence"],
        "results": results,
        "strategy_used": classification["intent"]
    }
```

**LLM Required**: ✅ Yes
**Complexity**: Medium
**Value**: Medium (improves search precision)

---

#### 11. `semantic_aggregation` / `answer_synthesis`

**Purpose**: Synthesize answers from multiple documents

**Use Cases**:
- "What is our authentication approach?" → combines multiple docs into coherent answer
- "How does the system work?" → synthesizes architecture docs
- "What are the deployment steps?" → combines multiple guides

**Implementation**:
```python
async def synthesize_answer(query: str, max_documents: int = 5) -> dict:
    # Get top results
    results = await search_engine.search(query, limit=max_documents)
    
    # Extract relevant passages
    passages = []
    for result in results:
        relevant_passages = extract_relevant_passages(result.text, query)
        passages.extend(relevant_passages)
    
    # Use LLM to synthesize
    prompt = f"""
    Query: {query}
    
    Relevant passages from multiple documents:
    {format_passages(passages)}
    
    Synthesize a comprehensive answer to the query using information from these passages.
    Cite sources where appropriate.
    """
    
    synthesized_answer = await chat_client.chat(
        messages=[{"role": "user", "content": prompt}],
        model="gpt-4"  # Use more capable model for synthesis
    )
    
    return {
        "query": query,
        "synthesized_answer": synthesized_answer,
        "source_documents": [r.document_id for r in results],
        "passages_used": len(passages)
    }
```

**LLM Required**: ✅ Yes
**Complexity**: Medium-High
**Value**: High (provides direct answers vs. just documents)

---

#### 12. `knowledge_graph_query`

**Purpose**: Query document relationships as a graph

**Use Cases**:
- "Show me all documents related to authentication"
- "What's the dependency chain for this feature?"
- "Find all documents that reference this API"

**Implementation**:
```python
async def query_knowledge_graph(
    start_document_id: str,
    relationship_type: str = "all",  # "all" | "references" | "similar" | "complementary"
    max_hops: int = 2,
    max_results: int = 20
) -> dict:
    # Build graph from document relationships
    graph = await build_document_graph()
    
    # Traverse graph
    if relationship_type == "all":
        neighbors = graph.get_all_neighbors(start_document_id, max_hops)
    elif relationship_type == "references":
        neighbors = graph.get_referencing_documents(start_document_id, max_hops)
    elif relationship_type == "similar":
        neighbors = graph.get_similar_documents(start_document_id, max_hops)
    else:
        neighbors = graph.get_complementary_documents(start_document_id, max_hops)
    
    return {
        "start_document": start_document_id,
        "relationship_type": relationship_type,
        "related_documents": neighbors[:max_results],
        "graph_visualization": graph.visualize(start_document_id, neighbors)
    }
```

**LLM Required**: ❌ No (but could enhance relationship detection)
**Complexity**: High (requires graph infrastructure)
**Value**: Medium (useful for exploration)

---

## Implementation Priority Matrix

| Tool | LLM Required | Complexity | Value | Priority |
|------|--------------|------------|-------|----------|
| `refine_query` | ✅ Yes | Medium | High | 🔥 P0 |
| `explain_results` | ✅ Yes | Low-Medium | High | 🔥 P0 |
| `conversational_search` | ✅ Yes | Medium | High | 🔥 P0 |
| `temporal_search` | ❌ No | Low-Medium | Medium-High | 🔥 P0 |
| `batch_search` | ❌ No | Low | Medium | 📊 P1 |
| `search_analytics` | ❌ No | Medium | Medium | 📊 P1 |
| `relevance_feedback` | ❌ No | Medium-High | Medium | 📊 P1 |
| `citation_tracker` | ❌ No | Medium | Medium | 📊 P1 |
| `query_classification` | ✅ Yes | Medium | Medium | 🚀 P2 |
| `semantic_aggregation` | ✅ Yes | Medium-High | High | 🚀 P2 |
| `multi_modal_search` | ❌ No | High | Low-Medium | 🚀 P2 |
| `knowledge_graph_query` | ❌ No | High | Medium | 🚀 P2 |

---

## Fix Priority for Existing Tools

1. **`expand_cluster`** - Implement cluster caching (P0)
2. **`HybridReranker`** - Implement LLM-based reranking (P0)
3. **`expand_document`** - Use direct Qdrant point retrieval (P1)

---

## Recommended Implementation Order

### Phase 1: Fix Existing Placeholders (1-2 weeks)
1. Fix `expand_cluster` (add cluster persistence)
2. Implement `HybridReranker` (LLM-based reranking)
3. Optimize `expand_document` (direct Qdrant retrieval)

### Phase 2: High-Value LLM Tools (2-3 weeks)
1. `explain_results` (easiest, high value)
2. `refine_query` (improves search quality)
3. `conversational_search` (better UX)

### Phase 3: Metadata & Analytics (1-2 weeks)
1. `temporal_search` (metadata filtering)
2. `search_analytics` (insights)

### Phase 4: Advanced Features (3-4 weeks)
1. `semantic_aggregation` (answer synthesis)
2. `query_classification` (intent routing)
3. `relevance_feedback` (learning system)

---

## Notes

- **LLM Availability**: System has full LLM access via `qdrant-loader-core` provider abstraction
- **Current LLM Usage**: Embeddings (required), conflict detection (optional)
- **LLM Not Used**: Query processing (uses spaCy), reranking (placeholder), result explanation (missing)
- **Opportunity**: Many high-value tools can leverage existing LLM infrastructure
