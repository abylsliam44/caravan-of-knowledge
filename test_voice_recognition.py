#!/usr/bin/env python3
"""
Тестовый скрипт для проверки распознавания голосовых сообщений
"""

import asyncio
import logging
import os
from speech_recognition import speech_service

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_voice_recognition():
    """Тестирует распознавание голосовых сообщений"""
    
    print("=== Тест распознавания голосовых сообщений ===")
    
    # Проверяем переменные окружения
    print(f"AZURE_SPEECH_KEY: {'Установлен' if os.getenv('AZURE_SPEECH_KEY') else 'НЕ УСТАНОВЛЕН'}")
    print(f"AZURE_SPEECH_REGION: {os.getenv('AZURE_SPEECH_REGION', 'НЕ УСТАНОВЛЕН')}")
    
    # Проверяем статус сервиса
    print(f"Speech service enabled: {speech_service.enabled}")
    
    if not speech_service.enabled:
        print("❌ Azure Speech Services отключен")
        return
    
    print(f"Speech config language: {speech_service.speech_config.speech_recognition_language}")
    print(f"Speech config region: {speech_service.speech_config.region}")
    
    # Тестируем загрузку аудио по URL (симуляция)
    print("\n--- Тест загрузки аудио ---")
    test_url = "https://httpbin.org/bytes/1024"  # Простой тест загрузки
    
    try:
        audio_data = await speech_service.download_audio_file_by_url(test_url)
        if audio_data:
            print(f"✅ Загрузка аудио работает: {len(audio_data)} байт")
        else:
            print("❌ Загрузка аудио не работает")
    except Exception as e:
        print(f"❌ Ошибка при загрузке аудио: {e}")
    
    # Тестируем конвертацию аудио
    print("\n--- Тест конвертации аудио ---")
    try:
        # Создаем простой тестовый аудиофайл (1 секунда тишины)
        test_audio = b'\x52\x49\x46\x46\x24\x00\x00\x00\x57\x41\x56\x45\x66\x6d\x74\x20\x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00\x64\x61\x74\x61\x00\x00\x00\x00'
        
        wav_data = speech_service.convert_audio_format(test_audio, from_format="wav")
        if wav_data:
            print(f"✅ Конвертация аудио работает: {len(wav_data)} байт")
        else:
            print("❌ Конвертация аудио не работает")
    except Exception as e:
        print(f"❌ Ошибка при конвертации аудио: {e}")
    
    print("\n=== Тест завершен ===")
    print("\nДля полного тестирования отправьте голосовое сообщение в WhatsApp")

if __name__ == "__main__":
    asyncio.run(test_voice_recognition()) 