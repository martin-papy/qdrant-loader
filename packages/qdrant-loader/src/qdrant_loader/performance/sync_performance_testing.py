"""
Performance and stress testing framework for the enhanced synchronization system.

This module provides comprehensive performance testing capabilities for:
- Load testing with concurrent operations
- Memory usage and resource monitoring
- Latency benchmarks for sync operations
- Stress testing with large datasets
- Throughput measurement and optimization
"""

import asyncio
import logging
import statistics
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import psutil

from qdrant_loader.core.atomic_transactions import AtomicTransactionManager
from qdrant_loader.core.managers.id_mapping_manager import IDMappingManager
from qdrant_loader.core.managers.neo4j_manager import Neo4jManager
from qdrant_loader.core.managers.qdrant_manager import QdrantManager
from qdrant_loader.core.operation_differentiation import (
    OperationDifferentiationManager,
)
from qdrant_loader.core.sync.conflict_monitor import SyncConflictMonitor
from qdrant_loader.core.sync.enhanced_event_system import EnhancedSyncEventSystem
from qdrant_loader.core.sync.event_system import DatabaseType
from qdrant_loader.core.sync.operations import EnhancedSyncOperation
from qdrant_loader.core.sync.types import SyncOperationType


@dataclass
class SyncPerformanceMetrics:
    """Performance metrics for sync operations."""

    # Timing metrics
    total_duration: float = 0.0
    avg_operation_time: float = 0.0
    min_operation_time: float = float("inf")
    max_operation_time: float = 0.0
    p95_operation_time: float = 0.0
    p99_operation_time: float = 0.0

    # Throughput metrics
    operations_per_second: float = 0.0
    documents_per_second: float = 0.0
    transactions_per_second: float = 0.0

    # Resource metrics
    peak_memory_mb: float = 0.0
    avg_memory_mb: float = 0.0
    peak_cpu_percent: float = 0.0
    avg_cpu_percent: float = 0.0

    # Operation metrics
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    timeout_operations: int = 0

    # Database metrics
    qdrant_operations: int = 0
    neo4j_operations: int = 0
    transaction_rollbacks: int = 0
    conflict_resolutions: int = 0

    # Quality metrics
    success_rate: float = 0.0
    error_rate: float = 0.0
    data_consistency_score: float = 0.0


@dataclass
class StressTestConfig:
    """Configuration for stress testing scenarios."""

    # Test parameters
    duration_seconds: int = 300  # 5 minutes default
    concurrent_operations: int = 50
    operation_timeout: float = 30.0
    ramp_up_seconds: int = 60

    # Operation distribution
    create_operations_percent: float = 40.0
    update_operations_percent: float = 40.0
    delete_operations_percent: float = 20.0

    # Data parameters
    document_size_range: tuple[int, int] = (1000, 10000)  # bytes
    metadata_complexity: str = "medium"  # low, medium, high
    entity_count_range: tuple[int, int] = (5, 20)

    # Performance thresholds
    max_avg_latency_ms: float = 1000.0
    min_throughput_ops: float = 10.0
    max_memory_mb: float = 2048.0
    max_cpu_percent: float = 80.0
    min_success_rate: float = 0.95


@dataclass
class LoadTestScenario:
    """Load testing scenario definition."""

    name: str
    description: str
    concurrent_users: int
    operations_per_user: int
    operation_types: list[SyncOperationType]
    data_size_mb: float
    expected_duration_seconds: float


