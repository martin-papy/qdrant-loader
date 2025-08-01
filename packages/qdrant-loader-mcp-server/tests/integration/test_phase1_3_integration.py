"""
Integration tests for Dynamic Faceted Search Interface

Integration tests that verify the complete faceted search workflow:
- Integration with existing hybrid search
- MCP server interface compatibility
- End-to-end faceted search scenarios
- Performance with real search results
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from qdrant_loader_mcp_server.search.components.search_result_models import create_hybrid_search_result
from qdrant_loader_mcp_server.search.hybrid_search import HybridSearchEngine
from qdrant_loader_mcp_server.search.engine import SearchEngine
from qdrant_loader_mcp_server.search.enhanced.faceted_search import (
    FacetType,
    FacetFilter,
    FacetedSearchResults,
    DynamicFacetGenerator,
    FacetedSearchEngine
)


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client for testing."""
    client = Mock()
    client.search = AsyncMock()
    return client


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    client = Mock()
    return client


@pytest.fixture
def sample_search_results():
    """Sample search results with diverse metadata for testing."""
    return [
        create_hybrid_search_result(
            score=0.95,
            text="OAuth 2.0 implementation guide with code examples",
            source_type="confluence",
            source_title="Authentication Guide",
            project_name="MyaHealth",
            has_code_blocks=True,
            has_links=True,
            entities=[
                {"text": "OAuth", "label": "PRODUCT"},
                {"text": "JWT", "label": "PRODUCT"}
            ],
            topics=[
                {"text": "authentication", "score": 0.9},
                {"text": "security", "score": 0.8}
            ],
            depth=2,
            estimated_read_time=8,
            word_count=1200
        ),
        create_hybrid_search_result(
            score=0.89,
            text="Database schema design for user management",
            source_type="localfile",
            source_title="Database Schema",
            project_name="MyaHealth",
            has_tables=True,
            has_images=True,
            entities=[
                {"text": "PostgreSQL", "label": "PRODUCT"},
                {"text": "User", "label": "PERSON"}
            ],
            topics=[
                {"text": "database", "score": 0.9},
                {"text": "schema", "score": 0.7}
            ],
            depth=1,
            estimated_read_time=5,
            word_count=800
        ),
        create_hybrid_search_result(
            score=0.83,
            text="Frontend React components for authentication UI",
            source_type="git",
            source_title="Auth Components",
            project_name="ProposAI",
            has_code_blocks=True,
            has_images=True,
            entities=[
                {"text": "React", "label": "PRODUCT"},
                {"text": "TypeScript", "label": "LANGUAGE"}
            ],
            topics=[
                {"text": "frontend", "score": 0.8},
                {"text": "components", "score": 0.7}
            ],
            depth=3,
            estimated_read_time=12,
            word_count=2100
        ),
        create_hybrid_search_result(
            score=0.78,
            text="API documentation for user authentication endpoints",
            source_type="confluence",
            source_title="API Documentation",
            project_name="ProposAI",
            has_tables=True,
            has_links=True,
            entities=[
                {"text": "REST API", "label": "PRODUCT"},
                {"text": "JSON", "label": "PRODUCT"}
            ],
            topics=[
                {"text": "api", "score": 0.9},
                {"text": "documentation", "score": 0.6}
            ],
            depth=2,
            estimated_read_time=6,
            word_count=900
        ),
        create_hybrid_search_result(
            score=0.72,
            text="Security best practices for authentication systems",
            source_type="localfile",
            source_title="Security Guidelines",
            project_name="MyaHealth",
            has_links=True,
            entities=[
                {"text": "HTTPS", "label": "PRODUCT"},
                {"text": "OWASP", "label": "ORG"}
            ],
            topics=[
                {"text": "security", "score": 0.9},
                {"text": "guidelines", "score": 0.7}
            ],
            depth=1,
            estimated_read_time=4,
            word_count=600
        )
    ]


