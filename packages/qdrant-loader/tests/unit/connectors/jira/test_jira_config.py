"""Unit tests for JiraProjectConfig – validate_no_placeholders validator."""

import pytest
from pydantic import HttpUrl, ValidationError
from qdrant_loader.config.types import SourceType
from qdrant_loader.connectors.jira.config import JiraDeploymentType, JiraProjectConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_VALID: dict = {
    "base_url": HttpUrl("https://test.atlassian.net"),
    "deployment_type": JiraDeploymentType.CLOUD,
    "project_key": "TEST",
    "source": "test-jira",
    "source_type": SourceType.JIRA,
    "token": "real-token",
    "email": "user@example.com",
}


def _make(**overrides) -> JiraProjectConfig:
    """Return a valid config, optionally overriding fields."""
    return JiraProjectConfig(**{**_BASE_VALID, **overrides})


def _error_messages(exc_info: pytest.ExceptionInfo) -> str:
    """Flatten all pydantic ValidationError messages into one string."""
    return " | ".join(str(e["msg"]) for e in exc_info.value.errors())


# ---------------------------------------------------------------------------
# Happy-path: no placeholders
# ---------------------------------------------------------------------------


class TestValidateNoPlaceholders:
    """validate_no_placeholders – happy paths (no ${...} remaining)."""

    def test_all_real_values_accepted(self):
        from urllib.parse import urlparse

        cfg = _make()
        assert cfg.project_key == "TEST"
        parsed = urlparse(str(cfg.base_url))
        assert parsed.scheme == "https"
        assert parsed.hostname == "test.atlassian.net"

    def test_datacenter_no_email_accepted(self):
        """Data Center deployment does not require email."""
        cfg = _make(
            base_url=HttpUrl("https://jira.corp.com"),
            deployment_type=JiraDeploymentType.DATACENTER,
            email=None,
        )
        assert cfg.deployment_type == JiraDeploymentType.DATACENTER

    def test_dollar_sign_not_in_brace_accepted(self):
        """A bare $ that is not part of ${...} must NOT be flagged."""
        cfg = _make(project_key="PRICE$100")
        assert cfg.project_key == "PRICE$100"


# ---------------------------------------------------------------------------
# project_key contains placeholder
# ---------------------------------------------------------------------------


class TestPlaceholderInProjectKey:
    def test_placeholder_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            _make(project_key="${JIRA_PROJECT_KEY}")
        msg = _error_messages(exc_info)
        assert "project_key" in msg
        assert "${JIRA_PROJECT_KEY}" in msg

    def test_error_mentions_env_var_not_set(self):
        with pytest.raises(ValidationError) as exc_info:
            _make(project_key="${MY_KEY}")
        assert "env var not set" in _error_messages(exc_info)

    def test_partial_placeholder_raises(self):
        """project_key that is part real text, part placeholder."""
        with pytest.raises(ValidationError) as exc_info:
            _make(project_key="PREFIX-${JIRA_PROJECT_KEY}")
        assert "project_key" in _error_messages(exc_info)


# ---------------------------------------------------------------------------
# base_url contains placeholder
# ---------------------------------------------------------------------------


class TestPlaceholderInBaseUrl:
    def test_placeholder_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            _make(base_url=HttpUrl("https://${BASE_URL_JIRA_CLOUD}"))
        msg = _error_messages(exc_info)
        assert "base_url" in msg

    def test_error_body_contains_placeholder(self):
        # Pydantic normalises the host to lowercase before the validator runs,
        # so the placeholder appears in lowercase in the error message.
        with pytest.raises(ValidationError) as exc_info:
            _make(base_url=HttpUrl("https://${BASE_URL_JIRA_CLOUD}"))
        assert "${base_url_jira_cloud}" in _error_messages(exc_info).lower()


# ---------------------------------------------------------------------------
# token contains placeholder
# ---------------------------------------------------------------------------


class TestPlaceholderInToken:
    def test_placeholder_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            _make(token="${JIRA_TOKEN}")
        msg = _error_messages(exc_info)
        assert "token" in msg
        assert "${JIRA_TOKEN}" in msg


# ---------------------------------------------------------------------------
# email contains placeholder
# ---------------------------------------------------------------------------


class TestPlaceholderInEmail:
    def test_placeholder_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            _make(email="${JIRA_EMAIL}")
        msg = _error_messages(exc_info)
        assert "email" in msg
        assert "${JIRA_EMAIL}" in msg


# ---------------------------------------------------------------------------
# Multiple fields with placeholders at the same time
# ---------------------------------------------------------------------------


