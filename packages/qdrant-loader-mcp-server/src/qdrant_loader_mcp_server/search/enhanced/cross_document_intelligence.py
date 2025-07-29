"""
Cross-Document Intelligence

This module implements advanced cross-document relationship analysis that leverages
the rich metadata extracted during document ingestion. It provides intelligent
document clustering, similarity analysis, citation networks, and complementary
content discovery.

Key Features:
- Document similarity calculation using entity/topic/metadata overlap
- Intelligent document clustering based on shared concepts
- Citation network analysis from cross-references and hierarchical data
- Complementary content recommendation using knowledge graph
- Conflict detection between documents
- Cross-project relationship discovery
"""

import logging
import time
import math
import networkx as nx
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from datetime import datetime

from ...utils.logging import LoggingConfig
from ..nlp.spacy_analyzer import SpaCyQueryAnalyzer, QueryAnalysis
from ..models import SearchResult
from .knowledge_graph import DocumentKnowledgeGraph, NodeType, TraversalStrategy

logger = LoggingConfig.get_logger(__name__)


class SimilarityMetric(Enum):
    """Types of similarity metrics for document comparison."""
    ENTITY_OVERLAP = "entity_overlap"
    TOPIC_OVERLAP = "topic_overlap"
    SEMANTIC_SIMILARITY = "semantic_similarity"
    METADATA_SIMILARITY = "metadata_similarity"
    HIERARCHICAL_DISTANCE = "hierarchical_distance"
    CONTENT_FEATURES = "content_features"
    COMBINED = "combined"


class ClusteringStrategy(Enum):
    """Strategies for document clustering."""
    ENTITY_BASED = "entity_based"
    TOPIC_BASED = "topic_based"
    PROJECT_BASED = "project_based"
    HIERARCHICAL = "hierarchical"
    MIXED_FEATURES = "mixed_features"
    SEMANTIC_EMBEDDING = "semantic_embedding"


class RelationshipType(Enum):
    """Types of relationships between documents."""
    HIERARCHICAL = "hierarchical"          # Parent-child relationships
    CROSS_REFERENCE = "cross_reference"    # Explicit links between documents
    SEMANTIC_SIMILARITY = "semantic_similarity"  # Content similarity
    COMPLEMENTARY = "complementary"        # Documents that complement each other
    CONFLICTING = "conflicting"            # Documents with contradictory information
    SEQUENTIAL = "sequential"              # Documents in sequence (next/previous)
    TOPICAL_GROUPING = "topical_grouping"  # Documents on same topic
    PROJECT_GROUPING = "project_grouping"  # Documents in same project


@dataclass
class DocumentSimilarity:
    """Represents similarity between two documents."""
    doc1_id: str
    doc2_id: str
    similarity_score: float  # 0.0 - 1.0
    metric_scores: Dict[SimilarityMetric, float] = field(default_factory=dict)
    shared_entities: List[str] = field(default_factory=list)
    shared_topics: List[str] = field(default_factory=list)
    relationship_type: RelationshipType = RelationshipType.SEMANTIC_SIMILARITY
    explanation: str = ""
    
    def get_display_explanation(self) -> str:
        """Get human-readable explanation of similarity."""
        if self.explanation:
            return self.explanation
            
        explanations = []
        if self.shared_entities:
            explanations.append(f"Shared entities: {', '.join(self.shared_entities[:3])}")
        if self.shared_topics:
            explanations.append(f"Shared topics: {', '.join(self.shared_topics[:3])}")
        if self.metric_scores:
            top_metric = max(self.metric_scores.items(), key=lambda x: x[1])
            explanations.append(f"High {top_metric[0].value}: {top_metric[1]:.2f}")
            
        return "; ".join(explanations) if explanations else "Semantic similarity"


@dataclass
class DocumentCluster:
    """Represents a cluster of related documents."""
    cluster_id: str
    name: str
    documents: List[str] = field(default_factory=list)  # Document IDs
    shared_entities: List[str] = field(default_factory=list)
    shared_topics: List[str] = field(default_factory=list)
    cluster_strategy: ClusteringStrategy = ClusteringStrategy.MIXED_FEATURES
    coherence_score: float = 0.0  # 0.0 - 1.0
    representative_doc_id: str = ""
    cluster_description: str = ""
    
    def get_cluster_summary(self) -> Dict[str, Any]:
        """Get summary information about the cluster."""
        return {
            "cluster_id": self.cluster_id,
            "name": self.name,
            "document_count": len(self.documents),
            "coherence_score": self.coherence_score,
            "primary_entities": self.shared_entities[:5],
            "primary_topics": self.shared_topics[:5],
            "strategy": self.cluster_strategy.value,
            "description": self.cluster_description
        }


@dataclass
class CitationNetwork:
    """Represents a citation/reference network between documents."""
    nodes: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # doc_id -> metadata
    edges: List[Tuple[str, str, Dict[str, Any]]] = field(default_factory=list)  # (from, to, metadata)
    graph: Optional[nx.DiGraph] = None
    authority_scores: Dict[str, float] = field(default_factory=dict)
    hub_scores: Dict[str, float] = field(default_factory=dict)
    pagerank_scores: Dict[str, float] = field(default_factory=dict)
    
    def build_graph(self) -> nx.DiGraph:
        """Build NetworkX graph from nodes and edges."""
        if self.graph is None:
            self.graph = nx.DiGraph()
            
            # Add nodes
            for doc_id, metadata in self.nodes.items():
                self.graph.add_node(doc_id, **metadata)
                
            # Add edges
            for from_doc, to_doc, edge_metadata in self.edges:
                self.graph.add_edge(from_doc, to_doc, **edge_metadata)
                
        return self.graph
    
    def calculate_centrality_scores(self):
        """Calculate various centrality scores for the citation network."""
        if self.graph is None:
            self.build_graph()
            
        try:
            # Calculate HITS algorithm scores
            hits_scores = nx.hits(self.graph, max_iter=100, normalized=True)
            self.hub_scores = hits_scores[0]
            self.authority_scores = hits_scores[1]
            
            # Calculate PageRank scores
            self.pagerank_scores = nx.pagerank(self.graph, max_iter=100)
            
        except Exception as e:
            logger.warning(f"Failed to calculate centrality scores: {e}")
            # Fallback to simple degree centrality
            if self.graph.nodes():
                degree_centrality = nx.degree_centrality(self.graph)
                self.authority_scores = degree_centrality
                self.hub_scores = degree_centrality
                self.pagerank_scores = degree_centrality


