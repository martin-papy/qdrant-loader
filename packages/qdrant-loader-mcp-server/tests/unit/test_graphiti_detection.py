"""Tests for Graphiti detection functionality."""

import os
from unittest.mock import AsyncMock, patch

import pytest
from qdrant_loader_mcp_server.graphiti.detection import (
    GraphitiDetector,
    get_graphiti_capabilities,
    is_graphiti_available,
    is_graphiti_configured,
)


class TestGraphitiDetector:
    """Test the GraphitiDetector class."""

    def test_is_configured_with_all_vars(self):
        """Test configuration detection when all environment variables are set."""
        with patch.dict(
            os.environ,
            {
                "NEO4J_URI": "bolt://localhost:7687",
                "NEO4J_USER": "neo4j",
                "NEO4J_PASSWORD": "password",
            },
        ):
            detector = GraphitiDetector()
            assert detector.is_configured() is True

    def test_is_configured_missing_vars(self):
        """Test configuration detection when environment variables are missing."""
        with patch.dict(os.environ, {}, clear=True):
            detector = GraphitiDetector()
            assert detector.is_configured() is False

    def test_is_configured_partial_vars(self):
        """Test configuration detection when some environment variables are missing."""
        with patch.dict(
            os.environ,
            {
                "NEO4J_URI": "bolt://localhost:7687",
                "NEO4J_USER": "neo4j",
                # Missing NEO4J_PASSWORD
            },
            clear=True,
        ):
            detector = GraphitiDetector()
            assert detector.is_configured() is False

    @pytest.mark.asyncio
    async def test_is_available_not_configured(self):
        """Test availability check when not configured."""
        with patch.dict(os.environ, {}, clear=True):
            detector = GraphitiDetector()
            available = await detector.is_available()
            assert available is False

    # Note: Import error testing is complex due to dynamic imports
    # The main functionality is covered by other tests

    @pytest.mark.asyncio
    async def test_is_available_connection_success(self):
        """Test availability check when connection succeeds."""
        with patch.dict(
            os.environ,
            {
                "NEO4J_URI": "bolt://localhost:7687",
                "NEO4J_USER": "neo4j",
                "NEO4J_PASSWORD": "password",
            },
        ):
            mock_client = AsyncMock()
            mock_client.search = AsyncMock(return_value=[])

            with patch("graphiti_core.Graphiti", return_value=mock_client):
                detector = GraphitiDetector()
                available = await detector.is_available()
                assert available is True
                assert detector.get_client() is mock_client

    @pytest.mark.asyncio
    async def test_is_available_connection_timeout(self):
        """Test availability check when connection times out."""
        with patch.dict(
            os.environ,
            {
                "NEO4J_URI": "bolt://localhost:7687",
                "NEO4J_USER": "neo4j",
                "NEO4J_PASSWORD": "password",
            },
        ):
            mock_client = AsyncMock()
            mock_client.search = AsyncMock(
                side_effect=TimeoutError("Connection timeout")
            )

            with patch("graphiti_core.Graphiti", return_value=mock_client):
                detector = GraphitiDetector()
                available = await detector.is_available()
                assert available is False

    @pytest.mark.asyncio
    async def test_get_capabilities_available(self):
        """Test capabilities when Graphiti is available."""
        with patch.dict(
            os.environ,
            {
                "NEO4J_URI": "bolt://localhost:7687",
                "NEO4J_USER": "neo4j",
                "NEO4J_PASSWORD": "password",
            },
        ):
            mock_client = AsyncMock()
            mock_client.search = AsyncMock(return_value=[])

            with patch("graphiti_core.Graphiti", return_value=mock_client):
                detector = GraphitiDetector()
                capabilities = await detector.get_capabilities()

                assert capabilities["graphiti_available"] is True
                assert capabilities["graph_operations"] is True
                assert capabilities["hybrid_search"] is True
                assert capabilities["temporal_queries"] is True
                assert capabilities["node_distance_reranking"] is True
                assert capabilities["fallback_mode"] is False

    @pytest.mark.asyncio
    async def test_get_capabilities_not_available(self):
        """Test capabilities when Graphiti is not available."""
        with patch.dict(os.environ, {}, clear=True):
            detector = GraphitiDetector()
            capabilities = await detector.get_capabilities()

            assert capabilities["graphiti_available"] is False
            assert capabilities["graph_operations"] is False
            assert capabilities["hybrid_search"] is False
            assert capabilities["temporal_queries"] is False
            assert capabilities["node_distance_reranking"] is False
            assert capabilities["fallback_mode"] is True


class TestModuleFunctions:
    """Test the module-level functions."""

    @pytest.mark.asyncio
    async def test_is_graphiti_available_function(self):
        """Test the is_graphiti_available function."""
        with patch.dict(os.environ, {}, clear=True):
            available = await is_graphiti_available()
            assert available is False

    def test_is_graphiti_configured_function(self):
        """Test the is_graphiti_configured function."""
        with patch.dict(
            os.environ,
            {
                "NEO4J_URI": "bolt://localhost:7687",
                "NEO4J_USER": "neo4j",
                "NEO4J_PASSWORD": "password",
            },
        ):
            configured = is_graphiti_configured()
            assert configured is True

    @pytest.mark.asyncio
    async def test_get_graphiti_capabilities_function(self):
        """Test the get_graphiti_capabilities function."""
        with patch.dict(os.environ, {}, clear=True):
            capabilities = await get_graphiti_capabilities()
            assert "graphiti_available" in capabilities
            assert "configuration" in capabilities
