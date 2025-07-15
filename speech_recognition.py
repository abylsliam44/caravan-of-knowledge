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
from language_detection import detect_language, get_speech_language_code

# Azure Speech SDK (может не работать в Docker)
AZURE_SDK_AVAILABLE = False
try:
    import azure.cognitiveservices.speech as speechsdk
    from azure.cognitiveservices.speech.audio import AudioConfig
    # Проверяем, что SDK действительно работает
    AZURE_SDK_AVAILABLE = True
    logging.info("Azure Speech SDK imported successfully")
except ImportError as e:
    logging.warning(f"Azure Speech SDK not available: {e}. Will use REST API")
except Exception as e:
    logging.warning(f"Azure Speech SDK import failed: {e}. Will use REST API")

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Проверяем переменные окружения
logger.info("Checking environment variables...")
logger.info(f"AZURE_SPEECH_KEY: {'SET' if os.getenv('AZURE_SPEECH_KEY') else 'NOT SET'}")
logger.info(f"AZURE_SPEECH_REGION: {os.getenv('AZURE_SPEECH_REGION', 'NOT SET')}")

class SpeechRecognitionService:
    def __init__(self):
        self.speech_key = os.getenv("AZURE_SPEECH_KEY")
        self.speech_region = os.getenv("AZURE_SPEECH_REGION")
        
        logger.info(f"Initializing SpeechRecognitionService with region: {self.speech_region}")
        logger.info(f"AZURE_SDK_AVAILABLE global variable: {AZURE_SDK_AVAILABLE}")
        
        if not self.speech_key or not self.speech_region:
            logger.warning("Azure Speech credentials not found. Speech recognition will be disabled.")
            self.enabled = False
            self.sdk_available = False
            self.speech_config = None
        else:
            self.enabled = True
            
            # Инициализируем Azure Speech SDK только если доступен
            self.speech_config = None
            self.sdk_available = AZURE_SDK_AVAILABLE
            
            if self.sdk_available:
                try:
                    logger.info("Attempting to initialize Azure Speech SDK...")
                    self.speech_config = speechsdk.SpeechConfig(
                        subscription=self.speech_key, 
                        region=self.speech_region
                    )
                    # Поддерживаем русский и казахский языки
                    self.speech_config.speech_recognition_language = "ru-RU"
                    # Для казахского языка можно использовать "kk-KZ"
                    logger.info("Azure Speech SDK initialized successfully")
                except Exception as e:
                    logger.error(f"Failed to initialize Azure Speech SDK: {e}")
                    self.sdk_available = False
                    self.speech_config = None
            
            if not self.sdk_available:
                logger.info("Using Azure Speech REST API instead of SDK")
    
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
                file_extension = download_url.rsplit(".", 1)[-1].lower()
                # Преобразуем расширения в правильные форматы для ffmpeg
                if file_extension in ["oga", "opus"]:
                    from_format = "ogg"
                else:
                    from_format = file_extension

            wav_data = self.convert_audio_format(audio_data, from_format=from_format)
            if not wav_data:
                return None

            recognized_text = await self.recognize_speech(wav_data)
            return recognized_text
        except Exception as e:
            logger.error(f"Error processing voice message by URL: {e}")
            return None
    
    async def recognize_speech(self, audio_data: bytes, detected_text: Optional[str] = None) -> Optional[str]:
        """Распознает речь в аудиофайле с поддержкой динамического языка"""
        if not self.enabled:
            logger.warning("Speech recognition is disabled")
            return None
        
        # Определяем язык на основе предыдущего текста или используем русский по умолчанию
        language = "ru-RU"
        if detected_text:
            detected_lang = detect_language(detected_text)
            language = get_speech_language_code(detected_lang)
            logger.info(f"Detected language: {detected_lang}, using speech code: {language}")
        
        logger.info(f"Starting speech recognition with language: {language}")
        
        # Пробуем сначала REST API
        logger.info("Trying REST API first...")
        try:
            result = await self._recognize_speech_rest_api(audio_data, language)
            if result:
                logger.info("REST API recognition successful")
                return result
            else:
                logger.warning("REST API returned no result")
        except Exception as e:
            logger.warning(f"REST API recognition failed: {e}")
        
        # Если REST API не сработал, пробуем SDK
        if self.sdk_available:
            logger.info("REST API failed, trying SDK...")
            try:
                result = await self._recognize_speech_sdk(audio_data, language)
                if result:
                    logger.info("SDK recognition successful")
                    return result
                else:
                    logger.warning("SDK returned no result")
            except Exception as e:
                logger.error(f"SDK recognition failed: {e}")
        else:
            logger.info("Azure SDK not available, skipping SDK attempt")
        
        logger.warning("Both REST API and SDK failed to recognize speech")
        return None
    
    async def _recognize_speech_rest_api(self, audio_data: bytes, language: str = "ru-RU") -> Optional[str]:
        """Распознает речь через REST API Azure Speech Services"""
        try:
            # Проверяем, что у нас есть необходимые данные
            if not self.speech_key or not self.speech_region:
                logger.error("Missing Azure Speech credentials")
                return None
            
            # Используем правильный endpoint для Azure Speech Services
            # Убираем возможные пробелы и приводим к нижнему регистру
            region = self.speech_region.strip().lower()
            # Поддерживаем русский, казахский и английский языки
            url = f"https://{region}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1?language={language}"
            
            headers = {
                'Ocp-Apim-Subscription-Key': self.speech_key,
                'Content-Type': 'audio/wav',
                'Accept': 'application/json'
            }
            
            logger.info(f"Making REST API request to: {url}")
            logger.info(f"Audio data size: {len(audio_data)} bytes")
            logger.info(f"Using region: {region}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, data=audio_data, timeout=30) as response:
                    logger.info(f"REST API response status: {response.status}")
                    
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"REST API response: {result}")
                        
                        if result.get('RecognitionStatus') == 'Success':
                            recognized_text = result.get('DisplayText', '')
                            logger.info(f"REST API recognition successful: {recognized_text}")
                            return recognized_text
                        else:
                            logger.warning(f"REST API recognition failed: {result}")
                    else:
                        response_text = await response.text()
                        logger.error(f"REST API request failed: {response.status}, response: {response_text}")
            
            return None
        except Exception as e:
            logger.error(f"Error in REST API recognition: {e}", exc_info=True)
            return None
    
    async def _recognize_speech_sdk(self, audio_data: bytes, language: str = "ru-RU") -> Optional[str]:
        """Распознает речь через Azure Speech SDK"""
        temp_file_path = None
        try:
            # Создаем временный файл для аудио
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            logger.info(f"Created temporary audio file: {temp_file_path}")
            
            # Настраиваем аудио конфигурацию
            audio_config = AudioConfig(filename=temp_file_path)
            
            # Создаем временную конфигурацию речи с нужным языком
            temp_speech_config = speechsdk.SpeechConfig(
                subscription=self.speech_key, 
                region=self.speech_region
            )
            temp_speech_config.speech_recognition_language = language
            
            # Создаем распознаватель речи
            recognizer = speechsdk.SpeechRecognizer(
                speech_config=temp_speech_config, 
                audio_config=audio_config
            )
            
            logger.info("Starting SDK speech recognition...")
            
            # Распознаем речь асинхронно
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, recognizer.recognize_once_async().get)
            
            logger.info(f"SDK speech recognition result reason: {result.reason}")
            
            if result.reason.name == "RecognizedSpeech":
                recognized_text = result.text
                logger.info(f"SDK speech recognized successfully: {recognized_text}")
                return recognized_text
            elif result.reason.name == "NoMatch":
                logger.warning("SDK speech recognition: No match found")
                if hasattr(result, 'no_match_details'):
                    logger.error(f"No match details: {result.no_match_details.reason}")
                return None
            elif result.reason.name == "Canceled":
                logger.warning("SDK speech recognition was canceled")
                if hasattr(result, 'cancellation_details'):
                    logger.error(f"Cancellation details: {result.cancellation_details.reason}")
                    if result.cancellation_details.reason.name == "Error":
                        logger.error(f"Error details: {result.cancellation_details.error_details}")
                return None
            else:
                logger.warning(f"SDK speech recognition failed with reason: {result.reason}")
                return None
                
        except Exception as e:
            logger.error(f"Error in SDK speech recognition: {e}", exc_info=True)
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

# Создаем глобальный экземпляр сервиса с обработкой ошибок
try:
    speech_service = SpeechRecognitionService()
    logger.info("SpeechRecognitionService initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize SpeechRecognitionService: {e}")
    # Создаем fallback сервис
    class FallbackSpeechService:
        def __init__(self):
            self.enabled = False
            self.sdk_available = False
            self.speech_config = None
        
        async def process_voice_message_by_url(self, download_url: str) -> Optional[str]:
            logger.warning("Speech recognition is disabled due to initialization error")
            return None
    
    speech_service = FallbackSpeechService() 