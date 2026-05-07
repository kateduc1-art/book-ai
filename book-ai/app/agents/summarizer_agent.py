"""
SummarizerAgent — generates structured summaries from chapter content.
Only summarizes provided content; never adds external information.
"""
from __future__ import annotations

import json
from typing import Any

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_SYSTEM_PROMPT = """Você é um especialista em síntese de conteúdo educacional.

Sua tarefa é gerar resumos estruturados de capítulos sobre educação.

Regras:
1. Resuma APENAS o conteúdo fornecido. Não adicione informações externas.
2. O resumo curto deve ter no máximo 3 frases.
3. O resumo detalhado deve cobrir os principais pontos em 1-2 parágrafos.
4. Os tópicos principais devem ser extraídos do texto, não inventados.
5. Os conceitos-chave devem ser termos ou ideias centrais presentes no texto.
6. Possíveis aplicações pedagógicas: inclua SOMENTE se o texto as mencionar ou sugerir claramente.

Responda SEMPRE no seguinte formato JSON:
{
  "summary_short": "...",
  "summary_detailed": "...",
  "key_points": ["ponto 1", "ponto 2"],
  "concepts": ["conceito 1", "conceito 2"],
  "pedagogical_applications": ["aplicação 1"]
}"""


def _parse_summary_response(raw: str) -> dict[str, Any]:
    """Extract JSON from agent response."""
    raw = raw.strip()
    if "```" in raw:
        parts = raw.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                raw = part
                break
    return json.loads(raw)


class SummarizerAgent:
    """Generates structured summaries from chapter Markdown content."""

    def __init__(self) -> None:
        self._agent = Agent(
            model=OpenAIChat(
                id=settings.openai_model,
                api_key=settings.openai_api_key,
            ),
            system_prompt=_SYSTEM_PROMPT,
            markdown=False,
        )

    def summarize(self, chapter_title: str, chapter_markdown: str) -> dict[str, Any]:
        """
        Generate a structured summary of the chapter.
        Returns a dict with summary fields.
        """
        # Truncate very long chapters to avoid token limits
        content = chapter_markdown[:12000] if len(chapter_markdown) > 12000 else chapter_markdown

        prompt = f"""Capítulo: {chapter_title}

Conteúdo:
{content}

Gere o resumo estruturado conforme as instruções."""

        try:
            response = self._agent.run(prompt)
            raw = response.content if hasattr(response, "content") else str(response)
            data = _parse_summary_response(raw)
            logger.info(f"SummarizerAgent: summarized chapter '{chapter_title}'")
            return data
        except Exception as e:
            logger.error(f"SummarizerAgent error: {e}")
            raise RuntimeError(f"Failed to summarize chapter: {e}") from e
