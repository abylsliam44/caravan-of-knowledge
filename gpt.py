import os
from dotenv import load_dotenv
import logging
import httpx
from google_docs import google_docs_service
from chat_memory import chat_memory

load_dotenv()

AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

async def ask_gpt(prompt: str, phone_number: str, is_first_message: bool = False) -> str:
    if not (AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_DEPLOYMENT_NAME):
        logging.error("Azure OpenAI credentials are not set!")
        return "Ошибка: не настроены переменные окружения Azure OpenAI."

    # Получаем актуальный промпт из Google Docs
    system_prompt = google_docs_service.get_prompt_from_docs(is_first_message)
    logging.info(f"Using system prompt: {system_prompt[:100]}...")

    # Получаем историю чата
    chat_history = chat_memory.get_messages_for_gpt(phone_number)
    logging.info(f"Chat history for {phone_number}: {len(chat_history)} messages")

    # Формируем сообщения для GPT
    messages = [{"role": "system", "content": system_prompt}]
    
    # Добавляем историю чата (если есть)
    if chat_history:
        messages.extend(chat_history)
        logging.info(f"Added {len(chat_history)} messages from chat history")
    
    # Добавляем текущее сообщение пользователя
    messages.append({"role": "user", "content": prompt})
    
    # Логируем контекст для отладки
    if chat_history:
        recent_context = chat_history[-3:] if len(chat_history) >= 3 else chat_history
        context_summary = " | ".join([f"{msg['role']}: {msg['content'][:50]}..." for msg in recent_context])
        logging.info(f"Recent context: {context_summary}")

    url = f"{AZURE_OPENAI_ENDPOINT}openai/deployments/{AZURE_OPENAI_DEPLOYMENT_NAME}/chat/completions?api-version=2024-02-15-preview"
    headers = {
        "api-key": AZURE_OPENAI_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "messages": messages,
        "max_tokens": 512,
        "temperature": 0.7
    }
    
    logging.info(f"Sending request to GPT with {len(messages)} messages")
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=data)
        if resp.status_code == 200:
            result = resp.json()
            gpt_response = result["choices"][0]["message"]["content"]
            
            # Сохраняем сообщения в историю чата
            chat_memory.add_message(phone_number, "user", prompt)
            chat_memory.add_message(phone_number, "assistant", gpt_response)
            
            logging.info(f"GPT response saved to chat history for {phone_number}")
            return gpt_response
        else:
            logging.error(f"Azure OpenAI error: {resp.status_code} {resp.text}")
            return f"Ошибка Azure OpenAI: {resp.status_code} {resp.text}" 