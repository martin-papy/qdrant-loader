"""Comprehensive tests for SearchHandler class to achieve 80%+ coverage."""

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
def search_handler(mock_search_engine, mock_query_processor, mock_protocol):
    """Create a SearchHandler instance for testing."""
    return SearchHandler(mock_search_engine, mock_query_processor, mock_protocol)


@pytest.fixture
def sample_search_results():
    """Create sample search results for testing."""
    result1 = Mock()
    result1.document_id = "doc1"
    result1.source_type = "confluence"
    result1.source_title = "Developer Guide"
    result1.text = "Complete developer documentation"
    result1.score = 0.95
    result1.depth = 0
    result1.parent_title = None
    result1.parent_id = None
    result1.children_count = 5
    result1.breadcrumb_text = ""
    result1.hierarchy_context = "Depth: 0 | Children: 5"
    result1.is_attachment = False
    result1.file_size = None
    result1.attachment_author = None
    result1.parent_document_title = None
    result1.original_filename = None
    result1.attachment_context = None
    result1.source_url = "https://docs.company.com/dev-guide"
    result1.file_path = None
    result1.repo_name = None
    result1.is_root_document = Mock(return_value=True)
    result1.has_children = Mock(return_value=True)
    result1.get_file_type = Mock(return_value=None)

    result2 = Mock()
    result2.document_id = "doc2"
    result2.source_type = "confluence"
    result2.source_title = "API Reference"
    result2.text = "API documentation and examples"
    result2.score = 0.88
    result2.depth = 1
    result2.parent_title = "Developer Guide"
    result2.parent_id = "dev-guide-123"
    result2.children_count = 0
    result2.breadcrumb_text = "Developer Guide > API Reference"
    result2.hierarchy_context = "Depth: 1 | Parent: Developer Guide"
    result2.is_attachment = False
    result2.file_size = None
    result2.attachment_author = None
    result2.parent_document_title = None
    result2.original_filename = None
    result2.attachment_context = None
    result2.source_url = "https://docs.company.com/api-ref"
    result2.file_path = None
    result2.repo_name = None
    result2.is_root_document = Mock(return_value=False)
    result2.has_children = Mock(return_value=False)
    result2.get_file_type = Mock(return_value=None)

    result3 = Mock()
    result3.document_id = "doc3"
    result3.source_type = "localfile"
    result3.source_title = "README.md"
    result3.text = "Project readme file"
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
    result3.original_filename = "README.md"
    result3.attachment_context = None
    result3.source_url = None
    result3.file_path = "project/docs/README.md"
    result3.repo_name = None
    result3.is_root_document = Mock(return_value=False)
    result3.has_children = Mock(return_value=False)
    result3.get_file_type = Mock(return_value=None)

    # PDF attachment result
    result4 = Mock()
    result4.document_id = "doc4"
    result4.source_type = "confluence"
    result4.source_title = "project-requirements.pdf"
    result4.text = "Project requirements and specifications document"
    result4.score = 0.82
    result4.depth = None
    result4.parent_title = None
    result4.parent_id = None
    result4.children_count = 0
    result4.breadcrumb_text = "Developer Guide > Project Planning"
    result4.hierarchy_context = None
    result4.is_attachment = True
    result4.file_size = 2097152  # 2MB
    result4.attachment_author = "project.manager@company.com"
    result4.parent_document_title = "Project Planning"
    result4.original_filename = "project-requirements.pdf"
    result4.attachment_context = "Requirements document for project planning phase"
    result4.source_url = "https://docs.company.com/attachments/project-req.pdf"
    result4.file_path = "/attachments/project-requirements.pdf"
    result4.repo_name = None
    result4.is_root_document = Mock(return_value=False)
    result4.has_children = Mock(return_value=False)
    result4.get_file_type = Mock(return_value="pdf")

    return [result1, result2, result3, result4]


class TestSearchHandlerInit:
    """Test SearchHandler initialization."""

    def test_init_creates_handler_with_components(self, mock_search_engine, mock_query_processor, mock_protocol):
        """Test that SearchHandler initializes correctly with all components."""
        handler = SearchHandler(mock_search_engine, mock_query_processor, mock_protocol)
        
        assert handler.search_engine == mock_search_engine
        assert handler.query_processor == mock_query_processor
        assert handler.protocol == mock_protocol
        assert handler.formatters is not None


