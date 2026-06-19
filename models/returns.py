from database.connection import get_connection
from utils.audit import log_action
from utils.auth import get_current_user


def create_sales_return(sale_id: int, items: list, reason: str) -> int:
    """مرتجع بيع: يُعاد المخزون ويُخصم من الخزينة"""
    user = get_current_user()
    if not user:
        raise ValueError("يجب تسجيل الدخول أولاً")
    conn = get_connection()
    c = conn.cursor()

    # التحقق من أن الفاتورة مكتملة
    c.execute("SELECT status FROM sales WHERE id=?", (sale_id,))
    sale_row = c.fetchone()
    if not sale_row:
        conn.close()
        raise ValueError(f"الفاتورة رقم {sale_id} غير موجودة")
    if sale_row["status"] != "completed":
        conn.close()
        raise ValueError("لا يمكن إرجاع فاتورة غير مكتملة")

    total_amount = sum(item["amount"] for item in items)
    c.execute("""
        INSERT INTO sales_returns (sale_id, user_id, return_reason, total_return_amount)
        VALUES (?,?,?,?)
    """, (sale_id, user["id"], reason, total_amount))
    return_id = c.lastrowid

    for item in items:
        c.execute("""
            INSERT INTO sales_return_items (return_id, medicine_id, quantity, amount)
            VALUES (?,?,?,?)
        """, (return_id, item["medicine_id"], item["quantity"], item["amount"]))
        # إعادة الكمية للمخزون
        c.execute("UPDATE medicines SET quantity = quantity + ? WHERE id = ?",
                  (item["quantity"], item["medicine_id"]))

    # تسجيل في الخزينة كمصروف (رد المبلغ للعميل)
    c.execute("""
        INSERT INTO treasury (transaction_type, amount, description, user_id, reference_id, reference_type)
        VALUES ('expense', ?, ?, ?, ?, 'sales_return')
    """, (total_amount, f"مرتجع بيع فاتورة #{sale_id}", user["id"], return_id))

    # تحديث الوردية لخصم مبلغ المرتجع من مبيعات الوردية لضمان دقة الجرد
    c.execute("SELECT id FROM shifts WHERE status='open' ORDER BY opened_at DESC LIMIT 1")
    shift = c.fetchone()
    if shift:
        c.execute("UPDATE shifts SET total_sales = total_sales - ? WHERE id = ?", (total_amount, shift["id"]))

    conn.commit()
    conn.close()
    log_action("process_returns", "sales_returns", return_id,
               new_values={"sale_id": sale_id, "total": total_amount, "reason": reason})
    return return_id


def create_purchase_return(purchase_id: int, supplier_id: int, items: list, reason: str) -> int:
    """مرتجع شراء: يُخصم المخزون ويُضاف للخزينة"""
    user = get_current_user()
    if not user:
        raise ValueError("يجب تسجيل الدخول أولاً")
    conn = get_connection()
    c = conn.cursor()

    total_amount = sum(item["amount"] for item in items)
    c.execute("""
        INSERT INTO purchase_returns (purchase_id, supplier_id, user_id, reason, total_amount)
        VALUES (?,?,?,?,?)
    """, (purchase_id, supplier_id, user["id"], reason, total_amount))
    return_id = c.lastrowid

    for item in items:
        c.execute("""
            INSERT INTO purchase_return_items (return_id, medicine_id, quantity, amount)
            VALUES (?,?,?,?)
        """, (return_id, item["medicine_id"], item["quantity"], item["amount"]))
        # خصم الكمية من المخزون (مع الحد بصفر)
        c.execute("""
            UPDATE medicines SET quantity = MAX(0, quantity - ?) WHERE id = ?
        """, (item["quantity"], item["medicine_id"]))

    # تسجيل في الخزينة كإيراد (استرداد من المورد)
    c.execute("""
        INSERT INTO treasury (transaction_type, amount, description, user_id, reference_id, reference_type)
        VALUES ('income', ?, ?, ?, ?, 'purchase_return')
    """, (total_amount, f"مرتجع شراء فاتورة #{purchase_id}", user["id"], return_id))

    conn.commit()
    conn.close()
    log_action("create_purchase_return", "purchase_returns", return_id,
               new_values={"purchase_id": purchase_id, "total": total_amount, "reason": reason})
    return return_id


def get_all_sales_returns(search=None, date_from=None, date_to=None, limit=200):
    conn = get_connection()
    c = conn.cursor()
    query = """
        SELECT sr.*, s.invoice_number, u.full_name as user_name
        FROM sales_returns sr
        JOIN sales s ON sr.sale_id = s.id
        JOIN users u ON sr.user_id = u.id
        WHERE 1=1
    """
    params = []
    if search:
        query += " AND (s.invoice_number LIKE ?)"
        params.append(f"%{search}%")
    if date_from:
        query += " AND date(sr.return_date) >= ?"
        params.append(date_from)
    if date_to:
        query += " AND date(sr.return_date) <= ?"
        params.append(date_to)
    query += " ORDER BY sr.return_date DESC LIMIT ?"
    params.append(limit)
    c.execute(query, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_all_purchase_returns(search=None, date_from=None, date_to=None, limit=200):
    conn = get_connection()
    c = conn.cursor()
    query = """
        SELECT pr.*, p.invoice_number, s.name as supplier_name, u.full_name as user_name
        FROM purchase_returns pr
        JOIN purchases p ON pr.purchase_id = p.id
        JOIN suppliers s ON pr.supplier_id = s.id
        JOIN users u ON pr.user_id = u.id
        WHERE 1=1
    """
    params = []
    if search:
        query += " AND (p.invoice_number LIKE ? OR s.name LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    if date_from:
        query += " AND date(pr.return_date) >= ?"
        params.append(date_from)
    if date_to:
        query += " AND date(pr.return_date) <= ?"
        params.append(date_to)
    query += " ORDER BY pr.return_date DESC LIMIT ?"
    params.append(limit)
    c.execute(query, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_return_items(return_id: int, is_purchase_return=False):
    conn = get_connection()
    c = conn.cursor()
    if is_purchase_return:
        c.execute("""
            SELECT ri.*, m.name as medicine_name
            FROM purchase_return_items ri
            JOIN medicines m ON ri.medicine_id = m.id
            WHERE ri.return_id = ?
        """, (return_id,))
    else:
        c.execute("""
            SELECT ri.*, m.name as medicine_name
            FROM sales_return_items ri
            JOIN medicines m ON ri.medicine_id = m.id
            WHERE ri.return_id = ?
        """, (return_id,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows
