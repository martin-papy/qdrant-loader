from __future__ import annotations

from requests import Session
from requests.auth import HTTPBasicAuth

from .config import JiraDeploymentType, JiraProjectConfig


def setup_authentication(session: Session, config: JiraProjectConfig) -> None:
    """Configure authentication on the provided requests session based on deployment type."""
    if config.deployment_type == JiraDeploymentType.CLOUD:
        if not config.token:
            raise ValueError("API token is required for Jira Cloud")
        if not config.email:
            raise ValueError("Email is required for Jira Cloud")
        session.auth = HTTPBasicAuth(config.email, config.token)
    else:
        if not config.token:
            raise ValueError(
                "Personal Access Token is required for Jira Data Center/Server"
            )
        session.headers.update(
            {
                "Authorization": f"Bearer {config.token}",
                "Content-Type": "application/json",
            }
        )


def auto_detect_deployment_type(base_url: str) -> JiraDeploymentType:
    """Auto-detect the Jira deployment type based on base URL."""
    from urllib.parse import urlparse

    try:
        parsed_url = urlparse(str(base_url))
        hostname = parsed_url.hostname
        if hostname is None:
            return JiraDeploymentType.DATACENTER
        if hostname.endswith(".atlassian.net") or hostname == "atlassian.net":
            return JiraDeploymentType.CLOUD
        return JiraDeploymentType.DATACENTER
    except Exception:
        return JiraDeploymentType.DATACENTER
