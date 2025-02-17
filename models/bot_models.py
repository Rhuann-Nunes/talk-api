from pydantic import BaseModel
from typing import Dict

class BotRequest(BaseModel):
    name: str
    description: str
    user_id: str

class BotResponse(BaseModel):
    bot_id: str
    name: str
    main_prompt: str
    behavioral_prompts: Dict[str, str] 