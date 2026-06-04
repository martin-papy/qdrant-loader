"""Background worker that processes queued webhook events."""

from __future__ import annotations

import asyncio
import os

from qdrant_loader.utils.logging import LoggingConfig
from qdrant_loader.webhooks.event_processor import process_change_event
from qdrant_loader.webhooks.queue_backend import QueueBackendManager, parse_job_payload

logger = LoggingConfig.get_logger(__name__)

WEBHOOK_WORKER_POLL_SECONDS = float(os.getenv("WEBHOOK_WORKER_POLL_SECONDS", "0.5"))
WEBHOOK_WORKER_LEASE_SECONDS = int(os.getenv("WEBHOOK_WORKER_LEASE_SECONDS", "120"))


async def run_webhook_worker(stop_event: asyncio.Event) -> None:
    """Poll the durable queue and process webhook jobs until stopped."""
    job_queue = QueueBackendManager.get_job_queue()
    logger.info(
        "Webhook worker started",
        poll_seconds=WEBHOOK_WORKER_POLL_SECONDS,
        lease_seconds=WEBHOOK_WORKER_LEASE_SECONDS,
    )

    while not stop_event.is_set():
        job = await job_queue.claim_next(lease_seconds=WEBHOOK_WORKER_LEASE_SECONDS)
        if job is None:
            try:
                await asyncio.wait_for(
                    stop_event.wait(),
                    timeout=WEBHOOK_WORKER_POLL_SECONDS,
                )
            except TimeoutError:
                pass
            continue

        try:
            event = parse_job_payload(job)
            logger.info(
                "Processing webhook job",
                job_id=job.id,
                operation=event.operation,
                source=event.source,
                entity_id=event.entity_id,
            )
            await process_change_event(event)
            await job_queue.mark_done(job.id, claim_attempt=job.attempts)
        except Exception as exc:
            logger.exception(
                "Webhook job failed",
                job_id=job.id,
                error=str(exc),
            )
            try:
                await job_queue.mark_failed(
                    job.id,
                    error_message=str(exc),
                    claim_attempt=job.attempts,
                )
            except Exception as mark_exc:
                logger.exception(
                    "Failed to mark webhook job as failed",
                    job_id=job.id,
                    error=str(mark_exc),
                )

    logger.info("Webhook worker stopped")
