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

async def test_green_api_connection() -> dict:
    """Test Green API connection and token validity"""
    url = f"{GREEN_API_URL}/waInstance{GREEN_ID_INSTANCE}/getStateInstance/{GREEN_API_TOKEN}"
    
    logging.info(f"Testing Green API connection...")
    logging.info(f"GREEN_ID_INSTANCE: {GREEN_ID_INSTANCE}")
    logging.info(f"GREEN_API_URL: {GREEN_API_URL}")
    logging.info(f"Test URL: {url}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            logging.info(f"Test response status: {response.status_code}")
            logging.info(f"Test response body: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                logging.info(f"✅ Green API connection successful: {data}")
                return {"status": "success", "data": data}
            else:
                logging.error(f"❌ Green API connection failed: {response.status_code} - {response.text}")
                return {"status": "error", "status_code": response.status_code, "error": response.text}
    except Exception as e:
        logging.error(f"❌ Exception during Green API test: {e}")
        return {"status": "error", "exception": str(e)}

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
        
        # Специальная обработка ошибок
        if response.status_code == 401:
            logging.error("Ошибка 401: Неверный токен API или токен истек")
            return {"error": "unauthorized", "message": "Invalid API token or token expired", "status_code": 401}
        elif response.status_code == 403:
            logging.error("Ошибка 403: Доступ запрещен (возможно, превышена квота)")
            return {"error": "forbidden", "message": "Access denied (possibly quota exceeded)", "status_code": 403}
        elif response.status_code >= 400:
            logging.error(f"HTTP ошибка {response.status_code}: {response.text}")
            return {"error": "http_error", "status_code": response.status_code, "raw": response.text}
        
        try:
            return response.json()
        except Exception:
            logging.error(f"Не удалось распарсить ответ как JSON: {response.text}")
            return {"error": "invalid_json", "raw": response.text, "status_code": response.status_code} 