import os
import httpx
from dotenv import load_dotenv
import logging

load_dotenv()
# Green API credentials
GREEN_ID_INSTANCE = os.getenv("GREEN_ID_INSTANCE")
GREEN_API_TOKEN = os.getenv("GREEN_API_TOKEN")
GREEN_API_URL = os.getenv("GREEN_API_URL", "https://api.green-api.com")

# Validate configuration at import time
if not (GREEN_ID_INSTANCE and GREEN_API_TOKEN):
    raise RuntimeError(
        "GREEN_ID_INSTANCE and GREEN_API_TOKEN environment variables must be set for Green API integration!"
    )

logging.basicConfig(level=logging.INFO)

async def send_whatsapp_message(to_number: str, text: str) -> dict:
    """Send a text message via Green API.

    Parameters
    ----------
    to_number : str
        Recipient phone number *without* leading plus sign (e.g. "77001234567").
    text : str
        Message body to send.
    """

    # Green API expects the chat ID in the format "<number>@c.us"
    chat_id = to_number if to_number.endswith("@c.us") else f"{to_number}@c.us"

    # Формируем URL из переменной окружения
    url = f"{GREEN_API_URL}/waInstance{GREEN_ID_INSTANCE}/sendMessage/{GREEN_API_TOKEN}"

    headers = {
        "Content-Type": "application/json"
    }

    data = {
        "chatId": chat_id,
        "message": text
    }

    # Подробное логирование для отладки
    logging.info(f"GREEN_ID_INSTANCE: {GREEN_ID_INSTANCE}")
    logging.info(f"Request URL: {url}")
    logging.info(f"Request headers: {headers}")
    logging.info(f"Request payload: {data}")

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=data)
        logging.info(f"Response status: {response.status_code}")
        logging.info(f"Response body: {response.text}")
        try:
            return response.json()
        except Exception:
            logging.error(f"Не удалось распарсить ответ как JSON: {response.text}")
            return {"error": "invalid_json", "raw": response.text, "status_code": response.status_code} 