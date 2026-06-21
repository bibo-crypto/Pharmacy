"""
database/connection.py
──────────────────────
طبقة الاتصال بقاعدة البيانات — تدعم SQLite و MySQL.
كل الكود الآخر يستدعي get_connection() فقط.
"""

import os
import sys
import sqlite3
from pathlib import Path
from contextlib import contextmanager

# ── Pool ──
_sqlite_path: Path | None = None
_mysql_pool = None
_db_type: str | None = None


# ─────────────────────────────────────────────────────────
# تهيئة المسار الافتراضي لـ SQLite
# ─────────────────────────────────────────────────────────
def _default_sqlite_path() -> Path:
    data_dir = os.environ.get("PHARMACY_DATA_DIR")
    if data_dir:
        return Path(data_dir) / "pharmacy.db"

    # عند التشغيل من ملف EXE مُجمَّع بـ PyInstaller، __file__ يشاور على
    # مجلد _MEIPASS المؤقت (غير قابل للكتابة) لا على مكان الـEXE الحقيقي.
    # لازم نخزن قاعدة البيانات بجانب الـEXE، لا جوه الحزمة المؤقتة.
    if getattr(sys, "frozen", False):
        app_dir = Path(sys.executable).parent
    else:
        app_dir = Path(__file__).parent.parent

    return app_dir / "pharmacy.db"


def _get_db_type() -> str:
    global _db_type
    if _db_type is None:
        from database.db_config import get_db_type
        _db_type = get_db_type()
    return _db_type


def _reset_cache():
    global _sqlite_path, _mysql_pool, _db_type
    _sqlite_path = None
    _mysql_pool  = None
    _db_type     = None


# DB_PATH للتوافق مع الكود القديم
@property
def _DB_PATH_PROP(self):
    return _get_sqlite_path()

def _get_sqlite_path() -> Path:
    global _sqlite_path
    if _sqlite_path is None:
        from database.db_config import get_config
        cfg  = get_config()
        path = cfg.get("sqlite_path", "").strip()
        _sqlite_path = Path(path) if path else _default_sqlite_path()
    return _sqlite_path


# ── للتوافق مع الكود القديم الذي يستخدم DB_PATH ──
class _DBPathDescriptor:
    def __get__(self, obj, objtype=None):
        return _get_sqlite_path()

import types
_module = sys.modules[__name__]
DB_PATH = _get_sqlite_path()   # قيمة أولية — تُحدَّث عند الاتصال


# ─────────────────────────────────────────────────────────
# SQLite Connection
# ─────────────────────────────────────────────────────────
def _sqlite_connection() -> sqlite3.Connection:
    path = _get_sqlite_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30,
                           check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA cache_size = -8000")   # 8 MB cache
    conn.execute("PRAGMA temp_store = MEMORY")
    return conn


# ─────────────────────────────────────────────────────────
# MySQL Connection
# ─────────────────────────────────────────────────────────
def _mysql_connection():
    global _mysql_pool
    try:
        import mysql.connector
        from mysql.connector import pooling
    except ImportError:
        raise RuntimeError(
            "مكتبة mysql-connector-python غير مثبتة.\n"
            "شغّل: pip install mysql-connector-python"
        )

    from database.db_config import get_config
    cfg = get_config()

    if _mysql_pool is None:
        _mysql_pool = pooling.MySQLConnectionPool(
            pool_name="pharmacy_pool",
            pool_size=5,
            host=cfg.get("mysql_host", "localhost"),
            port=int(cfg.get("mysql_port", 3306)),
            database=cfg.get("mysql_database", "pharmacy_db"),
            user=cfg.get("mysql_user", ""),
            password=cfg.get("mysql_password", ""),
            charset=cfg.get("mysql_charset", "utf8mb4"),
            use_unicode=True,
            connect_timeout=int(cfg.get("mysql_timeout", 10)),
            autocommit=False,
        )
    return _MySQLConnectionWrapper(_mysql_pool.get_connection())


# ─────────────────────────────────────────────────────────
# MySQL → SQLite wrapper
# يجعل MySQL يتصرف مثل sqlite3 (row_factory، cursor، إلخ)
# ─────────────────────────────────────────────────────────
class _MySQLRow(dict):
    """يحاكي sqlite3.Row — يدعم الوصول بالاسم والفهرس."""
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)

    def keys(self):
        return list(super().keys())

    def get(self, key, default=None):
        return super().get(key, default)


class _MySQLCursor:
    def __init__(self, cursor, conn_wrapper):
        self._cur  = cursor
        self._conn = conn_wrapper
        self.lastrowid   = None
        self.rowcount    = 0
        self.description = None

    def execute(self, sql: str, params=()):
        sql = _translate_sql(sql)
        self._cur.execute(sql, params or ())
        self.lastrowid   = self._cur.lastrowid
        self.rowcount    = self._cur.rowcount
        self.description = self._cur.description
        return self

    def executemany(self, sql: str, params_list):
        sql = _translate_sql(sql)
        self._cur.executemany(sql, params_list)

    def fetchone(self):
        row = self._cur.fetchone()
        if row is None:
            return None
        if self._cur.description:
            cols = [d[0] for d in self._cur.description]
            return _MySQLRow(zip(cols, row))
        return row

    def fetchall(self):
        rows = self._cur.fetchall()
        if not rows:
            return []
        if self._cur.description:
            cols = [d[0] for d in self._cur.description]
            return [_MySQLRow(zip(cols, r)) for r in rows]
        return rows

    def __iter__(self):
        return iter(self.fetchall())

    def close(self):
        self._cur.close()


class _MySQLConnectionWrapper:
    """يحاكي واجهة sqlite3.Connection."""
    def __init__(self, conn):
        self._conn = conn

    def cursor(self) -> _MySQLCursor:
        return _MySQLCursor(self._conn.cursor(), self)

    def execute(self, sql: str, params=()):
        c = self.cursor()
        c.execute(sql, params)
        return c

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, *_):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()


# ─────────────────────────────────────────────────────────
# SQL Translation: SQLite → MySQL
# ─────────────────────────────────────────────────────────
def _translate_sql(sql: str) -> str:
    """يترجم SQL من صيغة SQLite لـ MySQL."""
    import re
    # INTEGER PRIMARY KEY AUTOINCREMENT → INT AUTO_INCREMENT PRIMARY KEY
    sql = re.sub(r'\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b',
                 'INT AUTO_INCREMENT PRIMARY KEY', sql, flags=re.IGNORECASE)
    # AUTOINCREMENT بدون PRIMARY KEY
    sql = sql.replace('AUTOINCREMENT', 'AUTO_INCREMENT')
    # TEXT → VARCHAR(512) / LONGTEXT حسب السياق
    sql = re.sub(r'\bTEXT\b', 'LONGTEXT', sql, flags=re.IGNORECASE)
    # REAL → DOUBLE
    sql = re.sub(r'\bREAL\b', 'DOUBLE', sql, flags=re.IGNORECASE)
    # BLOB → LONGBLOB
    sql = re.sub(r'\bBLOB\b', 'LONGBLOB', sql, flags=re.IGNORECASE)
    # CURRENT_TIMESTAMP ok
    # INSERT OR IGNORE → INSERT IGNORE
    sql = re.sub(r'\bINSERT\s+OR\s+IGNORE\b',
                 'INSERT IGNORE', sql, flags=re.IGNORECASE)
    # INSERT OR REPLACE → REPLACE
    sql = re.sub(r'\bINSERT\s+OR\s+REPLACE\b',
                 'REPLACE', sql, flags=re.IGNORECASE)
    # ? → %s (MySQL params)
    sql = sql.replace('?', '%s')
    # PRAGMA (نتجاهلها في MySQL)
    if sql.strip().upper().startswith('PRAGMA'):
        return 'SELECT 1'
    return sql


# ─────────────────────────────────────────────────────────
# الدالة الرئيسية
# ─────────────────────────────────────────────────────────
def get_connection():
    """
    يرجع اتصال بقاعدة البيانات المُعيَّنة في الإعدادات.
    استخدم دائماً:
        conn = get_connection()
        ...
        conn.close()
    """
    db_type = _get_db_type()
    if db_type == "mysql":
        return _mysql_connection()
    return _sqlite_connection()


@contextmanager
def db_session():
    """Context manager آمن للاستخدام في try/except."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """تهيئة قاعدة البيانات — إنشاء الجداول إن لم تكن موجودة."""
    from database.db_config import load_config
    load_config()
    _reset_cache()
    from database.schema import create_tables
    create_tables()
