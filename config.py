from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class GroqSettings(BaseSettings):
    """Settings for interacting with Groq's API via the mandated proxy."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="GROQ_",
        extra="ignore",
        case_sensitive=False,
    )

    api_key: str
    base_url: str = Field(default="http://72.56.67.27/groq/openai/v1")
    whisper_model: str = Field(default="whisper-large-v3")
    llm_model: str = Field(default="llama-3.1-8b-instant")
    language: str = Field(default="ru")


class TelegramSettings(BaseSettings):
    """Telegram bot configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="TELEGRAM_",
        extra="ignore",
        case_sensitive=False,
    )

    bot_token: str
    chat_ids: List[str] = Field(default_factory=list)

    @field_validator("chat_ids", mode="before")
    @classmethod
    def _split_chat_ids(cls, raw: object) -> List[str]:
        if raw is None:
            return []
        if isinstance(raw, list):
            return [str(item).strip() for item in raw if str(item).strip()]
        if isinstance(raw, str):
            return [cid.strip() for cid in raw.split(",") if cid.strip()]
        raise ValueError("TELEGRAM_CHAT_ID must be a comma-separated string or list.")


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


