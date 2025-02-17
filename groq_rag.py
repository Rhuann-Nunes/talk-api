#!/usr/bin/env python
import os
from typing import List, Dict, Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from groq import Groq
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document
from langchain_community.vectorstores import Qdrant
from prompt_middleware import PromptMiddleware
from supabase import create_client, Client

# Models para a API
class ChatSession:
    def __init__(self, bot_id: str, processing_ids: List[str]):
        self.bot_id = bot_id
        self.processing_ids = processing_ids
        self.middleware = None
        self.vector_store = None
        self.groq_client = None
        self.chat_history: List[Dict[str, str]] = []
        self.setup()
    
    def setup(self):
        """Inicializa os componentes necessários para a sessão"""
        self.groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))
        embeddings = OpenAIEmbeddings(model=os.getenv('EMBEDDING_MODEL_NAME', 'text-embedding-3-small'))
        
        # Inicializa o middleware
        self.middleware = PromptMiddleware(bot_id=self.bot_id)
        
        # Carrega e combina todos os documentos
        all_documents = []
        for proc_id in self.processing_ids:
            documents = load_document_chunks(proc_id)
            all_documents.extend(documents)
        
        # Configura o vector store com todos os documentos
        collection_name = f"chat_{self.bot_id}_{'_'.join(self.processing_ids)}"
        self.vector_store = setup_vector_store(all_documents, embeddings, collection_name)

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    
class SessionConfig(BaseModel):
    bot_id: str
    processing_ids: List[str]

# Inicializa a aplicação FastAPI
app = FastAPI(title="Chat RAG API")

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Armazena as sessões ativas
active_sessions: Dict[str, ChatSession] = {}

def load_environment():
    """Load environment variables from .env file"""
    load_dotenv('./.env')
    
    required_vars = [
        'GROQ_API_KEY', 
        'OPENAI_API_KEY', 
        'QDRANT_HOST', 
        'QDRANT_PORT',
        'SUPABASE_URL',
        'SUPABASE_SERVICE_KEY',
        'PORT'  # Para o Railway
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

def load_document_chunks(processing_id: str) -> List[Document]:
    """Load document chunks from Supabase"""
    supabase = create_client(
        os.getenv('SUPABASE_URL'),
        os.getenv('SUPABASE_SERVICE_KEY')
    )
    
    response = supabase.table('document_chunks') \
        .select('chunk_text, chunk_index') \
        .eq('processing_id', processing_id) \
        .order('chunk_index') \
        .execute()
    
    if not response.data:
        raise ValueError(f"Nenhum documento encontrado para o processing_id: {processing_id}")
    
    documents = []
    for chunk in response.data:
        doc = Document(
            page_content=chunk['chunk_text'],
            metadata={
                'chunk_index': chunk['chunk_index'],
                'processing_id': processing_id
            }
        )
        documents.append(doc)
    
    return documents

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

def get_rag_response(query: str, session: ChatSession) -> str:
    """Get RAG-enhanced response for a query"""
    # Adiciona histórico ao contexto
    chat_context = "\nHistórico da conversa:\n" + "\n".join([
        f"Usuário: {msg['user']}\nAssistente: {msg['assistant']}"
        for msg in session.chat_history[-3:]  # Últimas 3 interações
    ]) if session.chat_history else ""
    
    # Gera o contexto RAG
    results = session.vector_store.similarity_search(query, k=3)
    rag_context = "\n".join([doc.page_content for doc in results])
    
    # Combina os contextos
    full_context = f"{rag_context}\n{chat_context}"
    
    # Processa através do middleware
    final_prompt, behavior = session.middleware.process_query(query, full_context)
    
    # Obtém a resposta
    response = get_groq_response(session.groq_client, final_prompt)
    
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

@app.post("/chat/session")
async def create_session(config: SessionConfig) -> Dict[str, str]:
    """Cria uma nova sessão de chat"""
    try:
        session_id = f"{config.bot_id}_{'_'.join(config.processing_ids)}"
        if session_id not in active_sessions:
            active_sessions[session_id] = ChatSession(config.bot_id, config.processing_ids)
        return {"session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/{session_id}")
async def chat(session_id: str, request: ChatRequest) -> ChatResponse:
    """Processa uma mensagem do chat"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    
    try:
        session = active_sessions[session_id]
        response = get_rag_response(request.message, session)
        return ChatResponse(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/chat/{session_id}")
async def end_session(session_id: str):
    """Encerra uma sessão de chat"""
    if session_id in active_sessions:
        del active_sessions[session_id]
    return {"status": "success"}

# Para deploy no Railway
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    uvicorn.run("groq_rag:app", host="0.0.0.0", port=port, reload=True) 