import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import json
from enum import Enum, auto
from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client, Client
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

class BehaviorType(Enum):
    """Tipos de comportamentos possíveis na interação"""
    GREETING = auto()              # Saudação Inicial
    EXPLORATION = auto()           # Exploração e Pesquisa Inicial
    PREFERENCES = auto()           # Definição de Preferências
    TECHNICAL = auto()             # Busca por Informações Técnicas
    COMPARISON = auto()            # Comparação e Validação
    INTEREST = auto()              # Interesse e Decisão Parcial
    PAYMENT = auto()               # Dúvidas sobre Pagamento
    DELIVERY = auto()              # Informação sobre Entrega
    EXCHANGE = auto()              # Políticas de Troca
    PURCHASE = auto()              # Decisão de Compra
    DATA_COLLECTION = auto()       # Fornecimento de Dados
    CONFIRMATION = auto()          # Confirmação e Comprovante
    FEEDBACK = auto()              # Feedback e Agradecimento
    POST_PURCHASE = auto()         # Dúvidas Pós-Compra
    HESITATION = auto()            # Indefinição ou Hesitação
    SUGGESTIONS = auto()           # Sugestões Adicionais
    CANCELLATION = auto()          # Cancelamento ou Alteração
    GENERAL = auto()               # Comportamento Geral

@dataclass
class BotConfig:
    """Configuração do bot"""
    name: str
    description: str
    user_id: str
    main_prompt: Optional[str] = None
    behavioral_prompts: Optional[Dict[str, str]] = None

class PromptGenerator:
    """Gera prompts usando OpenAI"""
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
    def generate_main_prompt(self, description: str) -> str:
        """Gera o prompt principal baseado na descrição"""
        system_prompt = """Você é um especialista em criar prompts para chatbots. 
Sua tarefa é criar um prompt principal que defina a personalidade e diretrizes do bot 
com base na descrição fornecida. O prompt deve ser claro, específico e seguir o formato:
'Você é [descrição da personalidade]. Seu objetivo é [objetivo principal]. 
[Diretrizes específicas de comportamento e tom].'"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Crie um prompt principal para um bot com a seguinte descrição: {description}"}
        ]
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
    
    def generate_behavioral_prompts(self, description: str, main_prompt: str) -> Dict[str, str]:
        """Gera sub-prompts comportamentais"""
        system_prompt = """Você é um especialista em criar prompts comportamentais para chatbots. 
Para cada comportamento listado, crie um sub-prompt específico que oriente como o bot deve responder 
naquela situação específica. Os prompts devem ser claros, práticos e alinhados com a personalidade 
principal do bot."""
        
        behaviors_description = "\n".join([
            f"- {behavior.name}: {behavior.value}" 
            for behavior in BehaviorType
        ])
        
        user_prompt = f"""Com base na descrição do bot e seu prompt principal:

Descrição: {description}
Prompt Principal: {main_prompt}

Crie sub-prompts para cada um dos seguintes comportamentos:
{behaviors_description}

Para cada comportamento, forneça um prompt que explique como o bot deve responder naquela situação específica.
Retorne no formato JSON:
{{
    "BEHAVIOR_TYPE": "prompt text",
    ...
}}"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7
        )
        
        return json.loads(response.choices[0].message.content)

class SupabaseManager:
    """Gerencia operações no Supabase"""
    def __init__(self):
        self.client: Client = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_KEY')
        )
    
    def save_bot(self, config: BotConfig) -> str:
        """Salva o bot e seus prompts no Supabase"""
        # Insere o bot
        bot_data = {
            'user_id': config.user_id,
            'name': config.name,
            'description': config.description,
            'main_prompt': config.main_prompt,
            'status': 'active'
        }
        
        result = self.client.table('bots').insert(bot_data).execute()
        bot_id = result.data[0]['id']
        
        # Insere os prompts comportamentais
        if config.behavioral_prompts:
            prompts_data = [
                {
                    'bot_id': bot_id,
                    'behavior_type': behavior,
                    'prompt': prompt
                }
                for behavior, prompt in config.behavioral_prompts.items()
            ]
            
            self.client.table('behavioral_prompts').insert(prompts_data).execute()
        
        return bot_id

class BotCreator:
    """Coordena a criação do bot"""
    def __init__(self):
        load_dotenv()
        self.prompt_generator = PromptGenerator()
        self.supabase_manager = SupabaseManager()
    
    def create_bot(self, name: str, description: str, user_id: str) -> str:
        """Cria um novo bot com prompts gerados por IA"""
        config = BotConfig(
            name=name,
            description=description,
            user_id=user_id
        )
        
        # Gera o prompt principal
        print("Gerando prompt principal...")
        config.main_prompt = self.prompt_generator.generate_main_prompt(description)
        
        # Gera os prompts comportamentais
        print("Gerando prompts comportamentais...")
        config.behavioral_prompts = self.prompt_generator.generate_behavioral_prompts(
            description,
            config.main_prompt
        )
        
        # Salva no Supabase
        print("Salvando bot no Supabase...")
        bot_id = self.supabase_manager.save_bot(config)
        
        print(f"Bot criado com sucesso! ID: {bot_id}")
        return bot_id

# Pydantic models for API
class BotRequest(BaseModel):
    name: str
    description: str
    user_id: str

class BotResponse(BaseModel):
    bot_id: str
    name: str
    main_prompt: str
    behavioral_prompts: Dict[str, str]

# Initialize FastAPI app
app = FastAPI(title="Bot Creator API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize BotCreator
creator = BotCreator()

@app.post("/bots", response_model=BotResponse)
async def create_bot(request: BotRequest):
    """Create a new bot with AI-generated prompts"""
    try:
        bot_id = creator.create_bot(
            name=request.name,
            description=request.description,
            user_id=request.user_id
        )
        
        # Get bot details from Supabase
        supabase = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_KEY')
        )
        
        # Get bot data
        bot_data = supabase.table('bots') \
            .select('*') \
            .eq('id', bot_id) \
            .single() \
            .execute()
            
        # Get behavioral prompts
        prompts_data = supabase.table('behavioral_prompts') \
            .select('*') \
            .eq('bot_id', bot_id) \
            .execute()
            
        behavioral_prompts = {
            prompt['behavior_type']: prompt['prompt']
            for prompt in prompts_data.data
        }
        
        return BotResponse(
            bot_id=bot_id,
            name=bot_data.data['name'],
            main_prompt=bot_data.data['main_prompt'],
            behavioral_prompts=behavioral_prompts
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    uvicorn.run("bot_creator:app", host="0.0.0.0", port=port, reload=True) 