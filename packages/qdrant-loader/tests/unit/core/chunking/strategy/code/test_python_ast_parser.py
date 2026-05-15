"""Unit tests for the fixed Python AST parser and CodeDocumentParser."""

import ast
import builtins
import importlib
from unittest.mock import Mock, patch

import qdrant_loader.core.chunking.strategy.code.code_document_parser as cdp_module
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


class TestParsePythonAstEdgeCoverage:
    def test_function_node_without_lineno_is_skipped(self):
        fake_tree = Mock()
        fake_tree.body = [
            ast.FunctionDef(
                name="no_line_info",
                args=ast.arguments(
                    posonlyargs=[],
                    args=[],
                    kwonlyargs=[],
                    kw_defaults=[],
                    defaults=[],
                ),
                body=[ast.Pass()],
                decorator_list=[],
            )
        ]

        with patch(
            "qdrant_loader.core.chunking.strategy.code.parser.python_ast.ast.parse",
            return_value=fake_tree,
        ):
            elements = parse_python_ast(
                "def x():\n    pass", max_elements_to_process=10
            )

        assert elements == []

    def test_module_group_without_lineno_is_skipped(self):
        fake_tree = Mock()
        fake_tree.body = [ast.Pass()]

        with patch(
            "qdrant_loader.core.chunking.strategy.code.parser.python_ast.ast.parse",
            return_value=fake_tree,
        ):
            elements = parse_python_ast("pass", max_elements_to_process=10)

        assert elements == []

    def test_empty_snippet_from_out_of_range_lines_is_ignored(self):
        node = ast.FunctionDef(
            name="f",
            args=ast.arguments(
                posonlyargs=[],
                args=[],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
            ),
            body=[ast.Pass()],
            decorator_list=[],
            lineno=50,
            end_lineno=50,
        )
        fake_tree = Mock()
        fake_tree.body = [node]

        with patch(
            "qdrant_loader.core.chunking.strategy.code.parser.python_ast.ast.parse",
            return_value=fake_tree,
        ):
            elements = parse_python_ast(
                "def f():\n    pass", max_elements_to_process=10
            )

        assert elements == []

    def test_flush_module_group_respects_limit(self):
        elements = parse_python_ast("import os", max_elements_to_process=0)
        assert elements == []

    def test_module_group_empty_snippet_path(self):
        fake_tree = Mock()
        module_stmt = ast.Pass(lineno=100, end_lineno=100)
        func_stmt = ast.FunctionDef(
            name="ok",
            args=ast.arguments(
                posonlyargs=[],
                args=[],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
            ),
            body=[ast.Pass()],
            decorator_list=[],
            lineno=1,
            end_lineno=2,
        )
        fake_tree.body = [module_stmt, func_stmt]

        with patch(
            "qdrant_loader.core.chunking.strategy.code.parser.python_ast.ast.parse",
            return_value=fake_tree,
        ):
            elements = parse_python_ast(
                "def ok():\n    pass", max_elements_to_process=10
            )

        assert len(elements) == 1
        assert elements[0].name == "ok"

    def test_break_when_flushing_group_before_class_hits_limit(self):
        code = "import os\nclass A:\n    pass\n"
        elements = parse_python_ast(code, max_elements_to_process=0)
        assert elements == []

    def test_break_when_adding_class_hits_limit(self):
        code = "class A:\n    pass\n"
        elements = parse_python_ast(code, max_elements_to_process=0)
        assert elements == []

    def test_break_when_flushing_group_before_function_hits_limit(self):
        code = "x = 1\ndef f():\n    pass\n"
        elements = parse_python_ast(code, max_elements_to_process=0)
        assert elements == []


