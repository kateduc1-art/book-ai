# 📚 Book AI

Sistema de processamento de livros e PDFs grandes com IA, capaz de extrair, indexar, filtrar por tema, e gerar novos capítulos organizados e reescritos com apoio de agentes Agno.

---

## Objetivo

Receba um PDF → indexe com embeddings → filtre por temas → valide relevância com IA → monte um capítulo filtrado → resuma → reescreva → exporte em Markdown e DOCX.

**Importante:** O sistema trabalha com conteúdo próprio, licenciado, de domínio público ou autorizado. Nunca copia livros inteiros nem reconstrói conteúdo protegido.

---

## Stack

| Camada | Tecnologia |
|---|---|
| API | FastAPI + Uvicorn |
| IA / Agentes | Agno + OpenAI |
| Banco de dados | PostgreSQL + pgvector |
| PDF | PyMuPDF + pdfplumber (fallback) |
| Export | python-docx + Markdown |
| Jobs assíncronos | FastAPI BackgroundTasks |
| Containers | Docker Compose |

---

## Instalação

### 1. Clone o repositório

```bash
git clone <repo-url>
cd book-ai
```

### 2. Configure o ambiente

```bash
cp .env.example .env
# Edite .env e preencha:
#   OPENAI_API_KEY=sk-...
#   DATABASE_URL (já configurado para Docker)
```

### 3. Suba com Docker Compose

```bash
docker compose up --build
```

A API ficará disponível em: http://localhost:8000  
Documentação Swagger: http://localhost:8000/docs

---

## Como rodar localmente (sem Docker)

### Pré-requisitos

- Python 3.11+
- PostgreSQL 16 com extensão pgvector instalada
- `pip install -r requirements.txt`

### Inicialize o banco

```bash
python scripts/create_db.py
```

### Suba a API

```bash
uvicorn app.main:app --reload
```

---

## Fluxo de uso

### 1. Health check

```bash
curl http://localhost:8000/health
```

### 2. Upload de PDF

```bash
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@meu_livro.pdf"
```

Resposta:
```json
{
  "document_id": "uuid-aqui",
  "filename": "meu_livro.pdf",
  "status": "uploaded"
}
```

### 3. Indexar o documento

```bash
curl -X POST http://localhost:8000/documents/{document_id}/index
```

Retorna um `job_id`. Acompanhe o progresso:

```bash
curl http://localhost:8000/documents/{document_id}/jobs/{job_id}
```

Aguarde `status: "completed"` antes de prosseguir.

### 4. Filtrar por temas (busca vetorial)

```bash
curl -X POST http://localhost:8000/documents/{document_id}/filter \
  -H "Content-Type: application/json" \
  -d '{
    "topics": ["consciência fonológica", "alfabetização"],
    "min_score": 0.75,
    "max_results": 50
  }'
```

Retorna lista de trechos com `chunk_id`, `page`, `paragraph`, `text`, `score` e `matched_topic`.

### 5. Validar relevância com IA

```bash
curl -X POST http://localhost:8000/documents/{document_id}/validate-relevance \
  -H "Content-Type: application/json" \
  -d '{
    "topics": ["consciência fonológica"],
    "candidate_chunk_ids": ["id1", "id2", "id3"]
  }'
```

Retorna `job_id`. Verifique com `/documents/{document_id}/jobs/{job_id}`.

O resultado incluirá `is_relevant`, `confidence`, `matched_topics` e `reason` para cada chunk.

### 6. Montar capítulo

Com os `chunk_ids` validados:

```bash
curl -X POST http://localhost:8000/chapters/build \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "uuid",
    "title": "Consciência Fonológica na Alfabetização",
    "topics": ["consciência fonológica", "alfabetização"],
    "validated_chunk_ids": ["id1", "id2"]
  }'
```

### 7. Resumir o capítulo

```bash
curl -X POST http://localhost:8000/chapters/{chapter_id}/summarize
```

Retorna `job_id`. Verifique com `/jobs/{job_id}` — resultado inclui `summary_short`, `summary_detailed`, `key_points` e `concepts`.

### 8. Reescrever o capítulo

```bash
curl -X POST http://localhost:8000/chapters/{chapter_id}/rewrite \
  -H "Content-Type: application/json" \
  -d '{
    "style": "didático, claro, profissional e agradável",
    "audience": "professores e gestores educacionais",
    "preserve_sources": true
  }'
```

### 9. Exportar

```bash
# Markdown
curl -OJ http://localhost:8000/exports/{chapter_id}/markdown

# DOCX
curl -OJ http://localhost:8000/exports/{chapter_id}/docx
```

---

## Estrutura do projeto

