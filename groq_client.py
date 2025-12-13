import httpx
from groq import Groq
from config import settings

# 1. Настраиваем HTTP-клиент с SOCKS5 прокси
# Это заставляет запросы идти через твой SSH-туннель
proxies = "socks5://127.0.0.1:1080"

http_client = httpx.Client(
    proxy=proxies,
    timeout=60.0,  # Увеличенный тайм-аут для загрузки аудиофайлов
)

# 2. Инициализируем клиента Groq
# api_key берется из config.py (который читает .env)
client = Groq(
    api_key=settings.GROQ_API_KEY,
    base_url=settings.GROQ_BASE_URL, # https://api.groq.com
    http_client=http_client,
)

# --- Блок для быстрой проверки связи ---
if __name__ == "__main__":
    try:
        print("📡 Проверка связи с Groq через туннель...")
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": "Привет! Ответь одним словом: работает?",
                }
            ],
            model="llama-3.1-8b-instant",
        )
        print("✅ Ответ от Groq:", chat_completion.choices[0].message.content)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        print("Убедись, что запущен SSH туннель: ssh -D 1080 ...")