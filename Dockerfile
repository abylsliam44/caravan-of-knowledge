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
    libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0 \
    libgstreamer-plugins-bad1.0-0 \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    gstreamer1.0-tools \
    gstreamer1.0-x \
    gstreamer1.0-alsa \
    gstreamer1.0-gl \
    gstreamer1.0-gtk3 \
    gstreamer1.0-qt5 \
    gstreamer1.0-pulseaudio \
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
ENV AZURE_SPEECH_SDK_LOG_LEVEL=INFO
ENV AZURE_SPEECH_SDK_LOG_FILTER=ALL

# Открываем порт
EXPOSE 8000

# Запуск через gunicorn + uvicorn worker
CMD ["gunicorn", "main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"] 