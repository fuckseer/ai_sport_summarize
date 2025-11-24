from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from openai import OpenAI
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)


class SummaryDecision(BaseModel):
    flash_alert: Optional[str] = None
    period_summary: Optional[str] = None


@dataclass(slots=True)
class SmartSummarizerConfig:
    api_key: str
    model: str = "gpt-4o-mini"
    summary_interval: timedelta = timedelta(minutes=5)
    flash_keywords: List[str] = field(default_factory=lambda: ["goal", "penalty", "red card"])
    context_window_chars: int = 3_000
    max_summary_bullets: int = 4


class SmartSummarizer:
    """
    Maintains rolling transcript context, detects urgent events, and produces periodic summaries.
    """

    def __init__(self, config: SmartSummarizerConfig) -> None:
        self.config = config
        self._client = OpenAI(api_key=config.api_key)
        self._context_buffer: List[str] = []
        self._period_context: List[str] = []
        self._context_char_count = 0
        self._last_summary_time = datetime.now(timezone.utc)

    async def process_transcript(self, text_chunk: str) -> SummaryDecision:
        decision = SummaryDecision()
        cleaned_chunk = text_chunk.strip()
        if not cleaned_chunk:
            return decision

        now = datetime.now(timezone.utc)
        self._append_to_context(cleaned_chunk)

        if self._contains_flash_keyword(cleaned_chunk):
            decision.flash_alert = f"⚡️ {cleaned_chunk}"

        analysis = await self._analyze_with_llm(cleaned_chunk)
        if analysis and analysis.get("is_urgent_event") and not decision.flash_alert:
            decision.flash_alert = f"⚽️ {analysis.get('event_description', cleaned_chunk)}"

        if analysis and analysis.get("game_context_summary"):
            self._period_context.append(analysis["game_context_summary"])

        if now - self._last_summary_time >= self.config.summary_interval:
            summary = await self._build_period_summary()
            if summary:
                decision.period_summary = summary
                self._period_context.clear()
                self._last_summary_time = now

        return decision

    def _append_to_context(self, chunk: str) -> None:
        self._context_buffer.append(chunk)
        self._context_char_count += len(chunk)
        while self._context_buffer and self._context_char_count > self.config.context_window_chars:
            removed = self._context_buffer.pop(0)
            self._context_char_count = max(0, self._context_char_count - len(removed))

    def _contains_flash_keyword(self, text: str) -> bool:
        lowered = text.lower()
        return any(keyword.lower() in lowered for keyword in self.config.flash_keywords)

    async def _analyze_with_llm(self, chunk: str) -> Optional[dict]:
        prompt = (
            "Ты — аналитик футбольного матча. Проанализируй транскрипт и ответь строго JSON.\n"
            "JSON поля: {\"is_urgent_event\": bool, \"event_description\": str, \"game_context_summary\": str}.\n"
            "Правила:\n"
            "1. Устанавливай is_urgent_event=true только если произошло важное событие (гол, пенальти, удаление).\n"
            "2. event_description — короткое предложение на русском.\n"
            "3. game_context_summary — 1-2 предложения о ходе игры на русском.\n"
            "4. Если данных недостаточно, ставь is_urgent_event=false и оставляй пустые строки.\n"
            "Текущий фрагмент:\n"
            f"{chunk}\n\n"
            "Контекст последних сообщений:\n"
            f"{' '.join(self._context_buffer[-5:])}"
        )

        try:
            response_text = await asyncio.to_thread(self._request_llm, prompt)
            return json.loads(response_text)
        except json.JSONDecodeError:
            logger.warning("LLM returned non-JSON payload: %s", response_text)
            return None
        except Exception as exc:
            logger.exception("LLM analysis failed: %s", exc)
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def _request_llm(self, prompt: str) -> str:
        response = self._client.responses.create(
            model=self.config.model,
            input=[
                {
                    "role": "system",
                    "content": "Ты профессиональный спортивный журналист. Всегда отвечай JSON без пояснений.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return response.output[0].content[0].text.strip()

    async def _build_period_summary(self) -> Optional[str]:
        if not self._period_context:
            return None

        bullet_prompt = (
            "Сформируй краткую сводку матча на русском в виде маркированного списка (• ...).\n"
            f"Не более {self.config.max_summary_bullets} пунктов. Отрази нападения, опасные моменты, тренды.\n"
            "Если информации недостаточно, верни одну строку '• Мало данных для сводки'.\n"
            "Контекст:\n"
            f"{' '.join(self._period_context)}"
        )

        try:
            summary_text = await asyncio.to_thread(self._request_summary, bullet_prompt)
            return summary_text
        except Exception as exc:
            logger.exception("Failed to build period summary: %s", exc)
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def _request_summary(self, prompt: str) -> str:
        response = self._client.responses.create(
            model=self.config.model,
            input=[
                {
                    "role": "system",
                    "content": "Ты спортивный журналист. Пиши по-русски. Форматируй маркерами.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
        )
        return response.output[0].content[0].text.strip()

