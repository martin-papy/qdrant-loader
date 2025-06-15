"""Tests for hybrid search interface compatibility and backward compatibility."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from qdrant_loader_mcp_server.mcp.handler import MCPHandler
from qdrant_loader_mcp_server.search.models import SearchResult


@pytest.fixture
def mock_search_engine():
    """Create a mock search engine."""
    engine = MagicMock()
    engine.search = AsyncMock()
    return engine


@pytest.fixture
def mock_query_processor():
    """Create a mock query processor."""
    processor = MagicMock()
    processor.process_query = AsyncMock(return_value={"query": "processed query"})
    return processor


@pytest.fixture
def mcp_handler(mock_search_engine, mock_query_processor):
    """Create an MCP handler with mocked dependencies."""
    return MCPHandler(mock_search_engine, mock_query_processor)


@pytest.fixture
def sample_search_results():
    """Create sample search results for testing."""
    return [
        SearchResult(
            text="Sample result 1",
            score=0.9,
            source_type="confluence",
            source_title="Test Document 1",
            source_url="https://example.com/doc1",
        ),
        SearchResult(
            text="Sample result 2",
            score=0.8,
            source_type="confluence",
            source_title="Test Document 2",
            source_url="https://example.com/doc2",
        ),
    ]


class TestBasicSearchHybridCompatibility:
    """Test basic search tool with hybrid parameters."""

    @pytest.mark.asyncio
    async def test_basic_search_legacy_behavior(
        self, mcp_handler, sample_search_results
    ):
        """Test that basic search maintains legacy behavior when no hybrid params provided."""
        mcp_handler.search_engine.search.return_value = sample_search_results

        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "search",
                "arguments": {
                    "query": "test query",
                    "limit": 5,
                },
            },
            "id": 1,
        }

        response = await mcp_handler.handle_request(request)

        # Verify legacy search was called without hybrid parameters
        mcp_handler.search_engine.search.assert_called_once()
        call_args = mcp_handler.search_engine.search.call_args

        # Should not have hybrid parameters in the call
        assert "mode" not in call_args.kwargs
        assert "vector_weight" not in call_args.kwargs
        assert "fusion_strategy" not in call_args.kwargs

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert "Found 2 results" in response["result"]["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_basic_search_with_hybrid_parameters(
        self, mcp_handler, sample_search_results
    ):
        """Test that basic search uses enhanced search when hybrid params provided."""
        mcp_handler.search_engine.search.return_value = sample_search_results

        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "search",
                "arguments": {
                    "query": "test query",
                    "limit": 5,
                    "mode": "hybrid",
                    "vector_weight": 0.6,
                    "keyword_weight": 0.3,
                    "graph_weight": 0.1,
                    "fusion_strategy": "weighted_sum",
                },
            },
            "id": 1,
        }

        response = await mcp_handler.handle_request(request)

        # Verify enhanced search was called with hybrid parameters
        mcp_handler.search_engine.search.assert_called_once()
        call_args = mcp_handler.search_engine.search.call_args

        # Should have hybrid parameters in the call
        assert call_args.kwargs["mode"] == "hybrid"
        assert call_args.kwargs["vector_weight"] == 0.6
        assert call_args.kwargs["keyword_weight"] == 0.3
        assert call_args.kwargs["graph_weight"] == 0.1
        assert call_args.kwargs["fusion_strategy"] == "weighted_sum"

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response

    @pytest.mark.asyncio
    async def test_basic_search_invalid_mode(self, mcp_handler):
        """Test that basic search validates mode parameter."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "search",
                "arguments": {
                    "query": "test query",
                    "mode": "invalid_mode",
                },
            },
            "id": 1,
        }

        response = await mcp_handler.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "error" in response
        assert "Invalid search mode" in response["error"]["data"]

    @pytest.mark.asyncio
    async def test_basic_search_invalid_weight(self, mcp_handler):
        """Test that basic search validates weight parameters."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "search",
                "arguments": {
                    "query": "test query",
                    "vector_weight": 1.5,  # Invalid: > 1.0
                },
            },
            "id": 1,
        }

        response = await mcp_handler.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "error" in response
        assert "Invalid vector_weight" in response["error"]["data"]


class TestHierarchySearchHybridCompatibility:
    """Test hierarchy search tool with hybrid parameters."""

    @pytest.mark.asyncio
    async def test_hierarchy_search_legacy_behavior(
        self, mcp_handler, sample_search_results
    ):
        """Test that hierarchy search maintains legacy behavior when no hybrid params provided."""
        mcp_handler.search_engine.search.return_value = sample_search_results

        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "hierarchy_search",
                "arguments": {
                    "query": "test query",
                    "limit": 10,
                },
            },
            "id": 1,
        }

        response = await mcp_handler.handle_request(request)

        # Verify legacy search was called without hybrid parameters
        mcp_handler.search_engine.search.assert_called_once()
        call_args = mcp_handler.search_engine.search.call_args

        # Should not have hybrid parameters in the call
        assert "mode" not in call_args.kwargs
        assert "vector_weight" not in call_args.kwargs
        assert "fusion_strategy" not in call_args.kwargs

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response

    @pytest.mark.asyncio
    async def test_hierarchy_search_with_hybrid_parameters(
        self, mcp_handler, sample_search_results
    ):
        """Test that hierarchy search uses enhanced search when hybrid params provided."""
        mcp_handler.search_engine.search.return_value = sample_search_results

        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "hierarchy_search",
                "arguments": {
                    "query": "test query",
                    "limit": 10,
                    "mode": "hybrid",
                    "fusion_strategy": "graph_enhanced_weighted",
                },
            },
            "id": 1,
        }

        response = await mcp_handler.handle_request(request)

        # Verify enhanced search was called with hybrid parameters
        mcp_handler.search_engine.search.assert_called_once()
        call_args = mcp_handler.search_engine.search.call_args

        # Should have hybrid parameters in the call
        assert call_args.kwargs["mode"] == "hybrid"
        assert call_args.kwargs["fusion_strategy"] == "graph_enhanced_weighted"

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response


class TestAttachmentSearchHybridCompatibility:
    """Test attachment search tool with hybrid parameters."""

    @pytest.mark.asyncio
    async def test_attachment_search_legacy_behavior(
        self, mcp_handler, sample_search_results
    ):
        """Test that attachment search maintains legacy behavior when no hybrid params provided."""
        mcp_handler.search_engine.search.return_value = sample_search_results

        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "attachment_search",
                "arguments": {
                    "query": "test query",
                    "limit": 10,
                },
            },
            "id": 1,
        }

        response = await mcp_handler.handle_request(request)

        # Verify legacy search was called without hybrid parameters
        mcp_handler.search_engine.search.assert_called_once()
        call_args = mcp_handler.search_engine.search.call_args

        # Should not have hybrid parameters in the call
        assert "mode" not in call_args.kwargs
        assert "vector_weight" not in call_args.kwargs
        assert "fusion_strategy" not in call_args.kwargs

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response

    @pytest.mark.asyncio
    async def test_attachment_search_with_hybrid_parameters(
        self, mcp_handler, sample_search_results
    ):
        """Test that attachment search uses enhanced search when hybrid params provided."""
        mcp_handler.search_engine.search.return_value = sample_search_results

        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "attachment_search",
                "arguments": {
                    "query": "test query",
                    "limit": 10,
                    "mode": "vector_only",
                    "vector_weight": 1.0,
                    "fusion_strategy": "confidence_adaptive",
                },
            },
            "id": 1,
        }

        response = await mcp_handler.handle_request(request)

        # Verify enhanced search was called with hybrid parameters
        mcp_handler.search_engine.search.assert_called_once()
        call_args = mcp_handler.search_engine.search.call_args

        # Should have hybrid parameters in the call
        assert call_args.kwargs["mode"] == "vector_only"
        assert call_args.kwargs["vector_weight"] == 1.0
        assert call_args.kwargs["fusion_strategy"] == "confidence_adaptive"

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response


class TestFusionStrategyValidation:
    """Test fusion strategy validation across all tools."""

    @pytest.mark.asyncio
    async def test_invalid_fusion_strategy_basic_search(self, mcp_handler):
        """Test that invalid fusion strategy is rejected in basic search."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "search",
                "arguments": {
                    "query": "test query",
                    "fusion_strategy": "invalid_strategy",
                },
            },
            "id": 1,
        }

        response = await mcp_handler.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "error" in response
        assert "Invalid fusion strategy" in response["error"]["data"]

    @pytest.mark.asyncio
    async def test_valid_fusion_strategies(self, mcp_handler, sample_search_results):
        """Test that all valid fusion strategies are accepted."""
        mcp_handler.search_engine.search.return_value = sample_search_results

        valid_strategies = [
            "weighted_sum",
            "reciprocal_rank_fusion",
            "maximal_marginal_relevance",
            "graph_enhanced_weighted",
            "confidence_adaptive",
            "multi_stage",
            "context_aware",
        ]

        for strategy in valid_strategies:
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "search",
                    "arguments": {
                        "query": "test query",
                        "fusion_strategy": strategy,
                    },
                },
                "id": 1,
            }

            response = await mcp_handler.handle_request(request)

            assert response["jsonrpc"] == "2.0"
            assert response["id"] == 1
            assert "result" in response, f"Strategy {strategy} should be valid"

            # Reset the mock for next iteration
            mcp_handler.search_engine.search.reset_mock()


