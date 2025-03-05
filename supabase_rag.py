#!/usr/bin/env python
import os
import json
from typing import List, Dict, Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from groq import Groq
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document
from langchain_community.vectorstores import Qdrant
from supabase import create_client, Client
import time

# Modelos para a API
class ProjectTask:
    def __init__(self, 
                user_name: str, 
                user_pronoun: str, 
                projects_data, 
                tasks_data,
                timestamp: Optional[str] = None):
        self.user_name = user_name
        self.user_pronoun = user_pronoun
        self.projects_data = projects_data
        self.tasks_data = tasks_data
        self.timestamp = timestamp
        self.vector_store = None
        self.groq_client = None
        self.chat_history: List[Dict[str, str]] = []
        self.setup()
    
    def setup(self):
        """Inicializa os componentes necessários para a sessão"""
        self.groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))
        embeddings = OpenAIEmbeddings(model=os.getenv('EMBEDDING_MODEL_NAME', 'text-embedding-3-small'))
        
        # Cria documentos para embedding diretamente dos dados fornecidos
        documents = self.create_documents(self.projects_data, self.tasks_data)
        
        # Configura o vector store com os documentos
        collection_name = f"project_tasks_{self.user_name}_{int(time.time())}"
        self.vector_store = setup_vector_store(documents, embeddings, collection_name)
    
    def create_documents(self, projects_data, tasks_data) -> List[Document]:
        """Cria documentos a partir dos dados de projetos e tarefas em qualquer formato"""
        documents = []
        
        # Função para processar dados em diferentes formatos possíveis
        def process_data(data, type_name):
            # Se for uma string, tenta processar como texto
            if isinstance(data, str):
                # Tenta primeiro como JSON
                try:
                    parsed_data = json.loads(data)
                    return self._process_structured_data(parsed_data, type_name)
                except:
                    # Se não for JSON válido, trata como texto não estruturado
                    return [Document(
                        page_content=f"{type_name} (texto não estruturado):\n{data}",
                        metadata={'type': type_name.lower(), 'format': 'unstructured'}
                    )]
            
            # Se for lista ou dicionário, trata como dados estruturados
            elif isinstance(data, (list, dict)):
                return self._process_structured_data(data, type_name)
            
            # Outros tipos de dados, converte para string
            else:
                return [Document(
                    page_content=f"{type_name} (formato desconhecido):\n{str(data)}",
                    metadata={'type': type_name.lower(), 'format': 'unknown'}
                )]
        
        # Processa projetos e tarefas e adiciona à lista de documentos
        documents.extend(process_data(projects_data, "Projetos"))
        documents.extend(process_data(tasks_data, "Tarefas"))
        
        return documents
    
    def _process_structured_data(self, data, type_name):
        """Processa dados estruturados (dicionários ou listas)"""
        documents = []
        
        # Se for um dicionário, trata como um único item
        if isinstance(data, dict):
            data = [data]  # Converte para lista com um item
        
        # Se for uma lista, processa cada item
        if isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, dict):
                    # Converte o item para um formato de texto estruturado
                    item_text = f"{type_name} #{i+1}:\n"
                    for key, value in item.items():
                        item_text += f"{key}: {value}\n"
                    
                    # Determina metadados apropriados
                    metadata = {
                        'type': type_name.lower().rstrip('s'),  # Remove o 's' de "Projetos"/"Tarefas"
                        'id': item.get('id', f'unknown_{i}')
                    }
                    
                    # Adiciona project_id para tarefas se disponível
                    if type_name.lower() == 'tarefas' and 'project_id' in item:
                        metadata['project_id'] = item['project_id']
                    
                    doc = Document(
                        page_content=item_text,
                        metadata=metadata
                    )
                    documents.append(doc)
                else:
                    # Item não é um dicionário, converte para string
                    documents.append(Document(
                        page_content=f"{type_name} #{i+1}:\n{str(item)}",
                        metadata={'type': type_name.lower(), 'format': 'simple'}
                    ))
        
        return documents

class UserConfig(BaseModel):
    user_name: str
    user_pronoun: str
    projects_data: Optional[str] = None
    tasks_data: Optional[str] = None
    timestamp: Optional[str] = None  # Campo para armazenar o timestamp

class QueryRequest(BaseModel):
    message: str

class QueryResponse(BaseModel):
    response: str

# Inicializa a aplicação FastAPI
app = FastAPI(title="Project Task RAG API")

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todas as origens
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos os métodos
    allow_headers=["*"],  # Permite todos os cabeçalhos
)

