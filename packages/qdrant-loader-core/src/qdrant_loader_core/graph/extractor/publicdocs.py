from typing import Any

from qdrant_loader_core.graph.extractor.base_extractor import BaseEntityExtractor


class PublicDocsEntityExtractor(BaseEntityExtractor):
    SOURCE_TYPE = "publicdocs"

    def _extract_impl(self, raw: dict[str, Any]) -> None:
        url = raw.get("url")
        if not url:
            return

        doc = self.build_document(
            source_type=self.SOURCE_TYPE,
            native_id=url,
            title=raw.get("title", url),
            url=url,
            created_at=raw.get("created_at"),
            updated_at=raw.get("updated_at"),
            qdrant_point_ids=[],
            properties={},
        )

        # Domain as container
        domain = url.split("/")[2] if "://" in url else "unknown"

        container = self.get_or_create_container(
            kind="web_domain",
            native_id=domain,
            name=domain,
        )

        self.emit_edge(source=doc, target=container, edge_type="BELONGS_TO")

        # Optional tags
        for tag in raw.get("tags", []):
            label = self.get_or_create_label(name=tag)
            self.emit_edge(source=doc, target=label, edge_type="HAS_LABEL")
