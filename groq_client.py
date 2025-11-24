from __future__ import annotations

import asyncio
import json
import logging
import random
from typing import Any, Dict, Optional

from groq import Groq

from config import GroqSettings

logger = logging.getLogger(__name__)


class GroqClientAdapter:
    """Thin async wrapper over the blocking Groq Python SDK."""

    def __init__(self, settings: GroqSettings, max_retries: int = 3) -> None:
        self.settings = settings
        self.client = Groq(
            api_key=settings.api_key,
            base_url=settings.base_url,
        )
        self._max_retries = max_retries

    async def transcribe_audio_chunk(
        self,
        file_path: str,
        language: Optional[str] = None,
    ) -> str:
        """Send an audio chunk to Groq Whisper and return plain text."""

        async def _call() -> str:
            def _blocking_call() -> str:
                with open(file_path, "rb") as audio_file:
                    return self.client.audio.transcriptions.create(
                        file=audio_file,
                        model=self.settings.whisper_model,
                        response_format="text",
                        language=language or self.settings.language,
                    )

            return await asyncio.to_thread(_blocking_call)

        return await self._retry(_call, op_name="whisper_transcription")

    async def analyze_text_chunk(
        self,
        text: str,
        context_state: Optional[Dict[str, Any]] = None,
        summary_interval_seconds: int = 300,
    ) -> Dict[str, Any]:
        """Invoke the Groq LLM to classify urgent events and summaries."""

        payload = {
            "recent_transcript": text,
            "context_state": context_state or {},
            "summary_interval_seconds": summary_interval_seconds,
        }

        system_prompt = (
            "Ты — опытный футбольный комментатор-аналитик. "
            "Твоя задача — мгновенно подсвечивать значимые игровые события и "
            "периодически формировать краткие сводки. "
            "Игнорируй оффтоп, рекламу и болтовню. "
            "Всегда отвечай строгим JSON без лишнего текста."
        )

        async def _call() -> Dict[str, Any]:
            def _blocking_call() -> Dict[str, Any]:
                response = self.client.chat.completions.create(
                    model=self.settings.llm_model,
                    temperature=0.2,
                    max_tokens=400,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": json.dumps(payload, ensure_ascii=False),
                        },
                    ],
                )
                content = response.choices[0].message.content
                return self._parse_llm_json(content)

            return await asyncio.to_thread(_blocking_call)

        return await self._retry(_call, op_name="llm_analysis")

    async def _retry(self, func, op_name: str) -> Any:
        """Retry helper with exponential backoff."""
        attempt = 0
        delay = 1.0
        while True:
            attempt += 1
            try:
                return await func()
            except Exception as exc:  # pragma: no cover - defensive logging
                if attempt >= self._max_retries:
                    logger.exception("Groq %s failed after %s attempts", op_name, attempt)
                    raise
                logger.warning(
                    "Groq %s attempt %s/%s failed: %s. Retrying in %.1fs",
                    op_name,
                    attempt,
                    self._max_retries,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
                delay *= 2 + random.random()

    @staticmethod
    def _parse_llm_json(content: Optional[str]) -> Dict[str, Any]:
        """Parse and validate the JSON payload returned by the LLM."""
        default_response = {
            "is_urgent_event": False,
            "urgent_event_text": "",
            "should_emit_summary": False,
            "summary_text": "",
            "updated_context_state": {},
        }
        if not content:
            return default_response
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            logger.warning("LLM returned invalid JSON: %s :: %s", content, exc)
            return default_response

        for key in default_response:
            parsed.setdefault(key, default_response[key])
        return parsed


def make_groq_client(settings: GroqSettings) -> GroqClientAdapter:
    """Factory to create the Groq client adapter."""
    return GroqClientAdapter(settings=settings)


