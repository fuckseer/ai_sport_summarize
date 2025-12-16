import os
import json
import subprocess
import asyncio
import time
from pathlib import Path
from typing import List, Dict

import groq
from tqdm import tqdm
from groq_client import client
from config import settings


class MatchProcessor:
    def __init__(self, input_file: str, output_dir: str = "./match_data"):
        self.input_file = Path(input_file)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.chunk_len = 300  # 5 минут (в секундах)

    def split_audio(self) -> List[Path]:
        """Режет видео/аудио на куски по 5 минут через ffmpeg"""
        print(f"🔪 Нарезаем {self.input_file.name} на сегменты...")

        segment_pattern = self.output_dir / "part_%03d.mp3"

        # ffmpeg команда: берем аудио, режем на куски, кодируем в легкий mp3
        cmd = [
            "ffmpeg", "-y", "-i", str(self.input_file),
            "-f", "segment", "-segment_time", str(self.chunk_len),
            "-c:a", "libmp3lame", "-q:a", "4",  # Хорошее качество, малый вес
            "-vn",  # Без видео
            "-loglevel", "error",
            str(segment_pattern)
        ]
        subprocess.run(cmd, check=True)

        # Собираем созданные файлы
        return sorted(self.output_dir.glob("part_*.mp3"))

    def transcribe_chunk(self, file_path: Path) -> str:
        """Отправляет кусок в Groq Whisper"""
        try:
            with open(file_path, "rb") as f:
                return client.audio.transcriptions.create(
                    file=f,
                    model=settings.WHISPER_MODEL,
                    language="ru",
                    response_format="text"
                )
        except groq.RateLimitError:
            print('limit, wait 3 min')
            time.sleep(180)
            with open(file_path, "rb") as f:
                return client.audio.transcriptions.create(
                    file=f,
                    model=settings.WHISPER_MODEL,
                    language="ru",
                    response_format="text"
                )


    def analyze_text(self, text: str, chunk_index: int) -> Dict:
        """Анализирует текст и извлекает события"""
        start_time = chunk_index * self.chunk_len // 60
        end_time = (chunk_index + 1) * self.chunk_len // 60
        time_range = f"{start_time}-{end_time} мин"

        prompt = f"""
        Ты — спортивный аналитик. Твоя задача — прочитать расшифровку комментария матча ({time_range}) 
        и извлечь ТОЛЬКО ключевые события в формате JSON. Пиши на русском.

        Текст:
        "{text}"

        Правила:
        1. Игнорируй воду, историю игроков, обсуждение погоды.
        2. Ищи: Голы, Опасные удары, Карточки, Замены, Травмы, VAR.
        3. Если событий нет, верни пустой список.
        4. Формат JSON: {{ "events": [ {{ "time": "точное время", "event": "Описание" }} ] }}
        """

        try:
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=settings.LLM_MODEL,
                response_format={"type": "json_object"}
            )
            return json.loads(chat_completion.choices[0].message.content)
        except Exception as e:
            print(f"Ошибка анализа: {e}")
            return {"events": []}

    def process(self):
        # 1. Нарезка
        chunks = self.split_audio()
        full_report = []

        print(f"🚀 Начинаем обработку {len(chunks)} сегментов...")

        # 2. Цикл по кускам
        for i, chunk_path in enumerate(tqdm(chunks, desc="Обработка матча")):
            # Транскрибация
            text = self.transcribe_chunk(chunk_path)

            # Если текст пустой или мусорный - скипаем
            if len(text) < 10:
                continue

            # Анализ
            analysis = self.analyze_text(text, i)

            if analysis.get("events"):
                full_report.extend(analysis["events"])
                # Сразу выводим в консоль, чтобы видеть прогресс
                for evt in analysis["events"]:
                    print(f"⚽ [{evt.get('time', '?')}] {evt.get('event')}")

        # 3. Финальный отчет
        self.save_report(full_report)

    def save_report(self, events):
        report_path = self.output_dir / "final_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Готово! Отчет сохранен в {report_path}")


# Запуск
if __name__ == "__main__":
    # Укажи путь к файлу с матчем (видео или аудио)
    # Можно скачать с YouTube любой обзор на 10-15 минут для теста
    processor = MatchProcessor("match_video.mp4")
    processor.process()