class TestPhase13FacetedSearchIntegration:
    """Integration tests for Faceted Search."""
    
    def test_faceted_search_engine_initialization(self, mock_qdrant_client, mock_openai_client):
        """Test that faceted search engine is properly initialized in HybridSearchEngine."""
        engine = HybridSearchEngine(
            qdrant_client=mock_qdrant_client,
            openai_client=mock_openai_client,
            collection_name="test",
            enable_intent_adaptation=False  # Disable for simpler testing
        )
        
        # Should have faceted search engine initialized
        assert hasattr(engine, 'faceted_search_engine')
        assert isinstance(engine.faceted_search_engine, FacetedSearchEngine)
        assert isinstance(engine.faceted_search_engine.facet_generator, DynamicFacetGenerator)
    
    @pytest.mark.asyncio
    async def test_hybrid_search_with_facets(self, mock_qdrant_client, mock_openai_client, sample_search_results):
        """Test the integrated search_with_facets method."""
        # Mock the regular search to return our sample results
        engine = HybridSearchEngine(
            qdrant_client=mock_qdrant_client,
            openai_client=mock_openai_client,
            collection_name="test",
            enable_intent_adaptation=False
        )
        
        # Mock the search method to return sample results
        engine.search = AsyncMock(return_value=sample_search_results)
        
        # Test faceted search
        faceted_results = await engine.search_with_facets(
            query="authentication system",
            limit=10,
            generate_facets=True
        )
        
        # Verify the structure
        assert isinstance(faceted_results, FacetedSearchResults)
        assert faceted_results.total_results == 5
        assert faceted_results.filtered_count == 5  # No filters applied
        assert len(faceted_results.results) == 5
        assert len(faceted_results.facets) > 0
        
        # Verify specific facets are generated
        facet_types = [f.facet_type for f in faceted_results.facets]
        assert FacetType.CONTENT_TYPE in facet_types
        assert FacetType.PROJECT in facet_types
        assert FacetType.HAS_FEATURES in facet_types
        
        # Verify content type facet values
        content_facet = next(f for f in faceted_results.facets if f.facet_type == FacetType.CONTENT_TYPE)
        content_values = [v.value for v in content_facet.values]
        assert "confluence" in content_values
        assert "localfile" in content_values
        assert "git" in content_values
        
        # Verify project facet values
        project_facet = next(f for f in faceted_results.facets if f.facet_type == FacetType.PROJECT)
        project_values = [v.value for v in project_facet.values]
        assert "MyaHealth" in project_values
        assert "ProposAI" in project_values
    
    @pytest.mark.asyncio
    async def test_faceted_search_with_filters(self, mock_qdrant_client, mock_openai_client, sample_search_results):
        """Test faceted search with applied filters."""
        engine = HybridSearchEngine(
            qdrant_client=mock_qdrant_client,
            openai_client=mock_openai_client,
            collection_name="test",
            enable_intent_adaptation=False
        )
        
        engine.search = AsyncMock(return_value=sample_search_results)
        
        # Apply filter for MyaHealth project only
        project_filter = FacetFilter(
            facet_type=FacetType.PROJECT,
            values=["MyaHealth"],
            operator="OR"
        )
        
        faceted_results = await engine.search_with_facets(
            query="authentication system",
            limit=10,
            facet_filters=[project_filter],
            generate_facets=True
        )
        
        # Should filter to only MyaHealth results (3 out of 5)
        assert faceted_results.total_results == 5  # Original count
        assert faceted_results.filtered_count == 3  # After filtering
        assert len(faceted_results.results) == 3
        assert all(r.project_name == "MyaHealth" for r in faceted_results.results)
        assert len(faceted_results.applied_filters) == 1
    
    @pytest.mark.asyncio
    async def test_multiple_facet_filters(self, mock_qdrant_client, mock_openai_client, sample_search_results):
        """Test multiple facet filters applied together."""
        engine = HybridSearchEngine(
            qdrant_client=mock_qdrant_client,
            openai_client=mock_openai_client,
            collection_name="test",
            enable_intent_adaptation=False
        )
        
        engine.search = AsyncMock(return_value=sample_search_results)
        
        # Apply multiple filters: MyaHealth project AND has code blocks
        filters = [
            FacetFilter(facet_type=FacetType.PROJECT, values=["MyaHealth"], operator="OR"),
            FacetFilter(facet_type=FacetType.HAS_FEATURES, values=["code"], operator="OR")
        ]
        
        faceted_results = await engine.search_with_facets(
            query="authentication system",
            limit=10,
            facet_filters=filters,
            generate_facets=True
        )
        
        # Should filter to only MyaHealth results with code blocks (1 result)
        assert faceted_results.filtered_count == 1
        assert faceted_results.results[0].project_name == "MyaHealth"
        assert faceted_results.results[0].has_code_blocks is True
    
    def test_facet_refinement_suggestions(self, mock_qdrant_client, mock_openai_client, sample_search_results):
        """Test facet refinement suggestions."""
        engine = HybridSearchEngine(
            qdrant_client=mock_qdrant_client,
            openai_client=mock_openai_client,
            collection_name="test",
            enable_intent_adaptation=False
        )
        
        # Test refinement suggestions
        suggestions = engine.suggest_facet_refinements(
            current_results=sample_search_results,
            current_filters=[]
        )
        
        assert isinstance(suggestions, list)
        if suggestions:
            # Should suggest useful filters
            suggestion = suggestions[0]
            assert "facet_type" in suggestion
            assert "reduction_percent" in suggestion
            assert "filtered_count" in suggestion
            assert suggestion["reduction_percent"] > 0
    
    def test_generate_facets_from_results(self, mock_qdrant_client, mock_openai_client, sample_search_results):
        """Test generating facets from search results."""
        engine = HybridSearchEngine(
            qdrant_client=mock_qdrant_client,
            openai_client=mock_openai_client,
            collection_name="test",
            enable_intent_adaptation=False
        )
        
        facets = engine.generate_facets(sample_search_results)
        
        assert len(facets) > 0
        
        # Verify content type facet
        content_facet = next((f for f in facets if f.facet_type == FacetType.CONTENT_TYPE), None)
        assert content_facet is not None
        assert content_facet.display_name == "Content Type"
        
        # Verify facet values and counts
        confluence_value = next((v for v in content_facet.values if v.value == "confluence"), None)
        assert confluence_value is not None
        assert confluence_value.count == 2  # 2 confluence results in sample data
        
        # Verify features facet
        features_facet = next((f for f in facets if f.facet_type == FacetType.HAS_FEATURES), None)
        assert features_facet is not None
        
        code_value = next((v for v in features_facet.values if v.value == "code"), None)
        assert code_value is not None
        assert code_value.count == 2  # 2 results with code blocks


