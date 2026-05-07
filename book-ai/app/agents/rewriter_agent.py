"""
RewriterAgent — rewrites chapter content in a more fluid, didactic style.
Maintains fidelity to source material; does NOT invent data or examples.
"""
from __future__ import annotations

import json
from typing import Any

from app.agents.openai_chat_client import OpenAIChatClient
from app.core.logging import get_logger

logger = get_logger(__name__)

_SYSTEM_PROMPT = """Você é um editor especializado em reescrita de textos educacionais.

Sua tarefa é melhorar a qualidade de escrita de um capítulo preservando fidelidade ao conteúdo.

Regras absolutas:
1. NÃO invente exemplos, autores, dados, pesquisas ou referências.
2. Mantenha TODAS as informações presentes no original.
3. Não apague conceitos, termos técnicos ou ideias importantes.
4. Preserve as referências de página no formato *[p. X]*.
5. Melhore a fluidez, a conexão entre parágrafos e a clareza.
6. Organize o texto em seções bem definidas com títulos em Markdown.
7. Use linguagem clara, direta e adequada ao público-alvo.
8. Não inclua opiniões pessoais ou julgamentos de valor não presentes no original.

Responda com o texto reescrito em Markdown. Não adicione comentários fora do texto."""


class RewriterAgent:
    """Rewrites chapter content in a more readable and didactic style."""

    def __init__(self) -> None:
        self._client = OpenAIChatClient()

    def rewrite(
        self,
        chapter_title: str,
        chapter_markdown: str,
        style: str = "didático, claro, profissional e agradável",
        audience: str = "professores e gestores educacionais",
        sources: list[dict] | None = None,
    ) -> tuple[str, list[dict]]:
        """
        Rewrite the chapter in a better style.
        Returns (rewritten_markdown, source_map).
        """
        sources_note = ""
        if sources:
            source_list = ", ".join(
                f"p.{s['page']}" for s in sorted(sources, key=lambda x: x["page"])
            )
            sources_note = f"\n\nFontes originais (PRESERVAR referências): {source_list}"

        # Truncate to avoid token limits
        content = (
            chapter_markdown[:14000]
            if len(chapter_markdown) > 14000
            else chapter_markdown
        )

        prompt = f"""Reescreva o capítulo abaixo.

Título: {chapter_title}
Estilo desejado: {style}
Público-alvo: {audience}
{sources_note}

Conteúdo original:
{content}

Reescreva mantendo fidelidade total ao conteúdo, melhorando clareza e fluidez."""

        try:
            rewritten = self._client.run(_SYSTEM_PROMPT, prompt)

            # Build a simple source_map from the sources list
            source_map = self._build_source_map(sources or [], rewritten)

            logger.info(f"RewriterAgent: rewrote chapter '{chapter_title}'")
            return rewritten, source_map

        except Exception as e:
            logger.error(f"RewriterAgent error: {e}")
            raise RuntimeError(f"Failed to rewrite chapter: {e}") from e

    def _build_source_map(
        self, sources: list[dict], rewritten_text: str
    ) -> list[dict]:
        """
        Build a paragraph → pages mapping from source list.
        Simple heuristic: group paragraphs by index and map all source pages.
        """
        if not sources:
            return []

        pages = sorted({s["page"] for s in sources})
        paragraphs = [
            p.strip()
            for p in rewritten_text.split("\n\n")
            if p.strip() and not p.strip().startswith("#")
        ]

        source_map = []
        # Distribute pages evenly across paragraphs
        pages_per_para = max(1, len(pages) // max(1, len(paragraphs)))
        for i, _ in enumerate(paragraphs):
            start = i * pages_per_para
            assigned_pages = pages[start : start + pages_per_para]
            if assigned_pages:
                source_map.append({"paragraph": i + 1, "based_on_pages": assigned_pages})

        return source_map
