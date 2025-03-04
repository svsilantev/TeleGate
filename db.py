import os
import psycopg2
from psycopg2 import pool
import platform
from datetime import datetime, timedelta
import logging
from telethon import TelegramClient
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
import asyncio


SESSION_FILES_DIR = "./sessions"  # путь к директории с файлами сессий

API_ID = 28903747
API_HASH = "f775a7c89795085b867066093060fc59"

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


def generate_session_string_sync(session_file: str) -> str:
    # Если в текущем потоке нет event loop, создаём его
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    with TelegramClient(session_file, API_ID, API_HASH) as client:
        client.connect()  # явное подключение
        # Проверяем, авторизована ли сессия
        if not client.is_user_authorized():
            raise Exception("Сессия не авторизована")
        session_string = StringSession.save(client.session)
        return session_string



# Функция для поиска свободной сессии (которая не занята и не в активном Flood Wait)

def find_free_session():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, session_name, session_string, proxy_host, proxy_port, proxy_type, proxy_login, proxy_password
        FROM sessions 
        WHERE in_use = FALSE 
          AND (in_floodwait = FALSE OR floodwait_until <= NOW())
          AND error_message IS NULL
        LIMIT 1;
    """)
    result = cur.fetchone()
    cur.close()
    release_connection(conn)
    if result:
        (session_id, session_name, session_string, 
         proxy_host, proxy_port, proxy_type, proxy_login, proxy_password) = result
        return {
            "id": session_id,
            "name": session_name,
            "session_string": session_string,
            "proxy_host": proxy_host,
            "proxy_port": proxy_port,
            "proxy_type": proxy_type,
            "proxy_login": proxy_login,
            "proxy_password": proxy_password
        }
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

async def generate_session_string(session_file):
    client = TelegramClient(session_file, API_ID, API_HASH)
    await client.connect()
    session_string = client.session.save()
    await client.disconnect()
    return session_string

def get_session_string(session_file):
    # Всегда создаем новый event loop
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(generate_session_string(session_file))
    finally:
        loop.close()
    return result


def sync_sessions():
    """
    Синхронизирует записи о сессиях в БД с реальными файлами .session на диске.
    Возвращает словарь с количеством новых и удалённых сессий.
    Все новые записи получают одинаковый прокси: user174044:lboavc@62.233.49.71:5862
    После вставки новой сессии пытаемся создать строку сессии.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
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
        # Вставляем новую запись и сразу возвращаем её id
        cur.execute(
            """
            INSERT INTO sessions 
                (session_name, in_use, in_floodwait, proxy_host, proxy_port, proxy_type, proxy_login, proxy_password)
            VALUES 
                (%s, FALSE, FALSE, %s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (name, "62.233.49.71", 5862, "socks5", "user174044", "lboavc")
        )
        session_id = cur.fetchone()[0]
        new_count += 1

        session_file = os.path.join(SESSION_FILES_DIR, f"{name}.session")
        try:
            session_string = generate_session_string_sync(session_file)
        except Exception as e:
            error_msg = str(e)
            # Помечаем сессию как недействительную: устанавливаем in_floodwait=TRUE,
            # floodwait_until до 2099 года и записываем сообщение об ошибке
            far_future = datetime.datetime(2099, 1, 1)
            cur.execute(
                "UPDATE sessions SET error_message=%s, in_floodwait=TRUE, floodwait_until=%s WHERE id=%s;",
                (error_msg, far_future, session_id)
            )
            logging.error(f"Ошибка при создании session_string для {name}: {error_msg}")
            continue
        cur.execute("UPDATE sessions SET session_string=%s WHERE id=%s;", (session_string, session_id))

    for name in removed_sessions:
        cur.execute("DELETE FROM sessions WHERE session_name = %s;", (name,))
        removed_count += 1

    conn.commit()
    cur.close()
    release_connection(conn)
    return {"new_sessions": new_count, "removed_sessions": removed_count, "total_sessions": len(files)}
