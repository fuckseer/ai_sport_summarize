from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict

from groq_client import GroqClientAdapter

logger = logging.getLogger(__name__)


class TranscriptionService:
    """Service that streams audio chunks to Groq Whisper and yields transcripts."""

    def __init__(self, groq_client: GroqClientAdapter) -> None:
        self._client = groq_client

    async def run(
        self,
        audio_chunk_iter: AsyncIterator[str],
    ) -> AsyncIterator[Dict[str, Any]]:
        """Consume audio file paths and yield transcription dictionaries."""
        async for file_path in audio_chunk_iter:
            started_at = datetime.now(timezone.utc)
            try:
                text = await self._client.transcribe_audio_chunk(file_path)
            except Exception as exc:  # pragma: no cover - defensive log
                logger.exception("Failed to transcribe %s: %s", file_path, exc)
                continue

            transcript = {
                "start_time": started_at.isoformat(),
                "end_time": datetime.now(timezone.utc).isoformat(),
                "text": text.strip(),
            }
            if transcript["text"]:
                yield transcript

