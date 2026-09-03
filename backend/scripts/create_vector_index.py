"""Creates the Atlas Vector Search index on `document_chunks` programmatically.

This is an alternative to creating the index by hand in the Atlas UI (see
README.md "MongoDB Atlas Setup" for the UI walkthrough and the equivalent
JSON definition). Requires an Atlas cluster (M10+, or a free/shared tier that
supports Search) — Atlas Search indexes cannot be created against a
self-hosted `mongod`.

Usage:
    cd backend
    python -m scripts.create_vector_index

Reads MONGODB_URI / MONGODB_DATABASE / VECTOR_INDEX_NAME from the same .env
the API server uses, and derives the vector dimensions from EMBEDDING_MODEL
so the index always matches what the app actually generates.
"""

from __future__ import annotations

import sys
import time

from pymongo import MongoClient
from pymongo.operations import SearchIndexModel

from app.config import get_settings


def _embedding_dimensions(model_name: str) -> int:
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name).get_sentence_embedding_dimension()


def main() -> None:
    settings = get_settings()
    dimensions = _embedding_dimensions(settings.embedding_model)

    client = MongoClient(settings.mongodb_uri)
    collection = client[settings.mongodb_database]["document_chunks"]

    existing = {idx["name"] for idx in collection.list_search_indexes()}
    if settings.vector_index_name in existing:
        print(f"Index '{settings.vector_index_name}' already exists — nothing to do.")
        return

    index_model = SearchIndexModel(
        name=settings.vector_index_name,
        type="vectorSearch",
        definition={
            "fields": [
                {
                    "type": "vector",
                    "path": "embedding",
                    "numDimensions": dimensions,
                    "similarity": "cosine",
                },
                {"type": "filter", "path": "document_id"},
            ]
        },
    )

    print(
        f"Creating Atlas Vector Search index '{settings.vector_index_name}' "
        f"({dimensions} dimensions, cosine similarity) on document_chunks..."
    )
    collection.create_search_index(index_model)

    print("Waiting for the index to become queryable (this can take a minute)...")
    for _ in range(60):
        indexes = list(collection.list_search_indexes(settings.vector_index_name))
        if indexes and indexes[0].get("queryable"):
            print("Index is ready.")
            return
        time.sleep(5)

    print(
        "Index was created but is not queryable yet. Check its status in the "
        "Atlas UI under Atlas Search.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
