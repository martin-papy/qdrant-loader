"""
Knowledge Graph Traversal Engine.

This module implements advanced graph traversal algorithms for multi-hop search
and content discovery within knowledge graphs.
"""

from __future__ import annotations

import heapq
from collections import deque
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...nlp.spacy_analyzer import QueryAnalysis, SpaCyQueryAnalyzer
    from .models import TraversalResult, TraversalStrategy
else:
    QueryAnalysis = Any
    SpaCyQueryAnalyzer = Any

from ....utils.logging import LoggingConfig
from .models import TraversalResult, TraversalStrategy
from .utils import (
    ENTITY_SIM_WEIGHT,
    KEYWORD_SIM_WEIGHT,
    TOPIC_SIM_WEIGHT,
    build_reasoning_path,
    calculate_list_similarity,
)

logger = LoggingConfig.get_logger(__name__)


class GraphTraverser:
    """Advanced graph traversal for multi-hop search and content discovery."""

    def __init__(
        self,
        knowledge_graph: Any,  # KnowledgeGraph - avoiding circular import
        spacy_analyzer: SpaCyQueryAnalyzer | None = None,
    ):
        """Initialize the graph traverser."""
        self.graph = knowledge_graph
        # Import SpaCyQueryAnalyzer at runtime to avoid circular import
        if spacy_analyzer is None:
            try:
                from ...nlp.spacy_analyzer import SpaCyQueryAnalyzer
            except ImportError as exc:
                logger.exception(
                    "SpaCyQueryAnalyzer is not available. Ensure optional NLP deps are installed (e.g., 'pip install spacy' and required models)."
                )
                raise ImportError(
                    "SpaCyQueryAnalyzer (and its spacy dependency) is missing. Install optional NLP extras to enable semantic traversal."
                ) from exc
            self.spacy_analyzer = SpaCyQueryAnalyzer()
        else:
            self.spacy_analyzer = spacy_analyzer
        logger.debug("Initialized graph traverser")

    def traverse(
        self,
        start_nodes: list[str],
        query_analysis: QueryAnalysis | None = None,
        strategy: TraversalStrategy = TraversalStrategy.WEIGHTED,
        max_hops: int = 3,
        max_results: int = 20,
        min_weight: float = 0.1,
    ) -> list[TraversalResult]:
        """Traverse the graph to find related content."""

        results = []

        for start_node_id in start_nodes:
            if start_node_id not in self.graph.nodes:
                continue

            # Perform traversal based on strategy
            if strategy == TraversalStrategy.BREADTH_FIRST:
                node_results = self._breadth_first_traversal(
                    start_node_id,
                    query_analysis,
                    max_hops,
                    max_results,
                    min_weight,
                )
            elif strategy == TraversalStrategy.WEIGHTED:
                node_results = self._weighted_traversal(
                    start_node_id,
                    query_analysis,
                    max_hops,
                    max_results,
                    min_weight,
                )
            elif strategy == TraversalStrategy.CENTRALITY:
                node_results = self._centrality_traversal(
                    start_node_id,
                    query_analysis,
                    max_hops,
                    max_results,
                    min_weight,
                )
            elif strategy == TraversalStrategy.SEMANTIC:
                node_results = self._semantic_traversal(
                    start_node_id,
                    query_analysis,
                    max_hops,
                    max_results,
                    min_weight,
                )
            else:
                node_results = self._breadth_first_traversal(
                    start_node_id,
                    query_analysis,
                    max_hops,
                    max_results,
                    min_weight,
                )

            results.extend(node_results)

        # Sort by semantic score and total weight
        results.sort(key=lambda r: (r.semantic_score, r.total_weight), reverse=True)
        return results[:max_results]

    def _breadth_first_traversal(
        self,
        start_node_id: str,
        query_analysis: QueryAnalysis | None,
        max_hops: int,
        max_results: int,
        min_weight: float,
    ) -> list[TraversalResult]:
        """Breadth-first traversal implementation."""

        results = []
        queue = deque(
            [(start_node_id, [], [], 0.0, 0)]
        )  # (node_id, path, edges, weight, hops)
        local_visited = set()

        while queue and len(results) < max_results:
            node_id, path, edges, total_weight, hops = queue.popleft()

            if node_id in local_visited or hops > max_hops:
                continue

            local_visited.add(node_id)

            # Create traversal result
            if node_id != start_node_id:  # Don't include the starting node
                semantic_score = self._calculate_semantic_score(node_id, query_analysis)
                reasoning_path = build_reasoning_path(edges, self.graph.nodes)

                result = TraversalResult(
                    path=path + [node_id],
                    nodes=[self.graph.nodes[nid] for nid in path + [node_id]],
                    edges=edges,
                    total_weight=total_weight,
                    semantic_score=semantic_score,
                    hop_count=hops,
                    reasoning_path=reasoning_path,
                )
                results.append(result)

            # Add neighbors to queue
            neighbors = self.graph.get_neighbors(node_id)
            for neighbor_id, edge in neighbors:
                if neighbor_id not in local_visited and edge.weight >= min_weight:
                    queue.append(
                        (
                            neighbor_id,
                            path + [node_id],
                            edges + [edge],
                            total_weight + edge.weight,
                            hops + 1,
                        )
                    )

        return results

    def _weighted_traversal(
        self,
        start_node_id: str,
        query_analysis: QueryAnalysis | None,
        max_hops: int,
        max_results: int,
        min_weight: float,
    ) -> list[TraversalResult]:
        """Weighted traversal prioritizing strong relationships."""

        results = []
        # Priority queue: (negative_weight, node_id, path, edges, weight, hops)
        heap = [(-1.0, start_node_id, [], [], 0.0, 0)]
        local_visited = set()

        while heap and len(results) < max_results:
            neg_weight, node_id, path, edges, total_weight, hops = heapq.heappop(heap)

            if node_id in local_visited or hops > max_hops:
                continue

            local_visited.add(node_id)

            # Create traversal result
            if node_id != start_node_id:
                semantic_score = self._calculate_semantic_score(node_id, query_analysis)
                reasoning_path = build_reasoning_path(edges, self.graph.nodes)

                result = TraversalResult(
                    path=path + [node_id],
                    nodes=[self.graph.nodes[nid] for nid in path + [node_id]],
                    edges=edges,
                    total_weight=total_weight,
                    semantic_score=semantic_score,
                    hop_count=hops,
                    reasoning_path=reasoning_path,
                )
                results.append(result)

            # Add neighbors to heap
            neighbors = self.graph.get_neighbors(node_id)
            for neighbor_id, edge in neighbors:
                if neighbor_id not in local_visited and edge.weight >= min_weight:
                    new_weight = total_weight + edge.weight
                    heapq.heappush(
                        heap,
                        (
                            -new_weight,  # Negative for max-heap behavior
                            neighbor_id,
                            path + [node_id],
                            edges + [edge],
                            new_weight,
                            hops + 1,
                        ),
                    )

        return results

    def _centrality_traversal(
        self,
        start_node_id: str,
        query_analysis: QueryAnalysis | None,
        max_hops: int,
        max_results: int,
        min_weight: float,
    ) -> list[TraversalResult]:
        """Traversal prioritizing high-centrality nodes."""

        results = []
        # Priority queue: (negative_centrality, node_id, path, edges, weight, hops)
        start_centrality = self.graph.nodes[start_node_id].centrality_score
        heap = [(-start_centrality, start_node_id, [], [], 0.0, 0)]
        local_visited = set()

        while heap and len(results) < max_results:
            neg_centrality, node_id, path, edges, total_weight, hops = heapq.heappop(
                heap
            )

            if node_id in local_visited or hops > max_hops:
                continue

            local_visited.add(node_id)

            # Create traversal result
            if node_id != start_node_id:
                semantic_score = self._calculate_semantic_score(node_id, query_analysis)
                reasoning_path = build_reasoning_path(edges, self.graph.nodes)

                result = TraversalResult(
                    path=path + [node_id],
                    nodes=[self.graph.nodes[nid] for nid in path + [node_id]],
                    edges=edges,
                    total_weight=total_weight,
                    semantic_score=semantic_score,
                    hop_count=hops,
                    reasoning_path=reasoning_path,
                )
                results.append(result)

            # Add neighbors to heap
            neighbors = self.graph.get_neighbors(node_id)
            for neighbor_id, edge in neighbors:
                if neighbor_id not in local_visited and edge.weight >= min_weight:
                    neighbor_centrality = self.graph.nodes[neighbor_id].centrality_score
                    heapq.heappush(
                        heap,
                        (
                            -neighbor_centrality,
                            neighbor_id,
                            path + [node_id],
                            edges + [edge],
                            total_weight + edge.weight,
                            hops + 1,
                        ),
                    )

        return results

    def _semantic_traversal(
        self,
        start_node_id: str,
        query_analysis: QueryAnalysis | None,
        max_hops: int,
        max_results: int,
        min_weight: float,
    ) -> list[TraversalResult]:
        """Traversal prioritizing semantic similarity to query."""

        if not query_analysis:
            return self._breadth_first_traversal(
                start_node_id,
                query_analysis,
                max_hops,
                max_results,
                min_weight,
            )

        results = []
        # Priority queue: (negative_semantic_score, node_id, path, edges, weight, hops)
        start_score = self._calculate_semantic_score(start_node_id, query_analysis)
        heap = [(-start_score, start_node_id, [], [], 0.0, 0)]
        local_visited = set()

        while heap and len(results) < max_results:
            neg_score, node_id, path, edges, total_weight, hops = heapq.heappop(heap)

            if node_id in local_visited or hops > max_hops:
                continue

            local_visited.add(node_id)

            # Create traversal result
            if node_id != start_node_id:
                semantic_score = -neg_score  # Convert back from negative
                reasoning_path = build_reasoning_path(edges, self.graph.nodes)

                result = TraversalResult(
                    path=path + [node_id],
                    nodes=[self.graph.nodes[nid] for nid in path + [node_id]],
                    edges=edges,
                    total_weight=total_weight,
                    semantic_score=semantic_score,
                    hop_count=hops,
                    reasoning_path=reasoning_path,
                )
                results.append(result)

            # Add neighbors to heap
            neighbors = self.graph.get_neighbors(node_id)
            for neighbor_id, edge in neighbors:
                if neighbor_id not in local_visited and edge.weight >= min_weight:
                    neighbor_score = self._calculate_semantic_score(
                        neighbor_id, query_analysis
                    )
                    heapq.heappush(
                        heap,
                        (
                            -neighbor_score,
                            neighbor_id,
                            path + [node_id],
                            edges + [edge],
                            total_weight + edge.weight,
                            hops + 1,
                        ),
                    )

        return results

    def _calculate_semantic_score(
        self, node_id: str, query_analysis: QueryAnalysis | None
    ) -> float:
        """Calculate semantic similarity between node and query."""
        if not query_analysis:
            return 0.0

        node = self.graph.nodes[node_id]

        # Calculate similarity based on entities, topics, and keywords
        entity_similarity = calculate_list_similarity(
            query_analysis.entities, [(e, "") for e in node.entities]
        )

        topic_similarity = calculate_list_similarity(
            [(t, "") for t in query_analysis.main_concepts],
            [(t, "") for t in node.topics],
        )

        keyword_similarity = calculate_list_similarity(
            [(k, "") for k in query_analysis.semantic_keywords],
            [(k, "") for k in node.keywords],
        )

        # Weighted combination
        total_score = (
            entity_similarity * ENTITY_SIM_WEIGHT
            + topic_similarity * TOPIC_SIM_WEIGHT
            + keyword_similarity * KEYWORD_SIM_WEIGHT
        )

        return total_score
