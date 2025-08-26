from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProjectInfo:
    project_id: str | None = None
    project_name: str | None = None
    project_description: str | None = None
    collection_name: str | None = None
