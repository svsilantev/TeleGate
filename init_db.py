# init_db.py

import psycopg2
from psycopg2 import sql

# Настройки подключения к БД
DB_CONFIG = {
    "dbname": "telethon_db",
    "user": "ssilantev",
    "password": "u2997988U",
    "host": "localhost",  # 178.238.114.132 для удаленного Или "localhost" для локального сервера
    "port": "5432" # "52057" для удаленного Или "5432" для локального сервера
}

def init_db():
    """Создание таблицы sessions, если она не существует."""
    connection = psycopg2.connect(**DB_CONFIG)
    connection.autocommit = True
    cursor = connection.cursor()
    
    create_table_query = sql.SQL(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id SERIAL PRIMARY KEY,
            session_name TEXT UNIQUE NOT NULL,
            session_string TEXT,
            in_use BOOLEAN DEFAULT FALSE,
            last_used TIMESTAMP,
            in_floodwait BOOLEAN DEFAULT FALSE,
            floodwait_until TIMESTAMP,
            error_message TEXT,
            proxy_host VARCHAR(100),
            proxy_port INTEGER,
            proxy_type VARCHAR(10),
            proxy_login VARCHAR(50),
            proxy_password VARCHAR(50)
        );
        """
    )
    
    cursor.execute(create_table_query)
    cursor.close()
    connection.close()
    print("✅ База данных инициализирована. Таблица sessions проверена.")

if __name__ == "__main__":
    init_db()
