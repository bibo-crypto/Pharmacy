"""
database/db_config.py
─────────────────────
مدير إعدادات الاتصال بقاعدة البيانات.
يدعم SQLite (محلي أو شبكة) و MySQL/MariaDB.
يُحفَظ الإعداد في: <APP_DIR>/db_config.json
"""

import json
import os
import sys
from pathlib import Path

# ── مسار ملف الإعداد ──
def _config_dir() -> Path:
    """
    مجلد حفظ الإعدادات — دائماً قابل للكتابة:
    - عند التجميع (frozen): مجلد الـ EXE أو PHARMACY_DATA_DIR
    - عند التشغيل المباشر: مجلد المشروع
    """
    data_env = os.environ.get("PHARMACY_DATA_DIR", "").strip()
    if data_env:
        return Path(data_env)
    if getattr(sys, 'frozen', False):
        # مجلد الـ EXE (قابل للكتابة) وليس _MEIPASS (للقراءة فقط)
        return Path(os.path.dirname(sys.executable))
    return Path(__file__).parent.parent

CONFIG_FILE = _config_dir() / "db_config.json"

# ── الافتراضي: SQLite محلي ──
_DEFAULTS = {
    "db_type": "sqlite",        # "sqlite" | "mysql"
    # SQLite
    "sqlite_path": "",          # فارغ = المسار التلقائي في مجلد البرنامج
    # MySQL / MariaDB
    "mysql_host":     "localhost",
    "mysql_port":     3306,
    "mysql_database": "pharmacy_db",
    "mysql_user":     "pharmacy_user",
    "mysql_password": "",
    "mysql_charset":  "utf8mb4",
    "mysql_timeout":  10,
}

# ── State محلي ──
_config: dict = dict(_DEFAULTS)
_loaded = False


def load_config() -> dict:
    """يحمّل الإعدادات من الملف — يُستدعى مرة عند بدء البرنامج."""
    global _config, _loaded
    p = _config_path()
    if p.is_file():
        try:
            with open(p, "r", encoding="utf-8") as f:
                saved = json.load(f)
            _config = {**_DEFAULTS, **saved}
        except Exception:
            _config = dict(_DEFAULTS)
    else:
        _config = dict(_DEFAULTS)
    _loaded = True
    return _config


def save_config(data: dict):
    """يحفظ الإعدادات مع تشفير كلمة مرور MySQL."""
    global _config, _loaded
    _config = {**_DEFAULTS, **data}
    _loaded = True
    p = _config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    to_save = dict(_config)
    # تشفير كلمة مرور MySQL قبل الحفظ
    if to_save.get("mysql_password"):
        try:
            from utils.crypto import encrypt, is_encrypted
            pw = to_save["mysql_password"]
            if not is_encrypted(pw):
                to_save["mysql_password"] = encrypt(pw)
        except Exception:
            pass
    with open(p, "w", encoding="utf-8") as f:
        json.dump(to_save, f, ensure_ascii=False, indent=2)
    _reset_connection()


def get_config() -> dict:
    """يرجع الإعدادات مع فك تشفير كلمة المرور."""
    if not _loaded:
        load_config()
    cfg = dict(_config)
    # فك تشفير كلمة المرور عند القراءة
    if cfg.get("mysql_password"):
        try:
            from utils.crypto import decrypt, is_encrypted
            pw = cfg["mysql_password"]
            if is_encrypted(pw):
                cfg["mysql_password"] = decrypt(pw)
        except Exception:
            pass
    return cfg


def get_db_type() -> str:
    return get_config().get("db_type", "sqlite")


def _config_path() -> Path:
    return _config_dir() / "db_config.json"


def _reset_connection():
    """يُعيد تهيئة الاتصال بعد تغيير الإعدادات."""
    try:
        from database import connection as c
        c._sqlite_path = None
        c._mysql_pool  = None
        c._db_type     = None
    except ImportError:
        pass


def test_connection(config: dict) -> tuple[bool, str]:
    """
    يختبر الاتصال بقاعدة البيانات.
    Returns: (success: bool, message: str)
    """
    db_type = config.get("db_type", "sqlite")

    if db_type == "sqlite":
        path = config.get("sqlite_path", "").strip()
        if not path:
            return True, "✅ SQLite محلي — لا حاجة لاختبار"
        try:
            import sqlite3
            if path.startswith("\\\\") or path.startswith("//"):
                # مسار شبكة — تأكد من إمكانية الوصول
                parent = os.path.dirname(path)
                if not os.path.exists(parent):
                    return False, f"❌ لا يمكن الوصول إلى: {parent}"
            conn = sqlite3.connect(path, timeout=5)
            conn.execute("SELECT 1")
            conn.close()
            return True, f"✅ تم الاتصال بـ SQLite: {path}"
        except Exception as e:
            return False, f"❌ فشل الاتصال: {e}"

    elif db_type == "mysql":
        try:
            import mysql.connector
            conn = mysql.connector.connect(
                host=config.get("mysql_host", "localhost"),
                port=int(config.get("mysql_port", 3306)),
                database=config.get("mysql_database", "pharmacy_db"),
                user=config.get("mysql_user", ""),
                password=config.get("mysql_password", ""),
                charset=config.get("mysql_charset", "utf8mb4"),
                connection_timeout=int(config.get("mysql_timeout", 10)),
            )
            conn.close()
            return True, f"✅ تم الاتصال بـ MySQL: {config['mysql_host']}:{config['mysql_port']}"
        except ImportError:
            return False, "❌ مكتبة mysql-connector-python غير مثبتة\nشغّل: pip install mysql-connector-python"
        except Exception as e:
            return False, f"❌ فشل الاتصال: {e}"

    return False, "❌ نوع قاعدة البيانات غير معروف"
