# Talk API

API para criação e interação com bots usando RAG (Retrieval-Augmented Generation) e LLMs.

## Funcionalidades

- Criação de bots com prompts gerados por IA
- Chat com RAG usando documentos do Supabase
- Histórico de conversas
- Middleware para gerenciamento de prompts

## Tecnologias

- FastAPI
- LangChain
- Groq
- Qdrant
- Supabase

## Variáveis de Ambiente

```env
# OpenAI
OPENAI_API_KEY=

# Groq
GROQ_API_KEY=
GROQ_MODEL_NAME=

# Qdrant
QDRANT_HOST=
QDRANT_PORT=
QDRANT_API_KEY=

# Supabase
SUPABASE_URL=
SUPABASE_SERVICE_KEY=

# Embedding Model
EMBEDDING_MODEL_NAME=
```

## Instalação

```bash
# Instalar dependências
pip install -r requirements.txt

# Executar
uvicorn main:app --reload
```

## Endpoints

### Bots

- `POST /bots` - Criar novo bot

### Chat

- `POST /chat/session` - Iniciar sessão
- `POST /chat/{session_id}` - Enviar mensagem
- `DELETE /chat/{session_id}` - Encerrar sessão

## Documentação

- Swagger UI: `/docs`
- ReDoc: `/redoc` 