#!/usr/bin/env python3
"""
Тестовый скрипт для проверки промпта
"""

import asyncio
import logging
from google_docs import google_docs_service

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_prompt():
    """Тестирует промпт для первого и последующих сообщений"""
    
    print("=== Тест промпта ===")
    
    # Тест для первого сообщения
    print("\n--- Промпт для первого сообщения ---")
    first_prompt = google_docs_service.get_prompt_from_docs(is_first_message=True)
    print(f"Длина промпта: {len(first_prompt)} символов")
    print("Первые 500 символов:")
    print(first_prompt[:500])
    print("...")
    
    # Проверяем, что нет упоминаний о представлении
    if "[Ваше Имя]" in first_prompt:
        print("❌ В промпте найдено '[Ваше Имя]'")
    else:
        print("✅ '[Ваше Имя]' не найдено в промпте")
    
    if "менеджер Caravan of Knowledge" in first_prompt:
        print("❌ В промпте найдено 'менеджер Caravan of Knowledge'")
    else:
        print("✅ 'менеджер Caravan of Knowledge' не найдено в промпте")
    
    # Тест для последующих сообщений
    print("\n--- Промпт для последующих сообщений ---")
    subsequent_prompt = google_docs_service.get_prompt_from_docs(is_first_message=False)
    print(f"Длина промпта: {len(subsequent_prompt)} символов")
    print("Первые 500 символов:")
    print(subsequent_prompt[:500])
    print("...")
    
    print("\n=== Тест завершен ===")

if __name__ == "__main__":
    asyncio.run(test_prompt()) 