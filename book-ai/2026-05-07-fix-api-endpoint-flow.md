# 2026-05-07 - fix: stabilize API endpoint flow

## Commit sugerido

```text
fix: stabilize API endpoint flow
```

## Contexto

Durante o teste ponta a ponta dos endpoints com o PDF `Refatorando com padrões de projeto_ Um guia em Java.pdf`, alguns pontos impediam o fluxo completo da API:

- `POST /documents/upload` falhava com erro de relationship do SQLAlchemy.
- `POST /documents/{document_id}/filter` falhava ao montar a consulta pgvector.
- Jobs de validação, resumo e reescrita dependiam do adapter `agno.models.openai.OpenAIChat`, que quebrou por incompatibilidade com a versão instalada do SDK OpenAI.
- As mensagens dos jobs de capítulo apontavam para uma rota global `/jobs/{job_id}` que não existe na API.

## Alterações feitas

### Inicialização dos modelos SQLAlchemy

Arquivos:

- `app/models/__init__.py`
- `app/core/database.py`

Mudanças:

- `app/models/__init__.py` agora importa explicitamente `Chapter`, `Chunk`, `Document` e `Job`.
- `init_db()` importa `app.models` antes de `Base.metadata.create_all()`.

Motivo:

- Garante que o registry do SQLAlchemy conheça todas as classes antes de resolver relationships como `Document.chunks`, `Document.chapters` e `Document.jobs`.

### Busca vetorial com pgvector

Arquivo:

- `app/services/vector_store.py`

Mudanças:

- Substituído o uso manual de `cast(query_vector, Vector(...))` e operador `<=>`.
- A busca agora usa `Chunk.embedding.cosine_distance(query_vector)`.
- Removidos imports não usados (`numpy`, `Vector`, `func`, `cast`).

Motivo:

- O bind manual do vetor chegava ao driver em formato inválido e causava `ValueError: expected ndim to be 1`.
- O helper `cosine_distance()` do `pgvector.sqlalchemy` serializa o vetor corretamente.

### Agentes usando OpenAI SDK direto

Arquivos:

- `app/agents/openai_chat_client.py`
- `app/agents/relevance_validator_agent.py`
- `app/agents/summarizer_agent.py`
- `app/agents/rewriter_agent.py`

Mudanças:

- Criado `OpenAIChatClient`, um wrapper pequeno para `client.chat.completions.create(...)`.
- `RelevanceValidatorAgent`, `SummarizerAgent` e `RewriterAgent` passaram a usar esse wrapper.
- Validação e resumo usam `response_format={"type": "json_object"}`.
- Reescrita retorna Markdown livre.

Motivo:

- O adapter `agno.models.openai.OpenAIChat` importava tipos indisponíveis no pacote `openai==1.51.0`, causando falha em background tasks.
- O SDK oficial da OpenAI já estava instalado e funcionando para embeddings, então a troca reduziu uma dependência instável no caminho crítico da API.

### Mensagens de polling dos jobs de capítulo

Arquivo:

- `app/api/routes/chapters.py`

Mudanças:

- As respostas de `POST /chapters/{chapter_id}/summarize` e `POST /chapters/{chapter_id}/rewrite` agora indicam a rota real:

```text
/documents/{document_id}/jobs/{job_id}
```

Motivo:

- A API não possui rota global `/jobs/{job_id}`.
- A mensagem antiga poderia confundir a futura interface web e qualquer cliente HTTP.

## Endpoints testados

Todos os endpoints abaixo foram testados com sucesso:

- `GET /health`
- `POST /documents/upload`
- `POST /documents/{document_id}/index`
- `GET /documents/{document_id}`
- `GET /documents/{document_id}/jobs/{job_id}`
- `POST /documents/{document_id}/filter`
- `POST /documents/{document_id}/validate-relevance`
- `POST /chapters/build`
- `GET /chapters/{chapter_id}`
- `POST /chapters/{chapter_id}/summarize`
- `POST /chapters/{chapter_id}/rewrite`
- `GET /exports/{chapter_id}/markdown`
- `GET /exports/{chapter_id}/docx`

## Resultado do teste ponta a ponta

- Documento: `098611b6-4930-442b-8f4e-bf5a87c4cbf2`
- PDF processado: 153 páginas
- Chunks criados: 412
- Capítulo criado: `c828ad3b-e974-48ad-8f12-b9f715dc7dfc`
- Markdown exportado: `200 OK`, 2235 bytes
- DOCX exportado: `200 OK`, 37729 bytes

## Validação

Comandos executados:

```powershell
docker compose up --build -d
docker compose exec -T app pytest -q
```

Resultado:

```text
18 passed
```

Health check final:

```json
{
  "status": "ok",
  "app": "Book AI",
  "version": "0.1.0"
}
```

## Observações para próximos passos

- A dependência `agno` ainda existe em `requirements.txt`, mas os agentes atuais não dependem mais do adapter OpenAI do Agno em runtime.
- Para a interface web, a rota correta de polling de qualquer job continua sendo `GET /documents/{document_id}/jobs/{job_id}`.
- O fluxo já está pronto para ser consumido por uma UI: upload, indexação, busca, validação, montagem, resumo, reescrita e exportação.
