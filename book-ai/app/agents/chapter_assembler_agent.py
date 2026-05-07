"""
ChapterAssemblerAgent — assembles a structured chapter from validated text chunks.
Does NOT invent content. Uses only the provided excerpts.
"""
from __future__ import annotations

import json

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_SYSTEM_PROMPT = """Você é um editor especializado em montagem de capítulos a partir de trechos de livros.

Regras absolutas:
1. Use APENAS os trechos fornecidos. Não invente nenhum conteúdo.
2. Organize os trechos em seções temáticas coerentes.
3. Crie transições curtas entre os trechos (1-2 frases no máximo).
4. Preserve SEMPRE as referências de página no formato: *[p. X]*.
5. Se algo não estiver claro nos trechos, não complete com suposições.
6. O resultado deve ser em Markdown.
7. Estrutura obrigatória: ## Introdução → seções temáticas → ## Considerações Finais

Formato de saída: Markdown puro, sem explicações adicionais."""


def _format_chunks_for_prompt(chunks: list[dict]) -> str:
    """Format chunk data into a structured prompt section."""
    lines = ["TRECHOS VALIDADOS:"]
    for i, chunk in enumerate(chunks, 1):
        lines.append(
            f"\n[Trecho {i}] Página {chunk['page']}, Parágrafo {chunk['paragraph']}:"
        )
        lines.append(chunk["text"])
    return "\n".join(lines)


class ChapterAssemblerAgent:
    """Assembles a Markdown chapter from validated text chunks."""

    def __init__(self) -> None:
        self._agent = Agent(
            model=OpenAIChat(
                id=settings.openai_model,
                api_key=settings.openai_api_key,
            ),
            system_prompt=_SYSTEM_PROMPT,
            markdown=True,
        )

    def assemble(
        self,
        title: str,
        topics: list[str],
        chunks: list[dict],  # [{page, paragraph, text}]
    ) -> str:
        """
        Assemble a structured Markdown chapter.
        Returns the Markdown string.
        """
        topics_str = ", ".join(topics)
        chunks_str = _format_chunks_for_prompt(chunks)

        prompt = f"""Monte um capítulo intitulado "{title}" sobre os temas: {topics_str}.

{chunks_str}

Instruções:
- Use apenas os trechos acima.
- Organize em seções temáticas.
- Preserve as referências de página.
- Não invente informações."""

        try:
            response = self._agent.run(prompt)
            content = response.content if hasattr(response, "content") else str(response)
            logger.info(f"ChapterAssemblerAgent: assembled chapter '{title}'")
            return content
        except Exception as e:
            logger.error(f"ChapterAssemblerAgent error: {e}")
            raise RuntimeError(f"Failed to assemble chapter: {e}") from e
