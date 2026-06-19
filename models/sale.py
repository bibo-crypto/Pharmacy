from database.connection import get_connection
from utils.audit import log_action
from utils.helpers import generate_invoice_number


def create_sale(sale_data: dict, items: list) -> int:
    conn = get_connection()
    c = conn.cursor()
    invoice_number = generate_invoice_number("invoice_prefix")
    c.execute("""
        INSERT INTO sales (invoice_number, customer_id, user_id, subtotal, discount,
            discount_type, tax, total, paid_amount, change_amount, payment_method, notes)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        invoice_number,
        sale_data.get("customer_id"),
        sale_data["user_id"],
        sale_data.get("subtotal", 0),
        sale_data.get("discount", 0),
        sale_data.get("discount_type", "amount"),
        sale_data.get("tax", 0),
        sale_data.get("total", 0),
        sale_data.get("paid_amount", 0),
        sale_data.get("change_amount", 0),
        sale_data.get("payment_method", "cash"),
        sale_data.get("notes", ""),
    ))
    sale_id = c.lastrowid

    for item in items:
        c.execute("""
            INSERT INTO sale_items (sale_id, medicine_id, quantity, unit_price, discount, total)
            VALUES (?,?,?,?,?,?)
        """, (sale_id, item["medicine_id"], item["quantity"],
              item["unit_price"], item.get("discount", 0), item["total"]))
        # خصم الكمية من المخزون مباشرة
        c.execute("UPDATE medicines SET quantity = quantity - ? WHERE id = ?",
                  (item["quantity"], item["medicine_id"]))

    # تسجيل العملية في الخزينة
    c.execute("""
        INSERT INTO treasury (transaction_type, amount, description, user_id, reference_id, reference_type)
        VALUES ('income', ?, ?, ?, ?, 'sale')
    """, (sale_data.get("total", 0), f"بيع فاتورة {invoice_number}",
          sale_data["user_id"], sale_id))

    # تحديث الشيفت المفتوح إن وجد
    shift = _get_open_shift_internal(c)
    if shift:
        c.execute("UPDATE shifts SET total_sales = total_sales + ? WHERE id = ?",
                  (sale_data.get("total", 0), shift["id"]))

    conn.commit()
    conn.close()
    log_action("create_sale", "sales", sale_id, new_values={"invoice": invoice_number, "total": sale_data.get("total", 0)})
    return sale_id


def create_pending_sale(sale_data: dict, items: list) -> int:
    """إنشاء فاتورة معلقة (من نقطة البيع → الكاشير) - لا يُخصم المخزون هنا"""
    conn = get_connection()
    c = conn.cursor()
    invoice_number = generate_invoice_number("invoice_prefix")
    c.execute("""
        INSERT INTO sales (invoice_number, customer_id, user_id, subtotal, discount,
            discount_type, tax, total, paid_amount, change_amount, payment_method, notes, status)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        invoice_number,
        sale_data.get("customer_id"),
        sale_data["user_id"],
        sale_data.get("subtotal", 0),
        sale_data.get("discount", 0),
        sale_data.get("discount_type", "amount"),
        sale_data.get("tax", 0),
        sale_data.get("total", 0),
        0,
        0,
        "pending",
        sale_data.get("notes", ""),
        "pending",
    ))
    sale_id = c.lastrowid

    for item in items:
        c.execute("""
            INSERT INTO sale_items (sale_id, medicine_id, quantity, unit_price, discount, total)
            VALUES (?,?,?,?,?,?)
        """, (sale_id, item["medicine_id"], item["quantity"],
              item["unit_price"], item.get("discount", 0), item["total"]))

    conn.commit()
    conn.close()
    log_action("create_pending_sale", "sales", sale_id,
               new_values={"invoice": invoice_number, "total": sale_data.get("total", 0), "status": "pending"})
    return sale_id


