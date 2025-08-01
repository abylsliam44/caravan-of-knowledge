# WhatsApp AI Chat Bot с распознаванием голосовых сообщений

Этот проект представляет собой AI-чат-бота для автоматического общения с клиентами через WhatsApp. Бот принимает входящие сообщения (текстовые и голосовые) через WhatsApp Cloud API, обрабатывает их и формирует интеллектуальные ответы с помощью Azure OpenAI (GPT-4).

## 🚀 Возможности

- **Текстовые сообщения**: Обработка и ответы на текстовые сообщения
- **Голосовые сообщения**: Распознавание речи с помощью Azure Speech Services
- **AI-ответы**: Интеллектуальные ответы с помощью Azure OpenAI GPT-4
- **Контекстная память**: Бот помнит всю историю диалога с каждым пользователем
- **Естественное общение**: Бот общается как реальный человек, учитывая контекст
- **Асинхронная обработка**: Быстрая обработка сообщений
- **Логирование**: Подробное логирование всех операций

## 📋 Требования

- Python 3.8+
- WhatsApp Business API (Cloud API)
- Azure OpenAI Service
- Azure Speech Services (для распознавания голосовых сообщений)

## 🛠️ Установка

1. **Клонируйте репозиторий:**
```bash
git clone <repository-url>
cd whatsapp-bot
```

2. **Установите зависимости:**
```bash
pip install -r requirements.txt
```

3. **Настройте переменные окружения:**
```bash
cp env.example .env
```

Отредактируйте файл `.env` и добавьте ваши ключи API:

```env
# WhatsApp Cloud API
WHATSAPP_TOKEN=your_whatsapp_token_here
PHONE_NUMBER_ID=your_phone_number_id_here
VERIFY_TOKEN=whatsapp_verify_token

# Azure OpenAI
AZURE_OPENAI_API_KEY=your_azure_openai_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment_name

# Azure Speech Services (для распознавания голосовых сообщений)
AZURE_SPEECH_KEY=your_azure_speech_key_here
AZURE_SPEECH_REGION=your_azure_speech_region_here

# Redis (для хранения истории чатов, опционально)
REDIS_URL=redis://localhost:6379
```

## 🔧 Настройка сервисов

### WhatsApp Cloud API
1. Создайте приложение в [Meta for Developers](https://developers.facebook.com/)
2. Настройте WhatsApp Business API
3. Получите `WHATSAPP_TOKEN` и `PHONE_NUMBER_ID`

### Azure OpenAI
1. Создайте ресурс Azure OpenAI в Azure Portal
2. Разверните модель GPT-4
3. Получите ключ API и endpoint

### Azure Speech Services
1. Создайте ресурс Speech Services в Azure Portal
2. Получите ключ API и регион
3. Настройте распознавание речи для русского языка
4. Убедитесь, что в переменных окружения указаны:
   - `AZURE_SPEECH_KEY` - ключ API
   - `AZURE_SPEECH_REGION` - регион (например, "eastus")

## 🚀 Запуск

### Локальный запуск
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Запуск с Docker
```bash
docker-compose up -d
```

## 📱 Настройка webhook

1. **Настройте webhook URL в WhatsApp Cloud API:**
   - URL: `https://your-domain.com/webhook`
   - Verify Token: значение из `VERIFY_TOKEN`

2. **Убедитесь, что ваш сервер доступен из интернета**

## 🔍 Логи

Логи сохраняются в директории `logs/` и содержат:
- Входящие сообщения
- Результаты распознавания речи
- Ответы от GPT
- Ошибки обработки

## 📊 Структура проекта

```
whatsapp-bot/
├── main.py              # Точка входа приложения
├── webhook.py           # Обработка webhook'ов WhatsApp
├── whatsapp.py          # Отправка сообщений в WhatsApp
├── gpt.py              # Интеграция с Azure OpenAI
├── speech_recognition.py # Распознавание голосовых сообщений
├── chat_memory.py       # Система контекстной памяти чатов
├── chat_manager.py      # Утилита управления историей чатов
├── google_docs.py       # Интеграция с Google Docs для динамических промптов
├── requirements.txt     # Зависимости Python
├── Dockerfile          # Конфигурация Docker
├── docker-compose.yml  # Docker Compose конфигурация
└── README.md           # Документация
```

## 🎯 Как это работает

1. **Получение сообщения**: WhatsApp отправляет webhook с сообщением
2. **Определение типа**: Бот определяет тип сообщения (текст/аудио)
3. **Обработка аудио**: Если это голосовое сообщение, оно скачивается и распознается
4. **Контекстная память**: Бот загружает историю диалога с пользователем
5. **AI-обработка**: Текст + история диалога передаются в Azure OpenAI для генерации контекстного ответа
6. **Сохранение контекста**: Новые сообщения сохраняются в историю диалога
7. **Отправка ответа**: Ответ отправляется обратно пользователю через WhatsApp API

## 🔧 Настройка распознавания речи

По умолчанию бот настроен на распознавание русского языка. Для изменения языка отредактируйте файл `speech_recognition.py`:

```python
self.speech_config.speech_recognition_language = "en-US"  # Для английского
```

## 💬 Управление историей чатов

Бот автоматически сохраняет историю диалогов для каждого пользователя. Для управления историей используйте утилиту `chat_manager.py`:

```bash
# Показать список активных чатов
python chat_manager.py list

# Показать историю конкретного чата
python chat_manager.py show --phone 77001234567

# Очистить историю конкретного чата
python chat_manager.py clear --phone 77001234567

# Очистить все чаты
python chat_manager.py clear-all

# Показать краткое описание чата
python chat_manager.py summary --phone 77001234567
```

### Хранение истории

- **С Redis**: История хранится в Redis с TTL 24 часа
- **Без Redis**: История хранится в памяти (теряется при перезапуске)
- **Лимит**: Максимум 20 сообщений на чат (настраивается в `chat_memory.py`)

## 🐛 Устранение неполадок

### Проблемы с распознаванием речи
- Убедитесь, что Azure Speech Services настроен правильно
- Проверьте ключи API в переменных окружения (`AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION`)
- Проверьте логи на наличие ошибок
- Убедитесь, что голосовые сообщения отправляются в поддерживаемом формате (OGG, MP3, WAV)
- Для тестирования используйте: `python test_voice.py`

### Проблемы с WhatsApp API
- Проверьте правильность `WHATSAPP_TOKEN` и `PHONE_NUMBER_ID`
- Убедитесь, что webhook URL доступен из интернета
- Проверьте настройки приложения в Meta for Developers

## 🤝 Поддержка

Если у вас есть вопросы или проблемы, создайте issue в репозитории. 
