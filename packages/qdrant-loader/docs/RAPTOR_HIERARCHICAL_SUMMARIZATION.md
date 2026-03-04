# RAPTOR: Hierarchical Summarization for RAG

## Overview

**RAPTOR** (Recursive Abstractive Processing for Tree-Organized Retrieval) is a state-of-the-art technique for building pre-computed summary trees over document collections. Instead of summarizing at query time (expensive, slow), RAPTOR builds a multi-level summary hierarchy at **ingestion time**.

> **Key Insight**: Build the summary tree ONCE when documents are ingested. Query-time summarization becomes instant retrieval.

**Paper**: [RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval](https://arxiv.org/abs/2401.18059) (Wu et al., 2024 - Stanford/Meta)

---

## Why Not Just Map-Reduce at Query Time?

| Approach | Cost per Query | Latency | Quality |
|----------|---------------|---------|---------|
| Bulk retrieval → Map-Reduce | $5-10 (500+ LLM calls) | 30-60s | ❌ Noisy, redundant |
| RAPTOR (pre-built tree) | ~$0.01 (retrieval only) | <1s | ✅ Clean, deduplicated |

**The problem with query-time map-reduce:**
- You pay to summarize the same content repeatedly
- Redundant chunks get summarized multiple times
- Irrelevant chunks (boilerplate, noise) waste tokens
- Users wait 30-60 seconds for every summary request

---

## How RAPTOR Works

### The Tree Structure

```
                    ┌─────────────────┐
                    │  Root Summary   │  ← Level 3: Executive overview
                    │  (~200 tokens)  │     "This project covers..."
                    └────────┬────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
    ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐
    │  Cluster A  │   │  Cluster B  │   │  Cluster C  │  ← Level 2: Topic summaries
    │  "Security  │   │  "Deploy-   │   │  "API       │     (~10 nodes)
    │   & Auth"   │   │   ment"     │   │   Design"   │
    └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
           │                 │                 │
     ┌─────┴─────┐     ┌─────┴─────┐     ┌─────┴─────┐
     ▼           ▼     ▼           ▼     ▼           ▼
   ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐  ← Level 1: Section summaries
   │   │ │   │ │   │ │   │ │   │ │   │ │   │ │   │ │   │     (~50 nodes)
   └─┬─┘ └─┬─┘ └─┬─┘ └─┬─┘ └─┬─┘ └─┬─┘ └─┬─┘ └─┬─┘ └─┬─┘
     │     │     │     │     │     │     │     │     │
   ┌─┴─┐ ┌─┴─┐ ┌─┴─┐ ┌─┴─┐ ┌─┴─┐ ┌─┴─┐ ┌─┴─┐ ┌─┴─┐ ┌─┴─┐  ← Level 0: Original chunks
   │c1 │ │c2 │ │c3 │ │...│ │...│ │...│ │...│ │...│ │cN │     (your existing chunks)
   └───┘ └───┘ └───┘ └───┘ └───┘ └───┘ └───┘ └───┘ └───┘
```

### Key Properties

1. **All nodes are embedded** - Every summary at every level gets a vector embedding
2. **All nodes are searchable** - Semantic search works across ALL levels
3. **Automatic resolution** - Query complexity determines which level responds

---

## Is This Only for Structured Documents (like RFPs)?

### **NO! RAPTOR is structure-agnostic.**

RAPTOR uses **semantic clustering**, not document structure. It works on ANY content:

| Content Type | How RAPTOR Handles It |
|--------------|----------------------|
| **RFP Documents** | Clusters naturally form around: requirements, timeline, budget, evaluation |
| **Code Repositories** | Clusters form around: authentication, database, API routes, utilities |
| **Confluence Wikis** | Clusters form around: topics, projects, teams, processes |
| **Research Papers** | Clusters form around: methodology, results, related work, conclusions |
| **Mixed Content** | Clustering finds natural topic boundaries regardless of source |

### The Magic of Semantic Clustering

```python
# RAPTOR doesn't look at document structure
# It looks at MEANING via embeddings

chunks = [
    "OAuth2 flow starts with redirect...",      # → Auth cluster
    "JWT tokens expire after 24 hours...",      # → Auth cluster
    "Deploy using kubectl apply...",            # → Deployment cluster
    "API rate limits are 100 req/min...",       # → API cluster
    "Authentication requires valid token...",   # → Auth cluster (grouped with related!)
]

# Clustering by embedding similarity automatically groups related content
# regardless of which document or section it came from
```

---

## Integration with qdrant-loader

### Current Pipeline (Existing)

```
Document → File Conversion → Chunking → Embedding → Qdrant
```

### With RAPTOR (Proposed)

```
Document → File Conversion → Chunking → Embedding → Qdrant
                                              ↓
                                    [NEW] RAPTOR Tree Builder
                                              ↓
                                    Level 1 Summaries → Embed → Qdrant
                                              ↓
                                    Level 2 Summaries → Embed → Qdrant
                                              ↓
                                    Root Summary → Embed → Qdrant
```

### Storage Schema

Each RAPTOR node stored with metadata:

```python
{
    "id": "raptor_node_abc123",
    "text": "This cluster covers authentication and authorization...",
    "vector": [0.1, 0.2, ...],  # Embedded summary
    "metadata": {
        "raptor_level": 2,           # 0=chunk, 1=section, 2=topic, 3=root
        "raptor_parent_id": "raptor_node_xyz789",
        "raptor_children_ids": ["chunk_1", "chunk_2", "chunk_3"],
        "project_id": "PROJECT-123",
        "document_ids": ["doc_1", "doc_2"],  # Source documents
        "source_type": "raptor_summary",
        "cluster_topic": "Authentication & Authorization",  # LLM-generated label
    }
}
```

---

## Query Patterns

### 1. Quick Overview (Root Level)

```python
# User: "Summarize this project"
results = search(
    query="project overview summary",
    filter={"raptor_level": 3, "project_id": "X"},
    limit=1
)
# Returns: Pre-computed root summary, instant
```

### 2. Topic Exploration (Mid Level)

```python
# User: "What does this project say about security?"
results = search(
    query="security authentication authorization",
    filter={"raptor_level": [1, 2], "project_id": "X"},
    limit=5
)
# Returns: Relevant topic/section summaries
```

### 3. Detailed Facts (All Levels)

```python
# User: "What is the JWT expiration time?"
results = search(
    query="JWT token expiration timeout",
    filter={"project_id": "X"},  # Search all levels
    limit=10
)
# Returns: Mix of chunks and summaries, best match wins
```

### 4. Multi-Resolution (Collapse/Expand)

```python
# Start with overview
overview = search(query="...", filter={"raptor_level": 3})

# User wants more detail on a topic
details = search(
    query="...",
    filter={"raptor_parent_id": overview[0].id}  # Get children
)
```

---

## Algorithm Details

### Phase 1: Clustering

```python
from sklearn.mixture import GaussianMixture

def cluster_nodes(embeddings, target_clusters=None):
    """
    Use Gaussian Mixture Model for soft clustering.
    Allows nodes to belong to multiple clusters (important for cross-cutting concerns).
    """
    if target_clusters is None:
        # Heuristic: sqrt(n) clusters, min 2, max 20
        target_clusters = max(2, min(20, int(len(embeddings) ** 0.5)))
    
    gmm = GaussianMixture(n_components=target_clusters, covariance_type='full')
    gmm.fit(embeddings)
    
    # Soft assignment - each node can contribute to multiple clusters
    probabilities = gmm.predict_proba(embeddings)
    
    # Assign to clusters where probability > threshold
    threshold = 0.1
    assignments = []
    for i, probs in enumerate(probabilities):
        for cluster_id, prob in enumerate(probs):
            if prob > threshold:
                assignments.append((i, cluster_id, prob))
    
    return assignments
```

### Phase 2: Summarization

```python
def summarize_cluster(chunks, cluster_topic=None):
    """
    Generate abstractive summary for a cluster of related chunks.
    """
    combined_text = "\n\n---\n\n".join([c.text for c in chunks])
    
    prompt = f"""Summarize the following related content into a coherent paragraph.
Focus on the key information and main points.
Remove redundancy and preserve important details.

Content:
{combined_text}

Summary:"""
    
    summary = llm.generate(prompt, max_tokens=500)
    
    # Optionally generate a topic label
    if cluster_topic is None:
        topic_prompt = f"In 3-5 words, what topic does this cover?\n\n{summary}"
        cluster_topic = llm.generate(topic_prompt, max_tokens=20)
    
    return summary, cluster_topic
```

### Phase 3: Recursive Tree Building

```python
def build_raptor_tree(chunks, project_id):
    """
    Recursively build summary tree from bottom up.
    """
    tree_levels = [chunks]  # Level 0 = original chunks
    current_level = chunks
    level_num = 0
    
    while len(current_level) > 1:
        level_num += 1
        
        # 1. Get embeddings for current level
        embeddings = [get_embedding(node.text) for node in current_level]
        
        # 2. Cluster similar nodes
        clusters = cluster_nodes(embeddings)
        
        # 3. Group nodes by cluster
        cluster_groups = defaultdict(list)
        for node_idx, cluster_id, weight in clusters:
            cluster_groups[cluster_id].append((current_level[node_idx], weight))
        
        # 4. Summarize each cluster
        next_level = []
        for cluster_id, nodes_with_weights in cluster_groups.items():
            nodes = [n for n, w in nodes_with_weights]
            summary_text, topic = summarize_cluster(nodes)
            
            summary_node = RaptorNode(
                text=summary_text,
                level=level_num,
                children=[n.id for n in nodes],
                topic=topic,
                project_id=project_id,
            )
            summary_node.embedding = get_embedding(summary_text)
            next_level.append(summary_node)
        
        tree_levels.append(next_level)
        current_level = next_level
        
        # Stop if we're down to a single root
        if len(current_level) <= 1:
            break
    
    return tree_levels
```

---

## Cost Analysis

### One-Time Ingestion Cost (per project)

| Step | LLM Calls | Tokens | Cost (GPT-4) |
|------|-----------|--------|--------------|
| Level 0 → Level 1 | ~50 | ~25,000 | ~$0.75 |
| Level 1 → Level 2 | ~10 | ~5,000 | ~$0.15 |
| Level 2 → Level 3 | ~1 | ~500 | ~$0.015 |
| **Total** | **~61** | **~30,500** | **~$0.92** |

### Query-Time Cost

| Query Type | LLM Calls | Cost |
|------------|-----------|------|
| Get summary | 0 | $0.00 |
| Semantic search | 0 | $0.00 |
| Synthesis (optional) | 1 | ~$0.03 |

### Break-Even Analysis

```
Without RAPTOR: $5/query × N queries
With RAPTOR: $0.92 (one-time) + $0.03/query × N queries

Break-even at N = 0.92 / (5 - 0.03) ≈ 0.19 queries

After just 1 query, RAPTOR is more cost-effective!
```

---

## Configuration Options

```yaml
# qdrant-loader config (proposed)
raptor:
  enabled: true
  
  # Clustering settings
  clustering:
    method: "gmm"              # gmm, kmeans, hdbscan
    min_clusters: 2
    max_clusters: 20
    soft_clustering: true      # Allow nodes in multiple clusters
    probability_threshold: 0.1
  
  # Tree settings
  tree:
    max_levels: 4              # 0=chunks, 1-3=summaries
    min_nodes_for_level: 3     # Don't create level if < 3 nodes
  
  # Summarization settings
  summarization:
    model: "gpt-4o-mini"       # Cost-effective for summarization
    max_tokens: 500
    generate_topic_labels: true
  
  # Storage settings
  storage:
    store_all_levels: true     # Store all levels in Qdrant
    separate_collection: false # Store in same collection with metadata filter
```

---

## Use Cases

### 1. RFP Document Summarization
- Ingest RFP documents → RAPTOR tree built automatically
- Query: "Summarize requirements" → Instant Level 2-3 summaries
- Query: "What's the budget?" → Relevant Level 1 chunks

### 2. Codebase Understanding
- Ingest repository → Clusters form around modules/features
- Query: "How does authentication work?" → Auth cluster summary
- Query: "Show me the login flow" → Detailed auth chunks

### 3. Knowledge Base Q&A
- Ingest Confluence/docs → Topic clusters emerge
- Query: "Onboarding process" → Process summary
- Query: "Specific step 3 details" → Detailed chunks

### 4. Research Paper Analysis
- Ingest papers → Methodology, results, conclusions clusters
- Query: "What methods were used?" → Methods cluster summary
- Query: "Statistical significance?" → Detailed results chunks

---

## Comparison with Alternatives

| Approach | Ingestion Cost | Query Cost | Query Latency | Quality |
|----------|---------------|------------|---------------|---------|
| No summarization | $0 | N/A | N/A | N/A |
| Query-time map-reduce | $0 | $5-10 | 30-60s | Medium |
| Query-time clustering | $0 | $2-5 | 15-30s | Good |
| **RAPTOR (pre-built)** | **$1** | **$0-0.03** | **<1s** | **Best** |

---

## Implementation Roadmap

### Phase 1: Core Tree Builder
- [ ] Implement clustering service (GMM-based)
- [ ] Implement summarization service
- [ ] Implement recursive tree builder
- [ ] Store RAPTOR nodes in Qdrant with metadata

### Phase 2: Query Integration
- [ ] Add `raptor_level` filter to search tools
- [ ] Add `get_summary` tool for direct summary retrieval
- [ ] Add `expand_summary` tool for drilling down

### Phase 3: Configuration & Optimization
- [ ] Add RAPTOR config to workspace settings
- [ ] Implement incremental updates (new docs → update tree)
- [ ] Add caching for frequently accessed summaries

---

## References

1. [RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval](https://arxiv.org/abs/2401.18059)
2. [LlamaIndex RAPTOR Implementation](https://docs.llamaindex.ai/en/stable/examples/retrievers/raptor_retriever/)
3. [LangChain RAPTOR Guide](https://python.langchain.com/docs/tutorials/raptor/)

---

## Summary

**RAPTOR transforms "I need to summarize everything" from an expensive query-time operation into a cheap pre-computed retrieval.**

- ✅ Works on ANY content (not just structured documents)
- ✅ Clusters by semantic similarity (automatic topic discovery)
- ✅ Multi-resolution queries (overview → details)
- ✅ 100-500x cheaper than query-time map-reduce
- ✅ <1s latency vs 30-60s

**The app team's map-reduce approach is doing the right thing (hierarchical summarization) at the wrong time (query time). RAPTOR does it at ingestion time.**
