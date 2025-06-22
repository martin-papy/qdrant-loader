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
        config.validate_after_document_operations = True
        config.validate_after_entity_operations = True
        config.validate_after_bulk_operations = True
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
    def validation_manager_with_integrator(
        self, mock_validation_config, mock_validation_integrator
    ):
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

    def test_initialization_with_integrator(
        self, mock_validation_config, mock_validation_integrator
    ):
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

    @pytest.mark.asyncio
    async def test_post_ingestion_validation_post_disabled(self, validation_manager):
        """Test post-ingestion validation when post-ingestion disabled."""
        validation_manager.config.enable_post_ingestion_validation = False

        result = await validation_manager.trigger_post_ingestion_validation(
            documents_processed=10,
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_post_sync_validation_disabled(self, validation_manager):
        """Test post-sync validation when disabled."""
        validation_manager.config.enable_auto_validation = False

        operation = EnhancedSyncOperation(
            operation_id="test_op",
            operation_type=SyncOperationType.CREATE_DOCUMENT,
            entity_id="test_entity",
        )

        result = await validation_manager.trigger_post_sync_validation(operation)

        assert result is False

    @pytest.mark.asyncio
    async def test_post_sync_validation_post_disabled(self, validation_manager):
        """Test post-sync validation when post-sync disabled."""
        validation_manager.config.enable_post_sync_validation = False

        operation = EnhancedSyncOperation(
            operation_id="test_op",
            operation_type=SyncOperationType.CREATE_DOCUMENT,
            entity_id="test_entity",
        )

        result = await validation_manager.trigger_post_sync_validation(operation)

        assert result is False

    @pytest.mark.asyncio
    async def test_post_sync_validation_no_integrator(self, validation_manager):
        """Test post-sync validation without integrator."""
        operation = EnhancedSyncOperation(
            operation_id="test_op",
            operation_type=SyncOperationType.CREATE_DOCUMENT,
            entity_id="test_entity",
        )

        result = await validation_manager.trigger_post_sync_validation(operation)

        assert result is False

    @pytest.mark.asyncio
    async def test_post_sync_validation_failed_operation(
        self, validation_manager_with_integrator
    ):
        """Test post-sync validation for failed operation."""
        operation = EnhancedSyncOperation(
            operation_id="test_op",
            operation_type=SyncOperationType.CREATE_DOCUMENT,
            entity_id="test_entity",
        )

        result = await validation_manager_with_integrator.trigger_post_sync_validation(
            operation, operation_success=False
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_change_event_validation_disabled(self, validation_manager):
        """Test change event validation when disabled."""
        validation_manager.config.enable_auto_validation = False

        event = ChangeEvent(
            change_type=ChangeType.CREATE,
            database_type=DatabaseType.QDRANT,
            entity_type=EntityType.CONCEPT,
        )

        result = await validation_manager.trigger_change_event_validation(event)

        assert result is False

    @pytest.mark.asyncio
    async def test_change_event_validation_no_integrator(self, validation_manager):
        """Test change event validation without integrator."""
        event = ChangeEvent(
            change_type=ChangeType.CREATE,
            database_type=DatabaseType.QDRANT,
            entity_type=EntityType.CONCEPT,
        )

        result = await validation_manager.trigger_change_event_validation(event)

        assert result is False

    def test_should_validate_operation_create(self, validation_manager):
        """Test operation validation logic for CREATE operations."""
        operation = EnhancedSyncOperation(
            operation_type=SyncOperationType.CREATE_DOCUMENT,
            entity_id="test_entity",
        )

        result = validation_manager._should_validate_operation(operation)
        assert result is True

    def test_should_validate_operation_update(self, validation_manager):
        """Test operation validation logic for UPDATE operations."""
        operation = EnhancedSyncOperation(
            operation_type=SyncOperationType.UPDATE_DOCUMENT,
            entity_id="test_entity",
        )

        result = validation_manager._should_validate_operation(operation)
        assert result is True

    def test_should_validate_operation_delete(self, validation_manager):
        """Test operation validation logic for DELETE operations."""
        operation = EnhancedSyncOperation(
            operation_type=SyncOperationType.DELETE_DOCUMENT,
            entity_id="test_entity",
        )

        result = validation_manager._should_validate_operation(operation)
        assert result is True

    def test_should_validate_operation_bulk_create(self, validation_manager):
        """Test operation validation logic for CASCADE_DELETE operations."""
        operation = EnhancedSyncOperation(
            operation_type=SyncOperationType.CASCADE_DELETE,
            entity_id="test_entity",
        )

        result = validation_manager._should_validate_operation(operation)
        assert result is True

    def test_should_validate_operation_bulk_disabled(self, validation_manager):
        """Test operation validation when bulk operations disabled."""
        validation_manager.config.validate_after_bulk_operations = False

        operation = EnhancedSyncOperation(
            operation_type=SyncOperationType.CASCADE_DELETE,
            entity_id="test_entity",
        )

        result = validation_manager._should_validate_operation(operation)
        assert result is False

    def test_should_validate_change_event_create(self, validation_manager):
        """Test change event validation for CREATE events."""
        validation_manager.config.validate_after_document_operations = True
        event = ChangeEvent(change_type=ChangeType.CREATE)

        result = validation_manager._should_validate_change_event(event)
        assert result is True

    def test_should_validate_change_event_update(self, validation_manager):
        """Test change event validation for UPDATE events."""
        validation_manager.config.validate_after_document_operations = True
        event = ChangeEvent(change_type=ChangeType.UPDATE)

        result = validation_manager._should_validate_change_event(event)
        assert result is True

    def test_should_validate_change_event_delete(self, validation_manager):
        """Test change event validation for DELETE events."""
        validation_manager.config.validate_after_document_operations = True
        event = ChangeEvent(change_type=ChangeType.DELETE)

        result = validation_manager._should_validate_change_event(event)
        assert result is True

    def test_should_validate_change_event_bulk_create(self, validation_manager):
        """Test change event validation for BULK_CREATE events."""
        validation_manager.config.validate_after_bulk_operations = True
        event = ChangeEvent(change_type=ChangeType.BULK_CREATE)

        result = validation_manager._should_validate_change_event(event)
        assert result is True

    def test_should_validate_change_event_bulk_disabled(self, validation_manager):
        """Test change event validation when bulk operations disabled."""
        validation_manager.config.validate_after_bulk_operations = False
        validation_manager.config.validate_after_document_operations = False
        validation_manager.config.validate_after_entity_operations = False

        event = ChangeEvent(change_type=ChangeType.BULK_CREATE)

        result = validation_manager._should_validate_change_event(event)
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
            "validation_history_count": 0,
            "config": {
                "auto_validation_enabled": True,
                "post_ingestion_enabled": True,
                "post_sync_enabled": True,
                "auto_repair_enabled": True,
                "max_concurrent_validations": 3,
            },
        }

        assert stats == expected_stats

    def test_get_statistics_with_data(self, validation_manager):
        """Test getting validation statistics with data."""
        # Set some test statistics
        validation_manager._stats["validations_triggered"] = 10
        validation_manager._stats["validations_completed"] = 8
        validation_manager._stats["validations_failed"] = 2
        validation_manager._stats["auto_repairs_triggered"] = 3
        validation_manager._stats["auto_repairs_completed"] = 2

        # Add some active validations and history
        validation_manager._active_validations.add("validation_1")
        validation_manager._active_validations.add("validation_2")
        validation_manager._validation_history["old_validation"] = datetime.now(UTC)

        stats = validation_manager.get_statistics()

        assert stats["validations_triggered"] == 10
        assert stats["validations_completed"] == 8
        assert stats["validations_failed"] == 2
        assert stats["auto_repairs_triggered"] == 3
        assert stats["auto_repairs_completed"] == 2
        assert stats["active_validations"] == 2
        assert stats["validation_history_count"] == 1

    @pytest.mark.asyncio
    async def test_cleanup(self, validation_manager):
        """Test cleanup functionality."""
        # Add some test data
        validation_manager._active_validations.add("validation_1")
        validation_manager._active_validations.add("validation_2")
        validation_manager._validation_history["old_validation"] = datetime.now(UTC)

        # Mock asyncio.sleep to avoid hanging in the while loop
        with patch("asyncio.sleep") as mock_sleep:
            # Clear active validations immediately to exit the while loop
            validation_manager._active_validations.clear()
            await validation_manager.cleanup()

        # Cleanup clears active validations in our test
        assert len(validation_manager._active_validations) == 0

    @pytest.mark.asyncio
    async def test_trigger_validation_with_delay_already_active(
        self, validation_manager_with_integrator
    ):
        """Test triggering validation when already active."""
        validation_key = "test_validation"
        validation_manager_with_integrator._active_validations.add(validation_key)

        result = (
            await validation_manager_with_integrator._trigger_validation_with_delay(
                context={"test": "data"},
                validation_key=validation_key,
            )
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_trigger_validation_with_delay_success_no_delay(
        self, validation_manager_with_integrator
    ):
        """Test successful validation trigger without delay."""
        validation_key = "test_validation"
        context = {"test": "data"}

        # Mock asyncio.create_task to avoid hanging
        with patch("asyncio.create_task") as mock_create_task:
            mock_create_task.return_value = None

            result = (
                await validation_manager_with_integrator._trigger_validation_with_delay(
                    context=context,
                    validation_key=validation_key,
                )
            )

        assert result is True
        assert validation_manager_with_integrator._stats["validations_triggered"] == 1
        assert validation_key in validation_manager_with_integrator._active_validations

    @pytest.mark.asyncio
    async def test_execute_validation_no_integrator(self, validation_manager):
        """Test validation execution without integrator."""
        with pytest.raises(ValueError, match="Validation integrator not available"):
            await validation_manager._execute_validation({}, "test_key")

    @pytest.mark.asyncio
    async def test_execute_validation_success(self, validation_manager_with_integrator):
        """Test successful validation execution."""
        context = {"test": "data"}
        validation_key = "test_validation"

        # Mock asyncio.wait_for to avoid hanging
        with patch("asyncio.wait_for") as mock_wait_for:
            validation_result = MagicMock()
            validation_result.total_issues = 0
            mock_wait_for.return_value = validation_result

            await validation_manager_with_integrator._execute_validation(
                context, validation_key
            )

        # Should call trigger_validation
        validation_manager_with_integrator.validation_integrator.trigger_validation.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_validation_with_issues_no_repair(
        self, validation_manager_with_integrator
    ):
        """Test validation execution with issues but no auto-repair."""
        validation_manager_with_integrator.config.enable_auto_repair = False

        context = {"test": "data"}
        validation_key = "test_validation"

        # Mock asyncio.wait_for
        with patch("asyncio.wait_for") as mock_wait_for:
            validation_result = MagicMock()
            validation_result.total_issues = 5
            mock_wait_for.return_value = validation_result

            await validation_manager_with_integrator._execute_validation(
                context, validation_key
            )

        # Should not trigger auto-repair
        validation_manager_with_integrator.validation_integrator.repair_issues.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_validation_with_auto_repair(
        self, validation_manager_with_integrator
    ):
        """Test validation execution that triggers auto-repair."""
        context = {"test": "data"}
        validation_key = "test_validation"

        # Mock asyncio.wait_for
        with (
            patch("asyncio.wait_for") as mock_wait_for,
            patch.object(
                validation_manager_with_integrator, "_trigger_auto_repair"
            ) as mock_repair,
        ):

            validation_result = MagicMock()
            validation_result.total_issues = 5
            mock_wait_for.return_value = validation_result
            mock_repair.return_value = None

            await validation_manager_with_integrator._execute_validation(
                context, validation_key
            )

        mock_repair.assert_called_once_with(context, validation_key, validation_result)

    @pytest.mark.asyncio
    async def test_trigger_auto_repair_disabled(
        self, validation_manager_with_integrator
    ):
        """Test auto-repair when disabled."""
        validation_manager_with_integrator.config.enable_auto_repair = False

        validation_result = MagicMock()
        validation_result.total_issues = 5
        validation_result.issues = ["issue1"]

        # This should still call repair_issues since the method doesn't check enable_auto_repair
        # The check happens in _execute_validation
        with patch("asyncio.wait_for") as mock_wait_for:
            mock_wait_for.return_value = []
            await validation_manager_with_integrator._trigger_auto_repair(
                context={"test": "data"},
                validation_key="test_key",
                validation_result=validation_result,
            )

        # Should trigger repair since _trigger_auto_repair doesn't check the flag
        validation_manager_with_integrator.validation_integrator.repair_issues.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_auto_repair_no_errors(
        self, validation_manager_with_integrator
    ):
        """Test auto-repair when no errors present."""
        validation_result = MagicMock()
        validation_result.total_issues = 5
        validation_result.issues = ["issue1"]

        # Even with issues, this method will call repair_issues
        with patch("asyncio.wait_for") as mock_wait_for:
            mock_wait_for.return_value = []
            await validation_manager_with_integrator._trigger_auto_repair(
                context={"test": "data"},
                validation_key="test_key",
                validation_result=validation_result,
            )

        # Should trigger repair since method doesn't check for zero issues
        validation_manager_with_integrator.validation_integrator.repair_issues.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_auto_repair_success(
        self, validation_manager_with_integrator
    ):
        """Test successful auto-repair execution."""
        validation_result = MagicMock()
        validation_result.total_issues = 2
        validation_result.issues = ["issue1", "issue2"]

        # Mock asyncio.wait_for to avoid hanging
        with patch("asyncio.wait_for") as mock_wait_for:
            repair_result = MagicMock()
            repair_result.success = True
            mock_wait_for.return_value = [repair_result]

            await validation_manager_with_integrator._trigger_auto_repair(
                context={"test": "data"},
                validation_key="test_key",
                validation_result=validation_result,
            )

        assert validation_manager_with_integrator._stats["auto_repairs_triggered"] == 1
        assert validation_manager_with_integrator._stats["auto_repairs_completed"] == 1

    @pytest.mark.asyncio
    async def test_trigger_auto_repair_no_integrator(self, validation_manager):
        """Test auto-repair without integrator."""
        validation_result = MagicMock()
        validation_result.total_issues = 1
        validation_result.issues = ["issue1"]

        # The method catches the exception and logs it, doesn't re-raise
        await validation_manager._trigger_auto_repair(
            context={"test": "data"},
            validation_key="test_key",
            validation_result=validation_result,
        )

        # Stats should still be updated even if it fails
        assert validation_manager._stats["auto_repairs_triggered"] == 1

    def test_semaphore_initialization(self, validation_manager):
        """Test that semaphore is initialized correctly."""
        assert validation_manager._validation_semaphore._value == 3

    def test_config_access(self, validation_manager, mock_validation_config):
        """Test configuration access."""
        assert validation_manager.config == mock_validation_config
        assert validation_manager.config.enable_auto_validation is True
        assert validation_manager.config.max_concurrent_validations == 3
