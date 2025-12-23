# ⚽ AI Match Summarizer

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-green.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**[English](#-english) | [Русский](#-русский) | [中文](#-中文)**

---

<div align="center">
  <img src="img.png" alt="Bot Demo Screenshot" width="600"/>
  <br>
  <em>AI-generated highlights delivered straight to Telegram / Хайлайты матча прямо в Telegram</em>
</div>

---

<a name="-english"></a>
## 🇬🇧 English

**AI Match Summarizer** is a fully automated tool that watches sports matches (from YouTube/Twitch), transcribes the commentary using **Whisper**, and generates a timeline of highlights (Goals, Fouls, VAR, etc.) using **LLMs** (Llama 3, GPT-4).

### ✨ Features
*   **Telegram Bot Interface:** Send a link, get a report.
*   **Video Downloader:** Powered by `yt-dlp` (supports YouTube, Twitch, etc.).
*   **Smart Audio Processing:** Splits audio into chunks, compresses to Mono/16kHz to save bandwidth.
*   **AI Transcription:** Uses OpenAI API or Groq (Whisper Large v3) with auto-retry on Rate Limits.
*   **Contextual Analysis:** LLM analyzes the text to find "highlight-worthy" moments based on commentary emotion and keywords.
*   **Proxy Support:** Native SOCKS5/HTTP proxy support for regions with restricted access.
*   **Dockerized:** No need to install FFmpeg or Python manually.

### 🚀 Quick Start

#### 1. Clone the repository
```bash
git clone https://github.com/your-username/match-transcriber.git
cd match-transcriber
```

#### 2. Configure environment
Create a `.env` file based on the example:
```bash
cp .env.example .env
```
Edit `.env` with your keys (see [Configuration](#-configuration)).

#### 3. Run with Docker
```bash
docker-compose up --build -d
```
The bot is now running! Send a YouTube link to your bot in Telegram.

---

<a name="-русский"></a>
## 🇷🇺 Русский

**AI Match Summarizer** — это инструмент для автоматического создания текстовых трансляций и хайлайтов спортивных матчей. Бот скачивает видео, переводит голос комментатора в текст (Whisper) и выделяет главные события (Голы, Удары, Карточки) с помощью нейросетей (Llama 3, GPT).

### ✨ Возможности
*   **Удобный Телеграм-бот:** Просто отправь ссылку на YouTube или Twitch.
*   **Загрузчик:** Использует `yt-dlp`, поддерживает большинство видеоплатформ.
*   **Умная обработка:** Нарезает аудио на куски, сжимает для экономии трафика и ускорения API.
*   **AI Транскрибация:** Поддержка Groq (Whisper Large v3) и OpenAI. Автоматический обход лимитов (Rate Limit).
*   **Анализ событий:** LLM фильтрует "воду" и оставляет только острые моменты с таймкодами.
*   **Прокси:** Полная поддержка SOCKS5/HTTP прокси (актуально для РФ).
*   **Docker:** Запуск одной командой, все зависимости (FFmpeg, Node.js) внутри.

### 🚀 Установка

#### 1. Клонирование
```bash
git clone https://github.com/your-username/match-transcriber.git
cd match-transcriber
```

#### 2. Настройка
Создайте файл `.env` из примера:
```bash
cp .env.example .env
```
Заполните ключи (см. раздел [Конфигурация](#-configuration)).

#### 3. Запуск в Docker
```bash
docker-compose up --build -d
```
Бот запущен! Напишите `/start` своему боту в Telegram.

---

<a name="-中文"></a>
## 🇨🇳 中文

**AI Match Summarizer** 是一款全自动工具，利用人工智能生成体育比赛的精彩片段摘要。它能下载比赛视频（来自 YouTube/Twitch），使用 **Whisper** 转录解说语音，并利用 **LLM**（Llama 3, GPT-4）生成包含时间轴的比赛报告。

### ✨ 特性
*   **Telegram 机器人界面:** 发送链接，即刻获取报告。
*   **视频下载:** 基于 `yt-dlp`，支持主流视频平台。
*   **智能音频处理:** 自动切分音频并压缩至 Mono/16kHz，节省带宽。
*   **AI 转录:** 支持 OpenAI API 或 Groq (Whisper Large v3)，自动处理速率限制 (Rate Limit)。
*   **上下文分析:** LLM 根据解说员的情绪和关键词筛选“值得一看”的时刻。
*   **代理支持:** 原生支持 SOCKS5/HTTP 代理。
*   **Docker 化:** 一键部署，无需手动安装 FFmpeg。

### 🚀 快速开始

#### 1. 克隆项目
```bash
git clone https://github.com/your-username/match-transcriber.git
cd match-transcriber
```

#### 2. 配置环境
复制配置文件示例：
```bash
cp .env.example .env
```
编辑 `.env` 填入您的密钥（参考 [配置说明](#-configuration)）。

#### 3. 启动 Docker
```bash
docker-compose up --build -d
```
机器人已启动！在 Telegram 中向您的机器人发送 YouTube 链接即可。

---

<a name="-configuration"></a>
## ⚙️ Configuration / Конфигурация / 配置

Edit `.env` file / Редактируйте `.env` / 编辑 `.env`:

```ini
# --- Telegram ---
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...   # Get from @BotFather
ALLOWED_USERS=[12345678]               # Your Telegram User ID (for security)

# --- AI Provider (Groq Example) ---
API_BASE_URL=https://api.groq.com/openai/v1
API_KEY=gsk_...                        # Your Groq or OpenAI Key

# --- Models ---
WHISPER_MODEL=whisper-large-v3
LLM_MODEL=llama3-70b-8192

# --- Proxy (Optional) ---
# Use host.docker.internal to access proxy on your machine
PROXY_URL=socks5://host.docker.internal:1080

# --- Settings ---
CHUNK_LENGTH=300                       # Seconds per audio chunk (default: 5 min)
```

## 🛠 Tech Stack
*   **Python 3.11**
*   **Aiogram 3.x** (Telegram Bot)
*   **OpenAI SDK** (Universal client for LLMs)
*   **FFmpeg** (Audio processing)
*   **yt-dlp** (Video downloading)
*   **Docker & Docker Compose**

## 📄 License
This project is licensed under the MIT License.
```
