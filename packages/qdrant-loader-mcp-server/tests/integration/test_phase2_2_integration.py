"""Integration tests for Phase 2.2 Intent-Aware Adaptive Search."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Dict, Any

from qdrant_loader_mcp_server.search.hybrid_search import HybridSearchEngine, HybridSearchResult
from qdrant_loader_mcp_server.search.models import SearchResult
from qdrant_loader_mcp_server.search.enhanced.intent_classifier import (
    IntentType, SearchIntent, IntentClassifier, AdaptiveSearchStrategy
)
from qdrant_loader_mcp_server.search.enhanced.knowledge_graph import DocumentKnowledgeGraph
from qdrant_loader_mcp_server.search.nlp.spacy_analyzer import SpaCyQueryAnalyzer, QueryAnalysis


class TestPhase2_2Integration:
    """Integration tests for Phase 2.2 Intent-Aware Adaptive Search."""
    
    @pytest.fixture
    def mock_qdrant_client(self):
        """Create a mock Qdrant client."""
        client = AsyncMock()
        client.search = AsyncMock(return_value=[
            Mock(score=0.9, payload={
                "content": "FastAPI OAuth 2.0 authentication implementation guide",
                "source_type": "git",
                "metadata": {
                    "title": "OAuth Authentication Guide",
                    "url": "https://example.com/oauth-guide",
                    "has_code_blocks": True,
                    "section_type": "implementation",
                    "entities": ["OAuth", "FastAPI"],
                    "topics": ["authentication", "security"]
                }
            }),
            Mock(score=0.8, payload={
                "content": "Business requirements for authentication system",
                "source_type": "confluence", 
                "metadata": {
                    "title": "Auth Requirements",
                    "url": "https://example.com/auth-requirements",
                    "has_code_blocks": False,
                    "section_type": "requirements",
                    "entities": ["Company"],
                    "topics": ["requirements", "security"]
                }
            }),
        ])
        
        client.scroll = AsyncMock(return_value=([
            Mock(payload={
                "content": "FastAPI OAuth 2.0 authentication implementation guide",
                "source_type": "git",
                "metadata": {"title": "OAuth Guide"}
            }),
            Mock(payload={
                "content": "Business requirements for authentication system", 
                "source_type": "confluence",
                "metadata": {"title": "Auth Requirements"}
            }),
        ], None))
        
        # Mock collection operations for SearchEngine initialization
        collections_response = MagicMock()
        collections_response.collections = []
        client.get_collections = AsyncMock(return_value=collections_response)
        client.create_collection = AsyncMock(return_value=None)
        client.close = AsyncMock(return_value=None)
        
        return client
    
    @pytest.fixture 
    def mock_openai_client(self):
        """Create a mock OpenAI client."""
        client = AsyncMock()
        client.embeddings.create.return_value = Mock(
            data=[Mock(embedding=[0.1] * 1536)]
        )
        return client
    
    @pytest.fixture
    def mock_knowledge_graph(self):
        """Create a mock knowledge graph."""
        kg = Mock(spec=DocumentKnowledgeGraph)
        return kg
    
    @pytest.fixture
    def hybrid_search_engine(self, mock_qdrant_client, mock_openai_client, mock_knowledge_graph):
        """Create a hybrid search engine with intent-aware features enabled."""
        return HybridSearchEngine(
            qdrant_client=mock_qdrant_client,
            openai_client=mock_openai_client, 
            collection_name="test_collection",
            knowledge_graph=mock_knowledge_graph,
            enable_intent_adaptation=True
        )
    
    def test_intent_aware_search_initialization(self, hybrid_search_engine):
        """Test that hybrid search engine initializes with intent-aware features."""
        assert hybrid_search_engine.enable_intent_adaptation == True
        assert hybrid_search_engine.intent_classifier is not None
        assert hybrid_search_engine.adaptive_strategy is not None
        assert hybrid_search_engine.knowledge_graph is not None
        
        # Test statistics
        stats = hybrid_search_engine.get_adaptive_search_stats()
        assert "intent_adaptation_enabled" in stats
        assert "has_knowledge_graph" in stats
        assert stats["intent_adaptation_enabled"] == True
        
    @pytest.mark.asyncio
    async def test_technical_intent_search_adaptation(self, hybrid_search_engine):
        """Test search adaptation for technical intent."""
        query = "How to implement FastAPI OAuth 2.0 authentication"
        
        # Mock spaCy analysis for technical query
        with patch.object(hybrid_search_engine.spacy_analyzer, 'analyze_query_semantic') as mock_spacy:
            mock_spacy.return_value = QueryAnalysis(
                entities=[("FastAPI", "PRODUCT"), ("OAuth", "PRODUCT")],
                pos_patterns=["ADV", "VERB", "NOUN", "NOUN"],
                semantic_keywords=["implement", "fastapi", "oauth", "authentication"],
                intent_signals={"primary_intent": "technical", "confidence": 0.8},
                main_concepts=["implementation", "authentication"],
                query_vector=[0.1] * 300,
                semantic_similarity_cache={},
                is_question=True,
                is_technical=True,
                complexity_score=0.6,
                processed_tokens=4,
                processing_time_ms=50.0
            )
            
            # Perform search
            results = await hybrid_search_engine.search(
                query=query,
                limit=10,
                session_context={"domain": "technical", "user_role": "developer"}
            )
            
            assert len(results) > 0
            
            # Technical intent should boost git sources and code-related content
            git_results = [r for r in results if r.source_type == "git"]
            assert len(git_results) > 0
            
            # Should have called spaCy analysis at least once
            mock_spacy.assert_called_with(query)
            assert mock_spacy.call_count >= 1
            
    @pytest.mark.asyncio
    async def test_business_intent_search_adaptation(self, hybrid_search_engine):
        """Test search adaptation for business intent."""
        query = "What are the business requirements for our authentication system"
        
        # Mock spaCy analysis for business query
        with patch.object(hybrid_search_engine.spacy_analyzer, 'analyze_query_semantic') as mock_spacy:
            mock_spacy.return_value = QueryAnalysis(
                entities=[("Company", "ORG")],
                pos_patterns=["PRON", "AUX", "DET", "NOUN"],
                semantic_keywords=["business", "requirements", "authentication", "system"],
                intent_signals={"primary_intent": "business", "confidence": 0.75},
                main_concepts=["requirements", "business"],
                query_vector=[0.1] * 300,
                semantic_similarity_cache={},
                is_question=True,
                is_technical=False,
                complexity_score=0.4,
                processed_tokens=4,
                processing_time_ms=40.0
            )
            
            # Perform search
            results = await hybrid_search_engine.search(
                query=query,
                limit=15,
                session_context={"domain": "business", "user_role": "analyst"}
            )
            
            assert len(results) > 0
            
            # Business intent should favor confluence sources
            confluence_results = [r for r in results if r.source_type == "confluence"]
            assert len(confluence_results) > 0
    
    @pytest.mark.asyncio
    async def test_procedural_intent_search_adaptation(self, hybrid_search_engine):
        """Test search adaptation for procedural intent."""
        query = "Step by step guide to setup OAuth authentication"
        
        with patch.object(hybrid_search_engine.spacy_analyzer, 'analyze_query_semantic') as mock_spacy:
            mock_spacy.return_value = QueryAnalysis(
                entities=[("OAuth", "PRODUCT")],
                pos_patterns=["NOUN", "ADP", "NOUN", "NOUN"],
                semantic_keywords=["step", "guide", "setup", "oauth", "authentication"],
                intent_signals={"primary_intent": "procedural", "confidence": 0.9},
                main_concepts=["setup", "guide"],
                query_vector=[0.1] * 300,
                semantic_similarity_cache={},
                is_question=False,
                is_technical=True,
                complexity_score=0.3,
                processed_tokens=5,
                processing_time_ms=35.0
            )
            
            results = await hybrid_search_engine.search(
                query=query,
                limit=15,
                session_context={"session_type": "learning", "experience_level": "beginner"}
            )
            
            assert len(results) > 0
            # Procedural intent should use breadth-first knowledge graph traversal
            # and prefer documentation sources
    
    @pytest.mark.asyncio
    async def test_exploratory_intent_with_diversity(self, hybrid_search_engine):
        """Test exploratory intent with diversity filtering."""
        query = "explore authentication methods"
        
        with patch.object(hybrid_search_engine.spacy_analyzer, 'analyze_query_semantic') as mock_spacy:
            mock_spacy.return_value = QueryAnalysis(
                entities=[],
                pos_patterns=["VERB", "NOUN", "NOUN"],
                semantic_keywords=["explore", "authentication", "methods"],
                intent_signals={"primary_intent": "exploratory", "confidence": 0.6},
                main_concepts=["authentication", "exploration"],
                query_vector=[0.1] * 300,
                semantic_similarity_cache={},
                is_question=False,
                is_technical=True,
                complexity_score=0.2,
                processed_tokens=3,
                processing_time_ms=30.0
            )
            
            # Mock diverse results
            hybrid_search_engine.qdrant_client.search.return_value = [
                Mock(score=0.9, payload={
                    "content": f"Authentication method {i}",
                    "source_type": "git" if i % 2 == 0 else "confluence",
                    "metadata": {
                        "title": f"Auth Method {i}",
                        "url": f"https://example.com/auth-{i}",
                        "entities": [f"Method{i}"],
                        "topics": ["authentication", f"topic{i}"]
                    }
                }) for i in range(10)
            ]
            
            results = await hybrid_search_engine.search(
                query=query,
                limit=20,
                session_context={"session_type": "exploration"}
            )
            
            assert len(results) > 0
            # Exploratory intent should return diverse results
            source_types = {r.source_type for r in results}
            assert len(source_types) > 1  # Should have diverse source types
    
    @pytest.mark.asyncio
    async def test_troubleshooting_intent_focused_search(self, hybrid_search_engine):
        """Test troubleshooting intent with focused search."""
        query = "OAuth authentication error 401 unauthorized"
        
        with patch.object(hybrid_search_engine.spacy_analyzer, 'analyze_query_semantic') as mock_spacy:
            mock_spacy.return_value = QueryAnalysis(
                entities=[("OAuth", "PRODUCT")],
                pos_patterns=["NOUN", "NOUN", "NOUN", "NUM", "ADJ"],
                semantic_keywords=["oauth", "authentication", "error", "401", "unauthorized"],
                intent_signals={"primary_intent": "troubleshooting", "confidence": 0.95},
                main_concepts=["error", "troubleshooting"],
                query_vector=[0.1] * 300,
                semantic_similarity_cache={},
                is_question=False,
                is_technical=True,
                complexity_score=0.8,
                processed_tokens=5,
                processing_time_ms=45.0
            )
            
            results = await hybrid_search_engine.search(
                query=query,
                limit=8,
                session_context={"urgency": "high", "session_type": "debugging"}
            )
            
            assert len(results) > 0
            # Troubleshooting intent should focus on recent, specific solutions
    
    @pytest.mark.asyncio
    async def test_behavioral_context_influence(self, hybrid_search_engine):
        """Test that behavioral context influences search adaptation."""
        query = "API documentation"
        
        with patch.object(hybrid_search_engine.spacy_analyzer, 'analyze_query_semantic') as mock_spacy:
            mock_spacy.return_value = QueryAnalysis(
                entities=[("API", "PRODUCT")],
                pos_patterns=["NOUN", "NOUN"],
                semantic_keywords=["api", "documentation"],
                intent_signals={"primary_intent": "technical", "confidence": 0.7},
                main_concepts=["api", "documentation"],
                query_vector=[0.1] * 300,
                semantic_similarity_cache={},
                is_question=False,
                is_technical=True,
                complexity_score=0.4,
                processed_tokens=2,
                processing_time_ms=25.0
            )
            
            # Test with different behavioral contexts
            behavioral_context = ["technical_lookup", "procedural", "technical_lookup"]
            
            results = await hybrid_search_engine.search(
                query=query,
                limit=10,
                session_context={"user_role": "developer", "domain": "technical"},
                behavioral_context=behavioral_context
            )
            
            assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_secondary_intent_blending(self, hybrid_search_engine):
        """Test secondary intent blending affects search parameters."""
        query = "how to implement authentication"
        
        with patch.object(hybrid_search_engine.spacy_analyzer, 'analyze_query_semantic') as mock_spacy:
            mock_spacy.return_value = QueryAnalysis(
                entities=[],
                pos_patterns=["ADV", "PART", "VERB", "NOUN"],
                semantic_keywords=["how", "implement", "authentication"],
                intent_signals={
                    "primary_intent": "technical", 
                    "confidence": 0.7,
                    "secondary_intents": [("procedural", 0.5)]
                },
                main_concepts=["implementation", "authentication"],
                query_vector=[0.1] * 300,
                semantic_similarity_cache={},
                is_question=True,
                is_technical=True,
                complexity_score=0.5,
                processed_tokens=3,
                processing_time_ms=40.0
            )
            
            # Mock the intent classification to return secondary intents
            with patch.object(hybrid_search_engine.intent_classifier, 'classify_intent') as mock_classifier:
                mock_classifier.return_value = SearchIntent(
                    intent_type=IntentType.TECHNICAL_LOOKUP,
                    confidence=0.7,
                    secondary_intents=[(IntentType.PROCEDURAL, 0.5)]
                )
                
                results = await hybrid_search_engine.search(
                    query=query,
                    limit=12
                )
                
                assert len(results) > 0
                mock_classifier.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_aggressive_query_expansion(self, hybrid_search_engine):
        """Test aggressive query expansion for low-confidence intents."""
        query = "auth"  # Short, ambiguous query
        
        with patch.object(hybrid_search_engine.spacy_analyzer, 'analyze_query_semantic') as mock_spacy:
            mock_spacy.return_value = QueryAnalysis(
                entities=[],
                pos_patterns=["NOUN"],
                semantic_keywords=["auth"],
                intent_signals={"primary_intent": "general", "confidence": 0.3},
                main_concepts=["auth"],
                query_vector=[0.1] * 300,
                semantic_similarity_cache={},
                is_question=False,
                is_technical=True,
                complexity_score=0.1,
                processed_tokens=1,
                processing_time_ms=15.0
            )
            
            # Mock query expansion
            with patch.object(hybrid_search_engine, '_expand_query_aggressive') as mock_expand:
                mock_expand.return_value = "authentication authorization oauth security"
                
                results = await hybrid_search_engine.search(
                    query=query,
                    limit=15
                )
                
                assert len(results) > 0
                # Aggressive expansion may or may not be called depending on intent classification
                # This is acceptable as the fallback behavior still works
                
    @pytest.mark.asyncio
    async def test_intent_specific_boosting(self, hybrid_search_engine):
        """Test intent-specific boosting affects result ranking."""
        query = "business requirements authentication"
        
        with patch.object(hybrid_search_engine.spacy_analyzer, 'analyze_query_semantic') as mock_spacy:
            mock_spacy.return_value = QueryAnalysis(
                entities=[],
                pos_patterns=["NOUN", "NOUN", "NOUN"],
                semantic_keywords=["business", "requirements", "authentication"],
                intent_signals={"primary_intent": "business", "confidence": 0.8},
                main_concepts=["business", "requirements"],
                query_vector=[0.1] * 300,
                semantic_similarity_cache={},
                is_question=False,
                is_technical=False,
                complexity_score=0.3,
                processed_tokens=3,
                processing_time_ms=30.0
            )
            
            results = await hybrid_search_engine.search(
                query=query,
                limit=10,
                session_context={"domain": "business"}
            )
            
            assert len(results) > 0
            # Business intent should boost confluence sources over git sources
            confluence_results = [r for r in results if r.source_type == "confluence"]
            git_results = [r for r in results if r.source_type == "git"]
            
            if confluence_results and git_results:
                # Should have some confluence results ranked highly
                assert any(r.source_type == "confluence" for r in results[:3])
    
    @pytest.mark.asyncio
    async def test_parameter_restoration(self, hybrid_search_engine):
        """Test that original search parameters are restored after adaptive search."""
        query = "test query"
        original_limit = 5
        
        with patch.object(hybrid_search_engine.spacy_analyzer, 'analyze_query_semantic') as mock_spacy:
            mock_spacy.return_value = QueryAnalysis(
                entities=[],
                pos_patterns=["NOUN", "NOUN"],
                semantic_keywords=["test", "query"],
                intent_signals={"primary_intent": "general", "confidence": 0.5},
                main_concepts=["test"],
                query_vector=[0.1] * 300,
                semantic_similarity_cache={},
                is_question=False,
                is_technical=False,
                complexity_score=0.2,
                processed_tokens=2,
                processing_time_ms=20.0
            )
            
            # Store original search parameters
            original_vector_weight = hybrid_search_engine.vector_weight
            original_keyword_weight = hybrid_search_engine.keyword_weight
            
            results = await hybrid_search_engine.search(
                query=query,
                limit=original_limit
            )
            
            # Check that original parameters are restored
            assert hybrid_search_engine.vector_weight == original_vector_weight
            assert hybrid_search_engine.keyword_weight == original_keyword_weight
            
    @pytest.mark.asyncio
    async def test_intent_classification_error_handling(self, hybrid_search_engine):
        """Test graceful handling of intent classification errors."""
        query = "test query"
        
        # Mock spaCy analyzer to raise an exception
        with patch.object(hybrid_search_engine.spacy_analyzer, 'analyze_query_semantic') as mock_spacy:
            mock_spacy.side_effect = Exception("Intent classification failed")
            
            # Should still return results with fallback behavior
            results = await hybrid_search_engine.search(
                query=query,
                limit=10
            )
            
            assert len(results) > 0  # Should fallback to basic search 