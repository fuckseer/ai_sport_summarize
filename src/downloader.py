import yt_dlp
from pathlib import Path
from .config import settings


def download_video(url: str) -> Path:
    """Скачивает видео и возвращает путь к файлу"""
    Path(settings.DOWNLOAD_DIR).mkdir(exist_ok=True, parents=True)

    ydl_opts = {
        'format': 'bestaudio/best',  # Нам нужен звук, так быстрее
        'outtmpl': f'{settings.DOWNLOAD_DIR}/%(id)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': False
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        # yt-dlp меняет расширение после конвертации
        final_path = Path(filename).with_suffix('.mp3')
        return final_path