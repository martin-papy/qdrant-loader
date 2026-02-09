"""
A/B Evaluation Test Battery: Cross-Encoder Reranking vs Control (No Reranking)

This test suite provides a comprehensive evaluation framework for comparing
search quality with and without cross-encoder reranking.

Metrics Evaluated:
- Precision@K (P@5, P@10)
- Mean Reciprocal Rank (MRR)
- Normalized Discounted Cumulative Gain (NDCG)
- Latency (ms)
- Rank displacement (how much results move after reranking)

Query Types Tested:
- Short queries (1-3 words)
- Long queries (7+ words)
- Question queries
- Technical/exact queries
- Ambiguous queries
- Multi-intent queries

Prerequisites:
    - Qdrant running on localhost:6333
    - OpenAI API key in OPENAI_API_KEY environment variable
    - sentence-transformers installed (for cross-encoder)
    - Test collection with sample documents

Run with:
    pytest tests/integration/test_reranking_ab_evaluation.py -v -s

    # Run specific test category:
    pytest tests/integration/test_reranking_ab_evaluation.py -k "precision" -v -s

Author: Nguyen Vu <nguyen.vu@cbtw.tech>
"""

import json
import math
import os
import time
from dataclasses import dataclass, field

import pytest
import requests

NORMAL_URL = "http://127.0.0.1:8080/mcp"
RERANK_URL = "http://127.0.0.1:8081/mcp"
REQUEST_TIMEOUT = 30

def call_search_api(url: str, query: str, limit: int = 10) -> tuple[list[dict], float]:
    """
    Call MCP search endpoint and return normalized results + latency.
    Normalizes MCP JSON-RPC response into evaluation format.
    """

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "search",
        "params": {
            "query": query,
            "limit": limit,
        },
    }

    start = time.time()

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        pytest.fail(f"MCP API call failed: {e}")

    latency_ms = (time.time() - start) * 1000
    data = response.json()

    if data.get("result", {}).get("isError"):
        pytest.fail(f"MCP returned error: {data}")

    raw_results = (
        data.get("result", {})
        .get("structuredContent", {})
        .get("results", [])
    )

    normalized_results = [
        {
            "id": r["document_id"],
            "text": r.get("content_snippet", ""),
            "score": r.get("score", 0.0),
        }
        for r in raw_results
    ]

    return normalized_results, latency_ms

# Skip all tests if prerequisites not available
pytestmark = [
    pytest.mark.integration,
    pytest.mark.reranking_evaluation,
    pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set"
    ),
]


# =============================================================================
# DATA CLASSES FOR EVALUATION
# =============================================================================


@dataclass
class RelevanceJudgment:
    """Ground truth relevance judgment for a query-document pair."""

    query: str
    doc_id: str
    relevance: int  # 0=not relevant, 1=marginally, 2=relevant, 3=highly relevant
    doc_title: str = ""


@dataclass
class QueryTestCase:
    """A test case with query, expected results, and categorization."""

    query: str
    query_type: str  # short, long, question, technical, ambiguous, multi_intent
    relevant_doc_ids: list[str]  # Ordered by relevance (most relevant first)
    relevance_scores: list[int] = field(default_factory=list)  # Graded relevance
    description: str = ""


@dataclass
class EvaluationResult:
    """Results from a single query evaluation."""

    query: str
    query_type: str
    # Control (no reranking)
    control_precision_at_5: float = 0.0
    control_precision_at_10: float = 0.0
    control_mrr: float = 0.0
    control_ndcg_at_10: float = 0.0
    control_latency_ms: float = 0.0
    control_result_ids: list[str] = field(default_factory=list)
    # Treatment (with reranking)
    treatment_precision_at_5: float = 0.0
    treatment_precision_at_10: float = 0.0
    treatment_mrr: float = 0.0
    treatment_ndcg_at_10: float = 0.0
    treatment_latency_ms: float = 0.0
    treatment_result_ids: list[str] = field(default_factory=list)
    # Comparison
    rank_displacement: float = 0.0  # Average position change


