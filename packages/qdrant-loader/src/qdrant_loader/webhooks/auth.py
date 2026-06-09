"""Webhook authentication and authorization (WS-6)."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

from fastapi import Header, HTTPException, Query, Request, status

from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)

WEBHOOK_SECRET_ENV_VAR = "WEBHOOK_SECRET"
WEBHOOK_QUERY_PARAM = "token"

WEBHOOK_USE_SECRETS_MANAGER = os.getenv(
    "WEBHOOK_USE_SECRETS_MANAGER", "false"
).lower() in ("true", "1", "yes")

WEBHOOK_ENABLE_COGNITO_JWT = os.getenv(
    "WEBHOOK_ENABLE_COGNITO_JWT", "false"
).lower() in ("true", "1", "yes")

WEBHOOK_TRUSTED_PROXY = os.getenv("WEBHOOK_TRUSTED_PROXY", None)

COGNITO_REGION = os.getenv("COGNITO_REGION", "")
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID", "")
COGNITO_APP_CLIENT_ID = os.getenv("COGNITO_APP_CLIENT_ID", "")


@lru_cache(maxsize=128)
def _get_webhook_secret_from_env() -> str:
    return os.getenv(WEBHOOK_SECRET_ENV_VAR, "")


def _load_project_secrets() -> dict[str, str]:
    raw = os.getenv("WEBHOOK_SECRETS", "")
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return {str(k): str(v) for k, v in parsed.items()}
    except json.JSONDecodeError:
        logger.warning("WEBHOOK_SECRETS is not valid JSON; ignoring")
    return {}


async def get_webhook_secret(
    project_id: str | None = None,
    workspace_id: str | None = None,
) -> str:
    """Resolve webhook secret for a workspace/project."""
    if WEBHOOK_USE_SECRETS_MANAGER:
        logger.warning(
            "Secrets Manager requested but not yet implemented (WS-6)",
            feature_flag="WEBHOOK_USE_SECRETS_MANAGER",
        )

    if project_id:
        project_secrets = _load_project_secrets()
        if project_id in project_secrets:
            return project_secrets[project_id]
        env_key = f"WEBHOOK_SECRET_{project_id.upper().replace('-', '_')}"
        project_env_secret = os.getenv(env_key)
        if project_env_secret:
            return project_env_secret

    _ = workspace_id
    return _get_webhook_secret_from_env()


def get_client_ip(request: Request) -> str:
    """Extract client IP, honoring X-Forwarded-For only from a trusted proxy."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for and WEBHOOK_TRUSTED_PROXY:
        if request.client and request.client.host == WEBHOOK_TRUSTED_PROXY:
            return forwarded_for.split(",", 1)[0].strip()
        logger.warning(
            "X-Forwarded-For header from untrusted source; ignoring",
            client_host=request.client.host if request.client else None,
            trusted_proxy=WEBHOOK_TRUSTED_PROXY,
        )
    elif forwarded_for and not WEBHOOK_TRUSTED_PROXY:
        logger.debug(
            "X-Forwarded-For present but WEBHOOK_TRUSTED_PROXY not set; using request.client",
        )

    if request.client:
        return request.client.host
    return "unknown"


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    auth = authorization.strip()
    if auth.lower().startswith("bearer "):
        return auth.split(None, 1)[1].strip()
    return auth


def _looks_like_jwt(token: str) -> bool:
    return token.count(".") == 2


class CognitoJWTValidator:
    """Validate Cognito JWT tokens for application routes (WS-6)."""

    @staticmethod
    def _issuer() -> str:
        if not COGNITO_REGION or not COGNITO_USER_POOL_ID:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cognito is not configured.",
            )
        return (
            f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/"
            f"{COGNITO_USER_POOL_ID}"
        )

    @classmethod
    async def validate_token(cls, token: str) -> dict[str, Any]:
        if not WEBHOOK_ENABLE_COGNITO_JWT:
            return {"sub": "local-dev"}

        try:
            import jwt
            from jwt import PyJWKClient
        except ImportError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="PyJWT is required for Cognito validation. "
                "Install qdrant-loader[server].",
            ) from exc

        issuer = cls._issuer()
        jwks_url = f"{issuer}/.well-known/jwks.json"

        try:
            jwk_client = PyJWKClient(jwks_url)
            signing_key = jwk_client.get_signing_key_from_jwt(token)
            decode_kwargs: dict[str, Any] = {
                "algorithms": ["RS256"],
                "issuer": issuer,
                "options": {"verify_aud": bool(COGNITO_APP_CLIENT_ID)},
            }
            if COGNITO_APP_CLIENT_ID:
                decode_kwargs["audience"] = COGNITO_APP_CLIENT_ID
            return jwt.decode(token, signing_key.key, **decode_kwargs)
        except Exception as exc:
            logger.warning("Cognito JWT validation failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired Cognito token.",
            ) from exc

    @staticmethod
    def extract_workspace_id(claims: dict[str, Any]) -> str | None:
        return claims.get("custom:workspace_id") or claims.get("workspace")


async def verify_webhook_token(
    project_id: str | None = None,
    webhook_token: str | None = Query(None, alias=WEBHOOK_QUERY_PARAM),
    authorization: str | None = Header(None, convert_underscores=False),
) -> None:
    """Verify webhook access for Jira-compatible endpoints.

    Jira Cloud only supports shared-secret query tokens, so webhook routes accept
    the project-scoped WEBHOOK_SECRET via Bearer header or ?token= query param.
    Cognito JWT is validated when enabled and the bearer token is a JWT.
    """
    secret = await get_webhook_secret(project_id=project_id)
    token_value = _extract_bearer_token(authorization) or webhook_token

    if WEBHOOK_ENABLE_COGNITO_JWT and token_value and _looks_like_jwt(token_value):
        await CognitoJWTValidator.validate_token(token_value)
        return

    if not secret:
        logger.error(
            "Webhook secret is not configured",
            env_var=WEBHOOK_SECRET_ENV_VAR,
            project_id=project_id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook authentication is not configured.",
        )

    if webhook_token and not authorization:
        logger.warning(
            "Using webhook token via URL query param is insecure; prefer Authorization: Bearer header",
            param=WEBHOOK_QUERY_PARAM,
        )

    if not token_value or token_value != secret:
        logger.warning(
            "Unauthorized webhook request",
            project_id=project_id,
            received=bool(token_value),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing webhook token.",
        )


async def verify_cognito_token(
    authorization: str | None = Header(None, convert_underscores=False),
) -> dict[str, Any]:
    """Dependency for non-webhook routes that require Cognito JWT (WS-6)."""
    token_value = _extract_bearer_token(authorization)
    if not token_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required.",
        )
    return await CognitoJWTValidator.validate_token(token_value)


async def verify_ingest_auth(
    project_id: str | None = Query(None),
    webhook_token: str | None = Query(None, alias=WEBHOOK_QUERY_PARAM),
    authorization: str | None = Header(None, convert_underscores=False),
) -> None:
    """Authenticate POST /ingest (API clients).

    Prefers Authorization: Bearer with Cognito JWT when enabled, otherwise the
    same project-scoped webhook secret used for connector webhooks.
    """
    await verify_webhook_token(
        project_id=project_id,
        webhook_token=webhook_token,
        authorization=authorization,
    )
