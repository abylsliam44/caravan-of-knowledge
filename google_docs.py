import os
import logging
from typing import Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class GoogleDocsService:
    def __init__(self):
        self.credentials = None
        self.service = None
        self.document_id = os.getenv("GOOGLE_DOCS_ID")
        self.service_account_email = os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL")
        self.private_key = os.getenv("GOOGLE_PRIVATE_KEY")
        
        if not self.document_id:
            logging.warning("GOOGLE_DOCS_ID not set, using default prompt only")
            return
            
        if not (self.service_account_email and self.private_key):
            logging.warning("Google credentials not set, using default prompt only")
            return
            
        self._authenticate()
    
    def _authenticate(self):
        """Аутентификация в Google API"""
        try:
            # Создаем credentials из переменных окружения
            self.credentials = service_account.Credentials.from_service_account_info({
                "type": "service_account",
                "project_id": os.getenv("GOOGLE_PROJECT_ID"),
                "private_key_id": os.getenv("GOOGLE_PRIVATE_KEY_ID"),
                "private_key": self.private_key,
                "client_email": self.service_account_email,
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": os.getenv("GOOGLE_CLIENT_X509_CERT_URL"),
                "universe_domain": "googleapis.com"
            }, scopes=['https://www.googleapis.com/auth/documents.readonly'])
            
            self.service = build('docs', 'v1', credentials=self.credentials)
            logging.info("Google Docs API authenticated successfully")
        except Exception as e:
            logging.error(f"Failed to authenticate with Google Docs API: {e}")
    
    def get_prompt_from_docs(self, is_first_message: bool = False) -> str:
        """Получает полный промпт: базовый + динамический контент из Google Docs"""
        # Базовый промпт (неизменяемый)
        base_prompt = self._get_base_prompt(is_first_message)
        
        # Динамический контент из Google Docs
        dynamic_content = self._get_dynamic_content()
        
        # Объединяем
        if dynamic_content:
            full_prompt = f"{base_prompt}\n\n{dynamic_content}"
            logging.info("Using hybrid prompt: base + dynamic content from Google Docs")
        else:
            full_prompt = base_prompt
            logging.info("Using base prompt only (no dynamic content)")
        
        return full_prompt
    
    def _get_base_prompt(self, is_first_message: bool = False) -> str:
        """Возвращает базовый промпт (неизменяемый)"""
        greeting_instruction = ""
        if is_first_message:
            greeting_instruction = """
ВАЖНО: Это первое сообщение от пользователя. Обязательно поприветствуйте его вежливо и представьтесь как менеджер Caravan of Knowledge."""
        else:
            greeting_instruction = """
ВАЖНО: Это НЕ первое сообщение от пользователя. НЕ приветствуйте его, отвечайте сразу по существу вопроса."""
        
        return f"""Вы - менеджер компании "Caravan of Knowledge", которая занимается продвижением STEAM-образования в Казахстане.

ВАШИ ОСНОВНЫЕ ПРАВИЛА:
- Всегда используйте формальное обращение "Вы" (с заглавной буквы)
- Придерживайтесь строго делового стиля без эмодзи
- Отвечайте кратко и по существу
- Приветствуйте пользователя ТОЛЬКО при первом сообщении в диалоге
- Избегайте длинных конструкций и лишних слов
- НЕ ОТВЕЧАЙТЕ на вопросы, не связанные с Caravan of Knowledge или STEAM-образованием
- Если вопрос не по теме - вежливо откажите и предложите задать профильный вопрос

ВАША РОЛЬ:
- Предоставлять информацию о программах STEAM-образования
- Отвечать на вопросы о курсах, мероприятиях и проектах компании
- Помогать потенциальным клиентам и партнерам
- Поддерживать профессиональный деловой стиль общения

О КОМПАНИИ:
- Название: Caravan of Knowledge
- Сфера деятельности: STEAM-образование в Казахстане
- Программы: курсы по науке, технологиям, инженерии, искусству и математике
- Целевая аудитория: студенты, преподаватели, образовательные учреждения

{greeting_instruction}

АКТУАЛЬНАЯ ИНФОРМАЦИЯ О МЕРОПРИЯТИЯХ И КУРСАХ:"""
    
    def _get_dynamic_content(self) -> str:
        """Получает динамический контент из Google Docs"""
        if not self.service or not self.document_id:
            return ""
        
        try:
            document = self.service.documents().get(documentId=self.document_id).execute()
            content = document.get('body', {}).get('content', [])
            
            # Извлекаем текст из документа
            text_parts = []
            for element in content:
                if 'paragraph' in element:
                    for para_element in element['paragraph']['elements']:
                        if 'textRun' in para_element:
                            text_parts.append(para_element['textRun']['content'])
            
            dynamic_content = ''.join(text_parts).strip()
            
            if dynamic_content:
                logging.info("Successfully retrieved dynamic content from Google Docs")
                return dynamic_content
            else:
                logging.warning("Empty dynamic content from Google Docs")
                return ""
                
        except HttpError as e:
            logging.error(f"Google Docs API error: {e}")
            return ""
        except Exception as e:
            logging.error(f"Error reading from Google Docs: {e}")
            return ""

# Глобальный экземпляр сервиса
google_docs_service = GoogleDocsService() 