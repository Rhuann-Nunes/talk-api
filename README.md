# Supabase Projects and Tasks RAG

Este Ã© um sistema de RAG (Retrieval-Augmented Generation) que permite consultar informaÃ§Ãµes sobre projetos e tarefas armazenados no Supabase. O sistema utiliza embeddings e um modelo Groq para fornecer respostas contextualizadas sobre os dados.

## Requisitos

- Python 3.8+
- Acesso ao Supabase
- Acesso Ã  API da Groq
- Acesso Ã  API do OpenAI (para embeddings)
- Qdrant (para armazenar e consultar vetores)

## InstalaÃ§Ã£o

1. Clone o repositÃ³rio:

```bash
git clone <URL_DO_REPOSITORIO>
cd <NOME_DO_REPOSITORIO>
```

2. Instale as dependÃªncias:

```bash
pip install -r requirements.txt
```

3. Crie um arquivo `.env` com as seguintes variÃ¡veis:

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

O sistema espera que vocÃª tenha tabelas no Supabase para projetos e tarefas. A estrutura especÃ­fica das tabelas Ã© flexÃ­vel, pois o sistema manipula qualquer conjunto de colunas encontradas nas tabelas.

Exemplo de estrutura mÃ­nima recomendada:

### Tabela de Projetos
- `id`: identificador Ãºnico do projeto
- `name`: nome do projeto
- `description`: descriÃ§Ã£o do projeto
- `status`: status atual do projeto
- `priority`: prioridade do projeto

### Tabela de Tarefas
- `id`: identificador Ãºnico da tarefa
- `project_id`: referÃªncia ao id do projeto (chave estrangeira)
- `title`: tÃ­tulo da tarefa
- `description`: descriÃ§Ã£o da tarefa
- `status`: status atual da tarefa
- `priority`: prioridade da tarefa
- `due_date`: data de vencimento

## Uso da API

### Iniciar uma sessÃ£o

Para iniciar uma sessÃ£o, envie uma requisiÃ§Ã£o POST para `/rag/session` com os dados dos projetos e tarefas:

```bash
curl -X POST http://localhost:8000/rag/session \
  -H "Content-Type: application/json" \
  -d '{
    "user_name": "JoÃ£o",
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
        "priority": "mÃ©dia",
        "deadline": "2025-03-15"
      }
    ],
    "tasks_data": [
      {
        "id": 101,
        "project_id": 1,
        "title": "Criar wireframes",
        "description": "Desenvolver wireframes para todas as pÃ¡ginas",
        "status": "concluÃ­da",
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

Isso retornarÃ¡ um `session_id` que deve ser usado nas consultas subsequentes.

### Enviar uma consulta

Para enviar uma consulta, use o `session_id` recebido anteriormente:

```bash
curl -X POST http://localhost:8000/rag/JoÃ£o_1697820000 \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Quais sÃ£o os projetos com prioridade alta?"
  }'
```

### Encerrar uma sessÃ£o

Para encerrar uma sessÃ£o:

```bash
curl -X DELETE http://localhost:8000/rag/JoÃ£o_1697820000
```

## Exemplos de consultas

- "Quais sÃ£o os projetos em andamento?"
- "Liste todas as tarefas atrasadas"
- "Qual projeto tem mais tarefas?"
- "Mostre as tarefas com prioridade alta do projeto X"
- "Qual Ã© o status do projeto Y?"

## Formato dos Dados

O sistema Ã© extremamente flexÃ­vel quanto ao formato dos dados de entrada. VocÃª pode fornecer dados em:

### Formato JSON (Recomendado para Dados Estruturados)
```json
[
  {
    "id": 1,
    "name": "Nome do Projeto",
    "description": "DescriÃ§Ã£o do projeto",
    "status": "em andamento",
    "priority": "alta"
  }
]
```

### Formato de Texto Livre
```
Projeto: Website Redesign
DescriÃ§Ã£o: Redesenhar o site da empresa
Status: Em andamento
Prioridade: Alta

Projeto: App Mobile
DescriÃ§Ã£o: Desenvolvimento de app
Status: Planejado
Prioridade: MÃ©dia
```

### Formato Tabular/CSV
```
id,nome,descriÃ§Ã£o,status,prioridade
1,Website Redesign,Redesenhar o site,Em andamento,Alta
2,App Mobile,Desenvolvimento de app,Planejado,MÃ©dia
```

### Outros Formatos
O sistema tentarÃ¡ extrair o mÃ¡ximo de informaÃ§Ãµes possÃ­vel, independentemente do formato fornecido. Desde que os dados contenham informaÃ§Ãµes sobre projetos e tarefas, o sistema serÃ¡ capaz de processar e responder a consultas sobre esses dados.

NÃ£o hÃ¡ necessidade de se preocupar com formataÃ§Ã£o especÃ­fica - basta fornecer os dados da forma que vocÃª os tem disponÃ­veis!

## Executando a aplicaÃ§Ã£o

Para executar a aplicaÃ§Ã£o localmente:

```bash
python supabase_rag.py
```

A API estarÃ¡ disponÃ­vel em `http://localhost:8000`.

## SoluÃ§Ã£o de Problemas

### Erro: Missing required environment variables: PORT

Se vocÃª receber este erro ao iniciar a aplicaÃ§Ã£o, hÃ¡ duas soluÃ§Ãµes possÃ­veis:

1. **Adicione a variÃ¡vel PORT ao seu arquivo .env**:
   ```
   PORT=8000
   ```

2. **Especifique a porta ao executar o aplicativo**:
   ```bash
   PORT=8000 python supabase_rag.py
   ```

3. **Modifique o cÃ³digo** para remover PORT da lista de variÃ¡veis obrigatÃ³rias (jÃ¡ implementado na versÃ£o mais recente).

### Outros erros comuns

- **Erro de conexÃ£o com o Supabase**: Verifique se as credenciais SUPABASE_URL e SUPABASE_SERVICE_KEY estÃ£o corretas.
- **Erro ao inicializar o Qdrant**: Certifique-se de que o Qdrant estÃ¡ em execuÃ§Ã£o e acessÃ­vel nas configuraÃ§Ãµes fornecidas.
- **Erro de API Groq ou OpenAI**: Confirme se as chaves de API estÃ£o ativas e possuem crÃ©ditos disponÃ­veis. 
