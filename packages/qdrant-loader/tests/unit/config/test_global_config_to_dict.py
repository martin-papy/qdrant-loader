"""Regression tests for GlobalConfig.to_dict() file_conversion serialization.

The parser round-trips the global config THROUGH to_dict() before deep-merging
project overrides (config/parser.py _merge_configs -> _deep_merge_dicts). If
to_dict() omits the docling engine selection and its settings sub-tree, every
multi-project setup silently reverts to the markitdown default. These tests pin
both the presence of the keys and their re-parse safety.
"""

from qdrant_loader.config.global_config import GlobalConfig
from qdrant_loader.core.file_conversion import FileConversionConfig


def _global_config_with_docling() -> GlobalConfig:
    return GlobalConfig(
        skip_validation=True,
        file_conversion={
            "engine": "docling",
            "docling": {"profile": "accurate", "num_threads": 8},
        },
    )


def test_to_dict_includes_engine_and_docling_block():
    cfg = _global_config_with_docling()

    file_conversion = cfg.to_dict()["file_conversion"]

    # engine must be the plain string value of the StrEnum
    assert file_conversion["engine"] == "docling"
    assert isinstance(file_conversion["engine"], str)

    # docling settings sub-tree must be present and reflect the overrides
    assert "docling" in file_conversion
    assert file_conversion["docling"]["profile"] == "accurate"
    assert file_conversion["docling"]["num_threads"] == 8

    # existing keys must remain untouched
    assert "max_file_size" in file_conversion
    assert "conversion_timeout" in file_conversion
    assert "markitdown" in file_conversion


def test_to_dict_file_conversion_round_trips_through_FileConversionConfig():
    """Mirrors the parser merge path: the dict must re-validate without losing
    the docling engine selection or its settings."""
    cfg = _global_config_with_docling()

    file_conversion = cfg.to_dict()["file_conversion"]

    # The merged dict is re-parsed by pydantic; the StrEnum must come back as a
    # string that re-validates to the docling engine.
    reparsed = FileConversionConfig(**file_conversion)

    assert reparsed.engine.value == "docling"
    assert reparsed.docling.profile.value == "accurate"
    assert reparsed.docling.num_threads == 8


def test_to_dict_round_trips_through_GlobalConfig():
    """The full global dict must survive a GlobalConfig re-parse (the actual
    shape parser._merge_configs feeds downstream)."""
    cfg = _global_config_with_docling()

    reparsed = GlobalConfig(skip_validation=True, **cfg.to_dict())

    assert reparsed.file_conversion.engine.value == "docling"
    assert reparsed.file_conversion.docling.profile.value == "accurate"
    assert reparsed.file_conversion.docling.num_threads == 8
