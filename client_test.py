import requests
import socks
from telethon import TelegramClient

API_ID = '28903747'
API_HASH = 'f775a7c89795085b867066093060fc59'
BASE_URL = "http://localhost:8000"

# 1. Запрос сессии из API
resp = requests.get(f"{BASE_URL}/session")
data = resp.json()
if "error" in data:
    print("Нет доступных сессий:", data["error"])
    exit(1)
session_name = data["session_name"]
session_id = data["session_id"]
proxy_info = data.get("proxy")

# 2. Настройка Telethon-клиента с прокси
proxy = None
if proxy_info:
    # Определяем тип прокси и формируем tuple
    if proxy_info["type"].lower() == "socks5":
        # True в кортеже означает rdns включен
        proxy = (socks.SOCKS5, proxy_info["host"], proxy_info["port"], True,
                 proxy_info.get("user"), proxy_info.get("pass"))
    elif proxy_info["type"].lower() in ("http", "https"):
        proxy = (socks.HTTP, proxy_info["host"], proxy_info["port"])
# Путь к файлу сессии (если нужен полный путь)
session_path = f"/home/ssilantev/TeleGate/telethon_sessions/{session_name}.session"
client = TelegramClient(session_path, API_ID, API_HASH, proxy=proxy)

# 3. Подключение и выполнение операции
try:
    client.connect()
    if not client.is_user_authorized():
        print("Сессия не авторизована. Требуется вход в аккаунт.")
        # В MVP мы предполагаем, что сессия уже авторизована, иначе тут нужен код подтверждения.
    else:
        me = client.get_me()
        print("Успешно получена сессия. Аккаунт:", me.username or me.first_name)
        # Можно отправить тестовое сообщение:
        # client.send_message('me', 'Test message from Telethon')
except Exception as e:
    # Отлавливаем FloodWaitError или другие ошибки
    if 'FloodWaitError' in str(e):
        # Извлекаем количество секунд из текста ошибки, например
        import re
        m = re.search(r'(\d+) seconds', str(e))
        wait_seconds = int(m.group(1)) if m else 0
        print(f"Flood wait detected: необходимо ждать {wait_seconds} сек.")
        # 4. Возврат с указанием Flood Wait
        requests.post(f"{BASE_URL}/session/return", params={"session_id": session_id, "flood_wait": wait_seconds})
    else:
        print("Ошибка при работе с сессией:", e)
        # При ошибке инвалидируем сессию
        requests.post(f"{BASE_URL}/session/invalidate", params={"session_id": session_id})
else:
    # 4. Если всё хорошо, возвращаем сессию без блокировки
    requests.post(f"{BASE_URL}/session/return", params={"session_id": session_id})
finally:
    client.disconnect()
