"""LLM provider abstraction.

`ChatService`/`RAGPipeline` depend only on this interface, never on a
specific vendor SDK. Adding OpenAI/Anthropic/Gemini later means writing one
new class here — retrieval, prompting, and the API layer are unaffected.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        """Returns the model's full text response for a single-turn completion."""

    @abstractmethod
    def generate_stream(self, *, system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
        """Yields the response incrementally as it's generated. Concatenating
        every yielded piece equals what generate() would return for the same
        prompt."""
