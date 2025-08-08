"""Tests for CLI project commands to improve coverage."""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from qdrant_loader.cli.project_commands import (
    _get_project_document_count,
    _get_project_latest_ingestion
)


class TestProjectCommandsCoverage:
    """Test cases for project commands to improve coverage."""

    @pytest.mark.asyncio
    async def test_get_project_document_count_success(self):
        """Test successful document count retrieval - covers lines 49, 54, 55."""
        # Mock state manager and session
        mock_state_manager = Mock()
        mock_session = AsyncMock()
        mock_state_manager._session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_state_manager._session_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Mock the query result
        mock_result = Mock()
        mock_result.scalar.return_value = 42
        mock_session.execute.return_value = mock_result
        
        # Call the function - this should cover lines 49, 54, 55
        count = await _get_project_document_count(mock_state_manager, "test_project")
        
        # Verify the result
        assert count == 42
        
        # Verify the session was used correctly
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_project_document_count_scalar_none(self):
        """Test document count when scalar returns None - covers lines 49, 54, 55."""
        # Mock state manager and session
        mock_state_manager = Mock()
        mock_session = AsyncMock()
        mock_state_manager._session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_state_manager._session_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Mock the query result with None scalar
        mock_result = Mock()
        mock_result.scalar.return_value = None  # This triggers "or 0" on line 54
        mock_session.execute.return_value = mock_result
        
        # Call the function - this should cover lines 49, 54, 55
        count = await _get_project_document_count(mock_state_manager, "test_project")
        
        # Verify the fallback to 0
        assert count == 0

    @pytest.mark.asyncio
    async def test_get_project_document_count_exception(self):
        """Test document count with database exception - covers exception handling."""
        # Mock state manager that raises an exception
        mock_state_manager = Mock()
        mock_state_manager._session_factory.side_effect = Exception("Database error")
        
        # Call the function - this should trigger the exception handler and return 0
        count = await _get_project_document_count(mock_state_manager, "test_project")
        
        # Verify graceful degradation
        assert count == 0

    @pytest.mark.asyncio
    async def test_get_project_latest_ingestion_success(self):
        """Test successful ingestion timestamp retrieval - covers lines 65, 71, 72."""
        # Mock state manager and session
        mock_state_manager = Mock()
        mock_session = AsyncMock()
        mock_state_manager._session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_state_manager._session_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Mock the query result with a datetime
        test_datetime = datetime(2023, 1, 1, 12, 0, 0)
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = test_datetime
        mock_session.execute.return_value = mock_result
        
        # Call the function - this should cover lines 65, 71, 72
        timestamp = await _get_project_latest_ingestion(mock_state_manager, "test_project")
        
        # Verify the result is ISO formatted
        assert timestamp == test_datetime.isoformat()
        
        # Verify the session was used correctly
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_project_latest_ingestion_none_result(self):
        """Test ingestion timestamp when no result found - covers lines 65, 71, 72."""
        # Mock state manager and session
        mock_state_manager = Mock()
        mock_session = AsyncMock()
        mock_state_manager._session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_state_manager._session_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Mock the query result with None (no records found)
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None  # This triggers line 72 condition
        mock_session.execute.return_value = mock_result
        
        # Call the function - this should cover lines 65, 71, 72
        timestamp = await _get_project_latest_ingestion(mock_state_manager, "test_project")
        
        # Verify None is returned when no timestamp found
        assert timestamp is None

    @pytest.mark.asyncio
    async def test_get_project_latest_ingestion_exception(self):
        """Test ingestion timestamp with database exception - covers exception handling."""
        # Mock state manager that raises an exception
        mock_state_manager = Mock()
        mock_state_manager._session_factory.side_effect = Exception("Database error")
        
        # Call the function - this should trigger the exception handler and return None
        timestamp = await _get_project_latest_ingestion(mock_state_manager, "test_project")
        
        # Verify graceful degradation
        assert timestamp is None

    @pytest.mark.asyncio
    async def test_get_project_document_count_session_execute_exception(self):
        """Test document count when session.execute raises exception."""
        # Mock state manager and session
        mock_state_manager = Mock()
        mock_session = AsyncMock()
        mock_state_manager._session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_state_manager._session_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Make session.execute raise an exception
        mock_session.execute.side_effect = Exception("Query failed")
        
        # Call the function - this should trigger exception handling
        count = await _get_project_document_count(mock_state_manager, "test_project")
        
        # Verify graceful degradation
        assert count == 0

    @pytest.mark.asyncio
    async def test_get_project_latest_ingestion_session_execute_exception(self):
        """Test ingestion timestamp when session.execute raises exception."""
        # Mock state manager and session
        mock_state_manager = Mock()
        mock_session = AsyncMock()
        mock_state_manager._session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_state_manager._session_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Make session.execute raise an exception
        mock_session.execute.side_effect = Exception("Query failed")
        
        # Call the function - this should trigger exception handling
        timestamp = await _get_project_latest_ingestion(mock_state_manager, "test_project")
        
        # Verify graceful degradation
        assert timestamp is None