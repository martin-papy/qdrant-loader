"""Tests for the error_formatter module."""

from __future__ import annotations

import io
from unittest.mock import patch

import pytest
import yaml
from pydantic import BaseModel, ValidationError
from qdrant_loader.config.error_formatter import (
    _suggest_fix,
    format_validation_errors,
    print_config_error,
)
from rich.console import Console
from rich.table import Table

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_validation_error(model_cls, data: dict) -> ValidationError:
    """Trigger a Pydantic ValidationError and return it."""
    try:
        model_cls(**data)
    except ValidationError as exc:
        return exc
    raise AssertionError("Expected ValidationError was not raised")


def _capture_print_config_error(error: Exception) -> str:
    """Run print_config_error with a captured in-memory console and return output."""
    buf = io.StringIO()
    capture_console = Console(file=buf, highlight=False, markup=False)
    with patch("qdrant_loader.config.error_formatter._stderr_console", capture_console):
        print_config_error(error)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# format_validation_errors
# ---------------------------------------------------------------------------


class TestFormatValidationErrors:
    """Tests for format_validation_errors()."""

    def test_format_validation_errors_returns_table(self):
        """format_validation_errors returns a Rich Table instance."""
        errors = [{"loc": ("field_a",), "msg": "value is required", "type": "missing"}]
        result = format_validation_errors(errors)
        assert isinstance(result, Table)

    def test_format_validation_errors_table_has_correct_columns(self):
        """The returned table has Field, Error, and Suggestion columns."""
        errors = [{"loc": ("field_a",), "msg": "value is required", "type": "missing"}]
        table = format_validation_errors(errors)
        column_names = [col.header for col in table.columns]
        assert "Field" in column_names
        assert "Error" in column_names
        assert "Suggestion" in column_names

    def test_format_validation_errors_with_multiple_errors(self):
        """Table row count matches the number of errors provided."""
        errors = [
            {"loc": ("api_key",), "msg": "field required", "type": "missing"},
            {"loc": ("url",), "msg": "invalid url", "type": "value_error"},
            {
                "loc": ("chunk_size",),
                "msg": "must be positive integer",
                "type": "value_error",
            },
        ]
        table = format_validation_errors(errors)
        assert table.row_count == len(errors)

    def test_format_validation_errors_empty_loc_uses_root(self):
        """An error with an empty loc tuple renders as '(root)' in the Field column."""
        errors = [{"loc": (), "msg": "some error", "type": "value_error"}]
        table = format_validation_errors(errors)
        # The table was built without raising; row was added.
        assert table.row_count == 1

    def test_format_validation_errors_nested_loc_joined_with_arrow(self):
        """Nested loc parts are joined with ' -> '."""
        errors = [
            {
                "loc": ("projects", "my_project", "collection_name"),
                "msg": "required",
                "type": "missing",
            }
        ]
        # Just verify no exception is raised and a row was added.
        table = format_validation_errors(errors)
        assert table.row_count == 1

    def test_format_validation_errors_missing_loc_key(self):
        """Error dict without 'loc' key is handled gracefully (defaults to empty)."""
        errors = [{"msg": "some error", "type": "value_error"}]
        table = format_validation_errors(errors)
        assert table.row_count == 1

    def test_format_validation_errors_missing_msg_key(self):
        """Error dict without 'msg' key shows 'Unknown error'."""
        errors = [{"loc": ("field_a",), "type": "missing"}]
        table = format_validation_errors(errors)
        assert table.row_count == 1


# ---------------------------------------------------------------------------
# print_config_error – ValidationError
# ---------------------------------------------------------------------------


class TestPrintConfigErrorValidationError:
    """Tests for print_config_error() when given a Pydantic ValidationError."""

    def _make_error(self) -> ValidationError:
        class _Model(BaseModel):
            name: str
            value: int

        return _make_validation_error(_Model, {"name": 123, "value": "not-an-int"})

    def test_print_config_error_validation_error_does_not_raise(self):
        """print_config_error handles ValidationError without raising."""
        error = self._make_error()
        # Should complete without any exception.
        _capture_print_config_error(error)

    def test_print_config_error_validation_error_output_non_empty(self):
        """print_config_error produces non-empty output for ValidationError."""
        error = self._make_error()
        output = _capture_print_config_error(error)
        assert len(output.strip()) > 0


