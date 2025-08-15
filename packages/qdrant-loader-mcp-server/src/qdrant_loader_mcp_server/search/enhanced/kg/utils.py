from __future__ import annotations

from typing import List, Tuple

from .models import GraphEdge, GraphNode


# Default weights and thresholds used across KG computations
ENTITY_SIM_WEIGHT: float = 0.4
TOPIC_SIM_WEIGHT: float = 0.3
KEYWORD_SIM_WEIGHT: float = 0.3
SIMILARITY_EDGE_THRESHOLD: float = 0.3


def jaccard_similarity(set1: set[str], set2: set[str]) -> float:
    """Calculate Jaccard similarity between two sets."""
    if not set1 or not set2:
        return 0.0

    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))

    return intersection / max(union, 1)


def calculate_list_similarity(
    list1: List[Tuple[str, str]], list2: List[Tuple[str, str]]
) -> float:
    """Calculate similarity between two lists of (text, label) items."""
    if not list1 or not list2:
        return 0.0

    set1 = {item[0].lower() for item in list1}
    set2 = {item[0].lower() for item in list2}

    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))

    return intersection / max(union, 1)


def calculate_node_similarity(node1: GraphNode, node2: GraphNode) -> float:
    """Calculate semantic similarity between two KG nodes."""
    entity_similarity = jaccard_similarity(set(node1.entities), set(node2.entities))
    topic_similarity = jaccard_similarity(set(node1.topics), set(node2.topics))
    keyword_similarity = jaccard_similarity(set(node1.keywords), set(node2.keywords))

    total_similarity = (
        entity_similarity * ENTITY_SIM_WEIGHT
        + topic_similarity * TOPIC_SIM_WEIGHT
        + keyword_similarity * KEYWORD_SIM_WEIGHT
    )
    return total_similarity


def build_reasoning_path(path: list[str], edges: list[GraphEdge], nodes_by_id: dict[str, GraphNode]) -> list[str]:
    """Build a human-readable reasoning path from a traversal."""
    reasoning: list[str] = []
    for _i, edge in enumerate(edges):
        source_node = nodes_by_id[edge.source_id]
        target_node = nodes_by_id[edge.target_id]
        reasoning.append(
            f"{source_node.title} --{edge.relationship_type.value}--> {target_node.title} "
            f"(weight: {edge.weight:.2f})"
        )
    return reasoning


