# 📚 Book AI — Análise Completa do Projeto

## O que é o Book AI?

O **Book AI** é um sistema backend (API REST) para **processamento inteligente de livros e PDFs** usando IA. Ele recebe um PDF, extrai o texto, indexa com embeddings vetoriais, filtra trechos por temas usando busca semântica, valida relevância com agentes de IA, monta capítulos filtrados, resume, reescreve e exporta em **Markdown** e **DOCX**.

> [!IMPORTANT]
> O projeto **não tem interface web** — é apenas uma API REST consumida via `curl`, Postman ou qualquer cliente HTTP. O roadmap futuro prevê um dashboard React/Next.js.

---

## Stack Tecnológica

| Camada | Tecnologia | Propósito |
|---|---|---|
| **API** | FastAPI + Uvicorn | Framework web assíncrono |
| **IA / Agentes** | [Agno](https://github.com/agno-agi/agno) + OpenAI | Framework de agentes + LLM |
| **Banco de dados** | PostgreSQL 16 + pgvector | Armazenamento + busca vetorial |
| **PDF** | PyMuPDF + pdfplumber (fallback) | Extração de texto de PDFs |
| **Exportação** | python-docx | Geração de .docx |
| **Jobs** | FastAPI BackgroundTasks | Tarefas assíncronas |
| **Containers** | Docker Compose | Orquestração local |
| **Config** | Pydantic Settings + .env | Configuração centralizada |

---

## Arquitetura e Estrutura de Diretórios

```mermaid
graph TB
    subgraph "API Layer"
        H["/health"]
        D["/documents"]
        S["/search"]
        C["/chapters"]
        E["/exports"]
    end
    
    subgraph "Services Layer"
        PDF["pdf_extractor"]
        CHK["chunker"]
        EMB["embedding_service"]
        VS["vector_store"]
        DI["document_indexer"]
        TS["topic_search_service"]
        CB["chapter_builder"]
        EXP["export_service"]
    end
    
    subgraph "Agents Layer (Agno + OpenAI)"
        RVA["RelevanceValidatorAgent"]
        CAA["ChapterAssemblerAgent"]
        SA["SummarizerAgent"]
        RA["RewriterAgent"]
    end
    
    subgraph "Data Layer"
        DB[(PostgreSQL + pgvector)]
        FS[("storage/uploads & exports")]
    end
    
    D --> DI --> PDF --> CHK --> EMB --> VS
    S --> TS --> VS
    S --> RVA
    C --> CB
    C --> SA
    C --> RA
    E --> EXP
    
    DI --> DB
    VS --> DB
    CB --> DB
    EXP --> FS
```

### Mapa de diretórios

| Caminho | Descrição |
|---|---|
| [main.py](file:///c:/Users/dnbs/Documents/book-ai/book-ai/app/main.py) | Entry point FastAPI — lifespan, middleware, registro de rotas |
| [app/core/](file:///c:/Users/dnbs/Documents/book-ai/book-ai/app/core) | Configuração, banco de dados e logging |
| [app/models/](file:///c:/Users/dnbs/Documents/book-ai/book-ai/app/models) | Modelos SQLAlchemy (Document, Chunk, Chapter, Job) |
| [app/schemas/](file:///c:/Users/dnbs/Documents/book-ai/book-ai/app/schemas) | DTOs Pydantic para request/response |
| [app/services/](file:///c:/Users/dnbs/Documents/book-ai/book-ai/app/services) | Lógica de negócio — extração, chunking, embeddings, busca, exportação |
| [app/agents/](file:///c:/Users/dnbs/Documents/book-ai/book-ai/app/agents) | 4 agentes de IA (Agno) — validação, montagem, resumo, reescrita |
| [app/workflows/](file:///c:/Users/dnbs/Documents/book-ai/book-ai/app/workflows) | Pipeline completo orquestrado (`BookProcessingWorkflow`) |
| [app/api/routes/](file:///c:/Users/dnbs/Documents/book-ai/book-ai/app/api/routes) | Endpoints REST — health, documents, search, chapters, exports |
| [tests/](file:///c:/Users/dnbs/Documents/book-ai/book-ai/tests) | Testes unitários (pdf_extractor, chunker, chapter_builder) |
| [scripts/](file:///c:/Users/dnbs/Documents/book-ai/book-ai/scripts) | Script de inicialização do banco |

---

## Pipeline de Processamento (10 Steps)

O pipeline completo é orquestrado pela classe [BookProcessingWorkflow](file:///c:/Users/dnbs/Documents/book-ai/book-ai/app/workflows/book_processing_workflow.py):

```mermaid
flowchart LR
    A["1. Upload PDF"] --> B["2. Extrair texto\n(PyMuPDF)"]
    B --> C["3. Chunking\n(sobreposição)"]
    C --> D["4. Gerar embeddings\n(OpenAI)"]
    D --> E["5. Armazenar vetores\n(pgvector)"]
    E --> F["6. Busca por temas\n(semântica + keywords)"]
    F --> G["7. Validar relevância\n(Agente IA)"]
    G --> H["8. Montar capítulo\n(Markdown)"]
    H --> I["9. Resumir\n(Agente IA)"]
    I --> J["10. Reescrever\n(Agente IA)"]
    J --> K["11. Exportar\n(.md + .docx)"]
```

### Detalhamento de cada etapa

#### 1️⃣ Upload de PDF → [documents.py:upload_document](file:///c:/Users/dnbs/Documents/book-ai/book-ai/app/api/routes/documents.py#L41-L73)
- Recebe o arquivo via `multipart/form-data`
- Valida extensão (apenas `.pdf`)
- Salva em `storage/uploads/` com nome baseado em UUID
- Cria registro `Document` no banco com status `uploaded`

#### 2️⃣ Extração de texto → [pdf_extractor.py](file:///c:/Users/dnbs/Documents/book-ai/book-ai/app/services/pdf_extractor.py)
- Tenta **PyMuPDF** (fitz) primeiro — é mais rápido e confiável
- Se falhar, usa **pdfplumber** como fallback
- Divide cada página em parágrafos (por quebras de linha duplas)
- Detecta headings de capítulos usando regex: `Capítulo X`, `Chapter X`, `1. Título`
- Retorna lista de `ExtractedParagraph` com `page_number`, `paragraph_number`, `text`, `original_chapter`

#### 3️⃣ Chunking → [chunker.py](file:///c:/Users/dnbs/Documents/book-ai/book-ai/app/services/chunker.py)
- Divide parágrafos longos em chunks menores com **sobreposição**
- Configurável via `CHUNK_SIZE` (padrão: 500 chars) e `CHUNK_OVERLAP` (padrão: 50 chars)
- Splitting baseado em sentenças (terminadores `.`, `!`, `?`)
- Mantém overlap preservando as últimas sentenças do chunk anterior
- Parágrafos menores que `chunk_size` ficam como chunk único

#### 4️⃣ Embeddings → [embedding_service.py](file:///c:/Users/dnbs/Documents/book-ai/book-ai/app/services/embedding_service.py)
- Interface abstrata `EmbeddingProvider` com implementação OpenAI
- Modelo padrão: `text-embedding-3-small` (1536 dimensões)
- Processa em batches de 100 textos por chamada API
- Preparado para extensão futura (Gemini, Anthropic, modelos locais)

#### 5️⃣ Armazenamento vetorial → [vector_store.py](file:///c:/Users/dnbs/Documents/book-ai/book-ai/app/services/vector_store.py)
- Interface abstrata `VectorStore` com implementação `PgVectorStore`
- Usa o operador `<=>` (distância cosseno) do pgvector
- Calcula score como `1 - distância_cosseno`
- Busca 3x mais resultados que `top_k` para filtrar por `min_score` depois

#### 6️⃣ Busca por temas → [topic_search_service.py](file:///c:/Users/dnbs/Documents/book-ai/book-ai/app/services/topic_search_service.py)
- Cada tópico é embeddado separadamente
- Busca vetorial por similaridade + **keyword boost** (até 0.05 extra)
- Resultados deduplicados por `chunk_id`
- Ordenados por score, limitados a `max_results`

#### 7️⃣ Validação de relevância → [relevance_validator_agent.py](file:///c:/Users/dnbs/Documents/book-ai/book-ai/app/agents/relevance_validator_agent.py)
- Agente **Agno** com prompt em português
- Para cada chunk, pergunta ao LLM: "este trecho contribui conceitualmente para os temas?"
- Retorna `is_relevant`, `confidence`, `matched_topics`, `reason`
- Processamento sequencial (chunk por chunk) — sem batching paralelo

#### 8️⃣ Montagem de capítulo → [chapter_builder.py](file:///c:/Users/dnbs/Documents/book-ai/book-ai/app/services/chapter_builder.py)
- Ordena chunks por página e parágrafo
- Gera Markdown estruturado: `# Título` → `## Introdução` → `## Conteúdo` → `## Considerações Finais` → `## Fontes`
- Cada trecho tem referência `*[p. X]*` e comentário HTML com fonte
- Preserva headings de capítulos originais como `### Heading`

#### 9️⃣ Resumo → [summarizer_agent.py](file:///c:/Users/dnbs/Documents/book-ai/book-ai/app/agents/summarizer_agent.py)
- Agente Agno que gera resumo estruturado em JSON
- Retorna: `summary_short` (3 frases), `summary_detailed` (1-2 parágrafos), `key_points`, `concepts`
- Trunca conteúdo a 12.000 chars para evitar limites de tokens

#### 🔟 Reescrita → [rewriter_agent.py](file:///c:/Users/dnbs/Documents/book-ai/book-ai/app/agents/rewriter_agent.py)
- Agente Agno que reescreve mantendo fidelidade ao original
- Configurável por `style` e `audience`
- Gera `source_map`: mapeamento parágrafo → páginas originais
- Trunca a 14.000 chars

#### 1️⃣1️⃣ Exportação → [export_service.py](file:///c:/Users/dnbs/Documents/book-ai/book-ai/app/services/export_service.py)
- **Markdown**: escreve o conteúdo reescrito (ou original) em `.md`
- **DOCX**: converte Markdown para documento Word usando `python-docx`, com headings, blockquotes, bullet lists, referências de página em fonte pequena e cinza

---

## Modelos de Dados

```mermaid
erDiagram
    Document {
        string id PK
        string filename
        string original_path
        enum status "uploaded|indexing|indexed|failed"
        int total_pages
        int total_chunks
        datetime created_at
        datetime updated_at
    }
    
    Chunk {
        string id PK
        string document_id FK
        int page_number
        int paragraph_number
        int chunk_index
        text text_content
        string original_chapter
        int char_count
        vector embedding "1536 dims"
        datetime created_at
    }
    
    Chapter {
        string id PK
        string document_id FK
        string title
        json topics
        text markdown_content
        text rewritten_markdown
        text summary_short
        text summary_detailed
        json key_points
        json concepts
        json sources
        json source_map
        json chunk_ids
        string export_md_path
        string export_docx_path
        datetime created_at
        datetime updated_at
    }
    
    Job {
        string id PK
        string document_id FK
        enum job_type "index|filter|validate|build|summarize|rewrite|export"
        enum status "pending|running|completed|failed"
        int progress "0-100"
        string current_step
        text error_message
        json result
        json input_data
        datetime created_at
        datetime started_at
        datetime finished_at
    }
    
    Document ||--o{ Chunk : has
    Document ||--o{ Chapter : has
    Document ||--o{ Job : has
```

---

## Endpoints da API

| Método | Path | Descrição | Tipo |
|---|---|---|---|
| `GET` | `/health` | Health check | Síncrono |
| `POST` | `/documents/upload` | Upload de PDF | Síncrono |
| `POST` | `/documents/{id}/index` | Iniciar indexação | **Async Job** |
| `GET` | `/documents/{id}` | Detalhes do documento | Síncrono |
| `GET` | `/documents/{id}/jobs/{job_id}` | Status de um job | Síncrono |
| `POST` | `/documents/{id}/filter` | Busca por temas | Síncrono |
| `POST` | `/documents/{id}/validate-relevance` | Validar chunks com IA | **Async Job** |
| `POST` | `/chapters/build` | Montar capítulo | Síncrono |
| `POST` | `/chapters/{id}/summarize` | Resumir capítulo | **Async Job** |
| `POST` | `/chapters/{id}/rewrite` | Reescrever capítulo | **Async Job** |
| `GET` | `/chapters/{id}` | Detalhes do capítulo | Síncrono |
| `GET` | `/exports/{id}/markdown` | Download .md | Síncrono |
| `GET` | `/exports/{id}/docx` | Download .docx | Síncrono |

> [!NOTE]
> Operações marcadas como **Async Job** retornam um `job_id`. Você deve fazer polling em `GET /documents/{id}/jobs/{job_id}` para acompanhar o progresso e obter o resultado.

---

## Como Rodar o Projeto

### Opção 1: Docker Compose (Recomendado)

```bash
# 1. Clone o repositório
git clone <repo-url>
cd book-ai

# 2. Crie o arquivo .env
cp .env.example .env
# Edite .env e preencha:
#   OPENAI_API_KEY=sk-...

# 3. Suba tudo
docker compose up --build
```

Isso levanta:
- **PostgreSQL 16 + pgvector** (porta 5432, container `book_ai_db`)
- **App FastAPI** (porta 8000, container `book_ai_app`)

A API fica disponível em `http://localhost:8000` e o Swagger em `http://localhost:8000/docs`.

### Opção 2: Localmente (sem Docker)

#### Pré-requisitos
- **Python 3.11+**
- **PostgreSQL 16** com extensão pgvector instalada
- Chave de API da OpenAI

```bash
# 1. Instale as dependências
pip install -r requirements.txt

# 2. Configure o .env
cp .env.example .env
# Edite com sua OPENAI_API_KEY e DATABASE_URL

# 3. Inicialize o banco de dados
python scripts/create_db.py

# 4. Suba a API
uvicorn app.main:app --reload
```

### Variáveis de Ambiente Obrigatórias

| Variável | Descrição | Padrão |
|---|---|---|
| `OPENAI_API_KEY` | Sua chave da OpenAI | *obrigatória* |
| `DATABASE_URL` | Connection string PostgreSQL | `postgresql+psycopg2://bookai:bookai@localhost:5432/book_ai` |

### Variáveis Opcionais

| Variável | Descrição | Padrão |
|---|---|---|
| `OPENAI_MODEL` | Modelo de chat | `gpt-4.1-mini` |
| `EMBEDDING_MODEL` | Modelo de embeddings | `text-embedding-3-small` |
| `CHUNK_SIZE` | Tamanho máximo de chunk (chars) | `500` |
| `CHUNK_OVERLAP` | Sobreposição entre chunks | `50` |
| `MIN_SCORE` | Score mínimo para busca vetorial | `0.75` |
| `MAX_RESULTS` | Máximo de resultados por busca | `100` |
| `USE_NOTEBOOKLM` | Ativar integração NotebookLM | `false` |

---

## Como Usar (Fluxo Completo)

### Passo 1: Verificar se a API está rodando
```bash
curl http://localhost:8000/health
# → {"status":"ok","app":"Book AI","version":"0.1.0"}
```

### Passo 2: Upload de PDF
```bash
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@meu_livro.pdf"
# → {"document_id":"uuid-aqui","filename":"meu_livro.pdf","status":"uploaded"}
```

### Passo 3: Indexar (extrai, chunka, gera embeddings)
```bash
curl -X POST http://localhost:8000/documents/{document_id}/index
# → {"job_id":"uuid","job_type":"index","status":"pending","message":"..."}

# Acompanhar progresso:
curl http://localhost:8000/documents/{document_id}/jobs/{job_id}
# Aguarde status="completed"
```

### Passo 4: Buscar por temas
```bash
curl -X POST http://localhost:8000/documents/{document_id}/filter \
  -H "Content-Type: application/json" \
  -d '{"topics":["consciência fonológica","alfabetização"],"min_score":0.75}'
# → Retorna lista de chunks com score, página, texto
```

### Passo 5: Validar relevância com IA
```bash
curl -X POST http://localhost:8000/documents/{document_id}/validate-relevance \
  -H "Content-Type: application/json" \
  -d '{"topics":["consciência fonológica"],"candidate_chunk_ids":["id1","id2"]}'
# → Retorna job_id (async). Resultado contém is_relevant, confidence, reason.
```

### Passo 6: Montar capítulo
```bash
curl -X POST http://localhost:8000/chapters/build \
  -H "Content-Type: application/json" \
  -d '{"document_id":"uuid","title":"Meu Capítulo","topics":["tema1"],"validated_chunk_ids":["id1","id2"]}'
```

### Passo 7: Resumir e reescrever (async)
```bash
# Resumir
curl -X POST http://localhost:8000/chapters/{chapter_id}/summarize

# Reescrever
curl -X POST http://localhost:8000/chapters/{chapter_id}/rewrite \
  -H "Content-Type: application/json" \
  -d '{"style":"didático","audience":"professores"}'
```

### Passo 8: Exportar
```bash
# Markdown
curl -OJ http://localhost:8000/exports/{chapter_id}/markdown

# DOCX
curl -OJ http://localhost:8000/exports/{chapter_id}/docx
```

---

## Como Modificar o Projeto

### 🔧 Trocar o modelo de LLM

Edite o `.env`:
```env
OPENAI_MODEL=gpt-4o           # modelo de chat
EMBEDDING_MODEL=text-embedding-3-large  # modelo de embeddings (3072 dims)
```

> [!WARNING]
> Se trocar para `text-embedding-3-large`, o modelo gera vetores de 3072 dimensões. A coluna `embedding` no [chunk.py](file:///c:/Users/dnbs/Documents/book-ai/book-ai/app/models/chunk.py#L24) está hardcoded para `Vector(1536)`. Você precisará alterar para `Vector(3072)` e recriar a tabela.

### 🔧 Alterar o tamanho dos chunks

No `.env`:
```env
CHUNK_SIZE=800     # chunks maiores = mais contexto, menos chunks
CHUNK_OVERLAP=100  # overlap maior = menos perda de contexto nas bordas
```

### 🔧 Adicionar um novo provider de embeddings

1. Crie uma nova classe em [embedding_service.py](file:///c:/Users/dnbs/Documents/book-ai/book-ai/app/services/embedding_service.py) que implemente `EmbeddingProvider`
2. Atualize a factory `get_embedding_provider()` para selecionar por config
3. Exemplo:
```python
class GeminiEmbeddingProvider(EmbeddingProvider):
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        # Implementação Gemini
        ...
```

### 🔧 Adicionar um novo agente

1. Crie um arquivo em `app/agents/` seguindo o padrão dos existentes
2. Defina o `_SYSTEM_PROMPT` em português com regras claras
3. Crie a classe com método `__init__` que instancia `Agent` do Agno
4. Use nos endpoints via routes ou no workflow

### 🔧 Adicionar um novo endpoint

1. Crie um arquivo em `app/api/routes/` com um `APIRouter`
2. Registre o router em [main.py](file:///c:/Users/dnbs/Documents/book-ai/book-ai/app/main.py#L44-L54)
3. Crie schemas em `app/schemas/` se necessário

### 🔧 Alterar o banco de dados

- Os modelos SQLAlchemy estão em `app/models/`
- O projeto usa `Base.metadata.create_all()` para criar tabelas automaticamente no startup
- Para migrações em produção, o `alembic` já está nas dependências mas **não está configurado** — seria necessário inicializar com `alembic init`

---

## Testes

```bash
pytest
# ou com mais detalhes:
pytest -v --tb=short
```

### Testes existentes

| Arquivo | O que testa | Requer banco? |
|---|---|---|
| [test_pdf_extractor.py](file:///c:/Users/dnbs/Documents/book-ai/book-ai/tests/test_pdf_extractor.py) | Extração de PDF (cria PDFs sintéticos in-memory) | ❌ |
| [test_chunker.py](file:///c:/Users/dnbs/Documents/book-ai/book-ai/tests/test_chunker.py) | Chunking com overlap, metadados, edge cases | ❌ |
| [test_chapter_builder.py](file:///c:/Users/dnbs/Documents/book-ai/book-ai/tests/test_chapter_builder.py) | Montagem de Markdown a partir de mock chunks | ❌ |

> [!TIP]
> Nenhum teste existente requer banco de dados ou chave de API. Eles usam PDFs sintéticos (PyMuPDF) e mocks. Você pode rodar `pytest` sem PostgreSQL ou OpenAI configurados.

---

## Padrões Arquiteturais Usados

| Padrão | Onde | Exemplo |
|---|---|---|
| **Abstract Factory** | Services | `EmbeddingProvider` → `OpenAIEmbeddingProvider` |
| **Strategy** | Vector Store, Embeddings | Interface + implementação trocável |
| **Pipeline/Workflow** | `BookProcessingWorkflow` | 10 steps encadeados |
| **Background Jobs** | Routes | `BackgroundTasks` do FastAPI |
| **DTO Pattern** | Schemas | Pydantic models para request/response |
| **Repository-like** | Database | `get_db()` dependency injection |

---

## Limitações Atuais

- ⚡ **Embeddings síncronos** — pode ser lento para PDFs grandes
- 🖼️ **Sem OCR** — PDFs baseados em imagem não são lidos
- 📄 **Um documento por vez** — sem pipeline multi-documento
- 🌐 **Sem interface web** — apenas API REST
- 🔄 **Validação sequencial** — chunks são validados um por um pelo agente
- 📏 **Truncamento** — resumo (12k chars) e reescrita (14k chars) truncam conteúdo longo
- 🗄️ **Sem migrações** — Alembic instalado mas não configurado
- 🔒 **Sem autenticação** — CORS aberto para `*`

---

## Roadmap Futuro (conforme README)

- [ ] OCR com Tesseract ou Google Document AI
- [ ] Fila assíncrona com Celery + Redis
- [ ] Interface web (React/Next.js)
- [ ] Integração real com NotebookLM Enterprise
- [ ] Pipeline multi-documento
- [ ] Detecção automática de capítulos via IA
- [ ] Comparação cross-document (RAG)
- [ ] Deduplicação semântica
- [ ] Painel administrativo
- [ ] Suporte a Gemini e Anthropic

---

## Atualizacao Tecnica - 2026-05-07

Depois do teste ponta a ponta da API com o PDF `Refatorando com padrões de projeto_ Um guia em Java.pdf`, foram feitas correcoes para estabilizar o fluxo completo dos endpoints antes da construcao da interface web.

### Commit sugerido

```text
fix: stabilize API endpoint flow
```

### Documento de referencia da diff

A diff documentada foi salva em:

```text
2026-05-07-fix-api-endpoint-flow.md
```

Esse arquivo registra o contexto, as alteracoes por modulo, os endpoints testados e o resultado da validacao.

### Mudancas principais

#### Inicializacao dos modelos SQLAlchemy

Arquivos alterados:

- `app/models/__init__.py`
- `app/core/database.py`

O pacote `app.models` agora importa explicitamente `Document`, `Chunk`, `Chapter` e `Job`. O `init_db()` carrega esses modelos antes de executar `Base.metadata.create_all()`.

Isso corrige o erro em `POST /documents/upload`, no qual o SQLAlchemy nao conseguia resolver relationships como `Document.chunks`.

#### Busca vetorial com pgvector

Arquivo alterado:

- `app/services/vector_store.py`

A busca vetorial passou a usar:

```python
Chunk.embedding.cosine_distance(query_vector)
```

em vez de montar manualmente o operador `<=>` com `cast(...)`.

Isso corrige o erro:

```text
ValueError: expected ndim to be 1
```

que acontecia em `POST /documents/{document_id}/filter`.

#### Agentes com OpenAI SDK direto

Arquivos alterados:

- `app/agents/openai_chat_client.py`
- `app/agents/relevance_validator_agent.py`
- `app/agents/summarizer_agent.py`
- `app/agents/rewriter_agent.py`

Foi criado um wrapper pequeno chamado `OpenAIChatClient`, usado pelos agentes de validacao, resumo e reescrita.

Com isso, os agentes deixam de depender do adapter `agno.models.openai.OpenAIChat` no caminho critico de execucao. A dependencia `agno` ainda existe no projeto, mas os agentes atuais usam o SDK oficial da OpenAI diretamente para evitar incompatibilidades de versao.

#### Mensagens de polling dos jobs de capitulo

Arquivo alterado:

- `app/api/routes/chapters.py`

As mensagens retornadas por:

- `POST /chapters/{chapter_id}/summarize`
- `POST /chapters/{chapter_id}/rewrite`

agora apontam para a rota correta de acompanhamento:

```text
GET /documents/{document_id}/jobs/{job_id}
```

A API nao possui uma rota global `/jobs/{job_id}`.

### Endpoints validados

Foram testados com sucesso:

| Metodo | Path |
|---|---|
| `GET` | `/health` |
| `POST` | `/documents/upload` |
| `POST` | `/documents/{document_id}/index` |
| `GET` | `/documents/{document_id}` |
| `GET` | `/documents/{document_id}/jobs/{job_id}` |
| `POST` | `/documents/{document_id}/filter` |
| `POST` | `/documents/{document_id}/validate-relevance` |
| `POST` | `/chapters/build` |
| `GET` | `/chapters/{chapter_id}` |
| `POST` | `/chapters/{chapter_id}/summarize` |
| `POST` | `/chapters/{chapter_id}/rewrite` |
| `GET` | `/exports/{chapter_id}/markdown` |
| `GET` | `/exports/{chapter_id}/docx` |

### Resultado do teste com PDF real

| Item | Resultado |
|---|---|
| Documento | `098611b6-4930-442b-8f4e-bf5a87c4cbf2` |
| PDF processado | 153 paginas |
| Chunks criados | 412 |
| Capitulo criado | `c828ad3b-e974-48ad-8f12-b9f715dc7dfc` |
| Export Markdown | `200 OK`, 2235 bytes |
| Export DOCX | `200 OK`, 37729 bytes |

### Validacao final

```powershell
docker compose up --build -d
docker compose exec -T app pytest -q
```

Resultado:

```text
18 passed
```

Health check:

```json
{
  "status": "ok",
  "app": "Book AI",
  "version": "0.1.0"
}
```
