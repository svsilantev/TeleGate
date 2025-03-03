"""
sync.py

Этот модуль тестирует эндпоинт POST /sync.
Эндпоинт /sync используется для синхронизации файлов сессий с записями в базе данных.
При вызове эндпоинта сервис сканирует директорию с файлами сессий и обновляет базу данных.

Для авторизации используется заголовок X-API-Key.
"""

import requests

BASE_URL = "http://178.238.114.132:52057"
API_KEY = "734f1f98137cc7dd341eee8148d73f1a0e6df6edd8b7dc627b66ea2312dc3be6"

def test_sync():
    """
    Отправляет POST-запрос на эндпоинт /sync и выводит статус-код и JSON-ответ.
    """
    url = f"{BASE_URL}/sync"
    headers = {"X-API-Key": API_KEY}
    response = requests.post(url, headers=headers)
    print("Endpoint: /sync")
    print("Response Code:", response.status_code)
    try:
        print("Response JSON:", response.json())
    except Exception as e:
        print("Ошибка при парсинге JSON:", e)

if __name__ == '__main__':
    test_sync()
