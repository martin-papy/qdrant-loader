# Cross-Encoder Reranking A/B Evaluation Test Battery

This test suite provides a comprehensive framework for evaluating the effectiveness of cross-encoder reranking compared to the baseline (no reranking). This is meant for internal development only and will not be available in version 0.7.7 release

Author: Nguyen Vu <nguyen.vu@cbtw.tech>

## Overview

The test battery evaluates:

| Category | What It Tests |
|----------|---------------|
| **Retrieval Quality** | Precision@K, MRR, NDCG |
| **Query Type Performance** | Short, long, question, technical, ambiguous queries |
| **Latency Impact** | Overhead introduced by reranking |
| **Edge Cases** | Empty results, single result, long documents |
| **Regression Safety** | Ensures reranking doesn't degrade results |

## Quick Start

```bash
# Prerequisites
pip install sentence-transformers pytest

# Run full evaluation
pytest tests/integration/test_reranking_ab_evaluation.py -v -s

# Run specific test category
pytest tests/integration/test_reranking_ab_evaluation.py -k "precision" -v -s
pytest tests/integration/test_reranking_ab_evaluation.py -k "latency" -v -s
pytest tests/integration/test_reranking_ab_evaluation.py -k "query_type" -v -s
```

## Metrics Explained

### Precision@K (P@K)
- **What:** Fraction of top-K results that are relevant
- **Formula:** `relevant_in_top_k / k`
- **Target:** Higher is better (max 1.0)

### Mean Reciprocal Rank (MRR)
- **What:** Position of first relevant result (inverse)
- **Formula:** `1 / position_of_first_relevant`
- **Target:** Higher is better (max 1.0 = first result is relevant)

### Normalized Discounted Cumulative Gain (NDCG)
- **What:** Measures ranking quality with graded relevance
- **Formula:** DCG / IDCG (normalized against ideal ranking)
- **Target:** Higher is better (max 1.0 = perfect ranking)

### Latency Overhead
- **What:** Additional time for reranking
- **Formula:** `(treatment_latency - control_latency) / control_latency * 100`
- **Target:** Lower is better, but accept some overhead for quality

## Query Types

| Type | Description | Expected Reranking Benefit |
|------|-------------|---------------------------|
| **Short** | 1-3 words (e.g., "authentication") | High - disambiguates meaning |
| **Long** | 7+ words descriptive query | Medium - refines good results |
| **Question** | Natural language questions | High - understands Q&A relationship |
| **Technical** | Specific terms (e.g., "PgBouncer config") | Medium - exact matching important |
| **Ambiguous** | Multiple interpretations | High - context helps |
| **Multi-intent** | Multiple concepts | Medium - needs comprehensive results |

## Test Structure

```
tests/integration/test_reranking_ab_evaluation.py
├── TestRetrievalMetrics          # Verify metric calculations
├── TestQueryTypePerformance      # Per-query-type evaluation
├── TestLatencyImpact             # Measure overhead
├── TestEdgeCases                 # Handle edge cases
├── TestABComparison              # Main A/B evaluation
└── TestRegressionSafety          # Prevent degradation
```

## Running with Real Data

To use with actual search:

1. **Replace mock functions** in the test file:
   - `mock_search_without_reranking` → actual search API with `reranking.enabled=false`
   - `mock_search_with_reranking` → actual search API with `reranking.enabled=true`

2. **Configure test collection:**
   - Ingest documents with known IDs matching `TEST_QUERIES.relevant_doc_ids`
   - Or update `TEST_QUERIES` to match your actual document IDs

3. **Run evaluation:**
   ```bash
   pytest tests/integration/test_reranking_ab_evaluation.py::TestABComparison::test_full_ab_evaluation -v -s
   ```

## Sample Output

```
======================================================================
A/B EVALUATION REPORT: Cross-Encoder Reranking
======================================================================

Total queries evaluated: 14

--- CONTROL (No Reranking) ---
  Avg Precision@5:  0.420
  Avg Precision@10: 0.350
  Avg MRR:          0.580
  Avg NDCG@10:      0.510
  Avg Latency:      52.3 ms

--- TREATMENT (With Reranking) ---
  Avg Precision@5:  0.540
  Avg Precision@10: 0.440
  Avg MRR:          0.720
  Avg NDCG@10:      0.650
  Avg Latency:      148.7 ms

--- IMPROVEMENTS ---
  P@5 Improvement:     +28.6%
  MRR Improvement:     +24.1%
  Latency Overhead:    +184.3%

--- PER QUERY TYPE ---
  short        MRR delta: +0.180
  long         MRR delta: +0.090
  question     MRR delta: +0.250
  technical    MRR delta: +0.120
  ambiguous    MRR delta: +0.160

======================================================================
```

## Success Criteria

| Metric | Minimum Target | Good Target | Excellent |
|--------|---------------|-------------|-----------|
| P@5 Improvement | > 0% | > 15% | > 30% |
| MRR Improvement | > 5% | > 20% | > 35% |
| NDCG Improvement | > 5% | > 15% | > 25% |
| Latency Overhead | < 500% | < 300% | < 200% |

## Configuration Options

Test the cross-encoder with different configurations:

```python
# In config
reranking:
  enabled: true
  model: "cross-encoder/ms-marco-MiniLM-L-12-v2"  # Fast, good quality
  # model: "cross-encoder/ms-marco-MiniLM-L-6-v2"  # Faster, slightly less quality
  device: "cpu"  # or "cuda" for GPU
  batch_size: 32
```

## Adding Custom Test Queries

Add queries to `TEST_QUERIES` list:

```python
QueryTestCase(
    query="your query here",
    query_type="short",  # or long, question, technical, ambiguous, multi_intent
    relevant_doc_ids=["doc-1", "doc-2", "doc-3"],  # Ordered by relevance
    relevance_scores=[3, 2, 1],  # 0-3 scale
    description="What this tests",
)
```

## Exporting Results

```python
from test_reranking_ab_evaluation import (
    TestABComparison,
    TEST_QUERIES,
    export_results_to_json
)

evaluator = TestABComparison()
results, aggregate = evaluator.run_evaluation(TEST_QUERIES)
export_results_to_json(results, aggregate, "evaluation_results.json")
```
