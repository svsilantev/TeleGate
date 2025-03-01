# client.py
import requests
import time
from datetime import datetime

class NoSessionAvailable(Exception):
    """Исключение, выбрасываемое при отсутствии свободных сессий (если авто-ожидание не используется)."""
    def __init__(self, waiting_count, next_release_in):
        super().__init__(f"No free session. In flood wait: {waiting_count}, next available in {next_release_in} sec")
        self.waiting_count = waiting_count
        self.next_release_in = next_release_in

class TelegramSessionManagerClient:
    def __init__(self, base_url, api_key, auto_wait=True):
        """
        base_url: базовый URL сервиса (например, 'http://localhost:8000').
        api_key: API-ключ для авторизации.
        auto_wait: если True, клиентская библиотека будет автоматически ждать освобождения сессии в случае Flood Wait.
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.auto_wait = auto_wait

    def get_session(self):
        """Запрос на получение свободной сессии. Возвращает словарь с данными сессии или выбрасывает исключение/ждет, если нет доступных."""
        url = f"{self.base_url}/session"
        headers = {"X-API-Key": self.api_key}
        response = requests.get(url, headers=headers)
        if response.status_code == 503:
            # Нет свободных сессий, обработка Flood Wait
            data = response.json().get("detail", {})
            waiting = data.get("in_floodwait", 0)
            next_in = data.get("next_release_in", None)
            if self.auto_wait and next_in:
                # Автоматически ждем указанное количество секунд и повторяем запрос
                time_to_wait = int(next_in)
                if time_to_wait > 0:
                    print(f"[Client] No session available. Waiting for {time_to_wait} seconds...")
                    time.sleep(time_to_wait)
                    return self.get_session()  # повторный вызов после ожидания
            # Если авто-ожидание отключено или неизвестно время, бросаем исключение
            raise NoSessionAvailable(waiting_count=waiting, next_release_in=next_in)
        # Если код 200 OK, возвращаем данные сессии
        response.raise_for_status()  # если другой неожиданный статус
        session_data = response.json()
        return session_data  # например, {"session_id": 5, "session_name": "session5"}

    def release_session(self, session_id):
        """Отправляет запрос на освобождение сессии с указанным session_id."""
        url = f"{self.base_url}/release"
        params = {"api_key": self.api_key, "session_id": session_id}
        response = requests.post(url, params=params)
        response.raise_for_status()
        return True  # при успешном выполнении вернём True

    def get_status(self):
        """Получение статуса пула сессий."""
        url = f"{self.base_url}/status"
        params = {"api_key": self.api_key}
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()

# Пример использования клиентской библиотеки:
if __name__ == "__main__":
    client = TelegramSessionManagerClient(base_url="http://178.238.114.132:52057", api_key="8093a9bbf4e0d87cfdac4e629c598a5021fc1c4d6d4c62e879150ccf14132dcf")
    try:
        session = client.get_session()
        print("Получена сессия:", session)
        # ... (здесь могла бы происходить работа с Telegram сессией) ...
        client.release_session(session["session_id"])
        print("Сессия освобождена")
    except NoSessionAvailable as e:
        print("Нет доступных сессий:", e)
