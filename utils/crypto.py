"""
utils/crypto.py
───────────────
تشفير بسيط للبيانات الحساسة (MySQL password في db_config.json).
يستخدم Fernet (AES-128-CBC + HMAC) من مكتبة cryptography.
المفتاح مشتق من machine-id + app salt.
"""

import base64
import hashlib
import os
import sys


_APP_SALT = b"PharmacyApp_2026_SecureKey_v1"


def _get_machine_key() -> bytes:
    """يولّد مفتاح فريد لكل جهاز مشتق من machine-id."""
    sources = []

    # Windows: machine GUID من registry
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                  r"SOFTWARE\Microsoft\Cryptography")
            guid, _ = winreg.QueryValueEx(key, "MachineGuid")
            winreg.CloseKey(key)
            sources.append(guid.encode())
        except Exception:
            pass

    # Linux: /etc/machine-id
    for mid_path in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
        if os.path.isfile(mid_path):
            try:
                with open(mid_path) as f:
                    sources.append(f.read().strip().encode())
                break
            except Exception:
                pass

    # Fallback: مسار البرنامج
    if not sources:
        if getattr(sys, "frozen", False):
            sources.append(os.path.dirname(sys.executable).encode())
        else:
            sources.append(str(os.path.abspath(__file__)).encode())

    combined = b"".join(sources) + _APP_SALT
    return hashlib.sha256(combined).digest()  # 32 bytes


def _get_fernet():
    """يرجع Fernet instance — يصنع مفتاح Base64URL من machine key."""
    try:
        from cryptography.fernet import Fernet
        raw_key  = _get_machine_key()
        b64_key  = base64.urlsafe_b64encode(raw_key)   # 44 chars
        return Fernet(b64_key)
    except ImportError:
        return None


def encrypt(plaintext: str) -> str:
    """
    يشفّر نصاً ويرجع Base64.
    لو cryptography مش موجودة يرجع النص كما هو (مع prefix للتعرف عليه).
    """
    if not plaintext:
        return ""
    f = _get_fernet()
    if f is None:
        # Fallback بسيط: XOR مع salt + base64 (أفضل من plain text)
        raw = plaintext.encode("utf-8")
        key = (_APP_SALT * (len(raw) // len(_APP_SALT) + 1))[:len(raw)]
        xored = bytes(a ^ b for a, b in zip(raw, key))
        return "XOR:" + base64.b64encode(xored).decode()
    token = f.encrypt(plaintext.encode("utf-8"))
    return "FRN:" + token.decode()


def decrypt(ciphertext: str) -> str:
    """يفك تشفير نص — يتعرف تلقائياً على نوع التشفير."""
    if not ciphertext:
        return ""
    if ciphertext.startswith("FRN:"):
        f = _get_fernet()
        if f is None:
            return ""
        try:
            return f.decrypt(ciphertext[4:].encode()).decode("utf-8")
        except Exception:
            return ""
    if ciphertext.startswith("XOR:"):
        try:
            xored = base64.b64decode(ciphertext[4:])
            key   = (_APP_SALT * (len(xored) // len(_APP_SALT) + 1))[:len(xored)]
            return bytes(a ^ b for a, b in zip(xored, key)).decode("utf-8")
        except Exception:
            return ""
    # بدون prefix = plain text قديم
    return ciphertext


def is_encrypted(value: str) -> bool:
    return value.startswith(("FRN:", "XOR:"))
