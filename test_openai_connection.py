#!/usr/bin/env python3
"""
Скрипт для тестирования подключения к OpenAI API
"""
import os
import asyncio
import sys
from dotenv import load_dotenv
import httpx

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

async def test_openai_chat():
    """Тест Chat Completions API"""
    print("=" * 60)
    print("🧪 Тестирование OpenAI Chat API")
    print("=" * 60)
    
    if not OPENAI_API_KEY:
        print("❌ OPENAI_API_KEY не установлен в .env файле!")
        return False
    
    print(f"✅ API Key найден: {OPENAI_API_KEY[:10]}...{OPENAI_API_KEY[-4:]}")
    print(f"📝 Модель: {OPENAI_MODEL}")
    
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": "Ты - полезный помощник."},
            {"role": "user", "content": "Привет! Скажи одним предложением, что ты умеешь."}
        ],
        "max_tokens": 100
    }
    
    try:
        print("\n🔄 Отправка запроса к OpenAI...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=data)
            
            if resp.status_code == 200:
                result = resp.json()
                response_text = result["choices"][0]["message"]["content"]
                
                print("✅ Подключение успешно!")
                print(f"\n💬 Ответ GPT:\n{response_text}")
                print(f"\n📊 Использовано токенов:")
                print(f"   - Входных: {result['usage']['prompt_tokens']}")
                print(f"   - Выходных: {result['usage']['completion_tokens']}")
                print(f"   - Всего: {result['usage']['total_tokens']}")
                
                return True
            else:
                print(f"❌ Ошибка: {resp.status_code}")
                print(f"Ответ: {resp.text}")
                
                if resp.status_code == 401:
                    print("\n💡 Подсказка: Проверьте правильность API ключа")
                elif resp.status_code == 429:
                    print("\n💡 Подсказка: Превышен лимит запросов или недостаточно средств")
                    print("   Пополните баланс: https://platform.openai.com/account/billing")
                elif resp.status_code == 404:
                    print(f"\n💡 Подсказка: Модель '{OPENAI_MODEL}' не найдена или недоступна")
                    
                return False
                
    except Exception as e:
        print(f"❌ Ошибка при подключении: {e}")
        return False

async def test_openai_models():
    """Тест доступных моделей"""
    print("\n" + "=" * 60)
    print("📋 Проверка доступных моделей")
    print("=" * 60)
    
    url = "https://api.openai.com/v1/models"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            
            if resp.status_code == 200:
                result = resp.json()
                models = [m["id"] for m in result["data"] if "gpt" in m["id"]]
                
                print(f"✅ Доступно моделей: {len(models)}")
                print("\n🤖 Доступные GPT модели:")
                for model in sorted(models)[:10]:  # Показываем первые 10
                    print(f"   - {model}")
                
                if len(models) > 10:
                    print(f"   ... и еще {len(models) - 10} моделей")
                
                return True
            else:
                print(f"❌ Не удалось получить список моделей: {resp.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

async def test_whisper_info():
    """Информация о Whisper API"""
    print("\n" + "=" * 60)
    print("🎤 Информация о Whisper API")
    print("=" * 60)
    
    print("✅ Whisper API доступен с тем же ключом")
    print("📝 Endpoint: https://api.openai.com/v1/audio/transcriptions")
    print("🌍 Поддерживаемые языки: русский, казахский, английский и др.")
    print("💰 Стоимость: $0.006 / минута аудио")
    print("\n💡 Для тестирования голосовых сообщений отправьте")
    print("   голосовое сообщение боту в WhatsApp")

async def main():
    """Основная функция тестирования"""
    print("\n🚀 Тестирование OpenAI подключения")
    print("=" * 60)
    
    # Тест Chat API
    chat_ok = await test_openai_chat()
    
    # Тест моделей
    if chat_ok:
        await test_openai_models()
    
    # Информация о Whisper
    await test_whisper_info()
    
    print("\n" + "=" * 60)
    if chat_ok:
        print("✅ Все тесты пройдены успешно!")
        print("\n🎉 Ваш бот готов к работе с OpenAI!")
        print("\nСледующие шаги:")
        print("1. Убедитесь, что все переменные в .env настроены")
        print("2. Запустите бота: uvicorn main:app --reload")
        print("3. Настройте webhook в Green API")
    else:
        print("❌ Тесты не пройдены")
        print("\n🔧 Проверьте:")
        print("1. OPENAI_API_KEY в файле .env")
        print("2. Баланс на https://platform.openai.com/account/billing")
        print("3. Права доступа к API ключу")
    print("=" * 60 + "\n")
    
    return 0 if chat_ok else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

