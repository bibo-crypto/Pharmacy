from database.connection import get_connection
from utils.auth import hash_password
from utils.audit import log_action


def get_all_users(active_only=False):
    conn = get_connection()
    c = conn.cursor()
    query = """
        SELECT u.*, r.name as role_name
        FROM users u
        JOIN roles r ON u.role_id = r.id
        WHERE 1=1
    """
    if active_only:
        query += " AND u.is_active = 1"
    query += " ORDER BY u.full_name"
    c.execute(query)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_user_by_id(user_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT u.*, r.name as role_name
        FROM users u JOIN roles r ON u.role_id = r.id
        WHERE u.id = ?
    """, (user_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def add_user(data: dict) -> int:
    conn = get_connection()
    c = conn.cursor()
    pw = hash_password(data.get("password", "123456"))
    c.execute("""
        INSERT INTO users (username, password, full_name, role_id, email, phone)
        VALUES (?,?,?,?,?,?)
    """, (
        data["username"], pw, data["full_name"], data["role_id"],
        data.get("email", ""), data.get("phone", ""),
    ))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    log_action("add", "users", new_id, new_values={k: v for k, v in data.items() if k != "password"})
    return new_id


def update_user(user_id: int, data: dict):
    conn = get_connection()
    c = conn.cursor()
    if data.get("password"):
        pw = hash_password(data["password"])
        c.execute("""
            UPDATE users SET full_name=?, role_id=?, email=?, phone=?, is_active=?, password=?
            WHERE id=?
        """, (data["full_name"], data["role_id"], data.get("email", ""),
              data.get("phone", ""), data.get("is_active", 1), pw, user_id))
    else:
        c.execute("""
            UPDATE users SET full_name=?, role_id=?, email=?, phone=?, is_active=?
            WHERE id=?
        """, (data["full_name"], data["role_id"], data.get("email", ""),
              data.get("phone", ""), data.get("is_active", 1), user_id))
    conn.commit()
    conn.close()
    log_action("edit", "users", user_id, new_values={k: v for k, v in data.items() if k != "password"})


def delete_user(user_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    log_action("delete", "users", user_id)


def get_all_roles():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM roles ORDER BY id")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_role_permissions(role_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT permission_code FROM role_permissions WHERE role_id = ?", (role_id,))
    rows = [r[0] for r in c.fetchall()]
    conn.close()
    return rows


def get_all_permissions():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM permissions ORDER BY category, label")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def update_role_permissions(role_id: int, permission_codes: list):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM role_permissions WHERE role_id = ?", (role_id,))
    for code in permission_codes:
        c.execute("INSERT INTO role_permissions (role_id, permission_code) VALUES (?,?)", (role_id, code))
    conn.commit()
    conn.close()
    log_action("edit", "role_permissions", role_id)
