"""
Knowledge Graph for Search Enhancement.

This module implements knowledge graph capabilities for search enhancement:
- Multi-node graph construction from document metadata
- Relationship extraction and strength scoring
- Graph traversal algorithms for multi-hop search
- Integration with spaCy-powered components
"""
import json
import time
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx

from ...utils.logging import LoggingConfig
from ..nlp.spacy_analyzer import SpaCyQueryAnalyzer, QueryAnalysis
from ..models import SearchResult

logger = LoggingConfig.get_logger(__name__)


class NodeType(Enum):
    """Types of nodes in the knowledge graph."""
    DOCUMENT = "document"
    SECTION = "section"
    ENTITY = "entity"
    TOPIC = "topic"
    CONCEPT = "concept"


class RelationshipType(Enum):
    """Types of relationships between graph nodes."""
    # Hierarchical relationships
    CONTAINS = "contains"  # document contains section, section contains subsection
    PART_OF = "part_of"   # inverse of contains
    SIBLING = "sibling"   # sections at same level
    
    # Content relationships  
    MENTIONS = "mentions"           # document/section mentions entity
    DISCUSSES = "discusses"         # document/section discusses topic
    RELATES_TO = "relates_to"      # generic semantic relationship
    SIMILAR_TO = "similar_to"      # semantic similarity
    
    # Cross-document relationships
    REFERENCES = "references"       # explicit cross-reference
    CITES = "cites"                # citation relationship
    BUILDS_ON = "builds_on"        # conceptual building
    CONTRADICTS = "contradicts"    # conflicting information
    
    # Entity relationships
    CO_OCCURS = "co_occurs"        # entities appear together
    CATEGORIZED_AS = "categorized_as"  # entity belongs to topic/concept


@dataclass
class GraphNode:
    """Node in the knowledge graph."""
    
    id: str
    node_type: NodeType
    title: str
    content: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Graph metrics (calculated)
    centrality_score: float = 0.0
    authority_score: float = 0.0
    hub_score: float = 0.0
    
    # Content analysis
    entities: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    concepts: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize derived properties."""
        if not self.id:
            self.id = f"{self.node_type.value}_{hash(self.title)}"


@dataclass
class GraphEdge:
    """Edge in the knowledge graph."""
    
    source_id: str
    target_id: str
    relationship_type: RelationshipType
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Evidence for the relationship
    evidence: List[str] = field(default_factory=list)
    confidence: float = 1.0
    
    def __post_init__(self):
        """Normalize weight and confidence."""
        self.weight = max(0.0, min(1.0, self.weight))
        self.confidence = max(0.0, min(1.0, self.confidence))


class TraversalStrategy(Enum):
    """Graph traversal strategies for different search goals."""
    BREADTH_FIRST = "breadth_first"      # Explore broadly
    DEPTH_FIRST = "depth_first"          # Explore deeply
    WEIGHTED = "weighted"                # Follow strongest relationships
    CENTRALITY = "centrality"            # Prefer high-centrality nodes
    SEMANTIC = "semantic"                # Follow semantic similarity
    HIERARCHICAL = "hierarchical"       # Follow document structure


@dataclass
class TraversalResult:
    """Result of graph traversal operation."""
    
    path: List[str]                      # Node IDs in traversal order
    nodes: List[GraphNode]               # Actual node objects
    relationships: List[GraphEdge]       # Edges traversed
    total_weight: float                  # Sum of edge weights
    semantic_score: float                # Semantic relevance to query
    hop_count: int                       # Number of hops from start
    reasoning_path: List[str]            # Human-readable reasoning


class KnowledgeGraph:
    """Core knowledge graph implementation using NetworkX."""
    
    def __init__(self):
        """Initialize the knowledge graph."""
        self.graph = nx.MultiDiGraph()  # Allow multiple edges between nodes
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: Dict[Tuple[str, str, str], GraphEdge] = {}  # (source, target, relationship)
        self.node_type_index: Dict[NodeType, Set[str]] = defaultdict(set)
        self.entity_index: Dict[str, Set[str]] = defaultdict(set)  # entity -> node_ids
        self.topic_index: Dict[str, Set[str]] = defaultdict(set)   # topic -> node_ids
        
        logger.info("Initialized empty knowledge graph")
    
    def add_node(self, node: GraphNode) -> bool:
        """Add a node to the graph."""
        try:
            if node.id in self.nodes:
                logger.debug(f"Node {node.id} already exists, updating")
            
            self.nodes[node.id] = node
            self.graph.add_node(node.id, **node.metadata)
            self.node_type_index[node.node_type].add(node.id)
            
            # Index entities and topics for fast lookup
            for entity in node.entities:
                self.entity_index[entity.lower()].add(node.id)
            for topic in node.topics:
                self.topic_index[topic.lower()].add(node.id)
            
            logger.debug(f"Added {node.node_type.value} node: {node.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add node {node.id}: {e}")
            return False
    
    def add_edge(self, edge: GraphEdge) -> bool:
        """Add an edge to the graph."""
        try:
            if edge.source_id not in self.nodes or edge.target_id not in self.nodes:
                logger.warning(f"Edge {edge.source_id} -> {edge.target_id}: missing nodes")
                return False
            
            edge_key = (edge.source_id, edge.target_id, edge.relationship_type.value)
            self.edges[edge_key] = edge
            
            self.graph.add_edge(
                edge.source_id, 
                edge.target_id,
                key=edge.relationship_type.value,
                weight=edge.weight,
                relationship=edge.relationship_type.value,
                confidence=edge.confidence,
                **edge.metadata
            )
            
            logger.debug(f"Added edge: {edge.source_id} --{edge.relationship_type.value}--> {edge.target_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add edge {edge.source_id} -> {edge.target_id}: {e}")
            return False
    
    def find_nodes_by_type(self, node_type: NodeType) -> List[GraphNode]:
        """Find all nodes of a specific type."""
        return [self.nodes[node_id] for node_id in self.node_type_index[node_type]]
    
    def find_nodes_by_entity(self, entity: str) -> List[GraphNode]:
        """Find all nodes containing a specific entity."""
        node_ids = self.entity_index.get(entity.lower(), set())
        return [self.nodes[node_id] for node_id in node_ids]
    
    def find_nodes_by_topic(self, topic: str) -> List[GraphNode]:
        """Find all nodes discussing a specific topic."""
        node_ids = self.topic_index.get(topic.lower(), set())
        return [self.nodes[node_id] for node_id in node_ids]
    
    def calculate_centrality_scores(self):
        """Calculate centrality scores for all nodes."""
        try:
            if len(self.graph.nodes) == 0:
                return
            
            # Calculate different centrality metrics
            degree_centrality = nx.degree_centrality(self.graph)
            betweenness_centrality = nx.betweenness_centrality(self.graph)
            
            # For directed graphs, calculate hub and authority scores
            try:
                hub_scores, authority_scores = nx.hits(self.graph, max_iter=100)
            except nx.PowerIterationFailedConvergence:
                logger.warning("HITS algorithm failed to converge, using default scores")
                hub_scores = {node: 0.0 for node in self.graph.nodes}
                authority_scores = {node: 0.0 for node in self.graph.nodes}
            
            # Update node objects with calculated scores
            for node_id, node in self.nodes.items():
                node.centrality_score = (
                    degree_centrality.get(node_id, 0.0) * 0.4 +
                    betweenness_centrality.get(node_id, 0.0) * 0.6
                )
                node.hub_score = hub_scores.get(node_id, 0.0)
                node.authority_score = authority_scores.get(node_id, 0.0)
            
            logger.info(f"Calculated centrality scores for {len(self.nodes)} nodes")
            
        except Exception as e:
            logger.error(f"Failed to calculate centrality scores: {e}")
    
    def get_neighbors(self, node_id: str, relationship_types: Optional[List[RelationshipType]] = None) -> List[Tuple[str, GraphEdge]]:
        """Get neighboring nodes with their connecting edges."""
        neighbors = []
        
        if node_id not in self.graph:
            return neighbors
        
        for neighbor_id in self.graph.neighbors(node_id):
            # Get all edges between these nodes
            edge_data = self.graph.get_edge_data(node_id, neighbor_id)
            if edge_data:
                for key, data in edge_data.items():
                    relationship = RelationshipType(data['relationship'])
                    if relationship_types is None or relationship in relationship_types:
                        edge_key = (node_id, neighbor_id, relationship.value)
                        if edge_key in self.edges:
                            neighbors.append((neighbor_id, self.edges[edge_key]))
        
        return neighbors
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get graph statistics."""
        stats = {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "node_types": {node_type.value: len(nodes) for node_type, nodes in self.node_type_index.items()},
            "relationship_types": {},
            "connected_components": nx.number_weakly_connected_components(self.graph),
            "avg_degree": sum(dict(self.graph.degree()).values()) / max(len(self.graph.nodes), 1)
        }
        
        # Count relationship types
        for edge in self.edges.values():
            rel_type = edge.relationship_type.value
            stats["relationship_types"][rel_type] = stats["relationship_types"].get(rel_type, 0) + 1
        
        return stats