```
book-ai/
├── app/
│   ├── main.py                    # FastAPI app + lifespan
│   ├── core/
│   │   ├── config.py              # Pydantic Settings
│   │   ├── database.py            # SQLAlchemy + pgvector init
│   │   └── logging.py             # Logger configurado
│   ├── models/
│   │   ├── document.py            # Document (SQLAlchemy)
│   │   ├── chunk.py               # Chunk + embedding (pgvector)
│   │   ├── chapter.py             # Chapter com markdown e exports
│   │   └── job.py                 # Job assíncrono com progresso
│   ├── schemas/
│   │   ├── document_schema.py     # Pydantic DTOs de documento
│   │   ├── filter_schema.py       # Busca e validação de relevância
│   │   ├── chapter_schema.py      # Criação, resumo e reescrita
│   │   └── export_schema.py       # Exportação e status de jobs
│   ├── services/
│   │   ├── pdf_extractor.py       # PyMuPDF → pdfplumber fallback
│   │   ├── chunker.py             # Splitting com sobreposição
│   │   ├── embedding_service.py   # Interface abstrata + OpenAI
│   │   ├── vector_store.py        # Interface abstrata + pgvector
│   │   ├── document_indexer.py    # Pipeline extract→chunk→embed→store
│   │   ├── topic_search_service.py # Busca vetorial + keyword boost
│   │   ├── chapter_builder.py     # Monta capítulo a partir de chunks
│   │   ├── export_service.py      # Gera .md e .docx
│   │   └── notebooklm_client.py   # Integração opcional NotebookLM
│   ├── agents/
│   │   ├── relevance_validator_agent.py  # Agno: valida relevância
│   │   ├── chapter_assembler_agent.py    # Agno: monta capítulo
│   │   ├── summarizer_agent.py           # Agno: gera resumo
│   │   └── rewriter_agent.py             # Agno: reescreve
│   ├── workflows/
│   │   └── book_processing_workflow.py   # Pipeline completo orquestrado
│   └── api/routes/
│       ├── health.py
│       ├── documents.py
│       ├── search.py
│       ├── chapters.py
│       └── exports.py
├── tests/
│   ├── test_pdf_extractor.py
│   ├── test_chunker.py
│   └── test_chapter_builder.py
├── scripts/
│   └── create_db.py
├── storage/
│   ├── uploads/                   # PDFs recebidos
│   └── exports/                   # Arquivos gerados
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── pytest.ini
└── .env.example
```

---

## Variáveis de ambiente

| Variável | Descrição | Padrão |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+psycopg2://bookai:bookai@localhost:5432/book_ai` |
| `OPENAI_API_KEY` | Chave da OpenAI | — |
| `OPENAI_MODEL` | Modelo de chat | `gpt-4.1-mini` |
| `EMBEDDING_MODEL` | Modelo de embeddings | `text-embedding-3-small` |
| `CHUNK_SIZE` | Tamanho máximo de chunk (chars) | `500` |
| `CHUNK_OVERLAP` | Sobreposição entre chunks | `50` |
| `MIN_SCORE` | Score mínimo para busca vetorial | `0.75` |
| `MAX_RESULTS` | Máximo de resultados por busca | `100` |
| `USE_NOTEBOOKLM` | Ativar integração NotebookLM | `false` |

---

## Testes

```bash
pytest
```

Os testes de extração de PDF criam PDFs sintéticos em tempo de execução (requer PyMuPDF). Os testes de chunker e chapter_builder não requerem banco de dados.

---

## NotebookLM Enterprise (opcional)

O arquivo `app/services/notebooklm_client.py` contém stubs documentados para integração com NotebookLM Enterprise API.

Para ativar:
1. Obtenha acesso ao NotebookLM Enterprise via Google Cloud
2. Configure `USE_NOTEBOOKLM=true` e as demais variáveis no `.env`
3. Implemente os métodos stub conforme a API oficial

> **Nota:** Não use automação de navegador ou scraping da interface do NotebookLM.

---

## Limitações atuais

- Processamento síncrono de embeddings (pode ser lento para PDFs grandes)
- Sem OCR — PDFs baseados em imagem não serão lidos
- Um documento por vez por pipeline
- Sem interface web

---

## Roadmap futuro

- [ ] **OCR** — integração com Tesseract ou Google Document AI
- [ ] **Fila assíncrona** — migração para Celery + Redis
- [ ] **Interface web** — dashboard React/Next.js
- [ ] **NotebookLM Enterprise** — integração real quando disponível
- [ ] **Múltiplos livros** — pipeline multi-documento
- [ ] **Detecção automática de capítulos** — via heurísticas e IA
- [ ] **Comparação entre livros** — RAG cross-document
- [ ] **Deduplicação semântica** — remover chunks muito similares
- [ ] **Painel administrativo** — gestão de documentos e jobs
- [ ] **Suporte a Gemini e Anthropic** — via camada de provider abstrata
