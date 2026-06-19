from database.connection import get_connection
from utils.audit import log_action


def get_all_suppliers(search=None, active_only=True):
    conn = get_connection()
    c = conn.cursor()
    query = "SELECT * FROM suppliers WHERE 1=1"
    params = []
    if active_only:
        query += " AND is_active = 1"
    if search:
        query += " AND (name LIKE ? OR contact_person LIKE ? OR phone LIKE ?)"
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]
    query += " ORDER BY name"
    c.execute(query, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_supplier_by_id(sid: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM suppliers WHERE id = ?", (sid,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def add_supplier(data: dict) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO suppliers (name, contact_person, phone, email, address, notes)
        VALUES (?,?,?,?,?,?)
    """, (data["name"], data.get("contact_person", ""), data.get("phone", ""),
          data.get("email", ""), data.get("address", ""), data.get("notes", "")))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    log_action("add", "suppliers", new_id, new_values=data)
    return new_id


def update_supplier(sid: int, data: dict):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE suppliers SET name=?, contact_person=?, phone=?, email=?, address=?, notes=?
        WHERE id=?
    """, (data["name"], data.get("contact_person", ""), data.get("phone", ""),
          data.get("email", ""), data.get("address", ""), data.get("notes", ""), sid))
    conn.commit()
    conn.close()
    log_action("edit", "suppliers", sid, new_values=data)


def delete_supplier(sid: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE suppliers SET is_active = 0 WHERE id = ?", (sid,))
    conn.commit()
    conn.close()
    log_action("delete", "suppliers", sid)
