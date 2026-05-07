from __future__ import annotations

from openai import OpenAI

from app.core.config import settings


class OpenAIChatClient:
    """Small wrapper around OpenAI chat completions used by the agents."""

    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set. Please configure it in your .env file.")
        self._client = OpenAI(api_key=settings.openai_api_key)

    def run(self, system_prompt: str, user_prompt: str, json_response: bool = False) -> str:
        kwargs = {}
        if json_response:
            kwargs["response_format"] = {"type": "json_object"}

        response = self._client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            **kwargs,
        )
        return response.choices[0].message.content or ""
