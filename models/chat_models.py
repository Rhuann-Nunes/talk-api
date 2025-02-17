from pydantic import BaseModel
from typing import List

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    
class SessionConfig(BaseModel):
    bot_id: str
    processing_ids: List[str] 