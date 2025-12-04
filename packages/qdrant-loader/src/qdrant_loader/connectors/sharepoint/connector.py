import requests
from .auth import SharePointAuth
from .config import SharePointConfig

class SharePointConnector:
    def __init__(self, config: SharePointConfig):
        self.config = config
        self.auth = SharePointAuth(config)

    def get(self, url: str):
        resp = requests.get(
            url,
            headers=self.auth.get_headers(),
            auth=self.auth.auth
        )
        resp.raise_for_status()
        return resp.json()

    def list_library_items(self, library: str):
        url = (
            f"{self.config.relative_url}"
            f"/_api/web/lists/getbytitle('{library}')/items"
        )
        return self.get(url)