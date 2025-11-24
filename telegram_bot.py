from __future__ import annotations

import logging
from typing import Iterable

from telegram import Bot

from config import TelegramSettings

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Async helper for sending messages to one or many chats."""

    def __init__(self, settings: TelegramSettings) -> None:
        if not settings.chat_ids:
            raise ValueError("TELEGRAM_CHAT_ID must contain at least one chat/channel id.")
        self._bot = Bot(token=settings.bot_token)
        self._chat_ids: Iterable[str] = settings.chat_ids

    async def __aenter__(self) -> "TelegramNotifier":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def close(self) -> None:
        await self._bot.session.close()

    async def send_message(self, text: str) -> None:
        if not text:
            return
        for chat_id in self._chat_ids:
            try:
                await self._bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    disable_web_page_preview=True,
                )
            except Exception as exc:  # pragma: no cover - best-effort logging
                logger.exception("Failed to send Telegram message to %s: %s", chat_id, exc)


