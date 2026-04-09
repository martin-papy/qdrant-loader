"""Tests for sensitive-data redaction utilities."""

from qdrant_loader.utils.sensitive import (
    redact_sensitive_data,
    sanitize_exception_message,
)


def test_redact_sensitive_data_masks_key_value_patterns() -> None:
    raw = "JIRA_TOKEN=ATATT-super-secret-value OPENAI_API_KEY=sk-proj-very-secret"
    redacted = redact_sensitive_data(raw)

    assert "ATATT-super-secret-value" not in redacted
    assert "sk-proj-very-secret" not in redacted
    assert "JIRA_TOKEN=**" in redacted
    assert "OPENAI_API_KEY=**" in redacted


def test_redact_sensitive_data_masks_pydantic_input_value() -> None:
    raw = (
        "Validation error ... input_value={'token': 'ABCD123', 'x': 1}, input_type=dict"
    )
    redacted = redact_sensitive_data(raw)

    assert "ABCD123" not in redacted
    assert "input_value=**" in redacted


def test_redact_sensitive_data_masks_deeply_nested_input_value() -> None:
    raw = (
        "Validation error ... input_value={'outer': {'inner': [{'token': 'ATATT-secret'}, "
        "{'client_secret': 'top-secret'}]}, 'ok': 1}, input_type=dict"
    )
    redacted = redact_sensitive_data(raw)

    assert "ATATT-secret" not in redacted
    assert "top-secret" not in redacted
    assert "input_value=**" in redacted
    assert "input_type=dict" in redacted


def test_redact_sensitive_data_masks_quoted_input_value_with_commas() -> None:
    raw = 'Validation error ... input_value="token=abc,secret=def", input_type=str'
    redacted = redact_sensitive_data(raw)

    assert "token=abc" not in redacted
    assert "secret=def" not in redacted
    assert "input_value=**" in redacted
    assert "input_type=str" in redacted


def test_sanitize_exception_message_masks_openai_key() -> None:
    error = ValueError("OPENAI_API_KEY=sk-proj-abcdef123456")
    safe = sanitize_exception_message(error)

    assert "sk-proj-abcdef123456" not in safe
    assert "OPENAI_API_KEY=**" in safe


def test_sanitize_exception_message_masks_jira_config_repr() -> None:
    error = ValueError(
        "JiraProjectConfig(source='jira', token='ATATT-very-secret-token', email='user@example.com')"
    )
    safe = sanitize_exception_message(error)

    assert "ATATT-very-secret-token" not in safe
    assert "token=**" in safe
