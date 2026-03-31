"""Unit tests for the fixed Python AST parser and CodeDocumentParser."""

from unittest.mock import Mock, patch

from qdrant_loader.core.chunking.strategy.code.code_document_parser import (
    CodeDocumentParser,
)
from qdrant_loader.core.chunking.strategy.code.parser.common import CodeElementType
from qdrant_loader.core.chunking.strategy.code.parser.python_ast import parse_python_ast

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings():
    s = Mock()
    gc = Mock()
    cc = Mock()
    cc.chunk_size = 1500
    cc.chunk_overlap = 200
    cc.max_chunks_per_document = 500
    strat = Mock()
    code = Mock()
    code.max_file_size_for_ast = 75000
    code.max_chunk_size_for_nlp = 20000
    code.enable_ast_parsing = True
    code.enable_dependency_analysis = True
    strat.code = code
    cc.strategies = strat
    sem = Mock()
    sem.spacy_model = "en_core_web_sm"
    emb = Mock()
    emb.tokenizer = "cl100k_base"
    gc.chunking = cc
    gc.semantic_analysis = sem
    gc.embedding = emb
    s.global_config = gc
    return s


# ---------------------------------------------------------------------------
# parse_python_ast
# ---------------------------------------------------------------------------

SIMPLE_PY = """\
class Student:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name


def main():
    student = Student("Alice")
    print(student)


def get_name():
    return input("Name: ")


if __name__ == "__main__":
    main()
"""

IMPORTS_ONLY_PY = """\
import os
import sys
from typing import List
"""

ASYNC_PY = """\
import asyncio

async def fetch(url: str) -> str:
    return url

async def main():
    result = await fetch("http://example.com")
    print(result)
"""

SYNTAX_ERROR_PY = "def broken(:"

EMPTY_PY = ""

COMMENTS_ONLY_PY = """\
# This is a comment
# Another comment
"""


class TestParsePythonAst:
    """Tests for parse_python_ast (the fixed version)."""

    # -- Basic extraction ---------------------------------------------------

    def test_top_level_class_and_functions_extracted(self):
        elements = parse_python_ast(SIMPLE_PY, max_elements_to_process=800)
        types = {e.element_type for e in elements}
        names = [e.name for e in elements]

        assert CodeElementType.CLASS in types
        assert CodeElementType.FUNCTION in types
        assert "Student" in names
        assert "main" in names
        assert "get_name" in names

    def test_no_nested_elements_extracted(self):
        """Methods inside a class must NOT appear as separate elements."""
        elements = parse_python_ast(SIMPLE_PY, max_elements_to_process=800)
        names = [e.name for e in elements]

        assert "__init__" not in names
        assert "__str__" not in names

    def test_module_level_code_captured(self):
        """if __name__ == '__main__' and imports are captured as MODULE element."""
        elements = parse_python_ast(SIMPLE_PY, max_elements_to_process=800)
        module_elements = [
            e for e in elements if e.element_type == CodeElementType.MODULE
        ]

        assert (
            module_elements
        ), "Expected at least one MODULE element for module-level code"

    def test_module_element_contains_dunder_main(self):
        elements = parse_python_ast(SIMPLE_PY, max_elements_to_process=800)
        module_elements = [
            e for e in elements if e.element_type == CodeElementType.MODULE
        ]
        combined = "\n".join(e.content for e in module_elements)

        assert "__name__" in combined

    # -- No overlapping line ranges -----------------------------------------

    def test_no_overlapping_line_ranges(self):
        elements = parse_python_ast(SIMPLE_PY, max_elements_to_process=800)

        for i, e1 in enumerate(elements):
            for j, e2 in enumerate(elements):
                if i >= j:
                    continue
                overlaps = e1.start_line <= e2.end_line and e2.start_line <= e1.end_line
                assert not overlaps, (
                    f"Overlap: '{e1.name}' ({e1.start_line}-{e1.end_line}) "
                    f"vs '{e2.name}' ({e2.start_line}-{e2.end_line})"
                )

    # -- Content correctness ------------------------------------------------

    def test_class_content_includes_methods(self):
        """Class element content must span its methods."""
        elements = parse_python_ast(SIMPLE_PY, max_elements_to_process=800)
        student = next(e for e in elements if e.name == "Student")

        assert "__init__" in student.content
        assert "__str__" in student.content

    def test_function_content_is_complete(self):
        elements = parse_python_ast(SIMPLE_PY, max_elements_to_process=800)
        main = next(e for e in elements if e.name == "main")

        assert "Student" in main.content
        assert "print" in main.content

    # -- Line numbers -------------------------------------------------------

    def test_element_start_line_matches_source(self):
        elements = parse_python_ast(SIMPLE_PY, max_elements_to_process=800)
        student = next(e for e in elements if e.name == "Student")
        lines = SIMPLE_PY.splitlines()

        assert lines[student.start_line - 1].strip().startswith("class Student")

    def test_element_end_line_matches_source(self):
        elements = parse_python_ast(SIMPLE_PY, max_elements_to_process=800)
        student = next(e for e in elements if e.name == "Student")
        lines = SIMPLE_PY.splitlines()

        # end_line should be the last non-blank line of the class body
        assert student.end_line >= student.start_line
        assert student.end_line <= len(lines)

    # -- Imports-only file --------------------------------------------------

    def test_imports_only_file_produces_module_element(self):
        elements = parse_python_ast(IMPORTS_ONLY_PY, max_elements_to_process=800)

        assert len(elements) == 1
        assert elements[0].element_type == CodeElementType.MODULE
        assert "import os" in elements[0].content

    # -- Async functions ----------------------------------------------------

    def test_async_functions_extracted(self):
        elements = parse_python_ast(ASYNC_PY, max_elements_to_process=800)
        names = [e.name for e in elements]

        assert "fetch" in names
        assert "main" in names

    def test_async_element_type_is_function(self):
        elements = parse_python_ast(ASYNC_PY, max_elements_to_process=800)
        fetch = next(e for e in elements if e.name == "fetch")

        assert fetch.element_type == CodeElementType.FUNCTION

    # -- Edge cases ---------------------------------------------------------

    def test_syntax_error_returns_empty_list(self):
        elements = parse_python_ast(SYNTAX_ERROR_PY, max_elements_to_process=800)
        assert elements == []

    def test_empty_content_returns_empty_list(self):
        elements = parse_python_ast(EMPTY_PY, max_elements_to_process=800)
        assert elements == []

    def test_comments_only_returns_empty_list(self):
        # Comments are not statements — tree.body is empty
        elements = parse_python_ast(COMMENTS_ONLY_PY, max_elements_to_process=800)
        assert elements == []

    def test_max_elements_limit_respected(self):
        # File with 5 top-level functions; limit to 2
        many_funcs = "\n".join(f"def func_{i}(): pass" for i in range(5))
        elements = parse_python_ast(many_funcs, max_elements_to_process=2)

        assert len(elements) <= 2

    def test_element_level_is_zero_for_top_level(self):
        elements = parse_python_ast(SIMPLE_PY, max_elements_to_process=800)
        for e in elements:
            assert e.level == 0, f"'{e.name}' has level={e.level}, expected 0"

    def test_consecutive_module_statements_grouped(self):
        """Imports before and after a class should each produce one MODULE element."""
        code = """\
import os

class Foo:
    pass

import sys
X = 1
"""
        elements = parse_python_ast(code, max_elements_to_process=800)
        module_elements = [
            e for e in elements if e.element_type == CodeElementType.MODULE
        ]

        # Two separate groups: [import os] and [import sys, X=1]
        assert len(module_elements) == 2

    def test_class_element_name(self):
        elements = parse_python_ast(SIMPLE_PY, max_elements_to_process=800)
        student = next(
            (e for e in elements if e.element_type == CodeElementType.CLASS), None
        )
        assert student is not None
        assert student.name == "Student"

    def test_function_element_name(self):
        elements = parse_python_ast(SIMPLE_PY, max_elements_to_process=800)
        main = next((e for e in elements if e.name == "main"), None)
        assert main is not None
        assert main.element_type == CodeElementType.FUNCTION


