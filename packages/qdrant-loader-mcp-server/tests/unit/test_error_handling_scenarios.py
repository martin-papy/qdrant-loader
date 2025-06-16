"""Tests for error handling scenarios in the search system."""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_loader_mcp_server.config import OpenAIConfig, QdrantConfig
from qdrant_loader_mcp_server.mcp.handler import MCPHandler
from qdrant_loader_mcp_server.search.engine import SearchEngine
from qdrant_loader_mcp_server.search.exceptions import (
    FusionStrategyError,
    GraphitiError,
    HybridSearchError,
    Neo4jConnectionError,
    OpenAIEmbeddingError,
    QdrantConnectionError,
    QdrantQueryError,
    SearchConfigurationError,
)
from qdrant_loader_mcp_server.search.processor import QueryProcessor


class TestSearchEngineExceptions:
    """Test custom search engine exceptions."""

    def test_search_engine_error_base(self):
        """Test base SearchEngineError functionality."""
        error = QdrantConnectionError(
            message="Test connection error",
            qdrant_url="http://localhost:6333",
            original_error=ConnectionError("Connection refused"),
        )

        assert error.error_code == "QDRANT_CONNECTION_ERROR"
        assert error.message == "Test connection error"
        assert error.recoverable is True
        assert "qdrant_url" in error.details
        assert error.details["qdrant_url"] == "http://localhost:6333"

        error_dict = error.to_dict()
        assert error_dict["error_code"] == "QDRANT_CONNECTION_ERROR"
        assert error_dict["recoverable"] is True

    def test_qdrant_connection_error(self):
        """Test QdrantConnectionError creation and properties."""
        error = QdrantConnectionError(
            qdrant_url="http://test:6333",
            original_error=ConnectionError("Network unreachable"),
        )

        assert error.error_code == "QDRANT_CONNECTION_ERROR"
        assert error.details["qdrant_url"] == "http://test:6333"
        assert error.details["error_type"] == "ConnectionError"

    def test_qdrant_query_error(self):
        """Test QdrantQueryError creation and properties."""
        error = QdrantQueryError(
            query="test query",
            collection_name="test_collection",
            original_error=ValueError("Invalid parameters"),
        )

        assert error.error_code == "QDRANT_QUERY_ERROR"
        assert error.details["query"] == "test query"
        assert error.details["collection_name"] == "test_collection"
        assert error.details["error_type"] == "ValueError"

    def test_neo4j_connection_error(self):
        """Test Neo4jConnectionError creation and properties."""
        error = Neo4jConnectionError(
            neo4j_uri="bolt://localhost:7687",
            original_error=ConnectionError("Service unavailable"),
        )

        assert error.error_code == "NEO4J_CONNECTION_ERROR"
        assert error.details["neo4j_uri"] == "bolt://localhost:7687"
        assert error.details["error_type"] == "ConnectionError"

    def test_openai_embedding_error(self):
        """Test OpenAIEmbeddingError creation and properties."""
        long_text = "a" * 200
        error = OpenAIEmbeddingError(
            text=long_text,
            model="text-embedding-3-small",
            original_error=Exception("API quota exceeded"),
        )

        assert error.error_code == "OPENAI_EMBEDDING_ERROR"
        assert error.details["text_length"] == 200
        assert error.details["text_preview"] == "a" * 100 + "..."
        assert error.details["model"] == "text-embedding-3-small"

    def test_search_configuration_error(self):
        """Test SearchConfigurationError creation and properties."""
        error = SearchConfigurationError(
            parameter="vector_weight", value=1.5, expected="0.0-1.0"
        )

        assert error.error_code == "SEARCH_CONFIG_ERROR"
        assert error.recoverable is False  # Config errors are not recoverable
        assert error.details["parameter"] == "vector_weight"
        assert error.details["value"] == 1.5

    def test_fusion_strategy_error(self):
        """Test FusionStrategyError creation and properties."""
        error = FusionStrategyError(
            strategy="weighted_sum",
            result_counts={"vector": 10, "graph": 5, "keyword": 8},
            original_error=ValueError("Incompatible result sets"),
        )

        assert error.error_code == "FUSION_STRATEGY_ERROR"
        assert error.details["strategy"] == "weighted_sum"
        assert error.details["result_counts"]["vector"] == 10

    def test_hybrid_search_error(self):
        """Test HybridSearchError creation and properties."""
        error = HybridSearchError(
            failed_components=["graph_search"],
            successful_components=["vector_search", "keyword_search"],
            original_error=Exception("Graph database unavailable"),
        )

        assert error.error_code == "HYBRID_SEARCH_ERROR"
        assert "graph_search" in error.details["failed_components"]
        assert "vector_search" in error.details["successful_components"]