class TestHandleSearch:
    """Test the main search functionality."""

    @pytest.mark.asyncio
    async def test_handle_search_success(self, search_handler, sample_search_results):
        """Test successful search request handling."""
        # Setup mocks
        search_handler.query_processor.process_query.return_value = {"query": "test query"}
        search_handler.search_engine.search.return_value = sample_search_results[:2]
        search_handler.protocol.create_response.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"content": [{"type": "text", "text": "Found 2 results"}]}
        }

        # Mock formatters
        with patch.object(search_handler.formatters, 'create_structured_search_results') as mock_structured:
            with patch.object(search_handler.formatters, 'format_search_result') as mock_format:
                mock_structured.return_value = []
                mock_format.return_value = "Formatted result"
                
                params = {
                    "query": "test query",
                    "source_types": ["confluence"],
                    "project_ids": ["proj1"],
                    "limit": 10
                }
                
                result = await search_handler.handle_search(1, params)
                
                # Verify calls
                search_handler.query_processor.process_query.assert_called_once_with("test query")
                search_handler.search_engine.search.assert_called_once_with(
                    query="test query",
                    source_types=["confluence"],
                    project_ids=["proj1"],
                    limit=10
                )
                search_handler.protocol.create_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_search_missing_query(self, search_handler):
        """Test search request with missing query parameter."""
        search_handler.protocol.create_response.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32602, "message": "Invalid params"}
        }
        
        params = {"source_types": ["confluence"]}
        
        result = await search_handler.handle_search(1, params)
        
        # Verify error response
        search_handler.protocol.create_response.assert_called_once_with(
            1,
            error={
                "code": -32602,
                "message": "Invalid params",
                "data": "Missing required parameter: query",
            }
        )

    @pytest.mark.asyncio
    async def test_handle_search_with_defaults(self, search_handler, sample_search_results):
        """Test search request with default parameters."""
        search_handler.query_processor.process_query.return_value = {"query": "test"}
        search_handler.search_engine.search.return_value = sample_search_results[:1]
        search_handler.protocol.create_response.return_value = {"jsonrpc": "2.0", "id": 1}

        with patch.object(search_handler.formatters, 'create_structured_search_results'):
            with patch.object(search_handler.formatters, 'format_search_result'):
                params = {"query": "test"}
                
                await search_handler.handle_search(1, params)
                
                # Verify defaults were used
                search_handler.search_engine.search.assert_called_once_with(
                    query="test",
                    source_types=[],
                    project_ids=[],
                    limit=10
                )

    @pytest.mark.asyncio
    async def test_handle_search_exception(self, search_handler):
        """Test search request that raises an exception."""
        search_handler.query_processor.process_query.side_effect = Exception("Test error")
        search_handler.protocol.create_response.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32603, "message": "Internal error"}
        }
        
        params = {"query": "test"}
        
        result = await search_handler.handle_search(1, params)
        
        # Verify error response
        search_handler.protocol.create_response.assert_called_once_with(
            1,
            error={"code": -32603, "message": "Internal error", "data": "Test error"}
        )


class TestHandleHierarchySearch:
    """Test hierarchical search functionality."""

    @pytest.mark.asyncio
    async def test_handle_hierarchy_search_success(self, search_handler, sample_search_results):
        """Test successful hierarchy search request."""
        search_handler.query_processor.process_query.return_value = {"query": "test query"}
        search_handler.search_engine.search.return_value = sample_search_results
        search_handler.protocol.create_response.return_value = {"jsonrpc": "2.0", "id": 1}

        with patch.object(search_handler.formatters, 'create_lightweight_hierarchy_results'):
            params = {
                "query": "test query",
                "hierarchy_filter": {"depth": 0},
                "organize_by_hierarchy": True,
                "limit": 10
            }
            
            result = await search_handler.handle_hierarchy_search(1, params)
            
            # Verify search was called with confluence and localfile types
            search_handler.search_engine.search.assert_called_once_with(
                query="test query",
                source_types=["confluence", "localfile"],
                limit=40  # max(limit * 2, 40) = max(10 * 2, 40) = max(20, 40) = 40
            )

    @pytest.mark.asyncio
    async def test_handle_hierarchy_search_missing_query(self, search_handler):
        """Test hierarchy search with missing query parameter."""
        search_handler.protocol.create_response.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32602, "message": "Invalid params"}
        }
        
        params = {"hierarchy_filter": {"depth": 0}}
        
        result = await search_handler.handle_hierarchy_search(1, params)
        
        search_handler.protocol.create_response.assert_called_once_with(
            1,
            error={
                "code": -32602,
                "message": "Invalid params",
                "data": "Missing required parameter: query",
            }
        )

    @pytest.mark.asyncio
    async def test_handle_hierarchy_search_with_defaults(self, search_handler, sample_search_results):
        """Test hierarchy search with default parameters."""
        search_handler.query_processor.process_query.return_value = {"query": "test"}
        search_handler.search_engine.search.return_value = sample_search_results
        search_handler.protocol.create_response.return_value = {"jsonrpc": "2.0", "id": 1}

        with patch.object(search_handler.formatters, 'create_lightweight_hierarchy_results'):
            params = {"query": "test"}
            
            await search_handler.handle_hierarchy_search(1, params)
            
            # Verify defaults were used
            search_handler.search_engine.search.assert_called_once_with(
                query="test",
                source_types=["confluence", "localfile"],
                limit=40
            )