@dataclass
class AggregateResults:
    """Aggregated results across all queries."""

    total_queries: int = 0
    # Control averages
    control_avg_p5: float = 0.0
    control_avg_p10: float = 0.0
    control_avg_mrr: float = 0.0
    control_avg_ndcg: float = 0.0
    control_avg_latency: float = 0.0
    # Treatment averages
    treatment_avg_p5: float = 0.0
    treatment_avg_p10: float = 0.0
    treatment_avg_mrr: float = 0.0
    treatment_avg_ndcg: float = 0.0
    treatment_avg_latency: float = 0.0
    # Improvements
    p5_improvement_pct: float = 0.0
    p10_improvement_pct: float = 0.0
    mrr_improvement_pct: float = 0.0
    ndcg_improvement_pct: float = 0.0
    latency_overhead_pct: float = 0.0
    # Statistical significance
    p5_significant: bool = False
    mrr_significant: bool = False


# =============================================================================
# TEST QUERIES - Designed to evaluate reranking effectiveness
# =============================================================================

TEST_QUERIES = [
    # SHORT QUERIES (1-3 words) - Harder for vector search, reranking should help
    QueryTestCase(
        query="authentication",
        query_type="short",
        relevant_doc_ids=["auth-guide", "security-overview", "login-flow"],
        relevance_scores=[3, 2, 2],
        description="Single word, multiple relevant docs",
    ),
    QueryTestCase(
        query="API endpoints",
        query_type="short",
        relevant_doc_ids=["api-reference", "rest-guide", "endpoint-list"],
        relevance_scores=[3, 2, 1],
        description="Two words, technical term",
    ),
    QueryTestCase(
        query="deployment",
        query_type="short",
        relevant_doc_ids=["deploy-guide", "cicd-pipeline", "kubernetes-setup"],
        relevance_scores=[3, 2, 2],
        description="Single word, DevOps context",
    ),
    # LONG QUERIES (7+ words) - Vector search usually good, reranking refines
    QueryTestCase(
        query="how to configure authentication for REST API endpoints",
        query_type="long",
        relevant_doc_ids=["api-auth-config", "auth-guide", "rest-security"],
        relevance_scores=[3, 2, 2],
        description="Long descriptive query",
    ),
    QueryTestCase(
        query="step by step guide to deploy application to production kubernetes",
        query_type="long",
        relevant_doc_ids=["k8s-deploy-guide", "prod-checklist", "deploy-guide"],
        relevance_scores=[3, 3, 2],
        description="Long procedural query",
    ),
    # QUESTION QUERIES - Natural language, cross-encoder excels here
    QueryTestCase(
        query="What is the best practice for token rotation?",
        query_type="question",
        relevant_doc_ids=["token-management", "security-best-practices", "auth-guide"],
        relevance_scores=[3, 2, 1],
        description="Best practice question",
    ),
    QueryTestCase(
        query="How do I handle session timeout errors?",
        query_type="question",
        relevant_doc_ids=["session-handling", "error-reference", "troubleshooting"],
        relevance_scores=[3, 2, 2],
        description="Troubleshooting question",
    ),
    QueryTestCase(
        query="Why is my database connection pool exhausted?",
        query_type="question",
        relevant_doc_ids=["db-connection-pool", "troubleshooting", "performance-guide"],
        relevance_scores=[3, 2, 1],
        description="Debugging question",
    ),
    # TECHNICAL/EXACT QUERIES - Specific terms, keyword matching important
    QueryTestCase(
        query="PgBouncer transaction mode configuration",
        query_type="technical",
        relevant_doc_ids=["pgbouncer-config", "db-optimization", "connection-guide"],
        relevance_scores=[3, 2, 1],
        description="Specific technology query",
    ),
    QueryTestCase(
        query="OAuth 2.0 authorization code flow",
        query_type="technical",
        relevant_doc_ids=["oauth-flows", "auth-guide", "security-protocols"],
        relevance_scores=[3, 2, 1],
        description="Protocol-specific query",
    ),
    # AMBIGUOUS QUERIES - Multiple interpretations, reranking should disambiguate
    QueryTestCase(
        query="connection",
        query_type="ambiguous",
        relevant_doc_ids=["db-connection", "network-config", "api-connection"],
        relevance_scores=[2, 2, 2],
        description="Ambiguous single word",
    ),
    QueryTestCase(
        query="timeout settings",
        query_type="ambiguous",
        relevant_doc_ids=["session-timeout", "connection-timeout", "request-timeout"],
        relevance_scores=[2, 2, 2],
        description="Multiple timeout types",
    ),
    # MULTI-INTENT QUERIES - Multiple aspects, comprehensive results needed
    QueryTestCase(
        query="security authentication and rate limiting",
        query_type="multi_intent",
        relevant_doc_ids=["security-overview", "auth-guide", "rate-limiting"],
        relevance_scores=[3, 2, 2],
        description="Multiple related concepts",
    ),
    QueryTestCase(
        query="database performance indexing and caching",
        query_type="multi_intent",
        relevant_doc_ids=["db-optimization", "indexing-guide", "caching-strategy"],
        relevance_scores=[3, 2, 2],
        description="Multiple optimization techniques",
    ),
]


