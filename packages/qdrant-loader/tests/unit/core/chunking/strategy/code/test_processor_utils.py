from __future__ import annotations

from qdrant_loader.core.chunking.strategy.code.processor import utils


def test_is_minified_code_detects_long_dense_content():
    content = "{" * 210 + "}" * 210
    assert utils.is_minified_code(content)


def test_has_meaningful_names_simple():
    content = "def compute_value(total_cost):\n    return total_cost * 1.1\n"
    assert utils.has_meaningful_names(content)
    bad = "def foo(x):\n    return x\n"
    assert not utils.has_meaningful_names(bad)


def test_determine_learning_level():
    assert utils.determine_learning_level(0) == "beginner"
    assert utils.determine_learning_level(3) == "intermediate"
    assert utils.determine_learning_level(10) == "advanced"






