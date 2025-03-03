"""
release.py

Этот модуль тестирует эндпоинт POST /release.
Эндпоинт /release используется для освобождения ранее выданной сессии,
возвращая ее обратно в пул.

Для авторизации используется заголовок X-API-Key.
При запуске модуль запрашивает session_id (либо принимает как аргумент командной строки),
после чего отправляет POST-запрос для освобождения указанной сессии.
"""

import requests
import sys

BASE_URL = "http://178.238.114.132:52057"
API_KEY = "734f1f98137cc7dd341eee8148d73f1a0e6df6edd8b7dc627b66ea2312dc3be6"

def test_release(session_id):
    """
    Отправляет POST-запрос на эндпоинт /release с заданным session_id.
    Выводит статус ответа и JSON, полученный от сервера.
    
    :param session_id: Идентификатор сессии для освобождения.
    """
    # Формируем URL с query-параметром session_id
    url = f"{BASE_URL}/release?session_id={session_id}"
    headers = {"X-API-Key": API_KEY}
    response = requests.post(url, headers=headers)
    print("Endpoint: /release")
    print("Response Code:", response.status_code)
    try:
        print("Response JSON:", response.json())
    except Exception as e:
        print("Ошибка при парсинге JSON:", e)

if __name__ == '__main__':
    # Если session_id не передан как аргумент, запрашиваем его через input
    if len(sys.argv) < 2:
        session_id = input("Введите session_id для освобождения: ")
    else:
        session_id = sys.argv[1]
    test_release(session_id)