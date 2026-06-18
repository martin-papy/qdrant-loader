"""Tests for connector → document checkpoint propagation and resume/skip behaviour.

These are regression tests for the WS-2 checkpoint feature, covering:
  1. __ingestion_checkpoint is propagated from JiraIssue to the issue Document.
  2. Attachment documents do NOT inherit the checkpoint.
  3. When the orchestrator resumes, the saved cursor_value is passed to the
     connector factory as checkpoint_cursor.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import HttpUrl
from qdrant_loader.config.types import SourceType
from qdrant_loader.connectors.jira.cloud_connector import JiraCloudConnector
from qdrant_loader.connectors.jira.config import JiraDeploymentType, JiraProjectConfig
from qdrant_loader.connectors.jira.models import (
    JiraAttachment,
    JiraIssue,
    JiraUser,
)
from qdrant_loader.core.document import Document

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def jira_config():
    return JiraProjectConfig(
        base_url=HttpUrl("https://test.atlassian.net"),
        deployment_type=JiraDeploymentType.CLOUD,
        project_key="TEST",
        source="test-jira",
        source_type=SourceType.JIRA,
        requests_per_minute=60,
        page_size=50,
        token="test-token",
        email="test@example.com",
        download_attachments=False,
    )


def _make_issue(issue_id: str = "10001", key: str = "TEST-1") -> JiraIssue:
    reporter = JiraUser(
        account_id="u1", display_name="Alice", email_address="alice@example.com"
    )
    return JiraIssue(
        id=issue_id,
        key=key,
        summary="Test Issue",
        description="Some description",
        issue_type="Bug",
        status="Open",
        priority="High",
        project_key="TEST",
        created=datetime(2024, 1, 1, tzinfo=UTC),
        updated=datetime(2024, 1, 2, tzinfo=UTC),
        reporter=reporter,
    )


# ---------------------------------------------------------------------------
# 1. Checkpoint propagation: issue → document
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_checkpoint_propagated_to_issue_document(jira_config):
    """__ingestion_checkpoint on a JiraIssue must appear in the produced Document's metadata."""
    connector = JiraCloudConnector(jira_config)

    issue = _make_issue()
    issue.ingestion_checkpoint = {
        "cursor_kind": "page_token",
        "cursor_value": "tok-page-2",
        "batch_index": 0,
    }

    docs: list[Document] = []
    async for doc in connector._stream_issues_to_documents(
        [issue], include_attachments=False
    ):
        docs.append(doc)

    assert len(docs) == 1
    cp = docs[0].metadata.get("__ingestion_checkpoint")
    assert cp is not None, "Issue document must carry __ingestion_checkpoint"
    assert cp["cursor_value"] == "tok-page-2"
    assert cp["cursor_kind"] == "page_token"


@pytest.mark.asyncio
async def test_no_checkpoint_when_issue_has_none(jira_config):
    """When an issue has no ingestion_checkpoint, the document must not have the key."""
    connector = JiraCloudConnector(jira_config)

    issue = _make_issue()
    # No ingestion_checkpoint set

    docs: list[Document] = []
    async for doc in connector._stream_issues_to_documents(
        [issue], include_attachments=False
    ):
        docs.append(doc)

    assert len(docs) == 1
    assert "__ingestion_checkpoint" not in docs[0].metadata


@pytest.mark.asyncio
async def test_checkpoint_not_on_attachment_documents(jira_config):
    """Attachment documents must NOT inherit __ingestion_checkpoint from the parent issue."""
    config_with_attachments = JiraProjectConfig(
        base_url=HttpUrl("https://test.atlassian.net"),
        deployment_type=JiraDeploymentType.CLOUD,
        project_key="TEST",
        source="test-jira",
        source_type=SourceType.JIRA,
        requests_per_minute=60,
        page_size=50,
        token="test-token",
        email="test@example.com",
        download_attachments=True,
    )

    connector = JiraCloudConnector(config_with_attachments)

    reporter = JiraUser(
        account_id="u1", display_name="Alice", email_address="alice@example.com"
    )
    issue = _make_issue()
    issue.ingestion_checkpoint = {
        "cursor_kind": "page_token",
        "cursor_value": "tok-page-2",
        "batch_index": 0,
    }
    att = JiraAttachment(
        id="att1",
        filename="report.txt",
        size=100,
        mime_type="text/plain",
        content_url=HttpUrl("https://test.atlassian.net/attachments/report.txt"),
        created=datetime(2024, 1, 1, tzinfo=UTC),
        author=reporter,
    )
    issue.attachments = [att]

    # Mock the attachment_reader so we can control what attachment documents look like
    att_doc = Document(
        id="att1",
        content="attachment content",
        content_type="text",
        source="test-jira",
        source_type=SourceType.JIRA,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        url="https://test.atlassian.net/attachments/report.txt",
        title="report.txt",
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        is_deleted=False,
        metadata={},  # No checkpoint in attachment doc
    )

    mock_reader = AsyncMock()
    mock_reader.fetch_and_process = AsyncMock(return_value=[att_doc])
    connector.attachment_reader = mock_reader

    docs: list[Document] = []
    async for doc in connector._stream_issues_to_documents(
        [issue], include_attachments=True
    ):
        docs.append(doc)

    assert len(docs) == 2, "Expected 1 issue doc + 1 attachment doc"
    issue_doc, attachment_doc = docs[0], docs[1]

    # Issue document has checkpoint
    assert issue_doc.metadata.get("__ingestion_checkpoint") is not None

    # Attachment document does NOT have checkpoint
    assert "__ingestion_checkpoint" not in (
        attachment_doc.metadata or {}
    ), "Attachment documents must not carry __ingestion_checkpoint"


