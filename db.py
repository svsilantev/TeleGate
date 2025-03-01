import os
import psycopg2
from psycopg2 import pool
import platform
from datetime import datetime, timedelta
import logging

SESSION_FILES_DIR = "./sessions"  # путь к директории с файлами сессий

# Определяем ОС
if platform.system() == "Windows":
    DB_CONFIG = {
        "host": "178.238.114.132",  # Windows → удалённая база
        "port": "51057",
    }
else:
    DB_CONFIG = {
        "host": "localhost",      # Linux → локальная база
        "port": "5432",
    }

# Добавляем общие параметры БД
DB_CONFIG.update({
    "database": "telethon_db",
    "user": "ssilantev",
    "password": "u2997988U"
})

# Инициализация пула соединений к PostgreSQL
conn_pool = pool.SimpleConnectionPool(minconn=1, maxconn=5, **DB_CONFIG)


def get_connection():
    """Получить соединение из пула."""
    return conn_pool.getconn()


def release_connection(conn):
    """Вернуть соединение в пул."""
    conn_pool.putconn(conn)


# Функция для поиска свободной сессии (которая не занята и не в активном Flood Wait)
def find_free_session():
    conn = get_connection()
    cur = conn.cursor()
    # Проверяем есть ли сессия, не занятая и не находящаяся в Flood Wait (или срок Flood Wait уже прошел)
    cur.execute("""
        SELECT id, session_name 
        FROM sessions 
        WHERE in_use = FALSE 
          AND (in_floodwait = FALSE OR floodwait_until <= NOW())
        LIMIT 1;
    """)
    result = cur.fetchone()
    cur.close()
    release_connection(conn)
    if result:
        session_id, session_name = result
        return {"id": session_id, "name": session_name}
    else:
        return None


# Функция пометить сессию как занятую
def mark_session_in_use(session_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE sessions 
        SET in_use = TRUE, in_floodwait = FALSE, floodwait_until = NULL, last_used = NOW() 
        WHERE id = %s;
    """, (session_id,))
    conn.commit()
    cur.close()
    release_connection(conn)


# Функция пометить сессию как свободную (освобождение)
def release_session(session_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE sessions 
        SET in_use = FALSE 
        WHERE id = %s;
    """, (session_id,))
    conn.commit()
    cur.close()
    release_connection(conn)


# Функция установки состояния Flood Wait для сессии (когда Telegram временно блокирует действия)
def set_floodwait(session_id, wait_seconds):
    conn = get_connection()
    cur = conn.cursor()
    until_time = datetime.now() + timedelta(seconds=wait_seconds)
    cur.execute("""
        UPDATE sessions 
        SET in_floodwait = TRUE, floodwait_until = %s, in_use = FALSE 
        WHERE id = %s;
    """, (until_time, session_id))
    conn.commit()
    cur.close()
    release_connection(conn)


# Функция получения статистики по сессиям для /status
def get_status():
    conn = get_connection()
    cur = conn.cursor()
    # Общее количество сессий
    cur.execute("SELECT COUNT(*) FROM sessions;")
    total = cur.fetchone()[0]
    # Свободные сессии (не заняты и не в активном Flood Wait)
    cur.execute("""
        SELECT COUNT(*) 
        FROM sessions 
        WHERE in_use = FALSE 
          AND (in_floodwait = FALSE OR floodwait_until <= NOW());
    """)
    free_count = cur.fetchone()[0]
    # Занятые сессии
    cur.execute("SELECT COUNT(*) FROM sessions WHERE in_use = TRUE;")
    in_use_count = cur.fetchone()[0]
    # Сессии в состоянии Flood Wait (срок которого ещё не истек)
    cur.execute("""
        SELECT COUNT(*) 
        FROM sessions 
        WHERE in_floodwait = TRUE AND floodwait_until > NOW();
    """)
    floodwait_count = cur.fetchone()[0]
    # Ближайшее время окончания текущего Flood Wait среди всех сессий
    cur.execute("""
        SELECT MIN(floodwait_until) 
        FROM sessions 
        WHERE in_floodwait = TRUE AND floodwait_until > NOW();
    """)
    next_free_time = cur.fetchone()[0]
    cur.close()
    release_connection(conn)
    return {
        "total": total,
        "free": free_count,
        "in_use": in_use_count,
        "in_floodwait": floodwait_count,
        "next_available": next_free_time  # может быть None, если нет заблокированных сессий
    }


def free_stuck_sessions(max_duration_hours=3):
    """Освобождает сессии, которые заняты дольше max_duration_hours часов."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE sessions 
        SET in_use = FALSE 
        WHERE in_use = TRUE 
          AND last_used < NOW() - INTERVAL '%s hour';
    """, (max_duration_hours,))
    freed = cur.rowcount  # сколько записей обновлено (освобождено)
    conn.commit()
    cur.close()
    release_connection(conn)
    return freed

def sync_sessions():
    """
    Синхронизирует записи о сессиях в БД с реальными файлами .session на диске.
    Возвращает словарь с количеством новых и удалённых сессий.
    Все новые записи получают одинаковый прокси: user174044:lboavc@62.233.49.71:5862
    """
    files = set()
    if os.path.isdir(SESSION_FILES_DIR):
        for fname in os.listdir(SESSION_FILES_DIR):
            if fname.endswith(".session"):
                # Имя сессии берем без расширения ".session"
                session_name = fname[:-8]
                files.add(session_name)
    else:
        logging.warning(f"Директория сессий {SESSION_FILES_DIR} не найдена")
        return {"new_sessions": 0, "removed_sessions": 0, "total_sessions": 0}

    conn = get_connection()
    cur = conn.cursor()
    # Получаем все записи из БД
    cur.execute("SELECT session_name FROM sessions;")
    db_sessions = {row[0] for row in cur.fetchall()}

    # Новые сессии: есть на диске, но отсутствуют в БД
    new_sessions = files - db_sessions
    # Сессии, которых нет на диске, но они есть в БД
    removed_sessions = db_sessions - files

    new_count = 0
    removed_count = 0

    for name in new_sessions:
        cur.execute(
            """
            INSERT INTO sessions 
                (session_name, in_use, in_floodwait, proxy_host, proxy_port, proxy_type, proxy_login, proxy_password)
            VALUES 
                (%s, FALSE, FALSE, %s, %s, %s, %s, %s);
            """,
            (name, "62.233.49.71", 5862, "socks5", "user174044", "lboavc")
        )
        new_count += 1

    for name in removed_sessions:
        cur.execute("DELETE FROM sessions WHERE session_name = %s;", (name,))
        removed_count += 1

    conn.commit()
    cur.close()
    release_connection(conn)
    return {"new_sessions": new_count, "removed_sessions": removed_count, "total_sessions": len(files)}