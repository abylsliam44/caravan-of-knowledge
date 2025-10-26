import os
from dotenv import load_dotenv
import logging
import httpx
from google_docs import google_docs_service
from chat_memory import chat_memory

load_dotenv()

# Поддержка обоих форматов: OPEN_AI_KEY и OPENAI_API_KEY
OPENAI_API_KEY = os.getenv("OPEN_AI_KEY") or os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "512"))
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))

async def ask_gpt(prompt: str, phone_number: str, is_first_message: bool = False) -> str:
    if not OPENAI_API_KEY:
        logging.error("OpenAI API key is not set!")
        return "Ошибка: не настроена переменная окружения OPEN_AI_KEY или OPENAI_API_KEY."

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

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": OPENAI_MODEL,
        "messages": messages,
        "max_tokens": OPENAI_MAX_TOKENS,
        "temperature": OPENAI_TEMPERATURE
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
            logging.error(f"OpenAI API error: {resp.status_code} {resp.text}")
            return f"Ошибка OpenAI API: {resp.status_code} {resp.text}" 