import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime


DB_PATH = os.getenv("DB_PATH", "hesabyar.db")


# ============================================================
# Connection
# ============================================================

def get_connection():
    conn = sqlite3.connect(
        DB_PATH,
        timeout=30,
        check_same_thread=False
    )

    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")

    return conn


# Compatibility alias
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


# ============================================================
# Helpers
# ============================================================

def now():
    return datetime.now().isoformat(timespec="seconds")


def table_columns(conn, table_name):
    rows = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return {
        row["name"]
        for row in rows
    }


def add_column_if_missing(
    conn,
    table_name,
    column_name,
    column_definition
):
    columns = table_columns(conn, table_name)

    if column_name not in columns:
        conn.execute(
            f"""
            ALTER TABLE {table_name}
            ADD COLUMN {column_name} {column_definition}
            """
        )


# ============================================================
# Database Initialization
# ============================================================

def init_db():

    conn = get_connection()

    try:

        # ----------------------------------------------------
        # Users
        # ----------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS telegram_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL UNIQUE,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # ----------------------------------------------------
        # Customers
        # ----------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                national_id TEXT,
                address TEXT,
                notes TEXT,
                active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL
            )
        """)

        # ----------------------------------------------------
        # Products
        # ----------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                sku TEXT UNIQUE,
                unit TEXT DEFAULT 'عدد',
                sale_price INTEGER DEFAULT 0,
                purchase_cost INTEGER DEFAULT 0,
                stock REAL DEFAULT 0,
                min_stock REAL DEFAULT 0,
                active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL
            )
        """)

        # ----------------------------------------------------
        # Suppliers
        # ----------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                national_id TEXT,
                address TEXT,
                notes TEXT,
                active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL
            )
        """)

        # ----------------------------------------------------
        # Invoices
        # ----------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_type TEXT NOT NULL,
                invoice_number TEXT,
                customer_id INTEGER,
                supplier_id INTEGER,
                invoice_date TEXT NOT NULL,
                subtotal INTEGER DEFAULT 0,
                discount INTEGER DEFAULT 0,
                tax INTEGER DEFAULT 0,
                total INTEGER DEFAULT 0,
                payment_method TEXT,
                status TEXT DEFAULT 'confirmed',
                notes TEXT,
                created_at TEXT NOT NULL,

                FOREIGN KEY(customer_id)
                    REFERENCES customers(id),

                FOREIGN KEY(supplier_id)
                    REFERENCES suppliers(id)
            )
        """)

        # ----------------------------------------------------
        # Invoice Items
        # ----------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS invoice_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity REAL NOT NULL,
                unit_price INTEGER NOT NULL,
                discount INTEGER DEFAULT 0,
                tax INTEGER DEFAULT 0,
                line_total INTEGER NOT NULL,

                FOREIGN KEY(invoice_id)
                    REFERENCES invoices(id)
                    ON DELETE CASCADE,

                FOREIGN KEY(product_id)
                    REFERENCES products(id)
            )
        """)

        # ----------------------------------------------------
        # Stock Movements
        # ----------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                movement_type TEXT NOT NULL,
                quantity REAL NOT NULL,
                unit_cost INTEGER DEFAULT 0,
                reference_type TEXT,
                reference_id INTEGER,
                movement_date TEXT NOT NULL,
                notes TEXT,

                FOREIGN KEY(product_id)
                    REFERENCES products(id)
            )
        """)

        # ----------------------------------------------------
        # Accounting Journal Entries
        # ----------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS journal_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_number TEXT,
                entry_date TEXT NOT NULL,
                description TEXT,
                reference_type TEXT,
                reference_id INTEGER,
                status TEXT DEFAULT 'posted',
                created_at TEXT NOT NULL
            )
        """)

        # ----------------------------------------------------
        # Accounting Journal Lines
        # ----------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS journal_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                journal_entry_id INTEGER NOT NULL,
                account_code TEXT NOT NULL,
                account_name TEXT,
                debit INTEGER DEFAULT 0,
                credit INTEGER DEFAULT 0,

                FOREIGN KEY(journal_entry_id)
                    REFERENCES journal_entries(id)
                    ON DELETE CASCADE
            )
        """)

        # ----------------------------------------------------
        # Subscription Payments
        # ----------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS subscription_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                plan_code TEXT,
                plan_name TEXT,
                amount INTEGER DEFAULT 0,
                receipt_file_id TEXT,
                receipt_file_unique_id TEXT,
                status TEXT DEFAULT 'pending',
                submitted_at TEXT,
                reviewed_at TEXT,
                reviewed_by INTEGER,
                rejection_reason TEXT,

                FOREIGN KEY(telegram_user_id)
                    REFERENCES telegram_users(id)
            )
        """)

        # ----------------------------------------------------
        # Subscriptions
        # ----------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                plan_code TEXT,
                plan_name TEXT,
                start_date TEXT,
                end_date TEXT,
                status TEXT DEFAULT 'inactive',
                payment_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,

                FOREIGN KEY(telegram_user_id)
                    REFERENCES telegram_users(id)
            )
        """)

        # ----------------------------------------------------
        # Indexes
        # ----------------------------------------------------

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_customers_active
            ON customers(active)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_products_active
            ON products(active)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_invoices_type
            ON invoices(invoice_type)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice
            ON invoice_items(invoice_id)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_stock_product
            ON stock_movements(product_id)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_journal_reference
            ON journal_entries(reference_type, reference_id)
        """)

        # ----------------------------------------------------
        # Migrations for older database
        # ----------------------------------------------------

        add_column_if_missing(
            conn,
            "customers",
            "active",
            "INTEGER DEFAULT 1"
        )

        add_column_if_missing(
            conn,
            "products",
            "active",
            "INTEGER DEFAULT 1"
        )

        add_column_if_missing(
            conn,
            "products",
            "stock",
            "REAL DEFAULT 0"
        )

        add_column_if_missing(
            conn,
            "products",
            "min_stock",
            "REAL DEFAULT 0"
        )

        add_column_if_missing(
            conn,
            "products",
            "created_at",
            "TEXT"
        )

        add_column_if_missing(
            conn,
            "suppliers",
            "active",
            "INTEGER DEFAULT 1"
        )

        conn.commit()

        # ----------------------------------------------------
        # Seed sample customer
        # ----------------------------------------------------

        customer_count = conn.execute(
            "SELECT COUNT(*) AS c FROM customers"
        ).fetchone()["c"]

        if customer_count == 0:
            conn.execute("""
                INSERT INTO customers
                (
                    name,
                    phone,
                    active,
                    created_at
                )
                VALUES (?, ?, 1, ?)
            """, (
                "مشتری نمونه",
                "",
                now()
            ))

        # ----------------------------------------------------
        # Seed sample supplier
        # ----------------------------------------------------

        supplier_count = conn.execute(
            "SELECT COUNT(*) AS c FROM suppliers"
        ).fetchone()["c"]

        if supplier_count == 0:
            conn.execute("""
                INSERT INTO suppliers
                (
                    name,
                    phone,
                    active,
                    created_at
                )
                VALUES (?, ?, 1, ?)
            """, (
                "تأمین‌کننده نمونه",
                "",
                now()
            ))

        # ----------------------------------------------------
        # Seed sample product
        # ----------------------------------------------------

        product_count = conn.execute(
            "SELECT COUNT(*) AS c FROM products"
        ).fetchone()["c"]

        if product_count == 0:
            conn.execute("""
                INSERT INTO products
                (
                    name,
                    sku,
                    unit,
                    sale_price,
                    purchase_cost,
                    stock,
                    min_stock,
                    active,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
            """, (
                "کالای نمونه",
                "P001",
                "عدد",
                100000,
                70000,
                0,
                5,
                now()
            ))

        conn.commit()

    finally:
        conn.close()


# ============================================================
# Telegram Users
# ============================================================

def upsert_telegram_user(
    telegram_id,
    username=None,
    first_name=None,
    last_name=None
):

    conn = get_connection()

    try:

        current = conn.execute("""
            SELECT id
            FROM telegram_users
            WHERE telegram_id = ?
        """, (telegram_id,)).fetchone()

        if current:

            conn.execute("""
                UPDATE telegram_users
                SET username = ?,
                    first_name = ?,
                    last_name = ?,
                    updated_at = ?
                WHERE telegram_id = ?
            """, (
                username,
                first_name,
                last_name,
                now(),
                telegram_id
            ))

            user_id = current["id"]

        else:

            cur = conn.execute("""
                INSERT INTO telegram_users
                (
                    telegram_id,
                    username,
                    first_name,
                    last_name,
                    is_active,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, 1, ?, ?)
            """, (
                telegram_id,
                username,
                first_name,
                last_name,
                now(),
                now()
            ))

            user_id = cur.lastrowid

        conn.commit()

        return user_id

    finally:
        conn.close()


def get_telegram_user(telegram_id):

    conn = get_connection()

    try:
        return conn.execute("""
            SELECT *
            FROM telegram_users
            WHERE telegram_id = ?
        """, (telegram_id,)).fetchone()

    finally:
        conn.close()


# ============================================================
# Subscription Payments
# ============================================================

def create_subscription_payment(
    telegram_user_id,
    plan_code,
    plan_name,
    amount
):

    conn = get_connection()

    try:

        cur = conn.execute("""
            INSERT INTO subscription_payments
            (
                telegram_user_id,
                plan_code,
                plan_name,
                amount,
                status,
                submitted_at
            )
            VALUES (?, ?, ?, ?, 'pending', ?)
        """, (
            telegram_user_id,
            plan_code,
            plan_name,
            amount,
            now()
        ))

        conn.commit()

        return cur.lastrowid

    finally:
        conn.close()


def attach_receipt_to_payment(
    payment_id,
    receipt_file_id,
    receipt_file_unique_id=None
):

    conn = get_connection()

    try:

        conn.execute("""
            UPDATE subscription_payments
            SET receipt_file_id = ?,
                receipt_file_unique_id = ?,
                submitted_at = ?,
                status = 'pending'
            WHERE id = ?
        """, (
            receipt_file_id,
            receipt_file_unique_id,
            now(),
            payment_id
        ))

        conn.commit()

    finally:
        conn.close()


def get_payment(payment_id):

    conn = get_connection()

    try:

        return conn.execute("""
            SELECT
                sp.*,
                tu.telegram_id,
                tu.username,
                tu.first_name,
                tu.last_name
            FROM subscription_payments sp
            JOIN telegram_users tu
                ON tu.id = sp.telegram_user_id
            WHERE sp.id = ?
        """, (payment_id,)).fetchone()

    finally:
        conn.close()


def get_pending_payments():

    conn = get_connection()

    try:

        return conn.execute("""
            SELECT
                sp.*,
                tu.telegram_id,
                tu.username,
                tu.first_name,
                tu.last_name
            FROM subscription_payments sp
            JOIN telegram_users tu
                ON tu.id = sp.telegram_user_id
            WHERE sp.status = 'pending'
              AND sp.receipt_file_id IS NOT NULL
            ORDER BY sp.id ASC
        """).fetchall()

    finally:
        conn.close()


def approve_subscription_payment(
    payment_id,
    start_date,
    end_date,
    reviewed_by
):

    conn = get_connection()

    try:

        payment = conn.execute("""
            SELECT *
            FROM subscription_payments
            WHERE id = ?
        """, (payment_id,)).fetchone()

        if not payment:
            raise ValueError("Payment not found.")

        if payment["status"] != "pending":
            raise ValueError("Payment is not pending.")

        conn.execute("""
            UPDATE subscription_payments
            SET status = 'approved',
                reviewed_at = ?,
                reviewed_by = ?
            WHERE id = ?
        """, (
            now(),
            reviewed_by,
            payment_id
        ))

        existing = conn.execute("""
            SELECT *
            FROM subscriptions
            WHERE telegram_user_id = ?
            ORDER BY id DESC
            LIMIT 1
        """, (
            payment["telegram_user_id"],
        )).fetchone()

        # اگر اشتراک قبلی هنوز فعال و معتبر است،
        # از انتهای آن تمدید می‌کنیم.
        actual_start = start_date
        actual_end = end_date

        if existing:
            if (
                existing["status"] == "active"
                and existing["end_date"]
                and existing["end_date"] >= start_date
            ):
                actual_start = existing["end_date"]

                from datetime import date, timedelta

                old_end = date.fromisoformat(
                    existing["end_date"]
                )

                requested_end = date.fromisoformat(
                    end_date
                )

                duration = requested_end - date.fromisoformat(
                    start_date
                )

                actual_end = (
                    old_end + duration
                ).isoformat()

        if existing:

            conn.execute("""
                UPDATE subscriptions
                SET plan_code = ?,
                    plan_name = ?,
                    start_date = ?,
                    end_date = ?,
                    status = 'active',
                    payment_id = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                payment["plan_code"],
                payment["plan_name"],
                actual_start,
                actual_end,
                payment_id,
                now(),
                existing["id"]
            ))

        else:

            conn.execute("""
                INSERT INTO subscriptions
                (
                    telegram_user_id,
                    plan_code,
                    plan_name,
                    start_date,
                    end_date,
                    status,
                    payment_id,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?)
            """, (
                payment["telegram_user_id"],
                payment["plan_code"],
                payment["plan_name"],
                actual_start,
                actual_end,
                payment_id,
                now(),
                now()
            ))

        conn.commit()

        return actual_start, actual_end

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def reject_subscription_payment(
    payment_id,
    reviewed_by,
    reason=""
):

    conn = get_connection()

    try:

        conn.execute("""
            UPDATE subscription_payments
            SET status = 'rejected',
                reviewed_at = ?,
                reviewed_by = ?,
                rejection_reason = ?
            WHERE id = ?
              AND status = 'pending'
        """, (
            now(),
            reviewed_by,
            reason,
            payment_id
        ))

        conn.commit()

    finally:
        conn.close()


