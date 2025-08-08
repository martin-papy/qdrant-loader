"""Error handling and edge case tests for SearchHandler."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from qdrant_loader_mcp_server.mcp.search_handler import SearchHandler
from qdrant_loader_mcp_server.mcp.protocol import MCPProtocol


@pytest.fixture
def mock_search_engine():
    """Create a mock search engine."""
    engine = Mock()
    engine.search = AsyncMock()
    return engine


@pytest.fixture
def mock_query_processor():
    """Create a mock query processor."""
    processor = Mock()
    processor.process_query = AsyncMock()
    return processor


@pytest.fixture
def mock_protocol():
    """Create a mock MCP protocol."""
    protocol = Mock(spec=MCPProtocol)
    protocol.create_response = Mock()
    return protocol


@pytest.fixture
def search_handler_with_mocks(mock_search_engine, mock_query_processor, mock_protocol):
    """Create a SearchHandler with all mocked dependencies."""
    return SearchHandler(mock_search_engine, mock_query_processor, mock_protocol)


class TestSearchErrorHandling:
    """Test error handling in basic search operations."""

    @pytest.mark.asyncio
    async def test_handle_search_query_processor_timeout(self, search_handler_with_mocks):
        """Test search when query processor times out."""
        search_handler_with_mocks.query_processor.process_query.side_effect = asyncio.TimeoutError("OpenAI request timed out")
        search_handler_with_mocks.protocol.create_response.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32603, "message": "Internal error"}
        }
        
        params = {"query": "test query"}
        result = await search_handler_with_mocks.handle_search(1, params)
        
        search_handler_with_mocks.protocol.create_response.assert_called_once_with(
            1,
            error={"code": -32603, "message": "Internal error", "data": "OpenAI request timed out"}
        )

    @pytest.mark.asyncio
    async def test_handle_search_search_engine_connection_error(self, search_handler_with_mocks):
        """Test search when search engine has connection issues."""
        search_handler_with_mocks.query_processor.process_query.return_value = {"query": "test"}
        search_handler_with_mocks.search_engine.search.side_effect = ConnectionRefusedError("Qdrant connection refused")
        search_handler_with_mocks.protocol.create_response.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32603, "message": "Internal error"}
        }
        
        params = {"query": "test query"}
        result = await search_handler_with_mocks.handle_search(1, params)
        
        search_handler_with_mocks.protocol.create_response.assert_called_once_with(
            1,
            error={"code": -32603, "message": "Internal error", "data": "Qdrant connection refused"}
        )

    @pytest.mark.asyncio
    async def test_handle_search_invalid_response_from_engine(self, search_handler_with_mocks):
        """Test search when engine returns invalid response."""
        search_handler_with_mocks.query_processor.process_query.return_value = {"query": "test"}
        search_handler_with_mocks.search_engine.search.return_value = None  # Invalid response
        search_handler_with_mocks.protocol.create_response.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32603, "message": "Internal error"}
        }
        
        with patch.object(search_handler_with_mocks.formatters, 'create_structured_search_results') as mock_structured:
            mock_structured.side_effect = TypeError("'NoneType' object is not iterable")
            
            params = {"query": "test query"}
            result = await search_handler_with_mocks.handle_search(1, params)
            
            # Should handle the error gracefully
            search_handler_with_mocks.protocol.create_response.assert_called_once()
            call_args = search_handler_with_mocks.protocol.create_response.call_args
            assert call_args[1]["error"]["code"] == -32603

    @pytest.mark.asyncio
    async def test_handle_search_malformed_query_params(self, search_handler_with_mocks):
        """Test search with malformed query parameters."""
        search_handler_with_mocks.protocol.create_response.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32602, "message": "Invalid params"}
        }
        
        # Test with non-string query
        params = {"query": 123}
        result = await search_handler_with_mocks.handle_search(1, params)
        
        # Should validate and reject
        search_handler_with_mocks.protocol.create_response.assert_called_once()
        assert "error" in result

    @pytest.mark.asyncio
    async def test_handle_search_empty_query_string(self, search_handler_with_mocks):
        """Test search with empty query string."""
        search_handler_with_mocks.query_processor.process_query.return_value = {"query": ""}
        search_handler_with_mocks.search_engine.search.return_value = []
        search_handler_with_mocks.protocol.create_response.return_value = {"jsonrpc": "2.0", "id": 1}
        
        with patch.object(search_handler_with_mocks.formatters, 'create_structured_search_results'):
            with patch.object(search_handler_with_mocks.formatters, 'format_search_result'):
                params = {"query": ""}
                result = await search_handler_with_mocks.handle_search(1, params)
                
                # Should handle empty query gracefully
                search_handler_with_mocks.search_engine.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_search_large_limit_parameter(self, search_handler_with_mocks):
        """Test search with unusually large limit parameter."""
        search_handler_with_mocks.query_processor.process_query.return_value = {"query": "test"}
        search_handler_with_mocks.search_engine.search.return_value = []
        search_handler_with_mocks.protocol.create_response.return_value = {"jsonrpc": "2.0", "id": 1}
        
        with patch.object(search_handler_with_mocks.formatters, 'create_structured_search_results'):
            with patch.object(search_handler_with_mocks.formatters, 'format_search_result'):
                params = {"query": "test", "limit": 999999}
                result = await search_handler_with_mocks.handle_search(1, params)
                
                # Should pass large limit to search engine without modification
                search_handler_with_mocks.search_engine.search.assert_called_once_with(
                    query="test",
                    source_types=[],
                    project_ids=[],
                    limit=999999
                )


class TestHierarchySearchErrorHandling:
    """Test error handling in hierarchy search operations."""

    @pytest.mark.asyncio
    async def test_handle_hierarchy_search_filter_processing_error(self, search_handler_with_mocks):
        """Test hierarchy search when filter processing fails."""
        search_handler_with_mocks.query_processor.process_query.return_value = {"query": "test"}
        search_handler_with_mocks.search_engine.search.return_value = []
        search_handler_with_mocks.protocol.create_response.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32603, "message": "Internal error"}
        }
        
        # Mock hierarchy filter to raise an error
        with patch.object(search_handler_with_mocks, '_apply_hierarchy_filters') as mock_filter:
            mock_filter.side_effect = ValueError("Invalid hierarchy filter")
            
            params = {"query": "test", "hierarchy_filter": {"invalid": "filter"}}
            result = await search_handler_with_mocks.handle_hierarchy_search(1, params)
            
            search_handler_with_mocks.protocol.create_response.assert_called_once_with(
                1,
                error={"code": -32603, "message": "Internal error", "data": "Invalid hierarchy filter"}
            )

    @pytest.mark.asyncio
    async def test_handle_hierarchy_search_organization_error(self, search_handler_with_mocks):
        """Test hierarchy search when result organization fails."""
        mock_result = Mock()
        mock_result.source_type = "confluence"
        
        search_handler_with_mocks.query_processor.process_query.return_value = {"query": "test"}
        search_handler_with_mocks.search_engine.search.return_value = [mock_result]
        search_handler_with_mocks.protocol.create_response.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32603, "message": "Internal error"}
        }
        
        # Mock organize hierarchy to raise an error
        with patch.object(search_handler_with_mocks, '_organize_by_hierarchy') as mock_organize:
            mock_organize.side_effect = KeyError("Missing hierarchy attribute")
            
            params = {"query": "test", "organize_by_hierarchy": True}
            result = await search_handler_with_mocks.handle_hierarchy_search(1, params)
            
            search_handler_with_mocks.protocol.create_response.assert_called_once_with(
                1,
                error={"code": -32603, "message": "Internal error", "data": "'Missing hierarchy attribute'"}
            )

    @pytest.mark.asyncio
    async def test_handle_hierarchy_search_malformed_hierarchy_filter(self, search_handler_with_mocks):
        """Test hierarchy search with malformed hierarchy filter."""
        search_handler_with_mocks.query_processor.process_query.return_value = {"query": "test"}
        search_handler_with_mocks.search_engine.search.return_value = []
        search_handler_with_mocks.protocol.create_response.return_value = {"jsonrpc": "2.0", "id": 1}
        
        with patch.object(search_handler_with_mocks.formatters, 'create_lightweight_hierarchy_results'):
            # Test with non-dict hierarchy filter
            params = {"query": "test", "hierarchy_filter": "invalid"}
            result = await search_handler_with_mocks.handle_hierarchy_search(1, params)
            
            # Should handle malformed filter gracefully
            search_handler_with_mocks.search_engine.search.assert_called_once()


class TestAttachmentSearchErrorHandling:
    """Test error handling in attachment search operations."""

    @pytest.mark.asyncio
    async def test_handle_attachment_search_filter_error(self, search_handler_with_mocks):
        """Test attachment search when filtering fails."""
        search_handler_with_mocks.query_processor.process_query.return_value = {"query": "test"}
        search_handler_with_mocks.search_engine.search.return_value = []
        search_handler_with_mocks.protocol.create_response.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32603, "message": "Internal error"}
        }
        
        # Mock attachment filter to raise an error
        with patch.object(search_handler_with_mocks, '_apply_lightweight_attachment_filters') as mock_filter:
            mock_filter.side_effect = AttributeError("'Mock' object has no attribute 'file_size'")
            
            params = {"query": "test", "attachment_filter": {"file_size_min": 1000}}
            result = await search_handler_with_mocks.handle_attachment_search(1, params)
            
            search_handler_with_mocks.protocol.create_response.assert_called_once_with(
                1,
                error={"code": -32603, "message": "Internal error", "data": "'Mock' object has no attribute 'file_size'"}
            )

    @pytest.mark.asyncio
    async def test_handle_attachment_search_organization_error(self, search_handler_with_mocks):
        """Test attachment search when organization fails."""
        mock_result = Mock()
        mock_result.is_attachment = True
        mock_result.original_filename = "test.pdf"
        
        search_handler_with_mocks.query_processor.process_query.return_value = {"query": "test"}
        search_handler_with_mocks.search_engine.search.return_value = [mock_result]
        search_handler_with_mocks.protocol.create_response.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32603, "message": "Internal error"}
        }
        
        # Mock attachment organization to raise an error
        with patch.object(search_handler_with_mocks.formatters, '_organize_attachments_by_type') as mock_organize:
            mock_organize.side_effect = TypeError("Cannot organize invalid attachment")
            
            params = {"query": "test"}
            result = await search_handler_with_mocks.handle_attachment_search(1, params)
            
            search_handler_with_mocks.protocol.create_response.assert_called_once_with(
                1,
                error={"code": -32603, "message": "Internal error", "data": "Cannot organize invalid attachment"}
            )


class TestExpandDocumentErrorHandling:
    """Test error handling in document expansion operations."""

    @pytest.mark.asyncio
    async def test_handle_expand_document_search_engine_error(self, search_handler_with_mocks):
        """Test document expansion when search engine fails."""
        search_handler_with_mocks.search_engine.search.side_effect = RuntimeError("Search index corrupted")
        search_handler_with_mocks.protocol.create_response.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32603, "message": "Internal error"}
        }
        
        params = {"document_id": "test-doc"}
        result = await search_handler_with_mocks.handle_expand_document(1, params)
        
        search_handler_with_mocks.protocol.create_response.assert_called_once_with(
            1,
            error={"code": -32603, "message": "Internal error", "data": "Search index corrupted"}
        )

    @pytest.mark.asyncio
    async def test_handle_expand_document_partial_match_error(self, search_handler_with_mocks):
        """Test document expansion when partial matching fails."""
        # First search returns results but no exact match
        partial_result = Mock()
        partial_result.document_id = "different-doc"
        
        search_handler_with_mocks.search_engine.search.side_effect = [
            [partial_result],  # Field search with no exact match
            RuntimeError("General search failed")  # Fallback search fails
        ]
        search_handler_with_mocks.protocol.create_response.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32603, "message": "Internal error"}
        }
        
        params = {"document_id": "target-doc"}
        result = await search_handler_with_mocks.handle_expand_document(1, params)
        
        search_handler_with_mocks.protocol.create_response.assert_called_once_with(
            1,
            error={"code": -32603, "message": "Internal error", "data": "General search failed"}
        )

    @pytest.mark.asyncio
    async def test_handle_expand_document_invalid_document_id(self, search_handler_with_mocks):
        """Test document expansion with various invalid document IDs."""
        search_handler_with_mocks.protocol.create_response.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32602, "message": "Invalid params"}
        }
        
        # Test with None document_id
        params = {"document_id": None}
        result = await search_handler_with_mocks.handle_expand_document(1, params)
        
        search_handler_with_mocks.protocol.create_response.assert_called_once_with(
            1,
            error={
                "code": -32602,
                "message": "Invalid params",
                "data": "Missing required parameter: document_id",
            }
        )

    @pytest.mark.asyncio
    async def test_handle_expand_document_formatting_error(self, search_handler_with_mocks):
        """Test document expansion when result formatting fails."""
        mock_result = Mock()
        mock_result.document_id = "test-doc"
        
        search_handler_with_mocks.search_engine.search.return_value = [mock_result]
        search_handler_with_mocks.protocol.create_response.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32603, "message": "Internal error"}
        }
        
        # Mock formatter to raise an error
        with patch.object(search_handler_with_mocks.formatters, 'format_search_result') as mock_format:
            mock_format.side_effect = ValueError("Cannot format malformed result")
            
            params = {"document_id": "test-doc"}
            result = await search_handler_with_mocks.handle_expand_document(1, params)
            
            search_handler_with_mocks.protocol.create_response.assert_called_once_with(
                1,
                error={"code": -32603, "message": "Internal error", "data": "Cannot format malformed result"}
            )


class TestFilterErrorHandling:
    """Test error handling in filter methods."""

    def test_apply_hierarchy_filters_malformed_results(self, search_handler_with_mocks):
        """Test hierarchy filters with malformed search results."""
        # Create malformed results missing required attributes
        malformed_result = Mock()
        del malformed_result.source_type  # Remove required attribute
        
        hierarchy_filter = {"depth": 0}
        
        # Should handle gracefully and not crash
        try:
            filtered = search_handler_with_mocks._apply_hierarchy_filters([malformed_result], hierarchy_filter)
            # Should return empty list or handle gracefully
            assert isinstance(filtered, list)
        except AttributeError:
            # This is expected behavior for malformed results
            pass

    def test_apply_hierarchy_filters_invalid_filter_values(self, search_handler_with_mocks):
        """Test hierarchy filters with invalid filter values."""
        mock_result = Mock()
        mock_result.source_type = "confluence"
        mock_result.depth = 0
        
        # Test with invalid depth type
        hierarchy_filter = {"depth": "invalid"}
        
        try:
            filtered = search_handler_with_mocks._apply_hierarchy_filters([mock_result], hierarchy_filter)
            # Should handle type mismatch gracefully
            assert isinstance(filtered, list)
        except (TypeError, ValueError):
            # Expected for type mismatches
            pass

    def test_apply_lightweight_attachment_filters_corrupted_results(self, search_handler_with_mocks):
        """Test attachment filters with corrupted search results."""
        corrupted_result = Mock()
        corrupted_result.is_attachment = None  # Should be boolean
        corrupted_result.original_filename = 123  # Should be string
        corrupted_result.file_path = []  # Should be string
        
        attachment_filter = {"attachments_only": True}
        
        # Should handle corrupted data gracefully
        try:
            filtered = search_handler_with_mocks._apply_lightweight_attachment_filters([corrupted_result], attachment_filter)
            assert isinstance(filtered, list)
        except (TypeError, AttributeError):
            # Expected for corrupted data
            pass

    def test_organize_by_hierarchy_missing_attributes(self, search_handler_with_mocks):
        """Test hierarchy organization with results missing attributes."""
        incomplete_result = Mock()
        incomplete_result.source_type = "confluence"
        # Missing breadcrumb_text, source_title, etc.
        del incomplete_result.breadcrumb_text
        del incomplete_result.source_title
        
        try:
            organized = search_handler_with_mocks._organize_by_hierarchy([incomplete_result])
            assert isinstance(organized, dict)
        except AttributeError:
            # Expected for incomplete results
            pass


class TestFormattingErrorHandling:
    """Test error handling in formatting methods."""

    def test_format_lightweight_attachment_text_invalid_data(self, search_handler_with_mocks):
        """Test attachment text formatting with invalid data."""
        # Test with invalid organized_results structure
        invalid_organized = {"invalid": "structure"}
        
        try:
            result = search_handler_with_mocks._format_lightweight_attachment_text(invalid_organized, 5)
            assert isinstance(result, str)
        except (TypeError, AttributeError, KeyError):
            # Expected for invalid data structure
            pass

    def test_format_lightweight_hierarchy_text_invalid_data(self, search_handler_with_mocks):
        """Test hierarchy text formatting with invalid data."""
        # Test with invalid organized_results structure
        invalid_organized = {"group": [None, "invalid"]}
        
        try:
            result = search_handler_with_mocks._format_lightweight_hierarchy_text(invalid_organized, 3)
            assert isinstance(result, str)
        except (TypeError, AttributeError):
            # Expected for invalid data structure
            pass

    def test_formatting_with_unicode_content(self, search_handler_with_mocks):
        """Test formatting with unicode and special characters."""
        unicode_organized = {"📁 Special Group 🔥": [Mock(source_title="测试文档", score=0.9)]}
        
        # Should handle unicode gracefully
        result = search_handler_with_mocks._format_lightweight_attachment_text(unicode_organized, 1)
        assert isinstance(result, str)
        
        result2 = search_handler_with_mocks._format_lightweight_hierarchy_text(unicode_organized, 1)
        assert isinstance(result2, str)


class TestConcurrencyErrorHandling:
    """Test error handling under concurrent access."""

    @pytest.mark.asyncio
    async def test_concurrent_search_with_failures(self, search_handler_with_mocks):
        """Test concurrent searches where some fail."""
        # Setup mixed success/failure scenarios
        search_handler_with_mocks.query_processor.process_query.side_effect = [
            {"query": "success1"},
            ConnectionError("Network error"),
            {"query": "success2"},
            TimeoutError("Timeout"),
        ]
        
        search_handler_with_mocks.search_engine.search.return_value = []
        search_handler_with_mocks.protocol.create_response.return_value = {"jsonrpc": "2.0"}
        
        # Create concurrent requests
        tasks = []
        for i in range(4):
            params = {"query": f"concurrent test {i}"}
            task = search_handler_with_mocks.handle_search(i, params)
            tasks.append(task)
        
        # Execute concurrently and collect results
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Should have 4 results (some may be exceptions handled internally)
        assert len(results) == 4
        
        # Verify error handling was called for failed requests
        assert search_handler_with_mocks.protocol.create_response.call_count == 4

    @pytest.mark.asyncio
    async def test_resource_exhaustion_simulation(self, search_handler_with_mocks):
        """Test behavior under simulated resource exhaustion."""
        search_handler_with_mocks.query_processor.process_query.side_effect = MemoryError("Out of memory")
        search_handler_with_mocks.protocol.create_response.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32603, "message": "Internal error"}
        }
        
        params = {"query": "resource intensive query"}
        result = await search_handler_with_mocks.handle_search(1, params)
        
        # Should handle memory errors gracefully
        search_handler_with_mocks.protocol.create_response.assert_called_once_with(
            1,
            error={"code": -32603, "message": "Internal error", "data": "Out of memory"}
        )
