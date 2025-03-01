import psycopg2
import platform
from fastapi import FastAPI
from datetime import datetime, timedelta

app = FastAPI()

# Определяем ОС
if platform.system() == "Windows":
    DB_HOST = "178.238.114.132"
    DB_PORT = "51057"
else:
    DB_HOST = "localhost"
    DB_PORT = "5432"
    
# Настройки соединения с БД
db_conn = psycopg2.connect(
    dbname="telethon_db", user="ssilantev", password="u2997988U", host="178.238.114.132", port = "51057"
)
db_conn.autocommit = True  # чтобы не вручную делать commit

# Вспомогательная функция для получения свободной сессии
def fetch_free_session():
    cur = db_conn.cursor()
    cur.execute(
        "SELECT id, session_name, proxy_host, proxy_port, proxy_type, proxy_login, proxy_password "
        "FROM sessions WHERE in_use = FALSE AND (blocked_until IS NULL OR blocked_until < NOW()) "
        "LIMIT 1 FOR UPDATE SKIP LOCKED;"
    )
    # Используем SELECT ... FOR UPDATE SKIP LOCKED, чтобы блокировать выбранную запись (если транзакционно),
    # и не столкнуться с конкурентным выбором той же сессии.
    row = cur.fetchone()
    if not row:
        return None
    session_id, session_name, proxy_host, proxy_port, proxy_type, proxy_login, proxy_pass = row
    # Помечаем как in_use
    cur.execute("UPDATE sessions SET in_use = TRUE WHERE id = %s;", (session_id,))
    cur.close()
    # Формируем результат для отдачи
    proxy_info = None
    if proxy_host:
        proxy_info = {
            "type": proxy_type or "socks5",
            "host": proxy_host,
            "port": proxy_port,
            "user": proxy_login,
            "pass": proxy_pass
        }
    return {"session_id": session_id, "session_name": session_name, "proxy": proxy_info}


@app.get("/session")
def get_session():
    """Запрос свободной сессии"""
    result = fetch_free_session()
    if not result:
        return {"error": "No available session"}  # при отсутствии свободных сессий
    return result

@app.post("/session/return")
def return_session(session_id: int, flood_wait: int = 0):
    """Возврат сессии в пул"""
    cur = db_conn.cursor()
    # Сбрасываем флаг in_use, устанавливаем время блокировки если нужно
    if flood_wait and flood_wait > 0:
        until_time = datetime.utcnow() + timedelta(seconds=flood_wait)
        cur.execute("UPDATE sessions SET in_use = FALSE, blocked_until = %s WHERE id = %s;", (until_time, session_id))
    else:
        cur.execute("UPDATE sessions SET in_use = FALSE, blocked_until = NULL WHERE id = %s;", (session_id,))
    cur.close()
    return {"status": "returned", "session_id": session_id}

@app.post("/session/invalidate")
def invalidate_session(session_id: int):
    """Инвалидировать (отключить) сессию"""
    cur = db_conn.cursor()
    # Помечаем сессию как занятую и ставим большой блок или отдельный флаг, либо удаляем
    cur.execute("UPDATE sessions SET in_use = TRUE, blocked_until = '2099-01-01' WHERE id = %s;", (session_id,))
    # В качестве упрощения: помечаем как in_use = TRUE и очень далекой блокировкой.
    # Можно добавить отдельное поле status (active/invalid).
    cur.close()
    return {"status": "invalidated", "session_id": session_id}
