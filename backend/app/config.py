"""Central application configuration, loaded once from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # MongoDB Atlas
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "docchat"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_timeout_seconds: float = 120.0

    # Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"

    # RAG
    top_k: int = 5
    num_candidates: int = 50
    min_relevance_score: float = 0.50
    chunk_size: int = 800
    chunk_overlap: int = 100
    max_history_messages: int = 10
    vector_index_name: str = "vector_index"
    debug_rag: bool = False

    # Uploads
    max_file_size_mb: int = 20
    storage_path: str = "./storage/documents"

    # CORS
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
