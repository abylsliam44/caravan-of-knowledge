import re
from typing import List, Dict, Optional

class SmartContentFilter:
    """Умная фильтрация контента для больших документов"""
    
    def __init__(self):
        self.keywords = {
            "курсы": ["курс", "обучение", "программа", "тренинг"],
            "мероприятия": ["мероприятие", "событие", "фестиваль", "конференция"],
            "контакты": ["контакт", "телефон", "email", "адрес"],
            "сроки": ["дата", "срок", "начало", "конец", "длительность"],
            "статус": ["активен", "завершен", "планируется", "набор"]
        }
    
    def filter_content_by_topic(self, content: str, user_question: str) -> str:
        """Фильтрует контент по теме вопроса пользователя"""
        question_lower = user_question.lower()
        
        # Определяем тему вопроса
        relevant_topics = []
        for topic, keywords in self.keywords.items():
            if any(keyword in question_lower for keyword in keywords):
                relevant_topics.append(topic)
        
        # Если тема не определена, возвращаем весь контент
        if not relevant_topics:
            return content
        
        # Фильтруем контент по релевантным темам
        filtered_lines = []
        lines = content.split('\n')
        
        for line in lines:
            line_lower = line.lower()
            for topic in relevant_topics:
                if any(keyword in line_lower for keyword in self.keywords[topic]):
                    filtered_lines.append(line)
                    break
        
        return '\n'.join(filtered_lines) if filtered_lines else content
    
    def extract_table_data(self, content: str) -> List[Dict[str, str]]:
        """Извлекает данные из таблиц"""
        tables = []
        lines = content.split('\n')
        
        current_table = []
        for line in lines:
            # Простая логика определения таблицы
            if '|' in line and len(line.split('|')) > 2:
                current_table.append(line)
            elif current_table:
                # Конец таблицы
                if current_table:
                    tables.append(self._parse_table(current_table))
                current_table = []
        
        return tables
    
    def _parse_table(self, table_lines: List[str]) -> Dict[str, str]:
        """Парсит таблицу в структурированный формат"""
        if len(table_lines) < 2:
            return {}
        
        # Получаем заголовки
        headers = [h.strip() for h in table_lines[0].split('|') if h.strip()]
        
        # Получаем данные
        data = []
        for line in table_lines[1:]:
            cells = [cell.strip() for cell in line.split('|') if cell.strip()]
            if len(cells) == len(headers):
                row = dict(zip(headers, cells))
                data.append(row)
        
        return {"headers": headers, "data": data}
    
    def summarize_large_content(self, content: str, max_length: int = 5000) -> str:
        """Сокращает большой контент до разумного размера"""
        if len(content) <= max_length:
            return content
        
        # Приоритетные секции
        priority_keywords = ["активен", "набор", "новый", "важно", "срочно"]
        
        lines = content.split('\n')
        priority_lines = []
        other_lines = []
        
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in priority_keywords):
                priority_lines.append(line)
            else:
                other_lines.append(line)
        
        # Собираем результат
        result = []
        result.extend(priority_lines)
        
        # Добавляем остальные строки до лимита
        remaining_length = max_length - len('\n'.join(result))
        for line in other_lines:
            if len('\n'.join(result + [line])) <= max_length:
                result.append(line)
            else:
                break
        
        return '\n'.join(result) 