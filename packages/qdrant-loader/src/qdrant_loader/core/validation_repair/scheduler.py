"""Scheduled validation jobs using APScheduler.

This module provides scheduled validation capabilities using APScheduler,
including job management, persistence, and conflict resolution.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

from apscheduler.events import (
    EVENT_JOB_ERROR,
    EVENT_JOB_EXECUTED,
    EVENT_JOB_MISSED,
    JobExecutionEvent,
)
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from pydantic import BaseModel

from ...config.validation import ValidationConfig
from .integrator import ValidationRepairSystemIntegrator

logger = logging.getLogger(__name__)


class ScheduledJobInfo(BaseModel):
    """Information about a scheduled validation job."""

    job_id: str
    name: str
    schedule_type: str  # 'interval' or 'cron'
    schedule_config: dict[str, Any]
    next_run_time: datetime | None = None
    last_run_time: datetime | None = None
    is_active: bool = True
    created_at: datetime
    failure_count: int = 0
    last_error: str | None = None


class ValidationScheduler:
    """Scheduler for automated validation jobs using APScheduler."""

    def __init__(
        self,
        validation_integrator: ValidationRepairSystemIntegrator,
        config: ValidationConfig,
        job_store_url: str | None = None,
    ):
        """Initialize the validation scheduler.

        Args:
            validation_integrator: The validation system integrator
            config: Validation configuration
            job_store_url: Optional SQLAlchemy URL for job persistence
        """
        self.validation_integrator = validation_integrator
        self.config = config
        self.job_store_url = job_store_url
        self._scheduler: AsyncIOScheduler | None = None
        self._active_jobs: set[str] = set()
        self._job_info: dict[str, ScheduledJobInfo] = {}
        self._shutdown_event = asyncio.Event()

    async def start(self) -> None:
        """Start the scheduler."""
        if self._scheduler is not None:
            logger.warning("Scheduler is already running")
            return

        # Configure job stores
        jobstores = {}
        if self.config.schedule_persistence_enabled and self.job_store_url:
            jobstores["default"] = SQLAlchemyJobStore(url=self.job_store_url)
        else:
            jobstores["default"] = MemoryJobStore()

        # Configure executors
        executors = {"default": AsyncIOExecutor()}

        # Job defaults
        job_defaults = {
            "coalesce": self.config.schedule_overlap_prevention,
            "max_instances": 1 if self.config.schedule_overlap_prevention else 3,
            "misfire_grace_time": 300,  # 5 minutes
        }

        # Create scheduler
        self._scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone="UTC",
        )

        # Add event listeners
        self._scheduler.add_listener(
            self._job_executed_listener,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED,
        )

        # Start the scheduler
        self._scheduler.start()
        logger.info("Validation scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler gracefully."""
        if self._scheduler is None:
            return

        logger.info("Stopping validation scheduler...")
        self._shutdown_event.set()

        # Wait for active jobs to complete (with timeout)
        if self._active_jobs:
            logger.info(
                f"Waiting for {len(self._active_jobs)} active jobs to complete..."
            )
            try:
                await asyncio.wait_for(self._wait_for_jobs_completion(), timeout=60.0)
            except TimeoutError:
                logger.warning("Timeout waiting for jobs to complete, forcing shutdown")

        # Shutdown scheduler
        self._scheduler.shutdown(wait=True)
        self._scheduler = None
        logger.info("Validation scheduler stopped")

    async def _wait_for_jobs_completion(self) -> None:
        """Wait for all active jobs to complete."""
        while self._active_jobs:
            await asyncio.sleep(1.0)

    def _job_executed_listener(self, event: JobExecutionEvent) -> None:
        """Handle job execution events."""
        job_id = event.job_id

        if event.exception:
            logger.error(f"Scheduled validation job {job_id} failed: {event.exception}")
            if job_id in self._job_info:
                self._job_info[job_id].failure_count += 1
                self._job_info[job_id].last_error = str(event.exception)
        else:
            logger.info(f"Scheduled validation job {job_id} completed successfully")
            if job_id in self._job_info:
                self._job_info[job_id].failure_count = 0
                self._job_info[job_id].last_error = None

        # Update last run time
        if job_id in self._job_info:
            self._job_info[job_id].last_run_time = datetime.now()

        # Remove from active jobs
        self._active_jobs.discard(job_id)

    async def schedule_validation(
        self,
        job_id: str,
        schedule_type: str = "daily",
        schedule_config: dict[str, Any] | None = None,
        scanners: list[str] | None = None,
        auto_repair: bool = False,
        name: str | None = None,
    ) -> bool:
        """Schedule a validation job.

        Args:
            job_id: Unique identifier for the job
            schedule_type: Type of schedule ('hourly', 'daily', 'weekly', 'cron', 'interval')
            schedule_config: Additional configuration for the schedule
            scanners: List of scanner types to run
            auto_repair: Whether to automatically repair issues
            name: Human-readable name for the job

        Returns:
            True if job was scheduled successfully
        """
        if self._scheduler is None:
            logger.error("Scheduler is not running")
            return False

        if job_id in self._job_info:
            logger.warning(f"Job {job_id} already exists")
            return False

        try:
            # Create trigger based on schedule type
            trigger = self._create_trigger(schedule_type, schedule_config or {})

            # Schedule the job
            self._scheduler.add_job(
                func=self._run_scheduled_validation,
                trigger=trigger,
                id=job_id,
                name=name or f"Validation Job {job_id}",
                args=[job_id, scanners, auto_repair],
                replace_existing=False,
            )

            # Store job info
            self._job_info[job_id] = ScheduledJobInfo(
                job_id=job_id,
                name=name or f"Validation Job {job_id}",
                schedule_type=schedule_type,
                schedule_config=schedule_config or {},
                created_at=datetime.now(),
            )

            # Update next run time
            job = self._scheduler.get_job(job_id)
            if job and job.next_run_time:
                self._job_info[job_id].next_run_time = job.next_run_time

            logger.info(
                f"Scheduled validation job {job_id} with {schedule_type} schedule"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to schedule validation job {job_id}: {e}")
            return False

    def _create_trigger(self, schedule_type: str, config: dict[str, Any]) -> Any:
        """Create an APScheduler trigger based on schedule type and config."""
        if schedule_type == "hourly":
            return IntervalTrigger(hours=1, **config)
        elif schedule_type == "daily":
            return CronTrigger(
                hour=config.get("hour", 2), minute=config.get("minute", 0)
            )
        elif schedule_type == "weekly":
            return CronTrigger(
                day_of_week=config.get("day_of_week", 0),  # Monday
                hour=config.get("hour", 2),
                minute=config.get("minute", 0),
            )
        elif schedule_type == "cron":
            return CronTrigger(**config)
        elif schedule_type == "interval":
            return IntervalTrigger(**config)
        else:
            raise ValueError(f"Unsupported schedule type: {schedule_type}")

    async def _run_scheduled_validation(
        self,
        job_id: str,
        scanners: list[str] | None = None,
        auto_repair: bool = False,
    ) -> None:
        """Run a scheduled validation job.

        Args:
            job_id: The job identifier
            scanners: List of scanner types to run
            auto_repair: Whether to automatically repair issues
        """
        if self._shutdown_event.is_set():
            logger.info(f"Skipping scheduled validation {job_id} due to shutdown")
            return

        self._active_jobs.add(job_id)
        logger.info(f"Starting scheduled validation job {job_id}")

        try:
            # Run validation with timeout
            validation_report = await asyncio.wait_for(
                self.validation_integrator.trigger_validation(
                    scanners=scanners,
                    auto_repair=auto_repair,
                ),
                timeout=self.config.scheduled_job_timeout_seconds,
            )

            if validation_report:
                logger.info(
                    f"Scheduled validation {job_id} completed: "
                    f"{len(validation_report.issues)} issues found"
                )
            else:
                logger.warning(f"Scheduled validation {job_id} returned no report")

        except TimeoutError:
            logger.error(f"Scheduled validation job {job_id} timed out")
            raise
        except Exception as e:
            logger.error(f"Scheduled validation job {job_id} failed: {e}")
            raise
        finally:
            self._active_jobs.discard(job_id)

    async def unschedule_validation(self, job_id: str) -> bool:
        """Remove a scheduled validation job.

        Args:
            job_id: The job identifier

        Returns:
            True if job was removed successfully
        """
        if self._scheduler is None:
            logger.error("Scheduler is not running")
            return False

        try:
            self._scheduler.remove_job(job_id)
            self._job_info.pop(job_id, None)
            logger.info(f"Unscheduled validation job {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to unschedule validation job {job_id}: {e}")
            return False

    async def pause_job(self, job_id: str) -> bool:
        """Pause a scheduled validation job.

        Args:
            job_id: The job identifier

        Returns:
            True if job was paused successfully
        """
        if self._scheduler is None:
            logger.error("Scheduler is not running")
            return False

        try:
            self._scheduler.pause_job(job_id)
            if job_id in self._job_info:
                self._job_info[job_id].is_active = False
            logger.info(f"Paused validation job {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to pause validation job {job_id}: {e}")
            return False

    async def resume_job(self, job_id: str) -> bool:
        """Resume a paused validation job.

        Args:
            job_id: The job identifier

        Returns:
            True if job was resumed successfully
        """
        if self._scheduler is None:
            logger.error("Scheduler is not running")
            return False

        try:
            self._scheduler.resume_job(job_id)
            if job_id in self._job_info:
                self._job_info[job_id].is_active = True
            logger.info(f"Resumed validation job {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to resume validation job {job_id}: {e}")
            return False

    def get_job_info(self, job_id: str) -> ScheduledJobInfo | None:
        """Get information about a scheduled job.

        Args:
            job_id: The job identifier

        Returns:
            Job information or None if not found
        """
        job_info = self._job_info.get(job_id)
        if job_info and self._scheduler:
            # Update next run time from scheduler
            job = self._scheduler.get_job(job_id)
            if job:
                job_info.next_run_time = job.next_run_time
        return job_info

    def list_jobs(self) -> list[ScheduledJobInfo]:
        """List all scheduled validation jobs.

        Returns:
            List of job information
        """
        jobs = []
        for job_id, job_info in self._job_info.items():
            if self._scheduler:
                # Update next run time from scheduler
                job = self._scheduler.get_job(job_id)
                if job:
                    job_info.next_run_time = job.next_run_time
            jobs.append(job_info)
        return jobs

    def get_active_jobs(self) -> set[str]:
        """Get the set of currently active job IDs.

        Returns:
            Set of active job IDs
        """
        return self._active_jobs.copy()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
