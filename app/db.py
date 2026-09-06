import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, date

DB_PATH = os.getenv("DB_PATH", "hesabyar.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


get_conn = get_connection


@contextmanager
def db_transaction():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def table_columns(conn, table_name):
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def add_column_if_missing(conn, table_name, column_name, definition):
    columns = table_columns(conn, table_name)
    if column_name not in columns:
        conn.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"
        )


def init_db():
    conn = get_connection()

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS telegram_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            address TEXT,
            active INTEGER DEFAULT 1,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            address TEXT,
            active INTEGER DEFAULT 1,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT,
            unit TEXT DEFAULT 'عدد',
            purchase_cost REAL DEFAULT 0,
            sale_price REAL DEFAULT 0,
            stock REAL DEFAULT 0,
            min_stock REAL DEFAULT 0,
            active INTEGER DEFAULT 1,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_type TEXT NOT NULL,
            customer_id INTEGER,
            supplier_id INTEGER,
            invoice_date TEXT,
            subtotal REAL DEFAULT 0,
            discount REAL DEFAULT 0,
            tax REAL DEFAULT 0,
            total REAL DEFAULT 0,
            payment_method TEXT,
            notes TEXT,
            created_at TEXT,
            FOREIGN KEY(customer_id) REFERENCES customers(id),
            FOREIGN KEY(supplier_id) REFERENCES suppliers(id)
        );

        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity REAL NOT NULL,
            unit_price REAL NOT NULL,
            discount REAL DEFAULT 0,
            tax REAL DEFAULT 0,
            total REAL DEFAULT 0,
            FOREIGN KEY(invoice_id) REFERENCES invoices(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS stock_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            invoice_id INTEGER,
            movement_type TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit_cost REAL DEFAULT 0,
            movement_date TEXT,
            notes TEXT,
            FOREIGN KEY(product_id) REFERENCES products(id),
            FOREIGN KEY(invoice_id) REFERENCES invoices(id)
        );

        CREATE TABLE IF NOT EXISTS journal_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_date TEXT,
            description TEXT,
            reference_type TEXT,
            reference_id INTEGER,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS journal_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            journal_entry_id INTEGER NOT NULL,
            account_code TEXT NOT NULL,
            account_name TEXT,
            debit REAL DEFAULT 0,
            credit REAL DEFAULT 0,
            FOREIGN KEY(journal_entry_id) REFERENCES journal_entries(id)
        );

        CREATE TABLE IF NOT EXISTS subscription_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_user_id INTEGER NOT NULL,
            plan_code TEXT NOT NULL,
            plan_name TEXT NOT NULL,
            amount REAL DEFAULT 0,
            receipt_file_id TEXT,
            receipt_file_unique_id TEXT,
            status TEXT DEFAULT 'pending',
            submitted_at TEXT,
            reviewed_at TEXT,
            reviewed_by INTEGER,
            rejection_reason TEXT,
            FOREIGN KEY(telegram_user_id) REFERENCES telegram_users(id)
        );

        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_user_id INTEGER NOT NULL,
            plan_code TEXT NOT NULL,
            plan_name TEXT NOT NULL,
            start_date TEXT,
            end_date TEXT,
            status TEXT DEFAULT 'inactive',
            payment_id INTEGER,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY(telegram_user_id) REFERENCES telegram_users(id),
            FOREIGN KEY(payment_id) REFERENCES subscription_payments(id)
        );

        CREATE INDEX IF NOT EXISTS idx_products_code
        ON products(code);

        CREATE INDEX IF NOT EXISTS idx_invoice_type
        ON invoices(invoice_type);

        CREATE INDEX IF NOT EXISTS idx_stock_product
        ON stock_movements(product_id);

        CREATE INDEX IF NOT EXISTS idx_subscription_user
        ON subscriptions(telegram_user_id);

        CREATE INDEX IF NOT EXISTS idx_payment_status
        ON subscription_payments(status);
        """
    )

    # Migration
    add_column_if_missing(
        conn, "customers", "active", "INTEGER DEFAULT 1"
    )
    add_column_if_missing(
        conn, "customers", "created_at", "TEXT"
    )

    add_column_if_missing(
        conn, "products", "active", "INTEGER DEFAULT 1"
    )
    add_column_if_missing(
        conn, "products", "stock", "REAL DEFAULT 0"
    )
    add_column_if_missing(
        conn, "products", "min_stock", "REAL DEFAULT 0"
    )
    add_column_if_missing(
        conn, "products", "created_at", "TEXT"
    )

    add_column_if_missing(
        conn, "suppliers", "active", "INTEGER DEFAULT 1"
    )
    add_column_if_missing(
        conn, "suppliers", "created_at", "TEXT"
    )

    # Seed data
    customer = conn.execute(
        "SELECT id FROM customers LIMIT 1"
    ).fetchone()

    if not customer:
        conn.execute(
            """
            INSERT INTO customers
            (name, phone, address, active, created_at)
            VALUES (?, ?, ?, 1, ?)
            """,
            ("مشتری نمونه", "09120000000", "", now()),
        )

    supplier = conn.execute(
        "SELECT id FROM suppliers LIMIT 1"
    ).fetchone()

    if not supplier:
        conn.execute(
            """
            INSERT INTO suppliers
            (name, phone, address, active, created_at)
            VALUES (?, ?, ?, 1, ?)
            """,
            ("تأمین‌کننده نمونه", "09121111111", "", now()),
        )

    product = conn.execute(
        "SELECT id FROM products LIMIT 1"
    ).fetchone()

    if not product:
        conn.execute(
            """
            INSERT INTO products
            (name, code, unit, purchase_cost, sale_price,
             stock, min_stock, active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (
                "کالای نمونه",
                "P001",
                "عدد",
                100000,
                150000,
                0,
                5,
                now(),
            ),
        )

    conn.commit()
    conn.close()


