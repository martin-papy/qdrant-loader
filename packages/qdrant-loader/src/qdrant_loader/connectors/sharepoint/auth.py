import requests
from .config import SharePointConfig, SharePointAuthMethod

class SharePointAuth:
    def __init__(self, config: SharePointConfig):
        self.config = config
        self.token = None
        self.auth = None

        if config.authentication_method == SharePointAuthMethod.CLIENT_CREDENTIALS:
            self._authenticate_client_credentials()
        else:
            self._authenticate_user_credentials()

    def _authenticate_client_credentials(self):
        base = None
        if getattr(self.config, "base_url", None):
            base = str(self.config.base_url)
        elif getattr(self.config, "relative_url", None) and str(self.config.relative_url).startswith("http"):
            base = str(self.config.relative_url)

        if not base:
            raise ValueError("SharePointConfig.base_url (or a full relative_url) is required to build the resource scope for client credentials")

        token_url = f"https://login.microsoftonline.com/{self.config.tenant_id}/oauth2/v2.0/token"
        scope = f"{base.rstrip('/')}/.default"

        payload = {
            "grant_type": "client_credentials",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "scope": scope,
        }

        r = requests.post(token_url, data=payload)
        r.raise_for_status()
        self.token = r.json().get("access_token")

    def _authenticate_user_credentials(self):
        try:
            from requests_ntlm import HttpNtlmAuth
        except Exception:
            raise RuntimeError("requests_ntlm is required for user credentials auth. Install with: pip install requests_ntlm")

        self.auth = HttpNtlmAuth(self.config.username, self.config.password)

    def get_headers(self):
        if self.token:
            return {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json;odata=verbose",
            }
        return {"Accept": "application/json;odata=verbose"}
