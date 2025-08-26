from __future__ import annotations

import requests

from qdrant_loader.core.attachment_downloader import (
    AttachmentDownloader,
    AttachmentMetadata,
)
from qdrant_loader.core.document import Document


class AttachmentReader:
    """Facade around `AttachmentDownloader` for uniform usage in connectors."""

    def __init__(
        self,
        session: requests.Session,
        downloader: AttachmentDownloader,
    ) -> None:
        self.session = session
        self.downloader = downloader

    async def fetch_and_process(
        self, attachments: list[AttachmentMetadata], parent: Document
    ) -> list[Document]:
        return await self.downloader.download_and_process_attachments(
            attachments, parent
        )

    # Optional cleanup hooks to allow connectors to close resources when reconfiguring
    async def aclose(self) -> None:  # noqa: D401 - simple cleanup hook
        """Asynchronous cleanup for compatibility; currently no async resources."""
        # If downloader/session expose explicit async cleanup in the future, call here
        return None

    def close(self) -> None:  # noqa: D401 - simple cleanup hook
        """Synchronous cleanup for compatibility; currently no resources to close."""
        # requests.Session is owned by the connector, not by the reader
        return None
