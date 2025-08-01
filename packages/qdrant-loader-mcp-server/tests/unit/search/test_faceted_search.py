"""
Unit tests for Dynamic Faceted Search Interface

Tests for faceted search functionality including:
- Dynamic facet generation from metadata
- Facet filtering and combination logic
- Facet suggestions and refinements
- Performance and error handling
"""

import pytest
from datetime import datetime

from qdrant_loader_mcp_server.search.components.search_result_models import HybridSearchResult, create_hybrid_search_result
from qdrant_loader_mcp_server.search.enhanced.faceted_search import (
    FacetType,
    FacetFilter,
    FacetedSearchResults,
    DynamicFacetGenerator,
    FacetedSearchEngine
)


class TestDynamicFacetGenerator:
    """Test suite for DynamicFacetGenerator class."""
    
    def test_facet_generator_initialization(self):
        """Test facet generator initializes correctly."""
        generator = DynamicFacetGenerator()
        
        assert generator is not None
        assert len(generator.facet_config) > 0
        assert FacetType.CONTENT_TYPE in generator.facet_config
        assert FacetType.HAS_FEATURES in generator.facet_config
    
    def test_generate_facets_empty_results(self):
        """Test facet generation with empty results."""
        generator = DynamicFacetGenerator()
        facets = generator.generate_facets([])
        
        assert facets == []
    
    def test_generate_content_type_facets(self):
        """Test content type facet generation."""
        generator = DynamicFacetGenerator()
        
        # Create test results with different content types
        results = [
            self._create_search_result(source_type="confluence"),
            self._create_search_result(source_type="confluence"),
            self._create_search_result(source_type="localfile"),
            self._create_search_result(source_type="git"),
        ]
        
        facets = generator.generate_facets(results)
        content_facet = next((f for f in facets if f.facet_type == FacetType.CONTENT_TYPE), None)
        
        assert content_facet is not None
        assert len(content_facet.values) == 3
        assert any(v.value == "confluence" and v.count == 2 for v in content_facet.values)
        assert any(v.value == "localfile" and v.count == 1 for v in content_facet.values)
        assert any(v.value == "git" and v.count == 1 for v in content_facet.values)
    
    def test_generate_features_facets(self):
        """Test content features facet generation."""
        generator = DynamicFacetGenerator()
        
        results = [
            self._create_search_result(has_code_blocks=True, has_tables=True),
            self._create_search_result(has_code_blocks=True),
            self._create_search_result(has_images=True, has_links=True),
            self._create_search_result(has_tables=True),
        ]
        
        facets = generator.generate_facets(results)
        features_facet = next((f for f in facets if f.facet_type == FacetType.HAS_FEATURES), None)
        
        assert features_facet is not None
        # Should have values for code, tables, images, links
        assert len(features_facet.values) >= 3
        
        # Check specific counts
        code_value = next((v for v in features_facet.values if v.value == "code"), None)
        assert code_value is not None
        assert code_value.count == 2
        
        tables_value = next((v for v in features_facet.values if v.value == "tables"), None)
        assert tables_value is not None
        assert tables_value.count == 2
    
    def test_generate_project_facets(self):
        """Test project facet generation."""
        generator = DynamicFacetGenerator()
        
        results = [
            self._create_search_result(project_name="MyaHealth"),
            self._create_search_result(project_name="MyaHealth"),
            self._create_search_result(project_name="ProposAI"),
        ]
        
        facets = generator.generate_facets(results)
        project_facet = next((f for f in facets if f.facet_type == FacetType.PROJECT), None)
        
        assert project_facet is not None
        assert len(project_facet.values) == 2
        assert any(v.value == "MyaHealth" and v.count == 2 for v in project_facet.values)
        assert any(v.value == "ProposAI" and v.count == 1 for v in project_facet.values)
    
    def test_generate_entity_facets(self):
        """Test entity facet generation."""
        generator = DynamicFacetGenerator()
        
        results = [
            self._create_search_result(entities=[
                {"text": "OAuth", "label": "PRODUCT"},
                {"text": "AWS", "label": "ORG"}
            ]),
            self._create_search_result(entities=[
                {"text": "oauth", "label": "PRODUCT"},  # Should be deduplicated (case insensitive)
                {"text": "React", "label": "PRODUCT"}
            ]),
        ]
        
        facets = generator.generate_facets(results)
        entity_facet = next((f for f in facets if f.facet_type == FacetType.ENTITIES), None)
        
        assert entity_facet is not None
        assert len(entity_facet.values) >= 2
        
        # OAuth should appear twice (case insensitive)
        oauth_value = next((v for v in entity_facet.values if v.value == "oauth"), None)
        assert oauth_value is not None
        assert oauth_value.count == 2
    
    def test_generate_hierarchy_depth_facets(self):
        """Test hierarchy depth facet generation."""
        generator = DynamicFacetGenerator()
        
        results = [
            self._create_search_result(depth=1),  # shallow
            self._create_search_result(depth=2),  # shallow
            self._create_search_result(depth=3),  # medium
            self._create_search_result(depth=5),  # deep
        ]
        
        facets = generator.generate_facets(results)
        depth_facet = next((f for f in facets if f.facet_type == FacetType.HIERARCHY_DEPTH), None)
        
        assert depth_facet is not None
        assert len(depth_facet.values) == 3
        
        shallow_value = next((v for v in depth_facet.values if v.value == "shallow"), None)
        assert shallow_value is not None
        assert shallow_value.count == 2
    
    def test_facet_display_names(self):
        """Test that facet values have proper display names."""
        generator = DynamicFacetGenerator()
        
        results = [self._create_search_result(has_code_blocks=True, estimated_read_time=1)]
        facets = generator.generate_facets(results)
        
        features_facet = next((f for f in facets if f.facet_type == FacetType.HAS_FEATURES), None)
        if features_facet:
            code_value = next((v for v in features_facet.values if v.value == "code"), None)
            assert code_value is not None
            assert code_value.display_name == "Code Blocks"
        
        read_time_facet = next((f for f in facets if f.facet_type == FacetType.READ_TIME), None)
        if read_time_facet:
            quick_value = next((v for v in read_time_facet.values if v.value == "quick"), None)
            assert quick_value is not None
            assert "Quick Read" in quick_value.display_name
    
    def test_facet_priority_sorting(self):
        """Test that facets are sorted by priority."""
        generator = DynamicFacetGenerator()
        
        results = [
            self._create_search_result(
                source_type="confluence",
                project_name="MyaHealth",
                has_code_blocks=True,
                entities=[{"text": "OAuth", "label": "PRODUCT"}]
            )
        ]
        
        facets = generator.generate_facets(results)
        
        # Content type should come before entities (higher priority)
        content_type_index = next((i for i, f in enumerate(facets) if f.facet_type == FacetType.CONTENT_TYPE), -1)
        entities_index = next((i for i, f in enumerate(facets) if f.facet_type == FacetType.ENTITIES), -1)
        
        if content_type_index != -1 and entities_index != -1:
            assert content_type_index < entities_index
    
    def _create_search_result(self, **kwargs) -> HybridSearchResult:
        """Helper to create HybridSearchResult for testing."""
        defaults = {
            "score": 0.8,
            "text": "Test content",
            "source_type": "confluence",
            "source_title": "Test Document",
            "entities": [],
            "topics": [],
            "key_phrases": [],
            "pos_tags": []
        }
        defaults.update(kwargs)
        return create_hybrid_search_result(**defaults)


class TestFacetFilter:
    """Test suite for FacetFilter class."""
    
    def test_facet_filter_initialization(self):
        """Test facet filter initialization."""
        filter_obj = FacetFilter(
            facet_type=FacetType.CONTENT_TYPE,
            values=["confluence", "localfile"],
            operator="OR"
        )
        
        assert filter_obj.facet_type == FacetType.CONTENT_TYPE
        assert filter_obj.values == ["confluence", "localfile"]
        assert filter_obj.operator == "OR"
    
    def test_content_type_filter_matches(self):
        """Test content type filter matching."""
        filter_obj = FacetFilter(
            facet_type=FacetType.CONTENT_TYPE,
            values=["confluence"],
            operator="OR"
        )
        
        result1 = create_hybrid_search_result(score=0.8, text="test", source_type="confluence", source_title="Test")
        result2 = create_hybrid_search_result(score=0.8, text="test", source_type="localfile", source_title="Test")
        
        assert filter_obj.matches(result1) is True
        assert filter_obj.matches(result2) is False
    
    def test_features_filter_matches(self):
        """Test features filter matching."""
        filter_obj = FacetFilter(
            facet_type=FacetType.HAS_FEATURES,
            values=["code", "tables"],
            operator="OR"
        )
        
        result1 = create_hybrid_search_result(score=0.8, text="test", source_type="confluence", source_title="Test", has_code_blocks=True)
        result2 = create_hybrid_search_result(score=0.8, text="test", source_type="confluence", source_title="Test", has_tables=True)
        result3 = create_hybrid_search_result(score=0.8, text="test", source_type="confluence", source_title="Test", has_images=True)
        
        assert filter_obj.matches(result1) is True
        assert filter_obj.matches(result2) is True
        assert filter_obj.matches(result3) is False
    
    def test_and_operator_filter(self):
        """Test AND operator for filters."""
        filter_obj = FacetFilter(
            facet_type=FacetType.HAS_FEATURES,
            values=["code", "tables"],
            operator="AND"
        )
        
        result1 = create_hybrid_search_result(score=0.8, text="test", source_type="confluence", source_title="Test", 
                              has_code_blocks=True, has_tables=True)
        result2 = create_hybrid_search_result(score=0.8, text="test", source_type="confluence", source_title="Test", 
                              has_code_blocks=True)
        
        assert filter_obj.matches(result1) is True
        assert filter_obj.matches(result2) is False
    
    def test_entity_filter_matches(self):
        """Test entity filter matching."""
        filter_obj = FacetFilter(
            facet_type=FacetType.ENTITIES,
            values=["oauth"],
            operator="OR"
        )
        
        result1 = create_hybrid_search_result(
            score=0.8, text="test", source_type="confluence", source_title="Test",
            entities=[{"text": "OAuth", "label": "PRODUCT"}]
        )
        result2 = create_hybrid_search_result(
            score=0.8, text="test", source_type="confluence", source_title="Test",
            entities=[{"text": "React", "label": "PRODUCT"}]
        )
        
        assert filter_obj.matches(result1) is True  # Case insensitive match
        assert filter_obj.matches(result2) is False


class TestFacetedSearchEngine:
    """Test suite for FacetedSearchEngine class."""
    
    def test_faceted_search_engine_initialization(self):
        """Test faceted search engine initialization."""
        engine = FacetedSearchEngine()
        
        assert engine is not None
        assert engine.facet_generator is not None
        assert isinstance(engine.facet_generator, DynamicFacetGenerator)
    
    def test_apply_single_filter(self):
        """Test applying a single facet filter."""
        engine = FacetedSearchEngine()
        
        results = [
            create_hybrid_search_result(score=0.8, text="test1", source_type="confluence", source_title="Test1"),
            create_hybrid_search_result(score=0.8, text="test2", source_type="localfile", source_title="Test2"),
            create_hybrid_search_result(score=0.8, text="test3", source_type="confluence", source_title="Test3"),
        ]
        
        filter_obj = FacetFilter(
            facet_type=FacetType.CONTENT_TYPE,
            values=["confluence"],
            operator="OR"
        )
        
        filtered_results = engine.apply_facet_filters(results, [filter_obj])
        
        assert len(filtered_results) == 2
        assert all(r.source_type == "confluence" for r in filtered_results)
    
    def test_apply_multiple_filters(self):
        """Test applying multiple facet filters."""
        engine = FacetedSearchEngine()
        
        results = [
            create_hybrid_search_result(score=0.8, text="test1", source_type="confluence", source_title="Test1", 
                        has_code_blocks=True),
            create_hybrid_search_result(score=0.8, text="test2", source_type="confluence", source_title="Test2", 
                        has_tables=True),
            create_hybrid_search_result(score=0.8, text="test3", source_type="localfile", source_title="Test3", 
                        has_code_blocks=True),
        ]
        
        filters = [
            FacetFilter(facet_type=FacetType.CONTENT_TYPE, values=["confluence"], operator="OR"),
            FacetFilter(facet_type=FacetType.HAS_FEATURES, values=["code"], operator="OR")
        ]
        
        filtered_results = engine.apply_facet_filters(results, filters)
        
        assert len(filtered_results) == 1
        assert filtered_results[0].source_type == "confluence"
        assert filtered_results[0].has_code_blocks is True
    
    def test_generate_faceted_results(self):
        """Test generating complete faceted search results."""
        engine = FacetedSearchEngine()
        
        results = [
            create_hybrid_search_result(score=0.8, text="test1", source_type="confluence", source_title="Test1"),
            create_hybrid_search_result(score=0.8, text="test2", source_type="localfile", source_title="Test2"),
        ]
        
        faceted_results = engine.generate_faceted_results(results)
        
        assert isinstance(faceted_results, FacetedSearchResults)
        assert faceted_results.total_results == 2
        assert faceted_results.filtered_count == 2
        assert len(faceted_results.results) == 2
        assert len(faceted_results.facets) > 0
        assert faceted_results.generation_time_ms > 0
    
    def test_generate_faceted_results_with_filters(self):
        """Test generating faceted results with applied filters."""
        engine = FacetedSearchEngine()
        
        results = [
            create_hybrid_search_result(score=0.8, text="test1", source_type="confluence", source_title="Test1"),
            create_hybrid_search_result(score=0.8, text="test2", source_type="localfile", source_title="Test2"),
        ]
        
        filter_obj = FacetFilter(
            facet_type=FacetType.CONTENT_TYPE,
            values=["confluence"],
            operator="OR"
        )
        
        faceted_results = engine.generate_faceted_results(results, [filter_obj])
        
        assert faceted_results.total_results == 2  # Total before filtering
        assert faceted_results.filtered_count == 1  # After filtering
        assert len(faceted_results.results) == 1
        assert len(faceted_results.applied_filters) == 1
    
    def test_suggest_refinements(self):
        """Test facet refinement suggestions."""
        engine = FacetedSearchEngine()
        
        results = [
            create_hybrid_search_result(score=0.8, text="test1", source_type="confluence", source_title="Test1"),
            create_hybrid_search_result(score=0.8, text="test2", source_type="confluence", source_title="Test2"),
            create_hybrid_search_result(score=0.8, text="test3", source_type="localfile", source_title="Test3"),
        ]
        
        suggestions = engine.suggest_refinements(results, [])
        
        assert isinstance(suggestions, list)
        # Should suggest filtering by source type since it would reduce results
        if suggestions:
            assert all("facet_type" in s for s in suggestions)
            assert all("reduction_percent" in s for s in suggestions)
    
    def test_create_filter_from_selection(self):
        """Test creating filter from user selection."""
        engine = FacetedSearchEngine()
        
        filter_obj = engine.create_filter_from_selection(
            facet_type=FacetType.CONTENT_TYPE,
            selected_values=["confluence", "localfile"],
            operator="OR"
        )
        
        assert isinstance(filter_obj, FacetFilter)
        assert filter_obj.facet_type == FacetType.CONTENT_TYPE
        assert filter_obj.values == ["confluence", "localfile"]
        assert filter_obj.operator == "OR"


class TestFacetedSearchIntegration:
    """Integration tests for faceted search components."""
    
    def test_complete_faceted_search_workflow(self):
        """Test complete faceted search workflow."""
        # Create diverse test data
        results = [
            create_hybrid_search_result(
                score=0.9, text="OAuth implementation guide", source_type="confluence", 
                source_title="Auth Guide", project_name="MyaHealth", has_code_blocks=True,
                entities=[{"text": "OAuth", "label": "PRODUCT"}], depth=2
            ),
            create_hybrid_search_result(
                score=0.8, text="Database schema", source_type="localfile", 
                source_title="DB Schema", project_name="MyaHealth", has_tables=True,
                entities=[{"text": "PostgreSQL", "label": "PRODUCT"}], depth=1
            ),
            create_hybrid_search_result(
                score=0.7, text="Frontend components", source_type="git", 
                source_title="Components", project_name="ProposAI", has_code_blocks=True,
                entities=[{"text": "React", "label": "PRODUCT"}], depth=3
            ),
        ]
        
        engine = FacetedSearchEngine()
        
        # Step 1: Generate initial faceted results
        faceted_results = engine.generate_faceted_results(results)
        
        assert faceted_results.total_results == 3
        assert faceted_results.filtered_count == 3
        assert len(faceted_results.facets) > 0
        
        # Verify specific facets exist
        content_facet = next((f for f in faceted_results.facets if f.facet_type == FacetType.CONTENT_TYPE), None)
        assert content_facet is not None
        assert len(content_facet.values) == 3  # confluence, localfile, git
        
        project_facet = next((f for f in faceted_results.facets if f.facet_type == FacetType.PROJECT), None)
        assert project_facet is not None
        assert len(project_facet.values) == 2  # MyaHealth, ProposAI
        
        # Step 2: Apply filter
        project_filter = FacetFilter(
            facet_type=FacetType.PROJECT,
            values=["MyaHealth"],
            operator="OR"
        )
        
        filtered_results = engine.generate_faceted_results(results, [project_filter])
        
        assert filtered_results.total_results == 3
        assert filtered_results.filtered_count == 2  # Only MyaHealth results
        assert len(filtered_results.applied_filters) == 1
        
        # Step 3: Get suggestions
        suggestions = engine.suggest_refinements(results, [project_filter])
        
        # Should suggest additional filters that would further refine
        assert isinstance(suggestions, list)
        if suggestions:
            # Should suggest content type filter since we have multiple types in MyaHealth
            content_suggestions = [s for s in suggestions if s.get("facet_type") == "content_type"]
            assert len(content_suggestions) > 0
    
    def test_performance_with_large_dataset(self):
        """Test faceted search performance with larger dataset."""
        # Create 100 test results
        results = []
        for i in range(100):
            result = create_hybrid_search_result(
                score=0.8, 
                text=f"Test content {i}", 
                source_type="confluence" if i % 2 == 0 else "localfile",
                source_title=f"Document {i}",
                project_name="MyaHealth" if i % 3 == 0 else "ProposAI",
                has_code_blocks=i % 4 == 0,
                has_tables=i % 5 == 0,
                entities=[{"text": f"Entity{i%10}", "label": "PRODUCT"}],
                depth=i % 5 + 1
            )
            results.append(result)
        
        engine = FacetedSearchEngine()
        
        start_time = datetime.now()
        faceted_results = engine.generate_faceted_results(results)
        end_time = datetime.now()
        
        generation_time_ms = (end_time - start_time).total_seconds() * 1000
        
        # Should complete within reasonable time (less than 1 second)
        assert generation_time_ms < 1000
        assert faceted_results.total_results == 100
        assert len(faceted_results.facets) > 0
        
        # Test that facets have reasonable counts
        content_facet = next((f for f in faceted_results.facets if f.facet_type == FacetType.CONTENT_TYPE), None)
        assert content_facet is not None
        assert len(content_facet.values) == 2  # confluence and localfile
        
        # Test applying multiple filters
        filters = [
            FacetFilter(facet_type=FacetType.CONTENT_TYPE, values=["confluence"], operator="OR"),
            FacetFilter(facet_type=FacetType.HAS_FEATURES, values=["code"], operator="OR")
        ]
        
        filtered_results = engine.apply_facet_filters(results, filters)
        expected_count = len([r for r in results if r.source_type == "confluence" and r.has_code_blocks])
        
        assert len(filtered_results) == expected_count


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 