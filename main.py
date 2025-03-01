# main.py
import os
import time
import threading
import logging
import datetime
import math
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request
from db import (
    find_free_session,
    mark_session_in_use,
    release_session,
    set_floodwait,
    get_status,
    free_stuck_sessions,
    sync_sessions,
    get_connection,
    release_connection
)

# Настройка логирования: логи будут записываться в файл session_manager.log
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    filename="session_manager.log",
    filemode="a"
)

# Обработчик жизненного цикла приложения через lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # При старте запускаем фоновые задачи:
    threading.Thread(target=background_free_stuck, daemon=True).start()
    threading.Thread(target=background_sync_files, daemon=True).start()
    logging.info("Фоновые задачи запущены")
    yield
    # При завершении можно добавить код очистки, если потребуется

app = FastAPI(lifespan=lifespan)

# Список разрешённых API-ключей (в продакшене можно хранить в БД или переменных окружения)
ALLOWED_API_KEYS = {"734f1f98137cc7dd341eee8148d73f1a0e6df6edd8b7dc627b66ea2312dc3be6",
                    "8093a9bbf4e0d87cfdac4e629c598a5021fc1c4d6d4c62e879150ccf14132dcf",
                    "f9f9bafd55922e1cacfffa46c6cf46f1414d332ae0e0c3aa8be6b8b797999041",
                    "418e0534f64f120a2739b08a108d8288b8b4e1e23bab0a7bc618fd2899a5d671",
                    "960954b245c7bf34ceff5e5073118aa59a225af139be281bbb12b5174d4f67cf"
                    }  


def check_api_key(request: Request):
    """
    Проверка API-ключа, передаваемого в заголовке 'X-API-Key'.
    Если ключ отсутствует или недопустим – выбрасываем HTTPException.
    """
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    if api_key not in ALLOWED_API_KEYS:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

@app.get("/status")
def status(api_key: str = Depends(check_api_key)):
    """
    Эндпоинт /status возвращает агрегированную статистику:
      - Общее количество сессий.
      - Количество свободных сессий.
      - Количество занятых сессий.
      - Количество сессий в состоянии Flood Wait.
      - Время, когда ближайшая сессия выйдет из Flood Wait.
    """
    stats = get_status()
    if stats["next_available"]:
        stats["next_available"] = stats["next_available"].strftime("%Y-%m-%d %H:%M:%S")
    return stats

@app.get("/session")
def acquire_session(api_key: str = Depends(check_api_key)):
    """
    Эндпоинт для выдачи свободной сессии.
    Если свободная сессия найдена – помечаем её как занятое и возвращаем данные.
    Если нет – возвращаем подробную информацию о Flood Wait:
      - Количество сессий в Flood Wait.
      - Через сколько секунд освободится ближайшая сессия.
    """
    session = find_free_session()
    if session is None:
        # Собираем информацию о сессиях в Flood Wait
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM sessions WHERE in_floodwait = TRUE AND floodwait_until > NOW();")
        waiting = cur.fetchone()[0]
        cur.execute("SELECT MIN(floodwait_until) FROM sessions WHERE in_floodwait = TRUE AND floodwait_until > NOW();")
        next_time = cur.fetchone()[0]
        cur.close()
        release_connection(conn)
        if next_time:
            seconds_to_wait = math.ceil((next_time - datetime.datetime.now()).total_seconds())
        else:
            seconds_to_wait = None
        detail = {
            "error": "no_free_session",
            "in_floodwait": int(waiting),
            "next_release_in": seconds_to_wait
        }
        raise HTTPException(status_code=503, detail=detail)
    # Если свободная сессия найдена, отмечаем её как in_use и возвращаем
    mark_session_in_use(session["id"])
    return {"session_id": session["id"], "session_name": session["name"]}

@app.post("/release")
def api_release_session(session_id: int, api_key: str = Depends(check_api_key)):
    """
    Эндпоинт для возврата сессии в пул.
    Клиент должен вызвать этот метод после завершения работы с сессией.
    """
    release_session(session_id)
    return {"status": "released", "session_id": session_id}

@app.post("/invalidate")
def api_invalidate_session(session_id: int, api_key: str = Depends(check_api_key)):
    """
    Эндпоинт для инвалидирования сессии.
    При инвалидировании устанавливаем floodwait_until на далёкую дату (например, 2099-01-01),
    что означает, что сессия не будет выдана до ручного вмешательства.
    """
    far_future = datetime.datetime(2099, 1, 1)
    wait_seconds = (far_future - datetime.datetime.now()).total_seconds()
    set_floodwait(session_id, wait_seconds=wait_seconds)
    return {"status": "invalidated", "session_id": session_id}

# Фоновая задача для освобождения зависших сессий (если сессия используется более 3 часов)
def background_free_stuck():
    while True:
        freed = free_stuck_sessions(max_duration_hours=3)
        if freed:
            logging.info(f"Освобождено зависших сессий: {freed}")
        time.sleep(1800)  # запуск проверки каждые 30 минут

# Фоновая задача для синхронизации файлов сессий с записями в БД
def background_sync_files():
    while True:
        sync_sessions()
        time.sleep(3600)  # запуск проверки каждые 1 час

# Примечание: запуск фоновых задач осуществляется в обработчике lifespan (см. выше)


# Основной запуск приложения выполняется через Uvicorn или Gunicorn+UvicornWorker.
# Пример запуска для разработки:
# uvicorn main:app --host 0.0.0.0 --port 8000 --reload