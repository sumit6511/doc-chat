"""Single application-wide MongoDB client with an explicit connect/close lifecycle.

FastAPI's lifespan hook (see app/main.py) calls `connect()` once at startup and
`close()` once at shutdown. Nothing in the request path creates a new client —
routes and repositories reuse the same `AsyncIOMotorClient`/connection pool.
"""

from __future__ import annotations

import asyncio

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import PyMongoError

from app.config import get_settings
from app.errors import DatabaseUnavailableError
from app.logging_config import get_logger

logger = get_logger("docchat.db")

# A container's network/DNS can be momentarily unsettled right as it starts
# (observed in practice: Docker's embedded DNS resolver returning SERVFAIL
# for the mongodb+srv:// SRV lookup on the very first attempt, succeeding
# immediately on the next). A few quick retries absorb that without needing
# a full container restart; a longer-lived Atlas outage still degrades
# gracefully afterward rather than crashing (see the except block below) —
# just without further automatic retries once startup finishes.
_CONNECT_MAX_ATTEMPTS = 3
_CONNECT_RETRY_DELAY_SECONDS = 2.0


class MongoDB:
    client: AsyncIOMotorClient | None = None
    database: AsyncIOMotorDatabase | None = None

    async def connect(self) -> None:
        settings = get_settings()
        for attempt in range(1, _CONNECT_MAX_ATTEMPTS + 1):
            try:
                # For mongodb+srv:// URIs (what every Atlas connection string
                # uses), pymongo resolves the DNS SRV record synchronously
                # *during construction* — a bad host, not-yet-configured
                # MONGODB_URI, or transient DNS/network hiccup can raise
                # right here, not just from the ping below. Both failure
                # points must stay inside this try, or a bad URI crashes
                # startup entirely.
                self.client = AsyncIOMotorClient(
                    settings.mongodb_uri,
                    serverSelectionTimeoutMS=8000,
                    connectTimeoutMS=8000,
                )
                self.database = self.client[settings.mongodb_database]
                await self.client.admin.command("ping")
                logger.info(
                    "mongodb_connected",
                    database=settings.mongodb_database,
                    attempt=attempt,
                    max_attempts=_CONNECT_MAX_ATTEMPTS,
                )
                return
            except PyMongoError:
                self.client = None
                self.database = None
                if attempt < _CONNECT_MAX_ATTEMPTS:
                    logger.warning(
                        "mongodb_connect_attempt_failed",
                        exc_info=True,
                        attempt=attempt,
                        max_attempts=_CONNECT_MAX_ATTEMPTS,
                        retrying_in_seconds=_CONNECT_RETRY_DELAY_SECONDS,
                    )
                    await asyncio.sleep(_CONNECT_RETRY_DELAY_SECONDS)
                else:
                    # Deliberately not re-raised: an unreachable/misconfigured
                    # Atlas cluster should degrade the app, not crash it.
                    # GET /api/health reports "database": "unavailable" until
                    # this succeeds; requests that need the database in the
                    # meantime get a clean 503 DATABASE_UNAVAILABLE (see
                    # get_database() below and errors.py's PyMongoError
                    # handler for outages that develop after a successful
                    # startup) instead of a hard crash.
                    logger.warning("mongodb_connect_failed_at_startup", exc_info=True)

    async def close(self) -> None:
        if self.client is not None:
            self.client.close()
            logger.info("mongodb_connection_closed")


mongodb = MongoDB()


def get_database() -> AsyncIOMotorDatabase:
    """FastAPI dependency for normal request handling.

    Raises a clean 503 DATABASE_UNAVAILABLE if startup's connect() never
    succeeded, instead of handing repositories a None database to crash on.
    """
    if mongodb.database is None:
        raise DatabaseUnavailableError(
            "The database is currently unavailable. Please try again shortly."
        )
    return mongodb.database


def get_database_or_none() -> AsyncIOMotorDatabase | None:
    """Lenient accessor for the health check specifically.

    Health must report connectivity state even when Mongo was never
    successfully connected — get_database()'s raise-on-None behavior is
    correct for normal endpoints but wrong for a health probe.
    """
    return mongodb.database
