"""File storage abstraction.

`LocalFileStorage` is a fine default for local development and demos, but a
local disk is not durable, shared, or scalable — it disappears if the
container is recreated. Production deployments should implement
`FileStorage` with an object-storage backend (S3, R2, GCS, Azure Blob) behind
the same three methods; nothing else in the app would need to change.
"""

from __future__ import annotations

import re
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

# Path separators and control characters only. This is deliberately much
# looser than a filesystem-safe charset: sanitize_display_filename() below is
# never used as an actual path (generate_storage_filename() below produces
# that, a random UUID), only stored as a string and shown in the UI/citations
# — so ordinary filenames like "Distributed Systems.pdf" or "Q&A (final).pdf"
# should survive unchanged.
_PATH_UNSAFE_CHARS_RE = re.compile(r"[\\/\x00-\x1f]+")


def generate_storage_filename(original_filename: str) -> str:
    """A random, filesystem-safe name — the original filename is never trusted as a path."""
    suffix = Path(original_filename).suffix.lower()
    if suffix != ".pdf":
        suffix = ".pdf"
    return f"{uuid.uuid4().hex}{suffix}"


def sanitize_display_filename(original_filename: str) -> str:
    """A safe filename for display/metadata — strips path components and control characters."""
    name = Path(original_filename).name
    name = _PATH_UNSAFE_CHARS_RE.sub("_", name).strip()
    return name[:255] or "document.pdf"


class FileStorage(ABC):
    @abstractmethod
    async def save(self, storage_filename: str, content: bytes) -> str:
        """Persists `content` and returns a storage path/key."""

    @abstractmethod
    async def get(self, storage_path: str) -> bytes:
        """Reads back previously saved content."""

    @abstractmethod
    async def delete(self, storage_path: str) -> None:
        """Removes stored content. Safe to call on an already-missing file."""


class LocalFileStorage(FileStorage):
    def __init__(self, base_path: str):
        self._base_path = Path(base_path)
        self._base_path.mkdir(parents=True, exist_ok=True)

    def _resolve(self, storage_filename: str) -> Path:
        # storage_filename is always our own generated uuid-based name, but we
        # still resolve-and-verify to make path traversal impossible even if
        # that assumption is ever violated.
        candidate = (self._base_path / storage_filename).resolve()
        if self._base_path.resolve() not in candidate.parents and candidate != self._base_path.resolve():
            raise ValueError("Resolved path escapes storage directory")
        return candidate

    async def save(self, storage_filename: str, content: bytes) -> str:
        path = self._resolve(storage_filename)
        path.write_bytes(content)
        return str(path)

    async def get(self, storage_path: str) -> bytes:
        return Path(storage_path).read_bytes()

    async def delete(self, storage_path: str) -> None:
        path = Path(storage_path)
        path.unlink(missing_ok=True)
