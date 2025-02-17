import os
from typing import List, Dict
from dotenv import load_dotenv
from groq import Groq
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document, SystemMessage, HumanMessage, AIMessage
from langchain_community.vectorstores import Qdrant
from prompt_middleware import PromptMiddleware
from supabase import create_client, Client

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

class ChatSession:
    def __init__(self, bot_id: str, processing_ids: List[str]):
        self.bot_id = bot_id
        self.processing_ids = processing_ids
        self.middleware = None
        self.vector_store = None
        self.groq_client = None
        self.messages = []  # Lista de mensagens no formato LangChain
        self.setup()
    
    def setup(self):
        """Inicializa os componentes necessários para a sessão"""
        load_dotenv()
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
        
        # Inicializa a lista de mensagens com a mensagem do sistema
        self.messages = [
            SystemMessage(content="Você é um assistente útil que responde perguntas com base no contexto fornecido.")
        ]
    
    def get_rag_response(self, query: str) -> str:
        """Get RAG-enhanced response for a query"""
        # Gera o contexto RAG
        results = self.vector_store.similarity_search(query, k=3)
        rag_context = "\n".join([doc.page_content for doc in results])
        
        # Cria o prompt aumentado com o contexto
        augmented_prompt = f"""Use o contexto abaixo para responder à pergunta.

Contexto:
{rag_context}

Pergunta: {query}"""
        
        # Adiciona a mensagem do usuário
        self.messages.append(HumanMessage(content=augmented_prompt))
        
        # Processa através do middleware
        final_prompt, behavior = self.middleware.process_query(query, rag_context)
        
        # Obtém a resposta
        response = get_groq_response(self.groq_client, final_prompt)
        
        # Adiciona a resposta do assistente ao histórico
        self.messages.append(AIMessage(content=response))
        
        # Mantém apenas as últimas N mensagens (sistema + 3 pares de interação)
        if len(self.messages) > 7:  # 1 sistema + 6 mensagens (3 pares)
            self.messages = [self.messages[0]] + self.messages[-6:]
        
        return response 