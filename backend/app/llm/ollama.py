from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from app.errors import LLMTimeoutError, LLMUnavailableError
from app.llm.base import LLMProvider
from app.logging_config import get_logger

logger = get_logger("docchat.llm")


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str, model: str, timeout_seconds: float = 120.0):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout_seconds

    async def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        logger.info("llm_request_started", model=self._model)
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
            logger.error("llm_request_timeout", model=self._model)
            raise LLMTimeoutError("The AI service took too long to respond.") from exc
        except httpx.HTTPError as exc:
            logger.error("llm_request_failed", model=self._model, error=str(exc))
            raise LLMUnavailableError(
                "The AI service is currently unavailable. Make sure Ollama is "
                "running and the configured model is installed."
            ) from exc

        content = (data.get("message") or {}).get("content", "").strip()
        if not content:
            raise LLMUnavailableError("The AI service returned an empty response.")

        logger.info("llm_request_completed", model=self._model, response_chars=len(content))
        return content

    async def generate_stream(self, *, system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
        logger.info("llm_stream_request_started", model=self._model)
        chars = 0
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/api/chat",
                    json={
                        "model": self._model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "stream": True,
                    },
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        chunk = json.loads(line)
                        content = (chunk.get("message") or {}).get("content", "")
                        if content:
                            chars += len(content)
                            yield content
                        if chunk.get("done"):
                            break
        except httpx.TimeoutException as exc:
            logger.error("llm_stream_request_timeout", model=self._model)
            raise LLMTimeoutError("The AI service took too long to respond.") from exc
        except httpx.HTTPError as exc:
            logger.error("llm_stream_request_failed", model=self._model, error=str(exc))
            raise LLMUnavailableError(
                "The AI service is currently unavailable. Make sure Ollama is "
                "running and the configured model is installed."
            ) from exc

        if chars == 0:
            raise LLMUnavailableError("The AI service returned an empty response.")

        logger.info("llm_stream_request_completed", model=self._model, response_chars=chars)

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                return response.status_code == 200
        except httpx.HTTPError:
            return False