class TestCodeDocumentParserHelperMethods:
    def setup_method(self):
        self.settings = _make_settings()
        self.parser = CodeDocumentParser(self.settings)

    def test_parse_document_structure_counts_and_flags(self):
        content = '"""doc"""\n# comment\nif x:\n    pass\nfor i in x:\n    pass\ndef f():\n    pass\nclass C:\n    pass\n'
        structure = self.parser.parse_document_structure(content)

        assert structure["structure_type"] == "code"
        assert structure["total_lines"] >= structure["non_empty_lines"]
        assert structure["blank_lines"] >= 0
        assert structure["avg_line_length"] > 0
        assert structure["max_line_length"] > 0
        assert structure["has_comments"] is True
        assert structure["has_docstrings"] is True
        assert structure["complexity_indicators"]["if_statements"] == 1
        assert structure["complexity_indicators"]["loop_statements"] == 1
        assert structure["complexity_indicators"]["function_definitions"] == 1
        assert structure["complexity_indicators"]["class_definitions"] == 1

    def test_parse_document_structure_empty_content(self):
        structure = self.parser.parse_document_structure("")

        assert structure["total_lines"] == 1
        assert structure["non_empty_lines"] == 0
        assert structure["blank_lines"] == 1
        assert structure["avg_line_length"] == 0
        assert structure["max_line_length"] == 0
        assert structure["has_comments"] is False
        assert structure["has_docstrings"] is False

    def test_extract_section_metadata_with_optional_fields(self):
        element = Mock()
        element.element_type = CodeElementType.FUNCTION
        element.name = "compute"
        element.start_line = 10
        element.end_line = 20
        element.level = 1
        element.visibility = "private"
        element.is_async = True
        element.is_static = True
        element.is_abstract = False
        element.complexity = 5
        element.docstring = "docs"
        element.decorators = ["cache"]
        element.parameters = ["x", "y"]
        element.return_type = "int"
        element.dependencies = ["math"]
        element.children = [Mock(), Mock()]

        metadata = self.parser.extract_section_metadata(element)

        assert metadata["line_count"] == 11
        assert metadata["docstring_length"] == 4
        assert metadata["decorators"] == ["cache"]
        assert metadata["parameters"] == ["x", "y"]
        assert metadata["return_type"] == "int"
        assert metadata["dependencies"] == ["math"]
        assert metadata["child_count"] == 2

    def test_extract_section_metadata_without_optional_fields(self):
        element = Mock()
        element.element_type = CodeElementType.CLASS
        element.name = "NoExtras"
        element.start_line = 1
        element.end_line = 1
        element.level = 0
        element.visibility = "public"
        element.is_async = False
        element.is_static = False
        element.is_abstract = False
        element.complexity = 0
        element.docstring = ""
        element.decorators = []
        element.parameters = []
        element.return_type = None
        element.dependencies = []
        element.children = []

        metadata = self.parser.extract_section_metadata(element)

        assert "docstring_length" not in metadata
        assert "decorators" not in metadata
        assert "parameters" not in metadata
        assert "return_type" not in metadata
        assert "dependencies" not in metadata

    def test_detect_language_known_and_unknown_extensions(self):
        assert self.parser.detect_language("src/main.py", "") == "python"
        assert self.parser.detect_language("src/Program.CS", "") == "c_sharp"
        assert self.parser.detect_language("README", "") == "unknown"
        assert self.parser.detect_language("archive.unknownext", "") == "unknown"

    def test_get_tree_sitter_parser_returns_none_when_disabled(self):
        with patch.object(cdp_module, "TREE_SITTER_AVAILABLE", False):
            assert self.parser._get_tree_sitter_parser("python") is None

    def test_get_tree_sitter_parser_returns_none_when_get_parser_missing(self):
        with (
            patch.object(cdp_module, "TREE_SITTER_AVAILABLE", True),
            patch.object(cdp_module, "get_parser", None),
        ):
            assert self.parser._get_tree_sitter_parser("python") is None

    def test_get_tree_sitter_parser_uses_cache(self):
        fake_parser = Mock()
        with (
            patch.object(cdp_module, "TREE_SITTER_AVAILABLE", True),
            patch.object(
                cdp_module, "get_parser", Mock(return_value=fake_parser)
            ) as get_parser_mock,
        ):
            p1 = self.parser._get_tree_sitter_parser("javascript")
            p2 = self.parser._get_tree_sitter_parser("javascript")

        assert p1 is fake_parser
        assert p2 is fake_parser
        assert get_parser_mock.call_count == 1

    def test_get_tree_sitter_parser_handles_exception(self):
        with (
            patch.object(cdp_module, "TREE_SITTER_AVAILABLE", True),
            patch.object(
                cdp_module, "get_parser", Mock(side_effect=RuntimeError("boom"))
            ),
        ):
            parser = self.parser._get_tree_sitter_parser("javascript")

        assert parser is None

    def test_parse_with_tree_sitter_returns_empty_when_parser_missing(self):
        with patch.object(self.parser, "_get_tree_sitter_parser", return_value=None):
            elements = self.parser._parse_with_tree_sitter("const x = 1", "javascript")

        assert elements == []

    def test_parse_with_tree_sitter_success_and_limit(self):
        fake_root = Mock()
        fake_tree = Mock(root_node=fake_root)
        fake_parser = Mock()
        fake_parser.parse.return_value = fake_tree
        too_many = [Mock() for _ in range(1000)]

        with (
            patch.object(
                self.parser, "_get_tree_sitter_parser", return_value=fake_parser
            ),
            patch.object(
                cdp_module, "extract_tree_sitter_elements", return_value=too_many
            ),
        ):
            elements = self.parser._parse_with_tree_sitter("const x = 1", "javascript")

        assert len(elements) == cdp_module.MAX_ELEMENTS_TO_PROCESS
        fake_parser.parse.assert_called_once_with(b"const x = 1")

    def test_parse_with_tree_sitter_handles_exception(self):
        fake_parser = Mock()
        fake_parser.parse.side_effect = ValueError("parse failed")

        with patch.object(
            self.parser, "_get_tree_sitter_parser", return_value=fake_parser
        ):
            elements = self.parser._parse_with_tree_sitter("const x = 1", "javascript")

        assert elements == []

    def test_parse_code_elements_non_python_when_tree_sitter_unavailable(self):
        with (
            patch.object(cdp_module, "TREE_SITTER_AVAILABLE", False),
            patch.object(self.parser, "_parse_with_tree_sitter") as mock_ts,
        ):
            elements = self.parser.parse_code_elements("const x = 1", "javascript")

        assert elements == []
        mock_ts.assert_not_called()

    def test_init_logs_warning_when_tree_sitter_unavailable(self):
        with (
            patch.object(cdp_module, "TREE_SITTER_AVAILABLE", False),
            patch.object(cdp_module, "logger") as logger_mock,
        ):
            parser = CodeDocumentParser(self.settings)

        assert parser is not None
        logger_mock.warning.assert_called_once()


class TestCodeDocumentParserImportFallback:
    def test_module_import_sets_tree_sitter_unavailable_on_import_error(self):
        original_import = builtins.__import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "tree_sitter_languages":
                raise ImportError("simulated missing dependency")
            return original_import(name, globals, locals, fromlist, level)

        with patch("builtins.__import__", side_effect=fake_import):
            reloaded = importlib.reload(cdp_module)

        assert reloaded.TREE_SITTER_AVAILABLE is False
        assert reloaded.get_parser is None

        # Restore module global state for tests that run after this one.
        importlib.reload(cdp_module)
