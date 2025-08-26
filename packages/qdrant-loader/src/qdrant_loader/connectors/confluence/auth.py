from __future__ import annotations

from requests import Session
from requests.auth import HTTPBasicAuth

from .config import ConfluenceDeploymentType, ConfluenceSpaceConfig


def setup_authentication(session: Session, config: ConfluenceSpaceConfig) -> None:
    """Configure authentication on the provided requests session based on deployment type."""
    if config.deployment_type == ConfluenceDeploymentType.CLOUD:
        if not config.token:
            raise ValueError("API token is required for Confluence Cloud")
        if not config.email:
            raise ValueError("Email is required for Confluence Cloud")
        session.auth = HTTPBasicAuth(config.email, config.token)
    else:
        if not config.token:
            raise ValueError(
                "Personal Access Token is required for Confluence Data Center/Server"
            )
        session.headers.update(
            {
                "Authorization": f"Bearer {config.token}",
            }
        )


def auto_detect_deployment_type(base_url: str) -> ConfluenceDeploymentType:
    """Auto-detect the Confluence deployment type based on base URL."""
    from urllib.parse import urlparse

    try:
        parsed_url = urlparse(str(base_url))
        hostname = parsed_url.hostname
        if hostname is None:
            return ConfluenceDeploymentType.DATACENTER
        if hostname.endswith(".atlassian.net") or hostname == "atlassian.net":
            return ConfluenceDeploymentType.CLOUD
        return ConfluenceDeploymentType.DATACENTER
    except Exception:
        return ConfluenceDeploymentType.DATACENTER
