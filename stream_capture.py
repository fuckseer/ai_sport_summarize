from __future__ import annotations
import asyncio
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import AsyncIterator
from contextlib import suppress

from config import StreamSettings

logger = logging.getLogger("stream_capture")


class StreamAudioCapture:
    """
    Streamlink -> ffmpeg (segment) -> chunk WAV files.
    Uses subprocess.Popen for streamlink to avoid fileno() issues.
    """

    def __init__(self, settings: StreamSettings) -> None:
        self.stream_url = settings.stream_url
        self.tmp_dir = Path(settings.tmp_dir)
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

        self.chunk_duration = settings.chunk_duration_seconds
        self.reconnect_delay = settings.reconnect_delay_seconds
        self._shutdown = False

    async def __aenter__(self):
        logger.info("Starting stream capture for %s", self.stream_url)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        logger.info("Stopping stream capture…")
        self._shutdown = True

    async def audio_chunks(self) -> AsyncIterator[str]:
        """
        Main async generator – reconnects automatically.
        """
        while not self._shutdown:
            try:
                async for p in self._run_session():
                    yield p
            except Exception as exc:
                logger.error("Stream capture crashed: %s | retry in %.1fs",
                             exc, self.reconnect_delay)
                await asyncio.sleep(self.reconnect_delay)

    async def _run_session(self) -> AsyncIterator[str]:
        """
        Launch streamlink via Popen (sync),
        pipe into ffmpeg (async),
        yield chunk files from directory.
        """

        session_dir = Path(tempfile.mkdtemp(prefix="session_", dir=self.tmp_dir))
        chunk_pattern = str(session_dir / "chunk_%03d.wav")

        # --------------------------------------------------------
        # 1) Start streamlink via Popen (sync), NOT asyncio
        # --------------------------------------------------------
        streamlink_cmd = [
            "streamlink",
            "--stdout",
            "--retry-open", "2",
            "--retry-stream", "2",
            self.stream_url,
            "best",
        ]

        logger.info("Starting streamlink…")

        streamlink_proc = subprocess.Popen(
            streamlink_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        if streamlink_proc.stdout is None:
            raise RuntimeError("Streamlink stdout is None!")

        # --------------------------------------------------------
        # 2) ffmpeg reads directly from streamlink_proc.stdout
        # --------------------------------------------------------
        ffmpeg_cmd = [
            "ffmpeg",
            "-loglevel", "error",
            "-i", "pipe:0",
            "-vn",
            "-ac", "1",
            "-ar", "16000",
            "-f", "segment",
            "-segment_time", str(self.chunk_duration),
            "-af", "silencedetect=noise=-50dB:d=0.2,apad",
            chunk_pattern,
        ]

        logger.info("Starting ffmpeg…")

        ffmpeg_proc = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdin=streamlink_proc.stdout,     # real FD — OK
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        last_seen = set()

        try:
            while not self._shutdown:
                chunk_files = sorted(session_dir.glob("chunk_*.wav"))

                for f in chunk_files:
                    if f not in last_seen:
                        # allow ffmpeg to finish writing
                        await asyncio.sleep(0.05)

                        size = f.stat().st_size
                        if size > 2000:
                            yield str(f)
                        else:
                            logger.warning("Ignoring silent/tiny chunk %s (%d bytes)", f, size)

                        last_seen.add(f)

                # If ffmpeg died — break and restart
                if ffmpeg_proc.returncode is not None:
                    raise RuntimeError(f"ffmpeg exited {ffmpeg_proc.returncode}")

                await asyncio.sleep(0.2)

        finally:
            logger.info("Cleaning up streamlink and ffmpeg…")

            with suppress(Exception):
                streamlink_proc.kill()
            with suppress(Exception):
                ffmpeg_proc.terminate()

