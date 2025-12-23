import json
import subprocess
import shutil
import time
import httpx
from pathlib import Path
from typing import List, Dict
from openai import OpenAI
from .config import settings


class MatchProcessor:
    def __init__(self, input_file: Path):
        self.input_file = input_file
        # Создаем папку reports/имя_файла
        self.output_dir = Path(settings.OUTPUT_DIR) / input_file.stem
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Берем длину куска из конфига (по дефолту 300 сек)
        self.chunk_len = settings.CHUNK_LENGTH

        # Настройка прокси (если есть в .env)
        http_client = None
        if settings.PROXY_URL:
            print(f"🌍 Using Proxy: {settings.PROXY_URL}")
            http_client = httpx.Client(
                proxy=settings.PROXY_URL,
                timeout=120.0  # Увеличенный таймаут для тяжелых файлов
            )

            self.audio_client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=settings.API_KEY,
                http_client=http_client
            )

            llm_base = settings.LLM_API_BASE_URL or settings.API_BASE_URL
            llm_key = settings.LLM_API_KEY or settings.API_KEY

            self.llm_client = OpenAI(
                base_url=llm_base,
                api_key=llm_key,
                http_client=http_client
            )
            if settings.LLM_API_BASE_URL:
                print(f"🧠 LLM Client connected to: {settings.LLM_API_BASE_URL}")

    def split_audio(self) -> List[Path]:
        """Режет и сжимает аудио, чтобы не превышать лимиты API (25MB)"""
        print(f"🔪 Нарезаем {self.input_file.name}...")
        segment_pattern = self.output_dir / "part_%03d.mp3"

        cmd = [
            "ffmpeg", "-y",
            "-i", str(self.input_file),
            "-f", "segment",
            "-segment_time", str(self.chunk_len),
            # Сжимаем в моно 16кГц для легкости (Whisper этого достаточно)
            "-ac", "1", "-ar", "16000", "-c:a", "libmp3lame", "-b:a", "48k",
            "-vn", "-loglevel", "error",
            str(segment_pattern)
        ]
        subprocess.run(cmd, check=True)
        return sorted(self.output_dir.glob("part_*.mp3"))

    def transcribe_chunk(self, file_path: Path):
        """Запрос к Whisper с умным ожиданием лимитов"""
        # Увеличиваем количество попыток до 5
        max_retries = 5

        for attempt in range(max_retries):
            try:
                with open(file_path, "rb") as f:
                    return self.audio_client.audio.transcriptions.create(
                        file=f,
                        model=settings.WHISPER_MODEL,
                        language="ru",
                        response_format="verbose_json"
                    )
            except Exception as e:
                error_str = str(e)

                if "429" in error_str or "Rate limit" in error_str:
                    wait_time = 60 * (attempt + 1)
                    print(f"⚠️ Rate Limit (Groq 429). Ждем {wait_time} сек... (Попытка {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)

                elif "Connection error" in error_str:
                    print(f"⚠️ Ошибка сети. Ждем 10 сек... (Попытка {attempt + 1}/{max_retries})")
                    time.sleep(10)

                else:
                    print(f"⚠️ Ошибка транскрибации: {e}")
                    time.sleep(5)

        print(f"❌ Не удалось транскрибировать {file_path.name} после {max_retries} попыток.")
        return None

    def analyze_text(self, text_with_timestamps: str) -> Dict:
        """Твой оригинальный промпт для анализа"""
        system_instruction = """
        Ты — интеллектуальный спортивный обозреватель.
        Твоя задача — создать хронику матча, выделив ВСЕ значимые эпизоды.
        Твой главный критерий отбора: "Достойно ли это попасть в видео-обзор матча?"

        КРИТЕРИИ ЗНАЧИМОСТИ:
        1. Влияние на счет (Голы, отмененные голы).
        2. Острота (Удары, сейвы вратарей, штанги, перекладины, опасные прострелы).
        3. Дисциплина и конфликты (Карточки, потасовки, споры с судьей, грубые фолы).
        4. Изменения в игре (Замены, травмы).
        5. Эмоциональные моменты (Красивые финты, ошибки защиты, реакция трибун).

        ИГНОРИРОВАТЬ:
        1. Ретроспективы ("А помните 2010 год...").
        2. Повторы обсуждений.
        3. Рутину (пас ради паса, ауты).

        ОБЯЗАТЕЛЬНО ОТВЕЧАЙ В ФОРМАТЕ JSON:
        {
          "events": [
            {
              "time": "ММ:СС",
              "type": "Короткий тег (ГОЛ, СЕЙВ, ФОЛ, АТАКА)",
              "description": "Живое описание того, что произошло"
            }
          ]
        }
        """

        try:
            response = self.llm_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": f"Фрагмент матча:\n{text_with_timestamps}"}
                ],
                model=settings.LLM_MODEL,
                response_format={"type": "json_object"},
                temperature=0.1,
            )

            # Очистка от Markdown (важно для Llama 3)
            content = response.choices[0].message.content
            if content.startswith("```"):
                content = content.replace("```json", "").replace("```", "").strip()

            return json.loads(content)
        except Exception as e:
            print(f"Ошибка LLM или парсинга JSON: {e}")
            return {"events": []}

    def run(self):
        # 1. Нарезка
        chunks = self.split_audio()
        full_report = []

        print(f"🚀 Обрабатываем {len(chunks)} сегментов...")

        for i, chunk_path in enumerate(chunks):
            # Пропуск пустых файлов
            if chunk_path.stat().st_size < 1000:
                continue

            # 2. Транскрибация
            result = self.transcribe_chunk(chunk_path)
            if not result:
                continue

            # 3. Сборка текста с АБСОЛЮТНЫМ временем
            chunk_offset_seconds = i * self.chunk_len
            formatted_lines = []

            # Безопасное получение списка сегментов
            if isinstance(result, dict):
                segments = result.get('segments', [])
            else:
                segments = getattr(result, 'segments', [])

            for seg in segments:
                # Безопасное получение start и text
                if isinstance(seg, dict):
                    start = seg.get('start', 0)
                    text = seg.get('text', '')
                else:
                    start = getattr(seg, 'start', 0)
                    text = getattr(seg, 'text', '')

                # Считаем время
                abs_time = chunk_offset_seconds + start
                mm = int(abs_time // 60)
                ss = int(abs_time % 60)

                formatted_lines.append(f"[{mm:02d}:{ss:02d}] {text}")

            full_text_chunk = "\n".join(formatted_lines)

            # Если текста мало, пропускаем
            if len(full_text_chunk) < 50:
                continue

            # 4. Анализ LLM
            print(f"🧠 Анализ фрагмента {i + 1}/{len(chunks)}...")
            analysis = self.analyze_text(full_text_chunk)

            if analysis.get("events"):
                for evt in analysis["events"]:
                    t = evt.get('time', '??:??')
                    d = evt.get('description', '') or evt.get('event', '')
                    print(f"⚽ [{t}] {d}")

                full_report.extend(analysis["events"])

        # 5. Очистка
        shutil.rmtree(self.output_dir, ignore_errors=True)
        return full_report