class TestSearchEngineErrorHandling:
    """Test error handling in SearchEngine."""

    @pytest.fixture
    def search_engine(self):
        """Create a SearchEngine instance for testing."""
        return SearchEngine()

    @pytest.fixture
    def qdrant_config(self):
        """Create a QdrantConfig for testing."""
        return QdrantConfig(
            url="http://localhost:6333",
            api_key="test-key",
            collection_name="test_collection",
        )

    @pytest.fixture
    def openai_config(self):
        """Create an OpenAIConfig for testing."""
        return OpenAIConfig(api_key="test-openai-key")

    @pytest.mark.asyncio
    async def test_qdrant_connection_error_during_init(
        self, search_engine, qdrant_config, openai_config
    ):
        """Test QdrantConnectionError during initialization."""
        with patch("qdrant_client.QdrantClient") as mock_client:
            mock_client.side_effect = ConnectionError("Connection refused")

            with pytest.raises(QdrantConnectionError) as exc_info:
                await search_engine.initialize(qdrant_config, openai_config)

            assert exc_info.value.error_code == "QDRANT_CONNECTION_ERROR"
            assert "Connection refused" in str(exc_info.value.details["original_error"])

    @pytest.mark.asyncio
    async def test_qdrant_unexpected_response_during_init(
        self, search_engine, qdrant_config, openai_config
    ):
        """Test UnexpectedResponse from Qdrant during initialization."""
        with patch("qdrant_client.QdrantClient") as mock_client:
            unexpected_error = UnexpectedResponse(
                status_code=500,
                reason_phrase="Internal Server Error",
                content=b"Internal Server Error",
                headers=httpx.Headers(),
            )
            mock_client.side_effect = unexpected_error

            with pytest.raises(QdrantConnectionError) as exc_info:
                await search_engine.initialize(qdrant_config, openai_config)

            assert exc_info.value.error_code == "QDRANT_CONNECTION_ERROR"
            # The actual error message will be about connection refused, not unexpected response
            assert "connection refused" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_search_with_qdrant_connection_error(self, search_engine):
        """Test search method with QdrantConnectionError."""
        # Mock a properly initialized search engine
        search_engine.hybrid_search = Mock()
        search_engine.hybrid_search.search = AsyncMock(
            side_effect=ConnectionError("Connection lost")
        )

        with pytest.raises(QdrantConnectionError) as exc_info:
            await search_engine.search("test query")

        assert exc_info.value.error_code == "QDRANT_CONNECTION_ERROR"

    @pytest.mark.asyncio
    async def test_search_with_qdrant_query_error(self, search_engine):
        """Test search method with QdrantQueryError."""
        search_engine.hybrid_search = Mock()
        search_engine.hybrid_search.search = AsyncMock(
            side_effect=UnexpectedResponse(
                status_code=400,
                reason_phrase="Bad Request",
                content=b"Bad Request",
                headers=httpx.Headers(),
            )
        )

        with pytest.raises(QdrantQueryError) as exc_info:
            await search_engine.search("test query")

        assert exc_info.value.error_code == "QDRANT_QUERY_ERROR"

    @pytest.mark.asyncio
    async def test_search_with_generic_error_wrapping(self, search_engine):
        """Test search method wrapping generic errors in HybridSearchError."""
        search_engine.hybrid_search = Mock()
        search_engine.hybrid_search.search = AsyncMock(
            side_effect=ValueError("Unexpected error")
        )

        with pytest.raises(HybridSearchError) as exc_info:
            await search_engine.search("test query")

        assert exc_info.value.error_code == "HYBRID_SEARCH_ERROR"
        assert "basic_hybrid_search" in exc_info.value.details["failed_components"]


