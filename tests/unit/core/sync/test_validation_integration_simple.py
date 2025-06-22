"""Simplified tests for ValidationIntegrationManager - Phase 4 coverage improvement.

Targets sync/validation_integration.py: 142 lines, 16% -> 70%+ coverage.
Avoids hanging async operations by comprehensive mocking.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from qdrant_loader.config.validation import ValidationConfig
from qdrant_loader.core.sync.event_system import ChangeEvent, ChangeType, DatabaseType
from qdrant_loader.core.sync.operations import EnhancedSyncOperation
from qdrant_loader.core.sync.types import SyncOperationType
from qdrant_loader.core.sync.validation_integration import ValidationIntegrationManager
from qdrant_loader.core.types import EntityType


class TestValidationIntegrationManagerSimple:
    """Simplified tests for ValidationIntegrationManager functionality."""

    @pytest.fixture
    def mock_validation_config(self):
        """Create mock validation configuration."""
        config = MagicMock(spec=ValidationConfig)
        config.enable_auto_validation = True
        config.enable_post_ingestion_validation = True
        config.enable_post_sync_validation = True
        config.max_concurrent_validations = 3
        config.validation_delay_seconds = 0  # No delay to avoid hanging
        config.validation_retry_attempts = 2
        config.max_validation_retries = 2
        config.validation_retry_delay_seconds = 0  # No delay
        config.validation_timeout_seconds = 30
        config.enable_auto_repair = True
        config.auto_repair_max_attempts = 1
        config.auto_repair_timeout_seconds = 30
        config.validate_on_create = True
        config.validate_on_update = True
        config.validate_on_delete = False
        config.validate_bulk_operations = True
        config.log_validation_events = False  # Disable logging
        return config

    @pytest.fixture
    def mock_validation_integrator(self):
        """Create mock validation integrator."""
        integrator = AsyncMock()
        
        # Mock validation result
        validation_result = MagicMock()
        validation_result.has_errors = False
        validation_result.has_warnings = False
        validation_result.total_issues = 0
        validation_result.critical_issues = 0
        validation_result.issues = []
        
        integrator.trigger_validation.return_value = validation_result
        integrator.repair_issues.return_value = []
        
        return integrator

    @pytest.fixture
    def validation_manager(self, mock_validation_config):
        """Create ValidationIntegrationManager instance."""
        return ValidationIntegrationManager(
            validation_config=mock_validation_config,
            validation_integrator=None,
        )

    @pytest.fixture
    def validation_manager_with_integrator(self, mock_validation_config, mock_validation_integrator):
        """Create ValidationIntegrationManager with integrator."""
        return ValidationIntegrationManager(
            validation_config=mock_validation_config,
            validation_integrator=mock_validation_integrator,
        )

    def test_initialization_basic(self, mock_validation_config):
        """Test basic ValidationIntegrationManager initialization."""
        manager = ValidationIntegrationManager(
            validation_config=mock_validation_config,
            validation_integrator=None,
        )

        assert manager.config == mock_validation_config
        assert manager.validation_integrator is None
        assert manager._active_validations == set()
        assert manager._validation_history == {}
        assert manager._stats["validations_triggered"] == 0

    def test_initialization_with_integrator(self, mock_validation_config, mock_validation_integrator):
        """Test initialization with validation integrator."""
        manager = ValidationIntegrationManager(
            validation_config=mock_validation_config,
            validation_integrator=mock_validation_integrator,
        )

        assert manager.validation_integrator == mock_validation_integrator

    @pytest.mark.asyncio
    async def test_post_ingestion_validation_disabled(self, validation_manager):
        """Test post-ingestion validation when disabled."""
        validation_manager.config.enable_auto_validation = False

        result = await validation_manager.trigger_post_ingestion_validation(
            documents_processed=10,
            project_id="test_project",
            source_type="localfile",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_post_ingestion_validation_no_integrator(self, validation_manager):
        """Test post-ingestion validation without integrator."""
        result = await validation_manager.trigger_post_ingestion_validation(
            documents_processed=10,
            project_id="test_project", 
            source_type="localfile",
        )

        assert result is False

    def test_should_validate_operation_create(self, validation_manager):
        """Test operation validation logic for CREATE operations."""
        operation = EnhancedSyncOperation(
            operation_type=SyncOperationType.CREATE,
            entity_id="test_entity",
        )

        result = validation_manager._should_validate_operation(operation)
        assert result is True

    def test_should_validate_operation_update(self, validation_manager):
        """Test operation validation logic for UPDATE operations."""
        operation = EnhancedSyncOperation(
            operation_type=SyncOperationType.UPDATE,
            entity_id="test_entity",
        )

        result = validation_manager._should_validate_operation(operation)
        assert result is True

    def test_should_validate_operation_delete(self, validation_manager):
        """Test operation validation logic for DELETE operations."""
        operation = EnhancedSyncOperation(
            operation_type=SyncOperationType.DELETE,
            entity_id="test_entity",
        )

        result = validation_manager._should_validate_operation(operation)
        assert result is False

    def test_get_statistics_empty(self, validation_manager):
        """Test getting validation statistics when empty."""
        stats = validation_manager.get_statistics()

        expected_stats = {
            "validations_triggered": 0,
            "validations_completed": 0,
            "validations_failed": 0,
            "auto_repairs_triggered": 0,
            "auto_repairs_completed": 0,
            "active_validations": 0,
            "validation_history_size": 0,
        }

        assert stats == expected_stats

    @pytest.mark.asyncio
    async def test_cleanup(self, validation_manager):
        """Test cleanup functionality."""
        # Add some test data
        validation_manager._active_validations.add("validation_1")
        validation_manager._active_validations.add("validation_2")
        validation_manager._validation_history["old_validation"] = datetime.now(UTC)

        await validation_manager.cleanup()

        assert len(validation_manager._active_validations) == 0
        assert len(validation_manager._validation_history) == 0

    def test_semaphore_initialization(self, validation_manager):
        """Test that semaphore is initialized correctly."""
        assert validation_manager._validation_semaphore._value == 3

    def test_config_access(self, validation_manager, mock_validation_config):
        """Test configuration access."""
        assert validation_manager.config == mock_validation_config
        assert validation_manager.config.enable_auto_validation is True
        assert validation_manager.config.max_concurrent_validations == 3 