class SyncPerformanceTester:
    """Performance and stress testing for the sync system."""

    def __init__(
        self,
        qdrant_manager: QdrantManager,
        neo4j_manager: Neo4jManager,
        id_mapping_manager: IDMappingManager,
        logger: logging.Logger | None = None,
    ):
        """Initialize the performance tester.

        Args:
            qdrant_manager: QDrant database manager
            neo4j_manager: Neo4j database manager
            id_mapping_manager: ID mapping manager
            logger: Optional logger instance
        """
        self.qdrant_manager = qdrant_manager
        self.neo4j_manager = neo4j_manager
        self.id_mapping_manager = id_mapping_manager
        self.logger = logger or logging.getLogger(__name__)

        # Initialize sync components
        self.atomic_transaction_manager = AtomicTransactionManager(
            qdrant_manager=qdrant_manager,
            neo4j_manager=neo4j_manager,
            id_mapping_manager=id_mapping_manager,
        )

        self.operation_diff_manager = OperationDifferentiationManager(
            enable_caching=True, cache_ttl_seconds=3600
        )

        # Initialize sync system first
        self.sync_system = EnhancedSyncEventSystem(
            qdrant_manager=qdrant_manager,
            neo4j_manager=neo4j_manager,
            id_mapping_manager=id_mapping_manager,
            atomic_transaction_manager=self.atomic_transaction_manager,
            enable_operation_differentiation=True,
        )

        # Initialize conflict resolution system for monitoring
        from qdrant_loader.core.conflict_resolution import ConflictResolutionSystem

        self.conflict_resolution_system = ConflictResolutionSystem(
            qdrant_manager=qdrant_manager,
            neo4j_manager=neo4j_manager,
            id_mapping_manager=id_mapping_manager,
        )

        # Initialize sync conflict monitor with required dependencies
        from qdrant_loader.core.sync.conflict_monitor import SyncMonitoringLevel

        self.sync_conflict_monitor = SyncConflictMonitor(
            enhanced_sync_system=self.sync_system,
            conflict_resolution_system=self.conflict_resolution_system,
            qdrant_manager=qdrant_manager,
            neo4j_manager=neo4j_manager,
            id_mapping_manager=id_mapping_manager,
            monitoring_level=SyncMonitoringLevel.DETAILED,
        )

        # Performance tracking
        self.operation_times: list[float] = []
        self.memory_samples: list[float] = []
        self.cpu_samples: list[float] = []
        self.process = psutil.Process()

    async def setup(self):
        """Set up the sync system for testing."""
        await self.sync_system.start()
        self.logger.info("Sync system started for performance testing")

    async def teardown(self):
        """Clean up after testing."""
        await self.sync_system.stop()
        self.logger.info("Sync system stopped after performance testing")

    async def run_load_test(self, scenario: LoadTestScenario) -> SyncPerformanceMetrics:
        """Run a load testing scenario.

        Args:
            scenario: Load test scenario configuration

        Returns:
            Performance metrics from the load test
        """
        self.logger.info(f"Starting load test: {scenario.name}")

        # Reset metrics
        self.operation_times.clear()
        self.memory_samples.clear()
        self.cpu_samples.clear()

        start_time = time.time()

        # Start resource monitoring
        monitor_task = asyncio.create_task(self._monitor_resources())

        try:
            # Create concurrent tasks for each user
            tasks = []
            for user_id in range(scenario.concurrent_users):
                task = self._simulate_user_operations(
                    user_id, scenario.operations_per_user, scenario.operation_types
                )
                tasks.append(task)

            # Execute all user simulations concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Stop resource monitoring
            monitor_task.cancel()

            end_time = time.time()
            total_duration = end_time - start_time

            # Calculate metrics
            metrics = self._calculate_metrics(total_duration, results)

            self.logger.info(f"Load test completed: {scenario.name}")
            self.logger.info(
                f"Duration: {total_duration:.2f}s, OPS: {metrics.operations_per_second:.2f}"
            )

            return metrics

        except Exception as e:
            monitor_task.cancel()
            self.logger.error(f"Load test failed: {e}")
            raise

    async def run_stress_test(self, config: StressTestConfig) -> SyncPerformanceMetrics:
        """Run a stress test with the given configuration.

        Args:
            config: Stress test configuration

        Returns:
            Performance metrics from the stress test
        """
        self.logger.info("Starting stress test")

        # Reset metrics
        self.operation_times.clear()
        self.memory_samples.clear()
        self.cpu_samples.clear()

        start_time = time.time()

        # Start resource monitoring
        monitor_task = asyncio.create_task(self._monitor_resources())

        try:
            # Ramp up phase
            await self._ramp_up_operations(config)

            # Sustained load phase
            await self._sustained_load_operations(config)

            # Stop resource monitoring
            monitor_task.cancel()

            end_time = time.time()
            total_duration = end_time - start_time

            # Calculate metrics
            metrics = self._calculate_stress_metrics(total_duration, config)

            self.logger.info("Stress test completed")
            self.logger.info(
                f"Duration: {total_duration:.2f}s, Peak OPS: {metrics.operations_per_second:.2f}"
            )

            return metrics

        except Exception as e:
            monitor_task.cancel()
            self.logger.error(f"Stress test failed: {e}")
            raise

    async def run_latency_benchmark(
        self, operation_count: int = 1000
    ) -> SyncPerformanceMetrics:
        """Run latency benchmarking for different operation types.

        Args:
            operation_count: Number of operations to test per type

        Returns:
            Latency benchmark metrics
        """
        self.logger.info(
            f"Starting latency benchmark with {operation_count} operations"
        )

        operation_types = [
            SyncOperationType.CREATE_DOCUMENT,
            SyncOperationType.UPDATE_DOCUMENT,
            SyncOperationType.DELETE_DOCUMENT,
        ]

        all_times = []

        for operation_type in operation_types:
            self.logger.info(f"Benchmarking {operation_type.value}")

            for i in range(operation_count):
                start_time = time.perf_counter()

                try:
                    await self._execute_benchmark_operation(operation_type)
                    end_time = time.perf_counter()
                    operation_time = end_time - start_time
                    all_times.append(operation_time)

                except Exception as e:
                    self.logger.warning(f"Benchmark operation failed: {e}")

        # Calculate latency metrics
        metrics = SyncPerformanceMetrics()
        if all_times:
            metrics.total_operations = len(all_times)
            metrics.successful_operations = len(all_times)
            metrics.avg_operation_time = statistics.mean(all_times)
            metrics.min_operation_time = min(all_times)
            metrics.max_operation_time = max(all_times)
            metrics.p95_operation_time = statistics.quantiles(all_times, n=20)[
                18
            ]  # 95th percentile
            metrics.p99_operation_time = statistics.quantiles(all_times, n=100)[
                98
            ]  # 99th percentile
            metrics.success_rate = 1.0

        self.logger.info("Latency benchmark completed")
        return metrics

    async def run_memory_stress_test(
        self, max_documents: int = 10000
    ) -> SyncPerformanceMetrics:
        """Run memory stress test with increasing document count.

        Args:
            max_documents: Maximum number of documents to create

        Returns:
            Memory stress test metrics
        """
        self.logger.info(f"Starting memory stress test with {max_documents} documents")

        # Reset metrics
        self.memory_samples.clear()

        start_time = time.time()
        initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB

        # Start memory monitoring
        monitor_task = asyncio.create_task(self._monitor_memory_only())

        try:
            # Create documents in batches
            batch_size = 100
            for batch_start in range(0, max_documents, batch_size):
                batch_end = min(batch_start + batch_size, max_documents)

                # Create batch of documents
                tasks = []
                for i in range(batch_start, batch_end):
                    task = self._create_test_document(f"memory_test_{i}")
                    tasks.append(task)

                await asyncio.gather(*tasks, return_exceptions=True)

                # Log progress
                if batch_end % 1000 == 0:
                    current_memory = self.process.memory_info().rss / 1024 / 1024
                    self.logger.info(
                        f"Created {batch_end} documents, Memory: {current_memory:.1f}MB"
                    )

            # Stop monitoring
            monitor_task.cancel()

            end_time = time.time()
            final_memory = self.process.memory_info().rss / 1024 / 1024  # MB

            # Calculate metrics
            metrics = SyncPerformanceMetrics()
            metrics.total_duration = end_time - start_time
            metrics.total_operations = max_documents
            metrics.successful_operations = max_documents
            metrics.peak_memory_mb = (
                max(self.memory_samples) if self.memory_samples else final_memory
            )
            metrics.avg_memory_mb = (
                statistics.mean(self.memory_samples)
                if self.memory_samples
                else final_memory
            )

            self.logger.info("Memory stress test completed")
            self.logger.info(
                f"Memory growth: {initial_memory:.1f}MB -> {final_memory:.1f}MB"
            )

            return metrics

        except Exception as e:
            monitor_task.cancel()
            self.logger.error(f"Memory stress test failed: {e}")
            raise

    async def _simulate_user_operations(
        self,
        user_id: int,
        operation_count: int,
        operation_types: list[SyncOperationType],
    ) -> dict[str, Any]:
        """Simulate operations for a single user.

        Args:
            user_id: Unique user identifier
            operation_count: Number of operations to perform
            operation_types: Types of operations to perform

        Returns:
            User operation results
        """
        results = {
            "user_id": user_id,
            "successful_operations": 0,
            "failed_operations": 0,
            "operation_times": [],
        }

        for i in range(operation_count):
            operation_type = operation_types[i % len(operation_types)]

            start_time = time.perf_counter()

            try:
                await self._execute_test_operation(
                    operation_type, f"user_{user_id}_op_{i}"
                )
                end_time = time.perf_counter()

                operation_time = end_time - start_time
                results["operation_times"].append(operation_time)
                results["successful_operations"] += 1

            except Exception as e:
                results["failed_operations"] += 1
                self.logger.warning(f"User {user_id} operation {i} failed: {e}")

        return results

    async def _ramp_up_operations(self, config: StressTestConfig):
        """Gradually ramp up operation load."""
        ramp_steps = 10
        step_duration = config.ramp_up_seconds / ramp_steps

        for step in range(ramp_steps):
            concurrent_ops = int((step + 1) * config.concurrent_operations / ramp_steps)

            tasks = []
            for i in range(concurrent_ops):
                operation_type = self._select_operation_type(config)
                task = self._execute_test_operation(operation_type, f"ramp_{step}_{i}")
                tasks.append(task)

            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(step_duration)

    async def _sustained_load_operations(self, config: StressTestConfig):
        """Run sustained load operations."""
        sustained_duration = config.duration_seconds - config.ramp_up_seconds
        end_time = time.time() + sustained_duration

        operation_counter = 0

        while time.time() < end_time:
            # Create batch of concurrent operations
            tasks = []
            for i in range(config.concurrent_operations):
                operation_type = self._select_operation_type(config)
                task = self._execute_test_operation(
                    operation_type, f"sustained_{operation_counter}_{i}"
                )
                tasks.append(task)

            start_time = time.perf_counter()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time_batch = time.perf_counter()

            # Record timing
            batch_time = end_time_batch - start_time
            self.operation_times.extend([batch_time / len(tasks)] * len(tasks))

            operation_counter += 1

            # Small delay to prevent overwhelming the system
            await asyncio.sleep(0.1)

    def _select_operation_type(self, config: StressTestConfig) -> SyncOperationType:
        """Select operation type based on configuration percentages."""
        import random

        rand = random.random() * 100

        if rand < config.create_operations_percent:
            return SyncOperationType.CREATE_DOCUMENT
        elif rand < config.create_operations_percent + config.update_operations_percent:
            return SyncOperationType.UPDATE_DOCUMENT
        else:
            return SyncOperationType.DELETE_DOCUMENT

    async def _execute_test_operation(
        self, operation_type: SyncOperationType, operation_id: str
    ):
        """Execute a test operation of the specified type."""
        if operation_type == SyncOperationType.CREATE_DOCUMENT:
            await self._create_test_document(operation_id)
        elif operation_type == SyncOperationType.UPDATE_DOCUMENT:
            await self._update_test_document(operation_id)
        elif operation_type == SyncOperationType.DELETE_DOCUMENT:
            await self._delete_test_document(operation_id)

    async def _execute_benchmark_operation(self, operation_type: SyncOperationType):
        """Execute a benchmark operation."""
        operation_id = str(uuid.uuid4())
        await self._execute_test_operation(operation_type, operation_id)

    async def _create_test_document(self, document_id: str):
        """Create a test document."""
        content = f"Test document content for {document_id} " * 50  # ~1KB content
        metadata = {
            "title": f"Test Document {document_id}",
            "created_at": datetime.now(UTC).isoformat(),
            "test_type": "performance_test",
        }

        operation = EnhancedSyncOperation(
            operation_type=SyncOperationType.CREATE_DOCUMENT,
            entity_id=document_id,
            target_databases={DatabaseType.QDRANT, DatabaseType.NEO4J},
            operation_data={"content": content, **metadata},
            metadata=metadata,
        )

        await self.sync_system.queue_operation(operation)

    async def _update_test_document(self, document_id: str):
        """Update a test document."""
        metadata = {
            "title": f"Updated Test Document {document_id}",
            "updated_at": datetime.now(UTC).isoformat(),
            "version": 2,
        }

        operation = EnhancedSyncOperation(
            operation_type=SyncOperationType.UPDATE_DOCUMENT,
            entity_id=document_id,
            target_databases={DatabaseType.QDRANT, DatabaseType.NEO4J},
            operation_data=metadata,
            metadata=metadata,
        )

        await self.sync_system.queue_operation(operation)

    async def _delete_test_document(self, document_id: str):
        """Delete a test document."""
        operation = EnhancedSyncOperation(
            operation_type=SyncOperationType.DELETE_DOCUMENT,
            entity_id=document_id,
            target_databases={DatabaseType.QDRANT, DatabaseType.NEO4J},
            operation_data={},
            metadata={},
        )

        await self.sync_system.queue_operation(operation)

    async def _monitor_resources(self):
        """Monitor system resources during testing."""
        try:
            while True:
                # Memory usage
                memory_mb = self.process.memory_info().rss / 1024 / 1024
                self.memory_samples.append(memory_mb)

                # CPU usage
                cpu_percent = self.process.cpu_percent()
                self.cpu_samples.append(cpu_percent)

                await asyncio.sleep(1.0)  # Sample every second

        except asyncio.CancelledError:
            pass

    async def _monitor_memory_only(self):
        """Monitor only memory usage during testing."""
        try:
            while True:
                memory_mb = self.process.memory_info().rss / 1024 / 1024
                self.memory_samples.append(memory_mb)
                await asyncio.sleep(0.5)  # Sample every 500ms for memory stress test

        except asyncio.CancelledError:
            pass

    def _calculate_metrics(
        self, total_duration: float, results: list[Any]
    ) -> SyncPerformanceMetrics:
        """Calculate performance metrics from test results."""
        metrics = SyncPerformanceMetrics()

        # Basic timing
        metrics.total_duration = total_duration

        # Aggregate operation results
        all_operation_times = []
        total_successful = 0
        total_failed = 0

        for result in results:
            if isinstance(result, dict):
                total_successful += result.get("successful_operations", 0)
                total_failed += result.get("failed_operations", 0)
                all_operation_times.extend(result.get("operation_times", []))

        metrics.total_operations = total_successful + total_failed
        metrics.successful_operations = total_successful
        metrics.failed_operations = total_failed

        # Calculate timing metrics
        if all_operation_times:
            metrics.avg_operation_time = statistics.mean(all_operation_times)
            metrics.min_operation_time = min(all_operation_times)
            metrics.max_operation_time = max(all_operation_times)

            if len(all_operation_times) >= 20:
                metrics.p95_operation_time = statistics.quantiles(
                    all_operation_times, n=20
                )[18]
            if len(all_operation_times) >= 100:
                metrics.p99_operation_time = statistics.quantiles(
                    all_operation_times, n=100
                )[98]

        # Calculate throughput
        if total_duration > 0:
            metrics.operations_per_second = metrics.total_operations / total_duration
            metrics.documents_per_second = (
                metrics.successful_operations / total_duration
            )

        # Calculate resource metrics
        if self.memory_samples:
            metrics.peak_memory_mb = max(self.memory_samples)
            metrics.avg_memory_mb = statistics.mean(self.memory_samples)

        if self.cpu_samples:
            metrics.peak_cpu_percent = max(self.cpu_samples)
            metrics.avg_cpu_percent = statistics.mean(self.cpu_samples)

        # Calculate quality metrics
        if metrics.total_operations > 0:
            metrics.success_rate = (
                metrics.successful_operations / metrics.total_operations
            )
            metrics.error_rate = metrics.failed_operations / metrics.total_operations

        return metrics

    def _calculate_stress_metrics(
        self, total_duration: float, config: StressTestConfig
    ) -> SyncPerformanceMetrics:
        """Calculate stress test specific metrics."""
        metrics = SyncPerformanceMetrics()

        metrics.total_duration = total_duration

        # Calculate from operation times
        if self.operation_times:
            metrics.total_operations = len(self.operation_times)
            metrics.successful_operations = len(self.operation_times)
            metrics.avg_operation_time = statistics.mean(self.operation_times)
            metrics.min_operation_time = min(self.operation_times)
            metrics.max_operation_time = max(self.operation_times)

            if len(self.operation_times) >= 20:
                metrics.p95_operation_time = statistics.quantiles(
                    self.operation_times, n=20
                )[18]
            if len(self.operation_times) >= 100:
                metrics.p99_operation_time = statistics.quantiles(
                    self.operation_times, n=100
                )[98]

        # Calculate throughput
        if total_duration > 0:
            metrics.operations_per_second = metrics.total_operations / total_duration

        # Resource metrics
        if self.memory_samples:
            metrics.peak_memory_mb = max(self.memory_samples)
            metrics.avg_memory_mb = statistics.mean(self.memory_samples)

        if self.cpu_samples:
            metrics.peak_cpu_percent = max(self.cpu_samples)
            metrics.avg_cpu_percent = statistics.mean(self.cpu_samples)

        # Quality metrics
        if metrics.total_operations > 0:
            metrics.success_rate = (
                metrics.successful_operations / metrics.total_operations
            )

        return metrics


