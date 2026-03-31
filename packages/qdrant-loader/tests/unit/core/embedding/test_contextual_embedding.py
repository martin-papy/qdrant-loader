"""Tests for build_contextual_text()."""

from unittest.mock import Mock

from qdrant_loader.config.embedding import ContextualEmbeddingConfig
from qdrant_loader.core.embedding.contextual_embedding import build_contextual_text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _config(**kwargs) -> ContextualEmbeddingConfig:
    defaults = {
        "enabled": True,
        "include_title": True,
        "include_source_type": True,
        "include_source": False,
        "include_path": False,
        "include_section": False,
    }
    defaults.update(kwargs)
    return ContextualEmbeddingConfig(**defaults)


def _parent(
    title="Doc Title",
    source_type="confluence",
    source="my-space",
    breadcrumb_text="",
) -> Mock:
    p = Mock()
    p.title = title
    p.source_type = source_type
    p.source = source
    p.get_breadcrumb_text.return_value = breadcrumb_text
    return p


def _chunk(content="chunk body", *, parent=None, **meta) -> Mock:
    c = Mock()
    c.content = content
    c.metadata = dict(meta)
    if parent is not None:
        c.metadata["parent_document"] = parent
    return c


# ---------------------------------------------------------------------------
# Disabled / missing context
# ---------------------------------------------------------------------------

class TestBuildContextualTextDisabled:
    def test_returns_raw_content_when_disabled(self):
        chunk = _chunk(parent=_parent())
        assert build_contextual_text(chunk, _config(enabled=False)) == "chunk body"

    def test_returns_raw_content_when_no_parent_document(self):
        chunk = _chunk()  # no parent_document key in metadata
        assert build_contextual_text(chunk, _config()) == "chunk body"

    def test_returns_raw_content_when_all_flags_off(self):
        chunk = _chunk(parent=_parent())
        cfg = _config(
            include_title=False,
            include_source_type=False,
            include_source=False,
            include_path=False,
            include_section=False,
        )
        assert build_contextual_text(chunk, cfg) == "chunk body"


# ---------------------------------------------------------------------------
# Title
# ---------------------------------------------------------------------------

class TestBuildContextualTextTitle:
    def test_includes_title(self):
        chunk = _chunk(parent=_parent(title="API Guide"))
        cfg = _config(include_source_type=False)
        assert build_contextual_text(chunk, cfg) == "[Document: API Guide]\n\nchunk body"

    def test_skips_empty_title(self):
        chunk = _chunk(parent=_parent(title=""))
        cfg = _config(include_source_type=False)
        assert build_contextual_text(chunk, cfg) == "chunk body"


# ---------------------------------------------------------------------------
# Source type / source
# ---------------------------------------------------------------------------

class TestBuildContextualTextSource:
    def test_includes_source_type(self):
        chunk = _chunk(parent=_parent(source_type="jira"))
        cfg = _config(include_title=False)
        assert build_contextual_text(chunk, cfg) == "[Source: jira]\n\nchunk body"

    def test_includes_source_when_enabled(self):
        chunk = _chunk(parent=_parent(source="kb-space"))
        cfg = _config(include_title=False, include_source_type=False, include_source=True)
        assert build_contextual_text(chunk, cfg) == "[Collection: kb-space]\n\nchunk body"

    def test_omits_source_when_disabled(self):
        chunk = _chunk(parent=_parent(source="kb-space"))
        cfg = _config(include_title=False, include_source_type=False, include_source=False)
        assert build_contextual_text(chunk, cfg) == "chunk body"


# ---------------------------------------------------------------------------
# Path (document-level breadcrumb)
# ---------------------------------------------------------------------------

