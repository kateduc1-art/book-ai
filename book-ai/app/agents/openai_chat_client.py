from __future__ import annotations

from app.agents.chat_provider import get_chat_provider


class OpenAIChatClient:
    """Backward-compatible wrapper around the configured chat provider."""

    def __init__(self) -> None:
        self._provider = get_chat_provider()

    def run(self, system_prompt: str, user_prompt: str, json_response: bool = False) -> str:
        return self._provider.generate(system_prompt, user_prompt, json_response)
