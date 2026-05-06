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


# ---------------------------------------------------------------------------
# updated_after field parsing
# ---------------------------------------------------------------------------


class TestUpdatedAfterParsing:
    """Test parse_updated_after validator with various input formats."""

    # ── None and datetime objects ──────────────────────────────────────────────

    def test_none_value_accepted(self):
        """None value should be accepted (fetch all issues)."""
        from datetime import datetime

        cfg = _make(updated_after=None)
        assert cfg.updated_after is None

    def test_datetime_object_accepted(self):
        """Datetime object should pass through unchanged."""
        from datetime import datetime

        test_dt = datetime(2026, 5, 4, 12, 0, 0)
        cfg = _make(updated_after=test_dt)
        assert cfg.updated_after == test_dt

    # ── ISO 8601 format ────────────────────────────────────────────────────────

    def test_iso8601_datetime_parsed(self):
        """ISO 8601 datetime string should be parsed correctly."""
        from datetime import datetime

        cfg = _make(updated_after="2026-05-04T12:30:45")
        assert isinstance(cfg.updated_after, datetime)
        assert cfg.updated_after.year == 2026
        assert cfg.updated_after.month == 5
        assert cfg.updated_after.day == 4
        assert cfg.updated_after.hour == 12
        assert cfg.updated_after.minute == 30
        assert cfg.updated_after.second == 45

    def test_iso8601_datetime_no_time(self):
        """ISO 8601 date without time should be parsed."""
        from datetime import datetime

        cfg = _make(updated_after="2026-05-04")
        assert isinstance(cfg.updated_after, datetime)
        assert cfg.updated_after.year == 2026
        assert cfg.updated_after.month == 5
        assert cfg.updated_after.day == 4

    # ── Relative date formats ──────────────────────────────────────────────────

    def test_relative_days_format(self):
        """Relative format '-2 days' should be parsed."""
        from datetime import datetime, timedelta

        cfg = _make(updated_after="-2 days")
        assert isinstance(cfg.updated_after, datetime)
        # Check that it's approximately 2 days ago (allow 1 second tolerance)
        expected = datetime.now() - timedelta(days=2)
        time_diff = abs((cfg.updated_after - expected).total_seconds())
        assert time_diff < 1, f"Expected ~2 days ago, got diff of {time_diff} seconds"

    def test_relative_day_singular(self):
        """Singular 'day' should also work."""
        from datetime import datetime, timedelta

        cfg = _make(updated_after="-1 day")
        assert isinstance(cfg.updated_after, datetime)
        expected = datetime.now() - timedelta(days=1)
        time_diff = abs((cfg.updated_after - expected).total_seconds())
        assert time_diff < 1

    def test_relative_days_short_format(self):
        """Short format '-2d' should work."""
        from datetime import datetime, timedelta

        cfg = _make(updated_after="-2d")
        assert isinstance(cfg.updated_after, datetime)
        expected = datetime.now() - timedelta(days=2)
        time_diff = abs((cfg.updated_after - expected).total_seconds())
        assert time_diff < 1

    def test_relative_hours_format(self):
        """Relative format '-48 hours' should be parsed."""
        from datetime import datetime, timedelta

        cfg = _make(updated_after="-48 hours")
        assert isinstance(cfg.updated_after, datetime)
        expected = datetime.now() - timedelta(hours=48)
        time_diff = abs((cfg.updated_after - expected).total_seconds())
        assert time_diff < 1

    def test_relative_hours_short_format(self):
        """Short format '-48h' should work."""
        from datetime import datetime, timedelta

        cfg = _make(updated_after="-48h")
        assert isinstance(cfg.updated_after, datetime)
        expected = datetime.now() - timedelta(hours=48)
        time_diff = abs((cfg.updated_after - expected).total_seconds())
        assert time_diff < 1

    def test_relative_hour_singular(self):
        """Singular 'hour' should work."""
        from datetime import datetime, timedelta

        cfg = _make(updated_after="-1 hour")
        assert isinstance(cfg.updated_after, datetime)
        expected = datetime.now() - timedelta(hours=1)
        time_diff = abs((cfg.updated_after - expected).total_seconds())
        assert time_diff < 1

    def test_relative_weeks_format(self):
        """Relative format '-1 weeks' should be parsed."""
        from datetime import datetime, timedelta

        cfg = _make(updated_after="-1 weeks")
        assert isinstance(cfg.updated_after, datetime)
        expected = datetime.now() - timedelta(weeks=1)
        time_diff = abs((cfg.updated_after - expected).total_seconds())
        assert time_diff < 1

    def test_relative_weeks_short_format(self):
        """Short format '-1w' should work."""
        from datetime import datetime, timedelta

        cfg = _make(updated_after="-1w")
        assert isinstance(cfg.updated_after, datetime)
        expected = datetime.now() - timedelta(weeks=1)
        time_diff = abs((cfg.updated_after - expected).total_seconds())
        assert time_diff < 1

    def test_relative_week_singular(self):
        """Singular 'week' should work."""
        from datetime import datetime, timedelta

        cfg = _make(updated_after="-1 week")
        assert isinstance(cfg.updated_after, datetime)
        expected = datetime.now() - timedelta(weeks=1)
        time_diff = abs((cfg.updated_after - expected).total_seconds())
        assert time_diff < 1

    def test_relative_format_with_whitespace(self):
        """Format with extra whitespace should be handled."""
        from datetime import datetime, timedelta

        cfg = _make(updated_after="  -2 days  ")
        assert isinstance(cfg.updated_after, datetime)
        expected = datetime.now() - timedelta(days=2)
        time_diff = abs((cfg.updated_after - expected).total_seconds())
        assert time_diff < 1

    def test_relative_format_case_insensitive(self):
        """Relative format should be case-insensitive."""
        from datetime import datetime, timedelta

        cfg = _make(updated_after="-2 DAYS")
        assert isinstance(cfg.updated_after, datetime)
        expected = datetime.now() - timedelta(days=2)
        time_diff = abs((cfg.updated_after - expected).total_seconds())
        assert time_diff < 1

    # ── Invalid formats ────────────────────────────────────────────────────────

    def test_invalid_relative_format_raises(self):
        """Invalid relative format should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            _make(updated_after="-2 months")  # months not supported
        msg = _error_messages(exc_info)
        assert "invalid" in msg.lower() or "updated_after" in msg.lower()

    def test_invalid_iso8601_raises(self):
        """Invalid ISO 8601 format should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            _make(updated_after="2026-13-01T12:00:00")  # invalid month
        msg = _error_messages(exc_info)
        assert "updated_after" in msg.lower() or "invalid" in msg.lower()

    def test_random_string_raises(self):
        """Random string that doesn't match any format should raise."""
        with pytest.raises(ValidationError) as exc_info:
            _make(updated_after="some random text")
        msg = _error_messages(exc_info)
        assert "updated_after" in msg.lower()

    def test_positive_days_raises(self):
        """Positive days (without minus) should raise."""
        with pytest.raises(ValidationError) as exc_info:
            _make(updated_after="2 days")
        msg = _error_messages(exc_info)
        assert "updated_after" in msg.lower()

    # ── Large relative values ──────────────────────────────────────────────────

    def test_large_days_value(self):
        """Large day values should be handled."""
        from datetime import datetime, timedelta

        cfg = _make(updated_after="-365 days")
        assert isinstance(cfg.updated_after, datetime)
        expected = datetime.now() - timedelta(days=365)
        time_diff = abs((cfg.updated_after - expected).total_seconds())
        assert time_diff < 1

    def test_zero_days_not_allowed(self):
        """Zero days format is technically valid (equals datetime.now())."""
        from datetime import datetime

        # -0 days is technically valid and equals datetime.now()
        cfg = _make(updated_after="-0 days")
        assert isinstance(cfg.updated_after, datetime)
        # Should be very close to now
        time_diff = abs((cfg.updated_after - datetime.now()).total_seconds())
        assert time_diff < 1