class TestMultiplePlaceholders:
    def test_all_four_fields_placeholder(self):
        """When all four fields have placeholders, all four are reported."""
        with pytest.raises(ValidationError) as exc_info:
            _make(
                project_key="${JIRA_PROJECT_KEY}",
                base_url=HttpUrl("https://${BASE_URL}"),
                token="${JIRA_TOKEN}",
                email="${JIRA_EMAIL}",
            )
        msg = _error_messages(exc_info)
        assert "project_key" in msg
        assert "token" in msg
        assert "email" in msg

    def test_two_fields_placeholder(self):
        with pytest.raises(ValidationError) as exc_info:
            _make(
                project_key="${KEY}",
                token="${TOK}",
            )
        msg = _error_messages(exc_info)
        assert "project_key" in msg
        assert "token" in msg

    def test_error_message_instructs_user(self):
        """Top-level error text must guide the user to set env vars."""
        with pytest.raises(ValidationError) as exc_info:
            _make(project_key="${KEY}")
        msg = _error_messages(exc_info)
        assert "un-substituted environment variables" in msg
        assert ".env" in msg


# ---------------------------------------------------------------------------
# Data Center (DC) deployment – placeholder validation
# ---------------------------------------------------------------------------

_BASE_DC: dict = {
    "base_url": HttpUrl("https://jira.corp.com"),
    "deployment_type": JiraDeploymentType.DATACENTER,
    "project_key": "TEST",
    "source": "test-jira-dc",
    "source_type": SourceType.JIRA,
    "token": "real-pat-token",
    "email": None,  # not required for DC
}


def _make_dc(**overrides) -> JiraProjectConfig:
    return JiraProjectConfig(**{**_BASE_DC, **overrides})


class TestDataCenterPlaceholders:
    """validate_no_placeholders behaves the same for DC deployments."""

    # ── happy paths ──────────────────────────────────────────────────────────

    def test_dc_all_real_values_accepted(self):
        """Valid DC config is accepted without error."""
        cfg = _make_dc()
        assert cfg.deployment_type == JiraDeploymentType.DATACENTER
        # email may be populated from JIRA_EMAIL env var by load_email_from_env
        # validator – the important thing is no ValidationError is raised.

    def test_dc_email_none_not_flagged(self):
        """Passing email=None must NOT raise a placeholder ValidationError.

        Note: load_email_from_env may still populate email from the JIRA_EMAIL
        env var, which is correct production behaviour.  What we assert is that
        no *placeholder* error is raised regardless.
        """
        # Should not raise a ValidationError for un-substituted placeholders
        _make_dc(email=None)  # must not raise

    # ── project_key placeholder ───────────────────────────────────────────────

    def test_dc_project_key_placeholder_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            _make_dc(project_key="${JIRA_PROJECT_KEY}")
        msg = _error_messages(exc_info)
        assert "project_key" in msg
        assert "${JIRA_PROJECT_KEY}" in msg

    # ── base_url placeholder ──────────────────────────────────────────────────

    def test_dc_base_url_placeholder_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            _make_dc(base_url=HttpUrl("https://${JIRA_DC_BASE_URL}"))
        assert "base_url" in _error_messages(exc_info)

    # ── token (PAT) placeholder ───────────────────────────────────────────────

    def test_dc_token_placeholder_raises(self):
        """PAT token placeholder must be caught for DC too."""
        with pytest.raises(ValidationError) as exc_info:
            _make_dc(token="${JIRA_PAT_TOKEN}")
        msg = _error_messages(exc_info)
        assert "token" in msg
        assert "${JIRA_PAT_TOKEN}" in msg

    # ── email explicitly set to placeholder in DC config ─────────────────────

    def test_dc_email_placeholder_still_flagged(self):
        """If someone explicitly puts ${...} in email even for DC, it must be caught."""
        with pytest.raises(ValidationError) as exc_info:
            _make_dc(email="${JIRA_EMAIL}")
        msg = _error_messages(exc_info)
        assert "email" in msg

    # ── multiple DC fields ────────────────────────────────────────────────────

    def test_dc_multiple_placeholders_all_reported(self):
        with pytest.raises(ValidationError) as exc_info:
            _make_dc(
                project_key="${JIRA_PROJECT_KEY}",
                token="${JIRA_PAT_TOKEN}",
                base_url=HttpUrl("https://${JIRA_DC_URL}"),
            )
        msg = _error_messages(exc_info)
        assert "project_key" in msg
        assert "token" in msg
        assert "base_url" in msg
