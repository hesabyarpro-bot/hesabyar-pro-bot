import os
import sqlite3
from pathlib import Path
from datetime import datetime, date, timedelta


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = Path(
    os.getenv(
        "DB_PATH",
        str(BASE_DIR / "hesabyar_pro.db")
    )
)


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    connection = get_connection()

    try:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                national_id TEXT,
                address TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                code TEXT,
                unit TEXT DEFAULT 'عدد',
                purchase_cost REAL DEFAULT 0,
                sale_price REAL DEFAULT 0,
                stock REAL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT,
                customer_id INTEGER,
                invoice_date TEXT DEFAULT CURRENT_TIMESTAMP,
                subtotal REAL DEFAULT 0,
                discount REAL DEFAULT 0,
                tax REAL DEFAULT 0,
                total REAL DEFAULT 0,
                payment_method TEXT,
                status TEXT DEFAULT 'confirmed',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            );

            CREATE TABLE IF NOT EXISTS invoice_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity REAL DEFAULT 0,
                unit_price REAL DEFAULT 0,
                discount REAL DEFAULT 0,
                tax REAL DEFAULT 0,
                total REAL DEFAULT 0,
                FOREIGN KEY (invoice_id) REFERENCES invoices(id)
                    ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id)
            );

            CREATE TABLE IF NOT EXISTS journal_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_number TEXT,
                entry_date TEXT DEFAULT CURRENT_TIMESTAMP,
                description TEXT,
                reference_type TEXT,
                reference_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS journal_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                journal_entry_id INTEGER NOT NULL,
                account_code TEXT NOT NULL,
                description TEXT,
                debit REAL DEFAULT 0,
                credit REAL DEFAULT 0,
                FOREIGN KEY (journal_entry_id) REFERENCES journal_entries(id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS stock_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                movement_type TEXT NOT NULL,
                quantity REAL DEFAULT 0,
                reference_type TEXT,
                reference_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id)
            );

            CREATE INDEX IF NOT EXISTS idx_customers_name
                ON customers(name);

            CREATE INDEX IF NOT EXISTS idx_products_name
                ON products(name);

            CREATE INDEX IF NOT EXISTS idx_invoices_customer
                ON invoices(customer_id);

            CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice
                ON invoice_items(invoice_id);

            CREATE INDEX IF NOT EXISTS idx_journal_lines_entry
                ON journal_lines(journal_entry_id);

            CREATE INDEX IF NOT EXISTS idx_stock_movements_product
                ON stock_movements(product_id);


            CREATE TABLE IF NOT EXISTS telegram_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL UNIQUE,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );


            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                plan_code TEXT NOT NULL,
                plan_name TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                status TEXT DEFAULT 'inactive',
                payment_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (telegram_user_id)
                    REFERENCES telegram_users(id)
                    ON DELETE CASCADE
            );


            CREATE TABLE IF NOT EXISTS subscription_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                plan_code TEXT NOT NULL,
                plan_name TEXT NOT NULL,
                amount REAL NOT NULL,
                receipt_file_id TEXT,
                receipt_file_unique_id TEXT,
                status TEXT DEFAULT 'pending',
                submitted_at TEXT DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TEXT,
                reviewed_by INTEGER,
                rejection_reason TEXT,
                FOREIGN KEY (telegram_user_id)
                    REFERENCES telegram_users(id)
                    ON DELETE CASCADE
            );


            CREATE INDEX IF NOT EXISTS idx_telegram_users_telegram_id
                ON telegram_users(telegram_id);

            CREATE INDEX IF NOT EXISTS idx_subscriptions_user
                ON subscriptions(telegram_user_id);

            CREATE INDEX IF NOT EXISTS idx_subscriptions_end_date
                ON subscriptions(end_date);

            CREATE INDEX IF NOT EXISTS idx_subscription_payments_user
                ON subscription_payments(telegram_user_id);

            CREATE INDEX IF NOT EXISTS idx_subscription_payments_status
                ON subscription_payments(status);
            """
        )

        connection.commit()

    finally:
        connection.close()


def fetch_one(query, params=()):
    connection = get_connection()

    try:
        cursor = connection.execute(query, params)
        row = cursor.fetchone()
        return row

    finally:
        connection.close()


def fetch_all(query, params=()):
    connection = get_connection()

    try:
        cursor = connection.execute(query, params)
        rows = cursor.fetchall()
        return rows

    finally:
        connection.close()


def execute(query, params=()):
    connection = get_connection()

    try:
        cursor = connection.execute(query, params)
        connection.commit()
        return cursor.lastrowid

    finally:
        connection.close()


def upsert_telegram_user(
    telegram_id,
    username=None,
    first_name=None,
    last_name=None
):
    connection = get_connection()

    try:
        now = datetime.utcnow().isoformat()

        connection.execute(
            """
            INSERT INTO telegram_users (
                telegram_id,
                username,
                first_name,
                last_name,
                is_active,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, 1, ?, ?)
            ON CONFLICT(telegram_id)
            DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                updated_at = excluded.updated_at
            """,
            (
                telegram_id,
                username,
                first_name,
                last_name,
                now,
                now
            )
        )

        connection.commit()

        row = connection.execute(
            """
            SELECT *
            FROM telegram_users
            WHERE telegram_id = ?
            """,
            (telegram_id,)
        ).fetchone()

        return row

    finally:
        connection.close()


def get_telegram_user(telegram_id):
    return fetch_one(
        """
        SELECT *
        FROM telegram_users
        WHERE telegram_id = ?
        """,
        (telegram_id,)
    )


def create_subscription_payment(
    telegram_id,
    plan_code,
    plan_name,
    amount
):
    user = get_telegram_user(telegram_id)

    if user is None:
        user = upsert_telegram_user(
            telegram_id=telegram_id
        )

    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            INSERT INTO subscription_payments (
                telegram_user_id,
                plan_code,
                plan_name,
                amount,
                status
            )
            VALUES (?, ?, ?, ?, 'pending')
            """,
            (
                user["id"],
                plan_code,
                plan_name,
                amount
            )
        )

        connection.commit()

        return cursor.lastrowid

    finally:
        connection.close()


