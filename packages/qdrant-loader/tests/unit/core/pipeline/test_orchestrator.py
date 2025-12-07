"""Tests for PipelineOrchestrator module."""

from typing import cast
from unittest.mock import AsyncMock, Mock, patch

import pytest
from qdrant_loader.config import Settings, SourcesConfig
from qdrant_loader.core.document import Document
from qdrant_loader.core.pipeline.document_pipeline import DocumentPipeline
from qdrant_loader.core.pipeline.orchestrator import (
    PipelineComponents,
    PipelineOrchestrator,
)
from qdrant_loader.core.pipeline.source_filter import SourceFilter
from qdrant_loader.core.pipeline.source_processor import SourceProcessor
from qdrant_loader.core.state.state_manager import StateManager


def make_rich_compatible_mock(*args, **kwargs):
    """Create a Mock that is compatible with Rich pretty-printing."""
    mock = Mock(*args, **kwargs)
    # Make the mock compatible with Rich's pretty-printing
    mock.__rich_repr__ = lambda: iter([])
    mock.__rich_console__ = lambda console, options: iter([])
    mock.__rich__ = lambda: ""
    return mock


class TestPipelineComponents:
    """Test PipelineComponents container."""

    def test_pipeline_components_initialization(self):
        """Test PipelineComponents initialization."""
        document_pipeline = Mock(spec=DocumentPipeline)
        source_processor = Mock(spec=SourceProcessor)
        source_filter = Mock(spec=SourceFilter)
        state_manager = Mock(spec=StateManager)

        components = PipelineComponents(
            document_pipeline=document_pipeline,
            source_processor=source_processor,
            source_filter=source_filter,
            state_manager=state_manager,
        )

        assert components.document_pipeline == document_pipeline
        assert components.source_processor == source_processor
        assert components.source_filter == source_filter
        assert components.state_manager == state_manager