class TestBuildContextualTextPath:
    def test_includes_path(self):
        chunk = _chunk(parent=_parent(breadcrumb_text="Engineering > Security > API"))
        cfg = _config(include_title=False, include_source_type=False, include_path=True)
        assert build_contextual_text(chunk, cfg) == "[Path: Engineering > Security > API]\n\nchunk body"

    def test_skips_path_when_breadcrumb_empty(self):
        chunk = _chunk(parent=_parent(breadcrumb_text=""))
        cfg = _config(include_title=False, include_source_type=False, include_path=True)
        assert build_contextual_text(chunk, cfg) == "chunk body"

    def test_skips_path_when_flag_off(self):
        chunk = _chunk(parent=_parent(breadcrumb_text="Engineering > Security"))
        cfg = _config(include_title=False, include_source_type=False, include_path=False)
        assert build_contextual_text(chunk, cfg) == "chunk body"


# ---------------------------------------------------------------------------
# Section (chunk-level heading path)
# ---------------------------------------------------------------------------

class TestBuildContextualTextSection:
    def test_includes_section_from_list_breadcrumb(self):
        chunk = _chunk(
            parent=_parent(),
            breadcrumb=["Authentication", "OAuth2", "Token Refresh"],
        )
        cfg = _config(include_title=False, include_source_type=False, include_section=True)
        assert build_contextual_text(chunk, cfg) == "[Section: Authentication > OAuth2 > Token Refresh]\n\nchunk body"

    def test_includes_section_from_string_breadcrumb(self):
        chunk = _chunk(parent=_parent(), breadcrumb="Setup > Docker")
        cfg = _config(include_title=False, include_source_type=False, include_section=True)
        assert build_contextual_text(chunk, cfg) == "[Section: Setup > Docker]\n\nchunk body"

    def test_falls_back_to_parent_title(self):
        chunk = _chunk(parent=_parent(), parent_title="Docker Setup")
        cfg = _config(include_title=False, include_source_type=False, include_section=True)
        assert build_contextual_text(chunk, cfg) == "[Section: Docker Setup]\n\nchunk body"

    def test_skips_section_when_no_breadcrumb_and_no_parent_title(self):
        chunk = _chunk(parent=_parent())
        cfg = _config(include_title=False, include_source_type=False, include_section=True)
        assert build_contextual_text(chunk, cfg) == "chunk body"

    def test_skips_section_when_flag_off(self):
        chunk = _chunk(parent=_parent(), breadcrumb=["Auth", "OAuth2"])
        cfg = _config(include_title=False, include_source_type=False, include_section=False)
        assert build_contextual_text(chunk, cfg) == "chunk body"


# ---------------------------------------------------------------------------
# Full context — ordering and combined output
# ---------------------------------------------------------------------------

class TestBuildContextualTextFull:
    def test_full_prefix_all_fields(self):
        chunk = _chunk(
            content="Token expires in 3600s",
            parent=_parent(
                title="API Security Guide",
                source_type="confluence",
                source="eng-space",
                breadcrumb_text="Engineering > Security",
            ),
            breadcrumb=["Authentication", "OAuth2"],
        )
        cfg = _config(
            include_title=True,
            include_source_type=True,
            include_source=True,
            include_path=True,
            include_section=True,
        )
        expected = (
            "[Document: API Security Guide"
            " | Path: Engineering > Security"
            " | Section: Authentication > OAuth2"
            " | Source: confluence"
            " | Collection: eng-space"
            "]\n\nToken expires in 3600s"
        )
        assert build_contextual_text(chunk, cfg) == expected

    def test_part_order_is_title_path_section_source_collection(self):
        chunk = _chunk(
            parent=_parent(breadcrumb_text="Eng > Sec"),
            breadcrumb=["Setup"],
        )
        cfg = _config(include_source=True, include_path=True, include_section=True)
        result = build_contextual_text(chunk, cfg)
        inner = result.split("[")[1].split("]")[0]
        parts = inner.split(" | ")
        assert parts[0].startswith("Document:")
        assert parts[1].startswith("Path:")
        assert parts[2].startswith("Section:")
        assert parts[3].startswith("Source:")
        assert parts[4].startswith("Collection:")
