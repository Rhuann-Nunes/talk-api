# Supabase Projects and Tasks RAG

Este é um sistema de RAG (Retrieval-Augmented Generation) que permite consultar informações sobre projetos e tarefas armazenados no Supabase. O sistema utiliza embeddings e um modelo Groq para fornecer respostas contextualizadas sobre os dados.

## Requisitos

- Python 3.8+
- Acesso ao Supabase
- Acesso à API da Groq
- Acesso à API do OpenAI (para embeddings)
- Qdrant (para armazenar e consultar vetores)

## Instalação

1. Clone o repositório:

```bash
git clone <URL_DO_REPOSITORIO>
cd <NOME_DO_REPOSITORIO>
```

2. Instale as dependências:

```bash
pip install -r requirements.txt
```

3. Crie um arquivo `.env` com as seguintes variáveis:

```
GROQ_API_KEY=sua_chave_groq
OPENAI_API_KEY=sua_chave_openai
QDRANT_HOST=seu_host_qdrant
QDRANT_PORT=seu_port_qdrant
SUPABASE_URL=sua_url_supabase
SUPABASE_SERVICE_KEY=sua_chave_supabase
PORT=8000
GROQ_MODEL_NAME=deepseek-r1-distill-llama-70b
EMBEDDING_MODEL_NAME=text-embedding-3-small
```

## Estrutura das tabelas no Supabase

O sistema espera que você tenha tabelas no Supabase para projetos e tarefas. A estrutura específica das tabelas é flexível, pois o sistema manipula qualquer conjunto de colunas encontradas nas tabelas.

Exemplo de estrutura mínima recomendada:

### Tabela de Projetos
- `id`: identificador único do projeto
- `name`: nome do projeto
- `description`: descrição do projeto
- `status`: status atual do projeto
- `priority`: prioridade do projeto

### Tabela de Tarefas
- `id`: identificador único da tarefa
- `project_id`: referência ao id do projeto (chave estrangeira)
- `title`: título da tarefa
- `description`: descrição da tarefa
- `status`: status atual da tarefa
- `priority`: prioridade da tarefa
- `due_date`: data de vencimento

## Uso da API

### Iniciar uma sessão

Para iniciar uma sessão, envie uma requisição POST para `/rag/session` com os dados dos projetos e tarefas:

```bash
curl -X POST http://localhost:8000/rag/session \
  -H "Content-Type: application/json" \
  -d '{
    "user_name": "João",
    "user_pronoun": "Sr",
    "projects_data": [
      {
        "id": 1,
        "name": "Website Redesign",
        "description": "Redesenhar o site da empresa com novo layout",
        "status": "em andamento",
        "priority": "alta",
        "deadline": "2024-12-20"
      },
      {
        "id": 2,
        "name": "App Mobile",
        "description": "Desenvolvimento de app para iOS e Android",
        "status": "planejado",
        "priority": "média",
        "deadline": "2025-03-15"
      }
    ],
    "tasks_data": [
      {
        "id": 101,
        "project_id": 1,
        "title": "Criar wireframes",
        "description": "Desenvolver wireframes para todas as páginas",
        "status": "concluída",
        "priority": "alta",
        "due_date": "2024-10-15",
        "assigned_to": "Ana Silva"
      },
      {
        "id": 102,
        "project_id": 1,
        "title": "Implementar frontend",
        "description": "Implementar o HTML/CSS conforme os wireframes",
        "status": "em andamento",
        "priority": "alta",
        "due_date": "2024-11-20",
        "assigned_to": "Pedro Santos"
      }
    ]
  }'
```

Isso retornará um `session_id` que deve ser usado nas consultas subsequentes.

### Enviar uma consulta

Para enviar uma consulta, use o `session_id` recebido anteriormente:

```bash
curl -X POST http://localhost:8000/rag/João_1697820000 \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Quais são os projetos com prioridade alta?"
  }'
```

### Encerrar uma sessão

Para encerrar uma sessão:

```bash
curl -X DELETE http://localhost:8000/rag/João_1697820000
```

## Exemplos de consultas

- "Quais são os projetos em andamento?"
- "Liste todas as tarefas atrasadas"
- "Qual projeto tem mais tarefas?"
- "Mostre as tarefas com prioridade alta do projeto X"
- "Qual é o status do projeto Y?"

## Formato dos Dados

O sistema é extremamente flexível quanto ao formato dos dados de entrada. Você pode fornecer dados em:

### Formato JSON (Recomendado para Dados Estruturados)
```json
[
  {
    "id": 1,
    "name": "Nome do Projeto",
    "description": "Descrição do projeto",
    "status": "em andamento",
    "priority": "alta"
  }
]
```

### Formato de Texto Livre
```
Projeto: Website Redesign
Descrição: Redesenhar o site da empresa
Status: Em andamento
Prioridade: Alta

Projeto: App Mobile
Descrição: Desenvolvimento de app
Status: Planejado
Prioridade: Média
```

### Formato Tabular/CSV
```
id,nome,descrição,status,prioridade
1,Website Redesign,Redesenhar o site,Em andamento,Alta
2,App Mobile,Desenvolvimento de app,Planejado,Média
```

### Outros Formatos
O sistema tentará extrair o máximo de informações possível, independentemente do formato fornecido. Desde que os dados contenham informações sobre projetos e tarefas, o sistema será capaz de processar e responder a consultas sobre esses dados.

Não há necessidade de se preocupar com formatação específica - basta fornecer os dados da forma que você os tem disponíveis!

## Executando a aplicação

Para executar a aplicação localmente:

```bash
python supabase_rag.py
```

A API estará disponível em `http://localhost:8000`.

## Solução de Problemas

### Erro: Missing required environment variables: PORT

Se você receber este erro ao iniciar a aplicação, há duas soluções possíveis:

1. **Adicione a variável PORT ao seu arquivo .env**:
   ```
   PORT=8000
   ```

2. **Especifique a porta ao executar o aplicativo**:
   ```bash
   PORT=8000 python supabase_rag.py
   ```

3. **Modifique o código** para remover PORT da lista de variáveis obrigatórias (já implementado na versão mais recente).

### Outros erros comuns

- **Erro de conexão com o Supabase**: Verifique se as credenciais SUPABASE_URL e SUPABASE_SERVICE_KEY estão corretas.
- **Erro ao inicializar o Qdrant**: Certifique-se de que o Qdrant está em execução e acessível nas configurações fornecidas.
- **Erro de API Groq ou OpenAI**: Confirme se as chaves de API estão ativas e possuem créditos disponíveis. 