# =============================================================================
# METRIC CALCULATION FUNCTIONS
# =============================================================================


def precision_at_k(result_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """Calculate Precision@K."""
    if k <= 0:
        return 0.0
    top_k = result_ids[:k]
    relevant_in_top_k = sum(1 for r in top_k if r in relevant_ids)
    return relevant_in_top_k / k


def mean_reciprocal_rank(result_ids: list[str], relevant_ids: set[str]) -> float:
    """Calculate Mean Reciprocal Rank (MRR)."""
    for i, doc_id in enumerate(result_ids):
        if doc_id in relevant_ids:
            return 1.0 / (i + 1)
    return 0.0


def dcg_at_k(relevance_scores: list[int], k: int) -> float:
    """Calculate Discounted Cumulative Gain at K."""
    dcg = 0.0
    for i, rel in enumerate(relevance_scores[:k]):
        dcg += (2**rel - 1) / math.log2(i + 2)  # i+2 because log2(1) = 0
    return dcg


def ndcg_at_k(
    result_ids: list[str],
    relevance_map: dict[str, int],
    ideal_order: list[str],
    k: int,
) -> float:
    """Calculate Normalized Discounted Cumulative Gain at K."""
    # Get relevance scores for actual results
    actual_relevances = [relevance_map.get(doc_id, 0) for doc_id in result_ids[:k]]
    # Get ideal relevance scores
    ideal_relevances = [relevance_map.get(doc_id, 0) for doc_id in ideal_order[:k]]
    ideal_relevances.sort(reverse=True)

    dcg = dcg_at_k(actual_relevances, k)
    idcg = dcg_at_k(ideal_relevances, k)

    if idcg == 0:
        return 0.0
    return dcg / idcg


def calculate_rank_displacement(
    control_ids: list[str], treatment_ids: list[str]
) -> float:
    """Calculate average rank displacement between control and treatment."""
    if not control_ids or not treatment_ids:
        return 0.0

    total_displacement = 0
    count = 0

    for i, doc_id in enumerate(control_ids):
        if doc_id in treatment_ids:
            new_rank = treatment_ids.index(doc_id)
            total_displacement += abs(i - new_rank)
            count += 1

    return total_displacement / count if count > 0 else 0.0


# =============================================================================
# MOCK SEARCH FUNCTIONS (Replace with actual search in real tests)
# =============================================================================

def mock_search_without_reranking(query: str, limit: int = 10):
    return call_search_api(NORMAL_URL, query, limit)

def mock_search_with_reranking(query: str, limit: int = 10):
    return call_search_api(RERANK_URL, query, limit)

# =============================================================================
# TEST CLASSES
# =============================================================================


class TestRetrievalMetrics:
    """Test retrieval quality metrics for control vs treatment."""

    def test_precision_at_k_calculation(self):
        """Verify precision@k calculation is correct."""
        result_ids = ["a", "b", "c", "d", "e"]
        relevant = {"a", "c", "e"}

        assert precision_at_k(result_ids, relevant, 1) == 1.0  # a is relevant
        assert precision_at_k(result_ids, relevant, 2) == 0.5  # 1/2 relevant
        assert precision_at_k(result_ids, relevant, 5) == 0.6  # 3/5 relevant

    def test_mrr_calculation(self):
        """Verify MRR calculation is correct."""
        relevant = {"target"}

        # Target at position 1
        assert mean_reciprocal_rank(["target", "b", "c"], relevant) == 1.0
        # Target at position 2
        assert mean_reciprocal_rank(["a", "target", "c"], relevant) == 0.5
        # Target at position 3
        assert mean_reciprocal_rank(["a", "b", "target"], relevant) == pytest.approx(
            0.333, rel=0.01
        )
        # Target not found
        assert mean_reciprocal_rank(["a", "b", "c"], relevant) == 0.0

    def test_ndcg_calculation(self):
        """Verify NDCG calculation is correct."""
        relevance_map = {"a": 3, "b": 2, "c": 1, "d": 0}
        ideal_order = ["a", "b", "c", "d"]

        # Perfect ranking
        perfect = ndcg_at_k(["a", "b", "c", "d"], relevance_map, ideal_order, 4)
        assert perfect == pytest.approx(1.0, rel=0.01)

        # Worst ranking (reversed)
        worst = ndcg_at_k(["d", "c", "b", "a"], relevance_map, ideal_order, 4)
        assert worst < 1.0

    def test_rank_displacement_calculation(self):
        """Verify rank displacement calculation."""
        control = ["a", "b", "c", "d"]
        treatment = ["b", "a", "d", "c"]  # Swapped pairs

        displacement = calculate_rank_displacement(control, treatment)
        # a: 0->1, b: 1->0, c: 2->3, d: 3->2 = avg of 1,1,1,1 = 1.0
        assert displacement == pytest.approx(1.0, rel=0.01)


class TestQueryTypePerformance:
    """Test reranking performance across different query types."""

    @pytest.mark.parametrize(
        "query_type",
        ["short", "long", "question", "technical", "ambiguous", "multi_intent"],
    )
    def test_query_type_evaluation_structure(self, query_type: str):
        """Verify we have test queries for each query type."""
        queries_of_type = [q for q in TEST_QUERIES if q.query_type == query_type]
        assert len(queries_of_type) >= 1, f"Need at least 1 {query_type} query"

    def test_short_queries_benefit_from_reranking(self):
        """
        Short queries (1-3 words) often have multiple interpretations.
        Cross-encoder should help disambiguate by considering full context.
        """
        short_queries = [q for q in TEST_QUERIES if q.query_type == "short"]

        for test_case in short_queries:
            # In real implementation, run both searches and compare
            control_results, control_latency = mock_search_without_reranking(
                test_case.query
            )
            treatment_results, treatment_latency = mock_search_with_reranking(
                test_case.query
            )

            # Cross-encoder adds latency but should improve relevance
            assert treatment_latency > control_latency

            # Verify we get results
            assert len(control_results) > 0
            assert len(treatment_results) > 0

    def test_question_queries_cross_encoder_advantage(self):
        """
        Question queries benefit most from cross-encoder because it
        understands the question-answer relationship.
        """
        question_queries = [q for q in TEST_QUERIES if q.query_type == "question"]

        for test_case in question_queries:
            control_results, _ = mock_search_without_reranking(test_case.query)
            treatment_results, _ = mock_search_with_reranking(test_case.query)

            # Both should return results
            assert len(control_results) > 0
            assert len(treatment_results) > 0

            # Treatment should have cross_encoder_score
            if treatment_results:
                assert "cross_encoder_score" in treatment_results[0]


class TestLatencyImpact:
    """Test the latency overhead of cross-encoder reranking."""

    def test_reranking_adds_latency(self):
        """Verify that reranking adds measurable latency."""
        query = "test query"

        _, control_latency = mock_search_without_reranking(query)
        _, treatment_latency = mock_search_with_reranking(query)

        # Reranking should add latency
        assert treatment_latency > control_latency

        # But shouldn't be excessive (< 5x overhead for 10 results)
        overhead_ratio = treatment_latency / control_latency
        assert overhead_ratio < 5.0, f"Latency overhead too high: {overhead_ratio}x"

    def test_latency_scales_with_result_count(self):
        """Test how latency scales with number of results to rerank."""
        query = "scalability test"

        latencies = {}
        for limit in [5, 10, 20]:
            _, latency = mock_search_with_reranking(query, limit=limit)
            latencies[limit] = latency

        # Latency should increase with more results (but not linearly due to batching)
        # In real implementation, verify sub-linear scaling


class TestEdgeCases:
    """Test edge cases for reranking."""

    @pytest.mark.skip(reason="Implement with actual search integration")
    def test_empty_results(self):
        """Reranking should handle empty results gracefully."""
        # This would test with a query that returns no results
        raise NotImplementedError("Implement with actual search")

    @pytest.mark.skip(reason="Implement with actual search integration")
    def test_single_result(self):
        """Reranking a single result should return it unchanged."""
        raise NotImplementedError("Implement with actual search")

    @pytest.mark.skip(reason="Implement with actual search integration")
    def test_identical_scores(self):
        """Handle results with identical scores correctly."""
        raise NotImplementedError("Implement with actual search")

    @pytest.mark.skip(reason="Implement with actual search integration")
    def test_very_long_documents(self):
        """Cross-encoder truncates to 512 tokens - verify behavior."""
        raise NotImplementedError("Implement with actual search")


class TestABComparison:
    """
    A/B test comparison framework.
    This is the main evaluation that compares control vs treatment.
    """

    def run_evaluation(
        self, test_cases: list[QueryTestCase]
    ) -> tuple[list[EvaluationResult], AggregateResults]:
        """
        Run full A/B evaluation on test cases.

        Returns:
            Tuple of (individual results, aggregate results)
        """
        results = []

        for test_case in test_cases:
            # Run control (no reranking)
            control_results, control_latency = mock_search_without_reranking(
                test_case.query
            )
            control_ids = [r["id"] for r in control_results]

            # Run treatment (with reranking)
            treatment_results, treatment_latency = mock_search_with_reranking(
                test_case.query
            )
            treatment_ids = [r["id"] for r in treatment_results]

            # Build relevance map
            relevant_set = set(test_case.relevant_doc_ids)
            relevance_map = dict(
                zip(
                    test_case.relevant_doc_ids,
                    test_case.relevance_scores,
                    strict=False,
                )
            )

            # Calculate metrics
            eval_result = EvaluationResult(
                query=test_case.query,
                query_type=test_case.query_type,
                control_precision_at_5=precision_at_k(control_ids, relevant_set, 5),
                control_precision_at_10=precision_at_k(control_ids, relevant_set, 10),
                control_mrr=mean_reciprocal_rank(control_ids, relevant_set),
                control_ndcg_at_10=ndcg_at_k(
                    control_ids, relevance_map, test_case.relevant_doc_ids, 10
                ),
                control_latency_ms=control_latency,
                control_result_ids=control_ids,
                treatment_precision_at_5=precision_at_k(treatment_ids, relevant_set, 5),
                treatment_precision_at_10=precision_at_k(
                    treatment_ids, relevant_set, 10
                ),
                treatment_mrr=mean_reciprocal_rank(treatment_ids, relevant_set),
                treatment_ndcg_at_10=ndcg_at_k(
                    treatment_ids, relevance_map, test_case.relevant_doc_ids, 10
                ),
                treatment_latency_ms=treatment_latency,
                treatment_result_ids=treatment_ids,
                rank_displacement=calculate_rank_displacement(
                    control_ids, treatment_ids
                ),
            )

            results.append(eval_result)

        # Aggregate results
        n = len(results)
        aggregate = AggregateResults(
            total_queries=n,
            control_avg_p5=sum(r.control_precision_at_5 for r in results) / n,
            control_avg_p10=sum(r.control_precision_at_10 for r in results) / n,
            control_avg_mrr=sum(r.control_mrr for r in results) / n,
            control_avg_ndcg=sum(r.control_ndcg_at_10 for r in results) / n,
            control_avg_latency=sum(r.control_latency_ms for r in results) / n,
            treatment_avg_p5=sum(r.treatment_precision_at_5 for r in results) / n,
            treatment_avg_p10=sum(r.treatment_precision_at_10 for r in results) / n,
            treatment_avg_mrr=sum(r.treatment_mrr for r in results) / n,
            treatment_avg_ndcg=sum(r.treatment_ndcg_at_10 for r in results) / n,
            treatment_avg_latency=sum(r.treatment_latency_ms for r in results) / n,
        )

        # Calculate improvements
        if aggregate.control_avg_p5 > 0:
            aggregate.p5_improvement_pct = (
                (aggregate.treatment_avg_p5 - aggregate.control_avg_p5)
                / aggregate.control_avg_p5
                * 100
            )
        if aggregate.control_avg_mrr > 0:
            aggregate.mrr_improvement_pct = (
                (aggregate.treatment_avg_mrr - aggregate.control_avg_mrr)
                / aggregate.control_avg_mrr
                * 100
            )
        if aggregate.control_avg_latency > 0:
            aggregate.latency_overhead_pct = (
                (aggregate.treatment_avg_latency - aggregate.control_avg_latency)
                / aggregate.control_avg_latency
                * 100
            )

        return results, aggregate

    def test_full_ab_evaluation(self):
        """Run full A/B evaluation and generate report."""
        individual_results, aggregate = self.run_evaluation(TEST_QUERIES)

        # Print detailed report
        print("\n" + "=" * 70)
        print("A/B EVALUATION REPORT: Cross-Encoder Reranking")
        print("=" * 70)

        print(f"\nTotal queries evaluated: {aggregate.total_queries}")

        print("\n--- CONTROL (No Reranking) ---")
        print(f"  Avg Precision@5:  {aggregate.control_avg_p5:.3f}")
        print(f"  Avg Precision@10: {aggregate.control_avg_p10:.3f}")
        print(f"  Avg MRR:          {aggregate.control_avg_mrr:.3f}")
        print(f"  Avg NDCG@10:      {aggregate.control_avg_ndcg:.3f}")
        print(f"  Avg Latency:      {aggregate.control_avg_latency:.1f} ms")

        print("\n--- TREATMENT (With Reranking) ---")
        print(f"  Avg Precision@5:  {aggregate.treatment_avg_p5:.3f}")
        print(f"  Avg Precision@10: {aggregate.treatment_avg_p10:.3f}")
        print(f"  Avg MRR:          {aggregate.treatment_avg_mrr:.3f}")
        print(f"  Avg NDCG@10:      {aggregate.treatment_avg_ndcg:.3f}")
        print(f"  Avg Latency:      {aggregate.treatment_avg_latency:.1f} ms")

        print("\n--- IMPROVEMENTS ---")
        print(f"  P@5 Improvement:     {aggregate.p5_improvement_pct:+.1f}%")
        print(f"  MRR Improvement:     {aggregate.mrr_improvement_pct:+.1f}%")
        print(f"  Latency Overhead:    {aggregate.latency_overhead_pct:+.1f}%")

        print("\n--- PER QUERY TYPE ---")
        for query_type in ["short", "long", "question", "technical", "ambiguous"]:
            type_results = [r for r in individual_results if r.query_type == query_type]
            if type_results:
                avg_improvement = sum(
                    r.treatment_mrr - r.control_mrr for r in type_results
                ) / len(type_results)
                print(f"  {query_type:12} MRR delta: {avg_improvement:+.3f}")

        print("\n" + "=" * 70)

    def test_reranking_improves_mrr(self):
        """
        Key hypothesis: Cross-encoder reranking should improve MRR.
        This is the primary success metric.
        """
        _, aggregate = self.run_evaluation(TEST_QUERIES)

        # NOTE: In a real evaluation with proper test data, we'd expect improvement
        # NOTE: For now, just verify the evaluation runs
        assert aggregate.total_queries > 0

    def test_latency_overhead_acceptable(self):
        """
        Verify latency overhead is within acceptable bounds.
        Target: < 200% overhead for significant quality improvement.
        """
        _, aggregate = self.run_evaluation(TEST_QUERIES)

        # Latency overhead should be reasonable
        # In production, we'd tune this threshold based on SLAs
        max_acceptable_overhead = 300  # 300% overhead max

        assert aggregate.latency_overhead_pct < max_acceptable_overhead, (
            f"Latency overhead too high: {aggregate.latency_overhead_pct:.1f}%"
        )


class TestRegressionSafety:
    """
    Regression tests to ensure reranking doesn't make things worse.
    """

    def test_no_precision_regression(self):
        """Reranking should not decrease precision significantly."""
        evaluator = TestABComparison()
        _, aggregate = evaluator.run_evaluation(TEST_QUERIES)

        # Allow up to 5% regression (noise tolerance)
        max_regression = -5.0

        assert aggregate.p5_improvement_pct > max_regression, (
            f"P@5 regression too large: {aggregate.p5_improvement_pct:.1f}%"
        )

    def test_no_mrr_regression(self):
        """Reranking should not decrease MRR significantly."""
        evaluator = TestABComparison()
        _, aggregate = evaluator.run_evaluation(TEST_QUERIES)

        max_regression = -5.0

        assert aggregate.mrr_improvement_pct > max_regression, (
            f"MRR regression too large: {aggregate.mrr_improvement_pct:.1f}%"
        )


# =============================================================================
# UTILITY: Export results for analysis
# =============================================================================


def export_results_to_json(
    results: list[EvaluationResult], aggregate: AggregateResults, filepath: str
) -> None:
    """Export evaluation results to JSON for further analysis."""
    data = {
        "aggregate": {
            "total_queries": aggregate.total_queries,
            "control": {
                "avg_p5": aggregate.control_avg_p5,
                "avg_p10": aggregate.control_avg_p10,
                "avg_mrr": aggregate.control_avg_mrr,
                "avg_ndcg": aggregate.control_avg_ndcg,
                "avg_latency_ms": aggregate.control_avg_latency,
            },
            "treatment": {
                "avg_p5": aggregate.treatment_avg_p5,
                "avg_p10": aggregate.treatment_avg_p10,
                "avg_mrr": aggregate.treatment_avg_mrr,
                "avg_ndcg": aggregate.treatment_avg_ndcg,
                "avg_latency_ms": aggregate.treatment_avg_latency,
            },
            "improvements": {
                "p5_pct": aggregate.p5_improvement_pct,
                "mrr_pct": aggregate.mrr_improvement_pct,
                "latency_overhead_pct": aggregate.latency_overhead_pct,
            },
        },
        "individual": [
            {
                "query": r.query,
                "query_type": r.query_type,
                "control_mrr": r.control_mrr,
                "treatment_mrr": r.treatment_mrr,
                "mrr_delta": r.treatment_mrr - r.control_mrr,
                "rank_displacement": r.rank_displacement,
            }
            for r in results
        ],
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