class GraphTraverser:
    """Advanced graph traversal for multi-hop search and content discovery."""
    
    def __init__(self, knowledge_graph: KnowledgeGraph, spacy_analyzer: Optional[SpaCyQueryAnalyzer] = None):
        """Initialize the graph traverser."""
        self.graph = knowledge_graph
        self.spacy_analyzer = spacy_analyzer or SpaCyQueryAnalyzer()
        logger.debug("Initialized graph traverser")
    
    def traverse(
        self, 
        start_nodes: List[str], 
        query_analysis: Optional[QueryAnalysis] = None,
        strategy: TraversalStrategy = TraversalStrategy.WEIGHTED,
        max_hops: int = 3,
        max_results: int = 20,
        min_weight: float = 0.1
    ) -> List[TraversalResult]:
        """Traverse the graph to find related content."""
        
        results = []
        visited = set()
        
        for start_node_id in start_nodes:
            if start_node_id not in self.graph.nodes:
                continue
            
            # Perform traversal based on strategy
            if strategy == TraversalStrategy.BREADTH_FIRST:
                node_results = self._breadth_first_traversal(
                    start_node_id, query_analysis, max_hops, max_results, min_weight, visited
                )
            elif strategy == TraversalStrategy.WEIGHTED:
                node_results = self._weighted_traversal(
                    start_node_id, query_analysis, max_hops, max_results, min_weight, visited
                )
            elif strategy == TraversalStrategy.CENTRALITY:
                node_results = self._centrality_traversal(
                    start_node_id, query_analysis, max_hops, max_results, min_weight, visited
                )
            elif strategy == TraversalStrategy.SEMANTIC:
                node_results = self._semantic_traversal(
                    start_node_id, query_analysis, max_hops, max_results, min_weight, visited
                )
            else:
                node_results = self._breadth_first_traversal(
                    start_node_id, query_analysis, max_hops, max_results, min_weight, visited
                )
            
            results.extend(node_results)
        
        # Sort by semantic score and total weight
        results.sort(key=lambda r: (r.semantic_score, r.total_weight), reverse=True)
        return results[:max_results]
    
    def _breadth_first_traversal(
        self, 
        start_node_id: str, 
        query_analysis: Optional[QueryAnalysis],
        max_hops: int, 
        max_results: int, 
        min_weight: float,
        visited: Set[str]
    ) -> List[TraversalResult]:
        """Breadth-first traversal implementation."""
        
        results = []
        queue = [(start_node_id, [], [], 0.0, 0)]  # (node_id, path, edges, weight, hops)
        local_visited = set()
        
        while queue and len(results) < max_results:
            node_id, path, edges, total_weight, hops = queue.pop(0)
            
            if node_id in local_visited or hops >= max_hops:
                continue
            
            local_visited.add(node_id)
            
            # Create traversal result
            if node_id != start_node_id:  # Don't include the starting node
                semantic_score = self._calculate_semantic_score(node_id, query_analysis)
                reasoning_path = self._build_reasoning_path(path, edges)
                
                result = TraversalResult(
                    path=path + [node_id],
                    nodes=[self.graph.nodes[nid] for nid in path + [node_id]],
                    relationships=edges,
                    total_weight=total_weight,
                    semantic_score=semantic_score,
                    hop_count=hops,
                    reasoning_path=reasoning_path
                )
                results.append(result)
            
            # Add neighbors to queue
            neighbors = self.graph.get_neighbors(node_id)
            for neighbor_id, edge in neighbors:
                if neighbor_id not in local_visited and edge.weight >= min_weight:
                    queue.append((
                        neighbor_id,
                        path + [node_id],
                        edges + [edge],
                        total_weight + edge.weight,
                        hops + 1
                    ))
        
        return results
    
    def _weighted_traversal(
        self, 
        start_node_id: str, 
        query_analysis: Optional[QueryAnalysis],
        max_hops: int, 
        max_results: int, 
        min_weight: float,
        visited: Set[str]
    ) -> List[TraversalResult]:
        """Weighted traversal prioritizing strong relationships."""
        
        results = []
        # Priority queue: (negative_weight, node_id, path, edges, weight, hops)
        import heapq
        heap = [(-1.0, start_node_id, [], [], 0.0, 0)]
        local_visited = set()
        
        while heap and len(results) < max_results:
            neg_weight, node_id, path, edges, total_weight, hops = heapq.heappop(heap)
            
            if node_id in local_visited or hops >= max_hops:
                continue
            
            local_visited.add(node_id)
            
            # Create traversal result
            if node_id != start_node_id:
                semantic_score = self._calculate_semantic_score(node_id, query_analysis)
                reasoning_path = self._build_reasoning_path(path, edges)
                
                result = TraversalResult(
                    path=path + [node_id],
                    nodes=[self.graph.nodes[nid] for nid in path + [node_id]],
                    relationships=edges,
                    total_weight=total_weight,
                    semantic_score=semantic_score,
                    hop_count=hops,
                    reasoning_path=reasoning_path
                )
                results.append(result)
            
            # Add neighbors to heap
            neighbors = self.graph.get_neighbors(node_id)
            for neighbor_id, edge in neighbors:
                if neighbor_id not in local_visited and edge.weight >= min_weight:
                    new_weight = total_weight + edge.weight
                    heapq.heappush(heap, (
                        -new_weight,  # Negative for max-heap behavior
                        neighbor_id,
                        path + [node_id],
                        edges + [edge],
                        new_weight,
                        hops + 1
                    ))
        
        return results
    
    def _centrality_traversal(
        self, 
        start_node_id: str, 
        query_analysis: Optional[QueryAnalysis],
        max_hops: int, 
        max_results: int, 
        min_weight: float,
        visited: Set[str]
    ) -> List[TraversalResult]:
        """Traversal prioritizing high-centrality nodes."""
        
        results = []
        import heapq
        # Priority queue: (negative_centrality, node_id, path, edges, weight, hops)
        start_centrality = self.graph.nodes[start_node_id].centrality_score
        heap = [(-start_centrality, start_node_id, [], [], 0.0, 0)]
        local_visited = set()
        
        while heap and len(results) < max_results:
            neg_centrality, node_id, path, edges, total_weight, hops = heapq.heappop(heap)
            
            if node_id in local_visited or hops >= max_hops:
                continue
            
            local_visited.add(node_id)
            
            # Create traversal result
            if node_id != start_node_id:
                semantic_score = self._calculate_semantic_score(node_id, query_analysis)
                reasoning_path = self._build_reasoning_path(path, edges)
                
                result = TraversalResult(
                    path=path + [node_id],
                    nodes=[self.graph.nodes[nid] for nid in path + [node_id]],
                    relationships=edges,
                    total_weight=total_weight,
                    semantic_score=semantic_score,
                    hop_count=hops,
                    reasoning_path=reasoning_path
                )
                results.append(result)
            
            # Add neighbors to heap
            neighbors = self.graph.get_neighbors(node_id)
            for neighbor_id, edge in neighbors:
                if neighbor_id not in local_visited and edge.weight >= min_weight:
                    neighbor_centrality = self.graph.nodes[neighbor_id].centrality_score
                    heapq.heappush(heap, (
                        -neighbor_centrality,
                        neighbor_id,
                        path + [node_id],
                        edges + [edge],
                        total_weight + edge.weight,
                        hops + 1
                    ))
        
        return results
    
    def _semantic_traversal(
        self, 
        start_node_id: str, 
        query_analysis: Optional[QueryAnalysis],
        max_hops: int, 
        max_results: int, 
        min_weight: float,
        visited: Set[str]
    ) -> List[TraversalResult]:
        """Traversal prioritizing semantic similarity to query."""
        
        if not query_analysis:
            return self._breadth_first_traversal(start_node_id, query_analysis, max_hops, max_results, min_weight, visited)
        
        results = []
        import heapq
        # Priority queue: (negative_semantic_score, node_id, path, edges, weight, hops)
        start_score = self._calculate_semantic_score(start_node_id, query_analysis)
        heap = [(-start_score, start_node_id, [], [], 0.0, 0)]
        local_visited = set()
        
        while heap and len(results) < max_results:
            neg_score, node_id, path, edges, total_weight, hops = heapq.heappop(heap)
            
            if node_id in local_visited or hops >= max_hops:
                continue
            
            local_visited.add(node_id)
            
            # Create traversal result
            if node_id != start_node_id:
                semantic_score = -neg_score  # Convert back from negative
                reasoning_path = self._build_reasoning_path(path, edges)
                
                result = TraversalResult(
                    path=path + [node_id],
                    nodes=[self.graph.nodes[nid] for nid in path + [node_id]],
                    relationships=edges,
                    total_weight=total_weight,
                    semantic_score=semantic_score,
                    hop_count=hops,
                    reasoning_path=reasoning_path
                )
                results.append(result)
            
            # Add neighbors to heap
            neighbors = self.graph.get_neighbors(node_id)
            for neighbor_id, edge in neighbors:
                if neighbor_id not in local_visited and edge.weight >= min_weight:
                    neighbor_score = self._calculate_semantic_score(neighbor_id, query_analysis)
                    heapq.heappush(heap, (
                        -neighbor_score,
                        neighbor_id,
                        path + [node_id],
                        edges + [edge],
                        total_weight + edge.weight,
                        hops + 1
                    ))
        
        return results
    
    def _calculate_semantic_score(self, node_id: str, query_analysis: Optional[QueryAnalysis]) -> float:
        """Calculate semantic similarity between node and query."""
        if not query_analysis:
            return 0.0
        
        node = self.graph.nodes[node_id]
        
        # Calculate similarity based on entities, topics, and keywords
        entity_similarity = self._calculate_list_similarity(
            query_analysis.entities, [(e, "") for e in node.entities]
        )
        
        topic_similarity = self._calculate_list_similarity(
            [(t, "") for t in query_analysis.main_concepts], [(t, "") for t in node.topics]
        )
        
        keyword_similarity = self._calculate_list_similarity(
            [(k, "") for k in query_analysis.semantic_keywords], [(k, "") for k in node.keywords]
        )
        
        # Weighted combination
        total_score = (
            entity_similarity * 0.4 +
            topic_similarity * 0.3 +
            keyword_similarity * 0.3
        )
        
        return total_score
    
    def _calculate_list_similarity(self, list1: List[Tuple[str, str]], list2: List[Tuple[str, str]]) -> float:
        """Calculate similarity between two lists of items."""
        if not list1 or not list2:
            return 0.0
        
        set1 = set(item[0].lower() for item in list1)
        set2 = set(item[0].lower() for item in list2)
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / max(union, 1)
    
    def _build_reasoning_path(self, path: List[str], edges: List[GraphEdge]) -> List[str]:
        """Build human-readable reasoning path."""
        reasoning = []
        
        for i, edge in enumerate(edges):
            source_node = self.graph.nodes[edge.source_id]
            target_node = self.graph.nodes[edge.target_id]
            
            reasoning.append(
                f"{source_node.title} --{edge.relationship_type.value}--> {target_node.title} "
                f"(weight: {edge.weight:.2f})"
            )
        
        return reasoning


