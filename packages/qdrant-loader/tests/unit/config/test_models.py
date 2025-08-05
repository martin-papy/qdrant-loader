"""Tests for the config models module."""

from datetime import datetime, timezone

import pytest

from qdrant_loader.config.models import ParsedConfig, ProjectInfo, ProjectStats


class TestParsedConfig:
    """Test cases for ParsedConfig."""

    def test_get_all_projects(self):
        """Test the get_all_projects method."""
        # Create a mock projects_config with projects
        from unittest.mock import MagicMock
        
        mock_project1 = MagicMock()
        mock_project2 = MagicMock()
        
        # Create ParsedConfig instance with correct parameters
        mock_projects_config = MagicMock()
        mock_projects_config.projects = {
            "project1": mock_project1,
            "project2": mock_project2
        }
        
        config = ParsedConfig(
            global_config=MagicMock(),
            projects_config=mock_projects_config
        )
        
        # Test get_all_projects
        result = config.get_all_projects()
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert mock_project1 in result
        assert mock_project2 in result


class TestProjectStats:
    """Test cases for ProjectStats."""

    def test_serialize_last_updated_with_datetime(self):
        """Test last_updated serialization with datetime value."""
        test_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        stats = ProjectStats(
            project_id="test_project",
            document_count=10,
            source_count=2,
            last_updated=test_time
        )
        
        # Test the serializer method directly
        result = stats.serialize_last_updated(test_time)
        assert result == test_time.isoformat()

    def test_serialize_last_updated_with_none(self):
        """Test last_updated serialization with None value."""
        stats = ProjectStats(
            project_id="test_project"
        )
        
        # Test the serializer method directly with None
        result = stats.serialize_last_updated(None)
        assert result is None

    def test_model_dump_with_datetime_serialization(self):
        """Test model dumping with datetime serialization."""
        test_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        stats = ProjectStats(
            project_id="test_project",
            document_count=10,
            source_count=2,
            last_updated=test_time
        )
        
        # This should trigger the field serializer
        dumped = stats.model_dump()
        assert dumped["last_updated"] == test_time.isoformat()

    def test_model_dump_with_none_serialization(self):
        """Test model dumping with None last_updated."""
        stats = ProjectStats(
            project_id="test_project",
            document_count=10,
            source_count=2,
            last_updated=None
        )
        
        # This should trigger the field serializer with None
        dumped = stats.model_dump()
        assert dumped["last_updated"] is None


class TestProjectInfo:
    """Test cases for ProjectInfo."""

    def test_serialize_last_updated_with_datetime(self):
        """Test last_updated serialization with datetime value."""
        test_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        info = ProjectInfo(
            id="test_project",
            display_name="Test Project",
            collection_name="test_collection",
            last_updated=test_time
        )
        
        # Test the serializer method directly
        result = info.serialize_last_updated(test_time)
        assert result == test_time.isoformat()

    def test_serialize_last_updated_with_none(self):
        """Test last_updated serialization with None value."""
        info = ProjectInfo(
            id="test_project",
            display_name="Test Project", 
            collection_name="test_collection"
        )
        
        # Test the serializer method directly with None
        result = info.serialize_last_updated(None)
        assert result is None

    def test_model_dump_with_datetime_serialization(self):
        """Test model dumping with datetime serialization."""
        test_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        info = ProjectInfo(
            id="test_project",
            display_name="Test Project",
            collection_name="test_collection",
            last_updated=test_time
        )
        
        # This should trigger the field serializer
        dumped = info.model_dump()
        assert dumped["last_updated"] == test_time.isoformat()

    def test_model_dump_with_none_serialization(self):
        """Test model dumping with None last_updated."""
        info = ProjectInfo(
            id="test_project",
            display_name="Test Project",
            collection_name="test_collection",
            last_updated=None
        )
        
        # This should trigger the field serializer with None
        dumped = info.model_dump()
        assert dumped["last_updated"] is None

    def test_project_info_with_optional_fields(self):
        """Test ProjectInfo with all optional fields."""
        test_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        info = ProjectInfo(
            id="test_project",
            display_name="Test Project",
            description="A test project",
            collection_name="test_collection",
            source_count=5,
            document_count=100,
            last_updated=test_time
        )
        
        assert info.id == "test_project"
        assert info.display_name == "Test Project"
        assert info.description == "A test project"
        assert info.collection_name == "test_collection"
        assert info.source_count == 5
        assert info.document_count == 100
        assert info.last_updated == test_time