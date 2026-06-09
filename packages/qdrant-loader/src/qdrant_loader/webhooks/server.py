from __future__ import annotations

import asyncio
import os
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

from qdrant_loader.utils.logging import LoggingConfig
from qdrant_loader.webhooks.auth import (
    WEBHOOK_SECRET_ENV_VAR,
    get_client_ip,
    verify_cognito_token,
    verify_ingest_auth,
    verify_webhook_token,
)
from qdrant_loader.webhooks.handlers import (
    INGEST_SUPPORTED_SOURCE_TYPES,
    SUPPORTED_SOURCE_TYPES,
    enqueue_ingest_request,
    enqueue_webhook_event,
    normalize_source_type,
)
from qdrant_loader.webhooks.queue_backend import QueueBackendManager
from qdrant_loader.webhooks.worker import run_webhook_worker

logger = LoggingConfig.get_logger(__name__)

WEBHOOK_RATE_LIMIT_WINDOW_SECONDS = int(
    os.getenv("WEBHOOK_RATE_LIMIT_WINDOW_SECONDS", "60")
)
WEBHOOK_RATE_LIMIT_REQUESTS_PER_WINDOW = int(
    os.getenv("WEBHOOK_RATE_LIMIT_REQUESTS_PER_WINDOW", "10")
)

# In-memory rate limit state (process-local).
#
# IMPORTANT: This is NOT a substitute for infrastructure-level rate limiting.
#
# LIMITATION: Each uvicorn worker, container, or ECS task has its own dict instance.
# Multiple instances → each enforces limits independently → effective limit = N × configured.
# Example: 2 workers with limit=10 → actual limit ≈ 20 req/min.
#
# DESIGN INTENT (WS-6): Primary rate-limiting should live at the ALB/WAF layer:
# "rate-limit per IP to 1000 req/min". This app-level check is a safety net.
#
# SECURITY NOTE: get_client_ip() relies on X-Forwarded-For header when running
# behind a trusted proxy. In untrusted environments, set WEBHOOK_TRUSTED_PROXY_IPS
# or similar to validate the header origin.
_request_timestamps: dict[str, list[float]] = {}


@asynccontextmanager
async def _lifespan(app: FastAPI):
    has_global_secret = bool(os.getenv(WEBHOOK_SECRET_ENV_VAR)) or bool(
        os.getenv("WEBHOOK_SECRETS")
    )
    has_project_secret = any(
        key.startswith("WEBHOOK_SECRET_") and bool(value)
        for key, value in os.environ.items()
    )
    cognito_enabled = os.getenv("WEBHOOK_ENABLE_COGNITO_JWT", "false").lower() in (
        "true",
        "1",
        "yes",
    )
    if not (has_global_secret or has_project_secret or cognito_enabled):
        raise RuntimeError(
            "Webhook authentication is not configured. Set WEBHOOK_SECRET, "
            "WEBHOOK_SECRETS, WEBHOOK_SECRET_<PROJECT_ID>, or enable Cognito JWT."
        )

    await QueueBackendManager.initialize()
    stop_event = asyncio.Event()
    worker_task = asyncio.create_task(run_webhook_worker(stop_event))
    app.state.worker_stop_event = stop_event
    app.state.worker_task = worker_task

    logger.info(
        "Webhook server startup",
        rate_limit_window_seconds=WEBHOOK_RATE_LIMIT_WINDOW_SECONDS,
        rate_limit_requests=WEBHOOK_RATE_LIMIT_REQUESTS_PER_WINDOW,
    )
    try:
        yield
    finally:
        stop_event.set()
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
        await QueueBackendManager.shutdown()
        logger.info("Webhook server shutdown")


app = FastAPI(
    title="QDrant Loader Webhook Server",
    version="1.0.0",
    description=(
        "Receives connector webhooks and direct /ingest API requests; "
        "enqueues durable ingestion jobs."
    ),
    lifespan=_lifespan,
)


def _cleanup_old_timestamps(client_key: str) -> None:
    now = time.monotonic()
    window = WEBHOOK_RATE_LIMIT_WINDOW_SECONDS
    timestamps = _request_timestamps.get(client_key, [])
    _request_timestamps[client_key] = [t for t in timestamps if now - t <= window]


def _enforce_rate_limit(request: Request) -> None:
    """Check rate limit for this request and reject if exceeded.

    This is a process-local safety net. For true DDoS protection, rely on ALB/WAF.
    See _request_timestamps docstring for design details.
    """
    client_key = get_client_ip(request)
    _cleanup_old_timestamps(client_key)
    timestamps = _request_timestamps.setdefault(client_key, [])
    if len(timestamps) >= WEBHOOK_RATE_LIMIT_REQUESTS_PER_WINDOW:
        logger.warning(
            "Rate limit exceeded for webhook client",
            client=client_key,
            request_count=len(timestamps),
            window_seconds=WEBHOOK_RATE_LIMIT_WINDOW_SECONDS,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again later.",
        )
    timestamps.append(time.monotonic())


