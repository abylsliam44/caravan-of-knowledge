import os
import asyncio
import aiofiles
import aiohttp
import logging
from typing import Optional
from pydub import AudioSegment
from azure.cognitiveservices.speech import SpeechConfig, SpeechRecognizer, AudioConfig
from azure.cognitiveservices.speech.audio import AudioInputStream
import tempfile
import io

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SpeechRecognitionService:
    def __init__(self):
        self.azure_speech_key = os.getenv("AZURE_SPEECH_KEY")
        self.azure_speech_region = os.getenv("AZURE_SPEECH_REGION")
        
        if not self.azure_speech_key or not self.azure_speech_region:
            logger.warning("Azure Speech credentials not found. Speech recognition will be disabled.")
            self.enabled = False
        else:
            self.enabled = True
            self.speech_config = SpeechConfig(
                subscription=self.azure_speech_key, 
                region=self.azure_speech_region
            )
            # Настройка для английского языка
            self.speech_config.speech_recognition_language = "en-US"
    
    async def download_audio_file(self, media_id: str, access_token: str) -> Optional[bytes]:
        """Скачивает аудиофайл из WhatsApp Cloud API"""
        try:
            # Получаем информацию о медиафайле
            media_url = f"https://graph.facebook.com/v18.0/{media_id}"
            headers = {"Authorization": f"Bearer {access_token}"}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(media_url, headers=headers) as response:
                    if response.status != 200:
                        logger.error(f"Failed to get media info: {response.status}")
                        return None
                    
                    media_info = await response.json()
                    download_url = media_info.get("url")
                    
                    if not download_url:
                        logger.error("No download URL in media info")
                        return None
                
                # Скачиваем аудиофайл
                async with session.get(download_url, headers=headers) as response:
                    if response.status != 200:
                        logger.error(f"Failed to download audio: {response.status}")
                        return None
                    
                    audio_data = await response.read()
                    logger.info(f"Downloaded audio file: {len(audio_data)} bytes")
                    return audio_data
                    
        except Exception as e:
            logger.error(f"Error downloading audio file: {e}")
            return None
    
    def convert_audio_format(self, audio_data: bytes, from_format: Optional[str] = "ogg") -> Optional[bytes]:
        """Конвертирует аудио в формат WAV для Azure Speech Services"""
        try:
            # Определяем формат, если не указан явно
            if not from_format:
                from_format = "ogg"  # Fall back to ogg

            # Создаем временный файл для конвертации
            with tempfile.NamedTemporaryFile(suffix=f".{from_format}", delete=False) as temp_input:
                temp_input.write(audio_data)
                temp_input_path = temp_input.name
            
            # Конвертируем в WAV
            audio = AudioSegment.from_file(temp_input_path, format=from_format)
            
            # Экспортируем в WAV
            output_buffer = io.BytesIO()
            audio.export(output_buffer, format="wav")
            wav_data = output_buffer.getvalue()
            
            # Удаляем временный файл
            os.unlink(temp_input_path)
            
            logger.info(f"Converted audio to WAV: {len(wav_data)} bytes")
            return wav_data
            
        except Exception as e:
            logger.error(f"Error converting audio format: {e}")
            return None

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

    async def process_voice_message_by_url(self, download_url: str) -> Optional[str]:
        """Полный процесс обработки голосового сообщения (Green API variant)."""
        try:
            audio_data = await self.download_audio_file_by_url(download_url)
            if not audio_data:
                return None

            # Определяем формат аудио из расширения URL
            from_format = None
            if "." in download_url.rsplit("/", 1)[-1]:
                from_format = download_url.rsplit(".", 1)[-1].lower()

            wav_data = self.convert_audio_format(audio_data, from_format=from_format)
            if not wav_data:
                return None

            recognized_text = await self.recognize_speech(wav_data)
            return recognized_text
        except Exception as e:
            logger.error(f"Error processing voice message by URL: {e}")
            return None
    
    async def recognize_speech(self, audio_data: bytes) -> Optional[str]:
        """Распознает речь в аудиофайле"""
        if not self.enabled:
            logger.warning("Speech recognition is disabled")
            return None
        
        try:
            # Создаем временный файл для аудио
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            # Настраиваем аудио конфигурацию
            audio_config = AudioConfig(filename=temp_file_path)
            
            # Создаем распознаватель речи
            recognizer = SpeechRecognizer(
                speech_config=self.speech_config, 
                audio_config=audio_config
            )
            
            # Распознаем речь
            result = recognizer.recognize_once_async().get()
            
            # Удаляем временный файл
            os.unlink(temp_file_path)
            
            if result.reason.name == "RecognizedSpeech":
                recognized_text = result.text
                logger.info(f"Speech recognized: {recognized_text}")
                return recognized_text
            else:
                logger.warning(f"Speech recognition failed: {result.reason}")
                if hasattr(result, 'cancellation_details'):
                    logger.error(f"Cancellation details: {result.cancellation_details.reason}, error details: {result.cancellation_details.error_details}")
                return None
                
        except Exception as e:
            logger.error(f"Error in speech recognition: {e}")
            return None
    
    async def process_voice_message(self, media_id: str, access_token: str) -> Optional[str]:
        """Полный процесс обработки голосового сообщения"""
        try:
            # Скачиваем аудиофайл
            audio_data = await self.download_audio_file(media_id, access_token)
            if not audio_data:
                return None
            
            # Конвертируем в WAV
            wav_data = self.convert_audio_format(audio_data)
            if not wav_data:
                return None
            
            # Распознаем речь
            recognized_text = await self.recognize_speech(wav_data)
            return recognized_text
            
        except Exception as e:
            logger.error(f"Error processing voice message: {e}")
            return None

# Создаем глобальный экземпляр сервиса
speech_service = SpeechRecognitionService() 