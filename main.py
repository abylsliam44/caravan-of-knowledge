import os
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI
from webhook import router as webhook_router

app = FastAPI(title="WhatsApp AI Bot")
app.include_router(webhook_router)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True) 