# Predefined load test scenarios
LOAD_TEST_SCENARIOS = [
    LoadTestScenario(
        name="Light Load",
        description="Light concurrent load with basic operations",
        concurrent_users=10,
        operations_per_user=50,
        operation_types=[
            SyncOperationType.CREATE_DOCUMENT,
            SyncOperationType.UPDATE_DOCUMENT,
        ],
        data_size_mb=5.0,
        expected_duration_seconds=60.0,
    ),
    LoadTestScenario(
        name="Medium Load",
        description="Medium concurrent load with mixed operations",
        concurrent_users=25,
        operations_per_user=100,
        operation_types=[
            SyncOperationType.CREATE_DOCUMENT,
            SyncOperationType.UPDATE_DOCUMENT,
            SyncOperationType.DELETE_DOCUMENT,
        ],
        data_size_mb=25.0,
        expected_duration_seconds=180.0,
    ),
    LoadTestScenario(
        name="Heavy Load",
        description="Heavy concurrent load with all operation types",
        concurrent_users=50,
        operations_per_user=200,
        operation_types=[
            SyncOperationType.CREATE_DOCUMENT,
            SyncOperationType.UPDATE_DOCUMENT,
            SyncOperationType.DELETE_DOCUMENT,
        ],
        data_size_mb=100.0,
        expected_duration_seconds=300.0,
    ),
    LoadTestScenario(
        name="Burst Load",
        description="High burst load to test system limits",
        concurrent_users=100,
        operations_per_user=50,
        operation_types=[SyncOperationType.CREATE_DOCUMENT],
        data_size_mb=50.0,
        expected_duration_seconds=120.0,
    ),
]


