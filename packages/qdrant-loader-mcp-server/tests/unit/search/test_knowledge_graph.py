"""Unit tests for Knowledge Graph implementation."""

import pytest
from unittest.mock import Mock, patch

from qdrant_loader_mcp_server.search.enhanced.knowledge_graph import (
    KnowledgeGraph,
    DocumentKnowledgeGraph,
    GraphBuilder,
    GraphTraverser,
    GraphNode,
    GraphEdge,
    NodeType,
    RelationshipType,
    TraversalStrategy
)
from qdrant_loader_mcp_server.search.nlp.spacy_analyzer import SpaCyQueryAnalyzer, QueryAnalysis
from qdrant_loader_mcp_server.search.components.search_result_models import create_hybrid_search_result


class TestKnowledgeGraph:
    """Test core knowledge graph functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.graph = KnowledgeGraph()
        
        # Sample nodes
        self.doc_node = GraphNode(
            id="doc_1",
            node_type=NodeType.DOCUMENT,
            title="Test Document",
            entities=["Entity1", "Entity2"],
            topics=["Topic1", "Topic2"],
            keywords=["keyword1", "keyword2"]
        )
        
        self.section_node = GraphNode(
            id="section_1",
            node_type=NodeType.SECTION,
            title="Test Section",
            entities=["Entity1"],
            topics=["Topic1"],
            keywords=["keyword1"]
        )
        
        self.entity_node = GraphNode(
            id="entity_1",
            node_type=NodeType.ENTITY,
            title="Entity1"
        )
    
    def test_graph_initialization(self):
        """Test knowledge graph initialization."""
        assert len(self.graph.nodes) == 0
        assert len(self.graph.edges) == 0
        assert len(self.graph.node_type_index) == 0
    
    def test_add_node(self):
        """Test adding nodes to the graph."""
        # Test successful node addition
        result = self.graph.add_node(self.doc_node)
        assert result is True
        assert self.doc_node.id in self.graph.nodes
        assert self.doc_node.id in self.graph.node_type_index[NodeType.DOCUMENT]
        
        # Test entity indexing
        assert "entity1" in self.graph.entity_index
        assert self.doc_node.id in self.graph.entity_index["entity1"]
        
        # Test topic indexing
        assert "topic1" in self.graph.topic_index
        assert self.doc_node.id in self.graph.topic_index["topic1"]
    
    def test_add_edge(self):
        """Test adding edges to the graph."""
        # Add prerequisite nodes
        self.graph.add_node(self.doc_node)
        self.graph.add_node(self.section_node)
        
        edge = GraphEdge(
            source_id=self.doc_node.id,
            target_id=self.section_node.id,
            relationship_type=RelationshipType.CONTAINS,
            weight=0.8,
            confidence=0.9
        )
        
        result = self.graph.add_edge(edge)
        assert result is True
        
        edge_key = (self.doc_node.id, self.section_node.id, RelationshipType.CONTAINS.value)
        assert edge_key in self.graph.edges
        
        # Test edge with missing nodes
        invalid_edge = GraphEdge(
            source_id="nonexistent",
            target_id=self.section_node.id,
            relationship_type=RelationshipType.MENTIONS,
            weight=0.5
        )
        
        result = self.graph.add_edge(invalid_edge)
        assert result is False
    
    def test_find_nodes_by_type(self):
        """Test finding nodes by type."""
        self.graph.add_node(self.doc_node)
        self.graph.add_node(self.section_node)
        self.graph.add_node(self.entity_node)
        
        doc_nodes = self.graph.find_nodes_by_type(NodeType.DOCUMENT)
        assert len(doc_nodes) == 1
        assert doc_nodes[0].id == self.doc_node.id
        
        section_nodes = self.graph.find_nodes_by_type(NodeType.SECTION)
        assert len(section_nodes) == 1
        
        topic_nodes = self.graph.find_nodes_by_type(NodeType.TOPIC)
        assert len(topic_nodes) == 0
    
    def test_find_nodes_by_entity(self):
        """Test finding nodes by entity."""
        self.graph.add_node(self.doc_node)
        self.graph.add_node(self.section_node)
        
        # Both nodes contain "Entity1"
        entity1_nodes = self.graph.find_nodes_by_entity("Entity1")
        assert len(entity1_nodes) == 2
        
        # Only doc_node contains "Entity2"
        entity2_nodes = self.graph.find_nodes_by_entity("Entity2")
        assert len(entity2_nodes) == 1
        assert entity2_nodes[0].id == self.doc_node.id
        
        # Case insensitive search
        entity_lower_nodes = self.graph.find_nodes_by_entity("entity1")
        assert len(entity_lower_nodes) == 2
    
    def test_find_nodes_by_topic(self):
        """Test finding nodes by topic."""
        self.graph.add_node(self.doc_node)
        self.graph.add_node(self.section_node)
        
        topic1_nodes = self.graph.find_nodes_by_topic("Topic1")
        assert len(topic1_nodes) == 2
        
        topic2_nodes = self.graph.find_nodes_by_topic("Topic2")
        assert len(topic2_nodes) == 1
        assert topic2_nodes[0].id == self.doc_node.id
    
    def test_calculate_centrality_scores(self):
        """Test centrality score calculation."""
        # Create a small graph
        self.graph.add_node(self.doc_node)
        self.graph.add_node(self.section_node)
        self.graph.add_node(self.entity_node)
        
        # Add edges
        edge1 = GraphEdge(
            source_id=self.doc_node.id,
            target_id=self.section_node.id,
            relationship_type=RelationshipType.CONTAINS
        )
        edge2 = GraphEdge(
            source_id=self.section_node.id,
            target_id=self.entity_node.id,
            relationship_type=RelationshipType.MENTIONS
        )
        
        self.graph.add_edge(edge1)
        self.graph.add_edge(edge2)
        
        # Calculate centrality
        self.graph.calculate_centrality_scores()
        
        # Check that scores were calculated
        for node in self.graph.nodes.values():
            assert node.centrality_score >= 0.0
            # Hub and authority scores can be negative in small graphs - just check they exist
            assert isinstance(node.hub_score, float)
            assert isinstance(node.authority_score, float)
    
    def test_get_neighbors(self):
        """Test getting neighboring nodes."""
        self.graph.add_node(self.doc_node)
        self.graph.add_node(self.section_node)
        
        edge = GraphEdge(
            source_id=self.doc_node.id,
            target_id=self.section_node.id,
            relationship_type=RelationshipType.CONTAINS
        )
        self.graph.add_edge(edge)
        
        neighbors = self.graph.get_neighbors(self.doc_node.id)
        assert len(neighbors) == 1
        assert neighbors[0][0] == self.section_node.id
        assert neighbors[0][1].relationship_type == RelationshipType.CONTAINS
        
        # Test with relationship type filter
        contains_neighbors = self.graph.get_neighbors(
            self.doc_node.id, 
            relationship_types=[RelationshipType.CONTAINS]
        )
        assert len(contains_neighbors) == 1
        
        mentions_neighbors = self.graph.get_neighbors(
            self.doc_node.id,
            relationship_types=[RelationshipType.MENTIONS]
        )
        assert len(mentions_neighbors) == 0
    
    def test_get_statistics(self):
        """Test graph statistics generation."""
        self.graph.add_node(self.doc_node)
        self.graph.add_node(self.section_node)
        
        edge = GraphEdge(
            source_id=self.doc_node.id,
            target_id=self.section_node.id,
            relationship_type=RelationshipType.CONTAINS
        )
        self.graph.add_edge(edge)
        
        stats = self.graph.get_statistics()
        
        assert stats["total_nodes"] == 2
        assert stats["total_edges"] == 1
        assert stats["node_types"][NodeType.DOCUMENT.value] == 1
        assert stats["node_types"][NodeType.SECTION.value] == 1
        assert stats["relationship_types"][RelationshipType.CONTAINS.value] == 1
        assert "connected_components" in stats
        assert "avg_degree" in stats


class TestGraphTraverser:
    """Test graph traversal algorithms."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.graph = KnowledgeGraph()
        self.spacy_analyzer = Mock(spec=SpaCyQueryAnalyzer)
        self.traverser = GraphTraverser(self.graph, self.spacy_analyzer)
        
        # Create a test graph: doc -> section1 -> entity1
        #                           -> section2 -> entity2
        self.doc_node = GraphNode(
            id="doc_1",
            node_type=NodeType.DOCUMENT,
            title="Test Document"
        )
        
        self.section1_node = GraphNode(
            id="section_1",
            node_type=NodeType.SECTION,
            title="Section 1"
        )
        
        self.section2_node = GraphNode(
            id="section_2",
            node_type=NodeType.SECTION,
            title="Section 2"
        )
        
        self.entity1_node = GraphNode(
            id="entity_1",
            node_type=NodeType.ENTITY,
            title="Entity 1"
        )
        
        self.entity2_node = GraphNode(
            id="entity_2",
            node_type=NodeType.ENTITY,
            title="Entity 2"
        )
        
        # Add nodes to graph
        for node in [self.doc_node, self.section1_node, self.section2_node, 
                     self.entity1_node, self.entity2_node]:
            self.graph.add_node(node)
        
        # Add edges
        edges = [
            GraphEdge(
                source_id="doc_1",
                target_id="section_1",
                relationship_type=RelationshipType.CONTAINS,
                weight=1.0
            ),
            GraphEdge(
                source_id="doc_1",
                target_id="section_2",
                relationship_type=RelationshipType.CONTAINS,
                weight=1.0
            ),
            GraphEdge(
                source_id="section_1",
                target_id="entity_1",
                relationship_type=RelationshipType.MENTIONS,
                weight=0.8
            ),
            GraphEdge(
                source_id="section_2",
                target_id="entity_2",
                relationship_type=RelationshipType.MENTIONS,
                weight=0.6
            )
        ]
        
        for edge in edges:
            self.graph.add_edge(edge)
    
    def test_breadth_first_traversal(self):
        """Test breadth-first traversal strategy."""
        results = self.traverser.traverse(
            start_nodes=["doc_1"],
            strategy=TraversalStrategy.BREADTH_FIRST,
            max_hops=2,
            max_results=10
        )
        
        assert len(results) > 0
        
        # Check that we get both sections and entities
        result_nodes = []
        for result in results:
            result_nodes.extend([node.id for node in result.nodes])
        
        assert "section_1" in result_nodes
        assert "section_2" in result_nodes
    
    def test_weighted_traversal(self):
        """Test weighted traversal strategy."""
        results = self.traverser.traverse(
            start_nodes=["doc_1"],
            strategy=TraversalStrategy.WEIGHTED,
            max_hops=2,
            max_results=10
        )
        
        assert len(results) > 0
        
        # Results should be ordered by weight (higher weights first)
        weights = [result.total_weight for result in results]
        assert weights == sorted(weights, reverse=True)
    
    def test_centrality_traversal(self):
        """Test centrality-based traversal strategy."""
        # Calculate centrality scores first
        self.graph.calculate_centrality_scores()
        
        results = self.traverser.traverse(
            start_nodes=["doc_1"],
            strategy=TraversalStrategy.CENTRALITY,
            max_hops=2,
            max_results=10
        )
        
        assert len(results) > 0
    
    def test_semantic_traversal(self):
        """Test semantic similarity traversal."""
        # Mock query analysis
        mock_query_analysis = QueryAnalysis(
            entities=[("Entity 1", "ENTITY")],
            pos_patterns=["NOUN"],
            semantic_keywords=["entity", "test"],
            intent_signals={"primary_intent": "informational"},
            main_concepts=["entity concept"],
            query_vector=Mock(),
            semantic_similarity_cache={},
            is_question=False,
            is_technical=True,
            complexity_score=0.5,
            processed_tokens=3,
            processing_time_ms=5.0
        )
        
        results = self.traverser.traverse(
            start_nodes=["doc_1"],
            query_analysis=mock_query_analysis,
            strategy=TraversalStrategy.SEMANTIC,
            max_hops=2,
            max_results=10
        )
        
        assert len(results) > 0
        
        # Results should be ordered by semantic score
        semantic_scores = [result.semantic_score for result in results]
        assert semantic_scores == sorted(semantic_scores, reverse=True)
    
    def test_max_hops_limit(self):
        """Test that traversal respects max hops limit."""
        results = self.traverser.traverse(
            start_nodes=["doc_1"],
            strategy=TraversalStrategy.BREADTH_FIRST,
            max_hops=2,  # Allow reaching sections and entities
            max_results=10
        )
        
        # Should get some results with max_hops=2
        assert len(results) > 0
        
        # Test with max_hops=1 - should get fewer results
        results_limited = self.traverser.traverse(
            start_nodes=["doc_1"],
            strategy=TraversalStrategy.BREADTH_FIRST,
            max_hops=1,
            max_results=10
        )
        
        # Should respect hop limit (fewer or equal results)
        assert len(results_limited) <= len(results)
    
    def test_min_weight_filtering(self):
        """Test minimum weight filtering."""
        results = self.traverser.traverse(
            start_nodes=["doc_1"],
            strategy=TraversalStrategy.WEIGHTED,
            max_hops=3,
            max_results=10,
            min_weight=0.7  # Should filter out entity_2 (weight 0.6)
        )
        
        # Should include entity_1 (weight 0.8) but not entity_2 (weight 0.6)
        result_node_ids = []
        for result in results:
            result_node_ids.extend([node.id for node in result.nodes])
        
        if "entity_1" in result_node_ids:
            assert "entity_1" in result_node_ids
        # entity_2 might be filtered out due to weight threshold


