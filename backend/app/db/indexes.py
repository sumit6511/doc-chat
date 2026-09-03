"""Standard (non-vector) MongoDB indexes.

The Atlas Vector Search index on `document_chunks.embedding` is NOT created
here — Atlas Search indexes are managed separately from regular collection
indexes (via the Atlas UI, Atlas CLI, or the `createSearchIndex` command).
See README.md "MongoDB Atlas Setup" and scripts/create_vector_index.py.
"""

from __future__ import annotations

import logging

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger("docchat.db")


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    await db.documents.create_index("status")
    await db.documents.create_index("created_at")

    await db.document_chunks.create_index("document_id")

    await db.conversations.create_index("created_at")
    await db.conversations.create_index("updated_at")

    await db.messages.create_index("conversation_id")
    await db.messages.create_index("created_at")

    logger.info("mongodb_indexes_ensured")
