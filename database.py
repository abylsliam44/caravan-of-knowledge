import os
import logging
from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Base для моделей
Base = declarative_base()

# Модель для хранения сообщений
class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    phone_number = Column(String(50), index=True, nullable=False)
    role = Column(String(20), nullable=False)  # user или assistant
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'phone_number': self.phone_number,
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat()
        }

class Database:
    def __init__(self):
        """Инициализация подключения к PostgreSQL"""
        self.engine = None
        self.SessionLocal = None
        self.enabled = False
        
        database_url = os.getenv("DATABASE_URL")
        
        if not database_url:
            logging.warning("DATABASE_URL not set. PostgreSQL storage disabled.")
            return
        
        try:
            # Render дает postgres://, но SQLAlchemy нужен postgresql://
            if database_url.startswith("postgres://"):
                database_url = database_url.replace("postgres://", "postgresql://", 1)
            
            # Для Neon: добавляем connect_args для SSL
            connect_args = {}
            if "neon.tech" in database_url:
                connect_args = {
                    "connect_timeout": 10,
                    "options": "-c timezone=utc"
                }
            
            self.engine = create_engine(
                database_url, 
                pool_pre_ping=True,
                connect_args=connect_args,
                pool_size=5,
                max_overflow=10
            )
            self.SessionLocal = sessionmaker(bind=self.engine)
            
            # Создаем таблицы если их нет
            Base.metadata.create_all(self.engine)
            
            self.enabled = True
            logging.info("PostgreSQL connection established for chat history")
        except Exception as e:
            logging.error(f"Failed to connect to PostgreSQL: {e}")
            self.enabled = False
    
    def save_message(self, phone_number: str, role: str, content: str) -> bool:
        """Сохраняет сообщение в PostgreSQL"""
        if not self.enabled:
            return False
        
        try:
            session = self.SessionLocal()
            message = ChatMessage(
                phone_number=phone_number,
                role=role,
                content=content
            )
            session.add(message)
            session.commit()
            session.close()
            logging.info(f"Message saved to PostgreSQL for {phone_number}")
            return True
        except Exception as e:
            logging.error(f"Error saving message to PostgreSQL: {e}")
            if session:
                session.rollback()
                session.close()
            return False
    
    def get_chat_history(self, phone_number: str, limit: int = 100):
        """Получает историю чата из PostgreSQL"""
        if not self.enabled:
            return []
        
        try:
            session = self.SessionLocal()
            messages = session.query(ChatMessage)\
                .filter(ChatMessage.phone_number == phone_number)\
                .order_by(ChatMessage.timestamp.desc())\
                .limit(limit)\
                .all()
            session.close()
            
            # Возвращаем в обратном порядке (от старых к новым)
            return [msg.to_dict() for msg in reversed(messages)]
        except Exception as e:
            logging.error(f"Error getting chat history from PostgreSQL: {e}")
            if session:
                session.close()
            return []
    
    def get_all_chats(self):
        """Получает список всех чатов (номера телефонов)"""
        if not self.enabled:
            return []
        
        try:
            session = self.SessionLocal()
            # Получаем уникальные номера телефонов
            result = session.query(ChatMessage.phone_number)\
                .distinct()\
                .all()
            session.close()
            return [row[0] for row in result]
        except Exception as e:
            logging.error(f"Error getting all chats: {e}")
            if session:
                session.close()
            return []
    
    def delete_chat_history(self, phone_number: str) -> bool:
        """Удаляет историю чата из PostgreSQL"""
        if not self.enabled:
            return False
        
        try:
            session = self.SessionLocal()
            session.query(ChatMessage)\
                .filter(ChatMessage.phone_number == phone_number)\
                .delete()
            session.commit()
            session.close()
            logging.info(f"Deleted chat history from PostgreSQL for {phone_number}")
            return True
        except Exception as e:
            logging.error(f"Error deleting chat history: {e}")
            if session:
                session.rollback()
                session.close()
            return False

# Глобальный экземпляр
db = Database()