# ---------------------------------------------------------------------------
# 2. Resume: saved cursor is passed to the connector factory
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resume_cursor_passed_to_connector_factory():
    """When a checkpoint exists for a source, _stream_batches_from_sources must
    pass its cursor_value as checkpoint_cursor to the connector factory."""
    from qdrant_loader.config import Settings, SourcesConfig
    from qdrant_loader.core.pipeline.document_pipeline import DocumentPipeline
    from qdrant_loader.core.pipeline.orchestrator import (
        PipelineComponents,
        PipelineOrchestrator,
    )
    from qdrant_loader.core.pipeline.source_filter import SourceFilter
    from qdrant_loader.core.pipeline.source_processor import SourceProcessor
    from qdrant_loader.core.qdrant_manager import QdrantManager
    from qdrant_loader.core.state.state_manager import StateManager

    settings = Mock(spec=Settings)
    state_manager = AsyncMock(spec=StateManager)
    state_manager._initialized = True

    # Checkpoint manager returns a saved cursor for the Jira source
    saved_cursor = "tok-saved"
    mock_cp = Mock(cursor_value=saved_cursor)
    cp_mgr = AsyncMock()
    cp_mgr.get_checkpoint = AsyncMock(return_value=mock_cp)

    session = object()
    session_ctx = Mock()
    session_ctx.__aenter__ = AsyncMock(return_value=session)
    session_ctx.__aexit__ = AsyncMock(return_value=None)
    state_manager.get_session = AsyncMock(return_value=session_ctx)

    source_processor = AsyncMock(spec=SourceProcessor)
    received_cursors: list = []

    async def fake_stream(source_configs, connector_factory, source_type, since=None):
        # Materialise the connector to capture what cursor was passed
        for _, src_cfg in source_configs.items():
            connector = await connector_factory(src_cfg)
            received_cursors.append(getattr(connector, "_checkpoint_cursor", None))
        if False:
            yield  # make it a generator

    source_processor.stream_source_documents = fake_stream

    src_cfg = Mock()
    src_cfg.source = "jira-main"
    filtered_config = Mock(spec=SourcesConfig)
    filtered_config.confluence = None
    filtered_config.git = None
    filtered_config.jira = {"jira-main": src_cfg}
    filtered_config.publicdocs = None
    filtered_config.localfile = None

    components = PipelineComponents(
        document_pipeline=AsyncMock(spec=DocumentPipeline),
        source_processor=source_processor,
        source_filter=Mock(spec=SourceFilter),
        state_manager=state_manager,
        qdrant_manager=AsyncMock(spec=QdrantManager),
    )
    orchestrator = PipelineOrchestrator(settings, components)

    # Patch CheckpointManager and get_connector_instance
    mock_connector = Mock()
    mock_connector._checkpoint_cursor = saved_cursor

    with (
        patch(
            # Lazy import inside connector_factory_with_checkpoint; patch at source
            "qdrant_loader.core.state.checkpoint_manager.CheckpointManager",
            return_value=cp_mgr,
        ),
        patch(
            "qdrant_loader.core.pipeline.orchestrator.get_connector_instance",
            return_value=mock_connector,
        ) as mock_factory,
    ):
        async for _ in orchestrator._stream_batches_from_sources(
            filtered_config,
            batch_size=256,
            since=None,
            project_id="project-1",
            resume=True,
        ):
            pass

    # The factory must have been called with checkpoint_cursor=saved_cursor
    mock_factory.assert_called_once()
    _, call_kwargs = mock_factory.call_args
    assert (
        call_kwargs.get("checkpoint_cursor") == saved_cursor
    ), "get_connector_instance must receive the saved checkpoint cursor on resume"
