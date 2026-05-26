from __future__ import annotations

import asyncio
import os
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, status, Query
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

_request_timestamps: dict[str, list[float]] = {}


@asynccontextmanager
async def _lifespan(app: FastAPI):
    if not os.getenv(WEBHOOK_SECRET_ENV_VAR) and not os.getenv("WEBHOOK_SECRETS"):
        raise RuntimeError(
            f"{WEBHOOK_SECRET_ENV_VAR} or WEBHOOK_SECRETS must be set before "
            "starting the webhook server."
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
    payload = await _parse_json_request(request)
    _enforce_rate_limit(request)

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


@app.get("/status", dependencies=[Depends(verify_cognito_token)])
async def status_route(claims: dict[str, Any] = Depends(verify_cognito_token)) -> dict[str, object]:
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
