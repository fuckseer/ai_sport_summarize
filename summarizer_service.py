from __future__ import annotations

import logging
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List

from groq_client import GroqClientAdapter

logger = logging.getLogger(__name__)


class SummarizerService:
    """Keeps rolling context and decides when to emit flash or summary events."""

    def __init__(
        self,
        groq_client: GroqClientAdapter,
        summary_interval_seconds: int,
    ) -> None:
        self._client = groq_client
        self._summary_interval = summary_interval_seconds
        self._buffer: Deque[str] = deque(maxlen=20)
        self._context_state: Dict[str, Any] = {}
        self._last_summary_at = datetime.now(timezone.utc)

    async def process_transcript(self, transcript_item: Dict[str, Any]) -> List[Dict[str, str]]:
        """Inspect a transcript chunk and return zero or more Telegram-ready events."""
        text = (transcript_item.get("text") or "").strip()
        if not text:
            return []

        self._buffer.append(text)
        combined_text = " ".join(self._buffer)
        seconds_since_summary = (datetime.now(timezone.utc) - self._last_summary_at).total_seconds()

        analysis = await self._client.analyze_text_chunk(
            combined_text,
            context_state={
                **self._context_state,
                "seconds_since_last_summary": seconds_since_summary,
            },
            summary_interval_seconds=self._summary_interval,
        )

        events: List[Dict[str, str]] = []

        if analysis.get("is_urgent_event") and analysis.get("urgent_event_text"):
            flash_text = analysis["urgent_event_text"].strip()
            if flash_text:
                events.append({"type": "flash", "text": flash_text})

        if (
            analysis.get("should_emit_summary")
            and analysis.get("summary_text")
            and seconds_since_summary >= self._summary_interval
        ):
            summary_text = analysis["summary_text"].strip()
            if summary_text:
                events.append({"type": "summary", "text": summary_text})
                self._last_summary_at = datetime.now(timezone.utc)

        updated_state = analysis.get("updated_context_state")
        if isinstance(updated_state, dict):
            self._context_state = updated_state

        # Clear the buffer once we have emitted anything to encourage fresh context.
        if events:
            self._buffer.clear()

        return events


