from fastapi import APIRouter, HTTPException
from typing import Dict
from services.chat_service import ChatSession
from models.chat_models import ChatRequest, ChatResponse, SessionConfig
import os

router = APIRouter()

# Armazena as sessões ativas
active_sessions: Dict[str, ChatSession] = {}

@router.post("/session")
async def create_session(config: SessionConfig) -> Dict[str, str]:
    """Cria uma nova sessão de chat"""
    try:
        session_id = f"{config.bot_id}_{'_'.join(config.processing_ids)}"
        if session_id not in active_sessions:
            active_sessions[session_id] = ChatSession(config.bot_id, config.processing_ids)
        return {"session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}")
async def chat(session_id: str, request: ChatRequest) -> ChatResponse:
    """Processa uma mensagem do chat"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    
    try:
        session = active_sessions[session_id]
        response = session.get_rag_response(request.message)
        return ChatResponse(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{session_id}")
async def end_session(session_id: str):
    """Encerra uma sessão de chat"""
    if session_id in active_sessions:
        del active_sessions[session_id]
    return {"status": "success"} 