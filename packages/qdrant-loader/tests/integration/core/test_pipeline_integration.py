"""
Tests for pipeline integration with multi-project support.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import AnyUrl
from qdrant_loader.config import Settings
from qdrant_loader.config.global_config import GlobalConfig
from qdrant_loader.config.models import ProjectConfig, ProjectsConfig
from qdrant_loader.config.qdrant import QdrantConfig
from qdrant_loader.config.sources import SourcesConfig
from qdrant_loader.connectors.git.config import GitRepoConfig
from qdrant_loader.core.async_ingestion_pipeline import AsyncIngestionPipeline
from qdrant_loader.core.document import Document
from qdrant_loader.core.qdrant_manager import QdrantManager
from qdrant_loader.core.state.state_manager import StateManager


@pytest.fixture
def sample_multi_project_settings():
    """Create sample settings with multiple projects for testing."""
    # Create Git configurations for different projects
    git_config_1 = GitRepoConfig(
        source_type="git",
        source="repo-1",
        base_url=AnyUrl("https://github.com/test/repo1.git"),
        branch="main",
        token="test-token",
        temp_dir="/tmp/test1",
        file_types=["md", "py"],
    )

    git_config_2 = GitRepoConfig(
        source_type="git",
        source="repo-2",
        base_url=AnyUrl("https://github.com/test/repo2.git"),
        branch="main",
        token="test-token",
        temp_dir="/tmp/test2",
        file_types=["md", "py"],
    )

    # Create sources configurations for each project
    sources_config_1 = SourcesConfig()
    sources_config_1.git = {"repo-1": git_config_1}

    sources_config_2 = SourcesConfig()
    sources_config_2.git = {"repo-2": git_config_2}

    # Create project configurations
    project_config_1 = ProjectConfig(
        project_id="project-1",
        display_name="Project One",
        description="First test project",
        sources=sources_config_1,
    )

    project_config_2 = ProjectConfig(
        project_id="project-2",
        display_name="Project Two",
        description="Second test project",
        sources=sources_config_2,
    )

    # Create projects configuration
    projects_config = ProjectsConfig()
    projects_config.projects = {
        "project-1": project_config_1,
        "project-2": project_config_2,
    }

    # Create global configuration
    global_config = GlobalConfig()
    global_config.qdrant = QdrantConfig(
        url="http://localhost:6333",
        collection_name="global_collection",
        api_key=None,
    )

    # Create settings
    settings = Settings(
        global_config=global_config,
        projects_config=projects_config,
    )

    # Provide unified LLM configuration to avoid legacy deprecation warnings
    settings.global_config.llm = {
        "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "models": {"embeddings": "text-embedding-3-small", "chat": "gpt-4o"},
        "tokenizer": "cl100k_base",
        "embeddings": {"vector_size": 1536},
    }

    return settings


@pytest.fixture
def mock_qdrant_manager():
    """Create a mock QdrantManager for testing."""
    return MagicMock(spec=QdrantManager)


@pytest.fixture
def mock_state_manager():
    """Create a mock StateManager for testing."""
    mock_state_manager = MagicMock(spec=StateManager)
    mock_state_manager._initialized = True
    mock_state_manager._session_factory = MagicMock()
    return mock_state_manager


@pytest.mark.asyncio
async def test_pipeline_initialization_with_projects(
    sample_multi_project_settings, mock_qdrant_manager, mock_state_manager
):
    """Test that the pipeline initializes correctly with multi-project support."""
    # Create pipeline
    pipeline = AsyncIngestionPipeline(
        settings=sample_multi_project_settings,
        qdrant_manager=mock_qdrant_manager,
        state_manager=mock_state_manager,
        enable_metrics=False,
    )

    # Verify pipeline components are created
    assert pipeline.project_manager is not None
    assert pipeline.orchestrator is not None
    assert pipeline.orchestrator.project_manager is not None

    # Verify project manager has correct configuration
    assert len(pipeline.project_manager.projects_config.projects) == 2
    assert "project-1" in pipeline.project_manager.projects_config.projects
    assert "project-2" in pipeline.project_manager.projects_config.projects


@pytest.mark.asyncio
async def test_pipeline_accepts_string_metrics_dir(
    sample_multi_project_settings, mock_qdrant_manager, mock_state_manager, tmp_path
):
    """Ensure AsyncIngestionPipeline accepts metrics_dir as string and creates directory."""
    metrics_dir_str = str(tmp_path / "metrics-out")

    # Create pipeline with metrics_dir as string
    pipeline = AsyncIngestionPipeline(
        settings=sample_multi_project_settings,
        qdrant_manager=mock_qdrant_manager,
        state_manager=mock_state_manager,
        enable_metrics=False,
        metrics_dir=metrics_dir_str,
    )

    # Directory should be created on init
    from pathlib import Path

    assert Path(metrics_dir_str).exists()


@pytest.mark.asyncio
async def test_pipeline_project_specific_processing(
    sample_multi_project_settings, mock_qdrant_manager, mock_state_manager
):
    """Test processing documents for a specific project."""
    # Mock session for project manager initialization
    mock_session = AsyncMock()
    # Ensure sync SQLAlchemy APIs are mocked as sync to avoid RuntimeWarning
    mock_session.add = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    mock_session.commit = AsyncMock()

    mock_state_manager._session_factory.return_value.__aenter__.return_value = (
        mock_session
    )
    mock_state_manager._session_factory.return_value.__aexit__.return_value = None

    # Create pipeline
    pipeline = AsyncIngestionPipeline(
        settings=sample_multi_project_settings,
        qdrant_manager=mock_qdrant_manager,
        state_manager=mock_state_manager,
        enable_metrics=False,
    )

    # Mock the orchestrator's process_documents method
    mock_documents = [
        Document(
            id="doc-1",
            title="Test Document 1",
            content="Test content 1",
            content_type="text/plain",
            url="http://test.com/doc1",
            source_type="git",
            source="repo-1",
            metadata={"test": "metadata"},
        )
    ]

    with patch.object(
        pipeline.orchestrator, "process_documents", return_value=mock_documents
    ) as mock_process:
        # Process documents for a specific project
        result = await pipeline.process_documents(project_id="project-1")

        # Verify the orchestrator was called with correct parameters
        mock_process.assert_called_once_with(
            sources_config=None,
            source_type=None,
            source=None,
            project_id="project-1",
            force=False,
        )

        # Verify result
        assert len(result) == 1
        assert result[0].title == "Test Document 1"


@pytest.mark.asyncio
async def test_pipeline_all_projects_processing(
    sample_multi_project_settings, mock_qdrant_manager, mock_state_manager
):
    """Test processing documents for all projects."""
    # Mock session for project manager initialization
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    mock_session.commit = AsyncMock()

    mock_state_manager._session_factory.return_value.__aenter__.return_value = (
        mock_session
    )
    mock_state_manager._session_factory.return_value.__aexit__.return_value = None

    # Create pipeline
    pipeline = AsyncIngestionPipeline(
        settings=sample_multi_project_settings,
        qdrant_manager=mock_qdrant_manager,
        state_manager=mock_state_manager,
        enable_metrics=False,
    )

    # Mock the orchestrator's process_documents method to return different documents for each project
    def mock_process_documents(**kwargs):
        project_id = kwargs.get("project_id")
        if project_id == "project-1":
            return [
                Document(
                    id="doc-1",
                    title="Project 1 Document",
                    content="Project 1 content",
                    content_type="text/plain",
                    url="http://test.com/project1/doc1",
                    source_type="git",
                    source="repo-1",
                    metadata={"project": "1"},
                )
            ]
        elif project_id == "project-2":
            return [
                Document(
                    id="doc-2",
                    title="Project 2 Document",
                    content="Project 2 content",
                    content_type="text/plain",
                    url="http://test.com/project2/doc2",
                    source_type="git",
                    source="repo-2",
                    metadata={"project": "2"},
                )
            ]
        else:
            # This is the call for all projects
            return []

    with patch.object(
        pipeline.orchestrator, "process_documents", side_effect=mock_process_documents
    ) as mock_process:
        # Process documents for all projects (no project_id specified)
        await pipeline.process_documents()

        # Verify the orchestrator was called multiple times (once for each project)
        assert mock_process.call_count >= 1


@pytest.mark.asyncio
async def test_pipeline_project_metadata_injection(
    sample_multi_project_settings, mock_qdrant_manager, mock_state_manager
):
    """Test that project metadata is properly injected into documents."""
    # Mock session for project manager initialization
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    mock_session.commit = AsyncMock()

    mock_state_manager._session_factory.return_value.__aenter__.return_value = (
        mock_session
    )
    mock_state_manager._session_factory.return_value.__aexit__.return_value = None

    # Create pipeline
    pipeline = AsyncIngestionPipeline(
        settings=sample_multi_project_settings,
        qdrant_manager=mock_qdrant_manager,
        state_manager=mock_state_manager,
        enable_metrics=False,
    )

    # Initialize the pipeline to set up project manager
    await pipeline.initialize()

    # Test project metadata injection directly
    original_metadata = {"title": "Test Document", "author": "Test Author"}
    enhanced_metadata = pipeline.project_manager.inject_project_metadata(
        "project-1", original_metadata
    )

    # Verify project metadata was injected
    assert enhanced_metadata["title"] == "Test Document"
    assert enhanced_metadata["author"] == "Test Author"
    assert enhanced_metadata["project_id"] == "project-1"
    assert enhanced_metadata["project_name"] == "Project One"
    assert enhanced_metadata["project_description"] == "First test project"
    assert enhanced_metadata["collection_name"] == "global_collection"


@pytest.mark.asyncio
async def test_pipeline_project_validation(
    sample_multi_project_settings, mock_qdrant_manager, mock_state_manager
):
    """Test pipeline validation for project existence."""
    # Mock session for project manager initialization
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    mock_session.commit = AsyncMock()

    mock_state_manager._session_factory.return_value.__aenter__.return_value = (
        mock_session
    )
    mock_state_manager._session_factory.return_value.__aexit__.return_value = None

    # Create pipeline
    pipeline = AsyncIngestionPipeline(
        settings=sample_multi_project_settings,
        qdrant_manager=mock_qdrant_manager,
        state_manager=mock_state_manager,
        enable_metrics=False,
    )

    # Initialize the pipeline to set up project manager
    await pipeline.initialize()

    # Test project validation
    assert pipeline.project_manager.validate_project_exists("project-1") is True
    assert pipeline.project_manager.validate_project_exists("project-2") is True
    assert pipeline.project_manager.validate_project_exists("non-existent") is False


@pytest.mark.asyncio
async def test_pipeline_error_handling_invalid_project(
    sample_multi_project_settings, mock_qdrant_manager, mock_state_manager
):
    """Test pipeline error handling for invalid project ID."""
    # Mock session for project manager initialization
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    mock_session.commit = AsyncMock()

    mock_state_manager._session_factory.return_value.__aenter__.return_value = (
        mock_session
    )
    mock_state_manager._session_factory.return_value.__aexit__.return_value = None

    # Create pipeline
    pipeline = AsyncIngestionPipeline(
        settings=sample_multi_project_settings,
        qdrant_manager=mock_qdrant_manager,
        state_manager=mock_state_manager,
        enable_metrics=False,
    )

    # Test processing with invalid project ID should raise an error
    with pytest.raises(ValueError, match="Project 'invalid-project' not found"):
        await pipeline.process_documents(project_id="invalid-project")
