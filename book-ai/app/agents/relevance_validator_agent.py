"""
RelevanceValidatorAgent — decides if a text chunk is genuinely relevant to a topic.
Uses Agno with an OpenAI LLM backend.
"""
from __future__ import annotations

import json
from typing import Any

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.filter_schema import ChunkValidationResult

logger = get_logger(__name__)

_SYSTEM_PROMPT = """Você é um avaliador de relevância especializado em conteúdo educacional.

Sua tarefa é analisar se o trecho de texto fornecido contribui conceitualmente para os temas solicitados.

Regras:
- Seja rigoroso. Não marque como relevante apenas por haver palavras semelhantes.
- O trecho precisa contribuir conceitualmente para ao menos um dos temas.
- Se o trecho apenas menciona uma palavra do tema sem desenvolvê-la, marque como NÃO relevante.
- Cite a razão objetivamente em 1-2 frases.
- Responda SEMPRE no formato JSON especificado. Não adicione texto fora do JSON.

Formato de resposta:
{
  "is_relevant": true|false,
  "confidence": 0.0-1.0,
  "matched_topics": ["tema1", "tema2"],
  "reason": "Explicação objetiva."
}"""


def _build_user_prompt(topics: list[str], chunk_text: str, page: int, paragraph: int) -> str:
    return f"""Temas solicitados: {json.dumps(topics, ensure_ascii=False)}

Localização: Página {page}, Parágrafo {paragraph}

Trecho:
\"\"\"
{chunk_text}
\"\"\"

Avalie se este trecho é genuinamente relevante para os temas acima."""


def _parse_response(raw: str) -> dict[str, Any]:
    """Extract JSON from agent response, handling markdown code blocks."""
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


class RelevanceValidatorAgent:
    """Validates whether a text chunk is relevant to given topics."""

    def __init__(self) -> None:
        self._agent = Agent(
            model=OpenAIChat(
                id=settings.openai_model,
                api_key=settings.openai_api_key,
            ),
            system_prompt=_SYSTEM_PROMPT,
            markdown=False,
        )

    def validate(
        self,
        chunk_id: str,
        chunk_text: str,
        topics: list[str],
        page: int,
        paragraph: int,
    ) -> ChunkValidationResult:
        """Validate a single chunk against the given topics."""
        prompt = _build_user_prompt(topics, chunk_text, page, paragraph)

        try:
            response = self._agent.run(prompt)
            raw = response.content if hasattr(response, "content") else str(response)
            data = _parse_response(raw)

            return ChunkValidationResult(
                chunk_id=chunk_id,
                is_relevant=bool(data.get("is_relevant", False)),
                confidence=float(data.get("confidence", 0.0)),
                matched_topics=list(data.get("matched_topics", [])),
                reason=str(data.get("reason", "")),
            )

        except Exception as e:
            logger.error(f"RelevanceValidatorAgent error for chunk {chunk_id}: {e}")
            return ChunkValidationResult(
                chunk_id=chunk_id,
                is_relevant=False,
                confidence=0.0,
                matched_topics=[],
                reason=f"Erro na validação: {e}",
            )

    def validate_batch(
        self,
        chunks: list[dict],  # [{chunk_id, text, page, paragraph}]
        topics: list[str],
    ) -> list[ChunkValidationResult]:
        """Validate multiple chunks sequentially."""
        results = []
        for item in chunks:
            result = self.validate(
                chunk_id=item["chunk_id"],
                chunk_text=item["text"],
                topics=topics,
                page=item["page"],
                paragraph=item["paragraph"],
            )
            results.append(result)
            logger.debug(
                f"Chunk {item['chunk_id']}: relevant={result.is_relevant} "
                f"confidence={result.confidence:.2f}"
            )
        return results
