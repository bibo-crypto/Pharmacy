import json
from database.connection import get_connection


def log_action(action: str, table_name, record_id, old_values=None, new_values=None):
    try:
        from utils.auth import get_current_user
        user = get_current_user()
        if not user:
            return
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO audit_logs (user_id, action, table_name, record_id, old_values, new_values)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user["id"],
            action,
            table_name,
            record_id,
            json.dumps(old_values, ensure_ascii=False) if old_values else None,
            json.dumps(new_values, ensure_ascii=False) if new_values else None,
        ))
        conn.commit()
        conn.close()
    except Exception:
        pass


def get_audit_logs(limit=200, user_id=None, action=None, table_name=None):
    conn = get_connection()
    c = conn.cursor()
    query = """
        SELECT al.*, u.full_name, u.username
        FROM audit_logs al
        JOIN users u ON al.user_id = u.id
        WHERE 1=1
    """
    params = []
    if user_id:
        query += " AND al.user_id = ?"
        params.append(user_id)
    if action:
        query += " AND al.action = ?"
        params.append(action)
    if table_name:
        query += " AND al.table_name = ?"
        params.append(table_name)
    query += " ORDER BY al.timestamp DESC LIMIT ?"
    params.append(limit)
    c.execute(query, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows
