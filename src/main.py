import asyncio
from src.bot import start_bot

if __name__ == "__main__":
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        print("Бот остановлен")