import re
from datetime import datetime
from database.connection import get_connection


def get_setting(key: str, default="") -> str:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else default


def set_setting(key: str, value: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, value))
    conn.commit()
    conn.close()


def generate_invoice_number(prefix_key="invoice_prefix") -> str:
    """توليد رقم فاتورة فريد بدون تكرار"""
    prefix = get_setting(prefix_key, "INV")
    conn = get_connection()
    c = conn.cursor()
    date_str = datetime.now().strftime("%Y%m%d")
    # البحث عن أعلى رقم تسلسلي لليوم الحالي لضمان عدم التكرار
    if prefix_key == "invoice_prefix":
        pattern = f"{prefix}-{date_str}-%"
        c.execute("SELECT invoice_number FROM sales WHERE invoice_number LIKE ? ORDER BY id DESC LIMIT 1", (pattern,))
    else:
        pattern = f"{prefix}-{date_str}-%"
        c.execute("SELECT invoice_number FROM purchases WHERE invoice_number LIKE ? ORDER BY id DESC LIMIT 1", (pattern,))
    row = c.fetchone()
    conn.close()
    if row:
        try:
            last_seq = int(row[0].split("-")[-1])
            seq = last_seq + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1
    return f"{prefix}-{date_str}-{seq:04d}"


def format_currency(amount, currency=None) -> str:
    if currency is None:
        currency = get_setting("currency", "ج.م")
    try:
        return f"{float(amount):,.2f} {currency}"
    except (ValueError, TypeError):
        return f"0.00 {currency}"


def validate_barcode(barcode: str) -> bool:
    if not barcode:
        return False
    return bool(re.match(r'^[A-Za-z0-9\-_]{4,30}$', barcode))


def is_barcode_unique(barcode: str, exclude_id=None) -> bool:
    conn = get_connection()
    c = conn.cursor()
    if exclude_id:
        c.execute("SELECT id FROM medicines WHERE barcode = ? AND id != ?", (barcode, exclude_id))
    else:
        c.execute("SELECT id FROM medicines WHERE barcode = ?", (barcode,))
    row = c.fetchone()
    conn.close()
    return row is None


def get_next_shift_id() -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM shifts WHERE status = 'open' ORDER BY opened_at DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


def get_open_shift():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT s.*, u.full_name FROM shifts s
        JOIN users u ON s.user_id = u.id
        WHERE s.status = 'open'
        ORDER BY s.opened_at DESC LIMIT 1
    """)
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def truncate_text(text: str, max_len: int) -> str:
    if not text:
        return ""
    return text if len(text) <= max_len else text[:max_len - 3] + "..."
