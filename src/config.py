from typing import List, Optional
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Определяем путь к корню проекта (на уровень выше папки src)
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"


class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str
    ALLOWED_USERS: List[int] = []

    API_BASE_URL: str
    API_KEY: str

    PROXY_URL: Optional[str] = None

    WHISPER_MODEL: str
    LLM_MODEL: str

    DOWNLOAD_DIR: str = str(BASE_DIR / "downloads")
    OUTPUT_DIR: str = str(BASE_DIR / "reports")
    CHUNK_LENGTH: int = 300

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,  # <--- Указываем точный путь
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()