import os
from dotenv import load_dotenv
import logging
import httpx
from google_docs import google_docs_service

load_dotenv()

AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

async def ask_gpt(prompt: str, is_first_message: bool = False) -> str:
    if not (AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_DEPLOYMENT_NAME):
        logging.error("Azure OpenAI credentials are not set!")
        return "Ошибка: не настроены переменные окружения Azure OpenAI."

    # Получаем актуальный промпт из Google Docs
    system_prompt = google_docs_service.get_prompt_from_docs(is_first_message)
    logging.info(f"Using system prompt: {system_prompt[:100]}...")

    url = f"{AZURE_OPENAI_ENDPOINT}openai/deployments/{AZURE_OPENAI_DEPLOYMENT_NAME}/chat/completions?api-version=2024-02-15-preview"
    headers = {
        "api-key": AZURE_OPENAI_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 512,
        "temperature": 0.7
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=data)
        if resp.status_code == 200:
            result = resp.json()
            return result["choices"][0]["message"]["content"]
        else:
            logging.error(f"Azure OpenAI error: {resp.status_code} {resp.text}")
            return f"Ошибка Azure OpenAI: {resp.status_code} {resp.text}" 