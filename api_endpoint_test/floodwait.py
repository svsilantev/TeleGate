import requests

# Задаем базовый URL сервиса и API-ключ для авторизации
BASE_URL = "http://178.238.114.132:52057"
API_KEY = "734f1f98137cc7dd341eee8148d73f1a0e6df6edd8b7dc627b66ea2312dc3be6"

def test_floodwait():
    """
    Этот модуль тестирует эндпоинт POST /floodwait вашего API.
    Эндпоинт устанавливает состояние Flood Wait для указанной сессии:
      - session_id: идентификатор сессии для обработки ошибки FloodWaitError
      - wait_seconds: время ожидания (например, 4593 секунд)
      
    Для авторизации в запросе передается заголовок X-API-Key.
    """
    url = f"{BASE_URL}/floodwait"
    headers = {"X-API-Key": API_KEY}
    # Укажите актуальный session_id для теста, здесь используется примерное значение 1
    params = {
        "session_id": 15,
        "wait_seconds": 4593
    }
    response = requests.post(url, headers=headers, params=params)
    print("Endpoint: /floodwait")
    print("Response Code:", response.status_code)
    try:
        print("Response JSON:", response.json())
    except Exception as e:
        print("Ошибка при парсинге JSON:", e)

if __name__ == '__main__':
    test_floodwait()
