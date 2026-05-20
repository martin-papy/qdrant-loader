from __future__ import annotations

import os

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status, Query
from fastapi.responses import JSONResponse

from qdrant_loader.utils.logging import LoggingConfig

from qdrant_loader.webhooks.handlers import (
    SUPPORTED_SOURCE_TYPES,
    normalize_source_type,
    process_webhook_event,
    process_ingest_request,
)

logger = LoggingConfig.get_logger(__name__)

app = FastAPI(
    title="QDrant Loader Webhook Server",
    version="1.0.0",
    description="Receives connector webhook events and triggers source ingestion.",
)

WEBHOOK_SECRET_ENV_VAR = "WEBHOOK_SECRET"
WEBHOOK_QUERY_PARAM = "token"

async def verify_webhook_token(
    webhook_token: str | None = Query(None, alias=WEBHOOK_QUERY_PARAM),
) -> None:
    """Verify the shared webhook secret via query parameter when configured."""
    secret = os.getenv(WEBHOOK_SECRET_ENV_VAR)
    
    if secret:
        if not webhook_token or webhook_token != secret:
            logger.warning(
                "Unauthorized webhook request",
                param=WEBHOOK_QUERY_PARAM,
                received=bool(webhook_token),
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing webhook token in URL.",
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
    }


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
    force: bool = False,
) -> JSONResponse:
    """Receive a webhook for a specific project source."""
    payload = await _parse_json_request(request)

    try:
        normalized_source_type = normalize_source_type(source_type)
        await process_webhook_event(
            project_id=project_id,
            source_type=normalized_source_type,
            source=source,
            payload=payload,
            force=force,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(
            "Webhook processing failed",
            project_id=project_id,
            source_type=normalized_source_type,
            source=source,
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed.",
        ) from exc

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "status": "accepted",
            "project_id": project_id,
            "source_type": normalized_source_type,
            "source": source,
            "force": force,
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
    force: bool = False,
) -> JSONResponse:
    """Receive a webhook for a source across all configured projects."""
    payload = await _parse_json_request(request)
    normalized_source_type = normalize_source_type(source_type)

    try:
        await process_webhook_event(
            project_id=None,
            source_type=normalized_source_type,
            source=source,
            payload=payload,
            force=force,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(
            "Webhook processing failed",
            source_type=normalized_source_type,
            source=source,
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed.",
        ) from exc

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "status": "accepted",
            "source_type": normalized_source_type,
            "source": source,
            "force": force,
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
) -> JSONResponse:
    """Receive a direct HTTP request to run ingestion on demand."""
    try:
        await process_ingest_request(
            project_id=project_id,
            source_type=source_type,
            source=source,
            force=force,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        logger.warning(
            "Direct ingest request validation failed",
            project_id=project_id,
            source_type=source_type,
            source=source,
            force=force,
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(
            "Direct ingest request failed",
            project_id=project_id,
            source_type=source_type,
            source=source,
            force=force,
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Direct ingest request failed.",
        ) from exc

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "status": "accepted",
            "project_id": project_id,
            "source_type": source_type,
            "source": source,
            "force": force,
        },
    )