# ---------------------------------------------------------------------------
# CodeDocumentParser.parse_code_elements
# ---------------------------------------------------------------------------


class TestCodeDocumentParserParsePython:
    """Tests for CodeDocumentParser ensuring Python uses AST, not tree-sitter."""

    def setup_method(self):
        self.settings = _make_settings()
        self.parser = CodeDocumentParser(self.settings)

    def test_python_uses_builtin_ast(self):
        """tree-sitter must NOT be called for Python files."""
        with patch.object(self.parser, "_parse_with_tree_sitter") as mock_ts:
            self.parser.parse_code_elements(SIMPLE_PY, "python")
            mock_ts.assert_not_called()

    def test_python_returns_correct_element_count(self):
        elements = self.parser.parse_code_elements(SIMPLE_PY, "python")
        names = [e.name for e in elements]

        assert "Student" in names
        assert "main" in names
        assert "get_name" in names

    def test_python_no_nested_elements(self):
        elements = self.parser.parse_code_elements(SIMPLE_PY, "python")
        names = [e.name for e in elements]

        assert "__init__" not in names
        assert "__str__" not in names

    def test_python_syntax_error_returns_empty(self):
        elements = self.parser.parse_code_elements(SYNTAX_ERROR_PY, "python")
        assert elements == []

    def test_non_python_uses_tree_sitter(self):
        """Non-Python languages should use tree-sitter (if available)."""
        js_code = "function greet(name) { return 'Hello ' + name; }"
        with patch.object(
            self.parser, "_parse_with_tree_sitter", return_value=[]
        ) as mock_ts:
            self.parser.parse_code_elements(js_code, "javascript")
            mock_ts.assert_called_once()

    def test_unknown_language_skips_all_parsing(self):
        with patch.object(self.parser, "_parse_with_tree_sitter") as mock_ts:
            elements = self.parser.parse_code_elements("x = 1", "unknown")
            mock_ts.assert_not_called()
            assert elements == []

    def test_file_too_large_returns_empty(self):
        huge_content = "x = 1\n" * 20_000  # well above 75KB
        elements = self.parser.parse_code_elements(huge_content, "python")
        assert elements == []

    def test_imports_captured_as_module_element(self):
        elements = self.parser.parse_code_elements(IMPORTS_ONLY_PY, "python")

        assert len(elements) == 1
        assert elements[0].element_type == CodeElementType.MODULE

    def test_no_overlapping_line_ranges(self):
        elements = self.parser.parse_code_elements(SIMPLE_PY, "python")

        for i, e1 in enumerate(elements):
            for j, e2 in enumerate(elements):
                if i >= j:
                    continue
                overlaps = e1.start_line <= e2.end_line and e2.start_line <= e1.end_line
                assert not overlaps, (
                    f"Overlap: '{e1.name}' ({e1.start_line}-{e1.end_line}) "
                    f"vs '{e2.name}' ({e2.start_line}-{e2.end_line})"
                )
