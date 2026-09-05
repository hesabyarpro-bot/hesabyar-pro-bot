import os
import sqlite3
from pathlib import Path
from datetime import datetime
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.getenv("DB_PATH", str(BASE_DIR / "hesabyar.db")))
SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    address TEXT,
    notes TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    sku TEXT UNIQUE,
    unit TEXT NOT NULL DEFAULT 'عدد',
    sale_price INTEGER NOT NULL DEFAULT 0,
    purchase_cost INTEGER NOT NULL DEFAULT 0,
    stock REAL NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_no TEXT UNIQUE,
    invoice_type TEXT NOT NULL DEFAULT 'SALE',
    customer_id INTEGER,
    total_amount INTEGER NOT NULL DEFAULT 0,
    discount_amount INTEGER NOT NULL DEFAULT 0,
    tax_amount INTEGER NOT NULL DEFAULT 0,
    payable_amount INTEGER NOT NULL DEFAULT 0,
    payment_method TEXT,
    status TEXT NOT NULL DEFAULT 'CONFIRMED',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(customer_id) REFERENCES customers(id)
);
CREATE TABLE IF NOT EXISTS invoice_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity REAL NOT NULL DEFAULT 0,
    unit_price INTEGER NOT NULL DEFAULT 0,
    discount_amount INTEGER NOT NULL DEFAULT 0,
    tax_amount INTEGER NOT NULL DEFAULT 0,
    line_total INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
    FOREIGN KEY(product_id) REFERENCES products(id)
);
CREATE TABLE IF NOT EXISTS journal_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_no TEXT UNIQUE,
    description TEXT,
    reference_type TEXT,
    reference_id INTEGER,
    entry_date TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS journal_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    journal_entry_id INTEGER NOT NULL,
    account_code TEXT NOT NULL,
    description TEXT,
    debit INTEGER NOT NULL DEFAULT 0,
    credit INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(journal_entry_id)
        REFERENCES journal_entries(id)
        ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS stock_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    movement_type TEXT NOT NULL,
    quantity REAL NOT NULL DEFAULT 0,
    unit_cost INTEGER NOT NULL DEFAULT 0,
    reference_type TEXT,
    reference_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(product_id) REFERENCES products(id)
);
CREATE INDEX IF NOT EXISTS idx_customers_active
ON customers(active);
CREATE INDEX IF NOT EXISTS idx_products_active
ON products(active);
CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice
ON invoice_items(invoice_id);
CREATE INDEX IF NOT EXISTS idx_invoice_items_product
ON invoice_items(product_id);
CREATE INDEX IF NOT EXISTS idx_stock_movements_product
ON stock_movements(product_id);
CREATE INDEX IF NOT EXISTS idx_journal_lines_account
ON journal_lines(account_code);
"""
def get_conn():
    """
    ایجاد اتصال به دیتابیس SQLite.
    نام اصلی تابع در پروژه: get_conn
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        str(DB_PATH),
        timeout=30,
        check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn
def get_connection():
    """
    نام سازگار برای کدهای قدیمی پروژه.
    بعضی فایل‌های پروژه ممکن است هنوز از:
        get_connection()
    استفاده کنند.
    این تابع همان اتصال get_conn() را برمی‌گرداند.
    """
    return get_conn()
def column_exists(conn, table_name, column_name):
    """
    بررسی وجود یک ستون در جدول.
    """
    rows = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()
    return any(row["name"] == column_name for row in rows)
def table_exists(conn, table_name):
    """
    بررسی وجود جدول.
    """
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,)
    ).fetchone()
    return row is not None
def migrate_database(conn):
    """
    مهاجرت‌های لازم برای نسخه‌های قدیمی دیتابیس.
    """
    # ---------------------------------------------------------
    # customers.active
    # ---------------------------------------------------------
    if table_exists(conn, "customers"):
        if not column_exists(conn, "customers", "active"):
            conn.execute(
                """
                ALTER TABLE customers
                ADD COLUMN active INTEGER NOT NULL DEFAULT 1
                """
            )
    # ---------------------------------------------------------
    # products.active
    # ---------------------------------------------------------
    if table_exists(conn, "products"):
        if not column_exists(conn, "products", "active"):
            conn.execute(
                """
                ALTER TABLE products
                ADD COLUMN active INTEGER NOT NULL DEFAULT 1
                """
            )
        if not column_exists(conn, "products", "created_at"):
            conn.execute(
                """
                ALTER TABLE products
                ADD COLUMN created_at TEXT
                """
            )
    # ---------------------------------------------------------
    # customers.created_at
    # ---------------------------------------------------------
    if table_exists(conn, "customers"):
        if not column_exists(conn, "customers", "created_at"):
            conn.execute(
                """
                ALTER TABLE customers
                ADD COLUMN created_at TEXT
                """
            )
    conn.commit()