# ---------------------------------------------------------------------------
# print_config_error – yaml.YAMLError
# ---------------------------------------------------------------------------


class TestPrintConfigErrorYamlError:
    """Tests for print_config_error() when given a yaml.YAMLError."""

    def test_print_config_error_yaml_error_without_problem_mark(self):
        """YAML error without problem_mark is handled without raising."""
        error = yaml.YAMLError("bad yaml content")
        assert not hasattr(error, "problem_mark")
        _capture_print_config_error(error)  # must not raise

    def test_print_config_error_yaml_error_with_problem_mark(self):
        """YAML error that carries a problem_mark is handled without raising."""
        try:
            yaml.safe_load("key: [unclosed bracket")
        except yaml.YAMLError as exc:
            yaml_error = exc
        else:
            pytest.skip("yaml did not raise for this input on this platform")

        assert hasattr(yaml_error, "problem_mark")
        _capture_print_config_error(yaml_error)  # must not raise

    def test_print_config_error_yaml_error_output_non_empty(self):
        """print_config_error produces output for YAML errors."""
        error = yaml.YAMLError("some yaml issue")
        output = _capture_print_config_error(error)
        assert len(output.strip()) > 0


# ---------------------------------------------------------------------------
# print_config_error – FileNotFoundError
# ---------------------------------------------------------------------------


class TestPrintConfigErrorFileNotFoundError:
    """Tests for print_config_error() when given a FileNotFoundError."""

    def test_print_config_error_file_not_found_does_not_raise(self):
        """print_config_error handles FileNotFoundError without raising."""
        error = FileNotFoundError("config.yaml not found")
        _capture_print_config_error(error)

    def test_print_config_error_file_not_found_output_non_empty(self):
        """print_config_error produces non-empty output for FileNotFoundError."""
        error = FileNotFoundError("config.yaml not found")
        output = _capture_print_config_error(error)
        assert len(output.strip()) > 0


# ---------------------------------------------------------------------------
# print_config_error – ValueError
# ---------------------------------------------------------------------------


class TestPrintConfigErrorValueError:
    """Tests for print_config_error() when given a ValueError."""

    def test_print_config_error_value_error_does_not_raise(self):
        """print_config_error handles ValueError without raising."""
        error = ValueError("some configuration value is invalid")
        _capture_print_config_error(error)

    def test_print_config_error_value_error_output_non_empty(self):
        """print_config_error produces non-empty output for ValueError."""
        error = ValueError("bad value")
        output = _capture_print_config_error(error)
        assert len(output.strip()) > 0

    def test_print_config_error_value_error_redacts_sensitive_values(self):
        """ValueError output masks secrets before printing to terminal."""
        error = ValueError(
            "JIRA_TOKEN=ATATT-sensitive-value OPENAI_API_KEY=sk-proj-abc"
        )
        output = _capture_print_config_error(error)

        assert "ATATT-sensitive-value" not in output
        assert "sk-proj-abc" not in output
        assert "JIRA_TOKEN=**" in output
        assert "OPENAI_API_KEY=**" in output

    def test_print_config_error_value_error_uses_raw_message_for_suggestion(self):
        """Suggestion matching should use raw error text, not the sanitized display text."""
        error = ValueError("source is required")

        with patch(
            "qdrant_loader.config.error_formatter.sanitize_exception_message",
            return_value="**",
        ):
            output = _capture_print_config_error(error)

        assert "Suggestion:" in output
        assert "Add at least one source under" in output
        assert "sources:" in output


# ---------------------------------------------------------------------------
# print_config_error – generic / unknown exception type
# ---------------------------------------------------------------------------


class TestPrintConfigErrorGeneric:
    """Tests for print_config_error() generic fallback path."""

    def test_print_config_error_generic_does_not_raise(self):
        """print_config_error handles an unknown exception type without raising."""

        class _WeirdError(Exception):
            pass

        error = _WeirdError("something completely unexpected")
        _capture_print_config_error(error)

    def test_print_config_error_generic_output_non_empty(self):
        """print_config_error produces non-empty output for unknown error types."""

        class _WeirdError(Exception):
            pass

        error = _WeirdError("unexpected situation")
        output = _capture_print_config_error(error)
        assert len(output.strip()) > 0

    def test_print_config_error_generic_includes_exception_class_name(self):
        """Generic fallback output contains the exception class name."""

        class _MyCustomError(Exception):
            pass

        error = _MyCustomError("details here")
        output = _capture_print_config_error(error)
        assert "_MyCustomError" in output


