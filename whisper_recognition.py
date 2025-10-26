import os
import asyncio
import aiohttp
import logging
from typing import Optional
from pydub import AudioSegment
import tempfile
import io

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Поддержка обоих форматов: OPEN_AI_KEY и OPENAI_API_KEY
OPENAI_API_KEY = os.getenv("OPEN_AI_KEY") or os.getenv("OPENAI_API_KEY")

logger.info(f"OPENAI_API_KEY: {'SET' if OPENAI_API_KEY else 'NOT SET'}")

class WhisperRecognitionService:
    def __init__(self):
        self.api_key = OPENAI_API_KEY
        
        if not self.api_key:
            logger.warning("OpenAI API key not found. Speech recognition will be disabled.")
            self.enabled = False
        else:
            self.enabled = True
            logger.info("Whisper API initialized successfully")
    
    def convert_audio_format(self, audio_data: bytes, from_format: Optional[str] = None) -> Optional[bytes]:
        """Конвертирует аудио в формат MP3 для Whisper API"""
        temp_input_path = None
        try:
            # Определяем формат, если не указан явно
            if not from_format:
                # Пытаемся определить формат по первым байтам
                if audio_data.startswith(b'OggS'):
                    from_format = "ogg"
                elif audio_data.startswith(b'ID3') or audio_data.startswith(b'\xff\xfb'):
                    from_format = "mp3"
                elif audio_data.startswith(b'RIFF'):
                    from_format = "wav"
                else:
                    from_format = "ogg"  # Fall back to ogg
            
            # Исправляем формат для ffmpeg
            if from_format == "oga":
                from_format = "ogg"
            elif from_format == "opus":
                from_format = "ogg"

            logger.info(f"Converting audio from format: {from_format}, size: {len(audio_data)} bytes")

            # Создаем временный файл для конвертации
            with tempfile.NamedTemporaryFile(suffix=f".{from_format}", delete=False) as temp_input:
                temp_input.write(audio_data)
                temp_input_path = temp_input.name
            
            logger.info(f"Created temporary input file: {temp_input_path}")
            
            # Конвертируем в MP3
            audio = AudioSegment.from_file(temp_input_path, format=from_format)
            logger.info(f"Audio loaded: duration={len(audio)}ms, channels={audio.channels}, frame_rate={audio.frame_rate}")
            
            # Экспортируем в MP3 с оптимальными параметрами
            output_buffer = io.BytesIO()
            audio.export(output_buffer, format="mp3", bitrate="128k")
            mp3_data = output_buffer.getvalue()
            
            logger.info(f"Converted audio to MP3: {len(mp3_data)} bytes")
            return mp3_data
            
        except Exception as e:
            logger.error(f"Error converting audio format: {e}", exc_info=True)
            return None
        finally:
            # Удаляем временный файл
            if temp_input_path and os.path.exists(temp_input_path):
                try:
                    os.unlink(temp_input_path)
                    logger.info(f"Cleaned up temporary input file: {temp_input_path}")
                except Exception as e:
                    logger.error(f"Error cleaning up temporary input file: {e}")

    async def download_audio_file_by_url(self, download_url: str) -> Optional[bytes]:
        """Скачивает аудиофайл по прямой ссылке (используется для Green API)."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(download_url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to download audio from URL: {response.status}")
                        return None
                    audio_data = await response.read()
                    logger.info(f"Downloaded audio via URL: {len(audio_data)} bytes")
                    return audio_data
        except Exception as e:
            logger.error(f"Error downloading audio by URL: {e}")
            return None

    async def recognize_speech(self, audio_data: bytes, language: str = "ru") -> Optional[str]:
        """Распознает речь через Whisper API
        
        Args:
            audio_data: Аудио данные в MP3 формате
            language: Код языка (ru, kk, en)
        """
        if not self.enabled:
            logger.warning("Speech recognition is disabled")
            return None
        
        try:
            url = "https://api.openai.com/v1/audio/transcriptions"
            
            # Создаем временный файл для отправки
            temp_file_path = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                    temp_file.write(audio_data)
                    temp_file_path = temp_file.name
                
                logger.info(f"Created temporary audio file for Whisper: {temp_file_path}")
                
                # Формируем multipart данные
                async with aiohttp.ClientSession() as session:
                    with open(temp_file_path, 'rb') as audio_file:
                        form_data = aiohttp.FormData()
                        form_data.add_field('file', audio_file, filename='audio.mp3', content_type='audio/mpeg')
                        form_data.add_field('model', 'whisper-1')
                        form_data.add_field('language', language)  # ru, kk, en
                        
                        headers = {
                            "Authorization": f"Bearer {self.api_key}"
                        }
                        
                        logger.info(f"Sending audio to Whisper API with language: {language}")
                        
                        async with session.post(url, headers=headers, data=form_data, timeout=30) as response:
                            logger.info(f"Whisper API response status: {response.status}")
                            
                            if response.status == 200:
                                result = await response.json()
                                recognized_text = result.get('text', '').strip()
                                logger.info(f"Whisper recognition successful: {recognized_text}")
                                return recognized_text
                            else:
                                response_text = await response.text()
                                logger.error(f"Whisper API request failed: {response.status}, response: {response_text}")
                                return None
            finally:
                # Удаляем временный файл
                if temp_file_path and os.path.exists(temp_file_path):
                    try:
                        os.unlink(temp_file_path)
                        logger.info(f"Cleaned up temporary audio file: {temp_file_path}")
                    except Exception as e:
                        logger.error(f"Error cleaning up temporary audio file: {e}")
        
        except Exception as e:
            logger.error(f"Error in Whisper recognition: {e}", exc_info=True)
            return None

    async def process_voice_message_by_url(self, download_url: str) -> Optional[str]:
        """Полный процесс обработки голосового сообщения через Whisper API."""
        try:
            # Скачиваем аудио
            audio_data = await self.download_audio_file_by_url(download_url)
            if not audio_data:
                return None

            # Определяем формат аудио из расширения URL
            from_format = None
            if "." in download_url.rsplit("/", 1)[-1]:
                file_extension = download_url.rsplit(".", 1)[-1].lower()
                # Преобразуем расширения в правильные форматы для ffmpeg
                if file_extension in ["oga", "opus"]:
                    from_format = "ogg"
                else:
                    from_format = file_extension

            # Конвертируем в MP3
            mp3_data = self.convert_audio_format(audio_data, from_format=from_format)
            if not mp3_data:
                return None

            # Распознаем речь через Whisper
            # По умолчанию используем русский, Whisper сам определит если это казахский
            recognized_text = await self.recognize_speech(mp3_data, language="ru")
            return recognized_text
            
        except Exception as e:
            logger.error(f"Error processing voice message by URL: {e}")
            return None

# Создаем глобальный экземпляр сервиса
try:
    speech_service = WhisperRecognitionService()
    logger.info("WhisperRecognitionService initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize WhisperRecognitionService: {e}")
    # Создаем fallback сервис
    class FallbackSpeechService:
        def __init__(self):
            self.enabled = False
        
        async def process_voice_message_by_url(self, download_url: str) -> Optional[str]:
            logger.warning("Speech recognition is disabled due to initialization error")
            return None
    
    speech_service = FallbackSpeechService()

