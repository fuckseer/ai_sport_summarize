import asyncio
import os
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
from .config import settings
from .downloader import download_video
from .processor import MatchProcessor

# Инициализация
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()


async def process_video_task(message: types.Message, url: str):
    """Тяжелая задача, которая выполняется в отдельном потоке"""
    status_msg = await message.answer("⏳ Скачиваю видео...")

    try:
        # 1. Скачивание (в отдельном потоке, чтобы не блочить бота)
        # yt-dlp синхронный, поэтому оборачиваем в to_thread
        audio_path = await asyncio.to_thread(download_video, url)

        await status_msg.edit_text("🔪 Нарезаю и транскрибирую (это займет время)...")

        # 2. Обработка
        processor = MatchProcessor(audio_path)
        # processor.run() тоже синхронный и долгий
        report = await asyncio.to_thread(processor.run)

        # 3. Формирование отчета
        await status_msg.edit_text("✅ Анализ завершен! Формирую отчет...")

        # Отправляем краткий текст в чат
        summary_text = "📊 **Хайлайты матча:**\n\n"
        for event in report:
            time = event.get('time', '??:??')
            etype = event.get('type', 'Событие')
            desc = event.get('description', '') or event.get('event', '')
            line = f"⏱ {time} | <b>{etype}</b>: {desc}\n"
            if len(summary_text) + len(line) < 4000:
                summary_text += line
            else:
                summary_text += "...\n(полный отчет в файле)"
                break

        await message.answer(summary_text, parse_mode="HTML")

        # 4. Отправляем JSON файл
        json_path = audio_path.with_suffix('.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        await message.answer_document(
            FSInputFile(json_path, filename=f"report_{audio_path.stem}.json")
        )

        # Чистка
        os.remove(audio_path)
        os.remove(json_path)

    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка: {str(e)}")


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! 👋\n"
        "Я бот-аналитик матчей. Отправь мне ссылку на YouTube/Twitch видео, "
        "и я сделаю транскрибацию и найду хайлайты."
    )


@dp.message(F.text)
async def handle_link(message: types.Message):
    # Простая проверка на ссылку
    if "http" not in message.text:
        await message.answer("Это не похоже на ссылку. Отправь URL видео.")
        return

    # Проверка доступа (если заполнил ALLOWED_USERS в конфиге)
    if settings.ALLOWED_USERS and message.from_user.id not in settings.ALLOWED_USERS:
        await message.answer("⛔ У вас нет доступа к этому боту.")
        return

    # Запускаем обработку, не блокируя бота для других сообщений
    asyncio.create_task(process_video_task(message, message.text))


async def start_bot():
    print("🤖 Бот запущен...")
    await dp.start_polling(bot)