async def run_comprehensive_performance_suite(
    qdrant_manager: QdrantManager,
    neo4j_manager: Neo4jManager,
    id_mapping_manager: IDMappingManager,
    logger: logging.Logger | None = None,
) -> dict[str, SyncPerformanceMetrics]:
    """Run the complete performance testing suite.

    Args:
        qdrant_manager: QDrant database manager
        neo4j_manager: Neo4j database manager
        id_mapping_manager: ID mapping manager
        logger: Optional logger instance

    Returns:
        Dictionary of test results by test name
    """
    tester = SyncPerformanceTester(
        qdrant_manager, neo4j_manager, id_mapping_manager, logger
    )

    await tester.setup()

    try:
        results = {}

        # Run latency benchmark
        results["latency_benchmark"] = await tester.run_latency_benchmark()

        # Run load test scenarios
        for scenario in LOAD_TEST_SCENARIOS:
            results[f"load_test_{scenario.name.lower().replace(' ', '_')}"] = (
                await tester.run_load_test(scenario)
            )

        # Run stress test
        stress_config = StressTestConfig(duration_seconds=300, concurrent_operations=50)
        results["stress_test"] = await tester.run_stress_test(stress_config)

        # Run memory stress test
        results["memory_stress_test"] = await tester.run_memory_stress_test(
            max_documents=5000
        )

        return results

    finally:
        await tester.teardown()
