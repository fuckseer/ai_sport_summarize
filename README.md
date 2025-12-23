# AI Sport Summarize – Real-Time Text Commentator
![img.png](img.png)
This project turns any live sports stream into near real-time text commentary delivered to Telegram. It ingests an HLS/DASH/YouTube/Twitch stream, transcribes the broadcast audio with Groq Whisper, classifies key events with a Groq LLM, and pushes flash alerts and periodic summaries to configured chats.

## Features
- **Stream capture**: `streamlink` + `ffmpeg` convert arbitrary live streams into rolling mono 16 kHz WAV chunks stored in `tmp_audio/`.
- **Transcription**: Each chunk is sent through Groq Whisper (`whisper-large-v3`) via the mandated proxy (`http://72.56.67.27/groq/openai/v1`).
- **Event analysis**: A lightweight Groq LLM (`llama-3.1-8b-instant`) receives rolling context and returns strict JSON describing urgent events and summary candidates.
- **Telegram delivery**: Flash notifications (goals, penalties, cards, etc.) plus scheduled summaries are sent to any number of chats through `python-telegram-bot`.
- **Resilience**: Async orchestration with retries, stream restarts, and graceful SIGINT/SIGTERM shutdown.

## Getting Started

### 1. Install system dependencies
```bash
brew install ffmpeg streamlink   # or use your distro's package manager
```
Ensure `ffmpeg` and `streamlink` are on the PATH; the Python code shells out to both.

### 2. Create and activate a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure environment variables
Copy `.env.example` to `.env` and fill in real values:

```bash
cp .env.example .env
```

Required variables:
| Key | Description |
| --- | ----------- |
| `GROQ_API_KEY` | Your Groq API key (proxied via `GROQ_BASE_URL`). |
| `GROQ_BASE_URL` | Must stay `http://127.0.0.1/groq/openai/v1`. |
| `TELEGRAM_BOT_TOKEN` | Bot token from BotFather. |
| `TELEGRAM_CHAT_ID` | One or more comma-separated chat/channel IDs for delivery. |
| `STREAM_URL` | HLS/DASH/YouTube/Twitch URL supported by `streamlink`. |
| `SUMMARY_INTERVAL_SECONDS` | Period between summary prompts (default 300). |

Optional overrides include tmp dir path, chunk duration, reconnect delay, Groq models, etc.

### 4. Run the pipeline
```bash
python main.py
```
The service connects to the stream, starts producing transcripts, and posts alerts to Telegram. Use `Ctrl+C` to stop gracefully.

## Project Structure

| File | Purpose |
| ---- | ------- |
| `main.py` | Async orchestrator wiring capture → transcription → summarization → Telegram. |
| `config.py` | Pydantic-based settings loader with typed sub-configs. |
| `stream_capture.py` | Streamlink/ffmpeg segmenter that yields WAV chunk paths. |
| `transcriber_service.py` | Wrapper that sends chunks to Groq Whisper via the proxy. |
| `summarizer_service.py` | Maintains conversation state, calls Groq LLM, emits flash/summary events. |
| `groq_client.py` | Shared Groq SDK adapter with retries and strict JSON parsing. |
| `telegram_bot.py` | Async helper for sending messages to configured chats. |
| `requirements.txt` | Python dependencies (system packages must install ffmpeg separately). |

## Development Tips
- Run inside the virtual environment so the correct versions of `groq`, `python-telegram-bot`, etc. are used.
- Monitor logs; warnings about reconnects or Groq retries indicate network instability.
- Keep `.gitignore` as provided so secrets (`.env`) and temp audio files never hit version control.

## License
MIT (or specify your preferred license here).


