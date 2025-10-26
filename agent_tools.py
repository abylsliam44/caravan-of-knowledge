"""
AI Agent Tools - Инструменты для автономного агента
"""
import os
import logging
from typing import Dict, Any, Optional
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)

# ==================== TOOL DEFINITIONS ====================

AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Ищет информацию в базе знаний Google Docs о курсах, ценах, расписании",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Поисковый запрос (например: 'цена курса Python', 'расписание STEAM')"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "register_student",
            "description": "Регистрирует студента на курс в Notion. Используй когда пользователь хочет записаться.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Имя студента"
                    },
                    "phone": {
                        "type": "string",
                        "description": "Номер телефона студента"
                    },
                    "course": {
                        "type": "string",
                        "description": "Название курса"
                    },
                    "comment": {
                        "type": "string",
                        "description": "Дополнительный комментарий"
                    }
                },
                "required": ["name", "phone", "course"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "notify_manager",
            "description": "Отправляет уведомление менеджеру в WhatsApp при сложном вопросе или жалобе",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Текст уведомления для менеджера"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Приоритет уведомления"
                    },
                    "user_phone": {
                        "type": "string",
                        "description": "Номер телефона пользователя (для контекста)"
                    }
                },
                "required": ["message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_date",
            "description": "Получает текущую дату и время",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

# ==================== TOOL IMPLEMENTATIONS ====================

async def search_knowledge_base(query: str) -> Dict[str, Any]:
    """
    Поиск в базе знаний Google Docs
    """
    try:
        from google_docs import google_docs_service
        
        # Получаем содержимое из Google Docs
        content = google_docs_service._get_dynamic_content()
        
        if not content:
            return {
                "success": False,
                "error": "База знаний недоступна"
            }
        
        # Простой поиск по ключевым словам
        query_lower = query.lower()
        lines = content.split('\n')
        relevant_lines = []
        
        for i, line in enumerate(lines):
            if any(word in line.lower() for word in query_lower.split()):
                # Берем контекст: строку до, саму строку, строку после
                context_start = max(0, i - 1)
                context_end = min(len(lines), i + 2)
                relevant_lines.extend(lines[context_start:context_end])
        
        if relevant_lines:
            result = '\n'.join(set(relevant_lines))[:500]  # Ограничение
            logger.info(f"Found knowledge: {result[:100]}...")
            return {
                "success": True,
                "result": result,
                "query": query
            }
        else:
            return {
                "success": True,
                "result": "Информация не найдена в базе знаний",
                "query": query
            }
            
    except Exception as e:
        logger.error(f"Error searching knowledge base: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def register_student(name: str, phone: str, course: str, comment: str = "") -> Dict[str, Any]:
    """
    Регистрация студента в Notion
    """
    try:
        notion_token = os.getenv("NOTION_TOKEN")
        notion_database_id = os.getenv("NOTION_DATABASE_ID")
        
        if not (notion_token and notion_database_id):
            logger.warning("Notion credentials not set")
            return {
                "success": False,
                "error": "Notion не настроен (добавьте NOTION_TOKEN и NOTION_DATABASE_ID)"
            }
        
        # Notion API request
        url = "https://api.notion.com/v1/pages"
        headers = {
            "Authorization": f"Bearer {notion_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        data = {
            "parent": {"database_id": notion_database_id},
            "properties": {
                "Name": {
                    "title": [{"text": {"content": name}}]
                },
                "Phone": {
                    "phone_number": phone
                },
                "Course": {
                    "rich_text": [{"text": {"content": course}}]
                },
                "Comment": {
                    "rich_text": [{"text": {"content": comment}}]
                },
                "Date": {
                    "date": {"start": datetime.now().isoformat()}
                }
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=data, timeout=10.0)
            
            if response.status_code == 200:
                logger.info(f"Student registered in Notion: {name}")
                return {
                    "success": True,
                    "result": f"Студент {name} успешно зарегистрирован на курс '{course}'",
                    "notion_id": response.json().get("id")
                }
            else:
                logger.error(f"Notion API error: {response.status_code}")
                return {
                    "success": False,
                    "error": f"Ошибка Notion API: {response.status_code}"
                }
                
    except Exception as e:
        logger.error(f"Error registering student: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def notify_manager(message: str, priority: str = "medium", user_phone: str = "") -> Dict[str, Any]:
    """
    Отправка уведомления менеджеру в WhatsApp
    """
    try:
        from whatsapp import send_whatsapp_message
        
        manager_phone = os.getenv("MANAGER_PHONE_NUMBER")
        
        if not manager_phone:
            logger.warning("MANAGER_PHONE_NUMBER not set")
            return {
                "success": False,
                "error": "Номер менеджера не настроен (добавьте MANAGER_PHONE_NUMBER)"
            }
        
        priority_emoji = {
            "low": "ℹ️",
            "medium": "⚠️",
            "high": "🚨"
        }
        
        emoji = priority_emoji.get(priority, "📌")
        
        # Формируем сообщение для менеджера
        full_message = f"{emoji} *{priority.upper()} PRIORITY*\n\n"
        full_message += f"*Сообщение:* {message}\n\n"
        
        if user_phone:
            full_message += f"*От пользователя:* {user_phone}\n"
        
        full_message += f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Отправляем через WhatsApp API
        result = await send_whatsapp_message(manager_phone, full_message)
        
        if result.get("status") == "success":
            logger.info(f"Manager notified via WhatsApp: {priority}")
            return {
                "success": True,
                "result": "Менеджер уведомлен в WhatsApp"
            }
        else:
            return {
                "success": False,
                "error": f"WhatsApp API error: {result.get('error')}"
            }
                
    except Exception as e:
        logger.error(f"Error notifying manager: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def get_current_date() -> Dict[str, Any]:
    """
    Получает текущую дату и время
    """
    try:
        now = datetime.now()
        return {
            "success": True,
            "result": now.strftime("%Y-%m-%d %H:%M:%S"),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "day_of_week": now.strftime("%A")
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ==================== TOOL EXECUTOR ====================

TOOL_FUNCTIONS = {
    "search_knowledge_base": search_knowledge_base,
    "register_student": register_student,
    "notify_manager": notify_manager,
    "get_current_date": get_current_date
}


async def execute_tool(tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Выполняет инструмент агента
    """
    logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
    
    if tool_name not in TOOL_FUNCTIONS:
        return {
            "success": False,
            "error": f"Unknown tool: {tool_name}"
        }
    
    try:
        result = await TOOL_FUNCTIONS[tool_name](**tool_args)
        logger.info(f"Tool {tool_name} result: {result}")
        return result
    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        return {
            "success": False,
            "error": str(e)
        }