class TestBackwardCompatibility:
    """Test that existing functionality remains unchanged."""

    @pytest.mark.asyncio
    async def test_existing_parameters_still_work(
        self, mcp_handler, sample_search_results
    ):
        """Test that all existing parameters continue to work as before."""
        mcp_handler.search_engine.search.return_value = sample_search_results

        # Test basic search with all existing parameters
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "search",
                "arguments": {
                    "query": "test query",
                    "source_types": ["confluence", "jira"],
                    "project_ids": ["project1", "project2"],
                    "limit": 15,
                },
            },
            "id": 1,
        }

        response = await mcp_handler.handle_request(request)

        # Verify all existing parameters are passed correctly
        mcp_handler.search_engine.search.assert_called_once()
        call_args = mcp_handler.search_engine.search.call_args

        assert call_args.kwargs["source_types"] == ["confluence", "jira"]
        assert call_args.kwargs["project_ids"] == ["project1", "project2"]
        assert call_args.kwargs["limit"] == 15

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response

    @pytest.mark.asyncio
    async def test_response_format_unchanged(self, mcp_handler, sample_search_results):
        """Test that response format remains the same for backward compatibility."""
        mcp_handler.search_engine.search.return_value = sample_search_results

        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "search",
                "arguments": {
                    "query": "test query",
                },
            },
            "id": 1,
        }

        response = await mcp_handler.handle_request(request)

        # Verify response structure is unchanged
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert "content" in response["result"]
        assert isinstance(response["result"]["content"], list)
        assert response["result"]["content"][0]["type"] == "text"
        assert "Found 2 results" in response["result"]["content"][0]["text"]
        assert response["result"]["isError"] is False