# -------------------------
# Telegram Users
# -------------------------

def upsert_telegram_user(
    telegram_id,
    username=None,
    first_name=None,
    last_name=None,
):
    with db_transaction() as conn:
        existing = conn.execute(
            "SELECT id FROM telegram_users WHERE telegram_id=?",
            (telegram_id,),
        ).fetchone()

        if existing:
            conn.execute(
                """
                UPDATE telegram_users
                SET username=?,
                    first_name=?,
                    last_name=?,
                    updated_at=?
                WHERE telegram_id=?
                """,
                (
                    username,
                    first_name,
                    last_name,
                    now(),
                    telegram_id,
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO telegram_users
                (telegram_id, username, first_name, last_name,
                 is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    telegram_id,
                    username,
                    first_name,
                    last_name,
                    now(),
                    now(),
                ),
            )

        return conn.execute(
            "SELECT * FROM telegram_users WHERE telegram_id=?",
            (telegram_id,),
        ).fetchone()


def get_telegram_user(telegram_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM telegram_users WHERE telegram_id=?",
        (telegram_id,),
    ).fetchone()
    conn.close()
    return row


# -------------------------
# Customers
# -------------------------

def list_customers(active_only=True):
    conn = get_connection()

    if active_only:
        rows = conn.execute(
            """
            SELECT * FROM customers
            WHERE active=1
            ORDER BY id DESC
            """
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT * FROM customers
            ORDER BY id DESC
            """
        ).fetchall()

    conn.close()
    return rows


def get_customer(customer_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM customers WHERE id=?",
        (customer_id,),
    ).fetchone()
    conn.close()
    return row


def create_customer(name, phone="", address=""):
    with db_transaction() as conn:
        cur = conn.execute(
            """
            INSERT INTO customers
            (name, phone, address, active, created_at)
            VALUES (?, ?, ?, 1, ?)
            """,
            (name, phone, address, now()),
        )
        return cur.lastrowid


def deactivate_customer(customer_id):
    with db_transaction() as conn:
        conn.execute(
            "UPDATE customers SET active=0 WHERE id=?",
            (customer_id,),
        )


# -------------------------
# Suppliers
# -------------------------

def list_suppliers(active_only=True):
    conn = get_connection()

    if active_only:
        rows = conn.execute(
            """
            SELECT * FROM suppliers
            WHERE active=1
            ORDER BY id DESC
            """
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT * FROM suppliers
            ORDER BY id DESC
            """
        ).fetchall()

    conn.close()
    return rows


def get_supplier(supplier_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM suppliers WHERE id=?",
        (supplier_id,),
    ).fetchone()
    conn.close()
    return row


def create_supplier(name, phone="", address=""):
    with db_transaction() as conn:
        cur = conn.execute(
            """
            INSERT INTO suppliers
            (name, phone, address, active, created_at)
            VALUES (?, ?, ?, 1, ?)
            """,
            (name, phone, address, now()),
        )
        return cur.lastrowid


def deactivate_supplier(supplier_id):
    with db_transaction() as conn:
        conn.execute(
            "UPDATE suppliers SET active=0 WHERE id=?",
            (supplier_id,),
        )


# -------------------------
# Products
# -------------------------

def list_products(active_only=True):
    conn = get_connection()

    if active_only:
        rows = conn.execute(
            """
            SELECT * FROM products
            WHERE active=1
            ORDER BY id DESC
            """
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT * FROM products
            ORDER BY id DESC
            """
        ).fetchall()

    conn.close()
    return rows


def get_product(product_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM products WHERE id=?",
        (product_id,),
    ).fetchone()
    conn.close()
    return row


def create_product(
    name,
    code="",
    unit="عدد",
    purchase_cost=0,
    sale_price=0,
    min_stock=0,
):
    with db_transaction() as conn:
        cur = conn.execute(
            """
            INSERT INTO products
            (name, code, unit, purchase_cost, sale_price,
             stock, min_stock, active, created_at)
            VALUES (?, ?, ?, ?, ?, 0, ?, 1, ?)
            """,
            (
                name,
                code,
                unit,
                purchase_cost,
                sale_price,
                min_stock,
                now(),
            ),
        )
        return cur.lastrowid


def deactivate_product(product_id):
    with db_transaction() as conn:
        conn.execute(
            "UPDATE products SET active=0 WHERE id=?",
            (product_id,),
        )


# -------------------------
# Invoices / Reports
# -------------------------

def get_invoice(invoice_id):
    conn = get_connection()

    invoice = conn.execute(
        """
        SELECT
            i.*,
            c.name AS customer_name,
            s.name AS supplier_name
        FROM invoices i
        LEFT JOIN customers c ON c.id=i.customer_id
        LEFT JOIN suppliers s ON s.id=i.supplier_id
        WHERE i.id=?
        """,
        (invoice_id,),
    ).fetchone()

    items = conn.execute(
        """
        SELECT
            ii.*,
            p.name AS product_name,
            p.code AS product_code,
            p.unit
        FROM invoice_items ii
        JOIN products p ON p.id=ii.product_id
        WHERE ii.invoice_id=?
        ORDER BY ii.id
        """,
        (invoice_id,),
    ).fetchall()

    conn.close()

    return {
        "invoice": invoice,
        "items": items,
    }


def list_invoices(invoice_type=None, limit=20):
    conn = get_connection()

    if invoice_type:
        rows = conn.execute(
            """
            SELECT
                i.*,
                c.name AS customer_name,
                s.name AS supplier_name
            FROM invoices i
            LEFT JOIN customers c ON c.id=i.customer_id
            LEFT JOIN suppliers s ON s.id=i.supplier_id
            WHERE i.invoice_type=?
            ORDER BY i.id DESC
            LIMIT ?
            """,
            (invoice_type, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT
                i.*,
                c.name AS customer_name,
                s.name AS supplier_name
            FROM invoices i
            LEFT JOIN customers c ON c.id=i.customer_id
            LEFT JOIN suppliers s ON s.id=i.supplier_id
            ORDER BY i.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    conn.close()
    return rows


def get_stock_report():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT *
        FROM products
        WHERE active=1
        ORDER BY name
        """
    ).fetchall()
    conn.close()
    return rows


def get_low_stock_products():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT *
        FROM products
        WHERE active=1
          AND stock <= min_stock
        ORDER BY stock ASC
        """
    ).fetchall()
    conn.close()
    return rows


def get_last_journal_for_invoice(invoice_id):
    conn = get_connection()

    entry = conn.execute(
        """
        SELECT *
        FROM journal_entries
        WHERE reference_id=?
        ORDER BY id DESC
        LIMIT 1
        """,
        (invoice_id,),
    ).fetchone()

    if not entry:
        conn.close()
        return None, []

    lines = conn.execute(
        """
        SELECT *
        FROM journal_lines
        WHERE journal_entry_id=?
        ORDER BY id
        """,
        (entry["id"],),
    ).fetchall()

    conn.close()

    return entry, lines


# -------------------------
# Subscription
# -------------------------

def create_subscription_payment(
    telegram_user_id,
    plan_code,
    plan_name,
    amount,
):
    with db_transaction() as conn:
        cur = conn.execute(
            """
            INSERT INTO subscription_payments
            (telegram_user_id, plan_code, plan_name,
             amount, status, submitted_at)
            VALUES (?, ?, ?, ?, 'pending', ?)
            """,
            (
                telegram_user_id,
                plan_code,
                plan_name,
                amount,
                now(),
            ),
        )
        return cur.lastrowid


def attach_receipt_to_payment(
    payment_id,
    receipt_file_id,
    receipt_file_unique_id=None,
):
    with db_transaction() as conn:
        conn.execute(
            """
            UPDATE subscription_payments
            SET receipt_file_id=?,
                receipt_file_unique_id=?,
                status='pending'
            WHERE id=?
            """,
            (
                receipt_file_id,
                receipt_file_unique_id,
                payment_id,
            ),
        )


def get_payment(payment_id):
    conn = get_connection()

    row = conn.execute(
        """
        SELECT
            p.*,
            u.telegram_id,
            u.username,
            u.first_name,
            u.last_name
        FROM subscription_payments p
        JOIN telegram_users u
          ON u.id=p.telegram_user_id
        WHERE p.id=?
        """,
        (payment_id,),
    ).fetchone()

    conn.close()
    return row


def get_pending_payments():
    conn = get_connection()

    rows = conn.execute(
        """
        SELECT
            p.*,
            u.telegram_id,
            u.username,
            u.first_name,
            u.last_name
        FROM subscription_payments p
        JOIN telegram_users u
          ON u.id=p.telegram_user_id
        WHERE p.status='pending'
        ORDER BY p.id DESC
        """
    ).fetchall()

    conn.close()
    return rows


def approve_subscription_payment(
    payment_id,
    reviewed_by,
    start_date=None,
    end_date=None,
):
    payment = get_payment(payment_id)

    if not payment:
        return None

    if payment["status"] == "approved":
        return get_active_subscription(payment["telegram_user_id"])

    if start_date is None:
        start_date = date.today()

    if end_date is None:
        end_date = start_date

    with db_transaction() as conn:
        existing = conn.execute(
            """
            SELECT *
            FROM subscriptions
            WHERE telegram_user_id=?
              AND status='active'
            ORDER BY end_date DESC
            LIMIT 1
            """,
            (payment["telegram_user_id"],),
        ).fetchone()

        actual_start = start_date
        actual_end = end_date

        if existing and existing["end_date"]:
            try:
                old_end = date.fromisoformat(existing["end_date"])

                if old_end >= start_date:
                    actual_start = old_end
                    duration = end_date - start_date
                    actual_end = old_end + duration
            except ValueError:
                pass

        conn.execute(
            """
            UPDATE subscription_payments
            SET status='approved',
                reviewed_at=?,
                reviewed_by=?
            WHERE id=?
            """,
            (
                now(),
                reviewed_by,
                payment_id,
            ),
        )

        conn.execute(
            """
            UPDATE subscriptions
            SET status='inactive',
                updated_at=?
            WHERE telegram_user_id=?
              AND status='active'
            """,
            (
                now(),
                payment["telegram_user_id"],
            ),
        )

        conn.execute(
            """
            INSERT INTO subscriptions
            (telegram_user_id, plan_code, plan_name,
             start_date, end_date, status,
             payment_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?)
            """,
            (
                payment["telegram_user_id"],
                payment["plan_code"],
                payment["plan_name"],
                actual_start.isoformat(),
                actual_end.isoformat(),
                payment_id,
                now(),
                now(),
            ),
        )

    return get_active_subscription(payment["telegram_user_id"])


def reject_subscription_payment(
    payment_id,
    reviewed_by,
    reason="",
):
    with db_transaction() as conn:
        conn.execute(
            """
            UPDATE subscription_payments
            SET status='rejected',
                reviewed_at=?,
                reviewed_by=?,
                rejection_reason=?
            WHERE id=?
            """,
            (
                now(),
                reviewed_by,
                reason,
                payment_id,
            ),
        )


def deactivate_expired_subscriptions():
    with db_transaction() as conn:
        conn.execute(
            """
            UPDATE subscriptions
            SET status='expired',
                updated_at=?
            WHERE status='active'
              AND end_date < ?
            """,
            (
                now(),
                date.today().isoformat(),
            ),
        )


def get_active_subscription(telegram_id):
    deactivate_expired_subscriptions()

    conn = get_connection()

    row = conn.execute(
        """
        SELECT s.*
        FROM subscriptions s
        JOIN telegram_users u
          ON u.id=s.telegram_user_id
        WHERE u.telegram_id=?
          AND s.status='active'
        ORDER BY s.end_date DESC
        LIMIT 1
        """,
        (telegram_id,),
    ).fetchone()

    conn.close()
    return row


def get_subscription_status(telegram_id):
    subscription = get_active_subscription(telegram_id)

    if not subscription:
        return {
            "active": False,
            "subscription": None,
            "remaining_days": 0,
        }

    try:
        end_date = date.fromisoformat(
            subscription["end_date"]
        )
        remaining = max(
            0,
            (end_date - date.today()).days + 1,
        )
    except Exception:
        remaining = 0

    return {
        "active": True,
        "subscription": subscription,
        "remaining_days": remaining,
    }