class TestSearchEngineMCPIntegration:
    """Integration tests for MCP server interface."""
    
    @pytest.mark.asyncio
    async def test_search_engine_faceted_search_method(self, sample_search_results):
        """Test SearchEngine.search_with_facets method for MCP interface."""
        search_engine = SearchEngine()
        
        # Mock the hybrid search
        mock_hybrid_search = Mock()
        mock_hybrid_search.search_with_facets = AsyncMock()
        
        # Create mock faceted results
        mock_faceted_results = FacetedSearchResults(
            results=sample_search_results,
            facets=[
                Mock(
                    facet_type=FacetType.CONTENT_TYPE,
                    name="content_type",
                    display_name="Content Type",
                    description="Type of content source",
                    get_top_values=Mock(return_value=[
                        Mock(value="confluence", count=2, display_name="Confluence", description=None),
                        Mock(value="localfile", count=2, display_name="Local File", description=None),
                        Mock(value="git", count=1, display_name="Git", description=None)
                    ])
                )
            ],
            applied_filters=[],
            total_results=5,
            filtered_count=5,
            generation_time_ms=15.2
        )
        
        mock_hybrid_search.search_with_facets.return_value = mock_faceted_results
        search_engine.hybrid_search = mock_hybrid_search
        
        # Test the MCP interface method
        result = await search_engine.search_with_facets(
            query="authentication system",
            limit=5,
            facet_filters=None
        )
        
        # Verify MCP-compatible response format
        assert isinstance(result, dict)
        assert "results" in result
        assert "facets" in result
        assert "total_results" in result
        assert "filtered_count" in result
        assert "applied_filters" in result
        assert "generation_time_ms" in result
        
        # Verify facets structure
        assert len(result["facets"]) == 1
        facet = result["facets"][0]
        assert facet["type"] == "content_type"
        assert facet["display_name"] == "Content Type"
        assert "values" in facet
        assert len(facet["values"]) == 3
        
        # Verify facet values structure
        facet_value = facet["values"][0]
        assert "value" in facet_value
        assert "count" in facet_value
        assert "display_name" in facet_value
    
    @pytest.mark.asyncio
    async def test_search_engine_facet_suggestions(self, sample_search_results):
        """Test SearchEngine.get_facet_suggestions method."""
        search_engine = SearchEngine()
        
        # Mock the hybrid search
        mock_hybrid_search = Mock()
        mock_hybrid_search.search = AsyncMock(return_value=sample_search_results)
        mock_hybrid_search.suggest_facet_refinements = Mock(return_value=[
            {
                "facet_type": "project",
                "facet_display_name": "Project",
                "value": "MyaHealth",
                "display_name": "MyaHealth",
                "current_count": 5,
                "filtered_count": 3,
                "reduction_percent": 40
            }
        ])
        search_engine.hybrid_search = mock_hybrid_search
        
        suggestions = await search_engine.get_facet_suggestions(
            query="authentication system",
            current_filters=[],
            limit=20
        )
        
        assert isinstance(suggestions, list)
        assert len(suggestions) == 1
        
        suggestion = suggestions[0]
        assert suggestion["facet_type"] == "project"
        assert suggestion["reduction_percent"] == 40
        assert suggestion["filtered_count"] == 3
    
    @pytest.mark.asyncio
    async def test_search_engine_with_facet_filters(self, sample_search_results):
        """Test SearchEngine with facet filters in MCP format."""
        search_engine = SearchEngine()
        
        # Mock the hybrid search
        mock_hybrid_search = Mock()
        mock_hybrid_search.search_with_facets = AsyncMock()
        
        # Create filtered results mock
        filtered_results = [r for r in sample_search_results if r.project_name == "MyaHealth"]
        mock_faceted_results = FacetedSearchResults(
            results=filtered_results,
            facets=[],
            applied_filters=[Mock(facet_type=FacetType.PROJECT, values=["MyaHealth"], operator="OR")],
            total_results=5,
            filtered_count=3,
            generation_time_ms=18.5
        )
        
        mock_hybrid_search.search_with_facets.return_value = mock_faceted_results
        search_engine.hybrid_search = mock_hybrid_search
        
        # Test with MCP-format facet filters
        facet_filters = [
            {
                "facet_type": "project",
                "values": ["MyaHealth"],
                "operator": "OR"
            }
        ]
        
        result = await search_engine.search_with_facets(
            query="authentication system",
            limit=5,
            facet_filters=facet_filters
        )
        
        # Verify the method was called with proper filter objects
        mock_hybrid_search.search_with_facets.assert_called_once()
        call_args = mock_hybrid_search.search_with_facets.call_args
        filter_objects = call_args.kwargs["facet_filters"]
        
        assert len(filter_objects) == 1
        assert isinstance(filter_objects[0], FacetFilter)
        assert filter_objects[0].facet_type == FacetType.PROJECT
        assert filter_objects[0].values == ["MyaHealth"]
        
        # Verify response
        assert result["total_results"] == 5
        assert result["filtered_count"] == 3
        assert len(result["applied_filters"]) == 1


