from database.connection import get_connection
from utils.audit import log_action
from utils.helpers import generate_invoice_number


def create_purchase(purchase_data: dict, items: list) -> int:
    conn = get_connection()
    c = conn.cursor()
    invoice_number = generate_invoice_number("purchase_prefix")
    c.execute("""
        INSERT INTO purchases (invoice_number, supplier_id, user_id, subtotal, discount,
            tax, total, paid_amount, payment_method, notes)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (
        invoice_number,
        purchase_data["supplier_id"],
        purchase_data["user_id"],
        purchase_data.get("subtotal", 0),
        purchase_data.get("discount", 0),
        purchase_data.get("tax", 0),
        purchase_data.get("total", 0),
        purchase_data.get("paid_amount", 0),
        purchase_data.get("payment_method", "cash"),
        purchase_data.get("notes", ""),
    ))
    purchase_id = c.lastrowid

    for item in items:
        c.execute("""
            INSERT INTO purchase_items (purchase_id, medicine_id, quantity, unit_price, total, expiry_date)
            VALUES (?,?,?,?,?,?)
        """, (purchase_id, item["medicine_id"], item["quantity"],
              item["unit_price"], item["total"], item.get("expiry_date") or ""))
        # إضافة الكمية للمخزون
        c.execute("UPDATE medicines SET quantity = quantity + ? WHERE id = ?",
                  (item["quantity"], item["medicine_id"]))
        # تحديث سعر الشراء وتاريخ الصلاحية (الأقدم انتهاءً يُعطى الأولوية للعرض)
        c.execute("""
            UPDATE medicines SET purchase_price = ?
            WHERE id = ?
        """, (item["unit_price"], item["medicine_id"]))
        if item.get("expiry_date"):
            # نحدّث تاريخ الصلاحية فقط إذا كان الجديد أقرب (لتحذير المخزون)
            c.execute("""
                UPDATE medicines SET expiry_date = ?
                WHERE id = ? AND (expiry_date IS NULL OR expiry_date = ''
                      OR date(?) < date(expiry_date))
            """, (item["expiry_date"], item["medicine_id"], item["expiry_date"]))

    # تسجيل في الخزينة
    c.execute("""
        INSERT INTO treasury (transaction_type, amount, description, user_id, reference_id, reference_type)
        VALUES ('expense', ?, ?, ?, ?, 'purchase')
    """, (purchase_data.get("total", 0), f"مشتريات فاتورة {invoice_number}",
          purchase_data["user_id"], purchase_id))

    conn.commit()
    conn.close()
    log_action("create_purchase", "purchases", purchase_id,
               new_values={"invoice": invoice_number, "total": purchase_data.get("total", 0)})
    return purchase_id


def get_all_purchases(search=None, date_from=None, date_to=None, limit=200):
    conn = get_connection()
    c = conn.cursor()
    query = """
        SELECT p.*, s.name as supplier_name, u.full_name as user_name
        FROM purchases p
        JOIN suppliers s ON p.supplier_id = s.id
        JOIN users u ON p.user_id = u.id
        WHERE 1=1
    """
    params = []
    if search:
        query += " AND (p.invoice_number LIKE ? OR s.name LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    if date_from:
        query += " AND date(p.purchase_date) >= ?"
        params.append(date_from)
    if date_to:
        query += " AND date(p.purchase_date) <= ?"
        params.append(date_to)
    query += " ORDER BY p.purchase_date DESC LIMIT ?"
    params.append(limit)
    c.execute(query, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_purchase_by_id(purchase_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT p.*, s.name as supplier_name, u.full_name as user_name
        FROM purchases p
        JOIN suppliers s ON p.supplier_id = s.id
        JOIN users u ON p.user_id = u.id
        WHERE p.id = ?
    """, (purchase_id,))
    purchase = c.fetchone()
    if not purchase:
        conn.close()
        return None, []
    purchase = dict(purchase)

    # حساب الكميات التي تم إرجاعها للمورد لخصمها من العرض
    c.execute("""
        SELECT pi.*, m.name as medicine_name, m.unit,
               COALESCE((SELECT SUM(pri.quantity) FROM purchase_return_items pri 
                         JOIN purchase_returns pr ON pri.return_id = pr.id 
                         WHERE pr.purchase_id = pi.purchase_id AND pri.medicine_id = pi.medicine_id), 0) as returned_qty
        FROM purchase_items pi 
        JOIN medicines m ON pi.medicine_id = m.id
        WHERE pi.purchase_id = ?
    """, (purchase_id,))
    items = []
    for r in c.fetchall():
        d = dict(r)
        d["quantity"] = d["quantity"] - d["returned_qty"]
        items.append(d)

    conn.close()
    return purchase, items
