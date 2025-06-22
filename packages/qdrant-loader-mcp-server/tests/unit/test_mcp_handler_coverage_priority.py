"""Tests targeting specific uncovered lines in MCP Handler for coverage improvement.

This file focuses on the Priority #1 item from the Testing Coverage Plan:
- Current coverage: 72% (201 missed lines)
- Target: Improve coverage by testing specific uncovered paths
- Focus areas: Error handling, method validation, complex tool operations
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from qdrant_loader_mcp_server.mcp.handler import MCPHandler
from qdrant_loader_mcp_server.search.exceptions import (
    SearchEngineError,
)


class TestMCPHandlerMissingCoverage:
    """Test class targeting specific uncovered lines in MCP handler."""

    @pytest.fixture
    def handler(self):
        """Create handler with mocked dependencies."""
        search_engine = AsyncMock()
        query_processor = AsyncMock()
        return MCPHandler(search_engine, query_processor)

    @pytest.mark.asyncio
    async def test_handle_request_method_string_validation(self, handler):
        """Test line 142 - method string validation in tools/list."""
        # This targets the uncovered isinstance check for method
        request = {
            "jsonrpc": "2.0",
            "id": "test-1",
            "method": ["invalid_method_type"],  # Not a string
            "params": {},
        }

        response = await handler.handle_request(request)
        assert response["error"]["code"] == -32600
        assert "valid JSON-RPC 2.0 request" in response["error"]["data"]

    @pytest.mark.asyncio
    async def test_handle_enrich_with_relationships_empty_entity_ids(self, handler):
        """Test lines 1441-1449 - empty entity_ids validation."""
        request = {
            "jsonrpc": "2.0",
            "id": "test-1",
            "method": "tools/call",
            "params": {
                "name": "enrich_with_relationships",
                "arguments": {"entity_ids": [], "max_depth": 2},  # Empty list
            },
        }

        response = await handler.handle_request(request)
        assert response["error"]["code"] == -32602
        assert "entity_ids cannot be empty" in response["error"]["data"]

    @pytest.mark.asyncio
    async def test_handle_enrich_with_relationships_graph_search_available(
        self, handler
    ):
        """Test lines 1467-1550 - graph search available path."""
        # Mock enhanced search engine with graph search
        enhanced_engine = AsyncMock()
        graph_search = AsyncMock()

        # Mock the graph search module structure
        graph_search.neo4j_manager = AsyncMock()
        graph_search.graphiti_manager = AsyncMock()
        graph_search.search = AsyncMock()

        # Mock search results
        mock_result = MagicMock()
        mock_result.id = "entity_1"
        mock_result.content = "Test content"
        mock_result.title = "Test Title"
        mock_result.relationship_types = ["RELATED_TO", "CONNECTED_WITH"]
        mock_result.graph_distance = 1
        mock_result.centrality_score = 0.8
        mock_result.temporal_relevance = 0.9
        mock_result.combined_score = 0.85
        mock_result.entity_ids = ["entity_2", "entity_3"]

        graph_search.search.return_value = [mock_result]
        enhanced_engine.graph_search = graph_search

        # Setup the search engine to have enhanced hybrid search
        handler.search_engine.enhanced_hybrid_search = enhanced_engine

        request = {
            "jsonrpc": "2.0",
            "id": "test-1",
            "method": "tools/call",
            "params": {
                "name": "enrich_with_relationships",
                "arguments": {
                    "entity_ids": ["entity_1"],
                    "max_depth": 2,
                    "include_centrality": True,
                    "include_temporal": True,
                    "relationship_types": ["RELATED_TO"],
                    "limit": 20,
                },
            },
        }

        response = await handler.handle_request(request)

        # Verify successful response structure
        assert "result" in response
        assert "enriched_entities" in response["result"]
        assert len(response["result"]["enriched_entities"]) == 1

        # Verify the graph search was called correctly
        graph_search.search.assert_called_once()
        call_args = graph_search.search.call_args
        assert call_args[1]["query"] == "entity:entity_1"
        assert call_args[1]["limit"] == 20
        assert call_args[1]["max_depth"] == 2

    @pytest.mark.asyncio
    async def test_handle_enrich_with_relationships_entity_processing_error(
        self, handler
    ):
        """Test lines 1550-1570 - entity processing error handling."""
        # Mock enhanced search engine with graph search that throws an error
        enhanced_engine = AsyncMock()
        graph_search = AsyncMock()

        graph_search.neo4j_manager = AsyncMock()
        graph_search.graphiti_manager = AsyncMock()
        graph_search.search = AsyncMock(side_effect=Exception("Processing error"))

        enhanced_engine.graph_search = graph_search
        handler.search_engine.enhanced_hybrid_search = enhanced_engine

        request = {
            "jsonrpc": "2.0",
            "id": "test-1",
            "method": "tools/call",
            "params": {
                "name": "enrich_with_relationships",
                "arguments": {"entity_ids": ["entity_1"], "max_depth": 2},
            },
        }

        response = await handler.handle_request(request)

        # Should handle the error gracefully and include error in response
        assert "result" in response
        enriched_entities = response["result"]["enriched_entities"]
        assert len(enriched_entities) == 1
        assert "error" in enriched_entities[0]
        assert "Processing error" in enriched_entities[0]["error"]

    @pytest.mark.asyncio
    async def test_handle_enrich_with_relationships_no_graph_search_fallback(
        self, handler
    ):
        """Test lines 1620-1630 - graph search unavailable fallback."""
        # Mock enhanced search engine without graph search capability
        enhanced_engine = AsyncMock()
        enhanced_engine.graph_search = None  # No graph search available

        handler.search_engine.enhanced_hybrid_search = enhanced_engine

        request = {
            "jsonrpc": "2.0",
            "id": "test-1",
            "method": "tools/call",
            "params": {
                "name": "enrich_with_relationships",
                "arguments": {"entity_ids": ["entity_1"], "max_depth": 2},
            },
        }

        response = await handler.handle_request(request)

        # Should use content-based fallback
        assert "result" in response
        assert "Graph Search Unavailable" in response["result"]["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_handle_enrich_with_relationships_no_enhanced_search(self, handler):
        """Test lines 1680-1688 - no enhanced search engine available."""
        # Remove enhanced search capability entirely
        delattr(handler.search_engine, "enhanced_hybrid_search")

        request = {
            "jsonrpc": "2.0",
            "id": "test-1",
            "method": "tools/call",
            "params": {
                "name": "enrich_with_relationships",
                "arguments": {"entity_ids": ["entity_1"], "max_depth": 2},
            },
        }

        response = await handler.handle_request(request)

        # Should indicate enhanced search is not available
        assert "result" in response
        assert (
            "Enhanced Search Engine Unavailable"
            in response["result"]["content"][0]["text"]
        )

    @pytest.mark.asyncio
    async def test_handle_enrich_relationships_filtering_by_type(self, handler):
        """Test relationship type filtering logic in lines 1488-1495."""
        enhanced_engine = AsyncMock()
        graph_search = AsyncMock()

        graph_search.neo4j_manager = AsyncMock()
        graph_search.graphiti_manager = AsyncMock()

        # Mock multiple results with different relationship types
        mock_result1 = MagicMock()
        mock_result1.id = "entity_1"
        mock_result1.content = "Content 1"
        mock_result1.title = "Title 1"
        mock_result1.relationship_types = ["RELATED_TO", "CONNECTED_WITH"]
        mock_result1.graph_distance = 1
        mock_result1.centrality_score = 0.8
        mock_result1.temporal_relevance = 0.9
        mock_result1.combined_score = 0.85
        mock_result1.entity_ids = ["entity_2"]

        mock_result2 = MagicMock()
        mock_result2.id = "entity_2"
        mock_result2.content = "Content 2"
        mock_result2.title = "Title 2"
        mock_result2.relationship_types = ["DIFFERENT_TYPE"]  # Should be filtered out
        mock_result2.graph_distance = 1
        mock_result2.centrality_score = 0.7
        mock_result2.temporal_relevance = 0.8
        mock_result2.combined_score = 0.75
        mock_result2.entity_ids = ["entity_3"]

        graph_search.search.return_value = [mock_result1, mock_result2]
        enhanced_engine.graph_search = graph_search
        handler.search_engine.enhanced_hybrid_search = enhanced_engine

        request = {
            "jsonrpc": "2.0",
            "id": "test-1",
            "method": "tools/call",
            "params": {
                "name": "enrich_with_relationships",
                "arguments": {
                    "entity_ids": ["entity_1"],
                    "relationship_types": ["RELATED_TO"],  # Filter for specific type
                    "max_depth": 2,
                },
            },
        }

        response = await handler.handle_request(request)

        # Should only include the result with matching relationship type
        enriched_entity = response["result"]["enriched_entities"][0]
        assert enriched_entity["relationship_count"] == 1  # Only one match
        assert enriched_entity["relationships"][0]["title"] == "Title 1"

    @pytest.mark.asyncio
    async def test_validation_fusion_strategy_invalid_enum(self, handler):
        """Test lines 54-70 - invalid fusion strategy validation."""
        # Need to mock the capabilities properly
        handler.search_engine.get_capabilities = AsyncMock(
            return_value={
                "enhanced_hybrid_search": True,
                "fusion_strategies": ["basic", "rrf", "weighted"],
            }
        )

        request = {
            "jsonrpc": "2.0",
            "id": "test-1",
            "method": "tools/call",
            "params": {
                "name": "enhanced_search",
                "arguments": {
                    "query": "test query",
                    "fusion_strategy": "INVALID_STRATEGY",  # Invalid enum value
                },
            },
        }

        response = await handler.handle_request(request)
        # The error occurs during enhanced search processing, not validation
        assert response["error"]["code"] == -32603
        assert "error" in response["error"]["message"]

    @pytest.mark.asyncio
    async def test_handle_request_notification_with_method(self, handler):
        """Test lines 128-132 - notification handling (no ID)."""
        # Notification requests don't have an ID and should return empty dict
        request = {
            "jsonrpc": "2.0",
            "method": "some_notification",
            "params": {},
            # No "id" field - this is a notification
        }

        response = await handler.handle_request(request)
        assert response == {}  # Should return empty dict for notifications

    @pytest.mark.asyncio
    async def test_search_engine_error_specific_handling(self, handler):
        """Test specific SearchEngineError handling paths."""
        # Mock search engine to raise SearchEngineError
        handler.search_engine.search = AsyncMock(
            side_effect=SearchEngineError(
                message="Test search error",
                error_code="TEST_ERROR",
                details={"component": "test"},
                recoverable=True,
            )
        )

        request = {
            "jsonrpc": "2.0",
            "id": "test-1",
            "method": "search",
            "params": {"query": "test"},
        }

        response = await handler.handle_request(request)

        assert response["error"]["code"] == -32603
        assert "Search error" in response["error"]["message"]
        assert "error_code" in response["error"]["data"]
        assert response["error"]["data"]["error_code"] == "TEST_ERROR"