class TestPipelineOrchestrator:
    """Test PipelineOrchestrator functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.settings = Mock(spec=Settings)
        # Create a mock sources config for testing purposes
        # In the new multi-project system, this would come from a project's sources
        self.mock_sources_config = Mock(spec=SourcesConfig)

        # Create mock components
        self.document_pipeline = AsyncMock(spec=DocumentPipeline)
        self.source_processor = AsyncMock(spec=SourceProcessor)
        self.source_filter = Mock(spec=SourceFilter)
        self.state_manager = AsyncMock(spec=StateManager)
        self.state_manager._initialized = False  # Add the _initialized attribute

        self.components = PipelineComponents(
            document_pipeline=self.document_pipeline,
            source_processor=self.source_processor,
            source_filter=self.source_filter,
            state_manager=self.state_manager,
        )

        self.orchestrator = PipelineOrchestrator(self.settings, self.components)

    def test_orchestrator_initialization(self):
        """Test PipelineOrchestrator initialization."""
        assert self.orchestrator.settings == self.settings
        assert self.orchestrator.components == self.components

    @pytest.mark.asyncio
    async def test_process_documents_success(self):
        """Test successful document processing."""
        # Setup mock documents
        mock_documents = cast(
            list[Document],
            [
                Mock(spec=Document, id="doc1"),
                Mock(spec=Document, id="doc2"),
            ],
        )

        # Setup mock filtered config
        filtered_config = Mock(spec=SourcesConfig)
        filtered_config.git = ["git_source"]
        filtered_config.confluence = None
        filtered_config.jira = None
        filtered_config.publicdocs = None
        filtered_config.localfile = None
        filtered_config.sharepoint = None

        # Setup mock pipeline result
        mock_result = Mock()
        mock_result.successfully_processed_documents = {"doc1", "doc2"}
        mock_result.success_count = 2

        # Configure mocks
        self.source_filter.filter_sources.return_value = filtered_config
        self.orchestrator._collect_documents_from_sources = AsyncMock(
            return_value=mock_documents
        )
        self.orchestrator._detect_document_changes = AsyncMock(
            return_value=mock_documents
        )
        self.document_pipeline.process_documents.return_value = mock_result
        self.orchestrator._update_document_states = AsyncMock()

        # Execute - pass sources_config parameter
        result = await self.orchestrator.process_documents(
            sources_config=self.mock_sources_config
        )

        # Verify
        assert result == mock_documents
        self.source_filter.filter_sources.assert_called_once_with(
            self.mock_sources_config, None, None
        )
        self.orchestrator._collect_documents_from_sources.assert_called_once_with(
            filtered_config, None
        )
        self.orchestrator._detect_document_changes.assert_called_once_with(
            mock_documents, filtered_config, None
        )
        self.document_pipeline.process_documents.assert_called_once_with(mock_documents)
        self.orchestrator._update_document_states.assert_called_once_with(
            mock_documents, {"doc1", "doc2"}, None
        )

    @pytest.mark.asyncio
    async def test_process_documents_with_custom_sources_config(self):
        """Test document processing with custom sources config."""
        custom_sources_config = Mock(spec=SourcesConfig)
        filtered_config = Mock(spec=SourcesConfig)
        mock_documents = [Mock(spec=Document, id="doc1")]

        # Setup mocks
        self.source_filter.filter_sources.return_value = filtered_config
        self.orchestrator._collect_documents_from_sources = AsyncMock(
            return_value=mock_documents
        )
        self.orchestrator._detect_document_changes = AsyncMock(
            return_value=mock_documents
        )

        mock_result = Mock()
        mock_result.successfully_processed_documents = {"doc1"}
        mock_result.success_count = 1
        self.document_pipeline.process_documents.return_value = mock_result
        self.orchestrator._update_document_states = AsyncMock()

        # Execute
        result = await self.orchestrator.process_documents(
            sources_config=custom_sources_config
        )

        # Verify
        assert result == mock_documents
        self.source_filter.filter_sources.assert_called_once_with(
            custom_sources_config, None, None
        )

    @pytest.mark.asyncio
    async def test_process_documents_with_source_filters(self):
        """Test document processing with source type and name filters."""
        filtered_config = Mock(spec=SourcesConfig)
        filtered_config.git = ["git_source"]
        filtered_config.confluence = None
        filtered_config.jira = None
        filtered_config.publicdocs = None
        filtered_config.localfile = None
        filtered_config.sharepoint = None

        mock_documents = [Mock(spec=Document, id="doc1")]

        # Setup mocks
        self.source_filter.filter_sources.return_value = filtered_config
        self.orchestrator._collect_documents_from_sources = AsyncMock(
            return_value=mock_documents
        )
        self.orchestrator._detect_document_changes = AsyncMock(
            return_value=mock_documents
        )

        mock_result = Mock()
        mock_result.successfully_processed_documents = {"doc1"}
        mock_result.success_count = 1
        self.document_pipeline.process_documents.return_value = mock_result
        self.orchestrator._update_document_states = AsyncMock()

        # Execute - pass sources_config parameter
        result = await self.orchestrator.process_documents(
            sources_config=self.mock_sources_config, source_type="git", source="my-repo"
        )

        # Verify
        assert result == mock_documents
        self.source_filter.filter_sources.assert_called_once_with(
            self.mock_sources_config, "git", "my-repo"
        )
        self.orchestrator._collect_documents_from_sources.assert_called_once_with(
            filtered_config, None
        )
        self.orchestrator._detect_document_changes.assert_called_once_with(
            mock_documents, filtered_config, None
        )
        self.document_pipeline.process_documents.assert_called_once_with(mock_documents)
        self.orchestrator._update_document_states.assert_called_once_with(
            mock_documents, {"doc1"}, None
        )

    @pytest.mark.asyncio
    async def test_process_documents_no_sources_found(self):
        """Test document processing when no sources are found for the specified type."""
        # Setup filtered config with no sources
        filtered_config = make_rich_compatible_mock(spec=SourcesConfig)
        filtered_config.git = None
        filtered_config.confluence = None
        filtered_config.jira = None
        filtered_config.publicdocs = None
        filtered_config.localfile = None
        filtered_config.sharepoint = None

        self.source_filter.filter_sources.return_value = filtered_config

        # Patch the logger to prevent Rich formatting issues during exception logging
        with patch("qdrant_loader.core.pipeline.orchestrator.logger"):
            # Execute and verify exception
            with pytest.raises(ValueError, match="No sources found for type 'git'"):
                await self.orchestrator.process_documents(
                    sources_config=self.mock_sources_config, source_type="git"
                )

    @pytest.mark.asyncio
    async def test_process_documents_no_documents_collected(self):
        """Test document processing when no documents are collected."""
        filtered_config = Mock(spec=SourcesConfig)
        filtered_config.git = ["git_source"]
        filtered_config.confluence = None
        filtered_config.jira = None
        filtered_config.publicdocs = None
        filtered_config.localfile = None
        filtered_config.sharepoint = None

        # Setup mocks
        self.source_filter.filter_sources.return_value = filtered_config
        self.orchestrator._collect_documents_from_sources = AsyncMock(return_value=[])

        # Execute
        result = await self.orchestrator.process_documents(
            sources_config=self.mock_sources_config
        )

        # Verify
        assert result == []
        self.orchestrator._collect_documents_from_sources.assert_called_once_with(
            filtered_config, None
        )

    @pytest.mark.asyncio
    async def test_process_documents_no_changes_detected(self):
        """Test document processing when no changes are detected."""
        mock_documents = [Mock(spec=Document, id="doc1")]
        filtered_config = Mock(spec=SourcesConfig)

        # Setup mocks
        self.source_filter.filter_sources.return_value = filtered_config
        self.orchestrator._collect_documents_from_sources = AsyncMock(
            return_value=mock_documents
        )
        self.orchestrator._detect_document_changes = AsyncMock(return_value=[])

        # Execute
        result = await self.orchestrator.process_documents(
            sources_config=self.mock_sources_config
        )

        # Verify
        assert result == []
        self.orchestrator._detect_document_changes.assert_called_once_with(
            mock_documents, filtered_config, None
        )

    @pytest.mark.asyncio
    async def test_process_documents_exception_handling(self):
        """Test document processing exception handling."""
        filtered_config = make_rich_compatible_mock(spec=SourcesConfig)
        self.source_filter.filter_sources.return_value = filtered_config
        self.orchestrator._collect_documents_from_sources = AsyncMock(
            side_effect=Exception("Collection failed")
        )

        # Patch the logger to prevent Rich formatting issues during exception logging
        with patch("qdrant_loader.core.pipeline.orchestrator.logger"):
            # Execute and verify exception
            with pytest.raises(Exception, match="Collection failed"):
                await self.orchestrator.process_documents(
                    sources_config=self.mock_sources_config
                )

    @pytest.mark.asyncio
    async def test_collect_documents_from_sources_all_types(self):
        """Test collecting documents from all source types."""
        # Setup filtered config with all source types
        filtered_config = Mock(spec=SourcesConfig)
        filtered_config.confluence = ["confluence_source"]
        filtered_config.git = ["git_source"]
        filtered_config.jira = ["jira_source"]
        filtered_config.publicdocs = ["publicdocs_source"]
        filtered_config.localfile = ["localfile_source"]
        filtered_config.sharepoint = None

        # Setup mock documents for each source type
        confluence_docs = [Mock(spec=Document, id="confluence_doc")]
        git_docs = [Mock(spec=Document, id="git_doc")]
        jira_docs = [Mock(spec=Document, id="jira_doc")]
        publicdocs_docs = [Mock(spec=Document, id="publicdocs_doc")]
        localfile_docs = [Mock(spec=Document, id="localfile_doc")]

        # Configure source processor mock
        self.source_processor.process_source_type.side_effect = [
            confluence_docs,
            git_docs,
            jira_docs,
            publicdocs_docs,
            localfile_docs,
        ]

        # Execute
        result = await self.orchestrator._collect_documents_from_sources(
            filtered_config, None
        )

        # Verify
        expected_docs = (
            confluence_docs + git_docs + jira_docs + publicdocs_docs + localfile_docs
        )
        assert result == expected_docs
        assert self.source_processor.process_source_type.call_count == 5

    @pytest.mark.asyncio
    async def test_collect_documents_from_sources_selective(self):
        """Test collecting documents from selective source types."""
        # Setup filtered config with only git and confluence
        filtered_config = Mock(spec=SourcesConfig)
        filtered_config.confluence = ["confluence_source"]
        filtered_config.git = ["git_source"]
        filtered_config.jira = None
        filtered_config.publicdocs = None
        filtered_config.localfile = None
        filtered_config.sharepoint = None

        # Setup mock documents
        confluence_docs = [Mock(spec=Document, id="confluence_doc")]
        git_docs = [Mock(spec=Document, id="git_doc")]

        self.source_processor.process_source_type.side_effect = [
            confluence_docs,
            git_docs,
        ]

        # Execute
        result = await self.orchestrator._collect_documents_from_sources(
            filtered_config, None
        )

        # Verify
        expected_docs = confluence_docs + git_docs
        assert result == expected_docs
        assert self.source_processor.process_source_type.call_count == 2

    @pytest.mark.asyncio
    async def test_collect_documents_from_sources_empty(self):
        """Test collecting documents when no sources are configured."""
        # Setup filtered config with no sources
        filtered_config = Mock(spec=SourcesConfig)
        filtered_config.confluence = None
        filtered_config.git = None
        filtered_config.jira = None
        filtered_config.publicdocs = None
        filtered_config.localfile = None
        filtered_config.sharepoint = None

        # Execute
        result = await self.orchestrator._collect_documents_from_sources(
            filtered_config, None
        )

        # Verify
        assert result == []
        self.source_processor.process_source_type.assert_not_called()

    @pytest.mark.asyncio
    async def test_detect_document_changes_success(self):
        """Test successful document change detection."""
        mock_documents = cast(
            list[Document],
            [
                Mock(spec=Document, id="doc1"),
                Mock(spec=Document, id="doc2"),
            ],
        )
        filtered_config = Mock(spec=SourcesConfig)

        # Setup state manager
        self.state_manager._initialized = False

        # Setup change detector mock
        mock_change_detector = AsyncMock()
        mock_changes = {
            "new": [mock_documents[0]],
            "updated": [mock_documents[1]],
            "deleted": [],
        }
        mock_change_detector.detect_changes.return_value = mock_changes

        with patch(
            "qdrant_loader.core.pipeline.orchestrator.StateChangeDetector"
        ) as mock_detector_class:
            mock_detector_class.return_value.__aenter__.return_value = (
                mock_change_detector
            )

            # Execute
            result = await self.orchestrator._detect_document_changes(
                mock_documents, filtered_config, None
            )

            # Verify
            assert result == mock_documents  # new + updated
            self.state_manager.initialize.assert_called_once()
            mock_change_detector.detect_changes.assert_called_once_with(
                mock_documents, filtered_config
            )

    @pytest.mark.asyncio
    async def test_detect_document_changes_empty_documents(self):
        """Test document change detection with empty document list."""
        result = await self.orchestrator._detect_document_changes([], Mock(), None)
        assert result == []

    @pytest.mark.asyncio
    async def test_detect_document_changes_state_manager_initialized(self):
        """Test document change detection when state manager is already initialized."""
        mock_documents = [Mock(spec=Document, id="doc1")]
        filtered_config = Mock(spec=SourcesConfig)

        # Setup state manager as already initialized
        self.state_manager._initialized = True

        # Setup change detector mock
        mock_change_detector = AsyncMock()
        mock_changes = {"new": mock_documents, "updated": [], "deleted": []}
        mock_change_detector.detect_changes.return_value = mock_changes

        with patch(
            "qdrant_loader.core.pipeline.orchestrator.StateChangeDetector"
        ) as mock_detector_class:
            mock_detector_class.return_value.__aenter__.return_value = (
                mock_change_detector
            )

            # Execute
            result = await self.orchestrator._detect_document_changes(mock_documents, filtered_config, None)  # type: ignore

            # Verify
            assert result == mock_documents
            self.state_manager.initialize.assert_not_called()

    @pytest.mark.asyncio
    async def test_detect_document_changes_exception_handling(self):
        """Test document change detection exception handling."""
        mock_documents = [make_rich_compatible_mock(spec=Document, id="doc1")]
        filtered_config = make_rich_compatible_mock(spec=SourcesConfig)

        self.state_manager._initialized = True

        with patch(
            "qdrant_loader.core.pipeline.orchestrator.StateChangeDetector"
        ) as mock_detector_class:
            mock_detector_class.return_value.__aenter__.side_effect = Exception(
                "Change detection failed"
            )

            # Patch the logger to prevent Rich formatting issues during exception logging
            with patch("qdrant_loader.core.pipeline.orchestrator.logger"):
                # Execute and verify exception
                with pytest.raises(Exception, match="Change detection failed"):
                    await self.orchestrator._detect_document_changes(mock_documents, filtered_config, None)  # type: ignore

    @pytest.mark.asyncio
    async def test_update_document_states_success(self):
        """Test successful document state updates."""
        mock_documents = cast(
            list[Document],
            [
                Mock(spec=Document, id="doc1"),
                Mock(spec=Document, id="doc2"),
                Mock(spec=Document, id="doc3"),
            ],
        )
        successfully_processed_doc_ids = {"doc1", "doc3"}

        # Setup state manager
        self.state_manager._initialized = False

        # Execute
        await self.orchestrator._update_document_states(
            mock_documents, successfully_processed_doc_ids, None
        )

        # Verify
        self.state_manager.initialize.assert_called_once()
        # Should update states for doc1 and doc3 only
        assert self.state_manager.update_document_state.call_count == 2
        updated_docs = [
            call.args[0]
            for call in self.state_manager.update_document_state.call_args_list
        ]
        updated_doc_ids = {doc.id for doc in updated_docs}
        assert updated_doc_ids == {"doc1", "doc3"}

    @pytest.mark.asyncio
    async def test_update_document_states_state_manager_initialized(self):
        """Test document state updates when state manager is already initialized."""
        mock_documents = [Mock(spec=Document, id="doc1")]
        successfully_processed_doc_ids = {"doc1"}

        # Setup state manager as already initialized
        self.state_manager._initialized = True

        # Execute
        await self.orchestrator._update_document_states(mock_documents, successfully_processed_doc_ids, None)  # type: ignore

        # Verify
        self.state_manager.initialize.assert_not_called()
        self.state_manager.update_document_state.assert_called_once_with(
            mock_documents[0], None
        )

    @pytest.mark.asyncio
    async def test_update_document_states_partial_failure(self):
        """Test document state updates with partial failures."""
        mock_documents = [
            Mock(spec=Document, id="doc1"),
            Mock(spec=Document, id="doc2"),
        ]
        successfully_processed_doc_ids = {"doc1", "doc2"}

        # Setup state manager
        self.state_manager._initialized = True

        # Configure one update to fail
        self.state_manager.update_document_state.side_effect = [
            None,  # Success for doc1
            Exception("Update failed for doc2"),  # Failure for doc2
        ]

        # Execute (should not raise exception)
        await self.orchestrator._update_document_states(mock_documents, successfully_processed_doc_ids, None)  # type: ignore

        # Verify both updates were attempted
        assert self.state_manager.update_document_state.call_count == 2

    @pytest.mark.asyncio
    async def test_update_document_states_empty_success_set(self):
        """Test document state updates with empty success set."""
        mock_documents = [Mock(spec=Document, id="doc1")]
        successfully_processed_doc_ids = set()

        # The state manager will be initialized during the call, so we need to expect that
        self.state_manager._initialized = False

        # Execute
        await self.orchestrator._update_document_states(mock_documents, successfully_processed_doc_ids, None)  # type: ignore

        # Verify no updates were attempted (but initialization was called)
        self.state_manager.update_document_state.assert_not_called()
        self.state_manager.initialize.assert_called_once()