class TestHandleAttachmentSearch:
    """Test attachment search functionality."""

    @pytest.mark.asyncio
    async def test_handle_attachment_search_success(self, search_handler, sample_search_results):
        """Test successful attachment search request."""
        search_handler.query_processor.process_query.return_value = {"query": "test query"}
        search_handler.search_engine.search.return_value = sample_search_results
        search_handler.protocol.create_response.return_value = {"jsonrpc": "2.0", "id": 1}

        with patch.object(search_handler.formatters, 'create_lightweight_attachment_results'):
            with patch.object(search_handler.formatters, '_organize_attachments_by_type') as mock_organize:
                mock_organize.return_value = [{"group_name": "PDF Files", "document_ids": ["doc4"]}]
                
                params = {
                    "query": "test query",
                    "attachment_filter": {"file_type": "pdf"},
                    "include_parent_context": True,
                    "limit": 10
                }
                
                result = await search_handler.handle_attachment_search(1, params)
                
                # Verify search was called
                search_handler.search_engine.search.assert_called_once_with(
                    query="test query",
                    source_types=None,  # Search all sources
                    limit=20  # limit * 2
                )

    @pytest.mark.asyncio
    async def test_handle_attachment_search_missing_query(self, search_handler):
        """Test attachment search with missing query parameter."""
        search_handler.protocol.create_response.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32602, "message": "Invalid params"}
        }
        
        params = {"attachment_filter": {"file_type": "pdf"}}
        
        result = await search_handler.handle_attachment_search(1, params)
        
        search_handler.protocol.create_response.assert_called_once_with(
            1,
            error={
                "code": -32602,
                "message": "Invalid params",
                "data": "Missing required parameter: query",
            }
        )


class TestHandleExpandDocument:
    """Test document expansion functionality."""

    @pytest.mark.asyncio
    async def test_handle_expand_document_success(self, search_handler, sample_search_results):
        """Test successful document expansion."""
        target_result = sample_search_results[0]
        search_handler.search_engine.search.return_value = [target_result]
        search_handler.protocol.create_response.return_value = {"jsonrpc": "2.0", "id": 1}

        with patch.object(search_handler.formatters, 'format_search_result') as mock_format:
            with patch.object(search_handler.formatters, 'create_structured_search_results') as mock_structured:
                mock_format.return_value = "Formatted result"
                mock_structured.return_value = []
                
                params = {"document_id": "doc1"}
                
                result = await search_handler.handle_expand_document(1, params)
                
                # Verify search was called with document_id field search
                search_handler.search_engine.search.assert_called_with(
                    query="document_id:doc1",
                    limit=10
                )

    @pytest.mark.asyncio
    async def test_handle_expand_document_not_found(self, search_handler):
        """Test document expansion when document is not found."""
        search_handler.search_engine.search.return_value = []
        search_handler.protocol.create_response.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32604, "message": "Document not found"}
        }
        
        params = {"document_id": "nonexistent"}
        
        result = await search_handler.handle_expand_document(1, params)
        
        search_handler.protocol.create_response.assert_called_once_with(
            1,
            error={
                "code": -32604,
                "message": "Document not found",
                "data": "No document found with ID: nonexistent",
            }
        )

    @pytest.mark.asyncio
    async def test_handle_expand_document_missing_id(self, search_handler):
        """Test document expansion with missing document_id parameter."""
        search_handler.protocol.create_response.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32602, "message": "Invalid params"}
        }
        
        params = {}
        
        result = await search_handler.handle_expand_document(1, params)
        
        search_handler.protocol.create_response.assert_called_once_with(
            1,
            error={
                "code": -32602,
                "message": "Invalid params",
                "data": "Missing required parameter: document_id",
            }
        )

    @pytest.mark.asyncio
    async def test_handle_expand_document_fallback_search(self, search_handler, sample_search_results):
        """Test document expansion with fallback to general search."""
        target_result = sample_search_results[0]
        
        # First search returns no exact matches, second search returns the document
        search_handler.search_engine.search.side_effect = [[], [target_result]]
        search_handler.protocol.create_response.return_value = {"jsonrpc": "2.0", "id": 1}

        with patch.object(search_handler.formatters, 'format_search_result'):
            with patch.object(search_handler.formatters, 'create_structured_search_results'):
                params = {"document_id": "doc1"}
                
                result = await search_handler.handle_expand_document(1, params)
                
                # Verify both searches were called
                assert search_handler.search_engine.search.call_count == 2


