from fastapi import APIRouter
from fastapi.responses import JSONResponse
import sys
import logging

from gpt import ask_gpt
from whatsapp import send_whatsapp_message
from speech_recognition import speech_service

router = APIRouter()

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, force=True)

# Простое хранилище для отслеживания состояний диалогов
# В продакшене лучше использовать Redis или базу данных
chat_states = {}

def is_first_message(from_number: str) -> bool:
    """Проверяет, является ли это первым сообщением от пользователя"""
    if from_number not in chat_states:
        chat_states[from_number] = {"message_count": 0}
    
    chat_states[from_number]["message_count"] += 1
    return chat_states[from_number]["message_count"] == 1


@router.post("/webhook")
async def receive_greenapi_webhook(payload: dict):
    print("=== /webhook CALLED ===")
    logging.info(f"Webhook payload: {payload}")
    try:
        type_webhook = payload.get("typeWebhook")
        logging.info(f"typeWebhook: {type_webhook}")
        if type_webhook != "incomingMessageReceived":
            logging.info("Webhook is not an incoming message event, skipping …")
            return {"status": "ignored", "reason": "non_message_webhook"}

        sender_data = payload.get("senderData", {})
        message_data = payload.get("messageData", {})
        logging.info(f"senderData: {sender_data}")
        logging.info(f"messageData: {message_data}")

        from_number = sender_data.get("sender")
        logging.info(f"from_number: {from_number}")
        if not from_number:
            logging.error("sender not found in webhook payload")
            return {"status": "error", "reason": "sender_not_found"}

        # Проверяем, первое ли это сообщение
        is_first = is_first_message(from_number)
        logging.info(f"Первое сообщение от {from_number}: {is_first}")

        type_message = message_data.get("typeMessage")
        logging.info(f"typeMessage: {type_message}")

        # TEXT MESSAGE
        if type_message == "textMessage":
            text = message_data.get("textMessageData", {}).get("textMessage")
            logging.info(f"Получено текстовое сообщение: {text}")

        # VOICE MESSAGE
        elif type_message == "voiceMessage":
            voice_data = message_data.get("voiceMessageData", {})
            download_url = voice_data.get("downloadUrl")
            logging.info(f"Получено голосовое сообщение, download_url: {download_url}")

            if not download_url:
                fallback_text = "Извините, не удалось обработать голосовое сообщение. Пожалуйста, отправьте текст."
                await send_whatsapp_message(from_number, fallback_text)
                logging.error("voiceMessage: download_url missing")
                return {"status": "voice_no_url"}

            recognized_text = await speech_service.process_voice_message_by_url(download_url)
            logging.info(f"Распознанный текст: {recognized_text}")

            if recognized_text:
                text = f"[Голосовое сообщение]: {recognized_text}"
            else:
                text = "Извините, не удалось распознать голосовое сообщение. Пожалуйста, отправьте текст."
                await send_whatsapp_message(from_number, text)
                logging.error("voiceMessage: распознавание не удалось")
                return {"status": "voice_recognition_failed"}

        # UNSUPPORTED TYPE
        else:
            fallback_text = (
                "Извините, я поддерживаю только текстовые и голосовые сообщения. "
                "Пожалуйста, отправьте текст или голосовое сообщение."
            )
            await send_whatsapp_message(from_number, fallback_text)
            logging.error(f"unsupported typeMessage: {type_message}")
            return {"status": "unsupported_message_type"}

        # Получаем ответ от GPT через Azure OpenAI
        logging.info(f"Передаём в GPT: {text}")
        gpt_response = await ask_gpt(text, is_first_message=is_first)
        logging.info(f"Ответ GPT: {gpt_response}")

        # Отправляем ответ клиенту
        logging.info(f"Отправляем ответ через send_whatsapp_message: {from_number} -> {gpt_response}")
        send_result = await send_whatsapp_message(from_number, gpt_response)
        logging.info(f"Результат отправки: {send_result}")
        print(f"Ответ отправлен: {gpt_response}")

        return {"status": "ok", "gpt_response": gpt_response, "send_result": send_result}

    except Exception as e:
        logging.error(f"Ошибка обработки webhook: {e}", exc_info=True)
        print(f"Ошибка обработки webhook: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)}) 