def attach_receipt_to_payment(
    payment_id,
    receipt_file_id,
    receipt_file_unique_id=None
):
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            UPDATE subscription_payments
            SET
                receipt_file_id = ?,
                receipt_file_unique_id = ?
            WHERE id = ?
            AND status = 'pending'
            """,
            (
                receipt_file_id,
                receipt_file_unique_id,
                payment_id
            )
        )

        connection.commit()

        return cursor.rowcount > 0

    finally:
        connection.close()


def get_payment(payment_id):
    return fetch_one(
        """
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
        """,
        (payment_id,)
    )


def get_pending_payments():
    return fetch_all(
        """
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
        ORDER BY sp.id DESC
        """
    )


def approve_subscription_payment(
    payment_id,
    start_date,
    end_date,
    reviewed_by
):
    connection = get_connection()

    try:
        payment = connection.execute(
            """
            SELECT *
            FROM subscription_payments
            WHERE id = ?
            AND status = 'pending'
            """,
            (payment_id,)
        ).fetchone()

        if payment is None:
            return False

        connection.execute(
            """
            UPDATE subscription_payments
            SET
                status = 'approved',
                reviewed_at = CURRENT_TIMESTAMP,
                reviewed_by = ?
            WHERE id = ?
            """,
            (
                reviewed_by,
                payment_id
            )
        )

        existing_subscription = connection.execute(
            """
            SELECT *
            FROM subscriptions
            WHERE telegram_user_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (
                payment["telegram_user_id"],
            )
        ).fetchone()

        if existing_subscription is None:

            connection.execute(
                """
                INSERT INTO subscriptions (
                    telegram_user_id,
                    plan_code,
                    plan_name,
                    start_date,
                    end_date,
                    status,
                    payment_id
                )
                VALUES (?, ?, ?, ?, ?, 'active', ?)
                """,
                (
                    payment["telegram_user_id"],
                    payment["plan_code"],
                    payment["plan_name"],
                    start_date,
                    end_date,
                    payment_id
                )
            )

        else:

            connection.execute(
                """
                UPDATE subscriptions
                SET
                    plan_code = ?,
                    plan_name = ?,
                    start_date = ?,
                    end_date = ?,
                    status = 'active',
                    payment_id = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    payment["plan_code"],
                    payment["plan_name"],
                    start_date,
                    end_date,
                    payment_id,
                    existing_subscription["id"]
                )
            )

        connection.commit()

        return True

    finally:
        connection.close()


def reject_subscription_payment(
    payment_id,
    reviewed_by,
    rejection_reason=None
):
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            UPDATE subscription_payments
            SET
                status = 'rejected',
                reviewed_at = CURRENT_TIMESTAMP,
                reviewed_by = ?,
                rejection_reason = ?
            WHERE id = ?
            AND status = 'pending'
            """,
            (
                reviewed_by,
                rejection_reason,
                payment_id
            )
        )

        connection.commit()

        return cursor.rowcount > 0

    finally:
        connection.close()


def get_active_subscription(telegram_id):
    return fetch_one(
        """
        SELECT
            s.*,
            tu.telegram_id
        FROM subscriptions s
        JOIN telegram_users tu
            ON tu.id = s.telegram_user_id
        WHERE tu.telegram_id = ?
        AND s.status = 'active'
        AND date(s.end_date) >= date('now')
        ORDER BY s.end_date DESC
        LIMIT 1
        """,
        (telegram_id,)
    )


def get_subscription_status(telegram_id):
    subscription = get_active_subscription(telegram_id)

    if subscription is None:
        return None

    try:
        end_date = date.fromisoformat(
            subscription["end_date"]
        )

        today = date.today()

        remaining_days = (
            end_date - today
        ).days

    except Exception:
        remaining_days = None

    return {
        "id": subscription["id"],
        "plan_code": subscription["plan_code"],
        "plan_name": subscription["plan_name"],
        "start_date": subscription["start_date"],
        "end_date": subscription["end_date"],
        "status": subscription["status"],
        "remaining_days": remaining_days
    }


def deactivate_expired_subscriptions():
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            UPDATE subscriptions
            SET
                status = 'expired',
                updated_at = CURRENT_TIMESTAMP
            WHERE status = 'active'
            AND date(end_date) < date('now')
            """
        )

        connection.commit()

        return cursor.rowcount

    finally:
        connection.close()
