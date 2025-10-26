import json
import logging
from typing import List, Dict, Optional
import redis
import os
from datetime import datetime
from database import db  # PostgreSQL для долгосрочного хранения

class ChatMemory:
    def __init__(self):
        """Инициализация системы памяти чатов"""
        self.redis_client = None
        # Максимальное количество сообщений (можно увеличить до 50-100)
        self.max_messages_per_chat = int(os.getenv("MAX_CHAT_HISTORY", "20"))
        
        # Подключение к Redis
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()  # Проверка подключения
            logging.info("Redis connection established for chat memory")
        except Exception as e:
            logging.warning(f"Redis connection failed: {e}. Using in-memory storage.")
            self.redis_client = None
            self._in_memory_storage = {}
    
    def _get_chat_key(self, phone_number: str) -> str:
        """Генерирует ключ для хранения истории чата"""
        return f"chat_history:{phone_number}"
    
    def add_message(self, phone_number: str, role: str, content: str) -> None:
        """Добавляет сообщение в историю чата"""
        try:
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat()
            }
            
            if self.redis_client:
                # Используем Redis
                chat_key = self._get_chat_key(phone_number)
                history = self.get_chat_history(phone_number)
                history.append(message)
                
                # Ограничиваем количество сообщений
                if len(history) > self.max_messages_per_chat:
                    history = history[-self.max_messages_per_chat:]
                
                # TTL настраивается через env (по умолчанию 7 дней)
                ttl_seconds = int(os.getenv("CHAT_HISTORY_TTL", "604800"))  # 7 дней
                self.redis_client.setex(
                    chat_key, 
                    ttl_seconds,
                    json.dumps(history, ensure_ascii=False)
                )
            else:
                # Используем in-memory storage
                if phone_number not in self._in_memory_storage:
                    self._in_memory_storage[phone_number] = []
                
                self._in_memory_storage[phone_number].append(message)
                
                # Ограничиваем количество сообщений
                if len(self._in_memory_storage[phone_number]) > self.max_messages_per_chat:
                    self._in_memory_storage[phone_number] = self._in_memory_storage[phone_number][-self.max_messages_per_chat:]
            
            logging.info(f"Added message to Redis for {phone_number}")
            
            # ПАРАЛЛЕЛЬНО сохраняем в PostgreSQL для долгосрочного хранения
            if db.enabled:
                db.save_message(phone_number, role, content)
            
        except Exception as e:
            logging.error(f"Error adding message to chat history: {e}")
    
    def get_chat_history(self, phone_number: str) -> List[Dict]:
        """Получает историю чата"""
        try:
            if self.redis_client:
                # Получаем из Redis
                chat_key = self._get_chat_key(phone_number)
                history_json = self.redis_client.get(chat_key)
                
                if history_json:
                    return json.loads(history_json)
                else:
                    return []
            else:
                # Получаем из in-memory storage
                return self._in_memory_storage.get(phone_number, [])
                
        except Exception as e:
            logging.error(f"Error getting chat history: {e}")
            return []
    
    def get_messages_for_gpt(self, phone_number: str) -> List[Dict]:
        """Получает сообщения в формате для GPT API"""
        history = self.get_chat_history(phone_number)
        
        # Преобразуем в формат для GPT
        messages = []
        for msg in history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        return messages
    
    def clear_chat_history(self, phone_number: str) -> None:
        """Очищает историю чата"""
        try:
            if self.redis_client:
                chat_key = self._get_chat_key(phone_number)
                self.redis_client.delete(chat_key)
            else:
                if phone_number in self._in_memory_storage:
                    del self._in_memory_storage[phone_number]
            
            logging.info(f"Cleared chat history for {phone_number}")
            
        except Exception as e:
            logging.error(f"Error clearing chat history: {e}")
    
    def get_chat_summary(self, phone_number: str) -> str:
        """Получает краткое описание контекста чата"""
        history = self.get_chat_history(phone_number)
        
        if not history:
            return "Новый диалог"
        
        # Анализируем последние сообщения для создания контекста
        recent_messages = history[-5:]  # Последние 5 сообщений
        
        context_parts = []
        for msg in recent_messages:
            role = "Пользователь" if msg["role"] == "user" else "Бот"
            content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
            context_parts.append(f"{role}: {content}")
        
        return f"Контекст: {' | '.join(context_parts)}"
    
    def is_first_message(self, phone_number: str) -> bool:
        """Проверяет, является ли это первым сообщением в чате"""
        history = self.get_chat_history(phone_number)
        return len(history) == 0
    
    def get_full_history_from_db(self, phone_number: str, limit: int = 1000) -> List[Dict]:
        """Получает ПОЛНУЮ историю из PostgreSQL (для аналитики, экспорта)"""
        if db.enabled:
            return db.get_chat_history(phone_number, limit)
        else:
            logging.warning("PostgreSQL not available, returning Redis history only")
            return self.get_chat_history(phone_number)
    
    def get_all_chat_numbers(self) -> List[str]:
        """Получает список всех номеров телефонов с которыми были диалоги"""
        if db.enabled:
            return db.get_all_chats()
        else:
            # Fallback на Redis (только активные чаты)
            if self.redis_client:
                keys = self.redis_client.keys("chat_history:*")
                return [key.replace("chat_history:", "") for key in keys]
            else:
                return list(self._in_memory_storage.keys())

# Глобальный экземпляр системы памяти
chat_memory = ChatMemory() 