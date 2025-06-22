"""Background Task Scheduler for QDrant Loader Daemon.

This module provides scheduled task execution capabilities for the daemon,
including periodic validation, monitoring, and maintenance operations.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Callable, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.job import Job
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, JobExecutionEvent

from .service import BaseService

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Background task status."""
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskInfo:
    """Information about a background task."""
    id: str
    name: str
    status: TaskStatus
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    run_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None


@dataclass
class ScheduleConfig:
    """Configuration for scheduled tasks."""
    
    # Validation schedule
    validation_interval_minutes: int = 60
    validation_enabled: bool = True
    
    # Health check schedule  
    health_check_interval_minutes: int = 5
    health_check_enabled: bool = True
    
    # Cleanup schedule
    cleanup_interval_hours: int = 24
    cleanup_enabled: bool = True
    
    # Custom schedules
    custom_schedules: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class BackgroundScheduler(BaseService):
    """Background task scheduler service."""
    
    def __init__(self, config: Optional[ScheduleConfig] = None):
        """Initialize background scheduler.
        
        Args:
            config: Schedule configuration. Uses defaults if None.
        """
        super().__init__("background_scheduler")
        self.config = config or ScheduleConfig()
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._tasks: Dict[str, TaskInfo] = {}
        self._task_handlers: Dict[str, Callable] = {}
        
    async def _start_impl(self) -> None:
        """Start the scheduler service."""
        # Create and configure scheduler
        self._scheduler = AsyncIOScheduler(
            timezone="UTC",
            job_defaults={
                'coalesce': True,
                'max_instances': 1,
                'misfire_grace_time': 30
            }
        )
        
        # Set up event listeners
        self._scheduler.add_listener(
            self._job_executed_listener,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
        )
        
        # Start scheduler
        self._scheduler.start()
        logger.info("Background scheduler started")
        
        # Schedule default tasks
        await self._schedule_default_tasks()
    
    async def _stop_impl(self) -> None:
        """Stop the scheduler service."""
        if self._scheduler:
            self._scheduler.shutdown(wait=True)
            self._scheduler = None
            
        # Clear task tracking
        self._tasks.clear()
        logger.info("Background scheduler stopped")
    
    async def health_check(self) -> bool:
        """Check if scheduler is healthy."""
        return (
            self._scheduler is not None and 
            self._scheduler.running
        )
    
    async def _schedule_default_tasks(self) -> None:
        """Schedule default daemon tasks."""
        # Validation task
        if self.config.validation_enabled:
            await self.schedule_interval_task(
                task_id="validation_check",
                name="Periodic Validation",
                handler=self._validation_task,
                minutes=self.config.validation_interval_minutes
            )
        
        # Health check task
        if self.config.health_check_enabled:
            await self.schedule_interval_task(
                task_id="health_check",
                name="Health Check",
                handler=self._health_check_task,
                minutes=self.config.health_check_interval_minutes
            )
        
        # Cleanup task
        if self.config.cleanup_enabled:
            await self.schedule_interval_task(
                task_id="cleanup",
                name="System Cleanup",
                handler=self._cleanup_task,
                hours=self.config.cleanup_interval_hours
            )
    
    async def schedule_interval_task(
        self,
        task_id: str,
        name: str,
        handler: Callable,
        seconds: int = 0,
        minutes: int = 0,
        hours: int = 0,
        days: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> str:
        """Schedule a task to run at regular intervals.
        
        Args:
            task_id: Unique task identifier.
            name: Human-readable task name.
            handler: Async function to execute.
            seconds: Interval in seconds.
            minutes: Interval in minutes.
            hours: Interval in hours.
            days: Interval in days.
            start_date: When to start scheduling.
            end_date: When to stop scheduling.
            
        Returns:
            Job ID from scheduler.
        """
        if not self._scheduler:
            raise RuntimeError("Scheduler not started")
        
        # Create task info
        task_info = TaskInfo(
            id=task_id,
            name=name,
            status=TaskStatus.SCHEDULED
        )
        self._tasks[task_id] = task_info
        self._task_handlers[task_id] = handler
        
        # Create trigger
        trigger = IntervalTrigger(
            seconds=seconds,
            minutes=minutes,
            hours=hours,
            days=days,
            start_date=start_date,
            end_date=end_date
        )
        
        # Schedule job
        job = self._scheduler.add_job(
            self._task_wrapper,
            trigger=trigger,
            args=[task_id],
            id=task_id,
            name=name,
            replace_existing=True
        )
        
        # Update next run time
        task_info.next_run = job.next_run_time
        
        logger.info(f"Scheduled interval task: {name} ({task_id})")
        return job.id
    
    async def schedule_cron_task(
        self,
        task_id: str,
        name: str,
        handler: Callable,
        cron_expression: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> str:
        """Schedule a task using cron expression.
        
        Args:
            task_id: Unique task identifier.
            name: Human-readable task name.
            handler: Async function to execute.
            cron_expression: Cron schedule expression.
            start_date: When to start scheduling.
            end_date: When to stop scheduling.
            
        Returns:
            Job ID from scheduler.
        """
        if not self._scheduler:
            raise RuntimeError("Scheduler not started")
        
        # Create task info
        task_info = TaskInfo(
            id=task_id,
            name=name,
            status=TaskStatus.SCHEDULED
        )
        self._tasks[task_id] = task_info
        self._task_handlers[task_id] = handler
        
        # Parse cron expression (simple format: "minute hour day month dow")
        parts = cron_expression.split()
        if len(parts) != 5:
            raise ValueError("Cron expression must have 5 parts: minute hour day month dow")
        
        minute, hour, day, month, day_of_week = parts
        
        # Create trigger
        trigger = CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
            start_date=start_date,
            end_date=end_date
        )
        
        # Schedule job
        job = self._scheduler.add_job(
            self._task_wrapper,
            trigger=trigger,
            args=[task_id],
            id=task_id,
            name=name,
            replace_existing=True
        )
        
        # Update next run time
        task_info.next_run = job.next_run_time
        
        logger.info(f"Scheduled cron task: {name} ({task_id}) - {cron_expression}")
        return job.id
    
    async def schedule_one_time_task(
        self,
        task_id: str,
        name: str,
        handler: Callable,
        run_date: datetime
    ) -> str:
        """Schedule a one-time task.
        
        Args:
            task_id: Unique task identifier.
            name: Human-readable task name.
            handler: Async function to execute.
            run_date: When to run the task.
            
        Returns:
            Job ID from scheduler.
        """
        if not self._scheduler:
            raise RuntimeError("Scheduler not started")
        
        # Create task info
        task_info = TaskInfo(
            id=task_id,
            name=name,
            status=TaskStatus.SCHEDULED,
            next_run=run_date
        )
        self._tasks[task_id] = task_info
        self._task_handlers[task_id] = handler
        
        # Schedule job
        job = self._scheduler.add_job(
            self._task_wrapper,
            trigger='date',
            run_date=run_date,
            args=[task_id],
            id=task_id,
            name=name,
            replace_existing=True
        )
        
        logger.info(f"Scheduled one-time task: {name} ({task_id}) at {run_date}")
        return job.id
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task.
        
        Args:
            task_id: Task to cancel.
            
        Returns:
            True if task was cancelled, False if not found.
        """
        if not self._scheduler:
            return False
        
        try:
            self._scheduler.remove_job(task_id)
            if task_id in self._tasks:
                self._tasks[task_id].status = TaskStatus.CANCELLED
            logger.info(f"Cancelled task: {task_id}")
            return True
        except:
            return False
    
    def get_task_info(self, task_id: str) -> Optional[TaskInfo]:
        """Get information about a task.
        
        Args:
            task_id: Task ID.
            
        Returns:
            TaskInfo if found, None otherwise.
        """
        return self._tasks.get(task_id)
    
    def get_all_tasks(self) -> Dict[str, TaskInfo]:
        """Get information about all tasks.
        
        Returns:
            Dictionary mapping task IDs to TaskInfo.
        """
        return self._tasks.copy()
    
    def get_running_tasks(self) -> List[TaskInfo]:
        """Get list of currently running tasks.
        
        Returns:
            List of TaskInfo for running tasks.
        """
        return [
            task for task in self._tasks.values()
            if task.status == TaskStatus.RUNNING
        ]
    
    async def _task_wrapper(self, task_id: str) -> None:
        """Wrapper for task execution with error handling and tracking."""
        if task_id not in self._tasks:
            logger.error(f"Unknown task ID: {task_id}")
            return
        
        task_info = self._tasks[task_id]
        handler = self._task_handlers.get(task_id)
        
        if not handler:
            logger.error(f"No handler found for task: {task_id}")
            return
        
        # Update task status
        task_info.status = TaskStatus.RUNNING
        task_info.last_run = datetime.utcnow()
        task_info.run_count += 1
        
        try:
            logger.debug(f"Executing task: {task_info.name} ({task_id})")
            
            # Execute handler
            if asyncio.iscoroutinefunction(handler):
                await handler()
            else:
                # Run sync function in thread pool
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, handler)
            
            task_info.status = TaskStatus.COMPLETED
            logger.debug(f"Task completed: {task_info.name} ({task_id})")
            
        except Exception as e:
            task_info.status = TaskStatus.FAILED
            task_info.error_count += 1
            task_info.last_error = str(e)
            logger.error(f"Task failed: {task_info.name} ({task_id}) - {e}")
        
        # Update next run time if recurring
        if self._scheduler:
            job = self._scheduler.get_job(task_id)
            if job:
                task_info.next_run = job.next_run_time
                if task_info.next_run:
                    task_info.status = TaskStatus.SCHEDULED
    
    def _job_executed_listener(self, event: JobExecutionEvent) -> None:
        """Handle job execution events."""
        job_id = event.job_id
        
        if event.exception:
            logger.error(f"Job {job_id} failed: {event.exception}")
        else:
            logger.debug(f"Job {job_id} executed successfully")
    
    # Default task implementations
    async def _validation_task(self) -> None:
        """Default validation task."""
        logger.info("Running periodic validation check...")
        # This would integrate with ValidationRepairSystem
        # For now, just a placeholder
        await asyncio.sleep(1)  # Simulate work
        logger.info("Validation check completed")
    
    async def _health_check_task(self) -> None:
        """Default health check task."""
        logger.debug("Running health check...")
        # Check system health, database connections, etc.
        await asyncio.sleep(0.5)  # Simulate work
        logger.debug("Health check completed")
    
    async def _cleanup_task(self) -> None:
        """Default cleanup task."""
        logger.info("Running system cleanup...")
        # Clean up logs, temporary files, etc.
        await asyncio.sleep(2)  # Simulate work
        logger.info("System cleanup completed") 