async def _parse_json_request(request: Request) -> object:
    try:
        return await request.json()
    except Exception as exc:
        logger.error("Invalid webhook payload", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook body must be valid JSON.",
        ) from exc


async def _handle_webhook(
    project_id: str | None,
    source_type: str,
    source: str,
    request: Request,
    force: bool = False,
) -> JSONResponse:
    # Check rate limit BEFORE parsing to avoid wasting CPU on flooded requests
    _enforce_rate_limit(request)

    payload = await _parse_json_request(request)

    try:
        normalized_source_type = normalize_source_type(source_type)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    try:
        result = await enqueue_webhook_event(
            project_id,
            normalized_source_type,
            source,
            payload,
            force,
        )
    except Exception as exc:
        logger.exception("Failed to enqueue webhook event", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enqueue webhook event.",
        ) from exc

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "status": "accepted",
            "project_id": project_id,
            "source_type": normalized_source_type,
            "source": source,
            "force": force,
            "queued": True,
            **result,
        },
    )


@app.get("/health")
async def health_check() -> dict[str, object]:
    """Simple readiness endpoint (no auth required)."""
    return {
        "status": "healthy",
        "supported_source_types": sorted(SUPPORTED_SOURCE_TYPES),
        "ingest_source_types": sorted(INGEST_SUPPORTED_SOURCE_TYPES),
        "rate_limit": {
            "window_seconds": WEBHOOK_RATE_LIMIT_WINDOW_SECONDS,
            "max_requests": WEBHOOK_RATE_LIMIT_REQUESTS_PER_WINDOW,
        },
        "queue": "sqlite",
    }


@app.get("/healthz")
async def healthz() -> dict[str, object]:
    """Kubernetes-compliant health check endpoint.

    Returns 200 OK if the webhook server process is running.
    No probing of dependencies (see /readyz for that).
    """
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict[str, object]:
    """Kubernetes-compliant readiness check endpoint.

    Returns 200 OK if the server is ready to accept requests:
    - Worker process is running
    - Queue backend is initialized

    Note: Currently does not probe Qdrant or DB connectivity;
    those would be probed by ALB/WAF health checks or monitored separately.
    """
    worker_task = getattr(app.state, "worker_task", None)

    if worker_task is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Worker task not initialized",
        )

    if worker_task.done():
        # If task is done, check if it errored
        try:
            worker_task.result()
        except Exception as err:
            logger.exception("Worker task failed readiness check", error=str(err))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Worker task failed.",
            ) from err

    return {"status": "ready"}


@app.get("/status")
async def status_route(
    claims: dict[str, Any] = Depends(verify_cognito_token),
) -> dict[str, object]:
    """Authenticated status endpoint for application clients (Cognito when enabled)."""
    return {
        "status": "ok",
        "subject": claims.get("sub"),
    }


@app.post("/ingest")
async def ingest_route(
    request: Request,
    project_id: str | None = Query(None),
    source_type: str | None = Query(None),
    source: str | None = Query(None),
    force: bool = False,
    _auth: None = Depends(verify_ingest_auth),
) -> JSONResponse:
    """Trigger ingestion via API (equivalent to `qdrant-loader ingest`).

    Query parameters mirror the ingest CLI flags. The job is enqueued and
    processed asynchronously by the background worker.
    """
    _enforce_rate_limit(request)

    try:
        result = await enqueue_ingest_request(
            project_id=project_id,
            source_type=source_type,
            source=source,
            force=force,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Failed to enqueue ingest request", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enqueue ingest request.",
        ) from exc

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "status": "accepted",
            "project_id": project_id,
            "source_type": source_type,
            "source": source,
            "force": force,
            "queued": True,
            **result,
        },
    )


@app.post("/webhooks/projects/{project_id}/{source_type}/{source}")
async def webhook_project_route(
    project_id: str,
    source_type: str,
    source: str,
    request: Request,
    force: bool = False,
    _auth: None = Depends(verify_webhook_token),
) -> JSONResponse:
    """Receive a webhook for a specific project source."""
    return await _handle_webhook(project_id, source_type, source, request, force)


@app.post("/webhooks/{source_type}/{source}")
async def webhook_source_route(
    source_type: str,
    source: str,
    request: Request,
    force: bool = False,
    _auth: None = Depends(verify_webhook_token),
) -> JSONResponse:
    """Receive a webhook for a source across all configured projects."""
    return await _handle_webhook(None, source_type, source, request, force)
