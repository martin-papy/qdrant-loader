from __future__ import annotations

import logging

from .models import GraphEdge, GraphNode

# Module-level logger
logger = logging.getLogger(__name__)

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
    list1: list[tuple[str, str]], list2: list[tuple[str, str]]
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


def _get_relationship_value(edge: GraphEdge | object) -> str:
    """Safely extract the relationship value string from an edge.

    Handles Enum, None, raw string, or objects with a ``value`` attribute.
    Falls back to "unknown" when it cannot determine a proper value.
    """
    relationship_type = getattr(edge, "relationship_type", None)
    if relationship_type is None:
        return "unknown"
    # Enum-like objects expose a .value string
    try:
        from enum import Enum

        if isinstance(relationship_type, Enum):
            value = getattr(relationship_type, "value", None)
            if isinstance(value, str) and value:
                return value
            return "unknown"
    except Exception:
        # If Enum isn't available or isinstance check fails, continue with other strategies
        pass

    # Raw string
    if isinstance(relationship_type, str):
        return relationship_type

    # Objects with a .value attribute
    value_attr = getattr(relationship_type, "value", None)
    if isinstance(value_attr, str) and value_attr:
        return value_attr

    # Fallback to string conversion; ensure we always return something
    try:
        return str(relationship_type)
    except Exception:
        return "unknown"


def build_reasoning_path(
    edges: list[GraphEdge], nodes_by_id: dict[str, GraphNode]
) -> list[str]:
    """Build a human-readable reasoning path from a traversal.

    Parameters
    - edges: Ordered list of graph edges traversed.
    - nodes_by_id: Mapping from node id to `GraphNode` for resolving titles.
    """
    reasoning: list[str] = []
    for _i, edge in enumerate(edges):
        source_node = nodes_by_id.get(edge.source_id)
        target_node = nodes_by_id.get(edge.target_id)

        if source_node is None or target_node is None:
            edge_id = getattr(edge, "id", "N/A")
            relationship = _get_relationship_value(edge)
            logger.warning(
                "KG reasoning: missing node(s) for edge. edge_id=%s relationship=%s source_id=%s found=%s target_id=%s found=%s",
                edge_id,
                relationship,
                getattr(edge, "source_id", "N/A"),
                source_node is not None,
                getattr(edge, "target_id", "N/A"),
                target_node is not None,
            )

        source_title = (
            source_node.title
            if source_node is not None
            else f"UNKNOWN NODE {getattr(edge, 'source_id', 'N/A')}"
        )
        target_title = (
            target_node.title
            if target_node is not None
            else f"UNKNOWN NODE {getattr(edge, 'target_id', 'N/A')}"
        )

        relationship_value = _get_relationship_value(edge)

        reasoning.append(
            f"{source_title} --{relationship_value}--> {target_title} "
            f"(weight: {getattr(edge, 'weight', 0.0):.2f})"
        )
    return reasoning
