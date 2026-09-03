from __future__ import annotations

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import PyMongoError

from app.api.deps import get_llm_provider
from app.config import Settings, get_settings
from app.db.client import get_database_or_none
from app.llm.base import LLMProvider
from app.logging_config import get_logger

logger = get_logger("docchat.health")

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(
    db: AsyncIOMotorDatabase | None = Depends(get_database_or_none),
    llm_provider: LLMProvider = Depends(get_llm_provider),
    settings: Settings = Depends(get_settings),
) -> dict:
    # Uses the lenient get_database_or_none (unlike every other route, which
    # uses the strict get_database) precisely so an unconnected database
    # reports "unavailable" here instead of the whole endpoint 503ing.
    database_ok = False
    if db is not None:
        try:
            await db.command("ping")
            database_ok = True
        except PyMongoError:
            logger.warning("database_health_check_failed", exc_info=True)

    vector_search_status = "unknown"
    if database_ok:
        try:
            indexes = [
                idx
                async for idx in db.document_chunks.list_search_indexes(settings.vector_index_name)
            ]
            queryable = any(idx.get("queryable") for idx in indexes)
            vector_search_status = "ok" if queryable else "not_configured"
        except Exception:
            logger.warning("vector_search_health_check_failed", exc_info=True)
            vector_search_status = "unavailable"

    llm_ok = await llm_provider.is_available() if hasattr(llm_provider, "is_available") else False

    overall = "ok" if database_ok and vector_search_status == "ok" and llm_ok else "degraded"

    return {
        "status": overall,
        "database": "ok" if database_ok else "unavailable",
        "vector_search": vector_search_status,
        "llm": "ok" if llm_ok else "unavailable",
    }
