from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from routers import bot_router, chat_router

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Talk API",
    description="API para criação e interação com bots usando RAG e LLMs",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(bot_router, prefix="/bots", tags=["Bots"])
app.include_router(chat_router, prefix="/chat", tags=["Chat"])

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True) 