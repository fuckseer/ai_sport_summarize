from __future__ import annotations

import asyncio
import logging
import signal
import contextlib
from contextlib import AsyncExitStack
from typing import AsyncIterator, Dict

from config import AppSettings, get_app_settings
from groq_client import make_groq_client
from stream_capture import StreamAudioCapture
from summarizer_service import SummarizerService
from telegram_bot import TelegramNotifier
from transcriber_service import TranscriptionService



logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sport_commentator")


async def _stream_transcripts(
    transcriber: TranscriptionService,
    capture: StreamAudioCapture,
) -> AsyncIterator[Dict[str, str]]:
    async for transcript in transcriber.run(capture.audio_chunks()):
        yield transcript


async def run_pipeline(settings: AppSettings) -> None:
    groq_client = make_groq_client(settings.groq)
    transcriber = TranscriptionService(groq_client)
    summarizer = SummarizerService(
        groq_client=groq_client,
        summary_interval_seconds=settings.summary_interval_seconds,
    )

    shutdown_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _request_shutdown() -> None:
        if not shutdown_event.is_set():
            logger.info("Shutdown signal received, stopping gracefully...")
            shutdown_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, _request_shutdown)

    async with AsyncExitStack() as stack:
        notifier = await stack.enter_async_context(TelegramNotifier(settings.telegram))
        stream_capture = await stack.enter_async_context(StreamAudioCapture(settings.stream))

        async for transcript in _stream_transcripts(transcriber, stream_capture):
            events = await summarizer.process_transcript(transcript)
            for event in events:
                await notifier.send_message(event["text"])
            if shutdown_event.is_set():
                break


async def main() -> None:
    try:
        settings = get_app_settings()
    except Exception as exc: 
        logger.error("Failed to load configuration: %s", exc)
        raise SystemExit(1) from exc

    try:
        await run_pipeline(settings)
    except asyncio.CancelledError:
        logger.info("Shutdown requested.")
    except Exception as exc: 
        logger.exception("Fatal pipeline error: %s", exc)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    asyncio.run(main())