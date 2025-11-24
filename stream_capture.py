from __future__ import annotations

import asyncio
import contextlib
import logging
import shutil
from pathlib import Path
from typing import AsyncIterator, Optional, Set

from config import StreamSettings

logger = logging.getLogger(__name__)

CHUNK_FILENAME_PATTERN = "chunk_%Y%m%d_%H%M%S.wav"


class StreamAudioCapture:
    """Capture audio chunks from an arbitrary stream using streamlink + ffmpeg."""

    def __init__(self, settings: StreamSettings) -> None:
        self.settings = settings
        self.tmp_dir = settings.tmp_dir
        self.chunk_duration = max(5, settings.chunk_duration_seconds)
        self.reconnect_delay = max(1.0, settings.reconnect_delay_seconds)
        self._streamlink_proc: Optional[asyncio.Process] = None
        self._ffmpeg_proc: Optional[asyncio.Process] = None
        self._pump_task: Optional[asyncio.Task[None]] = None
        self._closing = False
        self._seen_files: Set[str] = set()

    async def __aenter__(self) -> "StreamAudioCapture":
        await self._start_pipeline()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def close(self) -> None:
        self._closing = True
        await self._stop_pipeline()
        await self._cleanup_tmp_dir()

    async def audio_chunks(self) -> AsyncIterator[str]:
        """Yield freshly created audio chunk file paths."""
        while not self._closing:
            await self._ensure_pipeline_alive()
            new_chunks = await self._collect_new_chunks()
            if not new_chunks:
                await asyncio.sleep(1)
                continue

            for chunk in new_chunks:
                if self._closing:
                    break
                logger.debug("Yielding audio chunk %s", chunk)
                try:
                    yield str(chunk)
                finally:
                    with contextlib.suppress(FileNotFoundError):
                        chunk.unlink()

    async def _start_pipeline(self) -> None:
        logger.info("Starting stream capture for %s", self.settings.stream_url)
        await self._stop_pipeline()
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        await self._cleanup_tmp_dir()

        self._streamlink_proc = await asyncio.create_subprocess_exec(
            "streamlink",
            "--stdout",
            self.settings.stream_url,
            "best",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._ffmpeg_proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-loglevel",
            "error",
            "-i",
            "pipe:0",
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-f",
            "segment",
            "-segment_time",
            str(self.chunk_duration),
            "-segment_format",
            "wav",
            "-reset_timestamps",
            "1",
            "-strftime",
            "1",
            str(self.tmp_dir / CHUNK_FILENAME_PATTERN),
            stdin=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._pump_task = asyncio.create_task(self._pipe_streamlink_to_ffmpeg())

    async def _stop_pipeline(self) -> None:
        if self._pump_task:
            self._pump_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._pump_task
        for proc in (self._streamlink_proc, self._ffmpeg_proc):
            if proc and proc.returncode is None:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5)
                except asyncio.TimeoutError:
                    proc.kill()
        self._streamlink_proc = None
        self._ffmpeg_proc = None
        self._pump_task = None
        self._seen_files.clear()

    async def _pipe_streamlink_to_ffmpeg(self) -> None:
        assert self._streamlink_proc and self._ffmpeg_proc
        assert self._streamlink_proc.stdout and self._ffmpeg_proc.stdin
        reader = self._streamlink_proc.stdout
        writer = self._ffmpeg_proc.stdin
        try:
            while not reader.at_eof():
                data = await reader.read(64 * 1024)
                if not data:
                    break
                writer.write(data)
                await writer.drain()
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover - defensive log
            logger.exception("Streamlink->ffmpeg pipe failed: %s", exc)
        finally:
            with contextlib.suppress(Exception):
                writer.write_eof()

    async def _collect_new_chunks(self) -> list[Path]:
        files = sorted(self.tmp_dir.glob("chunk_*.wav"))
        new_files = [path for path in files if path.name not in self._seen_files]
        ready_files: list[Path] = []
        for path in new_files:
            # Ensure the file is closed by checking size stability
            size_before = path.stat().st_size
            await asyncio.sleep(0.1)
            size_after = path.stat().st_size
            if size_before == size_after:
                self._seen_files.add(path.name)
                ready_files.append(path)
        return ready_files

    async def _ensure_pipeline_alive(self) -> None:
        restart_needed = False
        if self._streamlink_proc and self._streamlink_proc.returncode not in (0, None):
            logger.warning("streamlink exited with %s", self._streamlink_proc.returncode)
            restart_needed = True
        if self._ffmpeg_proc and self._ffmpeg_proc.returncode not in (0, None):
            logger.warning("ffmpeg exited with %s", self._ffmpeg_proc.returncode)
            restart_needed = True
        if restart_needed:
            await self._restart_pipeline()

    async def _restart_pipeline(self) -> None:
        if self._closing:
            return
        logger.info("Restarting capture pipeline in %.1fs", self.reconnect_delay)
        await self._stop_pipeline()
        await asyncio.sleep(self.reconnect_delay)
        await self._start_pipeline()

    async def _cleanup_tmp_dir(self) -> None:
        if not self.tmp_dir.exists():
            return
        for path in self.tmp_dir.glob("*.wav"):
            with contextlib.suppress(FileNotFoundError):
                path.unlink()
        if self._closing:
            with contextlib.suppress(OSError):
                shutil.rmtree(self.tmp_dir)

