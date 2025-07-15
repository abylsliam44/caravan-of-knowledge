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
            # Настройка для русского языка
            self.speech_config.speech_recognition_language = "ru-RU"
            # Дополнительные настройки для лучшего распознавания
            self.speech_config.speech_recognition_mode = "INTERACTIVE"
            self.speech_config.enable_audio_logging = True
    
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
    
    def convert_audio_format(self, audio_data: bytes, from_format: Optional[str] = None) -> Optional[bytes]:
        """Конвертирует аудио в формат WAV для Azure Speech Services"""
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

            logger.info(f"Converting audio from format: {from_format}, size: {len(audio_data)} bytes")

            # Создаем временный файл для конвертации
            with tempfile.NamedTemporaryFile(suffix=f".{from_format}", delete=False) as temp_input:
                temp_input.write(audio_data)
                temp_input_path = temp_input.name
            
            logger.info(f"Created temporary input file: {temp_input_path}")
            
            # Конвертируем в WAV
            audio = AudioSegment.from_file(temp_input_path, format=from_format)
            logger.info(f"Audio loaded: duration={len(audio)}ms, channels={audio.channels}, frame_rate={audio.frame_rate}")
            
            # Экспортируем в WAV с оптимальными параметрами для распознавания речи
            output_buffer = io.BytesIO()
            audio.export(output_buffer, format="wav", parameters=["-ar", "16000", "-ac", "1"])
            wav_data = output_buffer.getvalue()
            
            logger.info(f"Converted audio to WAV: {len(wav_data)} bytes")
            return wav_data
            
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
        
        temp_file_path = None
        try:
            # Создаем временный файл для аудио
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            logger.info(f"Created temporary audio file: {temp_file_path}")
            
            # Настраиваем аудио конфигурацию
            audio_config = AudioConfig(filename=temp_file_path)
            
            # Создаем распознаватель речи
            recognizer = SpeechRecognizer(
                speech_config=self.speech_config, 
                audio_config=audio_config
            )
            
            logger.info("Starting speech recognition...")
            
            # Распознаем речь асинхронно
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, recognizer.recognize_once_async().get)
            
            logger.info(f"Speech recognition result reason: {result.reason}")
            
            if result.reason.name == "RecognizedSpeech":
                recognized_text = result.text
                logger.info(f"Speech recognized successfully: {recognized_text}")
                return recognized_text
            elif result.reason.name == "NoMatch":
                logger.warning("Speech recognition: No match found")
                if hasattr(result, 'no_match_details'):
                    logger.error(f"No match details: {result.no_match_details.reason}")
                return None
            elif result.reason.name == "Canceled":
                logger.warning("Speech recognition was canceled")
                if hasattr(result, 'cancellation_details'):
                    logger.error(f"Cancellation details: {result.cancellation_details.reason}")
                    if result.cancellation_details.reason.name == "Error":
                        logger.error(f"Error details: {result.cancellation_details.error_details}")
                return None
            else:
                logger.warning(f"Speech recognition failed with reason: {result.reason}")
                return None
                
        except Exception as e:
            logger.error(f"Error in speech recognition: {e}", exc_info=True)
            return None
        finally:
            # Удаляем временный файл
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                    logger.info(f"Cleaned up temporary file: {temp_file_path}")
                except Exception as e:
                    logger.error(f"Error cleaning up temporary file: {e}")
    
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