@dataclass
class ComplementaryContent:
    """Represents complementary content recommendations."""
    target_doc_id: str
    recommendations: List[Tuple[str, float, str]] = field(default_factory=list)  # (doc_id, score, reason)
    recommendation_strategy: str = "mixed"
    generated_at: datetime = field(default_factory=datetime.now)
    
    def get_top_recommendations(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top N recommendations with detailed information."""
        top_recs = sorted(self.recommendations, key=lambda x: x[1], reverse=True)[:limit]
        return [
            {
                "document_id": doc_id,
                "relevance_score": score,
                "recommendation_reason": reason,
                "strategy": self.recommendation_strategy
            }
            for doc_id, score, reason in top_recs
        ]


@dataclass
class ConflictAnalysis:
    """Represents analysis of conflicting information between documents."""
    conflicting_pairs: List[Tuple[str, str, Dict[str, Any]]] = field(default_factory=list)  # (doc1, doc2, conflict_info)
    conflict_categories: Dict[str, List[Tuple[str, str]]] = field(default_factory=dict)
    resolution_suggestions: Dict[str, str] = field(default_factory=dict)
    
    def get_conflict_summary(self) -> Dict[str, Any]:
        """Get summary of detected conflicts."""
        return {
            "total_conflicts": len(self.conflicting_pairs),
            "conflict_categories": {cat: len(pairs) for cat, pairs in self.conflict_categories.items()},
            "most_common_conflicts": self._get_most_common_conflicts(),
            "resolution_suggestions": list(self.resolution_suggestions.values())[:3]
        }
    
    def _get_most_common_conflicts(self) -> List[str]:
        """Get the most common types of conflicts."""
        return sorted(self.conflict_categories.keys(), 
                     key=lambda x: len(self.conflict_categories[x]), 
                     reverse=True)[:3]


class DocumentSimilarityCalculator:
    """Calculates similarity between documents using multiple metrics."""
    
    def __init__(self, spacy_analyzer: SpaCyQueryAnalyzer):
        """Initialize the similarity calculator."""
        self.spacy_analyzer = spacy_analyzer
        self.logger = LoggingConfig.get_logger(__name__)
        
    def calculate_similarity(self, doc1: SearchResult, doc2: SearchResult, 
                           metrics: List[SimilarityMetric] = None) -> DocumentSimilarity:
        """Calculate comprehensive similarity between two documents."""
        if metrics is None:
            metrics = [SimilarityMetric.ENTITY_OVERLAP, SimilarityMetric.TOPIC_OVERLAP, 
                      SimilarityMetric.METADATA_SIMILARITY, SimilarityMetric.CONTENT_FEATURES]
        
        start_time = time.time()
        metric_scores = {}
        
        # Calculate individual metric scores
        for metric in metrics:
            if metric == SimilarityMetric.ENTITY_OVERLAP:
                metric_scores[metric] = self._calculate_entity_overlap(doc1, doc2)
            elif metric == SimilarityMetric.TOPIC_OVERLAP:
                metric_scores[metric] = self._calculate_topic_overlap(doc1, doc2)
            elif metric == SimilarityMetric.METADATA_SIMILARITY:
                metric_scores[metric] = self._calculate_metadata_similarity(doc1, doc2)
            elif metric == SimilarityMetric.CONTENT_FEATURES:
                metric_scores[metric] = self._calculate_content_features_similarity(doc1, doc2)
            elif metric == SimilarityMetric.HIERARCHICAL_DISTANCE:
                metric_scores[metric] = self._calculate_hierarchical_similarity(doc1, doc2)
            elif metric == SimilarityMetric.SEMANTIC_SIMILARITY:
                metric_scores[metric] = self._calculate_semantic_similarity(doc1, doc2)
        
        # Calculate combined similarity score
        combined_score = self._combine_metric_scores(metric_scores)
        
        # Extract shared entities and topics
        shared_entities = self._get_shared_entities(doc1, doc2)
        shared_topics = self._get_shared_topics(doc1, doc2)
        
        # Determine relationship type
        relationship_type = self._determine_relationship_type(doc1, doc2, metric_scores)
        
        processing_time = (time.time() - start_time) * 1000
        self.logger.debug(f"Calculated similarity between documents in {processing_time:.2f}ms")
        
        return DocumentSimilarity(
            doc1_id=f"{doc1.source_type}:{doc1.source_title}",
            doc2_id=f"{doc2.source_type}:{doc2.source_title}",
            similarity_score=combined_score,
            metric_scores=metric_scores,
            shared_entities=shared_entities,
            shared_topics=shared_topics,
            relationship_type=relationship_type
        )
    
    def _calculate_entity_overlap(self, doc1: SearchResult, doc2: SearchResult) -> float:
        """Calculate entity overlap between documents."""
        entities1 = self._extract_entity_texts(doc1.entities)
        entities2 = self._extract_entity_texts(doc2.entities)
        
        if not entities1 and not entities2:
            return 0.0
        if not entities1 or not entities2:
            return 0.0
            
        # Jaccard similarity
        intersection = len(set(entities1) & set(entities2))
        union = len(set(entities1) | set(entities2))
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_topic_overlap(self, doc1: SearchResult, doc2: SearchResult) -> float:
        """Calculate topic overlap between documents."""
        topics1 = self._extract_topic_texts(doc1.topics)
        topics2 = self._extract_topic_texts(doc2.topics)
        
        if not topics1 and not topics2:
            return 0.0
        if not topics1 or not topics2:
            return 0.0
            
        # Jaccard similarity with topic weighting
        intersection = len(set(topics1) & set(topics2))
        union = len(set(topics1) | set(topics2))
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_metadata_similarity(self, doc1: SearchResult, doc2: SearchResult) -> float:
        """Calculate metadata similarity between documents."""
        similarity_factors = []
        
        # Project similarity
        if doc1.project_id and doc2.project_id:
            if doc1.project_id == doc2.project_id:
                similarity_factors.append(1.0)
            else:
                similarity_factors.append(0.0)
        
        # Source type similarity
        if doc1.source_type == doc2.source_type:
            similarity_factors.append(0.5)
        else:
            similarity_factors.append(0.0)
        
        # Content features similarity
        features1 = [doc1.has_code_blocks, doc1.has_tables, doc1.has_images, doc1.has_links]
        features2 = [doc2.has_code_blocks, doc2.has_tables, doc2.has_images, doc2.has_links]
        feature_similarity = sum(f1 == f2 for f1, f2 in zip(features1, features2)) / len(features1)
        similarity_factors.append(feature_similarity)
        
        # Word count similarity (normalized)
        if doc1.word_count and doc2.word_count:
            min_words = min(doc1.word_count, doc2.word_count)
            max_words = max(doc1.word_count, doc2.word_count)
            word_similarity = min_words / max_words if max_words > 0 else 0.0
            similarity_factors.append(word_similarity)
        
        return sum(similarity_factors) / len(similarity_factors) if similarity_factors else 0.0
    
    def _calculate_content_features_similarity(self, doc1: SearchResult, doc2: SearchResult) -> float:
        """Calculate content features similarity."""
        # Compare read time ranges
        read_time_similarity = 0.0
        if doc1.estimated_read_time and doc2.estimated_read_time:
            min_time = min(doc1.estimated_read_time, doc2.estimated_read_time)
            max_time = max(doc1.estimated_read_time, doc2.estimated_read_time)
            read_time_similarity = min_time / max_time if max_time > 0 else 0.0
        
        # Compare section depth (hierarchical level)
        depth_similarity = 0.0
        if doc1.depth is not None and doc2.depth is not None:
            depth_diff = abs(doc1.depth - doc2.depth)
            depth_similarity = max(0.0, 1.0 - depth_diff / 5.0)  # Normalize to 5 levels
        
        # Compare content type features
        feature_factors = [read_time_similarity, depth_similarity]
        return sum(feature_factors) / len(feature_factors) if feature_factors else 0.0
    
    def _calculate_hierarchical_similarity(self, doc1: SearchResult, doc2: SearchResult) -> float:
        """Calculate hierarchical relationship similarity."""
        # Check for direct parent-child relationship
        if doc1.parent_id and doc1.parent_id == f"{doc2.source_type}:{doc2.source_title}":
            return 1.0
        if doc2.parent_id and doc2.parent_id == f"{doc1.source_type}:{doc1.source_title}":
            return 1.0
        
        # Check for sibling relationship (same parent)
        if doc1.parent_id and doc2.parent_id and doc1.parent_id == doc2.parent_id:
            return 0.8
        
        # Check for breadcrumb overlap
        if doc1.breadcrumb_text and doc2.breadcrumb_text:
            breadcrumb1 = set(doc1.breadcrumb_text.split(" > "))
            breadcrumb2 = set(doc2.breadcrumb_text.split(" > "))
            
            if breadcrumb1 and breadcrumb2:
                intersection = len(breadcrumb1 & breadcrumb2)
                union = len(breadcrumb1 | breadcrumb2)
                return intersection / union if union > 0 else 0.0
        
        return 0.0
    
    def _calculate_semantic_similarity(self, doc1: SearchResult, doc2: SearchResult) -> float:
        """Calculate semantic similarity using spaCy."""
        try:
            # Use spaCy to analyze text similarity
            doc1_analyzed = self.spacy_analyzer.nlp(doc1.text[:500])  # First 500 chars for performance
            doc2_analyzed = self.spacy_analyzer.nlp(doc2.text[:500])
            
            return doc1_analyzed.similarity(doc2_analyzed)
        except Exception as e:
            self.logger.warning(f"Failed to calculate semantic similarity: {e}")
            return 0.0
    
    def _combine_metric_scores(self, metric_scores: Dict[SimilarityMetric, float]) -> float:
        """Combine multiple metric scores into final similarity score."""
        if not metric_scores:
            return 0.0
        
        # Weighted combination of metrics
        weights = {
            SimilarityMetric.ENTITY_OVERLAP: 0.25,
            SimilarityMetric.TOPIC_OVERLAP: 0.25,
            SimilarityMetric.METADATA_SIMILARITY: 0.20,
            SimilarityMetric.CONTENT_FEATURES: 0.15,
            SimilarityMetric.HIERARCHICAL_DISTANCE: 0.10,
            SimilarityMetric.SEMANTIC_SIMILARITY: 0.05
        }
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for metric, score in metric_scores.items():
            weight = weights.get(metric, 0.1)
            weighted_sum += score * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def _get_shared_entities(self, doc1: SearchResult, doc2: SearchResult) -> List[str]:
        """Get shared entities between documents."""
        entities1 = self._extract_entity_texts(doc1.entities)
        entities2 = self._extract_entity_texts(doc2.entities)
        return list(set(entities1) & set(entities2))
    
    def _get_shared_topics(self, doc1: SearchResult, doc2: SearchResult) -> List[str]:
        """Get shared topics between documents."""
        topics1 = self._extract_topic_texts(doc1.topics)
        topics2 = self._extract_topic_texts(doc2.topics)
        return list(set(topics1) & set(topics2))
    
    def _extract_entity_texts(self, entities: List[Union[dict, str]]) -> List[str]:
        """Extract entity text from various formats."""
        texts = []
        for entity in entities:
            if isinstance(entity, dict):
                texts.append(entity.get("text", "").lower())
            elif isinstance(entity, str):
                texts.append(entity.lower())
        return [t for t in texts if t]
    
    def _extract_topic_texts(self, topics: List[Union[dict, str]]) -> List[str]:
        """Extract topic text from various formats."""
        texts = []
        for topic in topics:
            if isinstance(topic, dict):
                texts.append(topic.get("text", "").lower())
            elif isinstance(topic, str):
                texts.append(topic.lower())
        return [t for t in texts if t]
    
    def _determine_relationship_type(self, doc1: SearchResult, doc2: SearchResult, 
                                   metric_scores: Dict[SimilarityMetric, float]) -> RelationshipType:
        """Determine the type of relationship between documents."""
        # Check for hierarchical relationship
        if (SimilarityMetric.HIERARCHICAL_DISTANCE in metric_scores and 
            metric_scores[SimilarityMetric.HIERARCHICAL_DISTANCE] > 0.7):
            return RelationshipType.HIERARCHICAL
        
        # Check for cross-references
        if doc1.cross_references or doc2.cross_references:
            return RelationshipType.CROSS_REFERENCE
        
        # Check for project grouping
        if doc1.project_id and doc2.project_id and doc1.project_id == doc2.project_id:
            return RelationshipType.PROJECT_GROUPING
        
        # Default to semantic similarity
        return RelationshipType.SEMANTIC_SIMILARITY


class DocumentClusterAnalyzer:
    """Analyzes and creates clusters of related documents."""
    
    def __init__(self, similarity_calculator: DocumentSimilarityCalculator):
        """Initialize the cluster analyzer."""
        self.similarity_calculator = similarity_calculator
        self.logger = LoggingConfig.get_logger(__name__)
        
    def create_clusters(self, documents: List[SearchResult], 
                       strategy: ClusteringStrategy = ClusteringStrategy.MIXED_FEATURES,
                       max_clusters: int = 10,
                       min_cluster_size: int = 2) -> List[DocumentCluster]:
        """Create document clusters using specified strategy."""
        start_time = time.time()
        
        if strategy == ClusteringStrategy.ENTITY_BASED:
            clusters = self._cluster_by_entities(documents, max_clusters, min_cluster_size)
        elif strategy == ClusteringStrategy.TOPIC_BASED:
            clusters = self._cluster_by_topics(documents, max_clusters, min_cluster_size)
        elif strategy == ClusteringStrategy.PROJECT_BASED:
            clusters = self._cluster_by_projects(documents, max_clusters, min_cluster_size)
        elif strategy == ClusteringStrategy.HIERARCHICAL:
            clusters = self._cluster_by_hierarchy(documents, max_clusters, min_cluster_size)
        elif strategy == ClusteringStrategy.MIXED_FEATURES:
            clusters = self._cluster_by_mixed_features(documents, max_clusters, min_cluster_size)
        else:
            clusters = self._cluster_by_mixed_features(documents, max_clusters, min_cluster_size)
        
        # Calculate coherence scores for clusters
        for cluster in clusters:
            cluster.coherence_score = self._calculate_cluster_coherence(cluster, documents)
            cluster.representative_doc_id = self._find_representative_document(cluster, documents)
            cluster.cluster_description = self._generate_cluster_description(cluster, documents)
        
        processing_time = (time.time() - start_time) * 1000
        self.logger.info(f"Created {len(clusters)} clusters using {strategy.value} in {processing_time:.2f}ms")
        
        return clusters
    
    def _cluster_by_entities(self, documents: List[SearchResult], 
                           max_clusters: int, min_cluster_size: int) -> List[DocumentCluster]:
        """Cluster documents based on shared entities."""
        entity_groups = defaultdict(list)
        
        # Group documents by their most common entities
        for doc in documents:
            doc_id = f"{doc.source_type}:{doc.source_title}"
            entities = self.similarity_calculator._extract_entity_texts(doc.entities)
            
            # Use most frequent entities as clustering key
            entity_counter = Counter(entities)
            top_entities = [entity for entity, _ in entity_counter.most_common(3)]
            
            if top_entities:
                cluster_key = "|".join(sorted(top_entities))
                entity_groups[cluster_key].append(doc_id)
        
        # Convert to DocumentCluster objects
        clusters = []
        for i, (entity_key, doc_ids) in enumerate(entity_groups.items()):
            if len(doc_ids) >= min_cluster_size and len(clusters) < max_clusters:
                shared_entities = entity_key.split("|")
                cluster = DocumentCluster(
                    cluster_id=f"entity_cluster_{i}",
                    name=f"Entity Cluster: {', '.join(shared_entities[:2])}",
                    documents=doc_ids,
                    shared_entities=shared_entities,
                    cluster_strategy=ClusteringStrategy.ENTITY_BASED
                )
                clusters.append(cluster)
        
        return clusters
    
    def _cluster_by_topics(self, documents: List[SearchResult], 
                          max_clusters: int, min_cluster_size: int) -> List[DocumentCluster]:
        """Cluster documents based on shared topics."""
        topic_groups = defaultdict(list)
        
        # Group documents by their most common topics
        for doc in documents:
            doc_id = f"{doc.source_type}:{doc.source_title}"
            topics = self.similarity_calculator._extract_topic_texts(doc.topics)
            
            # Use most frequent topics as clustering key
            topic_counter = Counter(topics)
            top_topics = [topic for topic, _ in topic_counter.most_common(3)]
            
            if top_topics:
                cluster_key = "|".join(sorted(top_topics))
                topic_groups[cluster_key].append(doc_id)
        
        # Convert to DocumentCluster objects
        clusters = []
        for i, (topic_key, doc_ids) in enumerate(topic_groups.items()):
            if len(doc_ids) >= min_cluster_size and len(clusters) < max_clusters:
                shared_topics = topic_key.split("|")
                cluster = DocumentCluster(
                    cluster_id=f"topic_cluster_{i}",
                    name=f"Topic Cluster: {', '.join(shared_topics[:2])}",
                    documents=doc_ids,
                    shared_topics=shared_topics,
                    cluster_strategy=ClusteringStrategy.TOPIC_BASED
                )
                clusters.append(cluster)
        
        return clusters
    
    def _cluster_by_projects(self, documents: List[SearchResult], 
                           max_clusters: int, min_cluster_size: int) -> List[DocumentCluster]:
        """Cluster documents based on project groupings."""
        project_groups = defaultdict(list)
        
        # Group documents by project
        for doc in documents:
            doc_id = f"{doc.source_type}:{doc.source_title}"
            project_key = doc.project_id or "no_project"
            project_groups[project_key].append(doc_id)
        
        # Convert to DocumentCluster objects
        clusters = []
        for i, (project_key, doc_ids) in enumerate(project_groups.items()):
            if len(doc_ids) >= min_cluster_size and len(clusters) < max_clusters:
                cluster = DocumentCluster(
                    cluster_id=f"project_cluster_{i}",
                    name=f"Project: {project_key}",
                    documents=doc_ids,
                    cluster_strategy=ClusteringStrategy.PROJECT_BASED
                )
                clusters.append(cluster)
        
        return clusters
    
    def _cluster_by_hierarchy(self, documents: List[SearchResult], 
                             max_clusters: int, min_cluster_size: int) -> List[DocumentCluster]:
        """Cluster documents based on hierarchical relationships."""
        hierarchy_groups = defaultdict(list)
        
        # Group documents by hierarchical context
        for doc in documents:
            doc_id = f"{doc.source_type}:{doc.source_title}"
            
            # Use breadcrumb as clustering key
            if doc.breadcrumb_text:
                # Use first few levels of breadcrumb
                breadcrumb_parts = doc.breadcrumb_text.split(" > ")
                cluster_key = " > ".join(breadcrumb_parts[:2])  # First 2 levels
                hierarchy_groups[cluster_key].append(doc_id)
            else:
                hierarchy_groups["root"].append(doc_id)
        
        # Convert to DocumentCluster objects
        clusters = []
        for i, (hierarchy_key, doc_ids) in enumerate(hierarchy_groups.items()):
            if len(doc_ids) >= min_cluster_size and len(clusters) < max_clusters:
                cluster = DocumentCluster(
                    cluster_id=f"hierarchy_cluster_{i}",
                    name=f"Hierarchy: {hierarchy_key}",
                    documents=doc_ids,
                    cluster_strategy=ClusteringStrategy.HIERARCHICAL
                )
                clusters.append(cluster)
        
        return clusters
    
    def _cluster_by_mixed_features(self, documents: List[SearchResult], 
                                  max_clusters: int, min_cluster_size: int) -> List[DocumentCluster]:
        """Cluster documents using mixed features (entities + topics + project)."""
        feature_groups = defaultdict(list)
        
        # Group documents by combined features
        for doc in documents:
            doc_id = f"{doc.source_type}:{doc.source_title}"
            
            # Combine key features
            entities = self.similarity_calculator._extract_entity_texts(doc.entities)[:2]
            topics = self.similarity_calculator._extract_topic_texts(doc.topics)[:2]
            project = doc.project_id or "no_project"
            
            # Create composite clustering key
            feature_parts = []
            if entities:
                feature_parts.append(f"entities:{','.join(entities)}")
            if topics:
                feature_parts.append(f"topics:{','.join(topics)}")
            feature_parts.append(f"project:{project}")
            
            cluster_key = "|".join(feature_parts)
            feature_groups[cluster_key].append(doc_id)
        
        # Convert to DocumentCluster objects
        clusters = []
        for i, (feature_key, doc_ids) in enumerate(feature_groups.items()):
            if len(doc_ids) >= min_cluster_size and len(clusters) < max_clusters:
                # Parse shared features
                shared_entities = []
                shared_topics = []
                
                for part in feature_key.split("|"):
                    if part.startswith("entities:"):
                        shared_entities = part.replace("entities:", "").split(",")
                    elif part.startswith("topics:"):
                        shared_topics = part.replace("topics:", "").split(",")
                
                cluster = DocumentCluster(
                    cluster_id=f"mixed_cluster_{i}",
                    name=f"Mixed Cluster {i+1}",
                    documents=doc_ids,
                    shared_entities=[e for e in shared_entities if e],
                    shared_topics=[t for t in shared_topics if t],
                    cluster_strategy=ClusteringStrategy.MIXED_FEATURES
                )
                clusters.append(cluster)
        
        return clusters
    
    def _calculate_cluster_coherence(self, cluster: DocumentCluster, 
                                   all_documents: List[SearchResult]) -> float:
        """Calculate coherence score for a cluster."""
        if len(cluster.documents) < 2:
            return 1.0
        
        # Find documents in this cluster
        cluster_docs = []
        doc_lookup = {f"{doc.source_type}:{doc.source_title}": doc for doc in all_documents}
        
        for doc_id in cluster.documents:
            if doc_id in doc_lookup:
                cluster_docs.append(doc_lookup[doc_id])
        
        if len(cluster_docs) < 2:
            return 0.0
        
        # Calculate pairwise similarities within cluster
        similarities = []
        for i in range(len(cluster_docs)):
            for j in range(i + 1, len(cluster_docs)):
                similarity = self.similarity_calculator.calculate_similarity(
                    cluster_docs[i], cluster_docs[j]
                )
                similarities.append(similarity.similarity_score)
        
        # Return average similarity as coherence score
        return sum(similarities) / len(similarities) if similarities else 0.0
    
    def _find_representative_document(self, cluster: DocumentCluster, 
                                    all_documents: List[SearchResult]) -> str:
        """Find the most representative document in a cluster."""
        if not cluster.documents:
            return ""
        
        # For now, return the first document
        # Could be enhanced to find document with highest centrality
        return cluster.documents[0]
    
    def _generate_cluster_description(self, cluster: DocumentCluster, 
                                    all_documents: List[SearchResult]) -> str:
        """Generate a description for the cluster."""
        descriptions = []
        
        if cluster.shared_entities:
            descriptions.append(f"Documents related to {', '.join(cluster.shared_entities[:2])}")
        
        if cluster.shared_topics:
            descriptions.append(f"Topics: {', '.join(cluster.shared_topics[:2])}")
        
        descriptions.append(f"Strategy: {cluster.cluster_strategy.value}")
        descriptions.append(f"{len(cluster.documents)} documents")
        
        return "; ".join(descriptions)


class CitationNetworkAnalyzer:
    """Analyzes citation and reference networks between documents."""
    
    def __init__(self):
        """Initialize the citation network analyzer."""
        self.logger = LoggingConfig.get_logger(__name__)
        
    def build_citation_network(self, documents: List[SearchResult]) -> CitationNetwork:
        """Build citation network from document cross-references and hierarchical relationships."""
        start_time = time.time()
        
        network = CitationNetwork()
        doc_lookup = {f"{doc.source_type}:{doc.source_title}": doc for doc in documents}
        
        # Add nodes to the network
        for doc in documents:
            doc_id = f"{doc.source_type}:{doc.source_title}"
            network.nodes[doc_id] = {
                "title": doc.source_title,
                "source_type": doc.source_type,
                "project_id": doc.project_id,
                "word_count": doc.word_count or 0,
                "has_code": doc.has_code_blocks,
                "has_tables": doc.has_tables,
                "depth": doc.depth or 0,
                "creation_date": getattr(doc, 'created_at', None),
            }
        
        # Add edges based on cross-references
        for doc in documents:
            doc_id = f"{doc.source_type}:{doc.source_title}"
            
            # Process cross-references
            if doc.cross_references:
                for ref in doc.cross_references:
                    target_url = ref.get("url", "") if isinstance(ref, dict) else ""
                    ref_text = ref.get("text", "") if isinstance(ref, dict) else str(ref)
                    
                    # Try to find referenced document
                    target_doc_id = self._find_referenced_document(target_url, doc_lookup)
                    if target_doc_id and target_doc_id != doc_id:
                        network.edges.append((doc_id, target_doc_id, {
                            "relation_type": "cross_reference",
                            "reference_text": ref_text,
                            "reference_url": target_url,
                            "weight": 1.0
                        }))
            
            # Add hierarchical relationships
            if doc.parent_id and doc.parent_id in doc_lookup:
                network.edges.append((doc.parent_id, doc_id, {
                    "relation_type": "hierarchical_child",
                    "weight": 2.0  # Higher weight for hierarchical relationships
                }))
            
            # Add sibling relationships
            if doc.sibling_sections:
                for sibling in doc.sibling_sections:
                    sibling_doc_id = self._find_sibling_document(sibling, doc_lookup)
                    if sibling_doc_id and sibling_doc_id != doc_id:
                        network.edges.append((doc_id, sibling_doc_id, {
                            "relation_type": "sibling",
                            "weight": 0.5
                        }))
        
        # Build NetworkX graph and calculate centrality scores
        network.build_graph()
        network.calculate_centrality_scores()
        
        processing_time = (time.time() - start_time) * 1000
        self.logger.info(f"Built citation network with {len(network.nodes)} nodes and {len(network.edges)} edges in {processing_time:.2f}ms")
        
        return network
    
    def _find_referenced_document(self, reference_url: str, doc_lookup: Dict[str, SearchResult]) -> Optional[str]:
        """Find document that matches a reference URL."""
        if not reference_url:
            return None
            
        # Try exact URL match first
        for doc_id, doc in doc_lookup.items():
            if doc.source_url and reference_url in doc.source_url:
                return doc_id
        
        # Try title-based matching for internal references
        for doc_id, doc in doc_lookup.items():
            if reference_url.lower() in doc.source_title.lower():
                return doc_id
        
        return None
    
    def _find_sibling_document(self, sibling_reference: str, doc_lookup: Dict[str, SearchResult]) -> Optional[str]:
        """Find document that matches a sibling reference."""
        # Try title-based matching
        for doc_id, doc in doc_lookup.items():
            if sibling_reference.lower() in doc.source_title.lower():
                return doc_id
        
        return None
    
    def get_most_authoritative_documents(self, network: CitationNetwork, limit: int = 10) -> List[Tuple[str, float]]:
        """Get the most authoritative documents based on citation analysis."""
        if not network.authority_scores:
            return []
        
        # Sort by authority score
        sorted_docs = sorted(network.authority_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_docs[:limit]
    
    def get_most_connected_documents(self, network: CitationNetwork, limit: int = 10) -> List[Tuple[str, int]]:
        """Get the most connected documents based on degree centrality."""
        if not network.graph:
            return []
        
        # Calculate degree centrality
        degree_centrality = dict(network.graph.degree())
        sorted_docs = sorted(degree_centrality.items(), key=lambda x: x[1], reverse=True)
        return sorted_docs[:limit]


class ComplementaryContentFinder:
    """Finds complementary content that would enhance understanding of a target document."""
    
    def __init__(self, similarity_calculator: DocumentSimilarityCalculator,
                 knowledge_graph: Optional[DocumentKnowledgeGraph] = None):
        """Initialize the complementary content finder."""
        self.similarity_calculator = similarity_calculator
        self.knowledge_graph = knowledge_graph
        self.logger = LoggingConfig.get_logger(__name__)
        
    def find_complementary_content(self, target_doc: SearchResult, 
                                 candidate_docs: List[SearchResult],
                                 max_recommendations: int = 5) -> ComplementaryContent:
        """Find complementary content for a target document."""
        start_time = time.time()
        
        recommendations = []
        target_doc_id = f"{target_doc.source_type}:{target_doc.source_title}"
        
        self.logger.info(f"Finding complementary content for target: {target_doc_id}")
        self.logger.info(f"Target doc topics: {target_doc.topics}")
        self.logger.info(f"Target doc entities: {target_doc.entities}")
        self.logger.info(f"Analyzing {len(candidate_docs)} candidate documents")
        
        for candidate in candidate_docs:
            candidate_id = f"{candidate.source_type}:{candidate.source_title}"
            
            if candidate_id == target_doc_id:
                continue
            
            self.logger.debug(f"Analyzing candidate: {candidate_id}")
            self.logger.debug(f"Candidate topics: {candidate.topics}")
            self.logger.debug(f"Candidate entities: {candidate.entities}")
            
            # Calculate complementary score
            complementary_score, reason = self._calculate_complementary_score(target_doc, candidate)
            
            self.logger.info(f"Complementary score for {candidate_id}: {complementary_score:.3f} - {reason}")
            
            if complementary_score > 0.15:  # Lowered threshold for complementary content
                recommendations.append((candidate_id, complementary_score, reason))
            else:
                # Log why it didn't make the cut
                self.logger.debug(f"Rejected {candidate_id}: score {complementary_score:.3f} below threshold 0.15")
        
        # Sort by complementary score
        recommendations.sort(key=lambda x: x[1], reverse=True)
        
        processing_time = (time.time() - start_time) * 1000
        self.logger.info(f"Found {len(recommendations)} complementary recommendations in {processing_time:.2f}ms")
        
        return ComplementaryContent(
            target_doc_id=target_doc_id,
            recommendations=recommendations[:max_recommendations],
            recommendation_strategy="mixed"
        )
    
    def _calculate_complementary_score(self, target_doc: SearchResult, 
                                     candidate_doc: SearchResult) -> Tuple[float, str]:
        """Calculate how complementary a candidate document is to the target.
        
        Redesigned algorithm that prioritizes intra-project relationships while
        maintaining intelligent inter-project discovery capabilities.
        """
        self.logger.info(f"=== Scoring {candidate_doc.source_title} against {target_doc.source_title} ===")
        
        same_project = (target_doc.project_id == candidate_doc.project_id)
        self.logger.info(f"Project context: target={target_doc.project_id}, candidate={candidate_doc.project_id}, same_project={same_project}")
        
        if same_project:
            # Prioritize intra-project relationships
            score, reason = self._score_intra_project_complementary(target_doc, candidate_doc)
            
            # Boost for high topic relevance within project
            if score > 0 and self._has_high_topic_overlap(target_doc, candidate_doc):
                boosted_score = min(0.95, score * 1.2)
                self.logger.info(f"✓ Intra-project topic boost: {score:.3f} → {boosted_score:.3f}")
                score = boosted_score
                reason = f"{reason} (high topic relevance)"
                
        else:
            # Evaluate inter-project relationships
            score, reason = self._score_inter_project_complementary(target_doc, candidate_doc)
            
            # Apply cross-project penalty (inter-project content is less immediately useful)
            if score > 0:
                adjusted_score = score * 0.8
                self.logger.info(f"✓ Inter-project penalty applied: {score:.3f} → {adjusted_score:.3f}")
                score = adjusted_score
                reason = f"Inter-project: {reason}"
        
        self.logger.info(f"Final complementary score: {score:.3f} for {candidate_doc.source_title} - {reason}")
        return score, reason
    
    def _score_intra_project_complementary(self, target_doc: SearchResult, candidate_doc: SearchResult) -> Tuple[float, str]:
        """Score complementary relationships within the same project."""
        factors = []
        
        # A. Requirements ↔ Implementation Chain
        if self._is_requirements_implementation_pair(target_doc, candidate_doc):
            factors.append((0.85, "Requirements-implementation chain"))
            self.logger.info("✓ Found requirements-implementation pair")
            
        # B. Abstraction Level Differences  
        abstraction_gap = self._calculate_abstraction_gap(target_doc, candidate_doc)
        if abstraction_gap > 0:
            score = 0.7 + (abstraction_gap * 0.1)
            factors.append((score, f"Different abstraction levels (gap: {abstraction_gap})"))
            self.logger.info(f"✓ Abstraction gap: {abstraction_gap} → score: {score:.3f}")
            
        # C. Cross-Functional Perspectives
        if self._has_cross_functional_relationship(target_doc, candidate_doc):
            factors.append((0.75, "Cross-functional perspectives"))
            self.logger.info("✓ Cross-functional relationship detected")
            
        # D. Topic Overlap with Different Document Types
        if (self._has_shared_topics(target_doc, candidate_doc) and 
            self._has_different_document_types(target_doc, candidate_doc)):
            shared_topics = self._get_shared_topics_count(target_doc, candidate_doc)
            score = min(0.65, 0.35 + (shared_topics * 0.1))
            factors.append((score, f"Same topics, different document types ({shared_topics} topics)"))
            self.logger.info(f"✓ Topic overlap with different doc types: {score:.3f}")
        
        return self._calculate_weighted_score(factors, target_doc, candidate_doc)
    
    def _score_inter_project_complementary(self, target_doc: SearchResult, candidate_doc: SearchResult) -> Tuple[float, str]:
        """Score complementary relationships between different projects."""
        factors = []
        
        # A. Similar Challenges/Solutions
        if self._has_similar_challenges(target_doc, candidate_doc):
            factors.append((0.8, "Similar challenges/solutions"))
            self.logger.info("✓ Similar challenges detected")
            
        # B. Domain Expertise Transfer
        if self._has_transferable_domain_knowledge(target_doc, candidate_doc):
            factors.append((0.75, "Transferable domain knowledge"))
            self.logger.info("✓ Transferable domain knowledge")
            
        # C. Architectural Patterns
        if self._has_reusable_architecture_patterns(target_doc, candidate_doc):
            factors.append((0.7, "Reusable architecture patterns"))
            self.logger.info("✓ Architecture patterns detected")
            
        # D. Shared Technologies/Standards
        if self._has_shared_technologies(target_doc, candidate_doc):
            shared_count = self._get_shared_technologies_count(target_doc, candidate_doc)
            score = min(0.6, 0.3 + (shared_count * 0.1))
            factors.append((score, f"Shared technologies ({shared_count} common)"))
            self.logger.info(f"✓ Shared technologies: {score:.3f}")
        
        return self._calculate_weighted_score(factors, target_doc, candidate_doc)
    
    def _calculate_weighted_score(self, factors: List[Tuple[float, str]], target_doc: SearchResult = None, candidate_doc: SearchResult = None) -> Tuple[float, str]:
        """Calculate weighted score from multiple factors."""
        if not factors:
            if target_doc and candidate_doc:
                return self._enhanced_fallback_scoring(target_doc, candidate_doc)
            else:
                return 0.0, "No complementary relationship found"
        
        # Use the highest scoring factor as primary, but consider multiple factors
        factors.sort(key=lambda x: x[0], reverse=True)
        primary_score, primary_reason = factors[0]
        
        # Boost if multiple factors contribute
        if len(factors) > 1:
            secondary_boost = sum(score for score, _ in factors[1:]) * 0.1
            final_score = min(0.95, primary_score + secondary_boost)
            primary_reason = f"{primary_reason} (+{len(factors)-1} other factors)"
        else:
            final_score = primary_score
            
        return final_score, primary_reason
    
    def _is_requirements_implementation_pair(self, doc1: SearchResult, doc2: SearchResult) -> bool:
        """Detect if documents form a requirements -> implementation chain."""
        req_keywords = ["requirements", "specification", "user story", "feature", "functional"]
        impl_keywords = ["implementation", "technical", "architecture", "api", "code", "development"]
        
        title1 = doc1.source_title.lower()
        title2 = doc2.source_title.lower()
        
        doc1_is_req = any(keyword in title1 for keyword in req_keywords)
        doc1_is_impl = any(keyword in title1 for keyword in impl_keywords)
        doc2_is_req = any(keyword in title2 for keyword in req_keywords)
        doc2_is_impl = any(keyword in title2 for keyword in impl_keywords)
        
        # One is requirements, other is implementation
        return ((doc1_is_req and doc2_is_impl) or (doc1_is_impl and doc2_is_req)) and \
               (self._has_shared_topics(doc1, doc2) or self._has_shared_entities(doc1, doc2))
    
    def _calculate_abstraction_gap(self, doc1: SearchResult, doc2: SearchResult) -> int:
        """Calculate difference in abstraction levels (0-3).
        0: Same level, 3: Maximum gap (e.g., epic vs implementation detail)
        """
        level1 = self._get_abstraction_level(doc1)
        level2 = self._get_abstraction_level(doc2)
        return abs(level1 - level2)
    
    def _get_abstraction_level(self, doc: SearchResult) -> int:
        """Determine abstraction level of document (0=highest, 3=lowest)."""
        title = doc.source_title.lower()
        
        # Level 0: High-level business/strategy
        if any(keyword in title for keyword in ["strategy", "vision", "overview", "executive", "business case"]):
            return 0
            
        # Level 1: Requirements/features  
        if any(keyword in title for keyword in ["requirements", "features", "user story", "epic", "specification"]):
            return 1
            
        # Level 2: Design/architecture
        if any(keyword in title for keyword in ["design", "architecture", "workflow", "process", "wireframe"]):
            return 2
            
        # Level 3: Implementation details
        if any(keyword in title for keyword in ["implementation", "code", "api", "technical", "development", "configuration"]):
            return 3
            
        # Default to middle level
        return 2
    
    def _has_cross_functional_relationship(self, doc1: SearchResult, doc2: SearchResult) -> bool:
        """Detect business + technical, feature + security, etc."""
        business_keywords = ["business", "user", "requirements", "workflow", "process", "feature"]
        technical_keywords = ["technical", "architecture", "api", "implementation", "code", "development"]
        security_keywords = ["security", "authentication", "authorization", "compliance", "audit"]
        
        title1 = doc1.source_title.lower()
        title2 = doc2.source_title.lower()
        
        # Business + Technical
        if (any(k in title1 for k in business_keywords) and any(k in title2 for k in technical_keywords)) or \
           (any(k in title2 for k in business_keywords) and any(k in title1 for k in technical_keywords)):
            return True
        
        # Feature + Security
        if (any(k in title1 for k in ["feature", "functionality"]) and any(k in title2 for k in security_keywords)) or \
           (any(k in title2 for k in ["feature", "functionality"]) and any(k in title1 for k in security_keywords)):
            return True
        
        return False
    
    def _has_different_document_types(self, doc1: SearchResult, doc2: SearchResult) -> bool:
        """Check if documents are of different types based on content and title."""
        type1 = self._classify_document_type(doc1)
        type2 = self._classify_document_type(doc2)
        return type1 != type2
    
    def _classify_document_type(self, doc: SearchResult) -> str:
        """Classify document as: user_story, technical_spec, architecture, compliance, testing, etc."""
        title = doc.source_title.lower()
        
        # Check more specific categories first to avoid conflicts
        if any(keyword in title for keyword in ["security", "compliance", "audit", "policy"]):
            return "compliance"
        elif any(keyword in title for keyword in ["test", "testing", "qa", "quality"]):
            return "testing"
        elif any(keyword in title for keyword in ["user story", "epic", "feature"]):
            return "user_story"
        elif any(keyword in title for keyword in ["technical", "specification", "api", "implementation"]):
            return "technical_spec"
        elif any(keyword in title for keyword in ["architecture", "design", "system"]):
            return "architecture"
        elif any(keyword in title for keyword in ["workflow", "process", "procedure"]):
            return "process"
        elif any(keyword in title for keyword in ["requirement"]):  # More general, check last
            return "user_story"
        else:
            return "general"
    
    def _has_high_topic_overlap(self, doc1: SearchResult, doc2: SearchResult) -> bool:
        """Check if documents have high topic overlap (>= 3 shared topics)."""
        return self._get_shared_topics_count(doc1, doc2) >= 3
    
    def _has_similar_challenges(self, doc1: SearchResult, doc2: SearchResult) -> bool:
        """Identify common challenge patterns (auth, scalability, compliance)."""
        challenge_patterns = [
            ["authentication", "login", "auth", "signin"],
            ["scalability", "performance", "optimization", "scale"],
            ["compliance", "regulation", "audit", "governance"],
            ["integration", "api", "interface", "connection"],
            ["security", "privacy", "protection", "safety"],
            ["migration", "upgrade", "transition", "conversion"]
        ]
        
        title1 = doc1.source_title.lower()
        title2 = doc2.source_title.lower()
        
        for pattern in challenge_patterns:
            if (any(keyword in title1 for keyword in pattern) and 
                any(keyword in title2 for keyword in pattern)):
                return True
        
        return False
    
    def _has_transferable_domain_knowledge(self, doc1: SearchResult, doc2: SearchResult) -> bool:
        """Check for transferable domain expertise between projects."""
        # This is a simplified implementation - could be enhanced with NLP
        domain_keywords = [
            ["healthcare", "medical", "patient", "clinical"],
            ["finance", "payment", "banking", "financial"],
            ["ecommerce", "retail", "shopping", "commerce"],
            ["education", "learning", "student", "academic"],
            ["iot", "device", "sensor", "embedded"],
            ["mobile", "app", "ios", "android"]
        ]
        
        title1 = doc1.source_title.lower()
        title2 = doc2.source_title.lower()
        
        for domain in domain_keywords:
            if (any(keyword in title1 for keyword in domain) and 
                any(keyword in title2 for keyword in domain)):
                return True
        
        return False
    
    def _has_reusable_architecture_patterns(self, doc1: SearchResult, doc2: SearchResult) -> bool:
        """Identify architectural patterns that are reusable across projects."""
        architecture_patterns = [
            ["microservices", "service", "microservice"],
            ["api", "rest", "graphql", "endpoint"],
            ["database", "data", "storage", "persistence"],
            ["authentication", "auth", "identity", "oauth"],
            ["messaging", "queue", "event", "pub-sub"],
            ["cache", "caching", "redis", "memory"],
            ["monitoring", "logging", "observability", "metrics"]
        ]
        
        title1 = doc1.source_title.lower()
        title2 = doc2.source_title.lower()
        
        for pattern in architecture_patterns:
            if (any(keyword in title1 for keyword in pattern) and 
                any(keyword in title2 for keyword in pattern)):
                return True
        
        return False
    
    def _has_shared_technologies(self, doc1: SearchResult, doc2: SearchResult) -> bool:
        """Identify shared technologies, frameworks, standards."""
        tech_patterns = [
            ["react", "angular", "vue", "frontend"],
            ["node", "python", "java", "golang"],
            ["docker", "kubernetes", "container"],
            ["aws", "azure", "gcp", "cloud"],
            ["postgres", "mysql", "mongodb", "database"],
            ["jwt", "oauth", "saml", "authentication"],
            ["rest", "graphql", "grpc", "api"]
        ]
        
        title1 = doc1.source_title.lower()
        title2 = doc2.source_title.lower()
        
        for tech in tech_patterns:
            if (any(keyword in title1 for keyword in tech) and 
                any(keyword in title2 for keyword in tech)):
                return True
        
        return False
    
    def _get_shared_technologies_count(self, doc1: SearchResult, doc2: SearchResult) -> int:
        """Count shared technologies between documents."""
        # Simplified implementation based on title analysis
        tech_keywords = ["react", "angular", "vue", "node", "python", "java", "docker", 
                        "kubernetes", "aws", "azure", "postgres", "mysql", "jwt", "oauth"]
        
        title1_words = set(doc1.source_title.lower().split())
        title2_words = set(doc2.source_title.lower().split())
        
        shared_tech = 0
        for tech in tech_keywords:
            if tech in title1_words and tech in title2_words:
                shared_tech += 1
        
        return shared_tech
    
    def _enhanced_fallback_scoring(self, target_doc: SearchResult, candidate_doc: SearchResult) -> Tuple[float, str]:
        """Enhanced fallback when advanced algorithms don't apply."""
        fallback_score = self._calculate_fallback_score(target_doc, candidate_doc)
        if fallback_score > 0:
            return fallback_score, "Basic content similarity"
        else:
            return 0.0, "No complementary relationship found"
    
    def _calculate_fallback_score(self, target_doc: SearchResult, candidate_doc: SearchResult) -> float:
        """Fallback scoring for when advanced methods don't find relationships."""
        score = 0.0
        
        # Just having any shared topics at all
        if self._has_shared_topics(target_doc, candidate_doc):
            shared_count = self._get_shared_topics_count(target_doc, candidate_doc)
            score = max(score, 0.2 + (shared_count * 0.05))
            self.logger.debug(f"Fallback: {shared_count} shared topics → score: {score:.3f}")
        
        # Just having any shared entities at all
        if self._has_shared_entities(target_doc, candidate_doc):
            shared_count = self._get_shared_entities_count(target_doc, candidate_doc)
            score = max(score, 0.15 + (shared_count * 0.05))
            self.logger.debug(f"Fallback: {shared_count} shared entities → score: {score:.3f}")
        
        # Simple keyword overlap in titles
        target_words = set(target_doc.source_title.lower().split())
        candidate_words = set(candidate_doc.source_title.lower().split())
        common_words = target_words & candidate_words
        if len(common_words) > 1:  # More than just common words like "the", "and"
            score = max(score, 0.1 + (len(common_words) * 0.02))
            self.logger.debug(f"Fallback: {len(common_words)} common words in titles → score: {score:.3f}")
        
        return min(score, 0.5)  # Cap fallback scores
    
    def _has_shared_entities(self, doc1: SearchResult, doc2: SearchResult) -> bool:
        """Check if documents have shared entities."""
        entities1 = self.similarity_calculator._extract_entity_texts(doc1.entities)
        entities2 = self.similarity_calculator._extract_entity_texts(doc2.entities)
        return len(set(entities1) & set(entities2)) > 0
    
    def _has_shared_topics(self, doc1: SearchResult, doc2: SearchResult) -> bool:
        """Check if documents have shared topics."""
        topics1 = self.similarity_calculator._extract_topic_texts(doc1.topics)
        topics2 = self.similarity_calculator._extract_topic_texts(doc2.topics)
        return len(set(topics1) & set(topics2)) > 0
    

    
    def _get_shared_topics_count(self, doc1: SearchResult, doc2: SearchResult) -> int:
        """Get the count of shared topics between documents."""
        topics1 = self.similarity_calculator._extract_topic_texts(doc1.topics)
        topics2 = self.similarity_calculator._extract_topic_texts(doc2.topics)
        return len(set(topics1) & set(topics2))
    
    def _get_shared_entities_count(self, doc1: SearchResult, doc2: SearchResult) -> int:
        """Get the count of shared entities between documents."""
        entities1 = self.similarity_calculator._extract_entity_texts(doc1.entities)
        entities2 = self.similarity_calculator._extract_entity_texts(doc2.entities)
        return len(set(entities1) & set(entities2))
    
    def _has_different_content_complexity(self, doc1: SearchResult, doc2: SearchResult) -> bool:
        """Check if documents have different levels of content complexity."""
        # Compare word counts if available
        if doc1.word_count and doc2.word_count:
            ratio = max(doc1.word_count, doc2.word_count) / min(doc1.word_count, doc2.word_count)
            if ratio > 2.0:  # One document is significantly longer
                return True
        
        # Compare content features
        features1 = (doc1.has_code_blocks, doc1.has_tables, doc1.has_images)
        features2 = (doc2.has_code_blocks, doc2.has_tables, doc2.has_images)
        
        # Different if one has technical content and the other doesn't
        return features1 != features2
    
    def _get_complementary_content_type_score(self, target_doc: SearchResult, candidate_doc: SearchResult) -> float:
        """Calculate score based on complementary content types."""
        score = 0.0
        
        # Technical + Business complement
        technical_keywords = ["api", "code", "implementation", "technical", "development", "architecture"]
        business_keywords = ["requirements", "business", "specification", "user", "workflow", "process"]
        
        target_title = target_doc.source_title.lower()
        candidate_title = candidate_doc.source_title.lower()
        
        target_is_technical = any(keyword in target_title for keyword in technical_keywords)
        target_is_business = any(keyword in target_title for keyword in business_keywords)
        candidate_is_technical = any(keyword in candidate_title for keyword in technical_keywords)
        candidate_is_business = any(keyword in candidate_title for keyword in business_keywords)
        
        # Technical document + Business document = complementary
        if (target_is_technical and candidate_is_business) or (target_is_business and candidate_is_technical):
            score = 0.7
        
        # Documentation + Implementation complement
        if ("documentation" in target_title and "implementation" in candidate_title) or \
           ("implementation" in target_title and "documentation" in candidate_title):
            score = max(score, 0.6)
        
        # Requirements + Design complement
        if ("requirements" in target_title and ("design" in candidate_title or "architecture" in candidate_title)) or \
           (("design" in target_title or "architecture" in target_title) and "requirements" in candidate_title):
            score = max(score, 0.6)
        
        return score
    



class ConflictDetector:
    """Detects conflicting information between documents."""
    
    def __init__(self, spacy_analyzer: SpaCyQueryAnalyzer):
        """Initialize the conflict detector."""
        self.spacy_analyzer = spacy_analyzer
        self.logger = LoggingConfig.get_logger(__name__)
        
    def detect_conflicts(self, documents: List[SearchResult]) -> ConflictAnalysis:
        """Detect conflicts between documents."""
        start_time = time.time()
        
        conflicts = ConflictAnalysis()
        
        # Compare documents pairwise for conflicts
        for i in range(len(documents)):
            for j in range(i + 1, len(documents)):
                doc1, doc2 = documents[i], documents[j]
                
                conflict_info = self._analyze_document_pair_for_conflicts(doc1, doc2)
                if conflict_info:
                    doc1_id = f"{doc1.source_type}:{doc1.source_title}"
                    doc2_id = f"{doc2.source_type}:{doc2.source_title}"
                    conflicts.conflicting_pairs.append((doc1_id, doc2_id, conflict_info))
                    
                    # Categorize conflict
                    conflict_type = conflict_info.get("type", "general")
                    if conflict_type not in conflicts.conflict_categories:
                        conflicts.conflict_categories[conflict_type] = []
                    conflicts.conflict_categories[conflict_type].append((doc1_id, doc2_id))
        
        # Generate resolution suggestions
        conflicts.resolution_suggestions = self._generate_resolution_suggestions(conflicts)
        
        processing_time = (time.time() - start_time) * 1000
        self.logger.info(f"Detected {len(conflicts.conflicting_pairs)} conflicts in {processing_time:.2f}ms")
        
        return conflicts
    
    def _analyze_document_pair_for_conflicts(self, doc1: SearchResult, 
                                           doc2: SearchResult) -> Optional[Dict[str, Any]]:
        """Analyze a pair of documents for potential conflicts."""
        # Only analyze documents that share some context (same project, entities, topics)
        if not self._should_analyze_for_conflicts(doc1, doc2):
            return None
        
        conflict_indicators = []
        
        # Check for contradictory information patterns
        contradiction_patterns = self._find_contradiction_patterns(doc1, doc2)
        if contradiction_patterns:
            conflict_indicators.extend(contradiction_patterns)
        
        # Check for version conflicts
        version_conflicts = self._detect_version_conflicts(doc1, doc2)
        if version_conflicts:
            conflict_indicators.extend(version_conflicts)
        
        # Check for procedural conflicts
        procedural_conflicts = self._detect_procedural_conflicts(doc1, doc2)
        if procedural_conflicts:
            conflict_indicators.extend(procedural_conflicts)
        
        if conflict_indicators:
            return {
                "type": self._categorize_conflict(conflict_indicators),
                "indicators": conflict_indicators,
                "confidence": self._calculate_conflict_confidence(conflict_indicators),
                "description": self._describe_conflict(conflict_indicators)
            }
        
        return None
    
    def _should_analyze_for_conflicts(self, doc1: SearchResult, doc2: SearchResult) -> bool:
        """Determine if two documents should be analyzed for conflicts."""
        # Same project
        if doc1.project_id and doc2.project_id and doc1.project_id == doc2.project_id:
            return True
        
        # Shared entities
        entities1 = self._extract_entity_texts(doc1.entities)
        entities2 = self._extract_entity_texts(doc2.entities)
        if len(set(entities1) & set(entities2)) > 0:
            return True
        
        # Shared topics
        topics1 = self._extract_topic_texts(doc1.topics)
        topics2 = self._extract_topic_texts(doc2.topics)
        if len(set(topics1) & set(topics2)) > 0:
            return True
        
        return False
    
    def _find_contradiction_patterns(self, doc1: SearchResult, doc2: SearchResult) -> List[str]:
        """Find textual patterns that suggest contradictions."""
        patterns = []
        
        # Look for opposing statements (simplified)
        opposing_keywords = [
            ("should", "should not"), ("enabled", "disabled"), ("true", "false"),
            ("required", "optional"), ("always", "never"), ("use", "avoid")
        ]
        
        text1_lower = doc1.text.lower()
        text2_lower = doc2.text.lower()
        
        for positive, negative in opposing_keywords:
            if positive in text1_lower and negative in text2_lower:
                patterns.append(f"Contradictory guidance: '{positive}' vs '{negative}'")
            elif negative in text1_lower and positive in text2_lower:
                patterns.append(f"Contradictory guidance: '{negative}' vs '{positive}'")
        
        return patterns
    
    def _detect_version_conflicts(self, doc1: SearchResult, doc2: SearchResult) -> List[str]:
        """Detect version-related conflicts."""
        conflicts = []
        
        # Check for different version numbers in similar contexts
        import re
        version_pattern = r'v?\d+\.\d+(?:\.\d+)?'
        
        versions1 = re.findall(version_pattern, doc1.text)
        versions2 = re.findall(version_pattern, doc2.text)
        
        if versions1 and versions2 and set(versions1) != set(versions2):
            conflicts.append(f"Version mismatch: {versions1} vs {versions2}")
        
        return conflicts
    
    def _detect_procedural_conflicts(self, doc1: SearchResult, doc2: SearchResult) -> List[str]:
        """Detect conflicts in procedural information."""
        conflicts = []
        
        # Look for step-by-step procedures that differ
        step_pattern = r'step \d+|step-\d+|\d+\.'
        
        if ("step" in doc1.text.lower() and "step" in doc2.text.lower()):
            # Simplified check for different procedure patterns
            if len(doc1.text.split("step")) != len(doc2.text.split("step")):
                conflicts.append("Different number of procedural steps")
        
        return conflicts
    
    def _categorize_conflict(self, indicators: List[str]) -> str:
        """Categorize the type of conflict."""
        indicator_text = " ".join(indicators).lower()
        
        if "version" in indicator_text:
            return "version_conflict"
        elif "step" in indicator_text or "procedure" in indicator_text:
            return "procedural_conflict"
        elif "guidance" in indicator_text:
            return "guidance_conflict"
        else:
            return "general_conflict"
    
    def _calculate_conflict_confidence(self, indicators: List[str]) -> float:
        """Calculate confidence in the conflict detection."""
        # Simple confidence based on number of indicators
        return min(0.9, len(indicators) * 0.3)
    
    def _describe_conflict(self, indicators: List[str]) -> str:
        """Generate a description of the conflict."""
        if len(indicators) == 1:
            return indicators[0]
        else:
            return f"Multiple conflicts detected: {'; '.join(indicators[:2])}"
    
    def _generate_resolution_suggestions(self, conflicts: ConflictAnalysis) -> Dict[str, str]:
        """Generate suggestions for resolving conflicts."""
        suggestions = {}
        
        for conflict_type, pairs in conflicts.conflict_categories.items():
            if conflict_type == "version_conflict":
                suggestions[conflict_type] = "Review documents for version consistency and update outdated information"
            elif conflict_type == "procedural_conflict":
                suggestions[conflict_type] = "Standardize procedural documentation and merge conflicting steps"
            elif conflict_type == "guidance_conflict":
                suggestions[conflict_type] = "Clarify guidance and ensure consistent recommendations"
            else:
                suggestions[conflict_type] = "Review conflicting documents and resolve inconsistencies"
        
        return suggestions
    
    def _extract_entity_texts(self, entities: List[Union[dict, str]]) -> List[str]:
        """Extract entity text from various formats."""
        texts = []
        for entity in entities:
            if isinstance(entity, dict):
                texts.append(entity.get("text", "").lower())
            elif isinstance(entity, str):
                texts.append(entity.lower())
        return [t for t in texts if t]
    
    def _extract_topic_texts(self, topics: List[Union[dict, str]]) -> List[str]:
        """Extract topic text from various formats."""
        texts = []
        for topic in topics:
            if isinstance(topic, dict):
                texts.append(topic.get("text", "").lower())
            elif isinstance(topic, str):
                texts.append(topic.lower())
        return [t for t in texts if t]


class CrossDocumentIntelligenceEngine:
    """Main engine that orchestrates cross-document intelligence analysis."""
    
    def __init__(self, spacy_analyzer: SpaCyQueryAnalyzer, 
                 knowledge_graph: Optional[DocumentKnowledgeGraph] = None):
        """Initialize the cross-document intelligence engine."""
        self.spacy_analyzer = spacy_analyzer
        self.knowledge_graph = knowledge_graph
        self.logger = LoggingConfig.get_logger(__name__)
        
        # Initialize component analyzers
        self.similarity_calculator = DocumentSimilarityCalculator(spacy_analyzer)
        self.cluster_analyzer = DocumentClusterAnalyzer(self.similarity_calculator)
        self.citation_analyzer = CitationNetworkAnalyzer()
        self.complementary_finder = ComplementaryContentFinder(self.similarity_calculator, knowledge_graph)
        self.conflict_detector = ConflictDetector(spacy_analyzer)
        
    def analyze_document_relationships(self, documents: List[SearchResult]) -> Dict[str, Any]:
        """Perform comprehensive cross-document relationship analysis."""
        start_time = time.time()
        
        self.logger.info(f"Starting cross-document intelligence analysis for {len(documents)} documents")
        
        # Document similarity analysis
        similarity_matrix = self._build_similarity_matrix(documents)
        
        # Document clustering
        clusters = self.cluster_analyzer.create_clusters(
            documents, 
            strategy=ClusteringStrategy.MIXED_FEATURES,
            max_clusters=10,
            min_cluster_size=2
        )
        
        # Citation network analysis
        citation_network = self.citation_analyzer.build_citation_network(documents)
        
        # Find complementary content for each document
        complementary_recommendations = {}
        for doc in documents[:5]:  # Limit to first 5 for performance
            doc_id = f"{doc.source_type}:{doc.source_title}"
            complementary = self.complementary_finder.find_complementary_content(doc, documents)
            complementary_recommendations[doc_id] = complementary
        
        # Conflict detection
        conflicts = self.conflict_detector.detect_conflicts(documents)
        
        processing_time = (time.time() - start_time) * 1000
        
        # Compile comprehensive analysis results
        analysis_results = {
            "summary": {
                "total_documents": len(documents),
                "processing_time_ms": processing_time,
                "clusters_found": len(clusters),
                "citation_relationships": len(citation_network.edges),
                "conflicts_detected": len(conflicts.conflicting_pairs),
                "complementary_pairs": sum(len(comp.recommendations) for comp in complementary_recommendations.values())
            },
            "document_clusters": [cluster.get_cluster_summary() for cluster in clusters],
            "citation_network": {
                "nodes": len(citation_network.nodes),
                "edges": len(citation_network.edges),
                "most_authoritative": self.citation_analyzer.get_most_authoritative_documents(citation_network, 5),
                "most_connected": self.citation_analyzer.get_most_connected_documents(citation_network, 5)
            },
            "complementary_content": {
                doc_id: comp.get_top_recommendations(3) 
                for doc_id, comp in complementary_recommendations.items()
            },
            "conflict_analysis": conflicts.get_conflict_summary(),
            "similarity_insights": self._extract_similarity_insights(similarity_matrix),
        }
        
        self.logger.info(f"Cross-document intelligence analysis completed in {processing_time:.2f}ms")
        
        return analysis_results
    
    def find_document_relationships(self, target_doc_id: str, documents: List[SearchResult], 
                                  relationship_types: List[RelationshipType] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Find specific relationships for a target document."""
        if relationship_types is None:
            relationship_types = [RelationshipType.SEMANTIC_SIMILARITY, RelationshipType.COMPLEMENTARY, 
                                RelationshipType.HIERARCHICAL]
        
        # Find target document
        target_doc = None
        for doc in documents:
            if f"{doc.source_type}:{doc.source_title}" == target_doc_id:
                target_doc = doc
                break
        
        if not target_doc:
            return {"error": "Target document not found"}
        
        relationships = {rel_type.value: [] for rel_type in relationship_types}
        
        for rel_type in relationship_types:
            if rel_type == RelationshipType.SEMANTIC_SIMILARITY:
                # Find similar documents
                for doc in documents:
                    if doc != target_doc:
                        similarity = self.similarity_calculator.calculate_similarity(target_doc, doc)
                        if similarity.similarity_score > 0.5:
                            relationships[rel_type.value].append({
                                "document_id": f"{doc.source_type}:{doc.source_title}",
                                "score": similarity.similarity_score,
                                "explanation": similarity.get_display_explanation()
                            })
            
            elif rel_type == RelationshipType.COMPLEMENTARY:
                # Find complementary content
                complementary = self.complementary_finder.find_complementary_content(target_doc, documents)
                relationships[rel_type.value] = complementary.get_top_recommendations(5)
            
            elif rel_type == RelationshipType.HIERARCHICAL:
                # Find hierarchical relationships
                for doc in documents:
                    if doc != target_doc:
                        if (doc.parent_id == target_doc_id or 
                            target_doc.parent_id == f"{doc.source_type}:{doc.source_title}"):
                            relationships[rel_type.value].append({
                                "document_id": f"{doc.source_type}:{doc.source_title}",
                                "relationship": "parent" if doc.parent_id == target_doc_id else "child",
                                "explanation": "Direct hierarchical relationship"
                            })
        
        # Sort each relationship type by score/relevance
        for rel_type in relationships:
            if relationships[rel_type]:
                relationships[rel_type] = sorted(
                    relationships[rel_type], 
                    key=lambda x: x.get("score", x.get("relevance_score", 0)), 
                    reverse=True
                )[:5]  # Top 5 for each type
        
        return relationships
    
    def _build_similarity_matrix(self, documents: List[SearchResult]) -> Dict[str, Dict[str, float]]:
        """Build similarity matrix for all document pairs."""
        matrix = {}
        
        for i, doc1 in enumerate(documents):
            doc1_id = f"{doc1.source_type}:{doc1.source_title}"
            matrix[doc1_id] = {}
            
            for j, doc2 in enumerate(documents):
                doc2_id = f"{doc2.source_type}:{doc2.source_title}"
                
                if i == j:
                    matrix[doc1_id][doc2_id] = 1.0
                elif doc2_id in matrix and doc1_id in matrix[doc2_id]:
                    # Use cached value
                    matrix[doc1_id][doc2_id] = matrix[doc2_id][doc1_id]
                else:
                    # Calculate similarity
                    similarity = self.similarity_calculator.calculate_similarity(doc1, doc2)
                    matrix[doc1_id][doc2_id] = similarity.similarity_score
        
        return matrix
    
    def _extract_similarity_insights(self, similarity_matrix: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """Extract insights from the similarity matrix."""
        if not similarity_matrix:
            return {}
        
        all_scores = []
        for doc1_scores in similarity_matrix.values():
            for doc2_id, score in doc1_scores.items():
                if score < 1.0:  # Exclude self-similarity
                    all_scores.append(score)
        
        if not all_scores:
            return {}
        
        return {
            "average_similarity": sum(all_scores) / len(all_scores),
            "max_similarity": max(all_scores),
            "min_similarity": min(all_scores),
            "high_similarity_pairs": sum(1 for score in all_scores if score > 0.7),
            "total_pairs_analyzed": len(all_scores)
        } 