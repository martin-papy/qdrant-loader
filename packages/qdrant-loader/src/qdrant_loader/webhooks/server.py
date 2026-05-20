from __future__ import annotations

import os
import threading
import time
from contextlib import asynccontextmanager
from typing import Any, Callable

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request, status, Query
from fastapi.responses import JSONResponse

from qdrant_loader.utils.logging import LoggingConfig

from qdrant_loader.webhooks.handlers import (
    SUPPORTED_SOURCE_TYPES,
    normalize_source_type,
    process_webhook_event,
    process_ingest_request,
)

logger = LoggingConfig.get_logger(__name__)

@asynccontextmanager
async def _lifespan(app: FastAPI):
    app.state.ingestion_semaphore = threading.BoundedSemaphore(
        WEBHOOK_MAX_CONCURRENT_INGESTIONS
    )
    logger.info(
        "Webhook server startup",
        max_concurrent_ingestions=WEBHOOK_MAX_CONCURRENT_INGESTIONS,
        rate_limit_window_seconds=WEBHOOK_RATE_LIMIT_WINDOW_SECONDS,
        rate_limit_requests=WEBHOOK_RATE_LIMIT_REQUESTS_PER_WINDOW,
    )
    yield
    logger.info("Webhook server shutdown")


app = FastAPI(
    title="QDrant Loader Webhook Server",
    version="1.0.0",
    description="Receives connector webhook events and triggers source ingestion.",
    lifespan=_lifespan,
)

WEBHOOK_SECRET_ENV_VAR = "WEBHOOK_SECRET"
WEBHOOK_QUERY_PARAM = "token"
WEBHOOK_RATE_LIMIT_WINDOW_SECONDS = int(
    os.getenv("WEBHOOK_RATE_LIMIT_WINDOW_SECONDS", "60")
)
WEBHOOK_RATE_LIMIT_REQUESTS_PER_WINDOW = int(
    os.getenv("WEBHOOK_RATE_LIMIT_REQUESTS_PER_WINDOW", "10")
)
WEBHOOK_MAX_CONCURRENT_INGESTIONS = int(
    os.getenv("WEBHOOK_MAX_CONCURRENT_INGESTIONS", "1")
)

# Simple in-memory rate limiting cache keyed by client IP.
_request_timestamps: dict[str, list[float]] = {}

async def verify_webhook_token(
    webhook_token: str | None = Query(None, alias=WEBHOOK_QUERY_PARAM),
    authorization: str | None = Header(None, convert_underscores=False),
) -> None:
    """Verify the shared webhook secret.

    Prefer the `Authorization: Bearer <token>` header to avoid leaking the
    token in logs, browser history, or access logs. For backward
    compatibility the query parameter is still accepted but a warning is
    emitted when used.
    """
    secret = os.getenv(WEBHOOK_SECRET_ENV_VAR)

    if secret:
        # Prefer Authorization header
        token_value: str | None = None
        if authorization:
            # Accept both 'Bearer <token>' and raw token in Authorization header
            auth = authorization.strip()
            if auth.lower().startswith("bearer "):
                token_value = auth.split(None, 1)[1].strip()
            else:
                token_value = auth
        elif webhook_token:
            token_value = webhook_token
            logger.warning(
                "Using webhook token via URL query param is insecure; prefer Authorization: Bearer header",
                param=WEBHOOK_QUERY_PARAM,
            )

        if not token_value or token_value != secret:
            logger.warning(
                "Unauthorized webhook request",
                param=WEBHOOK_QUERY_PARAM,
                received=bool(token_value),
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing webhook token.",
            )
    else:
        logger.warning(
            "Webhook secret is not configured; webhook endpoints are unprotected",
            env_var=WEBHOOK_SECRET_ENV_VAR,
        )

@app.get("/health")
async def health_check() -> dict[str, object]:
    """Simple readiness endpoint."""
    return {
        "status": "healthy",
        "supported_source_types": sorted(SUPPORTED_SOURCE_TYPES),
        "rate_limit": {
            "window_seconds": WEBHOOK_RATE_LIMIT_WINDOW_SECONDS,
            "max_requests": WEBHOOK_RATE_LIMIT_REQUESTS_PER_WINDOW,
        },
        "max_concurrent_ingestions": WEBHOOK_MAX_CONCURRENT_INGESTIONS,
    }


