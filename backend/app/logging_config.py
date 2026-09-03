"""Structured logging.

Every log call takes an event name plus keyword fields —
`logger.info("document_uploaded", document_id=..., pages=...)` — instead of
a free-text message with key=value pairs baked into the string. That
distinction is what makes LOG_FORMAT=json actually structured: each field
becomes its own top-level JSON key, directly queryable in a log aggregator
(CloudWatch Logs Insights, Datadog, Loki, ...), rather than a JSON envelope
wrapped around a text blob a downstream processor still has to regex apart.

LOG_FORMAT=text (the default, for local development) renders the same
fields as human-readable key=value suffixes instead.

Full document text, prompts, and secrets are never logged — only counts,
ids, and status.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

_ROOT_LOGGER_NAME = "docchat"


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        fields = getattr(record, "fields", None)
        if fields:
            payload.update(fields)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class TextFormatter(logging.Formatter):
    """Human-readable format for local development."""

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        fields = getattr(record, "fields", None)
        if fields:
            suffix = " ".join(f"{key}={value}" for key, value in fields.items())
            base = f"{base} {suffix}"
        return base


class StructuredLogger:
    """Thin wrapper around the stdlib logger.

    `logger.info("event_name", field=value, ...)` instead of %-style
    placeholders embedded in a free-text message. Fields are passed via
    `extra={"fields": {...}}` (nested under one key, not spread directly
    into `extra`) specifically to avoid `extra` colliding with LogRecord's
    own reserved attribute names (`message`, `asctime`, ...), which raises
    if you pass them directly.
    """

    def __init__(self, name: str):
        self._logger = logging.getLogger(name)

    def _log(self, level: int, event: str, exc_info: bool = False, **fields: Any) -> None:
        self._logger.log(level, event, exc_info=exc_info, extra={"fields": fields} if fields else None)

    def debug(self, event: str, **fields: Any) -> None:
        self._log(logging.DEBUG, event, **fields)

    def info(self, event: str, **fields: Any) -> None:
        self._log(logging.INFO, event, **fields)

    def warning(self, event: str, exc_info: bool = False, **fields: Any) -> None:
        self._log(logging.WARNING, event, exc_info=exc_info, **fields)

    def error(self, event: str, exc_info: bool = False, **fields: Any) -> None:
        self._log(logging.ERROR, event, exc_info=exc_info, **fields)

    def exception(self, event: str, **fields: Any) -> None:
        self._log(logging.ERROR, event, exc_info=True, **fields)


def configure_logging(level: str = "INFO", log_format: str = "text") -> None:
    root = logging.getLogger(_ROOT_LOGGER_NAME)
    if root.handlers:
        return  # already configured (e.g. reloader re-import)

    handler = logging.StreamHandler(sys.stdout)
    if log_format == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(TextFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root.addHandler(handler)
    root.setLevel(level)
    root.propagate = False


def get_logger(name: str) -> StructuredLogger:
    return StructuredLogger(name)