# Armazena as sessões ativas
active_sessions: Dict[str, ProjectTask] = {}

def load_environment():
    """Load environment variables from .env file"""
    load_dotenv('./.env')
    
    required_vars = [
        'GROQ_API_KEY', 
        'OPENAI_API_KEY', 
        'QDRANT_HOST', 
        'QDRANT_PORT',
        'SUPABASE_URL',
        'SUPABASE_SERVICE_KEY'
        # 'PORT' foi removido da lista de variáveis obrigatórias
    ]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

def get_groq_response(client: Groq, prompt: str) -> str:
    """Get response from Groq model"""
    completion = client.chat.completions.create(
        model=os.getenv('GROQ_MODEL_NAME', 'deepseek-r1-distill-llama-70b'),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6,
        max_completion_tokens=1024,
        top_p=0.95,
        stream=False,
        reasoning_format="hidden"
    )
    
    return completion.choices[0].message.content

def setup_vector_store(documents: List[Document], embeddings, collection_name: str):
    """Set up the Qdrant vector store with the documents"""
    return Qdrant.from_documents(
        documents=documents,
        embedding=embeddings,
        location=":memory:" if os.getenv('QDRANT_HOST') == 'localhost' else None,
        url=f"http://{os.getenv('QDRANT_HOST')}:{os.getenv('QDRANT_PORT')}" if os.getenv('QDRANT_HOST') != 'localhost' else None,
        api_key=os.getenv('QDRANT_API_KEY'),
        collection_name=collection_name
    )

def get_rag_response(query: str, session: ProjectTask) -> str:
    """Get RAG-enhanced response for a query"""
    # Adiciona histórico ao contexto
    chat_context = "\nHistórico da conversa:\n" + "\n".join([
        f"Usuário: {msg['user']}\nAssistente: {msg['assistant']}"
        for msg in session.chat_history[-3:]  # Últimas 3 interações
    ]) if session.chat_history else ""
    
    # Gera o contexto RAG
    results = session.vector_store.similarity_search(query, k=5)
    rag_context = "\n".join([doc.page_content for doc in results])
    
    # Combina os contextos
    full_context = f"{rag_context}\n{chat_context}"
    
    # Cria o prompt final
    prompt = f"""Você é um assistente de projetos e tarefas para {session.user_name}. 
Trate {session.user_name} usando o pronome {session.user_pronoun}.

Instruções de Resposta:
1. Use o contexto abaixo para responder à pergunta sobre os projetos e tarefas de {session.user_name}
2. Se a informação não estiver no contexto, diga que não tem informação suficiente para responder
3. Seja sempre cortês, profissional e útil
4. Se questionado sobre projetos, foque nas informações dos projetos
5. Se questionado sobre tarefas, foque nas informações das tarefas
6. Se perguntado sobre uma relação entre projetos e tarefas, busque as conexões entre eles

Contexto:
{full_context}

Pergunta: {query}"""
    
    # Obtém a resposta
    response = get_groq_response(session.groq_client, prompt)
    
    # Atualiza o histórico
    session.chat_history.append({
        "user": query,
        "assistant": response
    })
    
    return response

@app.on_event("startup")
async def startup_event():
    """Inicializa as configurações necessárias"""
    load_environment()

@app.post("/rag/session")
async def create_session(config: UserConfig) -> Dict[str, str]:
    """Cria uma nova sessão RAG"""
    try:
        # Usa o timestamp fornecido ou gera um novo baseado no tempo atual
        timestamp = config.timestamp if config.timestamp else str(int(time.time()))
        
        # Gera um ID de sessão único baseado no nome de usuário e um timestamp
        session_id = f"{config.user_name}_{int(time.time())}"
        
        if session_id not in active_sessions:
            active_sessions[session_id] = ProjectTask(
                config.user_name,
                config.user_pronoun,
                config.projects_data,
                config.tasks_data,
                timestamp
            )
        return {"session_id": session_id, "timestamp": timestamp}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/rag/{session_id}")
async def query(session_id: str, request: QueryRequest) -> QueryResponse:
    """Processa uma consulta RAG"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    
    try:
        session = active_sessions[session_id]
        response = get_rag_response(request.message, session)
        return QueryResponse(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/rag/{session_id}")
async def end_session(session_id: str):
    """Encerra uma sessão RAG"""
    if session_id in active_sessions:
        del active_sessions[session_id]
    return {"status": "success"}

# Para deploy no Railway
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    uvicorn.run("supabase_rag:app", host="0.0.0.0", port=port, reload=True) 