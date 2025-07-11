FROM python:3.11-slim

# Устанавливаем системные зависимости для аудио и Azure Speech SDK
RUN apt-get update && apt-get install -y \
    build-essential \
    ffmpeg \
    libavcodec-extra \
    libssl-dev \
    libasound2 \
    libcurl4 \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем только requirements.txt для кэширования слоёв pip
COPY requirements.txt ./

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY . .

# Переменные окружения
ENV PYTHONUNBUFFERED=1

# Открываем порт
EXPOSE 8000

# Запуск через gunicorn + uvicorn worker
CMD ["gunicorn", "main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"] 