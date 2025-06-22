"""Tests for ValidationRepairSystemIntegrator.

This module tests the central orchestrator for validation operations,
including integration with event systems, metrics collection, and repair workflows.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from qdrant_loader.config import Settings
from qdrant_loader.core.validation_repair.integrator import (
    ValidationRepairSystemIntegrator,
)
from qdrant_loader.core.validation_repair.models import (
    RepairAction,
    RepairResult,
    ValidationCategory,
    ValidationIssue,
    ValidationReport,
    ValidationSeverity,
)
from qdrant_loader.core.validation_repair.system import ValidationRepairSystem


@pytest.fixture
def mock_validation_repair_system():
    """Mock ValidationRepairSystem."""
    system = AsyncMock(spec=ValidationRepairSystem)
    system.run_full_validation = AsyncMock()
    system.auto_repair_issues = AsyncMock()
    return system


@pytest.fixture
def mock_settings():
    """Mock Settings."""
    settings = MagicMock(spec=Settings)
    settings.validation = MagicMock()
    settings.validation.timeout_seconds = 300
    settings.validation.batch_size = 1000
    return settings


@pytest.fixture
def mock_enhanced_sync_system():
    """Mock EnhancedSyncEventSystem."""
    sync_system = MagicMock()
    base_system = MagicMock()
    base_system.add_event_handler = MagicMock()
    sync_system.base_sync_system = base_system
    return sync_system


@pytest.fixture
def mock_metrics_collector():
    """Mock ValidationMetricsCollector."""
    collector = MagicMock()
    collector.record_validation_started = MagicMock()
    collector.record_validation_completed = MagicMock()
    collector.record_validation_failed = MagicMock()
    collector.record_repair_started = MagicMock()
    collector.record_repair_completed = MagicMock()
    collector.record_repair_failed = MagicMock()
    return collector


@pytest.fixture
def mock_event_integrator():
    """Mock ValidationEventIntegrator."""
    integrator = AsyncMock()
    integrator.initialize = AsyncMock()
    integrator.start = AsyncMock()
    integrator.stop = AsyncMock()
    return integrator


@pytest.fixture
def sample_validation_report():
    """Sample ValidationReport for testing."""
    report = ValidationReport(
        total_issues=2,
        critical_issues=1,
        error_issues=1,
        warning_issues=0,
        info_issues=0,
        auto_repairable_issues=1,
        system_health_score=85.0,
        validation_duration_ms=1500.0,
        scanned_entities={"missing_mappings": 100},
        database_connectivity={"neo4j": True, "qdrant": True},
        performance_metrics={"avg_query_time": 150.5},
    )

    # Add sample issues
    issue1 = ValidationIssue(
        category=ValidationCategory.MISSING_MAPPING,
        severity=ValidationSeverity.CRITICAL,
        title="Missing mapping",
        description="Test critical issue",
        auto_repairable=True,
    )
    issue2 = ValidationIssue(
        category=ValidationCategory.DATA_MISMATCH,
        severity=ValidationSeverity.ERROR,
        title="Data mismatch",
        description="Test error issue",
        auto_repairable=False,
    )

    report.issues = [issue1, issue2]
    return report


@pytest.fixture
def sample_repair_results():
    """Sample repair results for testing."""
    return [
        RepairResult(
            issue_id="issue_1",
            action_taken=RepairAction.CREATE_MAPPING,
            success=True,
            details={"mapping_id": "new_mapping_001"},
            execution_time_ms=150.0,
        ),
        RepairResult(
            issue_id="issue_2",
            action_taken=RepairAction.UPDATE_DATA,
            success=False,
            error_message="Database connection failed",
            execution_time_ms=75.0,
        ),
    ]


class TestValidationRepairSystemIntegratorInitialization:
    """Test ValidationRepairSystemIntegrator initialization."""

    def test_init_with_minimal_params(
        self, mock_validation_repair_system, mock_settings
    ):
        """Test initialization with minimal parameters."""
        integrator = ValidationRepairSystemIntegrator(
            validation_repair_system=mock_validation_repair_system,
            settings=mock_settings,
        )

        assert integrator.validation_repair_system == mock_validation_repair_system
        assert integrator.settings == mock_settings
        assert integrator.enhanced_sync_system is None
        assert integrator.metrics_collector is None
        assert integrator.event_integrator is None
        assert integrator.auto_validation_enabled is True
        assert integrator.validation_on_ingestion is True
        assert integrator.validation_on_extraction is True
        assert integrator.validation_batch_size == 1000
        assert integrator.validation_timeout_seconds == 300
        assert not integrator._initialized
        assert not integrator._running
        assert len(integrator._active_validations) == 0
        assert len(integrator._validation_history) == 0
        assert integrator._last_validation_report is None

    def test_init_with_all_params(
        self,
        mock_validation_repair_system,
        mock_settings,
        mock_enhanced_sync_system,
        mock_metrics_collector,
        mock_event_integrator,
    ):
        """Test initialization with all parameters."""
        integrator = ValidationRepairSystemIntegrator(
            validation_repair_system=mock_validation_repair_system,
            settings=mock_settings,
            enhanced_sync_system=mock_enhanced_sync_system,
            metrics_collector=mock_metrics_collector,
            event_integrator=mock_event_integrator,
            auto_validation_enabled=False,
            validation_on_ingestion=False,
            validation_on_extraction=False,
            validation_batch_size=500,
            validation_timeout_seconds=600,
        )

        assert integrator.enhanced_sync_system == mock_enhanced_sync_system
        assert integrator.metrics_collector == mock_metrics_collector
        assert integrator.event_integrator == mock_event_integrator
        assert integrator.auto_validation_enabled is False
        assert integrator.validation_on_ingestion is False
        assert integrator.validation_on_extraction is False
        assert integrator.validation_batch_size == 500
        assert integrator.validation_timeout_seconds == 600

    def test_init_event_handlers_structure(
        self, mock_validation_repair_system, mock_settings
    ):
        """Test that event handlers are properly initialized."""
        integrator = ValidationRepairSystemIntegrator(
            validation_repair_system=mock_validation_repair_system,
            settings=mock_settings,
        )

        expected_events = [
            "validation_started",
            "validation_completed",
            "validation_failed",
            "repair_started",
            "repair_completed",
            "repair_failed",
        ]

        for event_type in expected_events:
            assert event_type in integrator._event_handlers
            assert isinstance(integrator._event_handlers[event_type], list)

    def test_init_statistics_structure(
        self, mock_validation_repair_system, mock_settings
    ):
        """Test that statistics are properly initialized."""
        integrator = ValidationRepairSystemIntegrator(
            validation_repair_system=mock_validation_repair_system,
            settings=mock_settings,
        )

        expected_stats = {
            "total_validations": 0,
            "successful_validations": 0,
            "failed_validations": 0,
            "total_repairs": 0,
            "successful_repairs": 0,
            "failed_repairs": 0,
            "auto_repairs_performed": 0,
            "manual_repairs_performed": 0,
        }

        assert integrator._stats == expected_stats


class TestValidationRepairSystemIntegratorLifecycle:
    """Test ValidationRepairSystemIntegrator lifecycle management."""

    @pytest.mark.asyncio
    async def test_initialize_success(
        self,
        mock_validation_repair_system,
        mock_settings,
        mock_enhanced_sync_system,
        mock_event_integrator,
    ):
        """Test successful initialization."""
        integrator = ValidationRepairSystemIntegrator(
            validation_repair_system=mock_validation_repair_system,
            settings=mock_settings,
            enhanced_sync_system=mock_enhanced_sync_system,
            event_integrator=mock_event_integrator,
        )

        await integrator.initialize()

        assert integrator._initialized is True
        mock_event_integrator.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_already_initialized(
        self, mock_validation_repair_system, mock_settings
    ):
        """Test initialization when already initialized."""
        integrator = ValidationRepairSystemIntegrator(
            validation_repair_system=mock_validation_repair_system,
            settings=mock_settings,
        )
        integrator._initialized = True

        # Mock the logger to verify warning was called
        with patch(
            "qdrant_loader.core.validation_repair.integrator.logger"
        ) as mock_logger:
            await integrator.initialize()

        # Verify that the warning method was called with the expected message
        mock_logger.warning.assert_called_once_with(
            "ValidationRepairSystemIntegrator already initialized"
        )

    @pytest.mark.asyncio
    async def test_initialize_with_event_system_integration(
        self,
        mock_validation_repair_system,
        mock_settings,
        mock_enhanced_sync_system,
    ):
        """Test initialization with event system integration."""
        integrator = ValidationRepairSystemIntegrator(
            validation_repair_system=mock_validation_repair_system,
            settings=mock_settings,
            enhanced_sync_system=mock_enhanced_sync_system,
        )

        with patch.object(
            integrator, "_setup_event_system_integration", new_callable=AsyncMock
        ) as mock_setup:
            await integrator.initialize()

            mock_setup.assert_called_once()
            assert integrator._initialized is True

    @pytest.mark.asyncio
    async def test_initialize_error_handling(
        self, mock_validation_repair_system, mock_settings, mock_event_integrator
    ):
        """Test initialization error handling."""
        integrator = ValidationRepairSystemIntegrator(
            validation_repair_system=mock_validation_repair_system,
            settings=mock_settings,
            event_integrator=mock_event_integrator,
        )

        # Make event integrator initialization fail
        mock_event_integrator.initialize.side_effect = Exception("Init failed")

        with pytest.raises(Exception, match="Init failed"):
            await integrator.initialize()

        assert not integrator._initialized

    @pytest.mark.asyncio
    async def test_start_not_initialized(
        self, mock_validation_repair_system, mock_settings, mock_event_integrator
    ):
        """Test starting when not initialized."""
        integrator = ValidationRepairSystemIntegrator(
            validation_repair_system=mock_validation_repair_system,
            settings=mock_settings,
            event_integrator=mock_event_integrator,
        )

        await integrator.start()

        assert integrator._initialized is True
        assert integrator._running is True
        mock_event_integrator.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_already_running(
        self, mock_validation_repair_system, mock_settings
    ):
        """Test starting when already running."""
        integrator = ValidationRepairSystemIntegrator(
            validation_repair_system=mock_validation_repair_system,
            settings=mock_settings,
        )
        integrator._initialized = True
        integrator._running = True

        # Mock the logger to verify warning was called
        with patch(
            "qdrant_loader.core.validation_repair.integrator.logger"
        ) as mock_logger:
            await integrator.start()

        # Verify that the warning method was called with the expected message
        mock_logger.warning.assert_called_once_with(
            "ValidationRepairSystemIntegrator already running"
        )

    @pytest.mark.asyncio
    async def test_stop_success(
        self, mock_validation_repair_system, mock_settings, mock_event_integrator
    ):
        """Test successful stop."""
        integrator = ValidationRepairSystemIntegrator(
            validation_repair_system=mock_validation_repair_system,
            settings=mock_settings,
            event_integrator=mock_event_integrator,
        )
        integrator._running = True

        await integrator.stop()

        assert integrator._running is False
        mock_event_integrator.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_with_active_validations(
        self, mock_validation_repair_system, mock_settings
    ):
        """Test stop with active validations."""
        integrator = ValidationRepairSystemIntegrator(
            validation_repair_system=mock_validation_repair_system,
            settings=mock_settings,
        )
        integrator._running = True

        # Add active validations
        integrator._active_validations["validation_1"] = {
            "validation_id": "validation_1",
            "status": "running",
        }
        integrator._active_validations["validation_2"] = {
            "validation_id": "validation_2",
            "status": "running",
        }

        with patch.object(
            integrator, "_cancel_validation", new_callable=AsyncMock
        ) as mock_cancel:
            await integrator.stop()

            assert mock_cancel.call_count == 2
            mock_cancel.assert_any_call("validation_1")
            mock_cancel.assert_any_call("validation_2")
            assert integrator._running is False

    @pytest.mark.asyncio
    async def test_stop_not_running(self, mock_validation_repair_system, mock_settings):
        """Test stop when not running."""
        integrator = ValidationRepairSystemIntegrator(
            validation_repair_system=mock_validation_repair_system,
            settings=mock_settings,
        )
        integrator._running = False

        # Should not raise an exception
        await integrator.stop()

        assert integrator._running is False


class TestEventSystemIntegration:
    """Test event system integration functionality."""

    @pytest.mark.asyncio
    async def test_setup_event_system_integration_success(
        self,
        mock_validation_repair_system,
        mock_settings,
        mock_enhanced_sync_system,
    ):
        """Test successful event system integration setup."""
        integrator = ValidationRepairSystemIntegrator(
            validation_repair_system=mock_validation_repair_system,
            settings=mock_settings,
            enhanced_sync_system=mock_enhanced_sync_system,
            validation_on_ingestion=True,
            validation_on_extraction=True,
        )

        await integrator._setup_event_system_integration()

        base_system = mock_enhanced_sync_system.base_sync_system
        expected_calls = [
            ("qdrant.create", integrator._on_data_ingested),
            ("qdrant.update", integrator._on_data_ingested),
            ("neo4j.create", integrator._on_entity_extracted),
            ("neo4j.update", integrator._on_entity_extracted),
        ]

        for event_type, handler in expected_calls:
            base_system.add_event_handler.assert_any_call(event_type, handler)

    @pytest.mark.asyncio
    async def test_setup_event_system_integration_no_sync_system(
        self, mock_validation_repair_system, mock_settings
    ):
        """Test event system integration setup with no sync system."""
        integrator = ValidationRepairSystemIntegrator(
            validation_repair_system=mock_validation_repair_system,
            settings=mock_settings,
            enhanced_sync_system=None,
        )

        # Should not raise an exception
        await integrator._setup_event_system_integration()

    @pytest.mark.asyncio
    async def test_setup_event_system_integration_no_base_system(
        self, mock_validation_repair_system, mock_settings
    ):
        """Test event system integration setup with no base system."""
        mock_enhanced_sync_system = MagicMock()
        mock_enhanced_sync_system.base_sync_system = None

        integrator = ValidationRepairSystemIntegrator(
            validation_repair_system=mock_validation_repair_system,
            settings=mock_settings,
            enhanced_sync_system=mock_enhanced_sync_system,
        )

        # Mock the logger to verify warning was called
        with patch(
            "qdrant_loader.core.validation_repair.integrator.logger"
        ) as mock_logger:
            await integrator._setup_event_system_integration()

        # Verify that the warning method was called with the expected message
        mock_logger.warning.assert_called_once_with(
            "No base sync system available for event integration"
        )

    @pytest.mark.asyncio
    async def test_setup_event_system_integration_partial_flags(
        self,
        mock_validation_repair_system,
        mock_settings,
        mock_enhanced_sync_system,
    ):
        """Test event system integration setup with partial flags."""
        integrator = ValidationRepairSystemIntegrator(
            validation_repair_system=mock_validation_repair_system,
            settings=mock_settings,
            enhanced_sync_system=mock_enhanced_sync_system,
            validation_on_ingestion=True,
            validation_on_extraction=False,
        )

        await integrator._setup_event_system_integration()

        base_system = mock_enhanced_sync_system.base_sync_system
        # Should only register ingestion handlers
        base_system.add_event_handler.assert_any_call(
            "qdrant.create", integrator._on_data_ingested
        )
        base_system.add_event_handler.assert_any_call(
            "qdrant.update", integrator._on_data_ingested
        )

        # Should not register extraction handlers
        calls = [call[0][0] for call in base_system.add_event_handler.call_args_list]
        assert "neo4j.create" not in calls
        assert "neo4j.update" not in calls


class TestValidationOperations:
    """Test validation operation functionality."""

    @pytest.mark.asyncio
    async def test_trigger_validation_success(
        self,
        mock_validation_repair_system,
        mock_settings,
        mock_metrics_collector,
        sample_validation_report,
    ):
        """Test successful validation trigger."""
        integrator = ValidationRepairSystemIntegrator(
            validation_repair_system=mock_validation_repair_system,
            settings=mock_settings,
            metrics_collector=mock_metrics_collector,
        )
        integrator._running = True

        mock_validation_repair_system.run_full_validation.return_value = (
            sample_validation_report
        )

        with patch.object(
            integrator, "_emit_event", new_callable=AsyncMock
        ) as mock_emit:
            result = await integrator.trigger_validation(
                validation_id="test_validation_001",
                scanners=["missing_mappings"],
                max_entities_per_scanner=100,
                auto_repair=False,
                metadata={"test": "metadata"},
            )

            assert result == sample_validation_report
            assert integrator._last_validation_report == sample_validation_report
            assert integrator._stats["total_validations"] == 1
            assert integrator._stats["successful_validations"] == 1

            # Verify metrics collection
            mock_metrics_collector.record_validation_started.assert_called_once()
            mock_metrics_collector.record_validation_completed.assert_called_once()

            # Verify events were emitted
            assert mock_emit.call_count == 2  # started and completed

    @pytest.mark.asyncio
    async def test_trigger_validation_with_auto_repair(
        self,
        mock_validation_repair_system,
        mock_settings,
        sample_validation_report,
        sample_repair_results,
    ):
        """Test validation trigger with auto repair."""
        integrator = ValidationRepairSystemIntegrator(
            validation_repair_system=mock_validation_repair_system,
            settings=mock_settings,
        )
        integrator._running = True

        mock_validation_repair_system.run_full_validation.return_value = (
            sample_validation_report
        )

        with patch.object(
            integrator, "_perform_auto_repair", new_callable=AsyncMock
        ) as mock_auto_repair:
            mock_auto_repair.return_value = sample_repair_results

            result = await integrator.trigger_validation(auto_repair=True)

            # Verify auto repair was called with the validation ID and issues
            assert mock_auto_repair.call_count == 1
            call_args = mock_auto_repair.call_args[0]
            assert call_args[1] == sample_validation_report.issues

    @pytest.mark.asyncio
    async def test_trigger_validation_not_running(
        self, mock_validation_repair_system, mock_settings
    ):
        """Test validation trigger when not running."""
        integrator = ValidationRepairSystemIntegrator(
            validation_repair_system=mock_validation_repair_system,
            settings=mock_settings,
        )
        integrator._running = False

        with pytest.raises(
            RuntimeError, match="ValidationRepairSystemIntegrator not running"
        ):
            await integrator.trigger_validation()

    @pytest.mark.asyncio
    async def test_trigger_validation_already_running(
        self, mock_validation_repair_system, mock_settings
    ):
        """Test validation trigger when validation already running."""
        integrator = ValidationRepairSystemIntegrator(
            validation_repair_system=mock_validation_repair_system,
            settings=mock_settings,
        )
        integrator._running = True
        integrator._active_validations["test_validation"] = {"status": "running"}

        with pytest.raises(
            ValueError, match="Validation test_validation is already running"
        ):
            await integrator.trigger_validation(validation_id="test_validation")

    @pytest.mark.asyncio
    async def test_trigger_validation_timeout(
        self,
        mock_validation_repair_system,
        mock_settings,
        mock_metrics_collector,
    ):
        """Test validation trigger with timeout."""
        integrator = ValidationRepairSystemIntegrator(
            validation_repair_system=mock_validation_repair_system,
            settings=mock_settings,
            metrics_collector=mock_metrics_collector,
            validation_timeout_seconds=1,  # Very short timeout
        )
        integrator._running = True

        # Make validation take longer than timeout
        async def slow_validation(*args, **kwargs):
            await asyncio.sleep(2)  # Longer than 1 second timeout
            return sample_validation_report

        mock_validation_repair_system.run_full_validation.side_effect = slow_validation

        with patch.object(
            integrator, "_emit_event", new_callable=AsyncMock
        ) as mock_emit:
            with pytest.raises(asyncio.TimeoutError):
                await integrator.trigger_validation()

            # Verify failure was recorded
            assert integrator._stats["failed_validations"] == 1
            mock_metrics_collector.record_validation_failed.assert_called_once()
            # Verify failure event was emitted
            mock_emit.assert_called_with(
                "validation_failed",
                {
                    "validation_id": mock_emit.call_args_list[-1][0][1][
                        "validation_id"
                    ],
                    "error": "Validation timed out",
                    "metadata": None,
                },
            )

    @pytest.mark.asyncio
    async def test_trigger_validation_error(
        self,
        mock_validation_repair_system,
        mock_settings,
        mock_metrics_collector,
    ):
        """Test validation trigger with error."""
        integrator = ValidationRepairSystemIntegrator(
            validation_repair_system=mock_validation_repair_system,
            settings=mock_settings,
            metrics_collector=mock_metrics_collector,
        )
        integrator._running = True

        mock_validation_repair_system.run_full_validation.side_effect = Exception(
            "Validation failed"
        )

        with patch.object(
            integrator, "_emit_event", new_callable=AsyncMock
        ) as mock_emit:
            with pytest.raises(Exception, match="Validation failed"):
                await integrator.trigger_validation()

            # Verify failure was recorded
            assert integrator._stats["failed_validations"] == 1
            mock_metrics_collector.record_validation_failed.assert_called_once()
            # Verify failure event was emitted
            mock_emit.assert_called_with(
                "validation_failed",
                {
                    "validation_id": mock_emit.call_args_list[-1][0][1][
                        "validation_id"
                    ],
                    "error": "Validation failed",
                    "metadata": None,
                },
            )

    @pytest.mark.asyncio
    async def test_trigger_validation_auto_id_generation(
        self, mock_validation_repair_system, mock_settings, sample_validation_report
    ):
        """Test validation trigger with automatic ID generation."""
        integrator = ValidationRepairSystemIntegrator(
            validation_repair_system=mock_validation_repair_system,
            settings=mock_settings,
        )
        integrator._running = True

        mock_validation_repair_system.run_full_validation.return_value = (
            sample_validation_report
        )

        with patch.object(integrator, "_emit_event", new_callable=AsyncMock):
            result = await integrator.trigger_validation()

            # Verify validation ID was generated
            assert len(integrator._validation_history) == 1
            validation_record = integrator._validation_history[0]
            assert validation_record["validation_id"].startswith("validation_")


class TestRepairOperations:
    """Test repair operation functionality."""

    @pytest.mark.asyncio
    async def test_repair_issues_success(
        self,
        mock_validation_repair_system,
        mock_settings,
        mock_metrics_collector,
        sample_repair_results,
    ):
        """Test successful repair operation."""
        integrator = ValidationRepairSystemIntegrator(
            validation_repair_system=mock_validation_repair_system,
            settings=mock_settings,
            metrics_collector=mock_metrics_collector,
        )
        integrator._running = True

        # Create sample issues
        issues = [
            ValidationIssue(
                category=ValidationCategory.MISSING_MAPPING,
                severity=ValidationSeverity.CRITICAL,
                title="Missing mapping",
                description="Test issue",
                auto_repairable=True,
            )
        ]

        mock_validation_repair_system.auto_repair_issues.return_value = (
            sample_repair_results
        )

        with patch.object(
            integrator, "_emit_event", new_callable=AsyncMock
        ) as mock_emit:
            result = await integrator.repair_issues(
                issues=issues,
                repair_id="test_repair_001",
                max_repairs=10,
                metadata={"test": "metadata"},
            )

            assert result == sample_repair_results
            assert integrator._stats["total_repairs"] == 2
            assert integrator._stats["successful_repairs"] == 1
            assert integrator._stats["failed_repairs"] == 1
            assert integrator._stats["manual_repairs_performed"] == 2

            # Verify metrics collection
            mock_metrics_collector.record_repair_started.assert_called_once()
            mock_metrics_collector.record_repair_completed.assert_called_once()

            # Verify events were emitted
            assert mock_emit.call_count == 2  # started and completed

    @pytest.mark.asyncio
    async def test_repair_issues_not_running(
        self, mock_validation_repair_system, mock_settings
    ):
        """Test repair operation when not running."""
        integrator = ValidationRepairSystemIntegrator(
            validation_repair_system=mock_validation_repair_system,
            settings=mock_settings,
        )
        integrator._running = False

        with pytest.raises(
            RuntimeError, match="ValidationRepairSystemIntegrator not running"
        ):
            await integrator.repair_issues(issues=[])

    @pytest.mark.asyncio
    async def test_repair_issues_auto_id_generation(
        self, mock_validation_repair_system, mock_settings, sample_repair_results
    ):
        """Test repair operation with automatic ID generation."""
        integrator = ValidationRepairSystemIntegrator(
            validation_repair_system=mock_validation_repair_system,
            settings=mock_settings,
        )
        integrator._running = True

        mock_validation_repair_system.auto_repair_issues.return_value = (
            sample_repair_results
        )

        with patch.object(
            integrator, "_emit_event", new_callable=AsyncMock
        ) as mock_emit:
            await integrator.repair_issues(issues=[])

            # Verify repair ID was generated
            repair_started_call = mock_emit.call_args_list[0]
            assert repair_started_call[0][0] == "repair_started"
            repair_id = repair_started_call[0][1]["repair_id"]
            assert repair_id.startswith("repair_")

    @pytest.mark.asyncio
    async def test_repair_issues_error(
        self,
        mock_validation_repair_system,
        mock_settings,
        mock_metrics_collector,
    ):
        """Test repair operation with error."""
        integrator = ValidationRepairSystemIntegrator(
            validation_repair_system=mock_validation_repair_system,
            settings=mock_settings,
            metrics_collector=mock_metrics_collector,
        )
        integrator._running = True

        mock_validation_repair_system.auto_repair_issues.side_effect = Exception(
            "Repair failed"
        )

        with patch.object(
            integrator, "_emit_event", new_callable=AsyncMock
        ) as mock_emit:
            with pytest.raises(Exception, match="Repair failed"):
                await integrator.repair_issues(issues=[])

            # Verify failure was recorded
            mock_metrics_collector.record_repair_failed.assert_called_once()
            # Verify failure event was emitted
            mock_emit.assert_called_with(
                "repair_failed",
                {
                    "repair_id": mock_emit.call_args_list[-1][0][1]["repair_id"],
                    "error": "Repair failed",
                    "metadata": None,
                },
            )
