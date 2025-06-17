"""Tests for configuration models."""

from datetime import datetime

import pytest
from qdrant_loader.config.models import (
    ProjectConfig,
    ProjectContext,
    ProjectDetail,
    ProjectInfo,
    ProjectsConfig,
    ProjectStats,
)
from qdrant_loader.config.sources import SourcesConfig


class TestProjectContext:
    """Tests for ProjectContext dataclass."""

    def test_valid_project_context(self):
        """Test creating a valid project context."""
        context = ProjectContext(
            project_id="test-project",
            display_name="Test Project",
            description="A test project",
            collection_name="test_collection",
            config_overrides={"chunking": {"chunk_size": 1000}},
        )

        assert context.project_id == "test-project"
        assert context.display_name == "Test Project"
        assert context.description == "A test project"
        assert context.collection_name == "test_collection"
        assert context.config_overrides["chunking"]["chunk_size"] == 1000

    def test_project_context_validation(self):
        """Test project context validation."""
        # Empty project_id should raise ValueError
        with pytest.raises(ValueError, match="project_id cannot be empty"):
            ProjectContext(
                project_id="",
                display_name="Test",
                description=None,
                collection_name="test",
                config_overrides={},
            )

        # Empty display_name should raise ValueError
        with pytest.raises(ValueError, match="display_name cannot be empty"):
            ProjectContext(
                project_id="test",
                display_name="",
                description=None,
                collection_name="test",
                config_overrides={},
            )

        # Empty collection_name should raise ValueError
        with pytest.raises(ValueError, match="collection_name cannot be empty"):
            ProjectContext(
                project_id="test",
                display_name="Test",
                description=None,
                collection_name="",
                config_overrides={},
            )


class TestProjectConfig:
    """Tests for ProjectConfig model."""

    def test_valid_project_config(self):
        """Test creating a valid project configuration."""
        config = ProjectConfig(
            project_id="test-project",
            display_name="Test Project",
            description="A test project",
            overrides={"chunking": {"chunk_size": 1000}},
        )

        assert config.project_id == "test-project"
        assert config.display_name == "Test Project"
        assert config.description == "A test project"
        assert isinstance(config.sources, SourcesConfig)
        assert config.overrides["chunking"]["chunk_size"] == 1000

    def test_get_effective_collection_name(self):
        """Test collection name resolution logic."""
        # Test that all projects use the global collection name
        config = ProjectConfig(
            project_id="test-project",
            display_name="Test Project",
            description="A test project",
        )
        assert config.get_effective_collection_name("documents") == "documents"

        # Test default project (backward compatibility)
        config = ProjectConfig(
            project_id="default",
            display_name="Default Project",
            description="Default project description",
        )
        assert config.get_effective_collection_name("documents") == "documents"

        # Test regular project - now also uses global collection name
        config = ProjectConfig(
            project_id="my-project",
            display_name="My Project",
            description="My project description",
        )
        assert config.get_effective_collection_name("documents") == "documents"


class TestProjectsConfig:
    """Tests for ProjectsConfig model."""

    def test_empty_projects_config(self):
        """Test creating empty projects configuration."""
        config = ProjectsConfig()
        assert len(config.projects) == 0
        assert config.list_project_ids() == []
        assert config.get_project("nonexistent") is None

    def test_add_project(self):
        """Test adding projects to configuration."""
        config = ProjectsConfig()

        project = ProjectConfig(
            project_id="test-project",
            display_name="Test Project",
            description="A test project",
        )

        config.add_project(project)
        assert len(config.projects) == 1
        assert "test-project" in config.list_project_ids()
        assert config.get_project("test-project") == project

    def test_duplicate_project_id(self):
        """Test that duplicate project IDs are rejected."""
        config = ProjectsConfig()

        project1 = ProjectConfig(
            project_id="test-project",
            display_name="Test Project 1",
            description="First test project",
        )

        project2 = ProjectConfig(
            project_id="test-project",
            display_name="Test Project 2",
            description="Second test project",
        )

        config.add_project(project1)

        with pytest.raises(ValueError, match="Project 'test-project' already exists"):
            config.add_project(project2)

    def test_to_dict(self):
        """Test converting projects config to dictionary."""
        config = ProjectsConfig()

        project = ProjectConfig(
            project_id="test-project",
            display_name="Test Project",
            description="A test project",
        )

        config.add_project(project)

        result = config.to_dict()
        assert "test-project" in result
        assert result["test-project"]["project_id"] == "test-project"
        assert result["test-project"]["display_name"] == "Test Project"
        assert result["test-project"]["description"] == "A test project"


class TestProjectStats:
    """Tests for ProjectStats model."""

    def test_project_stats(self):
        """Test creating project statistics."""
        now = datetime.now()
        stats = ProjectStats(
            project_id="test-project",
            document_count=100,
            source_count=3,
            last_updated=now,
            storage_size=1024000,
        )

        assert stats.project_id == "test-project"
        assert stats.document_count == 100
        assert stats.source_count == 3
        assert stats.last_updated == now
        assert stats.storage_size == 1024000

    def test_project_stats_defaults(self):
        """Test project statistics with default values."""
        stats = ProjectStats(
            project_id="test-project", last_updated=None, storage_size=None
        )

        assert stats.project_id == "test-project"
        assert stats.document_count == 0
        assert stats.source_count == 0
        assert stats.last_updated is None
        assert stats.storage_size is None


class TestProjectInfo:
    """Tests for ProjectInfo model."""

    def test_project_info(self):
        """Test creating project information."""
        now = datetime.now()
        info = ProjectInfo(
            id="test-project",
            display_name="Test Project",
            description="A test project",
            collection_name="test_collection",
            source_count=3,
            document_count=100,
            last_updated=now,
        )

        assert info.id == "test-project"
        assert info.display_name == "Test Project"
        assert info.description == "A test project"
        assert info.collection_name == "test_collection"
        assert info.source_count == 3
        assert info.document_count == 100
        assert info.last_updated == now


class TestProjectDetail:
    """Tests for ProjectDetail model."""

    def test_project_detail(self):
        """Test creating detailed project information."""
        now = datetime.now()
        sources = [
            {"type": "git", "name": "repo1", "status": "completed"},
            {"type": "confluence", "name": "space1", "status": "completed"},
        ]

        statistics = {
            "total_documents": 100,
            "total_chunks": 500,
            "storage_size": "10MB",
        }

        detail = ProjectDetail(
            id="test-project",
            display_name="Test Project",
            description="A test project",
            collection_name="test_collection",
            source_count=2,
            document_count=100,
            last_updated=now,
            sources=sources,
            statistics=statistics,
        )

        assert detail.id == "test-project"
        assert detail.display_name == "Test Project"
        assert len(detail.sources) == 2
        assert detail.sources[0]["type"] == "git"
        assert detail.statistics["total_documents"] == 100
