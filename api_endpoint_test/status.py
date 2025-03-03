"""
status.py

Этот модуль тестирует эндпоинт GET /status вашего API.
Эндпоинт возвращает агрегированную статистику по пулу сессий:
  - Общее количество сессий
  - Количество свободных сессий
  - Количество занятых сессий
  - Количество сессий в состоянии Flood Wait
  - Время, когда ближайшая сессия выйдет из Flood Wait (если есть)
  
Для авторизации в запросе передается заголовок X-API-Key.
"""

import requests

# Задаем базовый URL сервиса и API-ключ для авторизации
BASE_URL = "http://178.238.114.132:52057"
API_KEY = "734f1f98137cc7dd341eee8148d73f1a0e6df6edd8b7dc627b66ea2312dc3be6"

def test_status():
    """
    Отправляет GET-запрос на эндпоинт /status и выводит статус-код ответа и JSON.
    """
    url = f"{BASE_URL}/status"
    headers = {"X-API-Key": API_KEY}
    # Выполняем GET-запрос
    response = requests.get(url, headers=headers)
    print("Endpoint: /status")
    print("Response Code:", response.status_code)
    try:
        # Пытаемся распарсить ответ как JSON
        print("Response JSON:", response.json())
    except Exception as e:
        print("Ошибка при парсинге JSON:", e)

if __name__ == '__main__':
    test_status()