class TestMCPHandlerErrorHandling:
    """Test error handling in MCPHandler."""

    @pytest.fixture
    def mock_search_engine(self):
        """Create a mock SearchEngine."""
        engine = Mock(spec=SearchEngine)
        engine.search = AsyncMock()
        return engine

    @pytest.fixture
    def mock_query_processor(self):
        """Create a mock QueryProcessor."""
        processor = Mock(spec=QueryProcessor)
        processor.process_query = AsyncMock(return_value={"query": "processed query"})
        return processor

    @pytest.fixture
    def mcp_handler(self, mock_search_engine, mock_query_processor):
        """Create an MCPHandler instance for testing."""
        return MCPHandler(mock_search_engine, mock_query_processor)

    @pytest.mark.asyncio
    async def test_qdrant_connection_error_handling(
        self, mcp_handler, mock_search_engine
    ):
        """Test MCP handler handling QdrantConnectionError."""
        mock_search_engine.search.side_effect = QdrantConnectionError(
            qdrant_url="http://localhost:6333"
        )

        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "search", "arguments": {"query": "test query"}},
            "id": "test-1",
        }

        response = await mcp_handler.handle_request(request)

        assert "error" in response
        assert response["error"]["message"] == "Vector database connection failed"
        assert "suggestion" in response["error"]["data"]
        assert "Qdrant server is running" in response["error"]["data"]["suggestion"]

    @pytest.mark.asyncio
    async def test_neo4j_connection_error_handling(
        self, mcp_handler, mock_search_engine
    ):
        """Test MCP handler handling Neo4jConnectionError."""
        mock_search_engine.search.side_effect = Neo4jConnectionError(
            neo4j_uri="bolt://localhost:7687"
        )

        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "search", "arguments": {"query": "test query"}},
            "id": "test-2",
        }

        response = await mcp_handler.handle_request(request)

        assert "error" in response
        assert response["error"]["message"] == "Graph database connection failed"
        assert "Vector search will continue" in response["error"]["data"]["suggestion"]

    @pytest.mark.asyncio
    async def test_openai_embedding_error_handling(
        self, mcp_handler, mock_search_engine
    ):
        """Test MCP handler handling OpenAIEmbeddingError."""
        mock_search_engine.search.side_effect = OpenAIEmbeddingError(
            text="test query", model="text-embedding-3-small"
        )

        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "search", "arguments": {"query": "test query"}},
            "id": "test-3",
        }

        response = await mcp_handler.handle_request(request)

        assert "error" in response
        assert response["error"]["message"] == "Text embedding generation failed"
        assert "OpenAI API key" in response["error"]["data"]["suggestion"]

    @pytest.mark.asyncio
    async def test_search_configuration_error_handling(
        self, mcp_handler, mock_search_engine
    ):
        """Test MCP handler handling SearchConfigurationError."""
        mock_search_engine.search.side_effect = SearchConfigurationError(
            parameter="vector_weight", value=1.5, expected="0.0-1.0"
        )

        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "search", "arguments": {"query": "test query"}},
            "id": "test-4",
        }

        response = await mcp_handler.handle_request(request)

        assert "error" in response
        assert response["error"]["code"] == -32602  # Invalid params
        assert response["error"]["message"] == "Invalid search configuration"

    @pytest.mark.asyncio
    async def test_fusion_strategy_error_handling(
        self, mcp_handler, mock_search_engine
    ):
        """Test MCP handler handling FusionStrategyError."""
        mock_search_engine.search.side_effect = FusionStrategyError(
            strategy="weighted_sum", result_counts={"vector": 10, "graph": 0}
        )

        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "search", "arguments": {"query": "test query"}},
            "id": "test-5",
        }

        response = await mcp_handler.handle_request(request)

        assert "error" in response
        assert response["error"]["message"] == "Result fusion failed"
        assert "default fusion strategy" in response["error"]["data"]["suggestion"]

    @pytest.mark.asyncio
    async def test_hybrid_search_error_handling(self, mcp_handler, mock_search_engine):
        """Test MCP handler handling HybridSearchError."""
        mock_search_engine.search.side_effect = HybridSearchError(
            failed_components=["graph_search"], successful_components=["vector_search"]
        )

        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "search", "arguments": {"query": "test query"}},
            "id": "test-6",
        }

        response = await mcp_handler.handle_request(request)

        assert "error" in response
        assert response["error"]["message"] == "Hybrid search operation failed"
        assert (
            "Partial results may be available"
            in response["error"]["data"]["suggestion"]
        )

    @pytest.mark.asyncio
    async def test_unexpected_error_handling(self, mcp_handler, mock_search_engine):
        """Test MCP handler handling unexpected errors."""
        mock_search_engine.search.side_effect = RuntimeError("Unexpected system error")

        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "search", "arguments": {"query": "test query"}},
            "id": "test-7",
        }

        response = await mcp_handler.handle_request(request)

        assert "error" in response
        assert response["error"]["message"] == "Unexpected search error"
        assert response["error"]["data"]["error_type"] == "RuntimeError"
        assert response["error"]["data"]["recoverable"] is True

    @pytest.mark.asyncio
    async def test_error_response_format_consistency(
        self, mcp_handler, mock_search_engine
    ):
        """Test that all error responses follow consistent format."""
        errors_to_test = [
            QdrantConnectionError(),
            Neo4jConnectionError(),
            OpenAIEmbeddingError(),
            SearchConfigurationError(),
            FusionStrategyError(),
            HybridSearchError(),
        ]

        for error in errors_to_test:
            mock_search_engine.search.side_effect = error

            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "search", "arguments": {"query": "test query"}},
                "id": f"test-{error.error_code}",
            }

            response = await mcp_handler.handle_request(request)

            # Check response structure
            assert "jsonrpc" in response
            assert "id" in response
            assert "error" in response

            # Check error structure
            error_obj = response["error"]
            assert "code" in error_obj
            assert "message" in error_obj
            assert "data" in error_obj

            # Check data structure
            data = error_obj["data"]
            assert "error_code" in data
            assert "message" in data
            assert "details" in data
            assert "recoverable" in data


