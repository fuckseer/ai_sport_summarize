from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    GROQ_API_KEY: str
    # Используем официальный API Groq напрямую
    GROQ_BASE_URL: str = "https://api.groq.com"

    # Модели
    WHISPER_MODEL: str = "whisper-large-v3"
    LLM_MODEL: str = "openai/gpt-oss-120b"  # Возьмем модель поумнее для анализа


settings = Settings()


class GroqSettings(BaseSettings):
    """Settings for interacting with Groq's API via the mandated proxy."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="GROQ_",
        extra="ignore",
        case_sensitive=False,
    )

    api_key: str
    base_url: str = Field()
    whisper_model: str = Field(default="whisper-large-v3")
    llm_model: str = Field(default="openai/gpt-oss-120b")
    language: str = Field(default="ru")


class TelegramSettings(BaseSettings):
    """Telegram bot configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    # .env: TELEGRAM_BOT_TOKEN=...
    bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")

    # .env: TELEGRAM_CHAT_ID=425516815 или TELEGRAM_CHAT_ID=123,456
    chat_ids: List[str] = Field(
        default_factory=list,
        alias="TELEGRAM_CHAT_ID",
        validation_alias="TELEGRAM_CHAT_ID",
    )

    @field_validator("chat_ids", mode="before")
    @classmethod
    def split_chat_ids(cls, raw) -> List[str]:
        # Ничего нет — возвращаем пустой список
        if raw is None:
            return []

        # Если пришла строка — поддерживаем "1" или "1,2,3"
        if isinstance(raw, str):
            return [cid.strip() for cid in raw.split(",") if cid.strip()]

        # Если пришёл int/float — делаем список из одного элемента
        if isinstance(raw, (int, float)):
            return [str(raw)]

        # Если уже список — приводим элементы к строке
        if isinstance(raw, list):
            return [str(item).strip() for item in raw if str(item).strip()]

        # На всякий случай — всё остальное тоже превращаем в одиночный список строк
        return [str(raw)]



class StreamSettings(BaseSettings):
    """Video stream capture configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    stream_url: str
    tmp_dir: Path = Field(default=Path("./tmp_audio"))
    chunk_duration_seconds: int = Field(default=10)
    reconnect_delay_seconds: float = Field(default=5.0)


class AppSettings(BaseSettings):
    """Aggregated settings tree that other modules depend on."""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    groq: GroqSettings = Field(default_factory=GroqSettings)
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    stream: StreamSettings = Field(default_factory=StreamSettings)
    summary_interval_seconds: int = Field(default=300)

    def ensure_directories(self) -> None:
        """Create runtime directories if they do not exist."""
        self.stream.tmp_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_app_settings() -> AppSettings:
    """Return a cached instance of the aggregated settings."""
    settings = AppSettings()
    settings.ensure_directories()
    if not settings.telegram.chat_ids:
        raise ValueError("At least one TELEGRAM_CHAT_ID must be configured.")
    return settings


