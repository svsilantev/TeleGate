"""
session.py

Этот модуль тестирует эндпоинт GET /session.
Эндпоинт /session выдает клиенту свободную сессию из пула,
возвращая ID, имя сессии, строку сессии и параметры прокси.
При отсутствии свободной сессии сервер возвращает ошибку 503.

Для авторизации используется заголовок X-API-Key.
"""

import requests

BASE_URL = "http://178.238.114.132:52057"
API_KEY = "734f1f98137cc7dd341eee8148d73f1a0e6df6edd8b7dc627b66ea2312dc3be6"

def test_session():
    """
    Отправляет GET-запрос на эндпоинт /session и выводит статус-код и ответ.
    В случае ошибки пытается вывести сообщение об ошибке.
    """
    url = f"{BASE_URL}/session"
    headers = {"X-API-Key": API_KEY}
    response = requests.get(url, headers=headers)
    print("Endpoint: /session")
    print("Response Code:", response.status_code)
    try:
        print("Response JSON:", response.json())
    except Exception as e:
        print("Ошибка при парсинге ответа:", e)

if __name__ == '__main__':
    test_session()
