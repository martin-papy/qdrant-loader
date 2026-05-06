from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from qdrant_loader.utils.logging import LoggingConfig
from .handlers import process_webhook_event, normalize_source_type

logger = LoggingConfig.get_logger(__name__)

app = FastAPI(
    title="QDrant Loader Webhook Server",
    version="1.0.0",
    description="Receives connector webhook events and triggers source ingestion.",
)

SUPPORTED_SOURCE_TYPES = {
    "jira",
    "confluence",
    "git",
    "publicdocs",
    "localfile",
}


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


@app.post("/webhooks/projects/{project_id}/{source_type}/{source}")
async def webhook_project_route(
    project_id: str,
    source_type: str,
    source: str,
    request: Request,
    force: bool = False,
) -> JSONResponse:
    """Receive a webhook for a specific project source."""
    payload = await _parse_json_request(request)
    normalized_source_type = normalize_source_type(source_type)

    await process_webhook_event(
        project_id=project_id,
        source_type=normalized_source_type,
        source=source,
        payload=payload,
        force=force,
    )

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


@app.post("/webhooks/{source_type}/{source}")
async def webhook_source_route(
    source_type: str,
    source: str,
    request: Request,
    force: bool = False,
) -> JSONResponse:
    """Receive a webhook for a source across all configured projects."""
    payload = await _parse_json_request(request)
    normalized_source_type = normalize_source_type(source_type)

    await process_webhook_event(
        project_id=None,
        source_type=normalized_source_type,
        source=source,
        payload=payload,
        force=force,
    )

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "status": "accepted",
            "source_type": normalized_source_type,
            "source": source,
            "force": force,
        },
    )
