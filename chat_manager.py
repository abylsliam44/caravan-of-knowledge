#!/usr/bin/env python3
"""
Утилита для управления историей чатов WhatsApp AI Bot
"""

import argparse
import json
from chat_memory import chat_memory
import logging

logging.basicConfig(level=logging.INFO)

def list_active_chats():
    """Показывает список активных чатов"""
    print("=== АКТИВНЫЕ ЧАТЫ ===")
    
    if chat_memory.redis_client:
        # Получаем все ключи чатов из Redis
        keys = chat_memory.redis_client.keys("chat_history:*")
        if not keys:
            print("Активных чатов не найдено")
            return
        
        for key in keys:
            phone_number = key.replace("chat_history:", "")
            history = chat_memory.get_chat_history(phone_number)
            print(f"📱 {phone_number}: {len(history)} сообщений")
    else:
        # In-memory storage
        if not chat_memory._in_memory_storage:
            print("Активных чатов не найдено")
            return
        
        for phone_number, history in chat_memory._in_memory_storage.items():
            print(f"📱 {phone_number}: {len(history)} сообщений")

def show_chat_history(phone_number: str):
    """Показывает историю конкретного чата"""
    print(f"=== ИСТОРИЯ ЧАТА: {phone_number} ===")
    
    history = chat_memory.get_chat_history(phone_number)
    if not history:
        print("История чата пуста")
        return
    
    for i, msg in enumerate(history, 1):
        role = "👤 Пользователь" if msg["role"] == "user" else "🤖 Бот"
        timestamp = msg.get("timestamp", "N/A")
        content = msg["content"]
        
        print(f"\n{i}. {role} ({timestamp})")
        print(f"   {content}")

def clear_chat_history(phone_number: str):
    """Очищает историю конкретного чата"""
    print(f"Очищаю историю чата: {phone_number}")
    chat_memory.clear_chat_history(phone_number)
    print("✅ История чата очищена")

def clear_all_chats():
    """Очищает все чаты"""
    print("Очищаю все чаты...")
    
    if chat_memory.redis_client:
        keys = chat_memory.redis_client.keys("chat_history:*")
        for key in keys:
            phone_number = key.replace("chat_history:", "")
            chat_memory.clear_chat_history(phone_number)
    else:
        for phone_number in list(chat_memory._in_memory_storage.keys()):
            chat_memory.clear_chat_history(phone_number)
    
    print("✅ Все чаты очищены")

def show_chat_summary(phone_number: str):
    """Показывает краткое описание чата"""
    print(f"=== КРАТКОЕ ОПИСАНИЕ ЧАТА: {phone_number} ===")
    summary = chat_memory.get_chat_summary(phone_number)
    print(summary)

def main():
    parser = argparse.ArgumentParser(description="Утилита управления историей чатов WhatsApp AI Bot")
    parser.add_argument("action", choices=["list", "show", "clear", "clear-all", "summary"], 
                       help="Действие для выполнения")
    parser.add_argument("--phone", "-p", help="Номер телефона для операций")
    
    args = parser.parse_args()
    
    if args.action == "list":
        list_active_chats()
    
    elif args.action == "show":
        if not args.phone:
            print("❌ Необходимо указать номер телефона: --phone <номер>")
            return
        show_chat_history(args.phone)
    
    elif args.action == "clear":
        if not args.phone:
            print("❌ Необходимо указать номер телефона: --phone <номер>")
            return
        clear_chat_history(args.phone)
    
    elif args.action == "clear-all":
        confirm = input("⚠️  Вы уверены, что хотите очистить ВСЕ чаты? (y/N): ")
        if confirm.lower() == 'y':
            clear_all_chats()
        else:
            print("❌ Операция отменена")
    
    elif args.action == "summary":
        if not args.phone:
            print("❌ Необходимо указать номер телефона: --phone <номер>")
            return
        show_chat_summary(args.phone)

if __name__ == "__main__":
    main() 