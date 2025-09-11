import logging
from importlib import import_module


def test_redaction_filter_masks_and_marks(caplog):
    caplog.set_level(logging.INFO)

    logging_mod = import_module("qdrant_loader_core.logging")
    RedactionFilter = logging_mod.RedactionFilter

    # Keep root handlers to restore after test to avoid side-effects
    root = logging.getLogger()
    prev_handlers = list(root.handlers)

    # Create a custom handler that captures messages after redaction
    captured_messages = []

    class TestHandler(logging.Handler):
        def emit(self, record):
            # Format the record to get the final message
            msg = self.format(record)
            captured_messages.append(msg)

    try:
        # Clear existing handlers and add our test handler with redaction filter
        for h in list(root.handlers):
            root.removeHandler(h)

        test_handler = TestHandler()
        test_handler.setLevel(logging.INFO)
        test_handler.addFilter(RedactionFilter())
        root.addHandler(test_handler)
        root.setLevel(logging.INFO)

        logger = logging.getLogger("redaction-test")

        # Message with obvious token in the raw string (no placeholders)
        logger.info("api_key=sk-ABCDEFGHIJKLMN")
        # Message with placeholder + token in args (ensures args are redacted safely)
        logger.info("arg test %s", "sk-ABCDEFGH")

        # Redaction marker should appear at least once
        assert any(
            "***REDACTED***" in m for m in captured_messages
        ), f"Messages: {captured_messages}"
        # Original secrets should not appear
        assert all(
            "sk-ABCDEFGHIJKLMN" not in m for m in captured_messages
        ), f"Messages: {captured_messages}"
        # Mask should keep first/last 2 chars for long secrets.
        # Depending on exact pattern matched, the visible context may be key or value.
        assert any(
            ("sk***REDACTED***MN" in m) or ("ap***REDACTED***MN" in m)
            for m in captured_messages
        ), f"Messages: {captured_messages}"
    finally:
        # Restore handlers
        for h in list(root.handlers):
            root.removeHandler(h)
        for h in prev_handlers:
            root.addHandler(h)


def test_clean_formatter_strips_ansi(tmp_path):
    logging_mod = import_module("qdrant_loader_core.logging")
    CleanFormatter = logging_mod.CleanFormatter

    path = tmp_path / "ansi.log"

    handler = logging.FileHandler(path)
    handler.setFormatter(CleanFormatter("%(message)s"))

    logger = logging.getLogger("ansi-test")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.addHandler(handler)

    try:
        logger.info("\x1b[31mred text\x1b[0m")
        handler.flush()
    finally:
        logger.removeHandler(handler)
        handler.close()

    content = path.read_text()
    assert "\x1b[" not in content
    assert "red text" in content


def test_redact_processor_masks_nested_fields():
    logging_mod = import_module("qdrant_loader_core.logging")
    redact = logging_mod._redact_processor

    event = {
        "api_key": "sk-ABCDEFGHIJKLMNOP",
        "nested": {
            "token": "abcd1234",  # short token -> fully redacted
            "list": [{"password": "supersecret"}, {"ok": "fine"}],
        },
        "note": "keep",
    }

    out = redact(None, "info", event)

    # Top-level sensitive key masked with visible marker in the value
    assert isinstance(out["api_key"], str) and "***REDACTED***" in out["api_key"]
    # Nested sensitive keys redacted/masked
    assert out["nested"]["token"] == "***REDACTED***"
    assert "***REDACTED***" in out["nested"]["list"][0]["password"]
    # Non-sensitive content preserved
    assert out["note"] == "keep"
