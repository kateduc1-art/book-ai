# 2026-05-07 - feat: add configurable chat provider

## Commit sugerido

```text
feat: add configurable chat provider
```

## Contexto

Depois de estabilizar o fluxo da API, o próximo passo foi preparar o projeto para escolher o modelo de LLM sem alterar os agentes. A primeira etapa cobre apenas chat/LLM. Embeddings continuam separados e ainda usam OpenAI.

## Alterações feitas

### Configuração de provider/modelo

Arquivo:

- `app/core/config.py`

Novas variáveis:

- `CHAT_PROVIDER`: provider de chat. Valores suportados hoje: `openai`, `openai-compatible`.
- `CHAT_MODEL`: modelo usado pelos agentes. Se vazio, usa `OPENAI_MODEL`.
- `OPENAI_BASE_URL`: endpoint opcional para provedores compatíveis com a API da OpenAI.

Compatibilidade:

- Configurações antigas continuam funcionando.
- Se apenas `OPENAI_MODEL` estiver definido, ele segue sendo usado.

### Camada de provider

Arquivo:

- `app/agents/chat_provider.py`

Foi criada a interface `ChatProvider` e a implementação `OpenAIChatProvider`.

O factory `get_chat_provider()` resolve o provider configurado e retorna a implementação adequada.

### Agentes desacoplados

Arquivos:

- `app/agents/relevance_validator_agent.py`
- `app/agents/summarizer_agent.py`
- `app/agents/rewriter_agent.py`

Os agentes agora usam:

```python
get_chat_provider()
```

em vez de depender diretamente de um client OpenAI específico.

### Exemplo de ambiente

Arquivo:

- `.env.example`

Inclui as variáveis principais para banco, OpenAI, chat provider, embeddings e processamento.

## Como trocar modelos de chat

### OpenAI padrão

```env
CHAT_PROVIDER=openai
CHAT_MODEL=gpt-4.1-mini
OPENAI_API_KEY=sk-...
```

Se `CHAT_MODEL` ficar vazio, o app usa `OPENAI_MODEL`.

### Provider OpenAI-compatible

```env
CHAT_PROVIDER=openai-compatible
CHAT_MODEL=nome-do-modelo
OPENAI_BASE_URL=http://localhost:1234/v1
OPENAI_API_KEY=local-ou-chave-do-provider
```

Esse modo pode ser usado com serviços que expõem uma API compatível com OpenAI, como servidores locais ou roteadores de modelos.

## Limite atual

Esta mudança não altera embeddings. O campo `chunks.embedding` ainda está fixo em `Vector(1536)`, adequado para `text-embedding-3-small`.

Trocar embeddings para modelos com outra dimensão ainda exige migração ou recriação da tabela.
