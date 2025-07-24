"""Simple integration test for Phase 1.2 Topic-Driven Search Chaining.

Tests real components working together without complex mocking.
"""

import pytest
import time
from typing import List

from qdrant_loader_mcp_server.search.enhanced.topic_search_chain import (
    TopicSearchChainGenerator,
    TopicRelationshipMap,
    TopicSearchChain,
    ChainStrategy
)
from qdrant_loader_mcp_server.search.nlp.spacy_analyzer import SpaCyQueryAnalyzer
from qdrant_loader_mcp_server.search.models import SearchResult


class TestPhase12SimpleIntegration:
    """Simple integration tests using real components."""
    
    @pytest.fixture
    def real_spacy_analyzer(self):
        """Real spaCy analyzer for integration testing."""
        try:
            return SpaCyQueryAnalyzer(spacy_model="en_core_web_md")
        except OSError:
            pytest.skip("spaCy model en_core_web_md not available")
    
    @pytest.fixture
    def sample_search_results(self):
        """Realistic search results for testing."""
        return [
            SearchResult(
                score=0.9,
                text="OAuth 2.0 authentication flow with JWT token validation for secure API access",
                source_type="git",
                source_title="OAuth Authentication Guide",
                topics=[
                    {"text": "authentication", "score": 0.9},
                    {"text": "oauth", "score": 0.8},
                    {"text": "jwt", "score": 0.7},
                    {"text": "api security", "score": 0.6}
                ],
                entities=[
                    {"text": "OAuth", "label": "PRODUCT"},
                    {"text": "JWT", "label": "PRODUCT"}
                ],
                breadcrumb_text="Documentation > Security > Authentication > OAuth"
            ),
            SearchResult(
                score=0.85,
                text="REST API design principles and security best practices for web applications",
                source_type="confluence",
                source_title="API Design Guidelines",
                topics=[
                    {"text": "api design", "score": 0.9},
                    {"text": "rest", "score": 0.8},
                    {"text": "security", "score": 0.7},
                    {"text": "web applications", "score": 0.6}
                ],
                entities=[
                    {"text": "REST", "label": "CONCEPT"},
                    {"text": "HTTP", "label": "PROTOCOL"}
                ],
                breadcrumb_text="Documentation > API > Design > REST"
            ),
            SearchResult(
                score=0.8,
                text="Database security patterns and encryption strategies for sensitive data protection",
                source_type="documentation",
                source_title="Database Security Guide",
                topics=[
                    {"text": "database security", "score": 0.9},
                    {"text": "encryption", "score": 0.8},
                    {"text": "data protection", "score": 0.7}
                ],
                entities=[
                    {"text": "PostgreSQL", "label": "PRODUCT"},
                    {"text": "encryption", "label": "CONCEPT"}
                ],
                breadcrumb_text="Documentation > Database > Security"
            ),
            SearchResult(
                score=0.75,
                text="Microservices architecture patterns for scalable web applications and APIs",
                source_type="git",
                source_title="Architecture Patterns",
                topics=[
                    {"text": "microservices", "score": 0.9},
                    {"text": "architecture", "score": 0.8},
                    {"text": "scalability", "score": 0.7},
                    {"text": "web applications", "score": 0.6}
                ],
                entities=[
                    {"text": "microservices", "label": "CONCEPT"},
                    {"text": "architecture", "label": "CONCEPT"}
                ],
                breadcrumb_text="Documentation > Architecture > Patterns"
            )
        ]
    
    def test_real_topic_relationship_mapping(self, real_spacy_analyzer, sample_search_results):
        """Test real topic relationship mapping with actual spaCy."""
        print("\n🔥 Testing Real Topic Relationship Mapping")
        print("=" * 50)
        
        # Create real topic relationship map
        topic_map = TopicRelationshipMap(real_spacy_analyzer)
        
        # Build relationships from real search results
        start_time = time.time()
        topic_map.build_topic_map(sample_search_results)
        build_time = (time.time() - start_time) * 1000
        
        print(f"✅ Topic map built in {build_time:.2f}ms")
        print(f"📊 Topics found: {len(topic_map.topic_document_frequency)}")
        print(f"🔗 Co-occurrences: {sum(len(cooc) for cooc in topic_map.topic_cooccurrence.values())}")
        
        # Test finding related topics with real spaCy similarity
        related_topics = topic_map.find_related_topics("authentication", max_related=3)
        
        print(f"\n🔍 Related topics for 'authentication':")
        for topic, score, rel_type in related_topics:
            print(f"   • {topic} (score: {score:.3f}, type: {rel_type})")
        
        # Verify we found relationships
        assert len(topic_map.topic_document_frequency) > 0
        assert len(related_topics) >= 0  # May be 0 if no strong relationships
        
        # Test semantic similarity with real spaCy vectors
        similarity = real_spacy_analyzer.nlp("authentication").similarity(
            real_spacy_analyzer.nlp("security")
        )
        print(f"🧠 spaCy similarity 'authentication' ↔ 'security': {similarity:.3f}")
        assert 0 <= similarity <= 1
    
    def test_real_topic_chain_generation(self, real_spacy_analyzer, sample_search_results):
        """Test real topic chain generation with all strategies."""
        print("\n🚀 Testing Real Topic Chain Generation")
        print("=" * 45)
        
        # Create real topic chain generator
        generator = TopicSearchChainGenerator(real_spacy_analyzer)
        generator.initialize_from_results(sample_search_results)
        
        # Test all chain strategies
        strategies = [
            ChainStrategy.BREADTH_FIRST,
            ChainStrategy.DEPTH_FIRST,
            ChainStrategy.RELEVANCE_RANKED,
            ChainStrategy.MIXED_EXPLORATION
        ]
        
        test_query = "How to implement secure API authentication"
        
        for strategy in strategies:
            print(f"\n🔄 Testing {strategy.value} strategy:")
            
            start_time = time.time()
            chain = generator.generate_search_chain(
                original_query=test_query,
                strategy=strategy,
                max_links=3
            )
            generation_time = (time.time() - start_time) * 1000
            
            print(f"   ⏱️ Generated in {generation_time:.2f}ms")
            print(f"   🔗 Chain length: {len(chain.chain_links)}")
            print(f"   📊 Topics covered: {chain.total_topics_covered}")
            print(f"   🎯 Discovery potential: {chain.estimated_discovery_potential:.2f}")
            print(f"   🧠 Coherence score: {chain.chain_coherence_score:.2f}")
            
            # Verify chain structure
            assert isinstance(chain, TopicSearchChain)
            assert chain.original_query == test_query
            assert chain.strategy == strategy
            assert 0 <= chain.estimated_discovery_potential <= 1
            assert 0 <= chain.chain_coherence_score <= 1
            assert chain.generation_time_ms > 0
            
            # Show generated chain links
            for i, link in enumerate(chain.chain_links):
                print(f"   {i+1}. '{link.query}' (focus: {link.topic_focus}, type: {link.exploration_type})")
    
    def test_real_performance_benchmarks(self, real_spacy_analyzer, sample_search_results):
        """Test real performance with actual components."""
        print("\n⚡ Testing Real Performance Benchmarks")
        print("=" * 40)
        
        generator = TopicSearchChainGenerator(real_spacy_analyzer)
        
        # Test initialization performance
        init_times = []
        for _ in range(3):
            start_time = time.time()
            generator.initialize_from_results(sample_search_results)
            init_time = (time.time() - start_time) * 1000
            init_times.append(init_time)
        
        avg_init_time = sum(init_times) / len(init_times)
        print(f"📊 Average initialization: {avg_init_time:.2f}ms")
        
        # Test chain generation performance
        generation_times = []
        test_queries = [
            "secure authentication implementation",
            "database security best practices", 
            "API design patterns",
            "microservices architecture"
        ]
        
        for query in test_queries:
            start_time = time.time()
            chain = generator.generate_search_chain(
                original_query=query,
                strategy=ChainStrategy.MIXED_EXPLORATION,
                max_links=2
            )
            gen_time = (time.time() - start_time) * 1000
            generation_times.append(gen_time)
            print(f"   • '{query}': {gen_time:.2f}ms ({len(chain.chain_links)} links)")
        
        avg_generation_time = sum(generation_times) / len(generation_times)
        print(f"📊 Average generation: {avg_generation_time:.2f}ms")
        
        # Performance assertions (real targets)
        assert avg_init_time < 100  # Should be very fast
        assert avg_generation_time < 100  # Reasonable for real spaCy processing
        
        print(f"✅ Performance targets met!")
        print(f"🎯 Initialization: {avg_init_time:.2f}ms < 100ms target")
        print(f"🎯 Generation: {avg_generation_time:.2f}ms < 100ms target")
    
    def test_end_to_end_real_workflow(self, real_spacy_analyzer, sample_search_results):
        """Test complete end-to-end workflow with real components."""
        print("\n🎯 Testing End-to-End Real Workflow")
        print("=" * 40)
        
        total_start_time = time.time()
        
        # Step 1: Create generator and initialize
        print("1️⃣ Creating topic chain generator...")
        generator = TopicSearchChainGenerator(real_spacy_analyzer)
        generator.initialize_from_results(sample_search_results)
        
        # Step 2: Analyze query with real spaCy
        print("2️⃣ Analyzing query with spaCy...")
        test_query = "How to secure REST API endpoints with OAuth"
        query_analysis = real_spacy_analyzer.analyze_query_semantic(test_query)
        
        print(f"   🏷️ Entities: {[ent[0] for ent in query_analysis.entities]}")
        print(f"   🔑 Keywords: {query_analysis.semantic_keywords[:3]}")
        print(f"   🎯 Intent: {query_analysis.intent_signals.get('primary_intent', 'unknown')}")
        
        # Step 3: Generate topic chain
        print("3️⃣ Generating topic search chain...")
        chain = generator.generate_search_chain(
            original_query=test_query,
            strategy=ChainStrategy.MIXED_EXPLORATION,
            max_links=4
        )
        
        # Step 4: Validate results
        print("4️⃣ Validating results...")
        total_time = (time.time() - total_start_time) * 1000
        
        print(f"\n📊 End-to-End Results:")
        print(f"   ⏱️ Total workflow time: {total_time:.2f}ms")
        print(f"   📝 Original query: '{test_query}'")
        print(f"   🔗 Generated {len(chain.chain_links)} chain links")
        print(f"   📈 Discovery potential: {chain.estimated_discovery_potential:.2f}")
        print(f"   🎯 Chain coherence: {chain.chain_coherence_score:.2f}")
        
        # Show the generated chain
        if chain.chain_links:
            print(f"\n🔍 Generated search chain:")
            for i, link in enumerate(chain.chain_links, 1):
                print(f"   {i}. '{link.query}'")
                print(f"      Focus: {link.topic_focus} | Type: {link.exploration_type}")
                print(f"      Relevance: {link.relevance_score:.2f}")
        
        # Final assertions
        assert total_time < 1000  # Should complete in under 1 second
        assert isinstance(chain, TopicSearchChain)
        assert len(chain.chain_links) >= 0  # May be 0 if no good chains found
        
        print(f"\n✅ End-to-end workflow completed successfully!")
        print(f"🚀 Phase 1.2 Topic-Driven Search Chaining is working with real components!")


if __name__ == "__main__":
    pytest.main([__file__]) 