"""
utils/auth.py
─────────────
المصادقة والجلسة — الباسورد مشفّر دائماً بـ bcrypt.
للتوافق مع قواعد البيانات القديمة (SHA-256): يُرقّى تلقائياً.
credentials.txt يحفظ اسم المستخدم فقط — لا باسورد مطلقاً.
"""

import hashlib
import os
import sys
from pathlib import Path


# ── bcrypt: يُستخدم إن وُجد ──────────────────────────────
def _bcrypt_available() -> bool:
    try:
        import bcrypt  # noqa
        return True
    except ImportError:
        return False


def _hash_bcrypt(password: str) -> str:
    import bcrypt
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def _verify_bcrypt(password: str, hashed: str) -> bool:
    import bcrypt
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def _hash_sha256(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    """يشفّر الباسورد — يستخدم bcrypt إن وُجد، وإلا SHA-256."""
    if _bcrypt_available():
        return _hash_bcrypt(password)
    return _hash_sha256(password)


def verify_password(password: str, stored_hash: str) -> bool:
    """يتحقق من الباسورد مهما كان نوع التشفير (bcrypt أو SHA-256)."""
    if not stored_hash:
        return False
    # bcrypt hashes تبدأ بـ $2b$ أو $2a$ أو $2y$
    if stored_hash.startswith(("$2b$", "$2a$", "$2y$")):
        if _bcrypt_available():
            return _verify_bcrypt(password, stored_hash)
        return False   # bcrypt hash بدون مكتبة bcrypt → فشل
    # SHA-256 (64 حرف hex)
    return stored_hash == _hash_sha256(password)


# ── مسار credentials ──────────────────────────────────────
def _creds_path() -> Path:
    data_dir = os.environ.get("PHARMACY_DATA_DIR")
    if data_dir:
        return Path(data_dir) / "credentials.txt"
    if getattr(sys, "frozen", False):
        return Path(os.path.dirname(sys.executable)) / "credentials.txt"
    return Path(__file__).resolve().parent.parent / "credentials.txt"


# ── Session ───────────────────────────────────────────────
_current_user   = None
_current_session: dict = {}


# ── Credentials file (اسم المستخدم فقط — لا باسورد) ──────
def load_last_username() -> str:
    """يرجع آخر اسم مستخدم تم الدخول به — بدون أي باسورد."""
    p = _creds_path()
    if not p.exists():
        return "admin"
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("username="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return "admin"


def save_last_username(username: str) -> None:
    """يحفظ اسم المستخدم فقط للراحة — لا باسورد."""
    p = _creds_path()
    try:
        p.write_text(f"username={username.strip()}\n", encoding="utf-8")
    except Exception:
        pass


# للتوافق مع الكود القديم الذي يستدعي load_default_credentials()
def load_default_credentials() -> dict:
    """محاكاة القديم — يرجع username فقط، password فارغ."""
    return {"username": load_last_username(), "password": ""}


def save_default_credentials(username: str, _password: str = "") -> None:
    """محاكاة القديم — يحفظ username فقط."""
    save_last_username(username)


# ── Login ─────────────────────────────────────────────────
def login(username: str, password: str):
    global _current_user, _current_session
    from database.connection import get_connection
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT u.*, r.name as role_name
        FROM users u
        JOIN roles r ON u.role_id = r.id
        WHERE u.username = ? AND u.is_active = 1
    """, (username,))
    user = c.fetchone()
    if not user:
        conn.close()
        return None

    user_dict = dict(user)
    stored_hash = user_dict.get("password", "")

    # التحقق من الباسورد
    if not verify_password(password, stored_hash):
        conn.close()
        return None

    # ترقية تلقائية من SHA-256 إلى bcrypt
    if _bcrypt_available() and not stored_hash.startswith(("$2b$", "$2a$", "$2y$")):
        new_hash = _hash_bcrypt(password)
        c.execute("UPDATE users SET password = ? WHERE id = ?",
                  (new_hash, user_dict["id"]))

    c.execute("SELECT permission_code FROM role_permissions WHERE role_id = ?",
              (user_dict["role_id"],))
    perms = [row[0] for row in c.fetchall()]
    user_dict["permissions"] = perms

    c.execute("UPDATE users SET last_login = datetime('now') WHERE id = ?",
              (user_dict["id"],))
    conn.commit()
    conn.close()

    _current_user    = user_dict
    _current_session = user_dict

    # احفظ اسم المستخدم للراحة (بدون باسورد)
    save_last_username(username)

    from utils.audit import log_action
    log_action("login", None, None)
    return user_dict


def logout():
    global _current_user, _current_session
    if _current_user:
        from utils.audit import log_action
        log_action("logout", None, None)
    _current_user    = None
    _current_session = {}


def get_current_user():
    return _current_user


def has_permission(permission_code: str) -> bool:
    if not _current_user:
        return False
    if _current_user.get("role_name") == "Super Admin":
        return True
    return permission_code in _current_user.get("permissions", [])


def require_permission(permission_code: str):
    if not has_permission(permission_code):
        raise PermissionError(f"ليس لديك صلاحية: {permission_code}")


def change_password(user_id: int, old_password: str, new_password: str) -> bool:
    from database.connection import get_connection
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    if not row or not verify_password(old_password, row[0]):
        conn.close()
        return False
    new_hash = hash_password(new_password)
    c.execute("UPDATE users SET password = ? WHERE id = ?", (new_hash, user_id))
    conn.commit()
    conn.close()
    return True
