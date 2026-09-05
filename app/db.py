from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from pathlib import Path
SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    opening_balance INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT UNIQUE,
    name TEXT NOT NULL,
    sale_price INTEGER NOT NULL DEFAULT 0,
    purchase_cost INTEGER NOT NULL DEFAULT 0,
    stock_qty REAL NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_no TEXT NOT NULL UNIQUE,
    customer_id INTEGER,
    invoice_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'POSTED',
    subtotal INTEGER NOT NULL,
    discount INTEGER NOT NULL DEFAULT 0,
    tax INTEGER NOT NULL DEFAULT 0,
    total INTEGER NOT NULL,
    payment_method TEXT NOT NULL,
    created_by_telegram_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(customer_id) REFERENCES customers(id)
);
CREATE TABLE IF NOT EXISTS invoice_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    qty REAL NOT NULL,
    unit_price INTEGER NOT NULL,
    discount INTEGER NOT NULL DEFAULT 0,
    tax INTEGER NOT NULL DEFAULT 0,
    line_total INTEGER NOT NULL,
    cost_total INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(invoice_id) REFERENCES invoices(id),
    FOREIGN KEY(product_id) REFERENCES products(id)
);
CREATE TABLE IF NOT EXISTS journal_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_no TEXT NOT NULL UNIQUE,
    entry_date TEXT NOT NULL,
    description TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS journal_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER NOT NULL,
    account_code TEXT NOT NULL,
    debit INTEGER NOT NULL DEFAULT 0,
    credit INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(entry_id) REFERENCES journal_entries(id)
);
CREATE TABLE IF NOT EXISTS stock_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    movement_type TEXT NOT NULL,
    qty REAL NOT NULL,
    source_type TEXT NOT NULL,
    source_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(product_id) REFERENCES products(id)
);
CREATE INDEX IF NOT EXISTS idx_customers_active
ON customers(active);
CREATE INDEX IF NOT EXISTS idx_products_active
ON products(active);
CREATE INDEX IF NOT EXISTS idx_invoices_customer
ON invoices(customer_id);
CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice
ON invoice_items(invoice_id);
CREATE INDEX IF NOT EXISTS idx_stock_movements_product
ON stock_movements(product_id);
"""
@contextmanager
def get_conn(db_path: str):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        db_path,
        timeout=10,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
def init_db(db_path: str):
    with get_conn(db_path) as conn:
        conn.executescript(SCHEMA)
        # -----------------------------
        # Migration: customers.active
        # -----------------------------
        customer_columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(customers)"
            ).fetchall()
        }
        if "active" not in customer_columns:
            conn.execute(
                """
                ALTER TABLE customers
                ADD COLUMN active INTEGER NOT NULL DEFAULT 1
                """
            )
        # -----------------------------
        # Migration: products.active
        # -----------------------------
        product_columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(products)"
            ).fetchall()
        }
        if "active" not in product_columns:
            conn.execute(
                """
                ALTER TABLE products
                ADD COLUMN active INTEGER NOT NULL DEFAULT 1
                """
            )
        # -----------------------------
        # Seed customers
        # فقط اگر دیتابیس کاملاً خالی باشد
        # -----------------------------
        customer_count = conn.execute(
            "SELECT COUNT(*) FROM customers"
        ).fetchone()[0]
        if customer_count == 0:
            conn.executemany(
                """
                INSERT INTO customers(
                    name,
                    phone,
                    opening_balance,
                    active
                )
                VALUES (?, ?, ?, 1)
                """,
                [
                    ("مشتری نقدی", None, 0),
                    ("علی احمدی", "09120000000", 0),
                    ("شرکت نمونه", "02100000000", 0),
                ],
            )
        # -----------------------------
        # Seed products
        # فقط اگر دیتابیس کاملاً خالی باشد
        # -----------------------------
        product_count = conn.execute(
            "SELECT COUNT(*) FROM products"
        ).fetchone()[0]
        if product_count == 0:
            conn.executemany(
                """
                INSERT INTO products(
                    sku,
                    name,
                    sale_price,
                    purchase_cost,
                    stock_qty,
                    active
                )
                VALUES (?, ?, ?, ?, ?, 1)
                """,
                [
                    (
                        "P-001",
                        "لپ‌تاپ نمونه",
                        250000000,
                        190000000,
                        10,
                    ),
                    (
                        "P-002",
                        "موس بی‌سیم",
                        25000000,
                        15000000,
                        30,
                    ),
                    (
                        "P-003",
                        "کیبورد",
                        45000000,
                        28000000,
                        20,
                    ),
                ],
            )