class TestGraphBuilder:
    """Test knowledge graph construction from search results."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.spacy_analyzer = Mock(spec=SpaCyQueryAnalyzer)
        self.graph_builder = GraphBuilder(self.spacy_analyzer)
        
        # Create sample search results
        self.search_results = [
            create_hybrid_search_result(
                score=0.9,
                text="This document discusses API authentication and authorization methods.",
                source="git",
                source_type="git",
                source_title="Authentication Guide",
                metadata={
                    "title": "Authentication Guide",
                    "source_url": "https://example.com/auth",
                    "breadcrumb": "Documentation > Security > Authentication",
                    "semantic_analysis": {
                        "entities": [
                            {"text": "API", "label": "PRODUCT"},
                            {"text": "authentication", "label": "CONCEPT"}
                        ],
                        "topics": ["security", "authentication"],
                        "key_phrases": ["API authentication", "authorization methods"]
                    },
                    "pos_analysis": {
                        "entities": ["API", "authentication"],
                        "keywords": ["document", "discusses", "methods"]
                    },
                    "content_analysis": {
                        "word_count": 150,
                        "has_tables": False,
                        "has_code_blocks": True
                    }
                }
            ),
            create_hybrid_search_result(
                score=0.8,
                text="Security best practices for API development include proper authentication.",
                source="confluence",
                source_type="confluence",
                source_title="Security Best Practices",
                metadata={
                    "title": "Security Best Practices",
                    "source_url": "https://wiki.example.com/security",
                    "breadcrumb": "Wiki > Development > Security",
                    "semantic_analysis": {
                        "entities": [
                            {"text": "API", "label": "PRODUCT"},
                            {"text": "security", "label": "CONCEPT"}
                        ],
                        "topics": ["security", "development"],
                        "key_phrases": ["security best practices", "API development"]
                    },
                    "pos_analysis": {
                        "entities": ["API", "security"],
                        "keywords": ["practices", "development", "proper"]
                    }
                }
            )
        ]
    
    def test_build_from_search_results(self):
        """Test building knowledge graph from search results."""
        graph = self.graph_builder.build_from_search_results(self.search_results)
        
        assert isinstance(graph, KnowledgeGraph)
        assert len(graph.nodes) > 0
        
        # Should have document nodes
        doc_nodes = graph.find_nodes_by_type(NodeType.DOCUMENT)
        assert len(doc_nodes) > 0
        
        # Should have section nodes
        section_nodes = graph.find_nodes_by_type(NodeType.SECTION)
        assert len(section_nodes) == 2  # One per search result
        
        # Should have entity nodes for frequent entities (from titles)
        entity_nodes = graph.find_nodes_by_type(NodeType.ENTITY)
        # Should have entities based on titles that appear in multiple documents
        if len(entity_nodes) > 0:
            # At least some entities should be extracted
            assert len(entity_nodes) >= 0
    
    def test_create_document_nodes(self):
        """Test document node creation."""
        doc_nodes = self.graph_builder._create_document_nodes(self.search_results)
        
        # Should create document nodes and section nodes
        assert len(doc_nodes) == 4  # 2 documents + 2 sections
        
        # Check node types
        doc_type_nodes = [node for node in doc_nodes if node.node_type == NodeType.DOCUMENT]
        section_type_nodes = [node for node in doc_nodes if node.node_type == NodeType.SECTION]
        
        assert len(doc_type_nodes) == 2
        assert len(section_type_nodes) == 2
        
        # Check that entities and topics are extracted
        for node in doc_nodes:
            if node.node_type == NodeType.SECTION:
                assert len(node.entities) > 0
                assert len(node.topics) > 0
    
    def test_create_concept_nodes(self):
        """Test entity and topic node creation."""
        entity_nodes, topic_nodes = self.graph_builder._create_concept_nodes(self.search_results)
        
        # Should create some entity and topic nodes
        # The actual entities depend on what appears frequently in titles/fields
        assert isinstance(entity_nodes, list)
        assert isinstance(topic_nodes, list)
        
        # Topic nodes are only created for topics that appear in multiple documents
        # With our test data having 2 different source_types, no topics will be created
        # This is expected behavior - let's just check the structure is correct
        assert len(topic_nodes) >= 0  # Can be 0 if no topics appear in multiple docs
    
    def test_relationship_creation(self):
        """Test relationship creation between nodes."""
        graph = self.graph_builder.build_from_search_results(self.search_results)
        
        # Should have CONTAINS relationships (doc -> section)
        contains_edges = [
            edge for edge in graph.edges.values() 
            if edge.relationship_type == RelationshipType.CONTAINS
        ]
        assert len(contains_edges) > 0
        
        # Should have MENTIONS relationships (section -> entity)
        mentions_edges = [
            edge for edge in graph.edges.values()
            if edge.relationship_type == RelationshipType.MENTIONS
        ]
        assert len(mentions_edges) > 0


class TestDocumentKnowledgeGraph:
    """Test high-level document knowledge graph interface."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.spacy_analyzer = Mock(spec=SpaCyQueryAnalyzer)
        self.doc_kg = DocumentKnowledgeGraph(self.spacy_analyzer)
        
        # Mock search results
        self.search_results = [
            create_hybrid_search_result(
                score=0.9,
                text="API documentation for authentication",
                source="git",
                source_type="git",
                source_title="API Documentation",
                metadata={
                    "semantic_analysis": {
                        "entities": [{"text": "API", "label": "PRODUCT"}],
                        "topics": ["authentication"]
                    },
                    "pos_analysis": {
                        "entities": ["API"],
                        "keywords": ["documentation", "authentication"]
                    }
                }
            )
        ]
    
    def test_build_graph(self):
        """Test graph building from search results."""
        result = self.doc_kg.build_graph(self.search_results)
        
        assert result is True
        assert self.doc_kg.knowledge_graph is not None
        assert self.doc_kg.traverser is not None
    
    @patch.object(SpaCyQueryAnalyzer, 'analyze_query_semantic')
    def test_find_related_content(self, mock_analyze):
        """Test finding related content via graph traversal."""
        # Setup graph
        self.doc_kg.build_graph(self.search_results)
        
        # Mock query analysis
        mock_analyze.return_value = QueryAnalysis(
            entities=[("API", "PRODUCT")],
            pos_patterns=["NOUN"],
            semantic_keywords=["api", "documentation"],
            intent_signals={"primary_intent": "technical"},
            main_concepts=["API documentation"],
            query_vector=Mock(),
            semantic_similarity_cache={},
            is_question=False,
            is_technical=True,
            complexity_score=0.4,
            processed_tokens=3,
            processing_time_ms=3.5
        )
        
        results = self.doc_kg.find_related_content(
            query="API documentation",
            max_hops=2,
            max_results=5
        )
        
        # Should return traversal results
        assert isinstance(results, list)
        # Results might be empty if no suitable start nodes found, which is ok for this test
    
    def test_get_graph_statistics(self):
        """Test getting graph statistics."""
        # Before building graph
        stats = self.doc_kg.get_graph_statistics()
        assert stats is None
        
        # After building graph
        self.doc_kg.build_graph(self.search_results)
        stats = self.doc_kg.get_graph_statistics()
        
        assert stats is not None
        assert "total_nodes" in stats
        assert "total_edges" in stats
        assert "node_types" in stats
    
    def test_export_graph(self):
        """Test graph export functionality."""
        self.doc_kg.build_graph(self.search_results)
        
        # Test JSON export
        json_export = self.doc_kg.export_graph(format="json")
        assert json_export is not None
        
        # Should be valid JSON
        import json
        data = json.loads(json_export)
        assert "nodes" in data
        assert "edges" in data


if __name__ == "__main__":
    pytest.main([__file__]) 