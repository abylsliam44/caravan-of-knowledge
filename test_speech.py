#!/usr/bin/env python3
"""
Тестовый скрипт для проверки настроек Azure Speech Services
"""

import os
import asyncio
import logging
from speech_recognition import speech_service

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_speech_service():
    """Тестирует настройки Azure Speech Services"""
    
    print("=== Тест настроек Azure Speech Services ===")
    
    # Проверяем переменные окружения
    print(f"AZURE_SPEECH_KEY: {'Установлен' if os.getenv('AZURE_SPEECH_KEY') else 'НЕ УСТАНОВЛЕН'}")
    print(f"AZURE_SPEECH_REGION: {os.getenv('AZURE_SPEECH_REGION', 'НЕ УСТАНОВЛЕН')}")
    
    # Проверяем статус сервиса
    print(f"Speech service enabled: {speech_service.enabled}")
    
    if speech_service.enabled:
        print(f"Speech config language: {speech_service.speech_config.speech_recognition_language}")
        print(f"Speech config region: {speech_service.speech_config.region}")
        print("✅ Azure Speech Services настроен корректно")
    else:
        print("❌ Azure Speech Services отключен")
        print("Убедитесь, что установлены переменные окружения AZURE_SPEECH_KEY и AZURE_SPEECH_REGION")
    
    print("\n=== Тест завершен ===")

if __name__ == "__main__":
    asyncio.run(test_speech_service()) 