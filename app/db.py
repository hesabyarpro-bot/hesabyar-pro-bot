import os
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = Path(
    os.getenv(
        "DB_PATH",
        BASE_DIR / "hesabyar_pro.db"
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                name TEXT NOT NULL,
                unit TEXT DEFAULT 'عدد',
                purchase_cost REAL DEFAULT 0,
                sale_price REAL DEFAULT 0,
                stock REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT UNIQUE,
                customer_id INTEGER,
                invoice_date TEXT NOT NULL,
                subtotal REAL DEFAULT 0,
                discount REAL DEFAULT 0,
                tax REAL DEFAULT 0,
                total REAL DEFAULT 0,
                payment_method TEXT,
                status TEXT DEFAULT 'confirmed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id)
                    REFERENCES customers(id)
            );

            CREATE TABLE IF NOT EXISTS invoice_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity REAL NOT NULL,
                unit_price REAL NOT NULL,
                discount REAL DEFAULT 0,
                tax REAL DEFAULT 0,
                line_total REAL DEFAULT 0,
                FOREIGN KEY (invoice_id)
                    REFERENCES invoices(id)
                    ON DELETE CASCADE,
                FOREIGN KEY (product_id)
                    REFERENCES products(id)
            );

            CREATE TABLE IF NOT EXISTS journal_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_number TEXT UNIQUE,
                entry_date TEXT NOT NULL,
                description TEXT,
                reference_type TEXT,
                reference_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS journal_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                journal_entry_id INTEGER NOT NULL,
                account_code TEXT NOT NULL,
                description TEXT,
                debit REAL DEFAULT 0,
                credit REAL DEFAULT 0,
                FOREIGN KEY (journal_entry_id)
                    REFERENCES journal_entries(id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS stock_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                movement_type TEXT NOT NULL,
                quantity REAL NOT NULL,
                unit_cost REAL DEFAULT 0,
                reference_type TEXT,
                reference_id INTEGER,
                movement_date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id)
                    REFERENCES products(id)
            );

            CREATE TABLE IF NOT EXISTS telegram_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                plan_code TEXT NOT NULL DEFAULT 'monthly',
                plan_name TEXT NOT NULL DEFAULT 'اشتراک ماهانه',
                start_date TEXT,
                end_date TEXT,
                status TEXT NOT NULL DEFAULT 'inactive',
                payment_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (telegram_user_id)
                    REFERENCES telegram_users(id)
            );

            CREATE TABLE IF NOT EXISTS subscription_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                plan_code TEXT NOT NULL DEFAULT 'monthly',
                plan_name TEXT NOT NULL DEFAULT 'اشتراک ماهانه',
                amount REAL NOT NULL DEFAULT 0,
                receipt_file_id TEXT,
                receipt_file_unique_id TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP,
                reviewed_by INTEGER,
                rejection_reason TEXT,
                FOREIGN KEY (telegram_user_id)
                    REFERENCES telegram_users(id)
            );

            CREATE INDEX IF NOT EXISTS idx_invoice_customer
                ON invoices(customer_id);

            CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice
                ON invoice_items(invoice_id);

            CREATE INDEX IF NOT EXISTS idx_stock_product
                ON stock_movements(product_id);

            CREATE INDEX IF NOT EXISTS idx_journal_lines_account
                ON journal_lines(account_code);

            CREATE INDEX IF NOT EXISTS idx_telegram_users_telegram_id
                ON telegram_users(telegram_id);

            CREATE INDEX IF NOT EXISTS idx_subscriptions_user
                ON subscriptions(telegram_user_id);

            CREATE INDEX IF NOT EXISTS idx_subscriptions_status
                ON subscriptions(status);

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
        return cursor.fetchone()
    finally:
        connection.close()


def fetch_all(query, params=()):
    connection = get_connection()

    try:
        cursor = connection.execute(query, params)
        return cursor.fetchall()
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
    last_name=None,
):
    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO telegram_users (
                telegram_id,
                username,
                first_name,
                last_name,
                is_active
            )
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(telegram_id)
            DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                telegram_id,
                username,
                first_name,
                last_name,
            ),
        )

        connection.commit()

        cursor = connection.execute(
            """
            SELECT *
            FROM telegram_users
            WHERE telegram_id = ?
            """,
            (telegram_id,),
        )

        return cursor.fetchone()

    finally:
        connection.close()


def get_telegram_user(telegram_id):
    return fetch_one(
        """
        SELECT *
        FROM telegram_users
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    )


def create_subscription_payment(
    telegram_id,
    amount,
    plan_code="monthly",
    plan_name="اشتراک ماهانه",
):
    user = get_telegram_user(telegram_id)

    if user is None:
        user = upsert_telegram_user(
            telegram_id=telegram_id
        )

    payment_id = execute(
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
            amount,
        ),
    )

    return get_payment(payment_id)


def attach_receipt_to_payment(
    payment_id,
    file_id,
   
