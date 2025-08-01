"""Unit tests for Topic-Driven Search Chaining."""

import pytest
from unittest.mock import Mock

from qdrant_loader_mcp_server.search.enhanced.topic_search_chain import (
    TopicSearchChainGenerator,
    TopicRelationshipMap,
    TopicSearchChain,
    TopicChainLink,
    ChainStrategy
)
from qdrant_loader_mcp_server.search.nlp.spacy_analyzer import SpaCyQueryAnalyzer, QueryAnalysis
from qdrant_loader_mcp_server.search.components.search_result_models import create_hybrid_search_result


class TestTopicRelationshipMap:
    """Test suite for TopicRelationshipMap."""
    
    @pytest.fixture
    def mock_spacy_analyzer(self):
        """Mock spaCy analyzer."""
        analyzer = Mock(spec=SpaCyQueryAnalyzer)
        
        # Mock spaCy NLP pipeline
        mock_nlp = Mock()
        mock_doc = Mock()
        mock_doc.similarity.return_value = 0.75
        mock_nlp.return_value = mock_doc
        analyzer.nlp = mock_nlp
        
        return analyzer
    
    @pytest.fixture
    def topic_map(self, mock_spacy_analyzer):
        """Create TopicRelationshipMap instance."""
        return TopicRelationshipMap(mock_spacy_analyzer)
    
    @pytest.fixture
    def sample_search_results(self):
        """Create sample search results for testing."""
        return [
            create_hybrid_search_result(
                score=0.9,
                text="API documentation for user authentication",
                source_type="confluence",
                source_title="Auth API Guide",
                topics=[
                    {"text": "authentication", "score": 0.8},
                    {"text": "api", "score": 0.7}
                ],
                entities=[
                    {"text": "API", "label": "PRODUCT"},
                    {"text": "OAuth", "label": "PRODUCT"}
                ],
                breadcrumb_text="Development > Authentication > API"
            ),
            create_hybrid_search_result(
                score=0.8,
                text="Database security best practices",
                source_type="documentation",
                source_title="Security Guidelines",
                topics=[
                    {"text": "security", "score": 0.9},
                    {"text": "database", "score": 0.8}
                ],
                entities=[
                    {"text": "PostgreSQL", "label": "PRODUCT"},
                    {"text": "encryption", "label": "CONCEPT"}
                ],
                breadcrumb_text="Development > Security > Database"
            ),
            create_hybrid_search_result(
                score=0.85,
                text="OAuth implementation with JWT tokens",
                source_type="git",
                source_title="auth-service.py",
                topics=[
                    {"text": "authentication", "score": 0.9},
                    {"text": "oauth", "score": 0.8},
                    {"text": "jwt", "score": 0.7}
                ],
                entities=[
                    {"text": "JWT", "label": "PRODUCT"},
                    {"text": "token", "label": "CONCEPT"}
                ]
            )
        ]
    
    def test_build_topic_map(self, topic_map, sample_search_results):
        """Test building topic relationship map from search results."""
        topic_map.build_topic_map(sample_search_results)
        
        # Check topic document frequency
        assert topic_map.topic_document_frequency["authentication"] == 2
        assert topic_map.topic_document_frequency["api"] == 1
        assert topic_map.topic_document_frequency["security"] == 1
        
        # Check co-occurrence mapping
        assert "api" in topic_map.topic_cooccurrence["authentication"]
        assert "oauth" in topic_map.topic_cooccurrence["authentication"]
        
        # Check entity mapping (entities are stored in lowercase)
        assert "api" in topic_map.topic_entities_map["authentication"]
        assert "oauth" in topic_map.topic_entities_map["authentication"]
    
    def test_extract_topics_from_result(self, topic_map):
        """Test topic extraction from search results."""
        result = create_hybrid_search_result(
            score=0.9,
            text="Test content",
            source_type="confluence",
            source_title="Test Document",
            topics=[
                {"text": "Machine Learning", "score": 0.8},
                "artificial intelligence"  # String format
            ],
            breadcrumb_text="AI > ML > Deep Learning",
            section_title="Neural Networks",
            section_type="h2"
        )
        
        topics = topic_map._extract_topics_from_result(result)
        
        expected_topics = {
            "machine learning", "artificial intelligence", 
            "ai", "ml", "deep learning", "neural networks", "h2", "confluence"
        }
        
        assert set(topics) == expected_topics
    
    def test_find_semantic_related_topics(self, topic_map, mock_spacy_analyzer):
        """Test finding semantically related topics."""
        # Setup mock similarity scores
        mock_spacy_analyzer.nlp.return_value.similarity.side_effect = [0.8, 0.6, 0.3]
        
        # Build basic topic frequency map
        topic_map.topic_document_frequency = {
            "authentication": 3,
            "authorization": 2,  # High similarity
            "security": 2,       # Medium similarity  
            "networking": 1      # Low similarity
        }
        
        related = topic_map._find_semantic_related_topics("authentication", max_related=3)
        
        assert len(related) == 2  # Only topics above threshold (0.4)
        assert related[0][0] == "authorization"  # Highest similarity first
        assert related[0][1] > related[1][1]    # Descending order
    
    def test_find_related_topics_combined(self, topic_map, sample_search_results):
        """Test finding related topics using both semantic and co-occurrence."""
        topic_map.build_topic_map(sample_search_results)
        
        # Mock semantic similarity
        topic_map.spacy_analyzer.nlp.return_value.similarity.return_value = 0.7
        
        related = topic_map.find_related_topics("authentication", max_related=3)
        
        assert len(related) > 0
        # Should include both semantic and co-occurrence relationships
        topic_names = [topic for topic, score, rel_type in related]
        assert any(rel_type == "semantic_similarity" for topic, score, rel_type in related)


