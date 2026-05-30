from pathlib import PurePath
from typing import Any

from qdrant_loader_core.graph.extractor.base_extractor import BaseEntityExtractor


class LocalFileEntityExtractor(BaseEntityExtractor):
    SOURCE_TYPE = "localfile"

    def _extract_impl(self, raw: dict[str, Any]) -> None:
        path = raw.get("path")
        if not path:
            return

        pure_path = PurePath(path)

        file_name = raw.get("file_name") or pure_path.name
        file_dir = str(pure_path.parent) or "root"

        native_id = f"{path}:{file_name}"

        created_at = raw.get("created_at")
        updated_at = raw.get("updated_at")

        properties = {
            "url": path,
            "created_at": created_at,
            "updated_at": updated_at,
        }

        doc = self.build_document(
            source_type=self.SOURCE_TYPE,
            native_id=native_id,
            title=file_name,
            url=path,
            created_at=created_at,
            updated_at=updated_at,
            qdrant_point_ids=[],
            properties=properties,
        )

        container = self.get_or_create_container(
            kind="filesystem_dir",
            native_id=file_dir,
            name=file_dir,
        )

        self.emit_edge(
            source=doc,
            target=container,
            edge_type="BELONGS_TO",
        )
