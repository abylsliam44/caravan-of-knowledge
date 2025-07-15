import re
from typing import Literal

def detect_language(text: str) -> Literal["kk", "ru", "en"]:
    """
    Простая функция определения языка на основе символов
    """
    if not text:
        return "ru"  # По умолчанию русский
    
    # Казахские специфические символы
    kazakh_chars = set("әғқңөұүіһ")
    
    # Английские символы
    english_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
    
    # Подсчитываем символы
    kazakh_count = sum(1 for char in text if char in kazakh_chars)
    english_count = sum(1 for char in text if char in english_chars)
    
    # Если есть казахские символы - казахский
    if kazakh_count > 0:
        return "kk"
    
    # Если много английских символов - английский
    if english_count > len(text) * 0.7:
        return "en"
    
    # По умолчанию русский
    return "ru"

def get_speech_language_code(language: Literal["kk", "ru", "en"]) -> str:
    """
    Возвращает код языка для Azure Speech Services
    """
    language_codes = {
        "kk": "kk-KZ",  # Казахский
        "ru": "ru-RU",  # Русский
        "en": "en-US"   # Английский
    }
    return language_codes.get(language, "ru-RU")

def get_language_name(language: Literal["kk", "ru", "en"]) -> str:
    """
    Возвращает название языка
    """
    names = {
        "kk": "қазақша",
        "ru": "русский", 
        "en": "English"
    }
    return names.get(language, "русский") 