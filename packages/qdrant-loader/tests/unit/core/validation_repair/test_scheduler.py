"""Comprehensive tests for ValidationScheduler.

This module tests the scheduled validation capabilities using APScheduler,
including job management, persistence, event handling, and error scenarios.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from apscheduler.events import JobExecutionEvent
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from qdrant_loader.config.validation import ValidationConfig
from qdrant_loader.core.validation_repair.integrator import (
    ValidationRepairSystemIntegrator,
)
from qdrant_loader.core.validation_repair.models import ValidationReport
from qdrant_loader.core.validation_repair.scheduler import (
    ScheduledJobInfo,
    ValidationScheduler,
)


class TestScheduledJobInfo:
    """Test ScheduledJobInfo model."""

    def test_scheduled_job_info_creation(self):
        """Test creating a ScheduledJobInfo instance."""
        created_at = datetime.now()
        job_info = ScheduledJobInfo(
            job_id="test_job",
            name="Test Job",
            schedule_type="daily",
            schedule_config={"hour": 2, "minute": 30},
            created_at=created_at,
        )

        assert job_info.job_id == "test_job"
        assert job_info.name == "Test Job"
        assert job_info.schedule_type == "daily"
        assert job_info.schedule_config == {"hour": 2, "minute": 30}
        assert job_info.next_run_time is None
        assert job_info.last_run_time is None
        assert job_info.is_active is True
        assert job_info.created_at == created_at
        assert job_info.failure_count == 0
        assert job_info.last_error is None

    def test_scheduled_job_info_with_optional_fields(self):
        """Test ScheduledJobInfo with all optional fields."""
        created_at = datetime.now()
        next_run = datetime.now() + timedelta(hours=1)
        last_run = datetime.now() - timedelta(hours=1)

        job_info = ScheduledJobInfo(
            job_id="test_job",
            name="Test Job",
            schedule_type="interval",
            schedule_config={"seconds": 30},
            next_run_time=next_run,
            last_run_time=last_run,
            is_active=False,
            created_at=created_at,
            failure_count=2,
            last_error="Test error",
        )

        assert job_info.next_run_time == next_run
        assert job_info.last_run_time == last_run
        assert job_info.is_active is False
        assert job_info.failure_count == 2
        assert job_info.last_error == "Test error"


class TestValidationScheduler:
    """Test ValidationScheduler class."""

    @pytest.fixture
    def mock_validation_integrator(self):
        """Create a mock validation integrator."""
        integrator = AsyncMock(spec=ValidationRepairSystemIntegrator)

        # Mock trigger_validation to return a validation report
        mock_report = Mock(spec=ValidationReport)
        mock_report.issues = []
        integrator.trigger_validation.return_value = mock_report

        return integrator

    @pytest.fixture
    def validation_config(self):
        """Create a validation configuration."""
        return ValidationConfig(
            scheduled_job_timeout_seconds=300,
            schedule_overlap_prevention=True,
            schedule_persistence_enabled=False,
        )

    @pytest.fixture
    def scheduler(self, mock_validation_integrator, validation_config):
        """Create a ValidationScheduler instance."""
        return ValidationScheduler(
            validation_integrator=mock_validation_integrator,
            config=validation_config,
        )

    @pytest.fixture
    def scheduler_with_persistence(self, mock_validation_integrator):
        """Create a ValidationScheduler with persistence enabled."""
        config = ValidationConfig(
            schedule_persistence_enabled=True,
            scheduled_job_timeout_seconds=300,
        )
        return ValidationScheduler(
            validation_integrator=mock_validation_integrator,
            config=config,
            job_store_url="sqlite:///test.db",
        )

    # Scheduler Lifecycle Tests

    @pytest.mark.asyncio
    async def test_scheduler_initialization(
        self, scheduler, mock_validation_integrator, validation_config
    ):
        """Test scheduler initialization."""
        assert scheduler.validation_integrator == mock_validation_integrator
        assert scheduler.config == validation_config
        assert scheduler.job_store_url is None
        assert scheduler._scheduler is None
        assert scheduler._active_jobs == set()
        assert scheduler._job_info == {}
        assert not scheduler._shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_scheduler_start_memory_jobstore(self, scheduler):
        """Test starting scheduler with memory job store."""
        with patch(
            "qdrant_loader.core.validation_repair.scheduler.AsyncIOScheduler"
        ) as mock_scheduler_class:
            mock_scheduler_instance = AsyncMock()
            mock_scheduler_class.return_value = mock_scheduler_instance

            await scheduler.start()

            # Verify scheduler was created with correct configuration
            mock_scheduler_class.assert_called_once()
            call_kwargs = mock_scheduler_class.call_args[1]

            assert isinstance(call_kwargs["jobstores"]["default"], MemoryJobStore)
            assert isinstance(call_kwargs["executors"]["default"], AsyncIOExecutor)
            assert call_kwargs["job_defaults"]["coalesce"] is True
            assert call_kwargs["job_defaults"]["max_instances"] == 1
            assert call_kwargs["timezone"] == "UTC"

            # Verify event listener was added
            mock_scheduler_instance.add_listener.assert_called_once()

            # Verify scheduler was started
            mock_scheduler_instance.start.assert_called_once()
            assert scheduler._scheduler == mock_scheduler_instance

    @pytest.mark.asyncio
    async def test_scheduler_start_sqlalchemy_jobstore(
        self, scheduler_with_persistence
    ):
        """Test starting scheduler with SQLAlchemy job store."""
        with (
            patch(
                "qdrant_loader.core.validation_repair.scheduler.AsyncIOScheduler"
            ) as mock_scheduler_class,
            patch(
                "qdrant_loader.core.validation_repair.scheduler.SQLAlchemyJobStore"
            ) as mock_sqlalchemy_store,
        ):

            mock_scheduler_instance = AsyncMock()
            mock_scheduler_class.return_value = mock_scheduler_instance
            mock_store_instance = Mock()
            mock_sqlalchemy_store.return_value = mock_store_instance

            await scheduler_with_persistence.start()

            # Verify SQLAlchemy job store was created
            mock_sqlalchemy_store.assert_called_once_with(url="sqlite:///test.db")

            # Verify scheduler was created with SQLAlchemy store
            call_kwargs = mock_scheduler_class.call_args[1]
            assert call_kwargs["jobstores"]["default"] == mock_store_instance

    @pytest.mark.asyncio
    async def test_scheduler_start_already_running(self, scheduler, caplog):
        """Test starting scheduler when already running."""
        scheduler._scheduler = AsyncMock()

        await scheduler.start()

        assert "Scheduler is already running" in caplog.text

    @pytest.mark.asyncio
    async def test_scheduler_stop_graceful(self, scheduler):
        """Test graceful scheduler stop."""
        mock_scheduler = AsyncMock()
        scheduler._scheduler = mock_scheduler

        await scheduler.stop()

        mock_scheduler.shutdown.assert_called_once_with(wait=True)
        assert scheduler._scheduler is None

    @pytest.mark.asyncio
    async def test_scheduler_stop_with_active_jobs(self, scheduler):
        """Test scheduler stop with active jobs."""
        mock_scheduler = AsyncMock()
        scheduler._scheduler = mock_scheduler
        scheduler._active_jobs.add("job1")
        scheduler._active_jobs.add("job2")

        # Mock job completion
        async def clear_jobs():
            await asyncio.sleep(0.1)
            scheduler._active_jobs.clear()

        asyncio.create_task(clear_jobs())

        await scheduler.stop()

        mock_scheduler.shutdown.assert_called_once_with(wait=True)
        assert scheduler._scheduler is None

    @pytest.mark.asyncio
    async def test_scheduler_stop_timeout(self, scheduler):
        """Test scheduler stop with timeout."""
        mock_scheduler = AsyncMock()
        scheduler._scheduler = mock_scheduler
        scheduler._active_jobs.add("job1")  # Job that won't complete

        with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
            await scheduler.stop()

        mock_scheduler.shutdown.assert_called_once_with(wait=True)
        assert scheduler._scheduler is None

    @pytest.mark.asyncio
    async def test_scheduler_stop_not_running(self, scheduler):
        """Test stopping scheduler when not running."""
        await scheduler.stop()  # Should not raise any exception

    @pytest.mark.asyncio
    async def test_context_manager(self, scheduler):
        """Test scheduler as async context manager."""
        with (
            patch.object(scheduler, "start", new_callable=AsyncMock) as mock_start,
            patch.object(scheduler, "stop", new_callable=AsyncMock) as mock_stop,
        ):

            async with scheduler as ctx:
                assert ctx == scheduler

            mock_start.assert_called_once()
            mock_stop.assert_called_once()

    # Job Scheduling Tests

    @pytest.mark.asyncio
    async def test_schedule_validation_daily(self, scheduler):
        """Test scheduling a daily validation job."""
        mock_scheduler = Mock()  # Use Mock for synchronous methods
        scheduler._scheduler = mock_scheduler

        # Mock job for next run time update
        mock_job = Mock()
        mock_job.next_run_time = datetime.now() + timedelta(days=1)
        mock_scheduler.get_job.return_value = mock_job

        result = await scheduler.schedule_validation(
            job_id="daily_job",
            schedule_type="daily",
            schedule_config={"hour": 3, "minute": 15},
            scanners=["consistency", "integrity"],
            auto_repair=True,
            name="Daily Validation",
        )

        assert result is True

        # Verify job was added to scheduler
        mock_scheduler.add_job.assert_called_once()
        call_args = mock_scheduler.add_job.call_args

        assert call_args[1]["id"] == "daily_job"
        assert call_args[1]["name"] == "Daily Validation"
        assert isinstance(call_args[1]["trigger"], CronTrigger)
        assert call_args[1]["args"] == ["daily_job", ["consistency", "integrity"], True]

        # Verify job info was stored
        assert "daily_job" in scheduler._job_info
        job_info = scheduler._job_info["daily_job"]
        assert job_info.job_id == "daily_job"
        assert job_info.name == "Daily Validation"
        assert job_info.schedule_type == "daily"
        assert job_info.schedule_config == {"hour": 3, "minute": 15}

    @pytest.mark.asyncio
    async def test_schedule_validation_hourly(self, scheduler):
        """Test scheduling an hourly validation job."""
        mock_scheduler = Mock()
        scheduler._scheduler = mock_scheduler
        mock_scheduler.get_job.return_value = None

        result = await scheduler.schedule_validation(
            job_id="hourly_job",
            schedule_type="hourly",
        )

        assert result is True

        # Verify correct trigger type
        call_args = mock_scheduler.add_job.call_args
        assert isinstance(call_args[1]["trigger"], IntervalTrigger)

    @pytest.mark.asyncio
    async def test_schedule_validation_weekly(self, scheduler):
        """Test scheduling a weekly validation job."""
        mock_scheduler = Mock()
        scheduler._scheduler = mock_scheduler
        mock_scheduler.get_job.return_value = None

        result = await scheduler.schedule_validation(
            job_id="weekly_job",
            schedule_type="weekly",
            schedule_config={"day_of_week": 1, "hour": 4},
        )

        assert result is True

        # Verify correct trigger type
        call_args = mock_scheduler.add_job.call_args
        assert isinstance(call_args[1]["trigger"], CronTrigger)

    @pytest.mark.asyncio
    async def test_schedule_validation_cron(self, scheduler):
        """Test scheduling with cron trigger."""
        mock_scheduler = Mock()
        scheduler._scheduler = mock_scheduler
        mock_scheduler.get_job.return_value = None

        result = await scheduler.schedule_validation(
            job_id="cron_job",
            schedule_type="cron",
            schedule_config={"hour": "*/2", "minute": "0"},
        )

        assert result is True

        # Verify correct trigger type
        call_args = mock_scheduler.add_job.call_args
        assert isinstance(call_args[1]["trigger"], CronTrigger)

    @pytest.mark.asyncio
    async def test_schedule_validation_interval(self, scheduler):
        """Test scheduling with interval trigger."""
        mock_scheduler = Mock()
        scheduler._scheduler = mock_scheduler
        mock_scheduler.get_job.return_value = None

        result = await scheduler.schedule_validation(
            job_id="interval_job",
            schedule_type="interval",
            schedule_config={"minutes": 30},
        )

        assert result is True

        # Verify correct trigger type
        call_args = mock_scheduler.add_job.call_args
        assert isinstance(call_args[1]["trigger"], IntervalTrigger)

    @pytest.mark.asyncio
    async def test_schedule_validation_invalid_schedule_type(self, scheduler):
        """Test scheduling with invalid schedule type."""
        mock_scheduler = Mock()
        scheduler._scheduler = mock_scheduler

        result = await scheduler.schedule_validation(
            job_id="invalid_job",
            schedule_type="invalid_type",
        )

        assert result is False
        mock_scheduler.add_job.assert_not_called()

    @pytest.mark.asyncio
    async def test_schedule_validation_scheduler_not_running(self, scheduler, caplog):
        """Test scheduling when scheduler is not running."""
        result = await scheduler.schedule_validation(job_id="test_job")

        assert result is False
        assert "Scheduler is not running" in caplog.text

    @pytest.mark.asyncio
    async def test_schedule_validation_duplicate_job(self, scheduler, caplog):
        """Test scheduling a job with duplicate ID."""
        mock_scheduler = Mock()
        scheduler._scheduler = mock_scheduler
        scheduler._job_info["existing_job"] = ScheduledJobInfo(
            job_id="existing_job",
            name="Existing Job",
            schedule_type="daily",
            schedule_config={},
            created_at=datetime.now(),
        )

        result = await scheduler.schedule_validation(job_id="existing_job")

        assert result is False
        assert "Job existing_job already exists" in caplog.text

    @pytest.mark.asyncio
    async def test_schedule_validation_exception(self, scheduler, caplog):
        """Test scheduling with exception."""
        mock_scheduler = Mock()
        mock_scheduler.add_job.side_effect = Exception("Scheduling error")
        scheduler._scheduler = mock_scheduler

        result = await scheduler.schedule_validation(job_id="error_job")

        assert result is False
        assert (
            "Failed to schedule validation job error_job: Scheduling error"
            in caplog.text
        )

    # Job Management Tests

    @pytest.mark.asyncio
    async def test_unschedule_validation(self, scheduler):
        """Test unscheduling a validation job."""
        mock_scheduler = Mock()
        scheduler._scheduler = mock_scheduler
        scheduler._job_info["test_job"] = ScheduledJobInfo(
            job_id="test_job",
            name="Test Job",
            schedule_type="daily",
            schedule_config={},
            created_at=datetime.now(),
        )

        result = await scheduler.unschedule_validation("test_job")

        assert result is True
        mock_scheduler.remove_job.assert_called_once_with("test_job")
        assert "test_job" not in scheduler._job_info

    @pytest.mark.asyncio
    async def test_unschedule_validation_scheduler_not_running(self, scheduler, caplog):
        """Test unscheduling when scheduler is not running."""
        result = await scheduler.unschedule_validation("test_job")

        assert result is False
        assert "Scheduler is not running" in caplog.text

    @pytest.mark.asyncio
    async def test_unschedule_validation_exception(self, scheduler, caplog):
        """Test unscheduling with exception."""
        mock_scheduler = Mock()
        mock_scheduler.remove_job.side_effect = Exception("Remove error")
        scheduler._scheduler = mock_scheduler

        result = await scheduler.unschedule_validation("test_job")

        assert result is False
        assert (
            "Failed to unschedule validation job test_job: Remove error" in caplog.text
        )

    @pytest.mark.asyncio
    async def test_pause_job(self, scheduler):
        """Test pausing a validation job."""
        mock_scheduler = Mock()
        scheduler._scheduler = mock_scheduler
        scheduler._job_info["test_job"] = ScheduledJobInfo(
            job_id="test_job",
            name="Test Job",
            schedule_type="daily",
            schedule_config={},
            created_at=datetime.now(),
            is_active=True,
        )

        result = await scheduler.pause_job("test_job")

        assert result is True
        mock_scheduler.pause_job.assert_called_once_with("test_job")
        assert scheduler._job_info["test_job"].is_active is False

    @pytest.mark.asyncio
    async def test_pause_job_scheduler_not_running(self, scheduler, caplog):
        """Test pausing when scheduler is not running."""
        result = await scheduler.pause_job("test_job")

        assert result is False
        assert "Scheduler is not running" in caplog.text

    @pytest.mark.asyncio
    async def test_pause_job_exception(self, scheduler, caplog):
        """Test pausing with exception."""
        mock_scheduler = Mock()
        mock_scheduler.pause_job.side_effect = Exception("Pause error")
        scheduler._scheduler = mock_scheduler

        result = await scheduler.pause_job("test_job")

        assert result is False
        assert "Failed to pause validation job test_job: Pause error" in caplog.text

    @pytest.mark.asyncio
    async def test_resume_job(self, scheduler):
        """Test resuming a validation job."""
        mock_scheduler = Mock()
        scheduler._scheduler = mock_scheduler
        scheduler._job_info["test_job"] = ScheduledJobInfo(
            job_id="test_job",
            name="Test Job",
            schedule_type="daily",
            schedule_config={},
            created_at=datetime.now(),
            is_active=False,
        )

        result = await scheduler.resume_job("test_job")

        assert result is True
        mock_scheduler.resume_job.assert_called_once_with("test_job")
        assert scheduler._job_info["test_job"].is_active is True

    @pytest.mark.asyncio
    async def test_resume_job_scheduler_not_running(self, scheduler, caplog):
        """Test resuming when scheduler is not running."""
        result = await scheduler.resume_job("test_job")

        assert result is False
        assert "Scheduler is not running" in caplog.text

    @pytest.mark.asyncio
    async def test_resume_job_exception(self, scheduler, caplog):
        """Test resuming with exception."""
        mock_scheduler = Mock()
        mock_scheduler.resume_job.side_effect = Exception("Resume error")
        scheduler._scheduler = mock_scheduler

        result = await scheduler.resume_job("test_job")

        assert result is False
        assert "Failed to resume validation job test_job: Resume error" in caplog.text

    # Job Information Tests

    def test_get_job_info_exists(self, scheduler):
        """Test getting job information for existing job."""
        created_at = datetime.now()
        next_run = datetime.now() + timedelta(hours=1)

        scheduler._job_info["test_job"] = ScheduledJobInfo(
            job_id="test_job",
            name="Test Job",
            schedule_type="daily",
            schedule_config={},
            created_at=created_at,
        )

        # Mock scheduler to update next run time
        mock_scheduler = Mock()
        mock_job = Mock()
        mock_job.next_run_time = next_run
        mock_scheduler.get_job.return_value = mock_job
        scheduler._scheduler = mock_scheduler

        job_info = scheduler.get_job_info("test_job")

        assert job_info is not None
        assert job_info.job_id == "test_job"
        assert job_info.next_run_time == next_run

    def test_get_job_info_not_exists(self, scheduler):
        """Test getting job information for non-existing job."""
        job_info = scheduler.get_job_info("nonexistent_job")
        assert job_info is None

    def test_list_jobs(self, scheduler):
        """Test listing all scheduled jobs."""
        created_at = datetime.now()
        next_run1 = datetime.now() + timedelta(hours=1)
        next_run2 = datetime.now() + timedelta(hours=2)

        scheduler._job_info["job1"] = ScheduledJobInfo(
            job_id="job1",
            name="Job 1",
            schedule_type="daily",
            schedule_config={},
            created_at=created_at,
        )
        scheduler._job_info["job2"] = ScheduledJobInfo(
            job_id="job2",
            name="Job 2",
            schedule_type="hourly",
            schedule_config={},
            created_at=created_at,
        )

        # Mock scheduler
        mock_scheduler = Mock()
        mock_job1 = Mock()
        mock_job1.next_run_time = next_run1
        mock_job2 = Mock()
        mock_job2.next_run_time = next_run2
        mock_scheduler.get_job.side_effect = lambda job_id: (
            mock_job1 if job_id == "job1" else mock_job2
        )
        scheduler._scheduler = mock_scheduler

        jobs = scheduler.list_jobs()

        assert len(jobs) == 2
        job_ids = [job.job_id for job in jobs]
        assert "job1" in job_ids
        assert "job2" in job_ids

    def test_get_active_jobs(self, scheduler):
        """Test getting active job IDs."""
        scheduler._active_jobs.add("job1")
        scheduler._active_jobs.add("job2")

        active_jobs = scheduler.get_active_jobs()

        assert active_jobs == {"job1", "job2"}
        # Verify it returns a copy
        active_jobs.add("job3")
        assert scheduler._active_jobs == {"job1", "job2"}

    # Job Execution Tests

    @pytest.mark.asyncio
    async def test_run_scheduled_validation_success(
        self, scheduler, mock_validation_integrator
    ):
        """Test successful scheduled validation execution."""
        mock_report = Mock(spec=ValidationReport)
        mock_report.issues = ["issue1", "issue2"]
        mock_validation_integrator.trigger_validation.return_value = mock_report

        await scheduler._run_scheduled_validation(
            job_id="test_job",
            scanners=["consistency"],
            auto_repair=True,
        )

        mock_validation_integrator.trigger_validation.assert_called_once_with(
            scanners=["consistency"],
            auto_repair=True,
        )
        assert "test_job" not in scheduler._active_jobs

    @pytest.mark.asyncio
    async def test_run_scheduled_validation_no_report(
        self, scheduler, mock_validation_integrator, caplog
    ):
        """Test scheduled validation with no report returned."""
        mock_validation_integrator.trigger_validation.return_value = None

        await scheduler._run_scheduled_validation(job_id="test_job")

        assert "Scheduled validation test_job returned no report" in caplog.text

    @pytest.mark.asyncio
    async def test_run_scheduled_validation_timeout(
        self, scheduler, mock_validation_integrator
    ):
        """Test scheduled validation timeout."""
        mock_validation_integrator.trigger_validation.side_effect = (
            TimeoutError()
        )

        with pytest.raises(asyncio.TimeoutError):
            await scheduler._run_scheduled_validation(job_id="test_job")

        assert "test_job" not in scheduler._active_jobs

    @pytest.mark.asyncio
    async def test_run_scheduled_validation_exception(
        self, scheduler, mock_validation_integrator
    ):
        """Test scheduled validation with exception."""
        mock_validation_integrator.trigger_validation.side_effect = Exception(
            "Validation error"
        )

        with pytest.raises(Exception, match="Validation error"):
            await scheduler._run_scheduled_validation(job_id="test_job")

        assert "test_job" not in scheduler._active_jobs

    @pytest.mark.asyncio
    async def test_run_scheduled_validation_shutdown(
        self, scheduler, mock_validation_integrator, caplog
    ):
        """Test scheduled validation during shutdown."""
        scheduler._shutdown_event.set()

        await scheduler._run_scheduled_validation(job_id="test_job")

        assert "Skipping scheduled validation test_job due to shutdown" in caplog.text
        mock_validation_integrator.trigger_validation.assert_not_called()

    # Event Handling Tests

    def test_job_executed_listener_success(self, scheduler):
        """Test job execution event listener for successful job."""
        scheduler._job_info["test_job"] = ScheduledJobInfo(
            job_id="test_job",
            name="Test Job",
            schedule_type="daily",
            schedule_config={},
            created_at=datetime.now(),
            failure_count=1,
            last_error="Previous error",
        )
        scheduler._active_jobs.add("test_job")

        # Mock successful event
        event = Mock(spec=JobExecutionEvent)
        event.job_id = "test_job"
        event.exception = None

        scheduler._job_executed_listener(event)

        job_info = scheduler._job_info["test_job"]
        assert job_info.failure_count == 0
        assert job_info.last_error is None
        assert job_info.last_run_time is not None
        assert "test_job" not in scheduler._active_jobs

    def test_job_executed_listener_failure(self, scheduler, caplog):
        """Test job execution event listener for failed job."""
        scheduler._job_info["test_job"] = ScheduledJobInfo(
            job_id="test_job",
            name="Test Job",
            schedule_type="daily",
            schedule_config={},
            created_at=datetime.now(),
            failure_count=0,
        )
        scheduler._active_jobs.add("test_job")

        # Mock failed event
        event = Mock(spec=JobExecutionEvent)
        event.job_id = "test_job"
        event.exception = Exception("Job failed")

        scheduler._job_executed_listener(event)

        job_info = scheduler._job_info["test_job"]
        assert job_info.failure_count == 1
        assert job_info.last_error == "Job failed"
        assert job_info.last_run_time is not None
        assert "test_job" not in scheduler._active_jobs
        assert "Scheduled validation job test_job failed: Job failed" in caplog.text

    def test_job_executed_listener_unknown_job(self, scheduler):
        """Test job execution event listener for unknown job."""
        scheduler._active_jobs.add("unknown_job")

        # Mock event for unknown job
        event = Mock(spec=JobExecutionEvent)
        event.job_id = "unknown_job"
        event.exception = None

        scheduler._job_executed_listener(event)

        # Should not crash, just remove from active jobs
        assert "unknown_job" not in scheduler._active_jobs

    # Trigger Creation Tests

    def test_create_trigger_hourly(self, scheduler):
        """Test creating hourly trigger."""
        trigger = scheduler._create_trigger("hourly", {"minutes": 30})

        assert isinstance(trigger, IntervalTrigger)

    def test_create_trigger_daily(self, scheduler):
        """Test creating daily trigger."""
        trigger = scheduler._create_trigger("daily", {"hour": 3, "minute": 15})

        assert isinstance(trigger, CronTrigger)

    def test_create_trigger_weekly(self, scheduler):
        """Test creating weekly trigger."""
        trigger = scheduler._create_trigger("weekly", {"day_of_week": 1, "hour": 4})

        assert isinstance(trigger, CronTrigger)

    def test_create_trigger_cron(self, scheduler):
        """Test creating cron trigger."""
        trigger = scheduler._create_trigger("cron", {"hour": "*/2", "minute": "0"})

        assert isinstance(trigger, CronTrigger)

    def test_create_trigger_interval(self, scheduler):
        """Test creating interval trigger."""
        trigger = scheduler._create_trigger("interval", {"minutes": 30})

        assert isinstance(trigger, IntervalTrigger)

    def test_create_trigger_invalid(self, scheduler):
        """Test creating trigger with invalid type."""
        with pytest.raises(ValueError, match="Unsupported schedule type: invalid"):
            scheduler._create_trigger("invalid", {})

    # Integration Tests

    @pytest.mark.asyncio
    async def test_full_job_lifecycle(self, scheduler):
        """Test complete job lifecycle: schedule -> execute -> unschedule."""
        mock_scheduler = Mock()
        scheduler._scheduler = mock_scheduler

        # Mock job for next run time
        mock_job = Mock()
        mock_job.next_run_time = datetime.now() + timedelta(hours=1)
        mock_scheduler.get_job.return_value = mock_job

        # Schedule job
        result = await scheduler.schedule_validation(
            job_id="lifecycle_job",
            schedule_type="daily",
            name="Lifecycle Test Job",
        )
        assert result is True
        assert "lifecycle_job" in scheduler._job_info

        # Pause job
        result = await scheduler.pause_job("lifecycle_job")
        assert result is True
        assert scheduler._job_info["lifecycle_job"].is_active is False

        # Resume job
        result = await scheduler.resume_job("lifecycle_job")
        assert result is True
        assert scheduler._job_info["lifecycle_job"].is_active is True

        # Get job info
        job_info = scheduler.get_job_info("lifecycle_job")
        assert job_info is not None
        assert job_info.job_id == "lifecycle_job"

        # List jobs
        jobs = scheduler.list_jobs()
        assert len(jobs) == 1
        assert jobs[0].job_id == "lifecycle_job"

        # Unschedule job
        result = await scheduler.unschedule_validation("lifecycle_job")
        assert result is True
        assert "lifecycle_job" not in scheduler._job_info

    @pytest.mark.asyncio
    async def test_multiple_concurrent_jobs(
        self, scheduler, mock_validation_integrator
    ):
        """Test handling multiple concurrent validation jobs."""
        # Setup multiple validation reports
        reports = []
        for i in range(3):
            mock_report = Mock(spec=ValidationReport)
            mock_report.issues = [f"issue_{i}"]
            reports.append(mock_report)

        mock_validation_integrator.trigger_validation.side_effect = reports

        # Run multiple jobs concurrently
        tasks = []
        for i in range(3):
            task = asyncio.create_task(
                scheduler._run_scheduled_validation(
                    job_id=f"job_{i}",
                    scanners=[f"scanner_{i}"],
                    auto_repair=False,
                )
            )
            tasks.append(task)

        # Wait for all jobs to complete
        await asyncio.gather(*tasks)

        # Verify all validation calls were made
        assert mock_validation_integrator.trigger_validation.call_count == 3

        # Verify no jobs are active
        assert len(scheduler._active_jobs) == 0

    @pytest.mark.asyncio
    async def test_scheduler_persistence_configuration(
        self, scheduler_with_persistence
    ):
        """Test scheduler configuration with persistence enabled."""
        with (
            patch(
                "qdrant_loader.core.validation_repair.scheduler.AsyncIOScheduler"
            ) as mock_scheduler_class,
            patch(
                "qdrant_loader.core.validation_repair.scheduler.SQLAlchemyJobStore"
            ) as mock_sqlalchemy_store,
        ):

            mock_scheduler_instance = AsyncMock()
            mock_scheduler_class.return_value = mock_scheduler_instance
            mock_store_instance = Mock()
            mock_sqlalchemy_store.return_value = mock_store_instance

            await scheduler_with_persistence.start()

            # Verify SQLAlchemy store was configured
            mock_sqlalchemy_store.assert_called_once_with(url="sqlite:///test.db")

            # Verify scheduler configuration
            call_kwargs = mock_scheduler_class.call_args[1]
            assert call_kwargs["jobstores"]["default"] == mock_store_instance
            assert isinstance(call_kwargs["executors"]["default"], AsyncIOExecutor)

    @pytest.mark.asyncio
    async def test_wait_for_jobs_completion(self, scheduler):
        """Test waiting for job completion during shutdown."""
        scheduler._active_jobs.add("job1")
        scheduler._active_jobs.add("job2")

        # Simulate jobs completing after a delay
        async def complete_jobs():
            await asyncio.sleep(0.1)
            scheduler._active_jobs.clear()

        # Start the task and ensure it's awaited
        task = asyncio.create_task(complete_jobs())

        # Should complete when jobs are done
        await scheduler._wait_for_jobs_completion()

        # Ensure the completion task is done
        await task

        assert len(scheduler._active_jobs) == 0