class TestTopicSearchChainGenerator:
    """Test suite for TopicSearchChainGenerator."""
    
    @pytest.fixture
    def mock_spacy_analyzer(self):
        """Mock spaCy analyzer with query analysis."""
        analyzer = Mock(spec=SpaCyQueryAnalyzer)
        
        # Mock query analysis results
        mock_analysis = QueryAnalysis(
            entities=[("API", "PRODUCT"), ("authentication", "CONCEPT")],
            pos_patterns=["NOUN", "NOUN"],
            semantic_keywords=["api", "authentication", "security"],
            intent_signals={"primary_intent": "technical_lookup", "confidence": 0.8},
            main_concepts=["API authentication", "security framework"],
            query_vector=Mock(),
            semantic_similarity_cache={},
            is_question=False,
            is_technical=True,
            complexity_score=0.7,
            processed_tokens=3,
            processing_time_ms=15.5
        )
        
        analyzer.analyze_query_semantic.return_value = mock_analysis
        
        # Mock spaCy NLP pipeline properly
        mock_nlp = Mock()
        mock_doc = Mock()
        mock_doc.similarity.return_value = 0.6
        mock_nlp.return_value = mock_doc
        analyzer.nlp = mock_nlp
        
        return analyzer
    
    @pytest.fixture
    def mock_knowledge_graph(self):
        """Mock knowledge graph."""
        return Mock()
    
    @pytest.fixture
    def chain_generator(self, mock_spacy_analyzer, mock_knowledge_graph):
        """Create TopicSearchChainGenerator instance."""
        return TopicSearchChainGenerator(mock_spacy_analyzer, mock_knowledge_graph)
    
    @pytest.fixture
    def sample_search_results_for_init(self):
        """Sample results for initializing topic relationships."""
        return [
            create_hybrid_search_result(
                score=0.9,
                text="REST API documentation",
                source_type="confluence",
                source_title="API Guide", 
                topics=[{"text": "api", "score": 0.8}, {"text": "rest", "score": 0.7}]
            ),
            create_hybrid_search_result(
                score=0.8,
                text="Authentication mechanisms",
                source_type="documentation",
                source_title="Auth Guide",
                topics=[{"text": "authentication", "score": 0.9}, {"text": "security", "score": 0.7}]
            )
        ]
    
    def test_initialize_from_results(self, chain_generator, sample_search_results_for_init):
        """Test initializing topic relationships from search results."""
        chain_generator.initialize_from_results(sample_search_results_for_init)
        
        # Should have topic frequencies
        assert chain_generator.topic_map.topic_document_frequency["api"] >= 1
        assert chain_generator.topic_map.topic_document_frequency["authentication"] >= 1
    
    def test_extract_primary_topics(self, chain_generator, mock_spacy_analyzer):
        """Test extracting primary topics from query analysis."""
        query = "How to implement API authentication"
        
        primary_topics = chain_generator._extract_primary_topics(
            mock_spacy_analyzer.analyze_query_semantic(query), 
            query
        )
        
        expected_topics = {"api", "authentication", "security", "API authentication", "security framework"}
        assert set(primary_topics) == expected_topics
    
    def test_generate_breadth_first_chain(self, chain_generator, sample_search_results_for_init):
        """Test breadth-first chain generation."""
        chain_generator.initialize_from_results(sample_search_results_for_init)
        
        # Mock related topics
        chain_generator.topic_map.find_related_topics = Mock(return_value=[
            ("oauth", 0.8, "semantic_similarity"),
            ("jwt", 0.7, "cooccurrence")
        ])
        
        query = "API authentication methods"
        spacy_analysis = chain_generator.spacy_analyzer.analyze_query_semantic(query)
        primary_topics = ["authentication", "api"]
        
        chain_links = chain_generator._generate_breadth_first_chain(
            query, primary_topics, spacy_analysis, max_links=3
        )
        
        assert len(chain_links) <= 3
        assert chain_links[0].exploration_type == "broader"
        assert "oauth" in chain_links[0].related_topics or "jwt" in chain_links[0].related_topics
    
    def test_generate_depth_first_chain(self, chain_generator, sample_search_results_for_init):
        """Test depth-first chain generation."""
        chain_generator.initialize_from_results(sample_search_results_for_init)
        
        # Mock progressive related topics
        call_count = 0
        def mock_find_related(topic, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [("oauth", 0.8, "semantic_similarity")]
            elif call_count == 2:
                return [("jwt", 0.7, "semantic_similarity")]
            else:
                return []
        
        chain_generator.topic_map.find_related_topics = Mock(side_effect=mock_find_related)
        
        query = "authentication systems"
        spacy_analysis = chain_generator.spacy_analyzer.analyze_query_semantic(query)
        primary_topics = ["authentication"]
        
        chain_links = chain_generator._generate_depth_first_chain(
            query, primary_topics, spacy_analysis, max_links=3
        )
        
        assert len(chain_links) <= 3
        assert all(link.exploration_type == "deeper" for link in chain_links)
        # Should progressively explore deeper into topics
        if len(chain_links) > 1:
            assert chain_links[1].topic_focus in ["oauth", "jwt"]
    
    def test_generate_search_chain_mixed_exploration(self, chain_generator, sample_search_results_for_init):
        """Test mixed exploration strategy."""
        chain_generator.initialize_from_results(sample_search_results_for_init)
        
        # Mock related topics
        chain_generator.topic_map.find_related_topics = Mock(return_value=[
            ("security", 0.8, "semantic_similarity"),
            ("oauth", 0.7, "cooccurrence")
        ])
        
        query = "API security best practices"
        
        topic_chain = chain_generator.generate_search_chain(
            original_query=query,
            strategy=ChainStrategy.MIXED_EXPLORATION,
            max_links=4
        )
        
        assert isinstance(topic_chain, TopicSearchChain)
        assert topic_chain.original_query == query
        assert topic_chain.strategy == ChainStrategy.MIXED_EXPLORATION
        assert len(topic_chain.chain_links) <= 4
        assert topic_chain.total_topics_covered > 0
        assert 0 <= topic_chain.estimated_discovery_potential <= 1
        assert 0 <= topic_chain.chain_coherence_score <= 1
        assert topic_chain.generation_time_ms > 0
    
    def test_calculate_discovery_potential(self, chain_generator):
        """Test discovery potential calculation."""
        chain_links = [
            TopicChainLink(
                query="test query 1",
                topic_focus="api",
                related_topics=["rest"],
                chain_position=0,
                relevance_score=0.9,
                exploration_type="broader"
            ),
            TopicChainLink(
                query="test query 2", 
                topic_focus="authentication",
                related_topics=["oauth"],
                chain_position=1,
                relevance_score=0.8,
                exploration_type="deeper"
            )
        ]
        
        mock_analysis = Mock()
        potential = chain_generator._calculate_discovery_potential(chain_links, mock_analysis)
        
        assert 0 <= potential <= 1
    
    def test_calculate_chain_coherence(self, chain_generator):
        """Test chain coherence calculation."""
        # Coherent chain with topic overlap
        coherent_links = [
            TopicChainLink(
                query="test 1",
                topic_focus="api",
                related_topics=["rest"],
                chain_position=0,
                relevance_score=0.9
            ),
            TopicChainLink(
                query="test 2",
                topic_focus="rest",  # Overlaps with previous
                related_topics=["http"],
                chain_position=1,
                relevance_score=0.8
            )
        ]
        
        coherence = chain_generator._calculate_chain_coherence(coherent_links)
        assert 0 <= coherence <= 1
        assert coherence > 0  # Should have some coherence due to overlap
        
        # Incoherent chain with no overlap
        incoherent_links = [
            TopicChainLink(
                query="test 1",
                topic_focus="api",
                related_topics=["rest"],
                chain_position=0,
                relevance_score=0.9
            ),
            TopicChainLink(
                query="test 2",
                topic_focus="database",  # No overlap
                related_topics=["sql"],
                chain_position=1,
                relevance_score=0.8
            )
        ]
        
        incoherent_coherence = chain_generator._calculate_chain_coherence(incoherent_links)
        assert coherence > incoherent_coherence  # Coherent should score higher


class TestTopicChainIntegration:
    """Integration tests for topic chaining functionality."""
    
    @pytest.fixture
    def real_spacy_analyzer(self):
        """Real spaCy analyzer for integration testing."""
        try:
            return SpaCyQueryAnalyzer(spacy_model="en_core_web_md")
        except OSError:
            pytest.skip("spaCy model en_core_web_md not available")
    
    def test_end_to_end_topic_chain_generation(self, real_spacy_analyzer):
        """Test complete topic chain generation workflow."""
        generator = TopicSearchChainGenerator(real_spacy_analyzer)
        
        # Create realistic search results
        sample_results = [
            create_hybrid_search_result(
                score=0.9,
                text="RESTful API design principles and best practices for authentication",
                source_type="confluence",
                source_title="API Design Guide",
                topics=[
                    {"text": "api design", "score": 0.9},
                    {"text": "rest", "score": 0.8},
                    {"text": "authentication", "score": 0.7}
                ],
                entities=[
                    {"text": "REST", "label": "CONCEPT"},
                    {"text": "HTTP", "label": "PROTOCOL"}
                ]
            ),
            create_hybrid_search_result(
                score=0.85,
                text="OAuth 2.0 implementation with JWT tokens for secure API access",
                source_type="documentation", 
                source_title="OAuth Guide",
                topics=[
                    {"text": "oauth", "score": 0.9},
                    {"text": "jwt", "score": 0.8},
                    {"text": "security", "score": 0.7}
                ],
                entities=[
                    {"text": "OAuth", "label": "PRODUCT"},
                    {"text": "JWT", "label": "PRODUCT"}
                ]
            )
        ]
        
        # Initialize topic relationships
        generator.initialize_from_results(sample_results)
        
        # Generate topic chain
        chain = generator.generate_search_chain(
            original_query="How to implement secure API authentication",
            strategy=ChainStrategy.MIXED_EXPLORATION,
            max_links=3
        )
        
        # Verify chain properties
        assert isinstance(chain, TopicSearchChain)
        assert chain.original_query == "How to implement secure API authentication"
        assert len(chain.chain_links) <= 3
        assert chain.total_topics_covered > 0
        assert chain.generation_time_ms > 0
        
        # Verify chain links have valid structure
        for link in chain.chain_links:
            assert isinstance(link.query, str)
            assert len(link.query) > 0
            assert isinstance(link.topic_focus, str)
            assert isinstance(link.related_topics, list)
            assert 0 <= link.relevance_score <= 1
            assert link.exploration_type in ["related", "deeper", "broader", "alternative"]
    
    def test_topic_similarity_with_real_spacy(self, real_spacy_analyzer):
        """Test topic similarity using real spaCy vectors."""
        topic_map = TopicRelationshipMap(real_spacy_analyzer)
        
        # Test semantic similarity calculation
        similarity = real_spacy_analyzer.nlp("authentication").similarity(
            real_spacy_analyzer.nlp("authorization")
        )
        
        assert 0 <= similarity <= 1
        assert similarity > 0.1  # Should be somewhat similar concepts (spaCy similarity varies)
        
        # Test with unrelated concepts
        unrelated_similarity = real_spacy_analyzer.nlp("authentication").similarity(
            real_spacy_analyzer.nlp("cooking")
        )
        
        assert similarity > unrelated_similarity  # Related concepts should be more similar


if __name__ == "__main__":
    pytest.main([__file__]) 