class GraphBuilder:
    """Build knowledge graph from document metadata and search results."""
    
    def __init__(self, spacy_analyzer: Optional[SpaCyQueryAnalyzer] = None):
        """Initialize the graph builder."""
        self.spacy_analyzer = spacy_analyzer or SpaCyQueryAnalyzer()
        logger.info("Initialized graph builder")
    
    def build_from_search_results(self, search_results: List[SearchResult]) -> KnowledgeGraph:
        """Build knowledge graph from search results metadata."""
        
        start_time = time.time()
        graph = KnowledgeGraph()
        
        try:
            # Step 1: Create nodes from search results
            document_nodes = self._create_document_nodes(search_results)
            for node in document_nodes:
                graph.add_node(node)
            
            # Step 2: Create entity and topic nodes
            entity_nodes, topic_nodes = self._create_concept_nodes(search_results)
            for node in entity_nodes + topic_nodes:
                graph.add_node(node)
            
            # Step 3: Create relationships
            edges = self._create_relationships(search_results, graph)
            for edge in edges:
                graph.add_edge(edge)
            
            # Step 4: Calculate centrality scores
            graph.calculate_centrality_scores()
            
            build_time = (time.time() - start_time) * 1000
            stats = graph.get_statistics()
            
            logger.info(
                f"Built knowledge graph in {build_time:.2f}ms",
                nodes=stats["total_nodes"],
                edges=stats["total_edges"],
                components=stats["connected_components"]
            )
            
            return graph
            
        except Exception as e:
            logger.error(f"Failed to build knowledge graph: {e}")
            return graph
    
    def _create_document_nodes(self, search_results: List[SearchResult]) -> List[GraphNode]:
        """Create document and section nodes from search results."""
        
        nodes = []
        seen_documents = set()
        
        for result in search_results:
            # Create document node
            doc_id = f"doc_{result.source_type}_{hash(result.source_url or result.text[:100])}"
            
            if doc_id not in seen_documents:
                seen_documents.add(doc_id)
                
                doc_node = GraphNode(
                    id=doc_id,
                    node_type=NodeType.DOCUMENT,
                    title=result.source_title or f"Document from {result.source_type}",
                    content=result.text[:500],  # First 500 chars as summary
                    metadata={
                        "source_type": result.source_type,
                        "source_title": result.source_title,
                        "url": result.source_url,
                        "project_id": result.project_id,
                        "collection_name": result.collection_name
                    },
                    entities=self._extract_entities(result),
                    topics=self._extract_topics(result),
                    concepts=self._extract_concepts(result),
                    keywords=self._extract_keywords(result)
                )
                nodes.append(doc_node)
            
            # Create section node
            section_id = f"section_{hash(result.text)}"
            section_node = GraphNode(
                id=section_id,
                node_type=NodeType.SECTION,
                title=(result.section_title or result.breadcrumb_text or "Section")[-50:],  # Last 50 chars
                content=result.text,
                metadata={
                    "parent_document": doc_id,
                    "breadcrumb": result.breadcrumb_text,
                    "section_level": result.section_level or result.depth,
                    "score": result.score,
                    "section_type": result.section_type
                },
                entities=self._extract_entities(result),
                topics=self._extract_topics(result),
                concepts=self._extract_concepts(result),
                keywords=self._extract_keywords(result)
            )
            nodes.append(section_node)
        
        return nodes
    
    def _create_concept_nodes(self, search_results: List[SearchResult]) -> Tuple[List[GraphNode], List[GraphNode]]:
        """Create entity and topic nodes from extracted metadata."""
        
        # Collect all entities and topics
        entity_counts = Counter()
        topic_counts = Counter()
        
        for result in search_results:
            entities = self._extract_entities(result)
            topics = self._extract_topics(result)
            
            for entity in entities:
                entity_counts[entity] += 1
            for topic in topics:
                topic_counts[topic] += 1
        
        # Create nodes for frequent entities and topics
        entity_nodes = []
        topic_nodes = []
        
        # Entities mentioned in at least 2 documents
        for entity, count in entity_counts.items():
            if count >= 2:
                entity_node = GraphNode(
                    id=f"entity_{hash(entity)}",
                    node_type=NodeType.ENTITY,
                    title=entity,
                    metadata={"mention_count": count, "entity_type": "extracted"}
                )
                entity_nodes.append(entity_node)
        
        # Topics mentioned in at least 2 documents
        for topic, count in topic_counts.items():
            if count >= 2:
                topic_node = GraphNode(
                    id=f"topic_{hash(topic)}",
                    node_type=NodeType.TOPIC,
                    title=topic,
                    metadata={"mention_count": count, "topic_type": "extracted"}
                )
                topic_nodes.append(topic_node)
        
        return entity_nodes, topic_nodes
    
    def _create_relationships(self, search_results: List[SearchResult], graph: KnowledgeGraph) -> List[GraphEdge]:
        """Create relationships between graph nodes."""
        
        edges = []
        
        # Document -> Section relationships
        for result in search_results:
            doc_id = f"doc_{result.source_type}_{hash(result.source_url or result.text[:100])}"
            section_id = f"section_{hash(result.text)}"
            
            if doc_id in graph.nodes and section_id in graph.nodes:
                edge = GraphEdge(
                    source_id=doc_id,
                    target_id=section_id,
                    relationship_type=RelationshipType.CONTAINS,
                    weight=1.0,
                    confidence=1.0,
                    evidence=["hierarchical_structure"]
                )
                edges.append(edge)
        
        # Entity relationships
        entity_edges = self._create_entity_relationships(search_results, graph)
        edges.extend(entity_edges)
        
        # Topic relationships  
        topic_edges = self._create_topic_relationships(search_results, graph)
        edges.extend(topic_edges)
        
        # Semantic similarity relationships
        similarity_edges = self._create_similarity_relationships(graph)
        edges.extend(similarity_edges)
        
        return edges
    
    def _create_entity_relationships(self, search_results: List[SearchResult], graph: KnowledgeGraph) -> List[GraphEdge]:
        """Create entity-related relationships."""
        
        edges = []
        
        # Document/Section mentions Entity
        for result in search_results:
            section_id = f"section_{hash(result.text)}"
            entities = self._extract_entities(result)
            
            for entity in entities:
                entity_nodes = graph.find_nodes_by_entity(entity)
                for entity_node in entity_nodes:
                    if section_id in graph.nodes:
                        edge = GraphEdge(
                            source_id=section_id,
                            target_id=entity_node.id,
                            relationship_type=RelationshipType.MENTIONS,
                            weight=0.7,
                            confidence=0.8,
                            evidence=[f"entity_extraction: {entity}"]
                        )
                        edges.append(edge)
        
        # Entity co-occurrence relationships
        co_occurrence_edges = self._create_entity_cooccurrence(search_results, graph)
        edges.extend(co_occurrence_edges)
        
        return edges
    
    def _create_topic_relationships(self, search_results: List[SearchResult], graph: KnowledgeGraph) -> List[GraphEdge]:
        """Create topic-related relationships."""
        
        edges = []
        
        # Document/Section discusses Topic
        for result in search_results:
            section_id = f"section_{hash(result.text)}"
            topics = self._extract_topics(result)
            
            for topic in topics:
                topic_nodes = graph.find_nodes_by_topic(topic)
                for topic_node in topic_nodes:
                    if section_id in graph.nodes:
                        edge = GraphEdge(
                            source_id=section_id,
                            target_id=topic_node.id,
                            relationship_type=RelationshipType.DISCUSSES,
                            weight=0.6,
                            confidence=0.7,
                            evidence=[f"topic_extraction: {topic}"]
                        )
                        edges.append(edge)
        
        return edges
    
    def _create_entity_cooccurrence(self, search_results: List[SearchResult], graph: KnowledgeGraph) -> List[GraphEdge]:
        """Create entity co-occurrence relationships."""
        
        edges = []
        cooccurrence_counts = defaultdict(int)
        
        # Count entity co-occurrences
        for result in search_results:
            entities = self._extract_entities(result)
            for i, entity1 in enumerate(entities):
                for entity2 in entities[i+1:]:
                    pair = tuple(sorted([entity1, entity2]))
                    cooccurrence_counts[pair] += 1
        
        # Create edges for significant co-occurrences
        for (entity1, entity2), count in cooccurrence_counts.items():
            if count >= 2:  # Appeared together at least twice
                entity1_nodes = graph.find_nodes_by_entity(entity1)
                entity2_nodes = graph.find_nodes_by_entity(entity2)
                
                for node1 in entity1_nodes:
                    for node2 in entity2_nodes:
                        weight = min(1.0, count / 5.0)  # Normalize to max 1.0
                        edge = GraphEdge(
                            source_id=node1.id,
                            target_id=node2.id,
                            relationship_type=RelationshipType.CO_OCCURS,
                            weight=weight,
                            confidence=weight,
                            evidence=[f"co_occurrence_count: {count}"]
                        )
                        edges.append(edge)
        
        return edges
    
    def _create_similarity_relationships(self, graph: KnowledgeGraph) -> List[GraphEdge]:
        """Create semantic similarity relationships between nodes."""
        
        edges = []
        
        # Calculate similarity between section nodes
        section_nodes = graph.find_nodes_by_type(NodeType.SECTION)
        
        for i, node1 in enumerate(section_nodes):
            for node2 in section_nodes[i+1:]:
                similarity = self._calculate_node_similarity(node1, node2)
                
                if similarity > 0.3:  # Threshold for meaningful similarity
                    edge = GraphEdge(
                        source_id=node1.id,
                        target_id=node2.id,
                        relationship_type=RelationshipType.SIMILAR_TO,
                        weight=similarity,
                        confidence=similarity,
                        evidence=[f"semantic_similarity: {similarity:.3f}"]
                    )
                    edges.append(edge)
        
        return edges
    
    def _calculate_node_similarity(self, node1: GraphNode, node2: GraphNode) -> float:
        """Calculate similarity between two nodes."""
        
        # Entity overlap
        entity_similarity = self._jaccard_similarity(set(node1.entities), set(node2.entities))
        
        # Topic overlap
        topic_similarity = self._jaccard_similarity(set(node1.topics), set(node2.topics))
        
        # Keyword overlap
        keyword_similarity = self._jaccard_similarity(set(node1.keywords), set(node2.keywords))
        
        # Weighted combination
        total_similarity = (
            entity_similarity * 0.4 +
            topic_similarity * 0.3 +
            keyword_similarity * 0.3
        )
        
        return total_similarity
    
    def _jaccard_similarity(self, set1: Set[str], set2: Set[str]) -> float:
        """Calculate Jaccard similarity between two sets."""
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / max(union, 1)
    
    def _extract_entities(self, result: SearchResult) -> List[str]:
        """Extract entities from search result fields."""
        entities = []
        
        # Use available fields from the SearchResult model
        # Since the metadata structure is now flattened, we'll extract from text and titles
        if result.source_title:
            entities.append(result.source_title)
        
        if result.parent_title:
            entities.append(result.parent_title)
            
        if result.section_title:
            entities.append(result.section_title)
            
        # Basic entity extraction from project names
        if result.project_name:
            entities.append(result.project_name)
        
        return list(set(entities))  # Remove duplicates
    
    def _extract_topics(self, result: SearchResult) -> List[str]:
        """Extract topics from search result fields."""
        topics = []
        
        # From breadcrumb (hierarchical topics)
        if result.breadcrumb_text:
            topics.extend([section.strip() for section in result.breadcrumb_text.split(" > ")])
        
        # From section information
        if result.section_type:
            topics.append(result.section_type)
            
        # From source type as a topic
        if result.source_type:
            topics.append(result.source_type)
        
        return list(set(topics))
    
    def _extract_concepts(self, result: SearchResult) -> List[str]:
        """Extract concepts from search result fields."""
        concepts = []
        
        # Use section titles and breadcrumbs as concepts
        if result.section_title:
            concepts.append(result.section_title)
            
        if result.hierarchy_context:
            concepts.append(result.hierarchy_context)
        
        return list(set(concepts))
    
    def _extract_keywords(self, result: SearchResult) -> List[str]:
        """Extract keywords from search result text and titles."""
        keywords = []
        
        # Basic keyword extraction from text (first few words)
        text_words = result.text.lower().split()[:10]  # First 10 words
        keywords.extend([word for word in text_words if len(word) > 3 and word.isalpha()])
        
        # Keywords from titles
        if result.source_title:
            title_words = result.source_title.lower().split()
            keywords.extend([word for word in title_words if len(word) > 3 and word.isalpha()])
        
        return list(set(keywords))


