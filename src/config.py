from typing import List, Optional
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"


class Settings(BaseSettings):
    # --- Основные настройки (По умолчанию используются для ВСЕГО) ---
    API_BASE_URL: str
    API_KEY: str

    # --- Опциональное переопределение для LLM (например, OpenRouter) ---
    LLM_API_BASE_URL: Optional[str] = None
    LLM_API_KEY: Optional[str] = None

    # --- Модели ---
    WHISPER_MODEL: str
    LLM_MODEL: str

    # --- Telegram & Proxy ---
    TELEGRAM_BOT_TOKEN: str
    ALLOWED_USERS: List[int] = []
    PROXY_URL: Optional[str] = None

    # --- Пути ---
    DOWNLOAD_DIR: str = str(BASE_DIR / "downloads")
    OUTPUT_DIR: str = str(BASE_DIR / "reports")
    CHUNK_LENGTH: int = 300

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()