class TestPhase13PerformanceIntegration:
    """Performance tests for integration."""
    
    def test_facet_generation_performance(self):
        """Test facet generation performance with larger dataset."""
        # Create 200 varied search results
        large_results = []
        for i in range(200):
            result = create_hybrid_search_result(
                score=0.8 - (i * 0.001),  # Decreasing scores
                text=f"Test document {i} with authentication content",
                source_type=["confluence", "localfile", "git"][i % 3],
                source_title=f"Document {i}",
                project_name=["MyaHealth", "ProposAI", "DevProject"][i % 3],
                has_code_blocks=i % 4 == 0,
                has_tables=i % 5 == 0,
                has_images=i % 6 == 0,
                has_links=i % 3 == 0,
                entities=[
                    {"text": f"Entity{i%20}", "label": ["PRODUCT", "ORG", "PERSON"][i % 3]}
                ],
                topics=[
                    {"text": f"topic{i%15}", "score": 0.8}
                ],
                depth=i % 5 + 1,
                estimated_read_time=i % 15 + 1,
                word_count=(i % 10 + 1) * 100
            )
            large_results.append(result)
        
        faceted_engine = FacetedSearchEngine()
        
        start_time = datetime.now()
        faceted_results = faceted_engine.generate_faceted_results(large_results)
        end_time = datetime.now()
        
        generation_time_ms = (end_time - start_time).total_seconds() * 1000
        
        # Should generate facets in reasonable time (< 500ms for 200 results)
        assert generation_time_ms < 500
        assert faceted_results.total_results == 200
        assert len(faceted_results.facets) > 0
        
        # Verify facet counts are correct
        content_facet = next(f for f in faceted_results.facets if f.facet_type == FacetType.CONTENT_TYPE)
        total_facet_counts = sum(v.count for v in content_facet.values)
        assert total_facet_counts == 200  # All results accounted for
    
    def test_multiple_filter_performance(self):
        """Test performance of applying multiple filters."""
        # Create test dataset
        large_results = []
        for i in range(500):
            result = create_hybrid_search_result(
                score=0.8,
                text=f"Content {i}",
                source_type=["confluence", "localfile"][i % 2],
                source_title=f"Doc {i}",
                project_name=["MyaHealth", "ProposAI"][i % 2],
                has_code_blocks=i % 3 == 0,
                has_tables=i % 4 == 0
            )
            large_results.append(result)
        
        faceted_engine = FacetedSearchEngine()
        
        # Apply multiple filters
        filters = [
            FacetFilter(facet_type=FacetType.CONTENT_TYPE, values=["confluence"], operator="OR"),
            FacetFilter(facet_type=FacetType.PROJECT, values=["MyaHealth"], operator="OR"),
            FacetFilter(facet_type=FacetType.HAS_FEATURES, values=["code"], operator="OR")
        ]
        
        start_time = datetime.now()
        filtered_results = faceted_engine.apply_facet_filters(large_results, filters)
        end_time = datetime.now()
        
        filter_time_ms = (end_time - start_time).total_seconds() * 1000
        
        # Should filter in reasonable time (< 100ms for 500 results)
        assert filter_time_ms < 100
        
        # Verify filtering correctness
        for result in filtered_results:
            assert result.source_type == "confluence"
            assert result.project_name == "MyaHealth"
            assert result.has_code_blocks is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 