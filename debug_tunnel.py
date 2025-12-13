import httpx
import sys

# Настройки прокси (ваш SSH туннель)
PROXY_URL = "socks5://127.0.0.1:1080"

print(f"--- НАЧАЛО ДИАГНОСТИКИ ---")
print(f"ОС: {sys.platform}")
print(f"Прокси: {PROXY_URL}")

try:
    # Проверяем, установлена ли поддержка socks
    import socksio
    print("✅ Библиотека socksio найдена.")
except ImportError:
    print("❌ ОШИБКА: Библиотека socksio НЕ найдена!")
    print("Вам нужно выполнить команду:")
    print('pip install "httpx[socks]"')
    sys.exit(1)

print("\n1. Пробуем подключиться к Google через туннель...")
try:
    with httpx.Client(proxy=PROXY_URL, timeout=5.0) as client:
        resp = client.get("https://www.google.com")
        print(f"✅ Успех! Google ответил кодом: {resp.status_code}")
except httpx.ProxyError:
    print("❌ ОШИБКА ПРОКСИ: Не удалось подключиться к 127.0.0.1:1080")
    print("Причины:")
    print("1. SSH-туннель НЕ запущен.")
    print("2. SSH-туннель запущен, но упал.")
    print("РЕШЕНИЕ: Откройте отдельное окно терминала и запустите:")
    print("ssh -D 1080 -N -q root@72.56.67.27")
    sys.exit(1)
except Exception as e:
    print(f"❌ ОШИБКА СОЕДИНЕНИЯ: {e}")
    sys.exit(1)

print("\n2. Пробуем подключиться к Groq API...")
try:
    with httpx.Client(proxy=PROXY_URL, timeout=10.0) as client:
        # Groq может вернуть 404 на корень, это нормально, главное - коннект есть
        resp = client.get("https://api.groq.com")
        print(f"✅ Успех! Groq API доступен. Код ответа: {resp.status_code}")
except Exception as e:
    print(f"❌ Ошибка при доступе к Groq: {e}")

print("\n--- ДИАГНОСТИКА ЗАВЕРШЕНА ---")