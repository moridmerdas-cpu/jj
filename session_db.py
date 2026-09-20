# session_db.py
"""
دیتابیس جدا (Supabase دوم) فقط برای نگه‌داری داده‌های سشن اکانت‌ها:
session_data, logged_in, session_started_at

هدف: جدا کردن داده‌ی حساس/سنگین سشن از بقیه‌ی تنظیمات، تا:
- اگه دیتابیس اصلی مشکل پیدا کرد، سشن‌ها دست‌نخورده بمونن
- بار (load) روی دیتابیس اصلی کمتر بشه

اگه SESSION_DATABASE_URL ست نشده باشه، این ماژول خودکار از همون
DATABASE_URL اصلی استفاده می‌کنه (سازگار با نصب‌های قدیمی).
"""
import os
import threading
import datetime
import psycopg2
import psycopg2.extras
import psycopg2.pool
from typing import Optional, Dict
from config import SESSION_DATABASE_URL

SESSION_KEYS = {"session_data", "logged_in", "session_started_at"}

# ✅ همون تغییر database_supabase.py: به‌جای یک کانکشنِ سراسری + Lock، از
# یک Connection Pool واقعی استفاده می‌کنیم تا کوئری‌های سشنِ کاربرهای مختلف
# پشتِ هم صف نکشن و سرعت با افزایشِ کاربر افت نکنه.
_SESSION_POOL_MIN = int(os.environ.get("SESSION_DB_POOL_MIN", "2"))
_SESSION_POOL_MAX = int(os.environ.get("SESSION_DB_POOL_MAX", "20"))

_pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None
_pool_lock = threading.Lock()


def _get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = psycopg2.pool.ThreadedConnectionPool(
                    _SESSION_POOL_MIN,
                    _SESSION_POOL_MAX,
                    dsn=SESSION_DATABASE_URL,
                    sslmode='require',
                    connect_timeout=10,
                    keepalives=1,
                    keepalives_idle=30,
                    keepalives_interval=10,
                    keepalives_count=5,
                )
    return _pool


def execute_query(query: str, params: tuple = None, fetch_one: bool = False, fetch_all: bool = False, _retry: bool = True):
    pool = _get_pool()
    conn = pool.getconn()
    conn_broken = False
    try:
        conn.autocommit = True
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cur.execute(query, params)
            if fetch_one:
                return cur.fetchone()
            elif fetch_all:
                return cur.fetchall()
            return cur.rowcount
        finally:
            cur.close()
    except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
        print(f"❌ Session DB connection error (در حال بازسازی کانکشن): {e}")
        conn_broken = True
        if _retry:
            return execute_query(query, params, fetch_one=fetch_one, fetch_all=fetch_all, _retry=False)
        raise
    except Exception as e:
        print(f"❌ Session DB error: {e}")
        raise
    finally:
        if conn_broken:
            try:
                pool.putconn(conn, close=True)
            except Exception:
                pass
        else:
            pool.putconn(conn)


def init_tables():
    """ساخت جدول amel_sessions در دیتابیس جدا"""
    query = """
        CREATE TABLE IF NOT EXISTS amel_sessions (
            owner_id INTEGER PRIMARY KEY,
            session_data TEXT DEFAULT '',
            logged_in TEXT DEFAULT '0',
            session_started_at TEXT DEFAULT '',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    try:
        execute_query(query)
        print("✅ جدول amel_sessions در دیتابیس سشن ایجاد/تأیید شد!")
    except Exception as e:
        print(f"❌ Error creating amel_sessions table: {e}")


def get_session_value(owner_id: int, key: str) -> Optional[str]:
    """خواندن یکی از session_data / logged_in / session_started_at"""
    try:
        query = f"SELECT {key} FROM amel_sessions WHERE owner_id = %s"
        result = execute_query(query, (owner_id,), fetch_one=True)
        if result:
            return result[key]
        return None
    except Exception as e:
        print(f"⚠️ get_session_value خطای موقتی ({owner_id}, {key}): {e}")
        return None


def set_session_value(owner_id: int, key: str, value):
    """نوشتن یکی از session_data / logged_in / session_started_at (upsert)"""
    try:
        query = f"""
            INSERT INTO amel_sessions (owner_id, {key}, updated_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (owner_id) DO UPDATE
            SET {key} = EXCLUDED.{key}, updated_at = EXCLUDED.updated_at
        """
        execute_query(query, (owner_id, str(value), datetime.datetime.now()))
    except Exception as e:
        print(f"❌ set_session_value error ({owner_id}, {key}): {e}")
        raise


def get_all_session_row(owner_id: int) -> Optional[Dict]:
    try:
        query = "SELECT * FROM amel_sessions WHERE owner_id = %s"
        result = execute_query(query, (owner_id,), fetch_one=True)
        return dict(result) if result else None
    except Exception as e:
        print(f"❌ get_all_session_row error: {e}")
        return None


def delete_session(owner_id: int):
    try:
        execute_query("DELETE FROM amel_sessions WHERE owner_id = %s", (owner_id,))
    except Exception as e:
        print(f"❌ delete_session error: {e}")
