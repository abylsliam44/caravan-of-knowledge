import os
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI
from webhook import router as webhook_router

app = FastAPI(title="WhatsApp AI Bot")
app.include_router(webhook_router)

# Health check endpoint для Render
@app.get("/health")
async def health_check():
    from database import db
    return {
        "status": "healthy",
        "service": "whatsapp-ai-bot",
        "version": "2.0.0",
        "features": {
            "openai_gpt": True,
            "whisper_api": True,
            "n8n_integration": os.getenv("USE_N8N", "false").lower() == "true",
            "redis_memory": os.getenv("REDIS_URL") is not None,
            "postgresql_history": db.enabled
        }
    }

# Endpoint для просмотра истории чатов (для аналитики)
@app.get("/api/chats")
async def get_all_chats():
    """Получить список всех чатов"""
    from chat_memory import chat_memory
    numbers = chat_memory.get_all_chat_numbers()
    return {"total": len(numbers), "chats": numbers}

@app.get("/api/chat/{phone_number}")
async def get_chat_history(phone_number: str, limit: int = 100):
    """Получить полную историю чата из PostgreSQL"""
    from chat_memory import chat_memory
    history = chat_memory.get_full_history_from_db(phone_number, limit)
    return {
        "phone": phone_number,
        "total_messages": len(history),
        "messages": history
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True) 