def seed_sample_data(conn):
    """
    فقط در صورتی که جدول‌ها خالی باشند،
    چند داده نمونه ایجاد می‌کند.
    """
    customer_count = conn.execute(
        "SELECT COUNT(*) AS c FROM customers"
    ).fetchone()["c"]
    if customer_count == 0:
        conn.execute(
            """
            INSERT INTO customers
                (name, phone, address, notes, active)
            VALUES
                (?, ?, ?, ?, 1)
            """,
            (
                "مشتری نمونه",
                "09120000000",
                "",
                "داده نمونه حساب‌یار پرو",
            )
        )
    product_count = conn.execute(
        "SELECT COUNT(*) AS c FROM products"
    ).fetchone()["c"]
    if product_count == 0:
        conn.execute(
            """
            INSERT INTO products
                (
                    name,
                    sku,
                    unit,
                    sale_price,
                    purchase_cost,
                    stock,
                    active
                )
            VALUES
                (?, ?, ?, ?, ?, ?, 1)
            """,
            (
                "کالای نمونه",
                "P001",
                "عدد",
                100000,
                70000,
                10,
            )
        )
    conn.commit()
def init_db():
    """
    ساخت دیتابیس و اجرای migrationها.
    """
    conn = get_conn()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
        migrate_database(conn)
        seed_sample_data(conn)
    finally:
        conn.close()
def execute(query, params=()):
    """
    اجرای یک دستور SQL و commit.
    """
    conn = get_conn()
    try:
        cursor = conn.execute(query, params)
        conn.commit()
        return cursor
    finally:
        conn.close()
def fetch_one(query, params=()):
    """
    دریافت یک رکورد.
    """
    conn = get_conn()
    try:
        return conn.execute(query, params).fetchone()
    finally:
        conn.close()
def fetch_all(query, params=()):
    """
    دریافت چند رکورد.
    """
    conn = get_conn()
    try:
        return conn.execute(query, params).fetchall()
    finally:
        conn.close()
