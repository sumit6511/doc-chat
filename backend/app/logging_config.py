"""Structured logging setup.

Log statements throughout the app emit key=value pairs (document_id=...,
chunks=..., etc.) so logs stay greppable without pulling in a logging
framework. Full document text, prompts, and secrets are never logged —
only counts, ids, and status.
"""

from __future__ import annotations

import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger("docchat")
    if root.handlers:
        return  # already configured (e.g. reloader re-import)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root.addHandler(handler)
    root.setLevel(level)
    root.propagate = False
