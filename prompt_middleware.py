from typing import Dict, List, Optional, Tuple
import re
from dataclasses import dataclass
import time
import os
from dotenv import load_dotenv
from supabase import create_client, Client

@dataclass
class Interaction:
    """Representa uma interação na conversa"""
    message: str
    behavior: str  # Mudado de BehaviorType para str para ser mais flexível
    timestamp: float
    response: Optional[str] = None

class ConversationContext:
    """Gerencia o contexto da conversa"""
    def __init__(self, max_history: int = 5):
        self.history: List[Interaction] = []
        self.max_history = max_history
    
    def add_interaction(self, interaction: Interaction):
        """Adiciona uma nova interação ao histórico"""
        self.history.append(interaction)
        if len(self.history) > self.max_history:
            self.history.pop(0)
    
    def get_recent_behaviors(self, n: int = 3) -> List[str]:
        """Retorna os comportamentos mais recentes"""
        return [i.behavior for i in self.history[-n:]]

class BehaviorClassifier:
    """Classifica o comportamento com base na mensagem"""
    def __init__(self):
        self.behavior_patterns: Dict[str, List[str]] = {}
        self.default_behavior = "GENERAL"
    
    def update_patterns(self, behaviors: Dict[str, str]):
        """Atualiza os padrões de comportamento baseado nos prompts disponíveis"""
        # Inicializa o dicionário de padrões vazio
        self.behavior_patterns = {}
        
        # Registra todos os comportamentos do bot
        for behavior in behaviors.keys():
            self.behavior_patterns[behavior] = []
    
    def add_pattern(self, behavior: str, pattern: str):
        """Adiciona um novo padrão para um comportamento"""
        if behavior not in self.behavior_patterns:
            self.behavior_patterns[behavior] = []
        self.behavior_patterns[behavior].append(pattern)
    
    def classify(self, message: str) -> str:
        """Classifica a mensagem em um comportamento"""
        message = message.lower()
        
        # Lista para armazenar matches encontrados
        matches = []
        
        for behavior, patterns in self.behavior_patterns.items():
            for pattern in patterns:
                if pattern and re.search(pattern, message):
                    matches.append(behavior)
        
        # Se encontrou matches, retorna o primeiro comportamento encontrado
        if matches:
            return matches[0]
        
        # Se não encontrou nenhum match, retorna o comportamento default
        return self.default_behavior

class SupabasePromptStore:
    """Gerencia os prompts armazenados no Supabase"""
    def __init__(self):
        load_dotenv()
        self.client: Client = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_KEY')
        )
    
    def get_bot_prompts(self, bot_id: str) -> Tuple[Optional[str], Optional[Dict[str, str]]]:
        """Recupera os prompts do bot do Supabase"""
        try:
            # Busca o prompt principal
            bot_response = self.client.table('bots') \
                .select('main_prompt') \
                .eq('id', bot_id) \
                .execute()
            
            if not bot_response.data:
                raise ValueError(f"Bot com ID {bot_id} não encontrado")
            
            main_prompt = bot_response.data[0]['main_prompt']
            
            # Busca os prompts comportamentais
            behavioral_response = self.client.table('behavioral_prompts') \
                .select('behavior_type, prompt') \
                .eq('bot_id', bot_id) \
                .execute()
            
            # Converte a lista de prompts em um dicionário
            behavioral_prompts = {
                row['behavior_type']: row['prompt']
                for row in behavioral_response.data
            }
            
            # Garante que sempre existe um comportamento GENERAL
            if 'GENERAL' not in behavioral_prompts:
                behavioral_prompts['GENERAL'] = """Mantenha um atendimento profissional e acolhedor, 
focando em entender e atender às necessidades do cliente."""
            
            return main_prompt, behavioral_prompts
            
        except Exception as e:
            raise ValueError(f"Erro ao recuperar prompts do bot: {str(e)}")

class PromptMiddleware:
    """Sistema de middleware para gerenciar prompts e contexto"""
    def __init__(self, bot_id: str):
        self.context = ConversationContext()
        self.classifier = BehaviorClassifier()
        self.prompt_store = SupabasePromptStore()
        self.bot_id = bot_id
        
        # Carrega os prompts do bot
        self.main_prompt, self.behavioral_prompts = self.prompt_store.get_bot_prompts(bot_id)
        if not self.main_prompt or not self.behavioral_prompts:
            raise ValueError(f"Não foi possível carregar os prompts para o bot {bot_id}")
        
        # Atualiza os padrões do classificador com os comportamentos disponíveis
        self.classifier.update_patterns(self.behavioral_prompts)
    
    def process_query(self, query: str, rag_context: str) -> Tuple[str, str]:
        """Processa a query e retorna o prompt final e o comportamento identificado"""
        try:
            # Classifica o comportamento
            behavior = self.classifier.classify(query)
            
            # Cria nova interação
            interaction = Interaction(
                message=query,
                behavior=behavior,
                timestamp=time.time()
            )
            self.context.add_interaction(interaction)
            
            # Recupera o prompt comportamental com fallback para GENERAL
            behavioral_prompt = self.behavioral_prompts.get(behavior, 
                self.behavioral_prompts.get('GENERAL', 
                    "Mantenha um atendimento profissional e acolhedor."))
            
            # Gera o prompt combinado
            final_prompt = f"""Sistema: Você deve seguir estritamente as instruções abaixo para responder.

Prompt Principal (Sua Personalidade):
{self.main_prompt}

Comportamento Específico para esta Interação:
{behavioral_prompt}

Instruções de Resposta:
1. Use o contexto abaixo para responder à pergunta
2. Se a informação não estiver no contexto, diga que não tem informação suficiente para responder
3. Mantenha a personalidade definida no Prompt Principal
4. Siga o comportamento específico definido acima

Contexto:
{rag_context}

Pergunta do Cliente: {query}"""
            
            return final_prompt, behavior
            
        except Exception as e:
            # Em caso de erro, usa o comportamento GENERAL como fallback
            return self._generate_fallback_prompt(query, rag_context), "GENERAL"
    
    def _generate_fallback_prompt(self, query: str, rag_context: str) -> str:
        """Gera um prompt de fallback em caso de erro"""
        return f"""Sistema: Você deve seguir estritamente as instruções abaixo para responder.

Prompt Principal (Sua Personalidade):
{self.main_prompt}

Comportamento Específico para esta Interação:
Mantenha um atendimento profissional e acolhedor.

Instruções de Resposta:
1. Use o contexto abaixo para responder à pergunta
2. Se a informação não estiver no contexto, diga que não tem informação suficiente para responder
3. Mantenha a personalidade definida no Prompt Principal

Contexto:
{rag_context}

Pergunta do Cliente: {query}"""

# Exemplo de uso:
"""
from prompt_middleware import PromptMiddleware

# No seu código principal:
middleware = PromptMiddleware(bot_id="seu-bot-id-aqui")

def get_rag_response(query: str, client: Groq, vector_store: Qdrant) -> str:
    # Gera o contexto RAG
    results = vector_store.similarity_search(query, k=3)
    rag_context = "\n".join([doc.page_content for doc in results])
    
    # Processa através do middleware
    final_prompt, behavior = middleware.process_query(query, rag_context)
    
    # Usa o prompt processado para obter a resposta
    return get_groq_response(client, final_prompt)
""" 