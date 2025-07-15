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
        
        # Логируем для диагностики
        if dynamic_content:
            # Показываем первые 200 символов для проверки
            preview = dynamic_content[:200] + "..." if len(dynamic_content) > 200 else dynamic_content
            logging.info(f"Dynamic content preview: {preview}")
            logging.info(f"Dynamic content length: {len(dynamic_content)} characters")
            
            full_prompt = f"{base_prompt}\n\n{dynamic_content}"
            logging.info("Using hybrid prompt: base + dynamic content from Google Docs")
        else:
            full_prompt = base_prompt
            logging.warning("Using base prompt only (no dynamic content from Google Docs)")
        
        return full_prompt
    
    def _get_base_prompt(self, is_first_message: bool = False) -> str:
        """Возвращает базовый промпт (неизменяемый)"""
        
        # Инструкции для первого сообщения
        if is_first_message:
            greeting_instruction = """
ВАЖНО: Это первое сообщение от пользователя в диалоге. 
- НЕ представляйтесь и НЕ используйте фразы типа "[Ваше Имя]" или "менеджер Caravan of Knowledge"
- Отвечайте сразу по существу вопроса пользователя
- Будьте вежливы и профессиональны, но без лишних представлений
- Если пользователь задал конкретный вопрос - отвечайте на него
- Если пользователь просто поздоровался - кратко поприветствуйте и спросите, чем можете помочь"""
        else:
            greeting_instruction = """
ВАЖНО: Это НЕ первое сообщение от пользователя. 
- НЕ приветствуйте его заново и НЕ представляйтесь повторно
- Отвечайте сразу по существу вопроса, учитывая контекст предыдущих сообщений
- Если пользователь продолжает предыдущую тему - развивайте её
- Если задает новый вопрос - отвечайте на него, но помните о контексте диалога"""
        
        return f"""Вы - опытный менеджер компании "Caravan of Knowledge", которая занимается продвижением STEAM-образования в Казахстане.

ВАШИ ОСНОВНЫЕ ПРАВИЛА ОБЩЕНИЯ:
- Всегда используйте формальное обращение "Вы" (с заглавной буквы)
- Придерживайтесь делового, но дружелюбного стиля общения
- Отвечайте кратко, четко и по существу
- НЕ представляйтесь и НЕ используйте фразы типа "[Ваше Имя]" или "менеджер Caravan of Knowledge"
- Избегайте длинных конструкций и лишних слов
- Будьте вежливы и профессиональны во всех ответах
- Поддерживайте общение на русском и казахском языках
- Если пользователь пишет на казахском - отвечайте на казахском
- Если пользователь пишет на русском - отвечайте на русском

ПРАВИЛА РАБОТЫ С КОНТЕКСТОМ:
- ВАЖНО: Учитывайте контекст всего диалога - помните предыдущие сообщения
- Не повторяйте информацию, которую уже обсуждали в диалоге
- Если пользователь ссылается на предыдущие сообщения - обязательно учитывайте этот контекст
- Если пользователь продолжает тему - развивайте её, не начинайте с нуля
- Если задается новый вопрос - отвечайте на него, но помните о контексте диалога
- Используйте местоимения "этот", "тот", "вышеупомянутый" для ссылок на предыдущую информацию

ПРАВИЛА ОТВЕТОВ:
- НЕ ОТВЕЧАЙТЕ на вопросы, не связанные с Caravan of Knowledge или STEAM-образованием
- Если вопрос не по теме - вежливо откажите и предложите задать профильный вопрос
- Если информации недостаточно - честно скажите об этом и предложите уточнить детали
- Если нужно время для поиска информации - сообщите об этом

ВАША РОЛЬ:
- Предоставлять информацию о программах STEAM-образования
- Отвечать на вопросы о курсах, мероприятиях и проектах компании
- Помогать потенциальным клиентам и партнерам
- Поддерживать профессиональный деловой стиль общения
- Вести естественный диалог с учетом всей истории разговора
- Быть полезным и информативным собеседником

О КОМПАНИИ:
- Название: Caravan of Knowledge
- Сфера деятельности: STEAM-образование в Казахстане
- Программы: курсы по науке, технологиям, инженерии, искусству и математике
- Целевая аудитория: студенты, преподаватели, образовательные учреждения

{greeting_instruction}

ПРИМЕРЫ ХОРОШЕГО ОБЩЕНИЯ С КОНТЕКСТОМ:

1. Если пользователь спрашивает "Сколько стоит?" после того, как вы уже назвали цену:
   ❌ "Курс стоит 150,000 тенге"
   ✅ "Как я уже упоминал, стоимость составляет 150,000 тенге"

2. Если пользователь продолжает тему:
   ❌ "У нас есть курсы по программированию..."
   ✅ "Продолжая тему программирования, курс Python включает..."

3. Если пользователь ссылается на предыдущую информацию:
   ❌ "У нас есть курсы для детей"
   ✅ "Да, как я говорил, у нас есть специальные программы для детей"

4. Если пользователь задает новый вопрос в рамках диалога:
   ✅ "Что касается времени начала курса, следующий набор..."

ПОМНИТЕ: Всегда учитывайте, что было сказано ранее в диалоге!

АКТУАЛЬНАЯ ИНФОРМАЦИЯ О МЕРОПРИЯТИЯХ И КУРСАХ:"""
    
    def _get_dynamic_content(self) -> str:
        """Получает динамический контент из Google Docs"""
        if not self.service or not self.document_id:
            return ""
        
        try:
            document = self.service.documents().get(documentId=self.document_id).execute()
            content = document.get('body', {}).get('content', [])
            
            # Извлекаем текст из документа, включая таблицы
            text_parts = []
            
            for element in content:
                # Обрабатываем обычные параграфы
                if 'paragraph' in element:
                    for para_element in element['paragraph']['elements']:
                        if 'textRun' in para_element:
                            text_parts.append(para_element['textRun']['content'])
                
                # Обрабатываем таблицы
                elif 'table' in element:
                    table_content = self._extract_table_content(element['table'])
                    if table_content:
                        text_parts.append(table_content)
                        logging.info("Successfully extracted table content from Google Docs")
            
            dynamic_content = ''.join(text_parts).strip()
            
            if dynamic_content:
                logging.info(f"Successfully retrieved dynamic content from Google Docs: {len(dynamic_content)} characters")
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
    
    def _extract_table_content(self, table) -> str:
        """Извлекает содержимое таблицы в читаемом формате"""
        try:
            table_content = []
            
            # Обрабатываем каждую строку таблицы
            for row in table.get('tableRows', []):
                row_content = []
                
                # Обрабатываем каждую ячейку в строке
                for cell in row.get('tableCells', []):
                    cell_text = ""
                    
                    # Извлекаем текст из ячейки
                    for content_element in cell.get('content', []):
                        if 'paragraph' in content_element:
                            for para_element in content_element['paragraph'].get('elements', []):
                                if 'textRun' in para_element:
                                    cell_text += para_element['textRun']['content']
                    
                    # Очищаем текст от лишних пробелов
                    cell_text = cell_text.strip()
                    if cell_text:
                        row_content.append(cell_text)
                
                # Объединяем ячейки строки
                if row_content:
                    table_content.append(" | ".join(row_content))
            
            # Объединяем все строки таблицы
            if table_content:
                return "\n".join(table_content) + "\n\n"
            
            return ""
            
        except Exception as e:
            logging.error(f"Error extracting table content: {e}")
            return ""

# Глобальный экземпляр сервиса
google_docs_service = GoogleDocsService()

# Метод для тестирования подключения
def test_google_docs_connection():
    """Тестирует подключение к Google Docs и показывает содержимое"""
    try:
        if not google_docs_service.service:
            print("❌ Google Docs service not initialized")
            return
        
        if not google_docs_service.document_id:
            print("❌ GOOGLE_DOCS_ID not set")
            return
        
        print(f"✅ Testing connection to document: {google_docs_service.document_id}")
        
        # Получаем содержимое документа
        content = google_docs_service._get_dynamic_content()
        
        if content:
            print(f"✅ Successfully retrieved content ({len(content)} characters)")
            print("📄 Content preview:")
            print("-" * 50)
            print(content[:500] + "..." if len(content) > 500 else content)
            print("-" * 50)
        else:
            print("❌ No content retrieved from document")
            
    except Exception as e:
        print(f"❌ Error testing Google Docs connection: {e}")

if __name__ == "__main__":
    test_google_docs_connection() 