"""LLM provider abstraction.

`ChatService`/`RAGPipeline` depend only on this interface, never on a
specific vendor SDK. Adding OpenAI/Anthropic/Gemini later means writing one
new class here — retrieval, prompting, and the API layer are unaffected.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        """Returns the model's full text response for a single-turn completion."""
