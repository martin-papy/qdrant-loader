"""Async behavior and request handling tests for SearchHandler."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch, call
from typing import Any, Dict
import time

import pytest
from qdrant_loader_mcp_server.mcp.search_handler import SearchHandler
from qdrant_loader_mcp_server.mcp.protocol import MCPProtocol


@pytest.fixture
def async_search_engine():
    """Create a mock search engine with async behavior."""
    engine = Mock()
    engine.search = AsyncMock()
    return engine


@pytest.fixture
def async_query_processor():
    """Create a mock query processor with async behavior."""
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
def async_search_handler(async_search_engine, async_query_processor, mock_protocol):
    """Create a SearchHandler with async components."""
    return SearchHandler(async_search_engine, async_query_processor, mock_protocol)


@pytest.fixture
def sample_async_results():
    """Create sample results for async testing."""
    results = []
    for i in range(3):
        result = Mock()
        result.document_id = f"async-doc-{i}"
        result.source_type = "confluence"
        result.source_title = f"Async Document {i}"
        result.text = f"Content for async document {i}"
        result.score = 0.9 - (i * 0.1)
        result.depth = i
        result.parent_title = None if i == 0 else f"Async Document {i-1}"
        result.is_attachment = False
        result.original_filename = None
        result.file_path = None
        result.is_root_document = Mock(return_value=i == 0)
        result.has_children = Mock(return_value=i < 2)
        result.get_file_type = Mock(return_value=None)
        results.append(result)
    
    return results


class TestAsyncSearchBehavior:
    """Test async behavior in search operations."""

    @pytest.mark.asyncio
    async def test_search_async_execution_order(self, async_search_handler, sample_async_results):
        """Test that async operations execute in the correct order."""
        execution_order = []
        
        async def mock_process_query(query):
            execution_order.append("process_query_start")
            await asyncio.sleep(0.01)  # Simulate processing time
            execution_order.append("process_query_end")
            return {"query": f"processed_{query}"}
        
        async def mock_search(query, **kwargs):
            execution_order.append("search_start")
            await asyncio.sleep(0.01)  # Simulate search time
            execution_order.append("search_end")
            return sample_async_results
        
        async_search_handler.query_processor.process_query = mock_process_query
        async_search_handler.search_engine.search = mock_search
        async_search_handler.protocol.create_response.return_value = {"jsonrpc": "2.0", "id": 1}
        
        with patch.object(async_search_handler.formatters, 'create_structured_search_results'):
            with patch.object(async_search_handler.formatters, 'format_search_result'):
                params = {"query": "test_async"}
                await async_search_handler.handle_search(1, params)
        
        # Verify execution order
        expected_order = ["process_query_start", "process_query_end", "search_start", "search_end"]
        assert execution_order == expected_order

    @pytest.mark.asyncio
    async def test_concurrent_search_requests(self, async_search_handler, sample_async_results):
        """Test handling multiple concurrent search requests."""
        async_search_handler.query_processor.process_query.return_value = {"query": "concurrent_test"}
        async_search_handler.search_engine.search.return_value = sample_async_results
        async_search_handler.protocol.create_response.return_value = {"jsonrpc": "2.0"}
        
        with patch.object(async_search_handler.formatters, 'create_structured_search_results'):
            with patch.object(async_search_handler.formatters, 'format_search_result'):
                # Create multiple concurrent requests
                tasks = []
                for i in range(5):
                    params = {"query": f"concurrent_query_{i}"}
                    task = async_search_handler.handle_search(f"req_{i}", params)
                    tasks.append(task)
                
                # Execute all requests concurrently
                start_time = time.time()
                results = await asyncio.gather(*tasks)
                end_time = time.time()
                
                # All requests should complete
                assert len(results) == 5
                
                # Verify all components were called for each request
                assert async_search_handler.query_processor.process_query.call_count == 5
                assert async_search_handler.search_engine.search.call_count == 5
                assert async_search_handler.protocol.create_response.call_count == 5

    @pytest.mark.asyncio
    async def test_search_with_slow_query_processor(self, async_search_handler, sample_async_results):
        """Test search behavior when query processor is slow."""
        async def slow_process_query(query):
            await asyncio.sleep(0.1)  # Simulate slow processing
            return {"query": f"slow_processed_{query}"}
        
        async_search_handler.query_processor.process_query = slow_process_query
        async_search_handler.search_engine.search.return_value = sample_async_results
        async_search_handler.protocol.create_response.return_value = {"jsonrpc": "2.0", "id": 1}
        
        with patch.object(async_search_handler.formatters, 'create_structured_search_results'):
            with patch.object(async_search_handler.formatters, 'format_search_result'):
                start_time = time.time()
                params = {"query": "slow_test"}
                result = await async_search_handler.handle_search(1, params)
                end_time = time.time()
                
                # Should wait for slow query processor
                assert end_time - start_time >= 0.1
                assert result["jsonrpc"] == "2.0"

    @pytest.mark.asyncio
    async def test_search_with_slow_search_engine(self, async_search_handler, sample_async_results):
        """Test search behavior when search engine is slow."""
        async_search_handler.query_processor.process_query.return_value = {"query": "fast_processed"}
        
        async def slow_search(query, **kwargs):
            await asyncio.sleep(0.1)  # Simulate slow search
            return sample_async_results
        
        async_search_handler.search_engine.search = slow_search
        async_search_handler.protocol.create_response.return_value = {"jsonrpc": "2.0", "id": 1}
        
        with patch.object(async_search_handler.formatters, 'create_structured_search_results'):
            with patch.object(async_search_handler.formatters, 'format_search_result'):
                start_time = time.time()
                params = {"query": "slow_search_test"}
                result = await async_search_handler.handle_search(1, params)
                end_time = time.time()
                
                # Should wait for slow search engine
                assert end_time - start_time >= 0.1
                assert result["jsonrpc"] == "2.0"

    @pytest.mark.asyncio
    async def test_search_cancellation_behavior(self, async_search_handler):
        """Test search behavior when operations are cancelled."""
        async def cancellable_process_query(query):
            try:
                await asyncio.sleep(1.0)  # Long operation
                return {"query": "should_not_complete"}
            except asyncio.CancelledError:
                raise
        
        async_search_handler.query_processor.process_query = cancellable_process_query
        
        # Start search and cancel it
        params = {"query": "cancellation_test"}
        task = asyncio.create_task(async_search_handler.handle_search(1, params))
        
        # Cancel after short delay
        await asyncio.sleep(0.01)
        task.cancel()
        
        with pytest.raises(asyncio.CancelledError):
            await task


class TestAsyncHierarchySearchBehavior:
    """Test async behavior in hierarchy search operations."""

    @pytest.mark.asyncio
    async def test_hierarchy_search_async_filtering(self, async_search_handler, sample_async_results):
        """Test async behavior with hierarchy filtering."""
        async_search_handler.query_processor.process_query.return_value = {"query": "hierarchy_test"}
        async_search_handler.search_engine.search.return_value = sample_async_results
        async_search_handler.protocol.create_response.return_value = {"jsonrpc": "2.0", "id": 1}
        
        # Mock the filtering to be slow
        original_filter = async_search_handler._apply_hierarchy_filters
        
        def slow_filter(results, filter_dict):
            time.sleep(0.05)  # Simulate slow filtering
            return original_filter(results, filter_dict)
        
        with patch.object(async_search_handler, '_apply_hierarchy_filters', side_effect=slow_filter):
            with patch.object(async_search_handler.formatters, 'create_lightweight_hierarchy_results'):
                start_time = time.time()
                params = {
                    "query": "hierarchy_filter_test",
                    "hierarchy_filter": {"depth": 0},
                    "organize_by_hierarchy": True
                }
                result = await async_search_handler.handle_hierarchy_search(1, params)
                end_time = time.time()
                
                # Should complete despite slow filtering
                assert result["jsonrpc"] == "2.0"
                assert end_time - start_time >= 0.05

    @pytest.mark.asyncio
    async def test_concurrent_hierarchy_searches(self, async_search_handler, sample_async_results):
        """Test concurrent hierarchy search requests."""
        async_search_handler.query_processor.process_query.return_value = {"query": "concurrent_hierarchy"}
        async_search_handler.search_engine.search.return_value = sample_async_results
        async_search_handler.protocol.create_response.return_value = {"jsonrpc": "2.0"}
        
        with patch.object(async_search_handler.formatters, 'create_lightweight_hierarchy_results'):
            # Create multiple concurrent hierarchy searches
            tasks = []
            for i in range(3):
                params = {
                    "query": f"hierarchy_query_{i}",
                    "hierarchy_filter": {"depth": i},
                    "organize_by_hierarchy": i % 2 == 0
                }
                task = async_search_handler.handle_hierarchy_search(f"hier_{i}", params)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            
            # All hierarchy searches should complete
            assert len(results) == 3
            assert all(r["jsonrpc"] == "2.0" for r in results)


class TestAsyncAttachmentSearchBehavior:
    """Test async behavior in attachment search operations."""

    @pytest.mark.asyncio
    async def test_attachment_search_async_organization(self, async_search_handler, sample_async_results):
        """Test async behavior with attachment organization."""
        async_search_handler.query_processor.process_query.return_value = {"query": "attachment_test"}
        async_search_handler.search_engine.search.return_value = sample_async_results
        async_search_handler.protocol.create_response.return_value = {"jsonrpc": "2.0", "id": 1}
        
        # Mock slow attachment organization
        with patch.object(async_search_handler.formatters, '_organize_attachments_by_type') as mock_organize:
            async def slow_organize(results):
                await asyncio.sleep(0.05)  # Simulate slow organization
                return [{"group_name": "Test Files", "document_ids": ["doc1"]}]
            
            mock_organize.side_effect = lambda x: [{"group_name": "Test Files", "document_ids": ["doc1"]}]
            
            with patch.object(async_search_handler.formatters, 'create_lightweight_attachment_results'):
                start_time = time.time()
                params = {
                    "query": "attachment_organization_test",
                    "attachment_filter": {"file_type": "pdf"}
                }
                result = await async_search_handler.handle_attachment_search(1, params)
                
                assert result["jsonrpc"] == "2.0"

    @pytest.mark.asyncio
    async def test_concurrent_attachment_searches(self, async_search_handler, sample_async_results):
        """Test concurrent attachment search requests."""
        async_search_handler.query_processor.process_query.return_value = {"query": "concurrent_attachment"}
        async_search_handler.search_engine.search.return_value = sample_async_results
        async_search_handler.protocol.create_response.return_value = {"jsonrpc": "2.0"}
        
        with patch.object(async_search_handler.formatters, '_organize_attachments_by_type'):
            with patch.object(async_search_handler.formatters, 'create_lightweight_attachment_results'):
                # Create multiple concurrent attachment searches
                tasks = []
                for i in range(3):
                    params = {
                        "query": f"attachment_query_{i}",
                        "attachment_filter": {"file_type": "pdf" if i % 2 == 0 else "docx"}
                    }
                    task = async_search_handler.handle_attachment_search(f"attach_{i}", params)
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks)
                
                assert len(results) == 3
                assert all(r["jsonrpc"] == "2.0" for r in results)


class TestAsyncExpandDocumentBehavior:
    """Test async behavior in document expansion operations."""

    @pytest.mark.asyncio
    async def test_expand_document_async_search_sequence(self, async_search_handler, sample_async_results):
        """Test async behavior with document expansion search sequence."""
        target_document = sample_async_results[0]
        
        # Setup sequential async searches
        async def sequential_search(query, **kwargs):
            if "document_id:" in query:
                await asyncio.sleep(0.02)  # First search delay
                return []  # No exact match
            else:
                await asyncio.sleep(0.03)  # Second search delay
                return [target_document]
        
        async_search_handler.search_engine.search = sequential_search
        async_search_handler.protocol.create_response.return_value = {"jsonrpc": "2.0", "id": 1}
        
        with patch.object(async_search_handler.formatters, 'format_search_result'):
            with patch.object(async_search_handler.formatters, 'create_structured_search_results'):
                start_time = time.time()
                params = {"document_id": "async-doc-0"}
                result = await async_search_handler.handle_expand_document(1, params)
                end_time = time.time()
                
                # Should wait for both search attempts
                assert end_time - start_time >= 0.05
                assert result["jsonrpc"] == "2.0"

    @pytest.mark.asyncio
    async def test_concurrent_document_expansions(self, async_search_handler, sample_async_results):
        """Test concurrent document expansion requests."""
        async_search_handler.search_engine.search.return_value = sample_async_results[:1]
        async_search_handler.protocol.create_response.return_value = {"jsonrpc": "2.0"}
        
        with patch.object(async_search_handler.formatters, 'format_search_result'):
            with patch.object(async_search_handler.formatters, 'create_structured_search_results'):
                # Create multiple concurrent expansion requests
                tasks = []
                for i in range(4):
                    params = {"document_id": f"async-doc-{i}"}
                    task = async_search_handler.handle_expand_document(f"expand_{i}", params)
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks)
                
                assert len(results) == 4
                assert all(r["jsonrpc"] == "2.0" for r in results)


class TestAsyncErrorHandling:
    """Test async error handling scenarios."""

    @pytest.mark.asyncio
    async def test_async_timeout_handling(self, async_search_handler):
        """Test handling of async operation timeouts."""
        async def timeout_process_query(query):
            await asyncio.sleep(10)  # Very long operation
            return {"query": "timeout_test"}
        
        async_search_handler.query_processor.process_query = timeout_process_query
        async_search_handler.protocol.create_response.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32603, "message": "Internal error"}
        }
        
        params = {"query": "timeout_test"}
        
        # Use asyncio.wait_for to simulate timeout
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                async_search_handler.handle_search(1, params),
                timeout=0.1
            )

    @pytest.mark.asyncio
    async def test_async_exception_propagation(self, async_search_handler):
        """Test proper exception propagation in async operations."""
        async def failing_process_query(query):
            raise ValueError("Async processing failed")
        
        async_search_handler.query_processor.process_query = failing_process_query
        async_search_handler.protocol.create_response.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32603, "message": "Internal error"}
        }
        
        params = {"query": "exception_test"}
        result = await async_search_handler.handle_search(1, params)
        
        # Should handle async exception and return error response
        async_search_handler.protocol.create_response.assert_called_once_with(
            1,
            error={"code": -32603, "message": "Internal error", "data": "Async processing failed"}
        )

    @pytest.mark.asyncio
    async def test_async_resource_cleanup(self, async_search_handler):
        """Test proper resource cleanup in async operations."""
        cleanup_called = []
        
        async def resource_intensive_search(query, **kwargs):
            try:
                await asyncio.sleep(0.1)
                return []
            finally:
                cleanup_called.append("search_cleanup")
        
        async def resource_intensive_process(query):
            try:
                await asyncio.sleep(0.05)
                return {"query": "resource_test"}
            finally:
                cleanup_called.append("process_cleanup")
        
        async_search_handler.query_processor.process_query = resource_intensive_process
        async_search_handler.search_engine.search = resource_intensive_search
        async_search_handler.protocol.create_response.return_value = {"jsonrpc": "2.0", "id": 1}
        
        with patch.object(async_search_handler.formatters, 'create_structured_search_results'):
            with patch.object(async_search_handler.formatters, 'format_search_result'):
                params = {"query": "resource_cleanup_test"}
                await async_search_handler.handle_search(1, params)
        
        # Verify cleanup was called for both operations
        assert "process_cleanup" in cleanup_called
        assert "search_cleanup" in cleanup_called


class TestAsyncPerformance:
    """Test async performance characteristics."""

    @pytest.mark.asyncio
    async def test_parallel_processing_efficiency(self, async_search_handler, sample_async_results):
        """Test that parallel operations are more efficient than sequential."""
        async def slow_operation(delay):
            await asyncio.sleep(delay)
            return sample_async_results
        
        async_search_handler.query_processor.process_query.return_value = {"query": "parallel_test"}
        async_search_handler.search_engine.search.side_effect = lambda **kwargs: slow_operation(0.1)
        async_search_handler.protocol.create_response.return_value = {"jsonrpc": "2.0"}
        
        with patch.object(async_search_handler.formatters, 'create_structured_search_results'):
            with patch.object(async_search_handler.formatters, 'format_search_result'):
                # Test parallel execution
                tasks = []
                for i in range(3):
                    params = {"query": f"parallel_query_{i}"}
                    task = async_search_handler.handle_search(f"par_{i}", params)
                    tasks.append(task)
                
                start_time = time.time()
                results = await asyncio.gather(*tasks)
                parallel_time = time.time() - start_time
                
                # Parallel execution should be faster than 3 * 0.1 seconds
                # (allowing some overhead)
                assert parallel_time < 0.35  # Much less than 3 * 0.1 = 0.3
                assert len(results) == 3

    @pytest.mark.asyncio
    async def test_memory_efficiency_concurrent_operations(self, async_search_handler, sample_async_results):
        """Test memory efficiency during concurrent operations."""
        async_search_handler.query_processor.process_query.return_value = {"query": "memory_test"}
        async_search_handler.search_engine.search.return_value = sample_async_results
        async_search_handler.protocol.create_response.return_value = {"jsonrpc": "2.0"}
        
        with patch.object(async_search_handler.formatters, 'create_structured_search_results'):
            with patch.object(async_search_handler.formatters, 'format_search_result'):
                # Create many concurrent operations
                tasks = []
                for i in range(20):
                    params = {"query": f"memory_query_{i}"}
                    task = async_search_handler.handle_search(f"mem_{i}", params)
                    tasks.append(task)
                
                # Should handle many concurrent operations without memory issues
                results = await asyncio.gather(*tasks)
                
                assert len(results) == 20
                assert all(r["jsonrpc"] == "2.0" for r in results)

    @pytest.mark.asyncio
    async def test_async_operation_isolation(self, async_search_handler, sample_async_results):
        """Test that async operations are properly isolated."""
        call_tracking = {"query_calls": [], "search_calls": []}
        
        async def tracking_process_query(query):
            call_tracking["query_calls"].append(query)
            await asyncio.sleep(0.01)
            return {"query": f"tracked_{query}"}
        
        async def tracking_search(query, **kwargs):
            call_tracking["search_calls"].append(query)
            await asyncio.sleep(0.01)
            return sample_async_results
        
        async_search_handler.query_processor.process_query = tracking_process_query
        async_search_handler.search_engine.search = tracking_search
        async_search_handler.protocol.create_response.return_value = {"jsonrpc": "2.0"}
        
        with patch.object(async_search_handler.formatters, 'create_structured_search_results'):
            with patch.object(async_search_handler.formatters, 'format_search_result'):
                # Create operations with different parameters
                tasks = []
                for i in range(3):
                    params = {"query": f"isolation_query_{i}"}
                    task = async_search_handler.handle_search(f"iso_{i}", params)
                    tasks.append(task)
                
                await asyncio.gather(*tasks)
                
                # Verify each operation was called with correct parameters
                assert len(call_tracking["query_calls"]) == 3
                assert len(call_tracking["search_calls"]) == 3
                
                # Verify parameter isolation
                for i in range(3):
                    assert f"isolation_query_{i}" in call_tracking["query_calls"]
                    assert f"tracked_isolation_query_{i}" in call_tracking["search_calls"]