class TestHierarchyFilters:
    """Test hierarchy filtering methods."""

    def test_apply_hierarchy_filters_depth(self, search_handler, sample_search_results):
        """Test filtering by depth."""
        hierarchy_filter = {"depth": 0}
        filtered = search_handler._apply_hierarchy_filters(sample_search_results, hierarchy_filter)
        
        # Should return confluence results with depth 0
        confluence_depth_0 = [r for r in filtered if r.depth == 0]
        assert len(confluence_depth_0) == 1
        assert confluence_depth_0[0].source_title == "Developer Guide"

    def test_apply_hierarchy_filters_localfile_depth(self, search_handler, sample_search_results):
        """Test filtering localfiles by folder depth."""
        # Create a localfile with specific folder structure
        localfile_result = Mock()
        localfile_result.source_type = "localfile"
        localfile_result.file_path = "project/docs/README.md"  # depth 1 (2 folders - 1)
        
        hierarchy_filter = {"depth": 1}
        filtered = search_handler._apply_hierarchy_filters([localfile_result], hierarchy_filter)
        
        assert len(filtered) == 1
        assert filtered[0].source_type == "localfile"

    def test_apply_hierarchy_filters_parent_title(self, search_handler, sample_search_results):
        """Test filtering by parent title."""
        hierarchy_filter = {"parent_title": "Developer Guide"}
        filtered = search_handler._apply_hierarchy_filters(sample_search_results, hierarchy_filter)
        
        # Should return confluence results with "Developer Guide" as parent
        parent_matches = [r for r in filtered if getattr(r, 'parent_title', None) == "Developer Guide"]
        assert len(parent_matches) == 1
        assert parent_matches[0].source_title == "API Reference"

    def test_apply_hierarchy_filters_root_only(self, search_handler, sample_search_results):
        """Test filtering for root documents only."""
        hierarchy_filter = {"root_only": True}
        filtered = search_handler._apply_hierarchy_filters(sample_search_results, hierarchy_filter)
        
        # Should return confluence root documents
        root_docs = [r for r in filtered if r.is_root_document()]
        assert len(root_docs) == 1
        assert root_docs[0].source_title == "Developer Guide"

    def test_apply_hierarchy_filters_has_children(self, search_handler, sample_search_results):
        """Test filtering for documents with children."""
        hierarchy_filter = {"has_children": True}
        filtered = search_handler._apply_hierarchy_filters(sample_search_results, hierarchy_filter)
        
        # Should return confluence documents with children
        docs_with_children = [r for r in filtered if r.has_children()]
        assert len(docs_with_children) == 1
        assert docs_with_children[0].source_title == "Developer Guide"

    def test_organize_by_hierarchy(self, search_handler, sample_search_results):
        """Test organizing results by hierarchy."""
        confluence_results = [r for r in sample_search_results if r.source_type in ["confluence", "localfile"]]
        organized = search_handler._organize_by_hierarchy(confluence_results)
        
        # Should have groups based on root/breadcrumb
        assert len(organized) >= 1
        assert "Developer Guide" in organized or "project" in organized


