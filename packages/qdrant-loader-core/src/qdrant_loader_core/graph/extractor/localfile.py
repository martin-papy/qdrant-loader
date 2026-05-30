from pathlib import PurePath
from typing import Any

from qdrant_loader_core.graph.extractor.base_extractor import BaseEntityExtractor


class LocalFileEntityExtractor(BaseEntityExtractor):
    SOURCE_TYPE = "localfile"

    def _extract_impl(self, raw: dict[str, Any]) -> None:
        path = raw.get("path")
        if not path:
            return

        created_at = raw.get("created_at")
        updated_at = raw.get("updated_at")

        properties = {
            "url": path,
            "created_at": created_at,
            "updated_at": updated_at,
        }
        pure_path = PurePath(path)
        doc = self.build_document(
            source_type=self.SOURCE_TYPE,
            native_id=path,
            title=pure_path.name or path,
            url=path,
            created_at=created_at,
            updated_at=updated_at,
            qdrant_point_ids=[],
            properties=properties,
        )

        # Directory as container
        dir_path = str(pure_path.parent) if str(pure_path.parent) else "."

        container = self.get_or_create_container(
            kind="filesystem_dir",
            native_id=dir_path,
            name=dir_path,
        )

        self.emit_edge(source=doc, target=container, edge_type="BELONGS_TO")
