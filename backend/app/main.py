from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import conversations, documents, health
from app.config import get_settings
from app.db.client import mongodb
from app.db.indexes import ensure_indexes
from app.errors import register_error_handlers
from app.llm.ollama import OllamaProvider
from app.logging_config import configure_logging
from app.rag.embeddings import LocalSentenceTransformerProvider
from app.services.file_storage import LocalFileStorage

logger = logging.getLogger("docchat")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings = get_settings()

    await mongodb.connect()
    if mongodb.database is not None:
        try:
            await ensure_indexes(mongodb.database)
        except Exception:
            # Same reasoning as mongodb.connect(): don't let a down/unreachable
            # Atlas cluster at startup crash the whole app. Indexes are a
            # performance optimization, not a correctness requirement — the
            # app is still usable (and /api/health reports the outage)
            # without them.
            logger.warning("index_creation_failed_at_startup", exc_info=True)

    # Loading the embedding model is CPU-bound and can take a few seconds;
    # run it off the event loop so startup doesn't block other coroutines.
    app.state.embedding_provider = await asyncio.to_thread(
        LocalSentenceTransformerProvider, settings.embedding_model
    )
    app.state.llm_provider = OllamaProvider(
        settings.ollama_base_url, settings.ollama_model, settings.ollama_timeout_seconds
    )
    app.state.file_storage = LocalFileStorage(str(settings.storage_path_resolved))

    logger.info(
        "docchat_startup_complete embedding_dimensions=%d ollama_model=%s storage_path=%s",
        app.state.embedding_provider.dimensions,
        settings.ollama_model,
        settings.storage_path_resolved,
    )

    yield

    await mongodb.close()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="DocChat API",
        description=(
            "AI-powered document Q&A backend. Upload PDFs, retrieve grounded "
            "context via MongoDB Atlas Vector Search, and get cited answers."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)

    app.include_router(health.router, prefix="/api")
    app.include_router(documents.router, prefix="/api")
    app.include_router(conversations.router, prefix="/api")

    return app


app = create_app()