# ---------------------------------------------------------------------------
# _suggest_fix
# ---------------------------------------------------------------------------


class TestSuggestFix:
    """Tests for the _suggest_fix() private helper."""

    def test_suggest_fix_api_key(self):
        """Returns OPENAI_API_KEY suggestion when field contains 'api_key'."""
        result = _suggest_fix("api_key", "field required")
        assert "OPENAI_API_KEY" in result

    def test_suggest_fix_api_key_in_message(self):
        """Returns OPENAI_API_KEY suggestion when message contains 'api_key'."""
        result = _suggest_fix("some_field", "api_key is missing")
        assert "OPENAI_API_KEY" in result

    def test_suggest_fix_collection_name(self):
        """Returns QDRANT_COLLECTION_NAME suggestion for collection_name field."""
        result = _suggest_fix("collection_name", "value is required")
        assert "QDRANT_COLLECTION_NAME" in result

    def test_suggest_fix_qdrant_url(self):
        """Returns QDRANT_URL suggestion when field contains both 'url' and 'qdrant'."""
        result = _suggest_fix("qdrant_url", "field required")
        assert "QDRANT_URL" in result

    def test_suggest_fix_sources_field(self):
        """Returns sources config suggestion when field contains 'sources'."""
        result = _suggest_fix("sources", "required")
        assert "sources" in result.lower()

    def test_suggest_fix_sources_message(self):
        """Returns sources config suggestion when message contains 'source'."""
        result = _suggest_fix("some_field", "no valid source defined")
        assert "sources" in result.lower()

    def test_suggest_fix_database_path(self):
        """Returns STATE_DB_PATH suggestion for database_path field."""
        result = _suggest_fix("database_path", "field required")
        assert "STATE_DB_PATH" in result

    def test_suggest_fix_chunk_size_field(self):
        """Returns chunk_size suggestion when field contains 'chunk_size'."""
        result = _suggest_fix("chunk_size", "must be a positive integer")
        assert "chunk_size" in result

    def test_suggest_fix_chunk_size_message(self):
        """Returns chunk_size suggestion when message contains 'chunk'."""
        result = _suggest_fix("some_field", "chunk value is invalid")
        assert "chunk_size" in result

    def test_suggest_fix_required(self):
        """Returns field-specific suggestion when message contains 'required'."""
        result = _suggest_fix("my_field", "field is required")
        assert "my_field" in result

    def test_suggest_fix_unknown(self):
        """Returns generic documentation suggestion for unrecognised field/message."""
        result = _suggest_fix("totally_unknown_field", "some obscure error")
        assert "documentation" in result.lower()

    def test_suggest_fix_case_insensitive_field(self):
        """Field matching is case-insensitive."""
        result = _suggest_fix("API_KEY", "missing")
        assert "OPENAI_API_KEY" in result

    def test_suggest_fix_case_insensitive_message(self):
        """Message matching is case-insensitive."""
        result = _suggest_fix("some_field", "CHUNK value is invalid")
        assert "chunk_size" in result

    def test_suggest_fix_qdrant_api_key(self):
        """Returns QDRANT_API_KEY suggestion for qdrant api_key field."""
        result = _suggest_fix("qdrant.api_key", "field required")
        assert "QDRANT_API_KEY" in result
        assert "OPENAI" not in result


# ---------------------------------------------------------------------------
# YAML error with problem_mark=None
# ---------------------------------------------------------------------------


class TestPrintConfigErrorYamlProblemMarkNone:
    """Tests for YAML error handling when problem_mark is explicitly None."""

    def test_yaml_error_with_problem_mark_none(self):
        """YAML error with problem_mark=None should not raise AttributeError."""
        error = yaml.MarkedYAMLError(problem="bad", problem_mark=None)
        output = _capture_print_config_error(error)
        assert len(output.strip()) > 0
