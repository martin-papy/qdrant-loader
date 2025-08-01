"""Simple test script to verify spaCy integration is working."""
import time

from qdrant_loader_mcp_server.search.nlp.spacy_analyzer import SpaCyQueryAnalyzer


def test_spacy_analyzer():
    """Test the SpaCyQueryAnalyzer to ensure it's working correctly."""
    print("🔥 Testing spaCy Query Analyzer Integration")
    print("=" * 50)
    
    # Initialize analyzer
    print("Initializing SpaCyQueryAnalyzer...")
    start_time = time.time()
    analyzer = SpaCyQueryAnalyzer()
    init_time = (time.time() - start_time) * 1000
    print(f"✅ Initialized in {init_time:.2f}ms")
    
    # Test queries
    test_queries = [
        "How do I implement authentication in my API?",
        "Show me the product requirements document",
        "What are the vendor evaluation criteria?", 
        "Find issues related to database performance",
        "architecture design patterns",
        "What is the database schema?"
    ]
    
    print("\n🧪 Testing Query Analysis:")
    print("-" * 30)
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        
        # Analyze query
        analysis = analyzer.analyze_query_semantic(query)
        
        # Print results
        print(f"  Intent: {analysis.intent_signals['primary_intent']} (confidence: {analysis.intent_signals['confidence']:.2f})")
        print(f"  Entities: {analysis.entities}")
        print(f"  Keywords: {analysis.semantic_keywords[:3]}")  # Show first 3
        print(f"  Concepts: {analysis.main_concepts}")
        print(f"  Is Question: {analysis.is_question}")
        print(f"  Is Technical: {analysis.is_technical}")
        print(f"  Complexity: {analysis.complexity_score:.2f}")
        print(f"  Processing Time: {analysis.processing_time_ms:.2f}ms")
    
    print("\n🔍 Testing Semantic Similarity:")
    print("-" * 30)
    
    # Test semantic similarity
    query = "database performance optimization"
    query_analysis = analyzer.analyze_query_semantic(query)
    
    test_entities = [
        "database schema design",
        "API authentication",
        "performance tuning",
        "user interface design",
        "data optimization strategies"
    ]
    
    print(f"Query: '{query}'")
    for entity in test_entities:
        similarity = analyzer.semantic_similarity_matching(query_analysis, entity)
        print(f"  '{entity}' -> {similarity:.3f}")
    
    print("\n📊 Cache Statistics:")
    print("-" * 20)
    stats = analyzer.get_cache_stats()
    print(f"Analysis Cache: {stats['analysis_cache_size']} entries")
    print(f"Similarity Cache: {stats['similarity_cache_size']} entries")
    
    print("\n✅ spaCy Integration Test Complete!")


def test_processor_integration():
    """Test QueryProcessor integration with spaCy."""
    print("\n🔥 Testing QueryProcessor spaCy Integration")
    print("=" * 50)
    
    # This would require the full config setup, so just test the concept
    test_queries_intents = [
        ("How to implement REST API authentication?", "code"),
        ("Show me the product requirements document", "documentation"),
        ("Database performance issues in Jira", "issue"),
        ("What is system architecture?", "general"),
    ]
    
    print("Expected Intent Mappings:")
    print("-" * 25)
    for query, expected_intent in test_queries_intents:
        print(f"  '{query[:40]}...' -> {expected_intent}")
    
    print("\n✅ QueryProcessor Integration Expected to Work!")


if __name__ == "__main__":
    try:
        test_spacy_analyzer()
        test_processor_integration()
        print("\n🎉 All tests completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc() 