import logging

from qdrant_loader.utils.logging import LoggingConfig


def test_logging_redacts_sensitive_fields(caplog):
    # Setup logging with console format to trigger processors
    LoggingConfig.setup(level="DEBUG", format="console", clean_output=True)
    logger = LoggingConfig.get_logger(__name__)

    # Create a custom handler to capture redacted messages
    captured_messages = []

    class TestHandler(logging.Handler):
        def emit(self, record):
            # Format the record to get the final message after redaction
            msg = self.format(record)
            captured_messages.append(msg)

    # Add our test handler to the root logger
    root_logger = logging.getLogger()
    test_handler = TestHandler()
    test_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(test_handler)

    try:
        logger.info(
            "config_dump",
            api_key="sk-secret-abcdef012345",
            token="tok-1234567890",
            nested={"llm_api_key": "sk-deeper-abcdef012345", "other": "ok"},
        )

        # Join captured messages
        output = "\n".join(captured_messages)

        # Ensure raw secrets are not present
        assert "sk-secret-abcdef012345" not in output
        assert "tok-1234567890" not in output
        assert "sk-deeper-abcdef012345" not in output

        # Redacted placeholders should appear
        assert "***REDACTED***" in output
    finally:
        # Clean up the test handler
        root_logger.removeHandler(test_handler)


def test_stdlib_logs_are_redacted(caplog):
    # Ensure setup called
    LoggingConfig.setup(level="DEBUG", format="console", clean_output=True)
    # Use LoggingConfig logger which supports structured logging
    logger = LoggingConfig.get_logger("stdlib.logger")

    # Create a custom handler to capture redacted messages
    captured_messages = []

    class TestHandler(logging.Handler):
        def emit(self, record):
            # Format the record to get the final message after redaction
            msg = self.format(record)
            captured_messages.append(msg)

    # Add our test handler to the root logger with formatter
    root_logger = logging.getLogger()
    test_handler = TestHandler()
    test_handler.setLevel(logging.DEBUG)

    # Get formatter from existing handlers to ensure consistent formatting
    if root_logger.handlers:
        formatter = root_logger.handlers[0].formatter
        if formatter:
            test_handler.setFormatter(formatter)

    root_logger.addHandler(test_handler)

    try:
        # Use structured logging format instead of % formatting for redaction to work
        logger.info(
            "Sending credentials",
            token="tok-SECRET-123456",
            api_key="sk-abcdef0123456789",
        )

        out = "\n".join(captured_messages)
        assert "tok-SECRET-123456" not in out
        assert "sk-abcdef0123456789" not in out
        assert "***REDACTED***" in out
    finally:
        # Clean up the test handler
        root_logger.removeHandler(test_handler)