# ============================================================
# مشتریان
# ============================================================
def create_customer(
    name,
    phone="",
    address="",
    notes=""
):
    conn = get_conn()
    try:
        cursor = conn.execute(
            """
            INSERT INTO customers
                (name, phone, address, notes, active)
            VALUES
                (?, ?, ?, ?, 1)
            """,
            (
                name,
                phone,
                address,
                notes,
            )
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()
def get_customer(customer_id):
    return fetch_one(
        """
        SELECT *
        FROM customers
        WHERE id = ?
        """,
        (customer_id,)
    )
def list_customers(active_only=True):
    conn = get_conn()
    try:
        if active_only:
            return conn.execute(
                """
                SELECT *
                FROM customers
                WHERE active = 1
                ORDER BY id DESC
                """
            ).fetchall()
        return conn.execute(
            """
            SELECT *
            FROM customers
            ORDER BY id DESC
            """
        ).fetchall()
    finally:
        conn.close()
def update_customer(
    customer_id,
    name,
    phone="",
    address="",
    notes=""
):
    conn = get_conn()
    try:
        conn.execute(
            """
            UPDATE customers
            SET
                name = ?,
                phone = ?,
                address = ?,
                notes = ?
            WHERE id = ?
            """,
            (
                name,
                phone,
                address,
                notes,
                customer_id,
            )
        )
        conn.commit()
    finally:
        conn.close()
def deactivate_customer(customer_id):
    execute(
        """
        UPDATE customers
        SET active = 0
        WHERE id = ?
        """,
        (customer_id,)
    )
def activate_customer(customer_id):
    execute(
        """
        UPDATE customers
        SET active = 1
        WHERE id = ?
        """,
        (customer_id,)
    )
# ============================================================
# کالاها
# ============================================================
def create_product(
    name,
    sku=None,
    unit="عدد",
    sale_price=0,
    purchase_cost=0,
    stock=0
):
    conn = get_conn()
    try:
        cursor = conn.execute(
            """
            INSERT INTO products
                (
                    name,
                    sku,
                    unit,
                    sale_price,
                    purchase_cost,
                    stock,
                    active
                )
            VALUES
                (?, ?, ?, ?, ?, ?, 1)
            """,
            (
                name,
                sku,
                unit,
                sale_price,
                purchase_cost,
                stock,
            )
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.rollback()
        raise
    finally:
        conn.close()
def get_product(product_id):
    return fetch_one(
        """
        SELECT *
        FROM products
        WHERE id = ?
        """,
        (product_id,)
    )
def get_product_by_sku(sku):
    return fetch_one(
        """
        SELECT *
        FROM products
        WHERE sku = ?
        """,
        (sku,)
    )
def list_products(active_only=True):
    conn = get_conn()
    try:
        if active_only:
            return conn.execute(
                """
                SELECT *
                FROM products
                WHERE active = 1
                ORDER BY id DESC
                """
            ).fetchall()
        return conn.execute(
            """
            SELECT *
            FROM products
            ORDER BY id DESC
            """
        ).fetchall()
    finally:
        conn.close()
def update_product(
    product_id,
    name,
    sku=None,
    unit="عدد",
    sale_price=0,
    purchase_cost=0
):
    conn = get_conn()
    try:
        conn.execute(
            """
            UPDATE products
            SET
                name = ?,
                sku = ?,
                unit = ?,
                sale_price = ?,
                purchase_cost = ?
            WHERE id = ?
            """,
            (
                name,
                sku,
                unit,
                sale_price,
                purchase_cost,
                product_id,
            )
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        raise
    finally:
        conn.close()
def deactivate_product(product_id):
    execute(
        """
        UPDATE products
        SET active = 0
        WHERE id = ?
        """,
        (product_id,)
    )
def activate_product(product_id):
    execute(
        """
        UPDATE products
        SET active = 1
        WHERE id = ?
        """,
        (product_id,)
    )
def update_product_stock(
    product_id,
    quantity
):
    """
    افزایش/کاهش موجودی کالا.
    مثال:
        update_product_stock(1, 5)
        update_product_stock(1, -2)
    """
    conn = get_conn()
    try:
        conn.execute(
            """
            UPDATE products
            SET stock = stock + ?
            WHERE id = ?
            """,
            (
                quantity,
                product_id,
            )
        )
        conn.commit()
    finally:
        conn.close()
# ============================================================
# فاکتور
# ============================================================
def create_invoice(
    invoice_no,
    invoice_type="SALE",
    customer_id=None,
    total_amount=0,
    discount_amount=0,
    tax_amount=0,
    payable_amount=0,
    payment_method=None,
    status="CONFIRMED"
):
    conn = get_conn()
    try:
        cursor = conn.execute(
            """
            INSERT INTO invoices
                (
                    invoice_no,
                    invoice_type,
                    customer_id,
                    total_amount,
                    discount_amount,
                    tax_amount,
                    payable_amount,
                    payment_method,
                    status
                )
            VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                invoice_no,
                invoice_type,
                customer_id,
                total_amount,
                discount_amount,
                tax_amount,
                payable_amount,
                payment_method,
                status,
            )
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()
def add_invoice_item(
    invoice_id,
    product_id,
    quantity,
    unit_price,
    discount_amount=0,
    tax_amount=0,
    line_total=0
):
    conn = get_conn()
    try:
        cursor = conn.execute(
            """
            INSERT INTO invoice_items
                (
                    invoice_id,
                    product_id,
                    quantity,
                    unit_price,
                    discount_amount,
                    tax_amount,
                    line_total
                )
            VALUES
                (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                invoice_id,
                product_id,
                quantity,
                unit_price,
                discount_amount,
                tax_amount,
                line_total,
            )
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()
# ============================================================
# اسناد حسابداری
# ============================================================
def create_journal_entry(
    entry_no,
    description="",
    reference_type=None,
    reference_id=None,
    entry_date=None
):
    if entry_date is None:
        entry_date = datetime.now().strftime("%Y-%m-%d")
    conn = get_conn()
    try:
        cursor = conn.execute(
            """
            INSERT INTO journal_entries
                (
                    entry_no,
                    description,
                    reference_type,
                    reference_id,
                    entry_date
                )
            VALUES
                (?, ?, ?, ?, ?)
            """,
            (
                entry_no,
                description,
                reference_type,
                reference_id,
                entry_date,
            )
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()
def add_journal_line(
    journal_entry_id,
    account_code,
    description="",
    debit=0,
    credit=0
):
    conn = get_conn()
    try:
        cursor = conn.execute(
            """
            INSERT INTO journal_lines
                (
                    journal_entry_id,
                    account_code,
                    description,
                    debit,
                    credit
                )
            VALUES
                (?, ?, ?, ?, ?)
            """,
            (
                journal_entry_id,
                account_code,
                description,
                debit,
                credit,
            )
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()
# ============================================================
# گردش انبار
# ============================================================
def add_stock_movement(
    product_id,
    movement_type,
    quantity,
    unit_cost=0,
    reference_type=None,
    reference_id=None
):
    conn = get_conn()
    try:
        cursor = conn.execute(
            """
            INSERT INTO stock_movements
                (
                    product_id,
                    movement_type,
                    quantity,
                    unit_cost,
                    reference_type,
                    reference_id
                )
            VALUES
                (?, ?, ?, ?, ?, ?)
            """,
            (
                product_id,
                movement_type,
                quantity,
                unit_cost,
                reference_type,
                reference_id,
            )
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()
