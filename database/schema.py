from .connection import get_connection


def _get_engine_clause() -> str:
    """يرجع ENGINE clause لـ MySQL أو فارغ لـ SQLite."""
    try:
        from database.db_config import get_db_type
        if get_db_type() == "mysql":
            return " ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
    except Exception:
        pass
    return ""


def create_tables():
    conn = get_connection()
    c = conn.cursor()

    c.executescript("""
    PRAGMA foreign_keys = ON;

    CREATE TABLE IF NOT EXISTS roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS permissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL UNIQUE,
        label TEXT NOT NULL,
        category TEXT
    );

    CREATE TABLE IF NOT EXISTS role_permissions (
        role_id INTEGER NOT NULL,
        permission_code TEXT NOT NULL,
        PRIMARY KEY (role_id, permission_code),
        FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role_id INTEGER NOT NULL,
        email TEXT,
        phone TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now')),
        last_login TEXT,
        FOREIGN KEY (role_id) REFERENCES roles(id)
    );

    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT
    );

    CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        contact_person TEXT,
        phone TEXT,
        email TEXT,
        address TEXT,
        notes TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        email TEXT,
        address TEXT,
        notes TEXT,
        loyalty_points INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS medicines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        barcode TEXT UNIQUE,
        name TEXT NOT NULL,
        generic_name TEXT,
        category_id INTEGER,
        supplier_id INTEGER,
        unit TEXT DEFAULT 'قطعة',
        purchase_price REAL DEFAULT 0,
        selling_price REAL DEFAULT 0,
        quantity INTEGER DEFAULT 0,
        min_quantity INTEGER DEFAULT 5,
        expiry_date TEXT,
        location TEXT,
        description TEXT,
        requires_prescription INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (category_id) REFERENCES categories(id),
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
    );

    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number TEXT NOT NULL UNIQUE,
        customer_id INTEGER,
        user_id INTEGER NOT NULL,
        subtotal REAL DEFAULT 0,
        discount REAL DEFAULT 0,
        discount_type TEXT DEFAULT 'amount',
        tax REAL DEFAULT 0,
        total REAL DEFAULT 0,
        paid_amount REAL DEFAULT 0,
        change_amount REAL DEFAULT 0,
        payment_method TEXT DEFAULT 'cash',
        notes TEXT,
        status TEXT DEFAULT 'completed',
        sale_date TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (customer_id) REFERENCES customers(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS sale_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id INTEGER NOT NULL,
        medicine_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        discount REAL DEFAULT 0,
        total REAL NOT NULL,
        FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE,
        FOREIGN KEY (medicine_id) REFERENCES medicines(id)
    );

    CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number TEXT NOT NULL UNIQUE,
        supplier_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        subtotal REAL DEFAULT 0,
        discount REAL DEFAULT 0,
        tax REAL DEFAULT 0,
        total REAL DEFAULT 0,
        paid_amount REAL DEFAULT 0,
        payment_method TEXT DEFAULT 'cash',
        notes TEXT,
        status TEXT DEFAULT 'completed',
        purchase_date TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS purchase_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        purchase_id INTEGER NOT NULL,
        medicine_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        total REAL NOT NULL,
        expiry_date TEXT,
        FOREIGN KEY (purchase_id) REFERENCES purchases(id) ON DELETE CASCADE,
        FOREIGN KEY (medicine_id) REFERENCES medicines(id)
    );

    CREATE TABLE IF NOT EXISTS sales_returns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        return_reason TEXT,
        total_return_amount REAL DEFAULT 0,
        return_date TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (sale_id) REFERENCES sales(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS sales_return_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        return_id INTEGER NOT NULL,
        medicine_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        amount REAL NOT NULL,
        FOREIGN KEY (return_id) REFERENCES sales_returns(id) ON DELETE CASCADE,
        FOREIGN KEY (medicine_id) REFERENCES medicines(id)
    );

    CREATE TABLE IF NOT EXISTS purchase_returns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        purchase_id INTEGER NOT NULL,
        supplier_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        reason TEXT,
        total_amount REAL DEFAULT 0,
        return_date TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (purchase_id) REFERENCES purchases(id),
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS purchase_return_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        return_id INTEGER NOT NULL,
        medicine_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        amount REAL NOT NULL,
        FOREIGN KEY (return_id) REFERENCES purchase_returns(id) ON DELETE CASCADE,
        FOREIGN KEY (medicine_id) REFERENCES medicines(id)
    );

    CREATE TABLE IF NOT EXISTS treasury (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_type TEXT NOT NULL,
        amount REAL NOT NULL,
        description TEXT,
        user_id INTEGER NOT NULL,
        reference_id INTEGER,
        reference_type TEXT,
        transaction_date TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS shifts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        opening_balance REAL DEFAULT 0,
        closing_balance REAL,
        total_sales REAL DEFAULT 0,
        total_expenses REAL DEFAULT 0,
        total_returns REAL DEFAULT 0,
        notes TEXT,
        status TEXT DEFAULT 'open',
        opened_at TEXT DEFAULT (datetime('now')),
        closed_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        amount REAL NOT NULL,
        category TEXT,
        notes TEXT,
        user_id INTEGER NOT NULL,
        expense_date TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        table_name TEXT,
        record_id INTEGER,
        old_values TEXT,
        new_values TEXT,
        ip_address TEXT,
        timestamp TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT,
        description TEXT
    );

    CREATE TABLE IF NOT EXISTS inventory_adjustments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        medicine_id INTEGER NOT NULL,
        adjustment_type TEXT NOT NULL,
        quantity_before INTEGER NOT NULL,
        quantity_after INTEGER NOT NULL,
        reason TEXT,
        user_id INTEGER NOT NULL,
        adjustment_date TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (medicine_id) REFERENCES medicines(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """)

    _seed_defaults(conn)
    conn.commit()
    conn.close()


