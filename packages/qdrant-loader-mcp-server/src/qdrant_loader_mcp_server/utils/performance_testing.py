"""Performance testing and benchmarking for the enhanced hybrid search engine."""

import asyncio
import statistics
import time
from dataclasses import dataclass, field
from typing import Any

from ..search.enhanced_hybrid_search import (
    EnhancedHybridSearchEngine,
    SearchMode,
)
from .logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for search operations."""

    # Timing metrics
    total_time: float = 0.0
    vector_search_time: float = 0.0
    graph_search_time: float = 0.0
    keyword_search_time: float = 0.0
    fusion_time: float = 0.0
    cache_lookup_time: float = 0.0

    # Throughput metrics
    queries_per_second: float = 0.0
    results_per_second: float = 0.0

    # Quality metrics
    result_count: int = 0
    avg_relevance_score: float = 0.0
    cache_hit_rate: float = 0.0

    # Resource metrics
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0

    # Error metrics
    error_count: int = 0
    timeout_count: int = 0


@dataclass
class BenchmarkConfig:
    """Configuration for performance benchmarks."""

    # Test parameters
    num_queries: int = 100
    concurrent_queries: int = 10
    timeout_seconds: float = 30.0
    warmup_queries: int = 10

    # Search configurations to test
    search_modes: list[SearchMode] = field(
        default_factory=lambda: [
            SearchMode.VECTOR_ONLY,
            SearchMode.GRAPH_ONLY,
            SearchMode.HYBRID,
            SearchMode.AUTO,
        ]
    )

    # Query complexity levels
    query_lengths: list[int] = field(default_factory=lambda: [5, 15, 50, 100])
    result_limits: list[int] = field(default_factory=lambda: [5, 10, 25, 50])

    # Performance thresholds
    max_latency_ms: float = 1000.0
    min_throughput_qps: float = 10.0
    min_cache_hit_rate: float = 0.3


@dataclass
class BenchmarkResult:
    """Results from a performance benchmark."""

    config: BenchmarkConfig
    metrics: dict[str, PerformanceMetrics] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


class PerformanceTester:
    """Performance testing and benchmarking for hybrid search engine."""

    def __init__(self, search_engine: EnhancedHybridSearchEngine):
        """Initialize performance tester.

        Args:
            search_engine: Enhanced hybrid search engine to test
        """
        self.search_engine = search_engine
        self.logger = LoggingConfig.get_logger(__name__)

        # Test queries for different complexity levels
        self.test_queries = {
            5: ["API", "user", "data", "auth", "test"],
            15: [
                "user authentication",
                "database connection",
                "API endpoint error",
                "data processing",
                "search functionality",
            ],
            50: [
                "How to implement user authentication with JWT tokens in a microservice architecture",
                "Database connection pooling best practices for high-throughput applications",
                "API rate limiting and error handling strategies for production systems",
                "Data processing pipeline optimization for real-time analytics",
                "Search functionality implementation with vector embeddings and graph relationships",
            ],
            100: [
                "Comprehensive guide to implementing secure user authentication and authorization in a distributed microservice architecture using JWT tokens, OAuth2, and role-based access control with proper session management and token refresh mechanisms",
                "Advanced database connection pooling strategies and optimization techniques for high-throughput applications including connection lifecycle management, pool sizing, and performance monitoring",
                "Production-ready API design patterns including rate limiting, circuit breakers, retry mechanisms, error handling, and comprehensive logging for distributed systems",
                "Real-time data processing pipeline architecture with stream processing, batch processing, data validation, transformation, and monitoring for large-scale analytics platforms",
                "Advanced search functionality combining vector embeddings, graph relationships, keyword matching, and machine learning ranking algorithms for intelligent information retrieval systems",
            ],
        }

    async def run_benchmark(self, config: BenchmarkConfig) -> BenchmarkResult:
        """Run comprehensive performance benchmark.

        Args:
            config: Benchmark configuration

        Returns:
            Benchmark results with metrics and recommendations
        """
        self.logger.info("Starting performance benchmark")
        result = BenchmarkResult(config=config)

        try:
            # Warmup phase
            await self._warmup(config)

            # Test different search modes
            for mode in config.search_modes:
                self.logger.info(f"Testing search mode: {mode.value}")
                metrics = await self._test_search_mode(mode, config)
                result.metrics[mode.value] = metrics

            # Test scalability
            scalability_metrics = await self._test_scalability(config)
            result.metrics["scalability"] = scalability_metrics

            # Test cache performance
            cache_metrics = await self._test_cache_performance(config)
            result.metrics["cache"] = cache_metrics

            # Generate summary and recommendations
            result.summary = self._generate_summary(result.metrics)
            result.recommendations = self._generate_recommendations(
                result.metrics, config
            )

            self.logger.info("Performance benchmark completed")

        except Exception as e:
            self.logger.error(f"Benchmark failed: {e}")
            raise

        return result

    async def _warmup(self, config: BenchmarkConfig) -> None:
        """Warm up the search engine with sample queries."""
        self.logger.info(f"Warming up with {config.warmup_queries} queries")

        warmup_queries = self.test_queries[15][: config.warmup_queries]

        for query in warmup_queries:
            try:
                await self.search_engine.search(query, limit=10)
            except Exception as e:
                self.logger.warning(f"Warmup query failed: {e}")

    async def _test_search_mode(
        self, mode: SearchMode, config: BenchmarkConfig
    ) -> PerformanceMetrics:
        """Test performance for a specific search mode."""
        metrics = PerformanceMetrics()

        # Test with different query complexities
        all_times = []
        all_results = []
        error_count = 0
        timeout_count = 0

        for query_length in config.query_lengths:
            queries = self.test_queries[query_length][
                : config.num_queries // len(config.query_lengths)
            ]

            for query in queries:
                start_time = time.time()

                try:
                    # Run search with timeout
                    results = await asyncio.wait_for(
                        self.search_engine.search(
                            query=query, mode=mode, limit=config.result_limits[0]
                        ),
                        timeout=config.timeout_seconds,
                    )

                    end_time = time.time()
                    query_time = end_time - start_time

                    all_times.append(query_time)
                    all_results.append(len(results))

                except TimeoutError:
                    timeout_count += 1
                    self.logger.warning(f"Query timeout: {query[:50]}...")

                except Exception as e:
                    error_count += 1
                    self.logger.warning(f"Query error: {e}")

        # Calculate metrics
        if all_times:
            metrics.total_time = sum(all_times)
            metrics.queries_per_second = (
                len(all_times) / metrics.total_time if metrics.total_time > 0 else 0
            )
            metrics.result_count = sum(all_results)
            metrics.results_per_second = (
                metrics.result_count / metrics.total_time
                if metrics.total_time > 0
                else 0
            )
            metrics.avg_relevance_score = (
                statistics.mean([r for r in all_results if r > 0]) if all_results else 0
            )

        metrics.error_count = error_count
        metrics.timeout_count = timeout_count

        # Get cache statistics
        cache_stats = self.search_engine.get_cache_stats()
        metrics.cache_hit_rate = cache_stats.get("hit_rate", 0.0)

        return metrics

    async def _test_scalability(self, config: BenchmarkConfig) -> PerformanceMetrics:
        """Test scalability with concurrent queries."""
        metrics = PerformanceMetrics()

        # Test with increasing concurrency
        concurrency_levels = [1, 5, 10, 20, 50]
        query = self.test_queries[15][0]  # Use a medium complexity query

        best_qps = 0.0

        for concurrency in concurrency_levels:
            if concurrency > config.concurrent_queries:
                break

            start_time = time.time()

            # Create concurrent tasks
            tasks = []
            for _ in range(concurrency):
                task = self.search_engine.search(query=query, limit=10)
                tasks.append(task)

            try:
                # Run concurrent queries
                results = await asyncio.gather(*tasks, return_exceptions=True)

                end_time = time.time()
                total_time = end_time - start_time

                # Count successful queries
                successful_queries = sum(
                    1 for r in results if not isinstance(r, Exception)
                )
                qps = successful_queries / total_time if total_time > 0 else 0

                if qps > best_qps:
                    best_qps = qps
                    metrics.queries_per_second = qps
                    metrics.total_time = total_time

                self.logger.debug(f"Concurrency {concurrency}: {qps:.2f} QPS")

            except Exception as e:
                self.logger.warning(
                    f"Scalability test failed at concurrency {concurrency}: {e}"
                )

        return metrics

    async def _test_cache_performance(
        self, config: BenchmarkConfig
    ) -> PerformanceMetrics:
        """Test cache performance with repeated queries."""
        metrics = PerformanceMetrics()

        # Clear cache first
        self.search_engine.clear_cache()

        query = self.test_queries[15][0]

        # First run (cache miss)
        start_time = time.time()
        await self.search_engine.search(query=query, limit=10)
        first_run_time = time.time() - start_time

        # Second run (cache hit)
        start_time = time.time()
        await self.search_engine.search(query=query, limit=10)
        second_run_time = time.time() - start_time

        # Calculate cache performance
        cache_speedup = first_run_time / second_run_time if second_run_time > 0 else 1.0

        metrics.cache_lookup_time = second_run_time
        metrics.total_time = first_run_time

        # Get final cache stats
        cache_stats = self.search_engine.get_cache_stats()
        metrics.cache_hit_rate = cache_stats.get("hit_rate", 0.0)

        self.logger.info(f"Cache speedup: {cache_speedup:.2f}x")

        return metrics

    def _generate_summary(
        self, metrics: dict[str, PerformanceMetrics]
    ) -> dict[str, Any]:
        """Generate performance summary."""
        summary = {
            "best_mode": None,
            "best_qps": 0.0,
            "avg_latency_ms": 0.0,
            "cache_effectiveness": 0.0,
            "error_rate": 0.0,
            "scalability_score": 0.0,
        }

        # Find best performing mode
        for mode_name, metric in metrics.items():
            if mode_name in ["scalability", "cache"]:
                continue

            if metric.queries_per_second > summary["best_qps"]:
                summary["best_qps"] = metric.queries_per_second
                summary["best_mode"] = mode_name

        # Calculate average latency
        latencies = []
        error_counts = []
        total_queries = []

        for mode_name, metric in metrics.items():
            if mode_name in ["scalability", "cache"]:
                continue

            if metric.queries_per_second > 0:
                avg_latency = 1000 / metric.queries_per_second  # Convert to ms
                latencies.append(avg_latency)

            error_counts.append(metric.error_count)
            total_queries.append(
                metric.error_count + (metric.total_time * metric.queries_per_second)
            )

        if latencies:
            summary["avg_latency_ms"] = statistics.mean(latencies)

        # Calculate error rate
        total_errors = sum(error_counts)
        total_requests = sum(total_queries)
        summary["error_rate"] = (
            total_errors / total_requests if total_requests > 0 else 0.0
        )

        # Cache effectiveness
        if "cache" in metrics:
            summary["cache_effectiveness"] = metrics["cache"].cache_hit_rate

        # Scalability score (based on concurrent performance)
        if "scalability" in metrics:
            summary["scalability_score"] = min(
                metrics["scalability"].queries_per_second / 10.0, 1.0
            )

        return summary

    def _generate_recommendations(
        self, metrics: dict[str, PerformanceMetrics], config: BenchmarkConfig
    ) -> list[str]:
        """Generate performance optimization recommendations."""
        recommendations = []

        # Check latency
        for mode_name, metric in metrics.items():
            if mode_name in ["scalability", "cache"]:
                continue

            if metric.queries_per_second > 0:
                avg_latency = 1000 / metric.queries_per_second
                if avg_latency > config.max_latency_ms:
                    recommendations.append(
                        f"High latency detected in {mode_name} mode ({avg_latency:.1f}ms). "
                        "Consider optimizing vector search parameters or graph query complexity."
                    )

        # Check throughput
        best_qps = max(
            (
                m.queries_per_second
                for m in metrics.values()
                if hasattr(m, "queries_per_second")
            ),
            default=0.0,
        )
        if best_qps < config.min_throughput_qps:
            recommendations.append(
                f"Low throughput detected ({best_qps:.1f} QPS). "
                "Consider enabling caching, optimizing database connections, or scaling resources."
            )

        # Check cache performance
        if "cache" in metrics:
            cache_hit_rate = metrics["cache"].cache_hit_rate
            if cache_hit_rate < config.min_cache_hit_rate:
                recommendations.append(
                    f"Low cache hit rate ({cache_hit_rate:.1%}). "
                    "Consider increasing cache TTL or cache size."
                )

        # Check error rates
        total_errors = sum(m.error_count for m in metrics.values())
        if total_errors > 0:
            recommendations.append(
                f"Detected {total_errors} errors during testing. "
                "Review error logs and improve error handling."
            )

        # Mode-specific recommendations
        if "hybrid" in metrics and "vector_only" in metrics:
            hybrid_qps = metrics["hybrid"].queries_per_second
            vector_qps = metrics["vector_only"].queries_per_second

            if vector_qps > hybrid_qps * 1.5:
                recommendations.append(
                    "Vector-only search significantly outperforms hybrid mode. "
                    "Consider reducing graph search weight or optimizing graph queries."
                )

        if not recommendations:
            recommendations.append(
                "Performance is within acceptable thresholds. No immediate optimizations needed."
            )

        return recommendations


async def run_performance_test(
    search_engine: EnhancedHybridSearchEngine, config: BenchmarkConfig | None = None
) -> BenchmarkResult:
    """Run performance test on the enhanced hybrid search engine.

    Args:
        search_engine: Search engine to test
        config: Optional benchmark configuration

    Returns:
        Benchmark results
    """
    if config is None:
        config = BenchmarkConfig()

    tester = PerformanceTester(search_engine)
    return await tester.run_benchmark(config)


def print_benchmark_results(result: BenchmarkResult) -> None:
    """Print formatted benchmark results.

    Args:
        result: Benchmark results to print
    """
    print("\n" + "=" * 80)
    print("ENHANCED HYBRID SEARCH PERFORMANCE BENCHMARK RESULTS")
    print("=" * 80)

    # Summary
    print("\nSUMMARY:")
    print(f"  Best Mode: {result.summary.get('best_mode', 'N/A')}")
    print(f"  Best QPS: {result.summary.get('best_qps', 0):.2f}")
    print(f"  Avg Latency: {result.summary.get('avg_latency_ms', 0):.1f}ms")
    print(f"  Cache Hit Rate: {result.summary.get('cache_effectiveness', 0):.1%}")
    print(f"  Error Rate: {result.summary.get('error_rate', 0):.1%}")
    print(f"  Scalability Score: {result.summary.get('scalability_score', 0):.1%}")

    # Detailed metrics
    print("\nDETAILED METRICS:")
    for mode_name, metrics in result.metrics.items():
        print(f"\n  {mode_name.upper()}:")
        print(f"    QPS: {metrics.queries_per_second:.2f}")
        print(f"    Total Time: {metrics.total_time:.2f}s")
        print(f"    Results: {metrics.result_count}")
        print(f"    Errors: {metrics.error_count}")
        print(f"    Timeouts: {metrics.timeout_count}")
        if hasattr(metrics, "cache_hit_rate"):
            print(f"    Cache Hit Rate: {metrics.cache_hit_rate:.1%}")

    # Recommendations
    print("\nRECOMMENDATIONS:")
    for i, rec in enumerate(result.recommendations, 1):
        print(f"  {i}. {rec}")

    print("\n" + "=" * 80)
