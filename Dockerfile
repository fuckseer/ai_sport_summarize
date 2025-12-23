FROM python:3.11-slim

# --- ИЗМЕНЕНИЕ ТУТ: Добавляем nodejs и curl ---
RUN apt-get update && \
    apt-get install -y ffmpeg git nodejs curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

ENV PYTHONPATH=/app
# --- ВАЖНО: Отключаем буферизацию логов, чтобы видеть их сразу ---
ENV PYTHONUNBUFFERED=1

RUN mkdir -p downloads reports

CMD ["python", "src/main.py"]