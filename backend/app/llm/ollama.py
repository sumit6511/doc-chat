from __future__ import annotations

import logging

import httpx

from app.errors import LLMTimeoutError, LLMUnavailableError
from app.llm.base import LLMProvider

logger = logging.getLogger("docchat.llm")


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str, model: str, timeout_seconds: float = 120.0):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout_seconds

    async def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        logger.info("llm_request_started model=%s", self._model)
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/api/chat",
                    json={
                        "model": self._model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "stream": False,
                    },
                )
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            logger.error("llm_request_timeout model=%s", self._model)
            raise LLMTimeoutError("The AI service took too long to respond.") from exc
        except httpx.HTTPError as exc:
            logger.error("llm_request_failed model=%s error=%s", self._model, exc)
            raise LLMUnavailableError(
                "The AI service is currently unavailable. Make sure Ollama is "
                "running and the configured model is installed."
            ) from exc

        content = (data.get("message") or {}).get("content", "").strip()
        if not content:
            raise LLMUnavailableError("The AI service returned an empty response.")

        logger.info("llm_request_completed model=%s response_chars=%d", self._model, len(content))
        return content

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                return response.status_code == 200
        except httpx.HTTPError:
            return False