def complete_pending_sale(sale_id: int, payment_data: dict) -> int:
    """إتمام الفاتورة المعلقة - يُخصم المخزون هنا فقط"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM sales WHERE id = ?", (sale_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise ValueError("الفاتورة غير موجودة")
    sale = dict(row)
    if sale.get("status") != "pending":
        conn.close()
        raise ValueError("لا يمكن إتمام هذه الفاتورة لأنها ليست في حالة معلقة")

    paid_amount = payment_data.get("paid_amount", 0)
    payment_method = payment_data.get("payment_method", "cash")
    total = sale.get("total", 0)
    change_amount = round(paid_amount - total, 2)

    c.execute("""
        UPDATE sales SET paid_amount=?, change_amount=?, payment_method=?, status='completed'
        WHERE id=?
    """, (paid_amount, change_amount, payment_method, sale_id))

    # خصم المخزون عند الإتمام الفعلي
    c.execute("SELECT * FROM sale_items WHERE sale_id = ?", (sale_id,))
    items = [dict(r) for r in c.fetchall()]
    for item in items:
        # التحقق من الكمية المتاحة قبل الخصم
        c.execute("SELECT quantity FROM medicines WHERE id=?", (item["medicine_id"],))
        med_row = c.fetchone()
        if med_row:
            available = med_row["quantity"]
            if available < item["quantity"]:
                conn.close()
                raise ValueError(f"الكمية في المخزون غير كافية للصنف رقم {item['medicine_id']}")
        c.execute("UPDATE medicines SET quantity = quantity - ? WHERE id = ?",
                  (item["quantity"], item["medicine_id"]))

    # تسجيل في الخزينة
    from utils.auth import get_current_user
    user = get_current_user()
    user_id = payment_data.get("user_id") or (user["id"] if user else 1)
    c.execute("""
        INSERT INTO treasury (transaction_type, amount, description, user_id, reference_id, reference_type)
        VALUES ('income', ?, ?, ?, ?, 'sale')
    """, (total, f"بيع فاتورة {sale.get('invoice_number','')}", user_id, sale_id))

    shift = _get_open_shift_internal(c)
    if shift:
        c.execute("UPDATE shifts SET total_sales = total_sales + ? WHERE id = ?",
                  (total, shift["id"]))

    conn.commit()
    conn.close()
    log_action("complete_pending_sale", "sales", sale_id,
               new_values={"paid_amount": paid_amount, "payment_method": payment_method, "status": "completed"})
    return sale_id


def get_pending_sales(search=None, limit=200):
    conn = get_connection()
    c = conn.cursor()
    query = """
        SELECT s.*, u.full_name as cashier_name, c.name as customer_name
        FROM sales s
        JOIN users u ON s.user_id = u.id
        LEFT JOIN customers c ON s.customer_id = c.id
        WHERE s.status = 'pending'
    """
    params = []
    if search:
        query += " AND (s.invoice_number LIKE ? OR c.name LIKE ? OR u.full_name LIKE ?)"
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]
    query += " ORDER BY s.sale_date ASC LIMIT ?"
    params.append(limit)
    c.execute(query, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def _get_open_shift_internal(cursor):
    cursor.execute("SELECT * FROM shifts WHERE status='open' ORDER BY opened_at DESC LIMIT 1")
    row = cursor.fetchone()
    return dict(row) if row else None


def get_all_sales(search=None, date_from=None, date_to=None, limit=200):
    conn = get_connection()
    c = conn.cursor()
    query = """
        SELECT s.*, u.full_name as cashier_name,
               c.name as customer_name
        FROM sales s
        JOIN users u ON s.user_id = u.id
        LEFT JOIN customers c ON s.customer_id = c.id
        WHERE s.status != 'cancelled'
    """
    params = []
    if search:
        query += " AND (s.invoice_number LIKE ? OR c.name LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    if date_from:
        query += " AND date(s.sale_date) >= ?"
        params.append(date_from)
    if date_to:
        query += " AND date(s.sale_date) <= ?"
        params.append(date_to)
    query += " ORDER BY s.sale_date DESC LIMIT ?"
    params.append(limit)
    c.execute(query, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_sale_by_id(sale_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT s.*, u.full_name as cashier_name, c.name as customer_name
        FROM sales s
        JOIN users u ON s.user_id = u.id
        LEFT JOIN customers c ON s.customer_id = c.id
        WHERE s.id = ?
    """, (sale_id,))
    sale = c.fetchone()
    if not sale:
        conn.close()
        return None, []
    sale = dict(sale)

    # تعديل الاستعلام لحساب الكمية الصافية المتبقية (الأصلية - المرتجعة)
    c.execute("""
        SELECT si.*, m.name as medicine_name, m.unit,
               COALESCE((SELECT SUM(sri.quantity) FROM sales_return_items sri 
                         JOIN sales_returns sr ON sri.return_id = sr.id 
                         WHERE sr.sale_id = si.sale_id AND sri.medicine_id = si.medicine_id), 0) as returned_qty
        FROM sale_items si 
        JOIN medicines m ON si.medicine_id = m.id
        WHERE si.sale_id = ?
    """, (sale_id,))
    items = []
    for r in c.fetchall():
        d = dict(r)
        d["original_quantity"] = d["quantity"]
        d["quantity"] = d["quantity"] - d["returned_qty"]
        if d["original_quantity"] > 0:
            d["total"] = round((d["quantity"] / d["original_quantity"]) * d["total"], 2)
        items.append(d)

    conn.close()
    return sale, items


