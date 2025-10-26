"""
AI Agent с OpenAI Function Calling
Автономный агент который сам решает какие инструменты использовать
"""
import os
import logging
import httpx
import json
from typing import Dict, Any, List, Optional
from agent_tools import AGENT_TOOLS, execute_tool
from google_docs import google_docs_service
from chat_memory import chat_memory

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPEN_AI_KEY") or os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
USE_AI_AGENT = os.getenv("USE_AI_AGENT", "true").lower() == "true"


class AIAgent:
    """
    Автономный AI-агент с Function Calling
    """
    
    def __init__(self):
        self.api_key = OPENAI_API_KEY
        self.model = OPENAI_MODEL
        self.tools = AGENT_TOOLS
        self.enabled = USE_AI_AGENT and bool(self.api_key)
        
        if not self.enabled:
            logger.warning("AI Agent disabled (set USE_AI_AGENT=true and OPEN_AI_KEY)")
        else:
            logger.info(f"AI Agent initialized with {len(self.tools)} tools")
    
    async def process_message(
        self, 
        user_message: str, 
        phone_number: str,
        is_first_message: bool = False
    ) -> str:
        """
        Обрабатывает сообщение пользователя через AI Agent
        
        Агент может:
        - Искать в базе знаний
        - Регистрировать студентов
        - Уведомлять менеджеров
        - Отвечать на вопросы
        """
        
        if not self.enabled:
            # Fallback на обычный GPT без агента
            logger.info("AI Agent disabled, using simple GPT")
            from gpt import ask_gpt
            return await ask_gpt(user_message, phone_number, is_first_message)
        
        try:
            # Получаем системный промпт
            system_prompt = google_docs_service.get_prompt_from_docs(is_first_message)
            
            # Добавляем инструкции для агента
            agent_instructions = """

ВАЖНО - ВЫ АВТОНОМНЫЙ AI-АГЕНТ С ИНСТРУМЕНТАМИ:

У вас есть доступ к следующим инструментам (functions):

1. search_knowledge_base(query) - поиск информации о курсах, ценах, расписании
   Используйте ВСЕГДА когда нужна конкретная информация о курсах!

2. register_student(name, phone, course, comment) - регистрация студента на курс
   Используйте когда пользователь хочет записаться или зарегистрироваться

3. notify_manager(message, priority, user_phone) - уведомление менеджера в WhatsApp
   Используйте при жалобах, сложных вопросах или важных ситуациях
   Priority: "low", "medium", "high"

4. get_current_date() - получить текущую дату и время
   Используйте когда нужна актуальная дата

ПРАВИЛА ИСПОЛЬЗОВАНИЯ ИНСТРУМЕНТОВ:
- Если пользователь спрашивает о курсах/ценах/расписании → search_knowledge_base()
- Если пользователь хочет записаться → register_student()
- Если жалоба или сложный вопрос → notify_manager()
- Можно использовать несколько инструментов последовательно

ВАЖНО: Сначала используйте инструменты, ПОТОМ формулируйте ответ на основе результатов!
"""
            
            full_system_prompt = system_prompt + agent_instructions
            
            # Получаем историю чата
            chat_history = chat_memory.get_messages_for_gpt(phone_number)
            
            # Формируем сообщения
            messages = [{"role": "system", "content": full_system_prompt}]
            
            if chat_history:
                messages.extend(chat_history)
            
            messages.append({"role": "user", "content": user_message})
            
            # Запускаем агента
            response = await self._run_agent_loop(messages, phone_number)
            
            # Сохраняем в историю
            chat_memory.add_message(phone_number, "user", user_message)
            chat_memory.add_message(phone_number, "assistant", response)
            
            return response
            
        except Exception as e:
            logger.error(f"AI Agent error: {e}", exc_info=True)
            return f"Извините, произошла ошибка обработки. Попробуйте позже."
    
    async def _run_agent_loop(
        self, 
        messages: List[Dict[str, str]], 
        phone_number: str,
        max_iterations: int = 5
    ) -> str:
        """
        Главный цикл агента с Function Calling
        
        Агент может вызывать инструменты несколько раз подряд
        """
        
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        current_messages = messages.copy()
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Agent iteration {iteration}/{max_iterations}")
            
            # Запрос к OpenAI с tools
            data = {
                "model": self.model,
                "messages": current_messages,
                "tools": self.tools,
                "tool_choice": "auto",  # GPT сам решает нужны ли инструменты
                "temperature": 0.7
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=headers, json=data)
                
                if response.status_code != 200:
                    logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                    return "Извините, сервис временно недоступен."
                
                result = response.json()
                assistant_message = result["choices"][0]["message"]
                
                # Добавляем ответ ассистента в историю
                current_messages.append(assistant_message)
                
                # Проверяем нужно ли вызывать инструменты
                tool_calls = assistant_message.get("tool_calls")
                
                if not tool_calls:
                    # Агент решил что инструменты не нужны, возвращаем финальный ответ
                    final_response = assistant_message.get("content", "")
                    logger.info(f"Agent finished in {iteration} iterations")
                    return final_response
                
                # Выполняем вызовы инструментов
                logger.info(f"Agent calling {len(tool_calls)} tools")
                
                for tool_call in tool_calls:
                    tool_name = tool_call["function"]["name"]
                    tool_args = json.loads(tool_call["function"]["arguments"])
                    tool_id = tool_call["id"]
                    
                    logger.info(f"Calling tool: {tool_name} with args: {tool_args}")
                    
                    # Добавляем user_phone если это notify_manager
                    if tool_name == "notify_manager" and "user_phone" not in tool_args:
                        tool_args["user_phone"] = phone_number
                    
                    # Выполняем инструмент
                    tool_result = await execute_tool(tool_name, tool_args)
                    
                    # Добавляем результат в сообщения
                    current_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "name": tool_name,
                        "content": json.dumps(tool_result, ensure_ascii=False)
                    })
                    
                    logger.info(f"Tool {tool_name} executed: {tool_result.get('success')}")
        
        # Если достигли максимума итераций
        logger.warning(f"Agent reached max iterations ({max_iterations})")
        return "Обрабатываю ваш запрос, но это занимает больше времени чем ожидалось. Попробуйте уточнить вопрос."


# Глобальный экземпляр агента
ai_agent = AIAgent()