class DocumentKnowledgeGraph:
    """High-level interface for document knowledge graph operations."""
    
    def __init__(self, spacy_analyzer: Optional[SpaCyQueryAnalyzer] = None):
        """Initialize the document knowledge graph system."""
        self.spacy_analyzer = spacy_analyzer or SpaCyQueryAnalyzer()
        self.graph_builder = GraphBuilder(self.spacy_analyzer)
        self.knowledge_graph: Optional[KnowledgeGraph] = None
        self.traverser: Optional[GraphTraverser] = None
        
        logger.info("Initialized document knowledge graph system")
    
    def build_graph(self, search_results: List[SearchResult]) -> bool:
        """Build knowledge graph from search results."""
        try:
            self.knowledge_graph = self.graph_builder.build_from_search_results(search_results)
            self.traverser = GraphTraverser(self.knowledge_graph, self.spacy_analyzer)
            
            stats = self.knowledge_graph.get_statistics()
            logger.info("Knowledge graph built successfully", **stats)
            return True
            
        except Exception as e:
            logger.error(f"Failed to build knowledge graph: {e}")
            return False
    
    def find_related_content(
        self, 
        query: str, 
        max_hops: int = 3, 
        max_results: int = 20,
        strategy: TraversalStrategy = TraversalStrategy.SEMANTIC
    ) -> List[TraversalResult]:
        """Find related content using graph traversal."""
        
        if not self.knowledge_graph or not self.traverser:
            logger.warning("Knowledge graph not initialized")
            return []
        
        try:
            # Analyze query with spaCy
            query_analysis = self.spacy_analyzer.analyze_query_semantic(query)
            
            # Find starting nodes based on query entities and concepts
            start_nodes = self._find_query_start_nodes(query_analysis)
            
            if not start_nodes:
                logger.debug("No starting nodes found for query")
                return []
            
            # Traverse graph to find related content
            results = self.traverser.traverse(
                start_nodes=start_nodes,
                query_analysis=query_analysis,
                strategy=strategy,
                max_hops=max_hops,
                max_results=max_results
            )
            
            logger.debug(f"Found {len(results)} related content items via graph traversal")
            return results
            
        except Exception as e:
            logger.error(f"Failed to find related content: {e}")
            return []
    
    def _find_query_start_nodes(self, query_analysis: QueryAnalysis) -> List[str]:
        """Find starting nodes for graph traversal based on query analysis."""
        
        start_nodes = []
        
        # Find nodes by entities
        for entity_text, entity_label in query_analysis.entities:
            entity_nodes = self.knowledge_graph.find_nodes_by_entity(entity_text)
            start_nodes.extend([node.id for node in entity_nodes])
        
        # Find nodes by main concepts (as topics)
        for concept in query_analysis.main_concepts:
            topic_nodes = self.knowledge_graph.find_nodes_by_topic(concept)
            start_nodes.extend([node.id for node in topic_nodes])
        
        # If no entity/topic matches, use high-centrality document nodes
        if not start_nodes:
            doc_nodes = self.knowledge_graph.find_nodes_by_type(NodeType.DOCUMENT)
            # Sort by centrality and take top 3
            doc_nodes.sort(key=lambda n: n.centrality_score, reverse=True)
            start_nodes = [node.id for node in doc_nodes[:3]]
        
        return list(set(start_nodes))  # Remove duplicates
    
    def get_graph_statistics(self) -> Optional[Dict[str, Any]]:
        """Get knowledge graph statistics."""
        if self.knowledge_graph:
            return self.knowledge_graph.get_statistics()
        return None
    
    def export_graph(self, format: str = "json") -> Optional[str]:
        """Export knowledge graph in specified format."""
        if not self.knowledge_graph:
            return None
        
        try:
            if format == "json":
                # Export as JSON with nodes and edges
                data = {
                    "nodes": [
                        {
                            "id": node.id,
                            "type": node.node_type.value,
                            "title": node.title,
                            "centrality": node.centrality_score,
                            "entities": node.entities,
                            "topics": node.topics
                        }
                        for node in self.knowledge_graph.nodes.values()
                    ],
                    "edges": [
                        {
                            "source": edge.source_id,
                            "target": edge.target_id,
                            "relationship": edge.relationship_type.value,
                            "weight": edge.weight,
                            "confidence": edge.confidence
                        }
                        for edge in self.knowledge_graph.edges.values()
                    ]
                }
                return json.dumps(data, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to export graph: {e}")
        
        return None 