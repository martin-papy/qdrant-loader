from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BaseSearchResult:
    score: float
    text: str
    source_type: str
    source_title: str
    source_url: str | None = None
    file_path: str | None = None
    repo_name: str | None = None
    vector_score: float = 0.0
    keyword_score: float = 0.0
    document_id: str | None = None
    created_at: str | None = None
    last_modified: str | None = None