def _get_client_key(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _cleanup_old_timestamps(client_key: str) -> None:
    now = time.monotonic()
    window = WEBHOOK_RATE_LIMIT_WINDOW_SECONDS
    timestamps = _request_timestamps.get(client_key, [])
    _request_timestamps[client_key] = [t for t in timestamps if now - t <= window]


def _enforce_rate_limit(request: Request) -> None:
    client_key = _get_client_key(request)
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


def _try_acquire_ingestion_slot() -> bool:
    semaphore = getattr(app.state, "ingestion_semaphore", None)
    if semaphore is None:
        return False
    try:
        return semaphore.acquire(blocking=False)
    except Exception:
        return False


async def _release_ingestion_slot() -> None:
    semaphore = getattr(app.state, "ingestion_semaphore", None)
    if semaphore is not None:
        try:
            semaphore.release()
        except ValueError:
            logger.warning("Attempted to release an unlocked ingestion semaphore")


async def _run_background_ingestion(
    task_name: str,
    ingestion_callable: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> None:
    """Run ingestion in background with concurrency tracking."""
    logger.info("Scheduling background ingestion task", task=task_name)
    try:
        await ingestion_callable(*args, **kwargs)
        logger.info("Background ingestion completed", task=task_name)
    except Exception as exc:
        logger.error(
            "Background ingestion failed",
            task=task_name,
            error=str(exc),
        )
    finally:
        await _release_ingestion_slot()


async def _parse_json_request(request: Request) -> object:
    try:
        return await request.json()
    except Exception as exc:
        logger.error("Invalid webhook payload", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook body must be valid JSON.",
        ) from exc


@app.post(
    "/webhooks/projects/{project_id}/{source_type}/{source}",
    dependencies=[Depends(verify_webhook_token)],
)
async def webhook_project_route(
    project_id: str,
    source_type: str,
    source: str,
    request: Request,
    background_tasks: BackgroundTasks,
    force: bool = False,
) -> JSONResponse:
    """Receive a webhook for a specific project source."""
    payload = await _parse_json_request(request)
    _enforce_rate_limit(request)

    normalized_source_type = normalize_source_type(source_type)
    if not _try_acquire_ingestion_slot():
        logger.warning(
            "Concurrent ingestion limit reached",
            source_type=normalized_source_type,
            source=source,
            project_id=project_id,
            concurrent_limit=WEBHOOK_MAX_CONCURRENT_INGESTIONS,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many concurrent ingestion jobs. Try again later.",
        )

    background_tasks.add_task(
        _run_background_ingestion,
        "webhook_project",
        process_webhook_event,
        project_id,
        normalized_source_type,
        source,
        payload,
        force,
    )

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "status": "accepted",
            "project_id": project_id,
            "source_type": normalized_source_type,
            "source": source,
            "force": force,
            "background": True,
        },
    )


@app.post(
    "/webhooks/{source_type}/{source}",
    dependencies=[Depends(verify_webhook_token)],
)
async def webhook_source_route(
    source_type: str,
    source: str,
    request: Request,
    background_tasks: BackgroundTasks,
    force: bool = False,
) -> JSONResponse:
    """Receive a webhook for a source across all configured projects."""
    payload = await _parse_json_request(request)
    _enforce_rate_limit(request)

    normalized_source_type = normalize_source_type(source_type)
    if not _try_acquire_ingestion_slot():
        logger.warning(
            "Concurrent ingestion limit reached",
            source_type=normalized_source_type,
            source=source,
            concurrent_limit=WEBHOOK_MAX_CONCURRENT_INGESTIONS,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many concurrent ingestion jobs. Try again later.",
        )

    background_tasks.add_task(
        _run_background_ingestion,
        "webhook_source",
        process_webhook_event,
        None,
        normalized_source_type,
        source,
        payload,
        force,
    )

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "status": "accepted",
            "source_type": normalized_source_type,
            "source": source,
            "force": force,
            "background": True,
        },
    )


@app.post(
    "/ingest",
    dependencies=[Depends(verify_webhook_token)],
)
async def ingest_route(
    project_id: str | None = Query(None),
    source_type: str | None = Query(None),
    source: str | None = Query(None),
    force: bool = False,
    request: Request = None,
    background_tasks: BackgroundTasks = None,
) -> JSONResponse:
    """Receive a direct HTTP request to run ingestion on demand."""
    if source is not None and source_type is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="source_type must be provided when source is specified.",
        )

    normalized_source_type = (
        normalize_source_type(source_type) if source_type is not None else None
    )

    if request is not None:
        _enforce_rate_limit(request)

    if not _try_acquire_ingestion_slot():
        logger.warning(
            "Concurrent ingestion limit reached",
            project_id=project_id,
            source_type=normalized_source_type,
            source=source,
            concurrent_limit=WEBHOOK_MAX_CONCURRENT_INGESTIONS,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many concurrent ingestion jobs. Try again later.",
        )

    background_tasks.add_task(
        _run_background_ingestion,
        "direct_ingest",
        process_ingest_request,
        project_id,
        normalized_source_type,
        source,
        force,
    )

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "status": "accepted",
            "project_id": project_id,
            "source_type": normalized_source_type,
            "source": source,
            "force": force,
            "background": True,
        },
    )
