from database.connection import get_connection
from utils.audit import log_action


def get_all_medicines(active_only=True, search=None, category_id=None, low_stock=False):
    conn = get_connection()
    c = conn.cursor()
    query = """
        SELECT m.*, cat.name as category_name, s.name as supplier_name
        FROM medicines m
        LEFT JOIN categories cat ON m.category_id = cat.id
        LEFT JOIN suppliers s ON m.supplier_id = s.id
        WHERE 1=1
    """
    params = []
    if active_only:
        query += " AND m.is_active = 1"
    if search:
        query += " AND (m.name LIKE ? OR m.barcode LIKE ? OR m.generic_name LIKE ?)"
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]
    if category_id:
        query += " AND m.category_id = ?"
        params.append(category_id)
    if low_stock:
        query += " AND m.quantity <= m.min_quantity"
    query += " ORDER BY m.name"
    c.execute(query, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_medicine_by_id(medicine_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT m.*, cat.name as category_name, s.name as supplier_name
        FROM medicines m
        LEFT JOIN categories cat ON m.category_id = cat.id
        LEFT JOIN suppliers s ON m.supplier_id = s.id
        WHERE m.id = ?
    """, (medicine_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def get_medicine_by_barcode(barcode: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT m.*, cat.name as category_name
        FROM medicines m
        LEFT JOIN categories cat ON m.category_id = cat.id
        WHERE m.barcode = ? AND m.is_active = 1
    """, (barcode,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def add_medicine(data: dict) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO medicines (barcode, name, generic_name, category_id, supplier_id, unit,
            purchase_price, selling_price, quantity, min_quantity, expiry_date, location,
            description, requires_prescription)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("barcode"), data["name"], data.get("generic_name"),
        data.get("category_id"), data.get("supplier_id"), data.get("unit", "قطعة"),
        data.get("purchase_price", 0), data.get("selling_price", 0),
        data.get("quantity", 0), data.get("min_quantity", 5),
        data.get("expiry_date"), data.get("location"), data.get("description"),
        data.get("requires_prescription", 0),
    ))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    log_action("add", "medicines", new_id, new_values=data)
    return new_id


def update_medicine(medicine_id: int, data: dict):
    old = get_medicine_by_id(medicine_id)
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE medicines SET barcode=?, name=?, generic_name=?, category_id=?, supplier_id=?,
            unit=?, purchase_price=?, selling_price=?, quantity=?, min_quantity=?,
            expiry_date=?, location=?, description=?, requires_prescription=?,
            updated_at=datetime('now')
        WHERE id=?
    """, (
        data.get("barcode"), data["name"], data.get("generic_name"),
        data.get("category_id"), data.get("supplier_id"), data.get("unit", "قطعة"),
        data.get("purchase_price", 0), data.get("selling_price", 0),
        data.get("quantity", 0), data.get("min_quantity", 5),
        data.get("expiry_date"), data.get("location"), data.get("description"),
        data.get("requires_prescription", 0), medicine_id,
    ))
    conn.commit()
    conn.close()
    log_action("edit", "medicines", medicine_id, old_values=old, new_values=data)


def delete_medicine(medicine_id: int):
    old = get_medicine_by_id(medicine_id)
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE medicines SET is_active = 0 WHERE id = ?", (medicine_id,))
    conn.commit()
    conn.close()
    log_action("delete", "medicines", medicine_id, old_values=old)


def update_stock(medicine_id: int, quantity_change: int, conn=None):
    close_after = False
    if conn is None:
        conn = get_connection()
        close_after = True
    c = conn.cursor()
    c.execute("UPDATE medicines SET quantity = quantity + ? WHERE id = ?", (quantity_change, medicine_id))
    if close_after:
        conn.commit()
        conn.close()


def get_categories():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM categories ORDER BY name")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def add_category(name: str, description: str = "") -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO categories (name, description) VALUES (?,?)", (name, description))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return new_id


def get_expiring_medicines(days=30):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM medicines
        WHERE is_active = 1
          AND expiry_date IS NOT NULL
          AND expiry_date != ''
          AND date(expiry_date) <= date('now', ? || ' days')
          AND quantity > 0
        ORDER BY expiry_date
    """, (f"+{days}",))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows
