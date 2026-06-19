from database.connection import get_connection
from utils.audit import log_action


def get_all_customers(search=None, active_only=True):
    conn = get_connection()
    c = conn.cursor()
    query = "SELECT * FROM customers WHERE 1=1"
    params = []
    if active_only:
        query += " AND is_active = 1"
    if search:
        query += " AND (name LIKE ? OR phone LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    query += " ORDER BY name"
    c.execute(query, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_customer_by_id(cid: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM customers WHERE id = ?", (cid,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def add_customer(data: dict) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO customers (name, phone, email, address, notes)
        VALUES (?,?,?,?,?)
    """, (data["name"], data.get("phone", ""), data.get("email", ""),
          data.get("address", ""), data.get("notes", "")))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    log_action("add", "customers", new_id, new_values=data)
    return new_id


def update_customer(cid: int, data: dict):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE customers SET name=?, phone=?, email=?, address=?, notes=?
        WHERE id=?
    """, (data["name"], data.get("phone", ""), data.get("email", ""),
          data.get("address", ""), data.get("notes", ""), cid))
    conn.commit()
    conn.close()
    log_action("edit", "customers", cid, new_values=data)


def delete_customer(cid: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE customers SET is_active = 0 WHERE id = ?", (cid,))
    conn.commit()
    conn.close()
    log_action("delete", "customers", cid)


def get_customer_purchases(cid: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT s.*, u.full_name as cashier_name
        FROM sales s JOIN users u ON s.user_id = u.id
        WHERE s.customer_id = ? AND s.status = 'completed'
        ORDER BY s.sale_date DESC
    """, (cid,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows
