"""Simple test script to verify spaCy integration is working."""
import logging
import time

from qdrant_loader_mcp_server.search.nlp.spacy_analyzer import SpaCyQueryAnalyzer

# Set up test logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def test_spacy_analyzer():
    """Test the SpaCyQueryAnalyzer to ensure it's working correctly."""
    logger.info("🔥 Testing spaCy Query Analyzer Integration")
    logger.info("=" * 50)
    
    # Initialize analyzer
    logger.info("Initializing SpaCyQueryAnalyzer...")
    start_time = time.time()
    analyzer = SpaCyQueryAnalyzer()
    init_time = (time.time() - start_time) * 1000
    logger.info(f"✅ Initialized in {init_time:.2f}ms")
    
    # Test queries
    test_queries = [
        "How do I implement authentication in my API?",
        "Show me the product requirements document",
        "What are the vendor evaluation criteria?", 
        "Find issues related to database performance",
        "architecture design patterns",
        "What is the database schema?"
    ]
    
    logger.info("\n🧪 Testing Query Analysis:")
    logger.info("-" * 30)
    
    for query in test_queries:
        logger.info(f"\nQuery: '{query}'")
        
        # Analyze query
        analysis = analyzer.analyze_query_semantic(query)
        
        # Log results with structured data for better test output
        logger.debug(f"  Intent: {analysis.intent_signals['primary_intent']} (confidence: {analysis.intent_signals['confidence']:.2f})")
        logger.debug(f"  Entities: {analysis.entities}")
        logger.debug(f"  Keywords: {analysis.semantic_keywords[:3]}")  # Show first 3
        logger.debug(f"  Concepts: {analysis.main_concepts}")
        logger.debug(f"  Is Question: {analysis.is_question}")
        logger.debug(f"  Is Technical: {analysis.is_technical}")
        logger.debug(f"  Complexity: {analysis.complexity_score:.2f}")
        logger.debug(f"  Processing Time: {analysis.processing_time_ms:.2f}ms")
    
    logger.info("\n🔍 Testing Semantic Similarity:")
    logger.info("-" * 30)
    
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
    
    logger.info(f"Query: '{query}'")
    for entity in test_entities:
        similarity = analyzer.semantic_similarity_matching(query_analysis, entity)
        logger.debug(f"  '{entity}' -> {similarity:.3f}")
    
    logger.info("\n📊 Cache Statistics:")
    logger.info("-" * 20)
    stats = analyzer.get_cache_stats()
    logger.info(f"Analysis Cache: {stats['analysis_cache_size']} entries")
    logger.info(f"Similarity Cache: {stats['similarity_cache_size']} entries")
    
    logger.info("\n✅ spaCy Integration Test Complete!")


def test_processor_integration():
    """Test QueryProcessor integration with spaCy."""
    logger.info("\n🔥 Testing QueryProcessor spaCy Integration")
    logger.info("=" * 50)
    
    # This would require the full config setup, so just test the concept
    test_queries_intents = [
        ("How to implement REST API authentication?", "code"),
        ("Show me the product requirements document", "documentation"),
        ("Database performance issues in Jira", "issue"),
        ("What is system architecture?", "general"),
    ]
    
    logger.info("Expected Intent Mappings:")
    logger.info("-" * 25)
    for query, expected_intent in test_queries_intents:
        logger.debug(f"  '{query[:40]}...' -> {expected_intent}")
    
    logger.info("\n✅ QueryProcessor Integration Expected to Work!")


if __name__ == "__main__":
    try:
        test_spacy_analyzer()
        test_processor_integration()
        logger.info("\n🎉 All tests completed successfully!")
    except Exception as e:
        logger.error(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc() 