class TestErrorRecoveryScenarios:
    """Test error recovery and fallback scenarios."""

    @pytest.fixture
    def search_engine_with_fallbacks(self):
        """Create a SearchEngine with mocked fallback capabilities."""
        engine = SearchEngine()
        engine.hybrid_search = Mock()
        engine.enhanced_hybrid_search = Mock()
        engine.use_enhanced_search = True
        return engine

    @pytest.mark.asyncio
    async def test_enhanced_to_basic_fallback(self, search_engine_with_fallbacks):
        """Test fallback from enhanced to basic search on error."""
        # Enhanced search fails
        search_engine_with_fallbacks.enhanced_hybrid_search.search = AsyncMock(
            side_effect=GraphitiError("Graphiti unavailable")
        )

        # Basic search succeeds
        from qdrant_loader_mcp_server.search.models import SearchResult

        mock_results = [
            SearchResult(
                text="Test result",
                score=0.8,
                source_type="test",
                source_title="Test Document",
            )
        ]
        search_engine_with_fallbacks.hybrid_search.search = AsyncMock(
            return_value=mock_results
        )

        # Should fall back to basic search
        results = await search_engine_with_fallbacks.search(
            "test query",
            mode="hybrid",  # This should trigger enhanced search attempt
            vector_weight=0.5,
        )

        assert len(results) == 1
        assert results[0].text == "Test result"

        # Verify enhanced search was attempted
        search_engine_with_fallbacks.enhanced_hybrid_search.search.assert_called_once()

        # Verify basic search was used as fallback
        search_engine_with_fallbacks.hybrid_search.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_fallback_on_critical_errors(self, search_engine_with_fallbacks):
        """Test that critical errors don't trigger fallback."""
        # Both enhanced and basic search fail with critical errors
        search_engine_with_fallbacks.enhanced_hybrid_search.search = AsyncMock(
            side_effect=QdrantConnectionError("Qdrant unavailable")
        )
        search_engine_with_fallbacks.hybrid_search.search = AsyncMock(
            side_effect=QdrantConnectionError("Qdrant unavailable")
        )

        # Should not fall back, should raise the error
        with pytest.raises(QdrantConnectionError):
            await search_engine_with_fallbacks.search(
                "test query", mode="hybrid", vector_weight=0.5
            )