def _seed_defaults(conn):
    c = conn.cursor()

    roles_data = [
        ("Super Admin", "مدير النظام الكامل"),
        ("Admin", "مدير الصيدلية"),
        ("Pharmacist", "صيدلاني"),
        ("Cashier", "كاشير"),
        ("Inventory Manager", "مدير المخزون"),
    ]
    for name, desc in roles_data:
        c.execute("INSERT OR IGNORE INTO roles (name, description) VALUES (?,?)", (name, desc))

    perms = [
        ("view_medicines", "عرض الأدوية", "medicines"),
        ("add_medicines", "إضافة أدوية", "medicines"),
        ("edit_medicines", "تعديل أدوية", "medicines"),
        ("delete_medicines", "حذف أدوية", "medicines"),
        ("view_sales", "عرض المبيعات", "sales"),
        ("create_sales", "إنشاء مبيعات", "sales"),
        ("cancel_sales", "إلغاء مبيعات", "sales"),
        ("process_returns", "معالجة المرتجعات", "returns"),
        ("view_purchases", "عرض المشتريات", "purchases"),
        ("create_purchases", "إنشاء مشتريات", "purchases"),
        ("manage_suppliers", "إدارة الموردين", "suppliers"),
        ("manage_customers", "إدارة العملاء", "customers"),
        ("manage_inventory", "إدارة المخزون", "inventory"),
        ("view_reports", "عرض التقارير", "reports"),
        ("export_reports", "تصدير التقارير", "reports"),
        ("manage_users", "إدارة المستخدمين", "users"),
        ("manage_settings", "إدارة الإعدادات", "settings"),
        ("backup_database", "نسخ احتياطي", "system"),
        ("restore_database", "استعادة النسخ", "system"),
        ("manage_treasury", "إدارة الخزينة", "treasury"),
    ]
    for code, label, cat in perms:
        c.execute("INSERT OR IGNORE INTO permissions (code, label, category) VALUES (?,?,?)", (code, label, cat))

    c.execute("SELECT id FROM roles WHERE name='Super Admin'")
    row = c.fetchone()
    if row:
        sa_id = row[0]
        for code, _, _ in perms:
            c.execute("INSERT OR IGNORE INTO role_permissions (role_id, permission_code) VALUES (?,?)", (sa_id, code))

    admin_perms = [p[0] for p in perms if p[0] not in ("manage_settings", "backup_database", "restore_database")]
    c.execute("SELECT id FROM roles WHERE name='Admin'")
    row = c.fetchone()
    if row:
        for code in admin_perms:
            c.execute("INSERT OR IGNORE INTO role_permissions (role_id, permission_code) VALUES (?,?)", (row[0], code))

    pharmacist_perms = ["view_medicines", "add_medicines", "edit_medicines", "view_sales", "create_sales",
                        "process_returns", "view_purchases", "manage_customers", "view_reports"]
    c.execute("SELECT id FROM roles WHERE name='Pharmacist'")
    row = c.fetchone()
    if row:
        for code in pharmacist_perms:
            c.execute("INSERT OR IGNORE INTO role_permissions (role_id, permission_code) VALUES (?,?)", (row[0], code))

    cashier_perms = ["view_medicines", "view_sales", "create_sales", "process_returns", "manage_customers"]
    c.execute("SELECT id FROM roles WHERE name='Cashier'")
    row = c.fetchone()
    if row:
        for code in cashier_perms:
            c.execute("INSERT OR IGNORE INTO role_permissions (role_id, permission_code) VALUES (?,?)", (row[0], code))

    inv_perms = ["view_medicines", "add_medicines", "edit_medicines", "view_purchases", "create_purchases",
                 "manage_suppliers", "manage_inventory", "view_reports"]
    c.execute("SELECT id FROM roles WHERE name='Inventory Manager'")
    row = c.fetchone()
    if row:
        for code in inv_perms:
            c.execute("INSERT OR IGNORE INTO role_permissions (role_id, permission_code) VALUES (?,?)", (row[0], code))

    from utils.auth import hash_password
    pw = hash_password("admin123")
    c.execute("SELECT id FROM roles WHERE name='Super Admin'")
    row = c.fetchone()
    if row:
        c.execute("""INSERT OR IGNORE INTO users (username, password, full_name, role_id)
                     VALUES ('admin', ?, 'مدير النظام', ?)""", (pw, row[0]))

    settings_defaults = [
        ("pharmacy_name", "صيدلية الأمل", "اسم الصيدلية"),
        ("pharmacy_address", "القاهرة، مصر", "عنوان الصيدلية"),
        ("pharmacy_phone", "01000000000", "هاتف الصيدلية"),
        ("pharmacy_license", "", "رقم الترخيص"),
        ("currency", "ج.م", "العملة"),
        ("tax_rate", "14", "نسبة الضريبة %"),
        ("receipt_footer", "شكراً لزيارتكم - نتمنى لكم الشفاء العاجل", "تذييل الإيصال"),
        ("low_stock_alert", "10", "حد التنبيه للمخزون المنخفض"),
        ("invoice_prefix", "INV", "بادئة رقم الفاتورة"),
        ("purchase_prefix", "PUR", "بادئة رقم أمر الشراء"),
        ("backup_path", "", "مسار النسخ الاحتياطي"),
        ("theme", "blue", "ثيم النظام"),
        ("language", "ar", "لغة النظام"),
    ]
    for key, val, desc in settings_defaults:
        c.execute("INSERT OR IGNORE INTO settings (key, value, description) VALUES (?,?,?)", (key, val, desc))

    categories_default = [
        ("مضادات حيوية",), ("مسكنات",), ("فيتامينات",), ("أدوية القلب",),
        ("أدوية السكر",), ("أدوية الضغط",), ("أدوية الجهاز الهضمي",),
        ("أدوية الجهاز التنفسي",), ("أدوية جلدية",), ("مستلزمات طبية",),
    ]
    for (name,) in categories_default:
        c.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (name,))

    category_ids = {}
    c.execute("SELECT id, name FROM categories")
    for row in c.fetchall():
        category_ids[row["name"]] = row["id"]

    demo_medicines = [
        {
            "barcode": "100000000001",
            "name": "Augmentin 1g",
            "generic_name": "Amoxicillin/Clavulanic Acid",
            "category": "مضادات حيوية",
            "unit": "شريط",
            "purchase_price": 120,
            "selling_price": 165,
            "quantity": 25,
            "min_quantity": 5,
            "expiry_date": "2027-12-31",
            "location": "A-1",
            "description": "مضاد حيوي تجريبي",
        },
        {
            "barcode": "100000000002",
            "name": "Panadol Extra",
            "generic_name": "Paracetamol/Caffeine",
            "category": "مسكنات",
            "unit": "علبة",
            "purchase_price": 35,
            "selling_price": 48,
            "quantity": 40,
            "min_quantity": 8,
            "expiry_date": "2027-06-30",
            "location": "B-2",
            "description": "مسكن وخافض حرارة",
        },
        {
            "barcode": "100000000003",
            "name": "Vitamin C 1000",
            "generic_name": "Ascorbic Acid",
            "category": "فيتامينات",
            "unit": "علبة",
            "purchase_price": 28,
            "selling_price": 42,
            "quantity": 30,
            "min_quantity": 6,
            "expiry_date": "2027-09-30",
            "location": "C-1",
            "description": "فيتامين سي فوّار",
        },
        {
            "barcode": "100000000004",
            "name": "Glucophage 850",
            "generic_name": "Metformin",
            "category": "أدوية السكر",
            "unit": "علبة",
            "purchase_price": 55,
            "selling_price": 78,
            "quantity": 18,
            "min_quantity": 4,
            "expiry_date": "2027-03-31",
            "location": "D-3",
            "description": "دواء للسكر",
        },
        {
            "barcode": "100000000005",
            "name": "Amlodipine 5mg",
            "generic_name": "Amlodipine",
            "category": "أدوية الضغط",
            "unit": "شريط",
            "purchase_price": 22,
            "selling_price": 31,
            "quantity": 12,
            "min_quantity": 5,
            "expiry_date": "2028-01-31",
            "location": "E-4",
            "description": "دواء ضغط",
        },
        {
            "barcode": "100000000006",
            "name": "Surgical Gloves",
            "generic_name": "Latex Gloves",
            "category": "مستلزمات طبية",
            "unit": "علبة",
            "purchase_price": 60,
            "selling_price": 88,
            "quantity": 50,
            "min_quantity": 10,
            "expiry_date": None,
            "location": "M-1",
            "description": "قفازات طبية للاختبار",
        },
    ]

    for item in demo_medicines:
        c.execute("""
            INSERT OR IGNORE INTO medicines
            (barcode, name, generic_name, category_id, unit, purchase_price, selling_price,
             quantity, min_quantity, expiry_date, location, description, requires_prescription)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item["barcode"],
            item["name"],
            item["generic_name"],
            category_ids.get(item["category"]),
            item["unit"],
            item["purchase_price"],
            item["selling_price"],
            item["quantity"],
            item["min_quantity"],
            item["expiry_date"],
            item["location"],
            item["description"],
            0,
        ))