def deactivate_expired_subscriptions():

    from datetime import date

    today = date.today().isoformat()

    conn = get_connection()

    try:

        conn.execute("""
            UPDATE subscriptions
            SET status = 'expired',
                updated_at = ?
            WHERE status = 'active'
              AND end_date < ?
        """, (
            now(),
            today
        ))

        conn.commit()

    finally:
        conn.close()


def get_active_subscription(telegram_id):

    deactivate_expired_subscriptions()

    conn = get_connection()

    try:

        return conn.execute("""
            SELECT
                s.*
            FROM subscriptions s
            JOIN telegram_users tu
                ON tu.id = s.telegram_user_id
            WHERE tu.telegram_id = ?
              AND s.status = 'active'
            ORDER BY s.end_date DESC
            LIMIT 1
        """, (
            telegram_id,
        )).fetchone()

    finally:
        conn.close()


def get_subscription_status(telegram_id):

    subscription = get_active_subscription(
        telegram_id
    )

    if not subscription:
        return None

    from datetime import date

    try:
        end_date = date.fromisoformat(
            subscription["end_date"]
        )

        remaining = (
            end_date - date.today()
        ).days

    except Exception:
        remaining = 0

    return {
        "plan_code": subscription["plan_code"],
        "plan_name": subscription["plan_name"],
        "start_date": subscription["start_date"],
        "end_date": subscription["end_date"],
        "remaining_days": max(remaining, 0),
        "status": subscription["status"]
    }
