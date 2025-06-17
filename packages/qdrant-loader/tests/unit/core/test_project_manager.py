"""
Tests for the Project Manager component.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import AnyUrl
from qdrant_loader.config.models import ProjectConfig, ProjectsConfig
from qdrant_loader.config.sources import SourcesConfig
from qdrant_loader.connectors.git.config import GitRepoConfig
from qdrant_loader.core.project_manager import ProjectContext, ProjectManager
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def sample_projects_config():
    """Create a sample projects configuration for testing."""
    git_config = GitRepoConfig(
        source_type="git",
        source="test-repo",
        base_url=AnyUrl("https://github.com/test/repo.git"),
        branch="main",
        token="test-token",
        temp_dir="/tmp/test",
        file_types=["md", "py"],
    )

    sources_config = SourcesConfig()
    sources_config.git = {"test-repo": git_config}

    project_config = ProjectConfig(
        project_id="test-project",
        display_name="Test Project",
        description="A test project",
        sources=sources_config,
    )

    projects_config = ProjectsConfig()
    projects_config.projects = {"test-project": project_config}

    return projects_config


@pytest.fixture
def project_manager(sample_projects_config):
    """Create a project manager instance for testing."""
    return ProjectManager(
        projects_config=sample_projects_config,
        global_collection_name="global_collection",
    )


@pytest.mark.asyncio
async def test_project_manager_initialization(project_manager):
    """Test that project manager initializes correctly."""
    # Mock session
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    # Mock database query results - create a proper mock result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    # Initialize project manager
    await project_manager.initialize(mock_session)

    # Verify initialization
    assert project_manager._initialized is True
    assert len(project_manager._project_contexts) == 1
    assert "test-project" in project_manager._project_contexts


@pytest.mark.asyncio
async def test_project_context_creation(project_manager):
    """Test that project contexts are created correctly."""
    # Mock session
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    # Mock database query results - create a proper mock result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    # Initialize project manager
    await project_manager.initialize(mock_session)

    # Get project context
    context = project_manager.get_project_context("test-project")

    # Verify context
    assert context is not None
    assert context.project_id == "test-project"
    assert context.display_name == "Test Project"
    assert context.description == "A test project"
    assert context.collection_name == "global_collection"


def test_project_metadata_injection(project_manager):
    """Test that project metadata is injected correctly."""
    # Create a project context manually for testing
    context = ProjectContext(
        project_id="test-project",
        display_name="Test Project",
        description="A test project",
        collection_name="global_collection",  # Use global collection name
    )
    project_manager._project_contexts["test-project"] = context

    # Test metadata injection
    original_metadata = {"title": "Test Document", "author": "Test Author"}
    enhanced_metadata = project_manager.inject_project_metadata(
        "test-project", original_metadata
    )

    # Verify enhanced metadata
    assert enhanced_metadata["title"] == "Test Document"
    assert enhanced_metadata["author"] == "Test Author"
    assert enhanced_metadata["project_id"] == "test-project"
    assert enhanced_metadata["project_name"] == "Test Project"
    assert enhanced_metadata["project_description"] == "A test project"
    assert enhanced_metadata["collection_name"] == "global_collection"


def test_project_validation(project_manager):
    """Test project validation methods."""
    # Create a project context manually for testing
    context = ProjectContext(project_id="test-project", display_name="Test Project")
    project_manager._project_contexts["test-project"] = context

    # Test validation
    assert project_manager.validate_project_exists("test-project") is True
    assert project_manager.validate_project_exists("non-existent") is False


def test_project_collection_name_resolution(project_manager):
    """Test that collection names are resolved correctly."""
    # Create project contexts - all should use global collection name
    context1 = ProjectContext(
        project_id="project-1",
        display_name="Project 1",
        collection_name="global_collection",  # All projects use global collection
    )
    context2 = ProjectContext(
        project_id="project-2",
        display_name="Project 2",
        collection_name="global_collection",  # All projects use global collection
    )

    project_manager._project_contexts["project-1"] = context1
    project_manager._project_contexts["project-2"] = context2

    # Test collection name resolution - all should return global collection name
    assert (
        project_manager.get_project_collection_name("project-1") == "global_collection"
    )
    assert (
        project_manager.get_project_collection_name("project-2") == "global_collection"
    )
    assert project_manager.get_project_collection_name("non-existent") is None


def test_project_listing(project_manager):
    """Test project listing functionality."""
    # Create multiple project contexts
    context1 = ProjectContext(project_id="project-1", display_name="Project 1")
    context2 = ProjectContext(project_id="project-2", display_name="Project 2")

    project_manager._project_contexts["project-1"] = context1
    project_manager._project_contexts["project-2"] = context2

    # Test listing
    project_ids = project_manager.list_project_ids()
    assert len(project_ids) == 2
    assert "project-1" in project_ids
    assert "project-2" in project_ids

    # Test getting all contexts
    all_contexts = project_manager.get_all_project_contexts()
    assert len(all_contexts) == 2
    assert all_contexts["project-1"].display_name == "Project 1"
    assert all_contexts["project-2"].display_name == "Project 2"
