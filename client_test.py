import requests
import socks
import asyncio
from telethon import TelegramClient

API_ID = '28903747'
API_HASH = 'f775a7c89795085b867066093060fc59'
BASE_URL = "http://localhost:8000"

async def main():
    # 1. Запрос сессии из API
    resp = requests.get(f"{BASE_URL}/session")
    data = resp.json()
    if "error" in data:
        print("Нет доступных сессий:", data["error"])
        return
    
    session_name = data["session_name"]
    session_id = data["session_id"]
    proxy_info = data.get("proxy")

    # 2. Настройка Telethon-клиента с прокси
    proxy = None
    if proxy_info:
        if proxy_info["type"].lower() == "socks5":
            proxy = (socks.SOCKS5, proxy_info["host"], proxy_info["port"], True,
                     proxy_info.get("user"), proxy_info.get("pass"))
        elif proxy_info["type"].lower() in ("http", "https"):
            proxy = (socks.HTTP, proxy_info["host"], proxy_info["port"])

    session_path = f"/home/ssilantev/TeleGate/telethon_sessions/{session_name}.session"
    client = TelegramClient(session_path, API_ID, API_HASH, proxy=proxy)

    # 3. Подключение и выполнение операций
    try:
        await client.connect()  # ✅ Добавлено await

        if not await client.is_user_authorized():  # ✅ Добавлено await
            print("Сессия не авторизована. Требуется вход в аккаунт.")
        else:
            me = await client.get_me()  # ✅ Добавлено await
            print("Успешно получена сессия. Аккаунт:", me.username or me.first_name)

    except Exception as e:
        import re
        if 'FloodWaitError' in str(e):
            m = re.search(r'(\d+) seconds', str(e))
            wait_seconds = int(m.group(1)) if m else 0
            print(f"Flood wait detected: необходимо ждать {wait_seconds} сек.")
            requests.post(f"{BASE_URL}/session/return", params={"session_id": session_id, "flood_wait": wait_seconds})
        else:
            print("Ошибка при работе с сессией:", e)
            requests.post(f"{BASE_URL}/session/invalidate", params={"session_id": session_id})

    else:
        requests.post(f"{BASE_URL}/session/return", params={"session_id": session_id})

    finally:
        await client.disconnect()  # ✅ Добавлено await

# Запуск асинхронного кода
asyncio.run(main())
