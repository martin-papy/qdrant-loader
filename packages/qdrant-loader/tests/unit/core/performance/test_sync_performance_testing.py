"""Unit tests for sync performance testing framework.

This module tests the comprehensive performance testing capabilities including
load testing, stress testing, latency benchmarking, and resource monitoring.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from qdrant_loader.core.sync.event_system import DatabaseType
from qdrant_loader.core.sync.operations import EnhancedSyncOperation
from qdrant_loader.core.sync.types import SyncOperationType
from qdrant_loader.performance.sync_performance_testing import (
    LOAD_TEST_SCENARIOS,
    LoadTestScenario,
    StressTestConfig,
    SyncPerformanceMetrics,
    SyncPerformanceTester,
    run_comprehensive_performance_suite,
)


class TestSyncPerformanceMetrics:
    """Test the SyncPerformanceMetrics dataclass."""

    def test_metrics_initialization(self):
        """Test metrics initialization with default values."""
        metrics = SyncPerformanceMetrics()

        assert metrics.total_duration == 0.0
        assert metrics.avg_operation_time == 0.0
        assert metrics.min_operation_time == float("inf")
        assert metrics.max_operation_time == 0.0
        assert metrics.operations_per_second == 0.0
        assert metrics.peak_memory_mb == 0.0
        assert metrics.total_operations == 0
        assert metrics.successful_operations == 0
        assert metrics.failed_operations == 0
        assert metrics.success_rate == 0.0

    def test_metrics_with_values(self):
        """Test metrics with specific values."""
        metrics = SyncPerformanceMetrics(
            total_duration=120.5,
            avg_operation_time=0.25,
            operations_per_second=400.0,
            total_operations=1000,
            successful_operations=950,
            failed_operations=50,
        )

        assert metrics.total_duration == 120.5
        assert metrics.avg_operation_time == 0.25
        assert metrics.operations_per_second == 400.0
        assert metrics.total_operations == 1000
        assert metrics.successful_operations == 950
        assert metrics.failed_operations == 50


class TestStressTestConfig:
    """Test the StressTestConfig dataclass."""

    def test_config_defaults(self):
        """Test default configuration values."""
        config = StressTestConfig()

        assert config.duration_seconds == 300
        assert config.concurrent_operations == 50
        assert config.operation_timeout == 30.0
        assert config.ramp_up_seconds == 60
        assert config.create_operations_percent == 40.0
        assert config.update_operations_percent == 40.0
        assert config.delete_operations_percent == 20.0
        assert config.document_size_range == (1000, 10000)
        assert config.max_avg_latency_ms == 1000.0
        assert config.min_success_rate == 0.95

    def test_config_custom_values(self):
        """Test configuration with custom values."""
        config = StressTestConfig(
            duration_seconds=600,
            concurrent_operations=100,
            create_operations_percent=50.0,
            update_operations_percent=30.0,
            delete_operations_percent=20.0,
        )

        assert config.duration_seconds == 600
        assert config.concurrent_operations == 100
        assert config.create_operations_percent == 50.0
        assert config.update_operations_percent == 30.0
        assert config.delete_operations_percent == 20.0


class TestLoadTestScenario:
    """Test the LoadTestScenario dataclass."""

    def test_scenario_creation(self):
        """Test load test scenario creation."""
        scenario = LoadTestScenario(
            name="Test Scenario",
            description="Test description",
            concurrent_users=25,
            operations_per_user=100,
            operation_types=[SyncOperationType.CREATE_DOCUMENT],
            data_size_mb=10.0,
            expected_duration_seconds=120.0,
        )

        assert scenario.name == "Test Scenario"
        assert scenario.description == "Test description"
        assert scenario.concurrent_users == 25
        assert scenario.operations_per_user == 100
        assert scenario.operation_types == [SyncOperationType.CREATE_DOCUMENT]
        assert scenario.data_size_mb == 10.0
        assert scenario.expected_duration_seconds == 120.0


class TestSyncPerformanceTester:
    """Test the SyncPerformanceTester class."""

    @pytest.fixture
    def mock_managers(self):
        """Create mock managers for testing."""
        qdrant_manager = MagicMock()
        neo4j_manager = MagicMock()
        id_mapping_manager = MagicMock()
        return qdrant_manager, neo4j_manager, id_mapping_manager

    @pytest.fixture
    def performance_tester(self, mock_managers):
        """Create a performance tester instance."""
        qdrant_manager, neo4j_manager, id_mapping_manager = mock_managers
        return SyncPerformanceTester(
            qdrant_manager=qdrant_manager,
            neo4j_manager=neo4j_manager,
            id_mapping_manager=id_mapping_manager,
        )

    def test_tester_initialization(self, performance_tester, mock_managers):
        """Test performance tester initialization."""
        qdrant_manager, neo4j_manager, id_mapping_manager = mock_managers

        assert performance_tester.qdrant_manager == qdrant_manager
        assert performance_tester.neo4j_manager == neo4j_manager
        assert performance_tester.id_mapping_manager == id_mapping_manager
        assert performance_tester.atomic_transaction_manager is not None
        assert performance_tester.operation_diff_manager is not None
        assert performance_tester.sync_system is not None
        assert performance_tester.operation_times == []
        assert performance_tester.memory_samples == []
        assert performance_tester.cpu_samples == []

    @pytest.mark.asyncio
    async def test_setup_and_teardown(self, performance_tester):
        """Test setup and teardown methods."""
        with patch.object(
            performance_tester.sync_system, "start", new_callable=AsyncMock
        ) as mock_start:
            await performance_tester.setup()
            mock_start.assert_called_once()

        with patch.object(
            performance_tester.sync_system, "stop", new_callable=AsyncMock
        ) as mock_stop:
            await performance_tester.teardown()
            mock_stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_test_document(self, performance_tester):
        """Test creating a test document."""
        with patch.object(
            performance_tester.sync_system, "queue_operation", new_callable=AsyncMock
        ) as mock_queue:
            await performance_tester._create_test_document("test_doc_001")

            mock_queue.assert_called_once()
            operation = mock_queue.call_args[0][0]
            assert isinstance(operation, EnhancedSyncOperation)
            assert operation.operation_type == SyncOperationType.CREATE_DOCUMENT
            assert operation.entity_id == "test_doc_001"
            assert DatabaseType.QDRANT in operation.target_databases
            assert DatabaseType.NEO4J in operation.target_databases

    @pytest.mark.asyncio
    async def test_update_test_document(self, performance_tester):
        """Test updating a test document."""
        with patch.object(
            performance_tester.sync_system, "queue_operation", new_callable=AsyncMock
        ) as mock_queue:
            await performance_tester._update_test_document("test_doc_001")

            mock_queue.assert_called_once()
            operation = mock_queue.call_args[0][0]
            assert isinstance(operation, EnhancedSyncOperation)
            assert operation.operation_type == SyncOperationType.UPDATE_DOCUMENT
            assert operation.entity_id == "test_doc_001"

    @pytest.mark.asyncio
    async def test_delete_test_document(self, performance_tester):
        """Test deleting a test document."""
        with patch.object(
            performance_tester.sync_system, "queue_operation", new_callable=AsyncMock
        ) as mock_queue:
            await performance_tester._delete_test_document("test_doc_001")

            mock_queue.assert_called_once()
            operation = mock_queue.call_args[0][0]
            assert isinstance(operation, EnhancedSyncOperation)
            assert operation.operation_type == SyncOperationType.DELETE_DOCUMENT
            assert operation.entity_id == "test_doc_001"

    def test_select_operation_type(self, performance_tester):
        """Test operation type selection based on configuration."""
        config = StressTestConfig(
            create_operations_percent=50.0,
            update_operations_percent=30.0,
            delete_operations_percent=20.0,
        )

        # Test multiple selections to verify distribution
        operation_types = []
        for _ in range(100):
            op_type = performance_tester._select_operation_type(config)
            operation_types.append(op_type)

        # Verify all operation types are represented
        assert SyncOperationType.CREATE_DOCUMENT in operation_types
        assert SyncOperationType.UPDATE_DOCUMENT in operation_types
        assert SyncOperationType.DELETE_DOCUMENT in operation_types

    @pytest.mark.asyncio
    async def test_execute_test_operation(self, performance_tester):
        """Test executing different types of test operations."""
        with patch.object(
            performance_tester, "_create_test_document", new_callable=AsyncMock
        ) as mock_create:
            await performance_tester._execute_test_operation(
                SyncOperationType.CREATE_DOCUMENT, "test_op_001"
            )
            mock_create.assert_called_once_with("test_op_001")

        with patch.object(
            performance_tester, "_update_test_document", new_callable=AsyncMock
        ) as mock_update:
            await performance_tester._execute_test_operation(
                SyncOperationType.UPDATE_DOCUMENT, "test_op_002"
            )
            mock_update.assert_called_once_with("test_op_002")

        with patch.object(
            performance_tester, "_delete_test_document", new_callable=AsyncMock
        ) as mock_delete:
            await performance_tester._execute_test_operation(
                SyncOperationType.DELETE_DOCUMENT, "test_op_003"
            )
            mock_delete.assert_called_once_with("test_op_003")

    @pytest.mark.asyncio
    async def test_simulate_user_operations(self, performance_tester):
        """Test simulating user operations."""
        operation_types = [
            SyncOperationType.CREATE_DOCUMENT,
            SyncOperationType.UPDATE_DOCUMENT,
        ]

        with patch.object(
            performance_tester, "_execute_test_operation", new_callable=AsyncMock
        ) as mock_execute:
            results = await performance_tester._simulate_user_operations(
                user_id=1, operation_count=5, operation_types=operation_types
            )

            assert results["user_id"] == 1
            assert results["successful_operations"] == 5
            assert results["failed_operations"] == 0
            assert len(results["operation_times"]) == 5
            assert mock_execute.call_count == 5

    @pytest.mark.asyncio
    async def test_simulate_user_operations_with_failures(self, performance_tester):
        """Test simulating user operations with failures."""
        operation_types = [SyncOperationType.CREATE_DOCUMENT]

        with patch.object(
            performance_tester,
            "_execute_test_operation",
            new_callable=AsyncMock,
            side_effect=Exception("Test error"),
        ) as mock_execute:
            results = await performance_tester._simulate_user_operations(
                user_id=1, operation_count=3, operation_types=operation_types
            )

            assert results["user_id"] == 1
            assert results["successful_operations"] == 0
            assert results["failed_operations"] == 3
            assert len(results["operation_times"]) == 0
            assert mock_execute.call_count == 3

    def test_calculate_metrics(self, performance_tester):
        """Test metrics calculation from test results."""
        # Mock results from user simulations
        results = [
            {
                "successful_operations": 10,
                "failed_operations": 2,
                "operation_times": [
                    0.1,
                    0.2,
                    0.15,
                    0.3,
                    0.25,
                    0.18,
                    0.22,
                    0.12,
                    0.28,
                    0.16,
                ],
            },
            {
                "successful_operations": 8,
                "failed_operations": 1,
                "operation_times": [0.14, 0.19, 0.21, 0.17, 0.23, 0.13, 0.26, 0.20],
            },
        ]

        # Add some sample data
        performance_tester.memory_samples = [100.0, 120.0, 110.0, 130.0]
        performance_tester.cpu_samples = [25.0, 30.0, 28.0, 35.0]

        total_duration = 60.0  # 1 minute
        metrics = performance_tester._calculate_metrics(total_duration, results)

        assert metrics.total_duration == 60.0
        assert metrics.total_operations == 21  # 12 + 9
        assert metrics.successful_operations == 18  # 10 + 8
        assert metrics.failed_operations == 3  # 2 + 1
        assert metrics.operations_per_second == 21 / 60.0
        assert metrics.peak_memory_mb == 130.0
        assert metrics.avg_memory_mb == 115.0  # (100+120+110+130)/4
        assert metrics.peak_cpu_percent == 35.0
        assert metrics.success_rate == 18 / 21
        assert metrics.error_rate == 3 / 21

    def test_calculate_stress_metrics(self, performance_tester):
        """Test stress test specific metrics calculation."""
        config = StressTestConfig(duration_seconds=300, concurrent_operations=50)

        # Add sample operation times
        performance_tester.operation_times = [
            0.1,
            0.2,
            0.15,
            0.3,
            0.25,
        ] * 20  # 100 operations
        performance_tester.memory_samples = [100.0, 150.0, 120.0]
        performance_tester.cpu_samples = [20.0, 40.0, 30.0]

        total_duration = 300.0
        metrics = performance_tester._calculate_stress_metrics(total_duration, config)

        assert metrics.total_duration == 300.0
        assert metrics.total_operations == 100
        assert metrics.successful_operations == 100
        assert metrics.operations_per_second == 100 / 300.0
        assert metrics.peak_memory_mb == 150.0
        assert metrics.avg_memory_mb == 123.33333333333333  # (100+150+120)/3
        assert metrics.peak_cpu_percent == 40.0
        assert metrics.success_rate == 1.0

    @pytest.mark.asyncio
    async def test_latency_benchmark(self, performance_tester):
        """Test latency benchmarking functionality."""
        with patch.object(
            performance_tester, "_execute_benchmark_operation", new_callable=AsyncMock
        ) as mock_execute:
            metrics = await performance_tester.run_latency_benchmark(operation_count=10)

            # Should call execute_benchmark_operation for each operation type * operation_count
            # 3 operation types * 10 operations = 30 calls
            assert mock_execute.call_count == 30
            assert metrics.total_operations == 30
            assert metrics.successful_operations == 30
            assert metrics.success_rate == 1.0

    @pytest.mark.asyncio
    async def test_latency_benchmark_with_failures(self, performance_tester):
        """Test latency benchmarking with some failures."""
        call_count = 0

        async def mock_execute_with_failures(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 5 == 0:  # Every 5th call fails
                raise Exception("Test failure")

        with patch.object(
            performance_tester,
            "_execute_benchmark_operation",
            new_callable=AsyncMock,
            side_effect=mock_execute_with_failures,
        ) as mock_execute:
            metrics = await performance_tester.run_latency_benchmark(operation_count=10)

            assert mock_execute.call_count == 30
            # Should have 6 failures (every 5th call: 5, 10, 15, 20, 25, 30)
            assert metrics.total_operations == 24  # 30 - 6 failures
            assert metrics.successful_operations == 24

    @pytest.mark.asyncio
    async def test_memory_stress_test(self, performance_tester):
        """Test memory stress testing functionality."""
        with patch.object(
            performance_tester, "_create_test_document", new_callable=AsyncMock
        ) as mock_create:
            with patch("psutil.Process") as mock_process:
                # Mock memory info
                mock_memory_info = MagicMock()
                mock_memory_info.rss = 100 * 1024 * 1024  # 100 MB in bytes
                mock_process.return_value.memory_info.return_value = mock_memory_info

                metrics = await performance_tester.run_memory_stress_test(
                    max_documents=100
                )

                assert mock_create.call_count == 100
                assert metrics.total_operations == 100
                assert metrics.successful_operations == 100

    @pytest.mark.asyncio
    async def test_monitor_resources(self, performance_tester):
        """Test resource monitoring functionality."""
        with patch("psutil.Process") as mock_process:
            # Mock memory and CPU info
            mock_memory_info = MagicMock()
            mock_memory_info.rss = 100 * 1024 * 1024  # 100 MB in bytes
            mock_process.return_value.memory_info.return_value = mock_memory_info
            mock_process.return_value.cpu_percent.return_value = 25.0

            # Start monitoring
            monitor_task = asyncio.create_task(performance_tester._monitor_resources())

            # Let it run for a short time
            await asyncio.sleep(0.1)

            # Cancel monitoring
            monitor_task.cancel()

            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

            # Should have collected some samples
            assert len(performance_tester.memory_samples) > 0
            assert len(performance_tester.cpu_samples) > 0


class TestPredefinedScenarios:
    """Test predefined load test scenarios."""

    def test_load_test_scenarios_exist(self):
        """Test that predefined load test scenarios exist."""
        assert len(LOAD_TEST_SCENARIOS) == 4

        scenario_names = [scenario.name for scenario in LOAD_TEST_SCENARIOS]
        assert "Light Load" in scenario_names
        assert "Medium Load" in scenario_names
        assert "Heavy Load" in scenario_names
        assert "Burst Load" in scenario_names

    def test_light_load_scenario(self):
        """Test light load scenario configuration."""
        light_load = next(s for s in LOAD_TEST_SCENARIOS if s.name == "Light Load")

        assert light_load.concurrent_users == 10
        assert light_load.operations_per_user == 50
        assert len(light_load.operation_types) == 2
        assert SyncOperationType.CREATE_DOCUMENT in light_load.operation_types
        assert SyncOperationType.UPDATE_DOCUMENT in light_load.operation_types

    def test_heavy_load_scenario(self):
        """Test heavy load scenario configuration."""
        heavy_load = next(s for s in LOAD_TEST_SCENARIOS if s.name == "Heavy Load")

        assert heavy_load.concurrent_users == 50
        assert heavy_load.operations_per_user == 200
        assert len(heavy_load.operation_types) == 3
        assert SyncOperationType.CREATE_DOCUMENT in heavy_load.operation_types
        assert SyncOperationType.UPDATE_DOCUMENT in heavy_load.operation_types
        assert SyncOperationType.DELETE_DOCUMENT in heavy_load.operation_types

    def test_burst_load_scenario(self):
        """Test burst load scenario configuration."""
        burst_load = next(s for s in LOAD_TEST_SCENARIOS if s.name == "Burst Load")

        assert burst_load.concurrent_users == 100
        assert burst_load.operations_per_user == 50
        assert len(burst_load.operation_types) == 1
        assert burst_load.operation_types[0] == SyncOperationType.CREATE_DOCUMENT


class TestComprehensivePerformanceSuite:
    """Test the comprehensive performance testing suite."""

    @pytest.mark.asyncio
    async def test_comprehensive_suite_structure(self):
        """Test that comprehensive suite function exists and has proper structure."""
        # Mock managers
        qdrant_manager = MagicMock()
        neo4j_manager = MagicMock()
        id_mapping_manager = MagicMock()

        with patch(
            "qdrant_loader.performance.sync_performance_testing.SyncPerformanceTester"
        ) as mock_tester_class:
            mock_tester = MagicMock()
            mock_tester_class.return_value = mock_tester

            # Mock all test methods
            mock_tester.setup = AsyncMock()
            mock_tester.teardown = AsyncMock()
            mock_tester.run_latency_benchmark = AsyncMock(
                return_value=SyncPerformanceMetrics()
            )
            mock_tester.run_load_test = AsyncMock(return_value=SyncPerformanceMetrics())
            mock_tester.run_stress_test = AsyncMock(
                return_value=SyncPerformanceMetrics()
            )
            mock_tester.run_memory_stress_test = AsyncMock(
                return_value=SyncPerformanceMetrics()
            )

            results = await run_comprehensive_performance_suite(
                qdrant_manager, neo4j_manager, id_mapping_manager
            )

            # Verify setup and teardown were called
            mock_tester.setup.assert_called_once()
            mock_tester.teardown.assert_called_once()

            # Verify all test types were run
            assert "latency_benchmark" in results
            assert "stress_test" in results
            assert "memory_stress_test" in results

            # Verify load tests for all scenarios
            for scenario in LOAD_TEST_SCENARIOS:
                scenario_key = f"load_test_{scenario.name.lower().replace(' ', '_')}"
                assert scenario_key in results

    @pytest.mark.asyncio
    async def test_comprehensive_suite_error_handling(self):
        """Test error handling in comprehensive suite."""
        # Mock managers
        qdrant_manager = MagicMock()
        neo4j_manager = MagicMock()
        id_mapping_manager = MagicMock()

        with patch(
            "qdrant_loader.performance.sync_performance_testing.SyncPerformanceTester"
        ) as mock_tester_class:
            mock_tester = MagicMock()
            mock_tester_class.return_value = mock_tester

            # Mock setup to succeed but one test to fail
            mock_tester.setup = AsyncMock()
            mock_tester.teardown = AsyncMock()
            mock_tester.run_latency_benchmark = AsyncMock(
                side_effect=Exception("Test error")
            )

            # Should still call teardown even if tests fail
            with pytest.raises(Exception, match="Test error"):
                await run_comprehensive_performance_suite(
                    qdrant_manager, neo4j_manager, id_mapping_manager
                )

            mock_tester.setup.assert_called_once()
            mock_tester.teardown.assert_called_once()