def cancel_sale(sale_id: int, reason: str = ""):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM sales WHERE id = ?", (sale_id,))
    sale = c.fetchone()
    if not sale or dict(sale)["status"] == "cancelled":
        conn.close()
        return False
    sale_dict = dict(sale)
    # إعادة المخزون فقط إذا كانت الفاتورة مكتملة (تم خصم مخزونها)
    if sale_dict["status"] == "completed":
        # نستخدم الوظيفة المعدلة لجلب الكميات المتبقية فقط (التي لم يتم إرجاعها)
        _, items = get_sale_by_id(sale_id)
        for item in items:
            if item["quantity"] > 0:
                c.execute("UPDATE medicines SET quantity = quantity + ? WHERE id = ?",
                          (item["quantity"], item["medicine_id"]))
        # عكس معاملة الخزينة
        from utils.auth import get_current_user
        user = get_current_user()
        if user:
            c.execute("""
                INSERT INTO treasury (transaction_type, amount, description, user_id, reference_id, reference_type)
                VALUES ('expense', ?, ?, ?, ?, 'sale_cancel')
            """, (sale_dict["total"], f"إلغاء فاتورة {sale_dict['invoice_number']}",
                  user["id"], sale_id))
        
        # تحديث الوردية بخصم المبلغ الملغى من إجمالي مبيعات اليوم
        shift = _get_open_shift_internal(c)
        if shift:
            c.execute("UPDATE shifts SET total_sales = total_sales - ? WHERE id = ?",
                      (sale_dict["total"], shift["id"]))

    c.execute("UPDATE sales SET status = 'cancelled' WHERE id = ?", (sale_id,))
    conn.commit()
    conn.close()
    log_action("cancel_sale", "sales", sale_id, new_values={"reason": reason})
    return True


def get_sales_summary(date_from=None, date_to=None):
    conn = get_connection()
    c = conn.cursor()
    query = "SELECT COUNT(*) as count, SUM(total) as revenue, SUM(discount) as discounts FROM sales WHERE status='completed'"
    params = []
    if date_from:
        query += " AND date(sale_date) >= ?"
        params.append(date_from)
    if date_to:
        query += " AND date(sale_date) <= ?"
        params.append(date_to)
    c.execute(query, params)
    row = dict(c.fetchone())
    conn.close()
    return row
