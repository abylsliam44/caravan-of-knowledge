# WhatsApp AI Chat Bot с распознаванием голосовых сообщений

Этот проект представляет собой AI-чат-бота для автоматического общения с клиентами через WhatsApp. Бот принимает входящие сообщения (текстовые и голосовые) через GREEN-API, обрабатывает их и формирует интеллектуальные ответы с помощью **OpenAI GPT-4**.

## 🚀 Возможности

- **Текстовые сообщения**: Обработка и ответы на текстовые сообщения
- **Голосовые сообщения**: Распознавание речи с помощью Whisper API
- **AI-ответы**: Интеллектуальные ответы с помощью OpenAI GPT-4/GPT-4o
- **Контекстная память**: Бот помнит всю историю диалога с каждым пользователем
- **Естественное общение**: Бот общается как реальный человек, учитывая контекст
- **Динамические промпты**: Промпты загружаются из Google Docs
- **Мультиязычность**: Поддержка русского, казахского и английского языков
- **Асинхронная обработка**: Быстрая обработка сообщений
- **Логирование**: Подробное логирование всех операций

## 📋 Требования

- Python 3.8+
- GREEN-API (для WhatsApp)
- OpenAI API Key (для GPT и Whisper)
- ffmpeg (для обработки аудио)
- Redis (опционально, для персистентной памяти)

## 🛠️ Установка

1. **Клонируйте репозиторий:**
```bash
git clone https://github.com/abylsliam44/caravan-of-knowledge
```

2. **Установите зависимости:**
```bash
pip install -r requirements.txt

# Установите ffmpeg (для обработки аудио)
# macOS:
brew install ffmpeg

# Ubuntu/Debian:
sudo apt-get install ffmpeg
```

3. **Настройте переменные окружения:**
```bash
cp .env.example .env
```

Отредактируйте файл `.env` и добавьте ваши ключи API:

```env
# WhatsApp (Green API)
GREEN_ID_INSTANCE=your_instance_id_here
GREEN_API_TOKEN=your_api_token_here

# OpenAI API
OPENAI_API_KEY=sk-proj-your_key_here
OPENAI_MODEL=gpt-4o
OPENAI_MAX_TOKENS=512
OPENAI_TEMPERATURE=0.7

# Google Docs (опционально, для динамических промптов)
GOOGLE_DOCS_ID=your_google_docs_id

# Redis (опционально, для персистентной памяти)
REDIS_URL=redis://localhost:6379
```

## 🔧 Настройка сервисов

### GREEN-API (WhatsApp)
1. Зарегистрируйтесь на [green-api.com](https://green-api.com/)
2. Создайте инстанс WhatsApp
3. Получите `GREEN_ID_INSTANCE` и `GREEN_API_TOKEN`
4. Настройте webhook URL: `https://your-domain.com/webhook`

### OpenAI API
1. Зарегистрируйтесь на [platform.openai.com](https://platform.openai.com/)
2. Создайте API ключ в разделе [API Keys](https://platform.openai.com/api-keys)
3. **Важно**: Пополните баланс минимум на $5
4. Скопируйте ключ в `.env` файл

**OpenAI включает:**
- ✅ GPT-4o, GPT-4-turbo, GPT-3.5-turbo
- ✅ Whisper API для распознавания речи
- ✅ Поддержка русского, казахского, английского

### Redis (опционально)
```bash
# Локально с Docker
docker run -d -p 6379:6379 redis:alpine

# Или используйте облачный сервис
# Upstash: https://upstash.com/
# Redis Cloud: https://redis.com/
```

### Google Docs (опционально)
Для загрузки динамических промптов из Google Docs:
1. Создайте Google Cloud проект
2. Включите Google Docs API
3. Создайте Service Account и скачайте JSON ключ
4. Добавьте переменные в `.env` (см. `.env.example`)

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

1. **Настройте webhook в Green API:**
   - Войдите в личный кабинет Green API
   - Перейдите в настройки инстанса
   - URL: `https://your-domain.com/webhook`
   - Метод: POST

2. **Убедитесь, что ваш сервер доступен из интернета**

## 🧪 Тестирование

```bash
# Тест OpenAI подключения
python test_openai_connection.py

# Тест Green API
curl http://localhost:8000/test-connection
```

## 🔍 Логи

Логи сохраняются в директории `logs/` и содержат:
- Входящие сообщения
- Результаты распознавания речи
- Ответы от GPT
- Ошибки обработки

## 📊 Структура проекта

```
whatsapp-bot/
├── main.py                      # Точка входа приложения
├── webhook.py                   # Обработка webhook'ов WhatsApp
├── whatsapp.py                  # Отправка сообщений в WhatsApp
├── gpt.py                       # Интеграция с OpenAI GPT
├── whisper_recognition.py       # Распознавание голоса через Whisper API
├── speech_recognition.py        # (legacy) Azure Speech - не используется
├── chat_memory.py               # Система контекстной памяти чатов
├── chat_manager.py              # Утилита управления историей чатов
├── google_docs.py               # Интеграция с Google Docs
├── language_detection.py        # Определение языка сообщений
├── requirements.txt             # Зависимости Python
├── Dockerfile                   # Конфигурация Docker
├── docker-compose.yml           # Docker Compose конфигурация
├── .env.example                 # Шаблон переменных окружения
├── test_openai_connection.py   # Тест OpenAI подключения
├── README.md                    # Основная документация
├── QUICKSTART.md                # Быстрый старт
└── MIGRATION_TO_OPENAI.md       # Инструкция по миграции с Azure
```

## 🎯 Как это работает

1. **Получение сообщения**: WhatsApp отправляет webhook с сообщением через Green API
2. **Определение типа**: Бот определяет тип сообщения (текст/аудио)
3. **Обработка аудио**: Если это голосовое сообщение:
   - Скачивается аудиофайл
   - Конвертируется в MP3 через ffmpeg
   - Распознается через Whisper API
4. **Определение языка**: Автоматическое определение русского/казахского/английского
5. **Контекстная память**: Бот загружает историю диалога из Redis/памяти
6. **Загрузка промптов**: Динамические промпты из Google Docs (опционально)
7. **AI-обработка**: Текст + история → OpenAI GPT → контекстный ответ
8. **Сохранение контекста**: Новые сообщения сохраняются в историю (до 20 сообщений)
9. **Отправка ответа**: Ответ отправляется через Green API

## 🔧 Настройка распознавания речи

Whisper API автоматически определяет язык, но можно указать явно в `whisper_recognition.py`:

```python
# Автоматическое определение (рекомендуется)
language = "ru"  # ru, kk, en

# Whisper поддерживает 99+ языков
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

### Проблемы с OpenAI API
- **Ошибка "Invalid API key"**: Проверьте `OPENAI_API_KEY` в `.env`
- **Ошибка "Insufficient credits"**: Пополните баланс на [billing page](https://platform.openai.com/account/billing)
- **Ошибка "Rate limit"**: Превышен лимит запросов, подождите или увеличьте лимит
- **Ошибка "Model not found"**: Проверьте `OPENAI_MODEL` (должен быть `gpt-4o`, `gpt-4-turbo` или `gpt-3.5-turbo`)

### Проблемы с распознаванием речи (Whisper)
- **Ошибка "ffmpeg not found"**: Установите ffmpeg (см. раздел Установка)
- **Голос не распознается**: Проверьте, что `OPENAI_API_KEY` установлен
- **Плохое качество распознавания**: Убедитесь, что аудио чистое и громкое
- Проверьте логи: `tail -f logs/app.log`

### Проблемы с Green API
- **Ошибка 401**: Проверьте `GREEN_ID_INSTANCE` и `GREEN_API_TOKEN`
- **Бот не отвечает**: 
  - Убедитесь, что webhook настроен в личном кабинете Green API
  - Проверьте, что сервер доступен из интернета
  - Проверьте логи: `docker-compose logs -f`
- **Ошибка 403**: Превышена квота, пополните баланс Green API

### Проблемы с Redis
- **Connection refused**: Убедитесь, что Redis запущен
- **Без Redis**: Бот будет работать с in-memory хранилищем (история теряется при перезапуске)

### Общие проблемы
- **Бот не запускается**: Проверьте, что все зависимости установлены: `pip install -r requirements.txt`
- **Логи не создаются**: Создайте директорию: `mkdir -p logs`

## 💰 Мониторинг расходов

- **OpenAI Dashboard**: [platform.openai.com/usage](https://platform.openai.com/usage)
- **Green API**: Личный кабинет на green-api.com

**Примерные расходы:**
- 1000 текстовых сообщений (GPT-4o): ~$0.50
- 1000 голосовых по 30 сек (Whisper): ~$3.00
- **Итого: ~$3.50 за 1000 сообщений**

## 📚 Дополнительная документация

- 📖 [Быстрый старт (5 минут)](QUICKSTART.md)
- 🔄 [Миграция с Azure на OpenAI](MIGRATION_TO_OPENAI.md)
- 🤖 [OpenAI API Documentation](https://platform.openai.com/docs)
- 🟢 [Green API Documentation](https://green-api.com/docs/)

## 🤝 Поддержка

Если у вас есть вопросы или проблемы:
1. Проверьте [QUICKSTART.md](QUICKSTART.md) и [MIGRATION_TO_OPENAI.md](MIGRATION_TO_OPENAI.md)
2. Запустите тест: `python test_openai_connection.py`
3. Проверьте логи: `tail -f logs/app.log`
4. Создайте issue в репозитории

## 🌟 Особенности

- ✅ **Простая настройка**: Всего 2 ключа API (Green API + OpenAI)
- ✅ **Дешевле Azure**: В среднем на 30-50% дешевле
- ✅ **Whisper из коробки**: Лучшее распознавание речи в мире
- ✅ **Мультиязычность**: Русский, казахский, английский
- ✅ **Контекстная память**: Бот помнит историю диалога
- ✅ **Динамические промпты**: Обновляйте промпты через Google Docs
- ✅ **Production-ready**: Docker, Redis, логирование

---

**Сделано с ❤️ для Caravan of Knowledge** 
