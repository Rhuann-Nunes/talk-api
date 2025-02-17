from fastapi import APIRouter, HTTPException
from typing import Dict
from services.bot_creator import BotCreator
from models.bot_models import BotRequest, BotResponse
from supabase import create_client
import os

router = APIRouter()
creator = BotCreator()

@router.post("/", response_model=BotResponse)
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