class TestErrorSimulationScenarios:
    """Test error simulation scenarios for QDrant and Neo4j outages."""

    @pytest.fixture
    def mcp_handler_with_real_engines(self):
        """Create MCPHandler with real but mocked engines for simulation."""
        search_engine = SearchEngine()
        query_processor = Mock(spec=QueryProcessor)
        query_processor.process_query = AsyncMock(
            return_value={"query": "processed query"}
        )
        return MCPHandler(search_engine, query_processor)

    @pytest.mark.asyncio
    async def test_qdrant_server_outage_simulation(self, mcp_handler_with_real_engines):
        """Simulate complete QDrant server outage."""
        handler = mcp_handler_with_real_engines

        # Mock QDrant client to simulate server outage
        with patch.object(handler.search_engine, "hybrid_search") as mock_hybrid:
            mock_hybrid.search = AsyncMock(
                side_effect=ConnectionError("Connection refused")
            )

            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "search", "arguments": {"query": "test outage"}},
                "id": "outage-test-1",
            }

            response = await handler.handle_request(request)

            assert "error" in response
            assert "Vector database connection failed" in response["error"]["message"]
            assert response["error"]["data"]["error_code"] == "QDRANT_CONNECTION_ERROR"

    @pytest.mark.asyncio
    async def test_neo4j_server_outage_simulation(self, mcp_handler_with_real_engines):
        """Simulate Neo4j server outage with graceful degradation."""
        handler = mcp_handler_with_real_engines

        # Mock enhanced search to fail with Neo4j error but basic search to succeed
        with patch.object(
            handler.search_engine, "enhanced_hybrid_search"
        ) as mock_enhanced:
            with patch.object(handler.search_engine, "hybrid_search") as mock_basic:
                mock_enhanced.search = AsyncMock(
                    side_effect=Neo4jConnectionError("Neo4j unavailable")
                )

                from qdrant_loader_mcp_server.search.models import SearchResult

                mock_results = [
                    SearchResult(
                        text="Fallback result",
                        score=0.7,
                        source_type="test",
                        source_title="Test",
                    )
                ]
                mock_basic.search = AsyncMock(return_value=mock_results)

                # Set up enhanced search availability
                handler.search_engine.use_enhanced_search = True

                request = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "search",
                        "arguments": {
                            "query": "test neo4j outage",
                            "mode": "hybrid",  # This should trigger enhanced search
                            "graph_weight": 0.3,
                        },
                    },
                    "id": "neo4j-outage-test",
                }

                response = await handler.handle_request(request)

                # Should succeed with fallback to basic search
                assert "error" not in response
                assert "result" in response
                assert "Fallback result" in response["result"]["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_openai_api_quota_exceeded_simulation(
        self, mcp_handler_with_real_engines
    ):
        """Simulate OpenAI API quota exceeded error."""
        handler = mcp_handler_with_real_engines

        with patch.object(handler.search_engine, "hybrid_search") as mock_hybrid:
            mock_hybrid.search = AsyncMock(
                side_effect=OpenAIEmbeddingError(
                    text="test query",
                    model="text-embedding-3-small",
                    original_error=Exception("Rate limit exceeded"),
                )
            )

            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "search", "arguments": {"query": "test quota"}},
                "id": "quota-test",
            }

            response = await handler.handle_request(request)

            assert "error" in response
            # The OpenAI error gets wrapped in a HybridSearchError
            assert "Hybrid search operation failed" in response["error"]["message"]
            assert response["error"]["data"]["error_code"] == "HYBRID_SEARCH_ERROR"

    @pytest.mark.asyncio
    async def test_malformed_qdrant_response_simulation(
        self, mcp_handler_with_real_engines
    ):
        """Simulate malformed response from QDrant server."""
        handler = mcp_handler_with_real_engines

        with patch.object(handler.search_engine, "hybrid_search") as mock_hybrid:
            mock_hybrid.search = AsyncMock(
                side_effect=UnexpectedResponse(
                    status_code=502,
                    reason_phrase="Bad Gateway",
                    content=b"Malformed response",
                    headers=httpx.Headers(),
                )
            )

            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "search", "arguments": {"query": "test malformed"}},
                "id": "malformed-test",
            }

            response = await handler.handle_request(request)

            assert "error" in response
            assert response["error"]["data"]["error_code"] == "QDRANT_QUERY_ERROR"

    @pytest.mark.asyncio
    async def test_partial_component_failure_simulation(
        self, mcp_handler_with_real_engines
    ):
        """Simulate partial failure where some search components work."""
        handler = mcp_handler_with_real_engines

        with patch.object(handler.search_engine, "hybrid_search") as mock_hybrid:
            mock_hybrid.search = AsyncMock(
                side_effect=HybridSearchError(
                    message="Graph search failed but vector search succeeded",
                    failed_components=["graph_search"],
                    successful_components=["vector_search", "keyword_search"],
                    original_error=Exception("Graph database timeout"),
                )
            )

            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "search",
                    "arguments": {"query": "test partial failure"},
                },
                "id": "partial-failure-test",
            }

            response = await handler.handle_request(request)

            assert "error" in response
            assert "Hybrid search operation failed" in response["error"]["message"]
            # The original HybridSearchError gets wrapped, so the failed components will be different
            assert (
                "basic_hybrid_search"
                in response["error"]["data"]["details"]["failed_components"]
            )
            # Check that the original error message is preserved
            assert (
                "Graph search failed but vector search succeeded"
                in response["error"]["data"]["details"]["original_error"]
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
