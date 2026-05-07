from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ChatProvider(ABC):
    """Interface for chat/LLM providers used by the agents."""

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        json_response: bool = False,
    ) -> str:
        """Generate a text response from a system and user prompt."""
        ...


class OpenAIChatProvider(ChatProvider):
    """Chat provider backed by OpenAI or an OpenAI-compatible endpoint."""

    def __init__(self) -> None:
        from openai import OpenAI

        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set. Please configure it in your .env file.")

        kwargs = {"api_key": settings.openai_api_key}
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url

        self._client = OpenAI(**kwargs)
        self._model = settings.chat_model or settings.openai_model
        logger.info(
            "Chat provider initialized "
            f"(provider={settings.chat_provider}, model={self._model})"
        )

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        json_response: bool = False,
    ) -> str:
        kwargs = {}
        if json_response:
            kwargs["response_format"] = {"type": "json_object"}

        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            **kwargs,
        )
        return response.choices[0].message.content or ""


def get_chat_provider() -> ChatProvider:
    """Return the configured chat provider implementation."""
    provider = settings.chat_provider.lower().strip()

    if provider in {"openai", "openai-compatible"}:
        return OpenAIChatProvider()

    raise ValueError(
        f"Unsupported CHAT_PROVIDER '{settings.chat_provider}'. "
        "Supported values: openai, openai-compatible."
    )
