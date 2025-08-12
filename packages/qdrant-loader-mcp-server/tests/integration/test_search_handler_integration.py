"""Integration tests for SearchHandler with real component interactions."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from qdrant_loader_mcp_server.mcp.formatters import MCPFormatters
from qdrant_loader_mcp_server.mcp.protocol import MCPProtocol
from qdrant_loader_mcp_server.mcp.search_handler import SearchHandler


@pytest.fixture
def real_protocol():
    """Create a real MCPProtocol instance."""
    return MCPProtocol()


@pytest.fixture
def real_formatters():
    """Create a real MCPFormatters instance."""
    return MCPFormatters()


@pytest.fixture
def integration_search_handler(real_protocol):
    """Create a SearchHandler with real protocol but mocked engine/processor."""
    mock_search_engine = Mock()
    mock_search_engine.search = AsyncMock()

    mock_query_processor = Mock()
    mock_query_processor.process_query = AsyncMock()

    return SearchHandler(mock_search_engine, mock_query_processor, real_protocol)


@pytest.fixture
def realistic_search_results():
    """Create realistic search results for integration testing."""
    result1 = Mock()
    result1.document_id = "confluence-doc-123"
    result1.source_type = "confluence"
    result1.source_title = "API Integration Guide"
    result1.text = "This guide covers how to integrate with our REST API endpoints, including authentication, rate limiting, and best practices for error handling."
    result1.score = 0.92
    result1.depth = 0
    result1.parent_title = None
    result1.parent_id = None
    result1.children_count = 3
    result1.breadcrumb_text = ""
    result1.hierarchy_context = "Root document with 3 children"
    result1.is_attachment = False
    result1.file_size = None
    result1.attachment_author = None
    result1.parent_document_title = None
    result1.original_filename = None
    result1.attachment_context = None
    result1.source_url = "https://docs.company.com/api-guide"
    result1.file_path = None
    result1.repo_name = None
    result1.is_root_document = Mock(return_value=True)
    result1.has_children = Mock(return_value=True)
    result1.get_file_type = Mock(return_value=None)
    # Add numeric attributes needed by formatters
    result1.chunk_index = 0
    result1.total_chunks = 3
    result1.chunking_strategy = "paragraph"
    result1.word_count = 150
    result1.has_code_blocks = False
    result1.has_tables = True
    result1.has_images = False
    result1.vector_score = 0.85
    result1.keyword_score = 0.92
    result1.created_at = "2024-01-15T10:30:00Z"
    result1.last_modified = "2024-01-20T14:45:00Z"

    result2 = Mock()
    result2.document_id = "confluence-doc-456"
    result2.source_type = "confluence"
    result2.source_title = "Authentication Methods"
    result2.text = "Details on OAuth 2.0, API keys, and JWT token authentication for accessing our services."
    result2.score = 0.87
    result2.depth = 1
    result2.parent_title = "API Integration Guide"
    result2.parent_id = "confluence-doc-123"
    result2.children_count = 0
    result2.breadcrumb_text = "API Integration Guide > Authentication Methods"
    result2.hierarchy_context = "Child document under API Guide"
    result2.is_attachment = False
    result2.file_size = None
    result2.attachment_author = None
    result2.parent_document_title = None
    result2.original_filename = None
    result2.attachment_context = None
    result2.source_url = "https://docs.company.com/auth-methods"
    result2.file_path = None
    result2.repo_name = None
    result2.is_root_document = Mock(return_value=False)
    result2.has_children = Mock(return_value=False)
    result2.get_file_type = Mock(return_value=None)
    # Add numeric attributes needed by formatters
    result2.chunk_index = 1
    result2.total_chunks = 2
    result2.chunking_strategy = "section"
    result2.word_count = 120
    result2.has_code_blocks = True
    result2.has_tables = False
    result2.has_images = False
    result2.vector_score = 0.80
    result2.keyword_score = 0.87
    result2.created_at = "2024-01-15T11:00:00Z"
    result2.last_modified = "2024-01-18T16:30:00Z"

    result3 = Mock()
    result3.document_id = "localfile-789"
    result3.source_type = "localfile"
    result3.source_title = "config.yaml"
    result3.text = "Application configuration settings including database connections, API endpoints, and feature flags."
    result3.score = 0.75
    result3.depth = None
    result3.parent_title = None
    result3.parent_id = None
    result3.children_count = 0
    result3.breadcrumb_text = None
    result3.hierarchy_context = None
    result3.is_attachment = False
    result3.file_size = None
    result3.attachment_author = None
    result3.parent_document_title = None
    result3.original_filename = "config.yaml"
    result3.attachment_context = None
    result3.source_url = None
    result3.file_path = "project/config/config.yaml"
    result3.repo_name = "my-app"
    result3.is_root_document = Mock(return_value=False)
    result3.has_children = Mock(return_value=False)
    result3.get_file_type = Mock(return_value="yaml")
    # Add numeric attributes needed by formatters
    result3.chunk_index = 0
    result3.total_chunks = 1
    result3.chunking_strategy = "file"
    result3.word_count = 80
    result3.has_code_blocks = False
    result3.has_tables = False
    result3.has_images = False
    result3.vector_score = 0.70
    result3.keyword_score = 0.75
    result3.created_at = "2024-01-10T09:15:00Z"
    result3.last_modified = "2024-01-22T13:20:00Z"

    result4 = Mock()
    result4.document_id = "attachment-101"
    result4.source_type = "confluence"
    result4.source_title = "api-specification.json"
    result4.text = "OpenAPI specification file containing all REST API endpoints, request/response schemas, and examples."
    result4.score = 0.83
    result4.depth = None
    result4.parent_title = None
    result4.parent_id = None
    result4.children_count = 0
    result4.breadcrumb_text = "API Integration Guide > Resources"
    result4.hierarchy_context = None
    result4.is_attachment = True
    result4.file_size = 524288  # 512KB
    result4.attachment_author = "api.team@company.com"
    result4.parent_document_title = "API Integration Guide"
    result4.original_filename = "api-specification.json"
    result4.attachment_context = "OpenAPI spec for integration testing"
    result4.source_url = "https://docs.company.com/attachments/api-spec.json"
    result4.file_path = "/attachments/api-specification.json"
    result4.repo_name = None
    result4.is_root_document = Mock(return_value=False)
    result4.has_children = Mock(return_value=False)
    result4.get_file_type = Mock(return_value="json")
    # Add numeric attributes needed by formatters
    result4.chunk_index = 2
    result4.total_chunks = 4
    result4.chunking_strategy = "json"
    result4.word_count = 200
    result4.has_code_blocks = True
    result4.has_tables = False
    result4.has_images = False
    result4.vector_score = 0.78
    result4.keyword_score = 0.83
    result4.created_at = "2024-01-12T14:00:00Z"
    result4.last_modified = "2024-01-25T10:45:00Z"

    return [result1, result2, result3, result4]


class TestSearchIntegration:
    """Integration tests for basic search functionality."""

    @pytest.mark.asyncio
    async def test_search_integration_full_flow(
        self, integration_search_handler, realistic_search_results
    ):
        """Test complete search flow with real formatters and protocol."""
        # Setup realistic query processing
        integration_search_handler.query_processor.process_query.return_value = {
            "query": "API authentication methods",
            "intent": "informational",
            "entities": ["API", "authentication"],
        }

        # Setup realistic search results
        integration_search_handler.search_engine.search.return_value = (
            realistic_search_results
        )

        params = {
            "query": "How to authenticate with the API?",
            "source_types": ["confluence"],
            "project_ids": ["main-docs"],
            "limit": 5,
        }

        result = await integration_search_handler.handle_search("req-123", params)

        # Verify response structure
        assert result["jsonrpc"] == "2.0"
        assert result["id"] == "req-123"
        assert "result" in result
        assert "content" in result["result"]
        assert "structuredContent" in result["result"]
        assert result["result"]["isError"] is False

        # Verify content structure
        content = result["result"]["content"]
        assert len(content) == 1
        assert content[0]["type"] == "text"
        assert "Found 4 results" in content[0]["text"]

        # Verify structured content
        structured = result["result"]["structuredContent"]
        assert "results" in structured
        assert "total_found" in structured
        assert "query_context" in structured
        assert structured["total_found"] == 4
        assert (
            structured["query_context"]["original_query"]
            == "How to authenticate with the API?"
        )

    @pytest.mark.asyncio
    async def test_search_integration_error_propagation(
        self, integration_search_handler
    ):
        """Test that errors from components are properly handled and formatted."""
        # Setup query processor to fail
        integration_search_handler.query_processor.process_query.side_effect = (
            ConnectionError("OpenAI API unavailable")
        )

        params = {"query": "test query"}

        result = await integration_search_handler.handle_search("req-456", params)

        # Verify error response
        assert result["jsonrpc"] == "2.0"
        assert result["id"] == "req-456"
        assert "error" in result
        assert result["error"]["code"] == -32603
        assert result["error"]["message"] == "Internal error"
        assert "OpenAI API unavailable" in result["error"]["data"]

    @pytest.mark.asyncio
    async def test_search_integration_empty_results(self, integration_search_handler):
        """Test search integration with empty results."""
        integration_search_handler.query_processor.process_query.return_value = {
            "query": "no results query"
        }
        integration_search_handler.search_engine.search.return_value = []

        params = {"query": "no results query"}

        result = await integration_search_handler.handle_search("req-789", params)

        # Verify response for empty results
        assert result["result"]["isError"] is False
        content = result["result"]["content"][0]["text"]
        assert "Found 0 results" in content

        structured = result["result"]["structuredContent"]
        assert structured["total_found"] == 0
        assert len(structured["results"]) == 0


class TestHierarchySearchIntegration:
    """Integration tests for hierarchy search functionality."""

    @pytest.mark.asyncio
    async def test_hierarchy_search_integration_with_organization(
        self, integration_search_handler, realistic_search_results
    ):
        """Test hierarchy search with result organization."""
        integration_search_handler.query_processor.process_query.return_value = {
            "query": "API documentation"
        }
        integration_search_handler.search_engine.search.return_value = (
            realistic_search_results
        )

        params = {
            "query": "API documentation structure",
            "hierarchy_filter": {"depth": 0},
            "organize_by_hierarchy": True,
            "limit": 10,
        }

        result = await integration_search_handler.handle_hierarchy_search(
            "hier-123", params
        )

        # Verify hierarchy-specific response structure
        assert result["result"]["isError"] is False

        content = result["result"]["content"][0]["text"]
        assert "Hierarchy Search Results" in content

        structured = result["result"]["structuredContent"]
        assert "hierarchy_index" in structured or "hierarchy_groups" in structured

    @pytest.mark.asyncio
    async def test_hierarchy_search_integration_localfile_filtering(
        self, integration_search_handler, realistic_search_results
    ):
        """Test hierarchy search with localfile filtering."""
        integration_search_handler.query_processor.process_query.return_value = {
            "query": "config files"
        }
        integration_search_handler.search_engine.search.return_value = (
            realistic_search_results
        )

        params = {
            "query": "configuration files",
            "hierarchy_filter": {"root_only": True},
            "organize_by_hierarchy": False,
            "limit": 5,
        }

        result = await integration_search_handler.handle_hierarchy_search(
            "hier-456", params
        )

        # Verify search called with correct source types
        integration_search_handler.search_engine.search.assert_called_once_with(
            query="config files",
            source_types=["confluence", "localfile"],
            limit=40,  # max(5 * 2, 40)
        )

        assert result["result"]["isError"] is False


class TestAttachmentSearchIntegration:
    """Integration tests for attachment search functionality."""

    @pytest.mark.asyncio
    async def test_attachment_search_integration_with_grouping(
        self, integration_search_handler, realistic_search_results
    ):
        """Test attachment search with attachment grouping."""
        integration_search_handler.query_processor.process_query.return_value = {
            "query": "API specifications"
        }
        integration_search_handler.search_engine.search.return_value = (
            realistic_search_results
        )

        # Mock the attachment grouping
        with patch.object(
            integration_search_handler.formatters, "_organize_attachments_by_type"
        ) as mock_organize:
            mock_organize.return_value = [
                {"group_name": "JSON Files", "document_ids": ["attachment-101"]},
                {"group_name": "YAML Files", "document_ids": ["localfile-789"]},
            ]

            params = {
                "query": "API specification files",
                "attachment_filter": {"file_type": "json"},
                "include_parent_context": True,
                "limit": 10,
            }

            result = await integration_search_handler.handle_attachment_search(
                "attach-123", params
            )

            # Verify attachment-specific response
            assert result["result"]["isError"] is False

            content = result["result"]["content"][0]["text"]
            assert "Attachment Search Results" in content

            # Verify attachment grouping was called
            mock_organize.assert_called_once()

    @pytest.mark.asyncio
    async def test_attachment_search_integration_lightweight_filtering(
        self, integration_search_handler, realistic_search_results
    ):
        """Test attachment search with lightweight filtering."""
        integration_search_handler.query_processor.process_query.return_value = {
            "query": "files"
        }
        integration_search_handler.search_engine.search.return_value = (
            realistic_search_results
        )

        # Mock file type extraction
        with patch.object(
            integration_search_handler.formatters, "_extract_file_type_minimal"
        ) as mock_extract:
            mock_extract.side_effect = lambda x: (
                "json" if "json" in x.source_title else "yaml"
            )

            params = {
                "query": "configuration and specification files",
                "attachment_filter": {"file_type": "json", "file_size_max": 1048576},
                "limit": 5,
            }

            result = await integration_search_handler.handle_attachment_search(
                "attach-456", params
            )

            # Verify filtering was applied
            assert result["result"]["isError"] is False

            # Verify file type extraction was called
            assert mock_extract.called


class TestExpandDocumentIntegration:
    """Integration tests for document expansion functionality."""

    @pytest.mark.asyncio
    async def test_expand_document_integration_exact_match(
        self, integration_search_handler, realistic_search_results
    ):
        """Test document expansion with exact document ID match."""
        target_document = realistic_search_results[0]

        # Setup search to return exact match first
        integration_search_handler.search_engine.search.return_value = [target_document]

        params = {"document_id": "confluence-doc-123"}

        result = await integration_search_handler.handle_expand_document(
            "expand-123", params
        )

        # Verify exact match response
        assert result["result"]["isError"] is False

        content = result["result"]["content"][0]["text"]
        assert "Found 1 document" in content

        structured = result["result"]["structuredContent"]
        assert structured["total_found"] == 1
        assert structured["query_context"]["is_document_expansion"] is True
        assert (
            structured["query_context"]["original_query"]
            == "expand_document:confluence-doc-123"
        )

    @pytest.mark.asyncio
    async def test_expand_document_integration_fallback_search(
        self, integration_search_handler, realistic_search_results
    ):
        """Test document expansion with fallback to general search."""
        target_document = realistic_search_results[1]

        # Setup field search to fail, general search to succeed
        search_results = [[], [target_document]]
        integration_search_handler.search_engine.search.side_effect = search_results

        params = {"document_id": "confluence-doc-456"}

        result = await integration_search_handler.handle_expand_document(
            "expand-456", params
        )

        # Verify fallback search was used
        assert integration_search_handler.search_engine.search.call_count == 2
        assert result["result"]["isError"] is False

    @pytest.mark.asyncio
    async def test_expand_document_integration_not_found(
        self, integration_search_handler
    ):
        """Test document expansion when document is not found."""
        integration_search_handler.search_engine.search.side_effect = [[], []]

        params = {"document_id": "nonexistent-doc"}

        result = await integration_search_handler.handle_expand_document(
            "expand-789", params
        )

        # Verify not found error
        assert "error" in result
        assert result["error"]["code"] == -32604
        assert result["error"]["message"] == "Document not found"
        assert "nonexistent-doc" in result["error"]["data"]


class TestRealWorldScenarios:
    """Integration tests simulating real-world usage scenarios."""

    @pytest.mark.asyncio
    async def test_developer_workflow_api_search(
        self, integration_search_handler, realistic_search_results
    ):
        """Test a typical developer workflow searching for API information."""
        # Simulate developer searching for API authentication
        integration_search_handler.query_processor.process_query.return_value = {
            "query": "API authentication OAuth JWT",
            "intent": "technical_implementation",
            "entities": ["API", "authentication", "OAuth", "JWT"],
        }
        integration_search_handler.search_engine.search.return_value = (
            realistic_search_results
        )

        # First search: General API search
        params1 = {
            "query": "How do I authenticate with your API?",
            "source_types": ["confluence"],
            "limit": 10,
        }

        result1 = await integration_search_handler.handle_search(
            "dev-search-1", params1
        )
        assert result1["result"]["isError"] is False

        # Second search: Hierarchy search for related documents
        params2 = {
            "query": "API authentication methods",
            "hierarchy_filter": {"parent_title": "API Integration Guide"},
            "organize_by_hierarchy": True,
            "limit": 5,
        }

        result2 = await integration_search_handler.handle_hierarchy_search(
            "dev-search-2", params2
        )
        assert result2["result"]["isError"] is False

        # Third search: Look for specification files
        params3 = {
            "query": "API specification OpenAPI",
            "attachment_filter": {"file_type": "json"},
            "limit": 5,
        }

        result3 = await integration_search_handler.handle_attachment_search(
            "dev-search-3", params3
        )
        assert result3["result"]["isError"] is False

    @pytest.mark.asyncio
    async def test_content_manager_workflow(
        self, integration_search_handler, realistic_search_results
    ):
        """Test a content manager workflow organizing documentation."""
        integration_search_handler.query_processor.process_query.return_value = {
            "query": "documentation organization structure",
            "intent": "content_management",
        }
        integration_search_handler.search_engine.search.return_value = (
            realistic_search_results
        )

        # Search for root documents to understand structure
        params = {
            "query": "documentation structure overview",
            "hierarchy_filter": {"root_only": True, "has_children": True},
            "organize_by_hierarchy": True,
            "limit": 20,
        }

        result = await integration_search_handler.handle_hierarchy_search(
            "content-mgr-1", params
        )

        assert result["result"]["isError"] is False
        structured = result["result"]["structuredContent"]
        # Should have hierarchy organization for content management
        assert "hierarchy_index" in structured or "hierarchy_groups" in structured

    @pytest.mark.asyncio
    async def test_support_team_workflow(
        self, integration_search_handler, realistic_search_results
    ):
        """Test a support team workflow finding specific documentation."""
        integration_search_handler.query_processor.process_query.return_value = {
            "query": "customer support troubleshooting guide",
            "intent": "support",
        }
        integration_search_handler.search_engine.search.return_value = (
            realistic_search_results
        )

        # Start with broad search
        params1 = {
            "query": "customer having authentication issues",
            "source_types": ["confluence", "localfile"],
            "limit": 15,
        }

        result1 = await integration_search_handler.handle_search("support-1", params1)
        assert result1["result"]["isError"] is False

        # Expand specific document for details
        params2 = {"document_id": "confluence-doc-456"}  # Authentication Methods doc

        result2 = await integration_search_handler.handle_expand_document(
            "support-2", params2
        )
        assert result2["result"]["isError"] is False

        # Look for related attachments/resources
        params3 = {
            "query": "authentication troubleshooting resources",
            "attachment_filter": {"parent_document_title": "API Integration Guide"},
            "limit": 10,
        }

        result3 = await integration_search_handler.handle_attachment_search(
            "support-3", params3
        )
        assert result3["result"]["isError"] is False


class TestPerformanceScenarios:
    """Integration tests for performance-related scenarios."""

    @pytest.mark.asyncio
    async def test_large_result_set_handling(self, integration_search_handler):
        """Test handling of large result sets."""
        # Create many results
        large_result_set = []
        for i in range(100):
            result = Mock()
            result.document_id = f"doc-{i}"
            result.source_type = "confluence"
            result.source_title = f"Document {i}"
            result.text = f"Content for document {i}"
            result.score = 0.9 - (i * 0.001)  # Decreasing scores
            result.is_attachment = False
            result.original_filename = None
            result.file_path = None
            result.is_root_document = Mock(return_value=i < 10)
            result.has_children = Mock(return_value=i < 5)
            large_result_set.append(result)

        integration_search_handler.query_processor.process_query.return_value = {
            "query": "large dataset"
        }
        integration_search_handler.search_engine.search.return_value = large_result_set

        params = {"query": "find all documents", "limit": 50}

        result = await integration_search_handler.handle_search("perf-1", params)

        # Should handle large result set without issues
        assert result["result"]["isError"] is False
        structured = result["result"]["structuredContent"]
        assert structured["total_found"] == 100
        assert len(structured["results"]) <= 100  # Formatter may limit

    @pytest.mark.asyncio
    async def test_concurrent_requests(
        self, integration_search_handler, realistic_search_results
    ):
        """Test handling of concurrent search requests."""
        integration_search_handler.query_processor.process_query.return_value = {
            "query": "concurrent test"
        }
        integration_search_handler.search_engine.search.return_value = (
            realistic_search_results
        )

        # Create multiple concurrent requests
        tasks = []
        for i in range(5):
            params = {"query": f"concurrent search {i}", "limit": 5}
            task = integration_search_handler.handle_search(f"concurrent-{i}", params)
            tasks.append(task)

        # Execute all requests concurrently
        results = await asyncio.gather(*tasks)

        # All requests should complete successfully
        for i, result in enumerate(results):
            assert result["result"]["isError"] is False
            assert result["id"] == f"concurrent-{i}"
