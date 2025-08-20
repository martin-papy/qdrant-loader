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
        return await self.downloader.download_and_process_attachments(attachments, parent)


