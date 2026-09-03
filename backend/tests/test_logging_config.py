import json
import logging
import sys

import pytest
from bson import ObjectId

from app.logging_config import JSONFormatter, TextFormatter, configure_logging, get_logger


@pytest.fixture(autouse=True)
def _reset_docchat_root_logger():
    """configure_logging() mutates the process-wide "docchat" logger, and
    several tests below call it directly — restore its handlers/level after
    each test so this file doesn't leak logging state into other tests."""
    root = logging.getLogger("docchat")
    original_handlers = root.handlers[:]
    original_level = root.level
    original_propagate = root.propagate
    yield
    root.handlers[:] = original_handlers
    root.level = original_level
    root.propagate = original_propagate


def _make_record(msg: str = "document_uploaded", **attrs) -> logging.LogRecord:
    record = logging.LogRecord(
        name="docchat.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=(),
        exc_info=None,
    )
    for key, value in attrs.items():
        setattr(record, key, value)
    return record


class TestStructuredLogger:
    def test_info_attaches_fields_to_the_record(self, caplog):
        logger = get_logger("docchat.test")
        with caplog.at_level(logging.INFO, logger="docchat.test"):
            logger.info("document_uploaded", document_id="abc123", pages=5)

        record = caplog.records[0]
        assert record.getMessage() == "document_uploaded"
        assert record.fields == {"document_id": "abc123", "pages": 5}

    def test_event_with_no_fields_sets_no_fields_attribute(self, caplog):
        logger = get_logger("docchat.test")
        with caplog.at_level(logging.INFO, logger="docchat.test"):
            logger.info("mongodb_connection_closed")

        record = caplog.records[0]
        assert getattr(record, "fields", None) is None

    def test_warning_passes_exc_info_through(self, caplog):
        logger = get_logger("docchat.test")
        with caplog.at_level(logging.WARNING, logger="docchat.test"):
            try:
                raise ValueError("boom")
            except ValueError:
                logger.warning("something_failed", exc_info=True, reason="boom")

        record = caplog.records[0]
        assert record.exc_info is not None
        assert record.fields == {"reason": "boom"}

    def test_exception_always_includes_exc_info(self, caplog):
        logger = get_logger("docchat.test")
        with caplog.at_level(logging.ERROR, logger="docchat.test"):
            try:
                raise RuntimeError("oops")
            except RuntimeError:
                logger.exception("unhandled_error", path="/api/documents")

        record = caplog.records[0]
        assert record.levelname == "ERROR"
        assert record.exc_info is not None
        assert record.fields == {"path": "/api/documents"}


class TestJSONFormatter:
    def test_fields_become_top_level_json_keys(self):
        record = _make_record(fields={"document_id": "abc123", "pages": 5})
        payload = json.loads(JSONFormatter().format(record))

        assert payload["event"] == "document_uploaded"
        assert payload["level"] == "INFO"
        assert payload["logger"] == "docchat.test"
        assert payload["document_id"] == "abc123"
        assert payload["pages"] == 5
        assert "timestamp" in payload

    def test_handles_no_fields(self):
        payload = json.loads(JSONFormatter().format(_make_record()))
        assert set(payload.keys()) == {"timestamp", "level", "logger", "event"}

    def test_includes_exception_traceback_when_present(self):
        try:
            raise ValueError("boom")
        except ValueError:
            record = _make_record(exc_info=sys.exc_info())
        payload = json.loads(JSONFormatter().format(record))
        assert "boom" in payload["exception"]

    def test_non_json_native_values_are_stringified(self):
        oid = ObjectId()
        record = _make_record(fields={"document_id": oid})
        payload = json.loads(JSONFormatter().format(record))
        assert payload["document_id"] == str(oid)


class TestTextFormatter:
    def test_appends_fields_as_key_value_suffix(self):
        record = _make_record(fields={"document_id": "abc123", "pages": 5})
        formatted = TextFormatter("%(message)s").format(record)
        assert formatted == "document_uploaded document_id=abc123 pages=5"

    def test_no_fields_means_no_suffix(self):
        formatted = TextFormatter("%(message)s").format(_make_record("mongodb_connection_closed"))
        assert formatted == "mongodb_connection_closed"


class TestConfigureLogging:
    def test_uses_json_formatter_when_configured(self):
        root = logging.getLogger("docchat")
        root.handlers.clear()

        configure_logging(level="INFO", log_format="json")

        assert len(root.handlers) == 1
        assert isinstance(root.handlers[0].formatter, JSONFormatter)

    def test_uses_text_formatter_by_default(self):
        root = logging.getLogger("docchat")
        root.handlers.clear()

        configure_logging(level="INFO", log_format="text")

        assert isinstance(root.handlers[0].formatter, TextFormatter)

    def test_does_not_add_duplicate_handlers_when_called_again(self):
        root = logging.getLogger("docchat")
        root.handlers.clear()

        configure_logging()
        configure_logging()

        assert len(root.handlers) == 1