class TestAttachmentFilters:
    """Test attachment filtering methods."""

    def test_apply_lightweight_attachment_filters_basic(self, search_handler, sample_search_results):
        """Test basic attachment filtering."""
        attachment_filter = {}
        filtered = search_handler._apply_lightweight_attachment_filters(sample_search_results, attachment_filter)
        
        # Should return attachments and files with extensions
        attachment_results = [r for r in filtered if r.is_attachment or r.original_filename]
        assert len(attachment_results) >= 1

    def test_apply_lightweight_attachment_filters_file_type(self, search_handler, sample_search_results):
        """Test filtering by file type."""
        attachment_filter = {"file_type": "pdf"}
        
        with patch.object(search_handler.formatters, '_extract_file_type_minimal') as mock_extract:
            mock_extract.return_value = "pdf"
            filtered = search_handler._apply_lightweight_attachment_filters(sample_search_results, attachment_filter)
            
            # Should call file type extraction
            assert mock_extract.called

    def test_apply_lightweight_attachment_filters_file_size(self, search_handler, sample_search_results):
        """Test filtering by file size."""
        attachment_filter = {"file_size_min": 1000000, "file_size_max": 3000000}
        filtered = search_handler._apply_lightweight_attachment_filters(sample_search_results, attachment_filter)
        
        # Should filter by size for results that have file_size
        for result in filtered:
            if result.file_size:
                assert 1000000 <= result.file_size <= 3000000


class TestFormattingMethods:
    """Test text formatting methods."""

    def test_format_lightweight_attachment_text_empty(self, search_handler):
        """Test formatting attachment text with no results."""
        result = search_handler._format_lightweight_attachment_text({}, 0)
        
        assert "Found 0 attachments" in result
        assert "Use the structured data below" in result

    def test_format_lightweight_attachment_text_with_results(self, search_handler, sample_search_results):
        """Test formatting attachment text with results."""
        organized_results = {"PDF Files": sample_search_results[:2]}
        
        with patch.object(search_handler.formatters, '_extract_safe_filename') as mock_filename:
            with patch.object(search_handler.formatters, '_extract_file_type_minimal') as mock_type:
                mock_filename.return_value = "test.pdf"
                mock_type.return_value = "pdf"
                
                result = search_handler._format_lightweight_attachment_text(organized_results, 2)
                
                assert "2 attachments" in result
                assert "PDF Files" in result
                assert "Usage:" in result

    def test_format_lightweight_hierarchy_text_empty(self, search_handler):
        """Test formatting hierarchy text with no results."""
        result = search_handler._format_lightweight_hierarchy_text({}, 0)
        
        assert "Found 0 documents" in result
        assert "Use the structured data below" in result

    def test_format_lightweight_hierarchy_text_with_results(self, search_handler, sample_search_results):
        """Test formatting hierarchy text with results."""
        organized_results = {"Developer Guide": sample_search_results[:2]}
        
        with patch.object(search_handler.formatters, '_generate_clean_group_name') as mock_clean:
            mock_clean.return_value = "Developer Guide"
            
            result = search_handler._format_lightweight_hierarchy_text(organized_results, 2)
            
            assert "2 documents" in result
            assert "Developer Guide" in result
            assert "Usage:" in result


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_search_with_none_request_id(self, search_handler, sample_search_results):
        """Test search with None request ID."""
        search_handler.query_processor.process_query.return_value = {"query": "test"}
        search_handler.search_engine.search.return_value = sample_search_results[:1]
        search_handler.protocol.create_response.return_value = {"jsonrpc": "2.0", "id": None}

        with patch.object(search_handler.formatters, 'create_structured_search_results'):
            with patch.object(search_handler.formatters, 'format_search_result'):
                params = {"query": "test"}
                
                result = await search_handler.handle_search(None, params)
                
                # Should handle None request ID
                search_handler.protocol.create_response.assert_called_once()

    def test_hierarchy_filters_with_empty_results(self, search_handler):
        """Test hierarchy filters with empty results list."""
        hierarchy_filter = {"depth": 0}
        filtered = search_handler._apply_hierarchy_filters([], hierarchy_filter)
        
        assert filtered == []

    def test_organize_hierarchy_with_empty_results(self, search_handler):
        """Test organize hierarchy with empty results list."""
        organized = search_handler._organize_by_hierarchy([])
        
        assert organized == {}

    def test_attachment_filters_with_none_values(self, search_handler, sample_search_results):
        """Test attachment filters with None values in filter."""
        attachment_filter = {"file_type": None, "file_size_min": None}
        
        # Should not crash with None values
        filtered = search_handler._apply_lightweight_attachment_filters(sample_search_results, attachment_filter)
        
        # Should return some results
        assert isinstance(filtered, list)
