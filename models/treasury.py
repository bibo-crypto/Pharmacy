from database.connection import get_connection
from utils.audit import log_action


def get_treasury_transactions(date_from=None, date_to=None, t_type=None, limit=200):
    conn = get_connection()
    c = conn.cursor()
    query = """
        SELECT t.*, u.full_name as user_name
        FROM treasury t JOIN users u ON t.user_id = u.id
        WHERE 1=1
    """
    params = []
    if t_type:
        query += " AND t.transaction_type = ?"
        params.append(t_type)
    if date_from:
        query += " AND date(t.transaction_date) >= ?"
        params.append(date_from)
    if date_to:
        query += " AND date(t.transaction_date) <= ?"
        params.append(date_to)
    query += " ORDER BY t.transaction_date DESC LIMIT ?"
    params.append(limit)
    c.execute(query, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def add_treasury_transaction(t_type: str, amount: float, description: str, user_id: int) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO treasury (transaction_type, amount, description, user_id)
        VALUES (?,?,?,?)
    """, (t_type, amount, description, user_id))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    log_action(f"treasury_{t_type}", "treasury", new_id,
               new_values={"type": t_type, "amount": amount, "desc": description})
    return new_id


def open_shift(user_id: int, opening_balance: float) -> int:
    existing = get_open_shift()
    if existing:
        return existing["id"]
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO shifts (user_id, opening_balance, status)
        VALUES (?,?,'open')
    """, (user_id, opening_balance))
    new_id = c.lastrowid
    c.execute("""
        INSERT INTO treasury (transaction_type, amount, description, user_id)
        VALUES ('opening', ?, 'فتح وردية', ?)
    """, (opening_balance, user_id))
    conn.commit()
    conn.close()
    log_action("open_shift", "shifts", new_id)
    return new_id


def close_shift(shift_id: int, user_id: int, closing_balance: float, notes: str = ""):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE shifts SET status='closed', closing_balance=?, closed_at=datetime('now'), notes=?
        WHERE id=?
    """, (closing_balance, notes, shift_id))
    conn.commit()
    conn.close()
    log_action("close_shift", "shifts", shift_id)


def get_open_shift():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT s.*, u.full_name FROM shifts s
        JOIN users u ON s.user_id = u.id
        WHERE s.status='open'
        ORDER BY s.opened_at DESC LIMIT 1
    """)
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_shifts(limit=50):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT s.*, u.full_name as user_name FROM shifts s
        JOIN users u ON s.user_id = u.id
        ORDER BY s.opened_at DESC LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_treasury_balance():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT
            SUM(CASE WHEN transaction_type IN ('income','opening') THEN amount ELSE 0 END) -
            SUM(CASE WHEN transaction_type IN ('expense') THEN amount ELSE 0 END) as balance
        FROM treasury
    """)
    row = c.fetchone()
    conn.close()
    return row[0] or 0


def add_expense(title: str, amount: float, category: str, notes: str, user_id: int) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO expenses (title, amount, category, notes, user_id)
        VALUES (?,?,?,?,?)
    """, (title, amount, category, notes, user_id))
    exp_id = c.lastrowid
    c.execute("""
        INSERT INTO treasury (transaction_type, amount, description, user_id, reference_id, reference_type)
        VALUES ('expense', ?, ?, ?, ?, 'expense')
    """, (amount, f"مصروف: {title}", user_id, exp_id))
    shift = _get_open_shift_c(c)
    if shift:
        c.execute("UPDATE shifts SET total_expenses = total_expenses + ? WHERE id = ?",
                  (amount, shift["id"]))
    conn.commit()
    conn.close()
    log_action("add_expense", "expenses", exp_id)
    return exp_id


def _get_open_shift_c(cursor):
    cursor.execute("SELECT * FROM shifts WHERE status='open' ORDER BY opened_at DESC LIMIT 1")
    row = cursor.fetchone()
    return dict(row) if row else None


def get_all_expenses(date_from=None, date_to=None):
    conn = get_connection()
    c = conn.cursor()
    query = "SELECT e.*, u.full_name as user_name FROM expenses e JOIN users u ON e.user_id=u.id WHERE 1=1"
    params = []
    if date_from:
        query += " AND date(e.expense_date) >= ?"
        params.append(date_from)
    if date_to:
        query += " AND date(e.expense_date) <= ?"
        params.append(date_to)
    query += " ORDER BY e.expense_date DESC"
    c.execute(query, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows
