from __future__ import annotations

import asyncio
import logging
import os
from typing import AsyncIterator, Dict

from groq_client import GroqClientAdapter

logger = logging.getLogger(__name__)


class TranscriptionService:
    """
    Consumes audio chunk file paths from StreamAudioCapture and sends them
    to Groq Whisper via GroqClientAdapter. Skips empty or invalid chunks.
    """

    def __init__(self, client: GroqClientAdapter) -> None:
        self._client = client

    async def run(
        self,
        audio_chunk_iter: AsyncIterator[str],
    ) -> AsyncIterator[Dict[str, str]]:
        """
        The main async loop: receives file paths for wav chunks,
        ensures they contain audio data, and yields transcription dicts.
        """

        async for file_path in audio_chunk_iter:
            # ----------------------------------------------------------
            # FIX #1: skip empty files (MatchTV often produces silent HLS segments)
            # ----------------------------------------------------------
            if not os.path.exists(file_path):
                logger.warning("Audio chunk does not exist, skipping: %s", file_path)
                continue

            file_size = os.path.getsize(file_path)
            if file_size < 500:  # 500 bytes is minimal valid WAV with real PCM
                logger.warning("Skipping empty audio chunk (%d bytes): %s", file_size, file_path)
                continue

            # ----------------------------------------------------------
            # FIX #2: small delay to ensure ffmpeg closes/flushed file
            # ----------------------------------------------------------
            await asyncio.sleep(0.03)

            try:
                text = await self._client.transcribe_audio_chunk(file_path)
            except Exception as exc:
                logger.error("Failed to transcribe %s: %s", file_path, exc)
                continue

            if not text or not text.strip():
                logger.warning("Whisper returned empty transcript for %s", file_path)
                continue

            yield {
                "text": text.strip(),
                "file_path": file_path,
            }

    # Convenience helper if you want to transcribe a single one-shot file
    async def run_single_chunk(self, file_path: str) -> Dict[str, str]:
        """
        Process a single file path (used occasionally in the pipeline).
        """
        if not os.path.exists(file_path) or os.path.getsize(file_path) < 500:
            logger.warning("Skipping empty audio chunk in single mode: %s", file_path)
            return {"text": "", "file_path": file_path}

        await asyncio.sleep(0.03)

        try:
            text = await self._client.transcribe_audio_chunk(file_path)
        except Exception as exc:
            logger.error("Failed to transcribe %s: %s", file_path, exc)
            return {"text": "", "file_path": file_path}

        return {"text": text.strip(), "file_path": file_path}

