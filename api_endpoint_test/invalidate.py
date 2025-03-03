"""
invalidate.py

Этот модуль тестирует эндпоинт POST /invalidate.
Эндпоинт /invalidate используется для инвалидирования сессии,
то есть пометки ее как недоступной для дальнейшей выдачи.

Для авторизации используется заголовок X-API-Key.
Модуль принимает session_id (через аргументы командной строки или через input)
и отправляет POST-запрос для инвалидирования указанной сессии.
"""

import requests
import sys

BASE_URL = "http://178.238.114.132:52057"
API_KEY = "734f1f98137cc7dd341eee8148d73f1a0e6df6edd8b7dc627b66ea2312dc3be6"

def test_invalidate(session_id):
    """
    Отправляет POST-запрос на эндпоинт /invalidate с заданным session_id.
    Выводит статус-код и JSON-ответ сервера.
    
    :param session_id: Идентификатор сессии для инвалидирования.
    """
    url = f"{BASE_URL}/invalidate?session_id={session_id}"
    headers = {"X-API-Key": API_KEY}
    response = requests.post(url, headers=headers)
    print("Endpoint: /invalidate")
    print("Response Code:", response.status_code)
    try:
        print("Response JSON:", response.json())
    except Exception as e:
        print("Ошибка при парсинге JSON:", e)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        session_id = input("Введите session_id для инвалидирования: ")
    else:
        session_id = sys.argv[1]
    test_invalidate(session_id)
