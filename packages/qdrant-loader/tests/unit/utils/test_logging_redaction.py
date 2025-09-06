import logging

from qdrant_loader.utils.logging import LoggingConfig


def test_logging_redacts_sensitive_fields(caplog):
    # Setup logging with console format to trigger processors
    LoggingConfig.setup(level="DEBUG", format="console", clean_output=True)
    logger = LoggingConfig.get_logger(__name__)

    with caplog.at_level(logging.DEBUG):
        logger.info(
            "config_dump",
            api_key="sk-secret-abcdef012345",
            token="tok-1234567890",
            nested={"llm_api_key": "sk-deeper-abcdef012345", "other": "ok"},
        )

    # Join captured messages
    output = "\n".join(record.getMessage() for record in caplog.records)

    # Ensure raw secrets are not present
    assert "sk-secret-abcdef012345" not in output
    assert "tok-1234567890" not in output
    assert "sk-deeper-abcdef012345" not in output

    # Redacted placeholders should appear
    assert "***REDACTED***" in output


def test_stdlib_logs_are_redacted(caplog):
    # Ensure setup called
    LoggingConfig.setup(level="DEBUG", format="console", clean_output=True)
    logger = logging.getLogger("stdlib.logger")

    with caplog.at_level(logging.DEBUG):
        logger.info(
            "Sending token=%s and api_key=%s",
            "tok-SECRET-123456",
            "sk-abcdef0123456789",
        )

    out = "\n".join(record.getMessage() for record in caplog.records)
    assert "tok-SECRET-123456" not in out
    assert "sk-abcdef0123456789" not in out
    assert "***REDACTED***" in out
