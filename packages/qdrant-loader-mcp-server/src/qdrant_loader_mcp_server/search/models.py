"""Search result models."""

from pydantic import BaseModel


class SearchResult(BaseModel):
    """Search result model."""

    score: float
    text: str
    source_type: str
    source_title: str
    source_url: str | None = None
    file_path: str | None = None
    repo_name: str | None = None
