import os
import sqlite3

from datetime import datetime, date, timedelta
from contextlib import contextmanager


DB_PATH = os.getenv(
    "DB_PATH",
    "hesabyar.db",
)


SCHEMA = """
PRAGMA foreign_keys = ON;


CREATE TABLE IF NOT EXISTS telegram_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);


CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    national_id TEXT,
    address TEXT,
    created_at TEXT NOT NULL
);


CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    national_id TEXT,
    address TEXT,
    created_at TEXT NOT NULL
);


CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    unit TEXT DEFAULT 'عدد',
    sale_price INTEGER NOT NULL DEFAULT 0,
    purchase_cost INTEGER NOT NULL DEFAULT 0,
    stock REAL NOT NULL DEFAULT 0,
    min_stock REAL NOT NULL DEFAULT 0,
    active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
);


CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_no INTEGER UNIQUE NOT NULL,
    invoice_type TEXT NOT NULL,
    customer_id INTEGER,
    supplier_id INTEGER,
    subtotal INTEGER NOT NULL DEFAULT 0,
    discount INTEGER NOT NULL DEFAULT 0,
    tax INTEGER NOT NULL DEFAULT 0,
    total INTEGER NOT NULL DEFAULT 0,
    payment_method TEXT,
    status TEXT DEFAULT 'confirmed',
    created_at TEXT NOT NULL,

    FOREIGN KEY(customer_id)
        REFERENCES customers(id),

    FOREIGN KEY(supplier_id)
        REFERENCES suppliers(id)
);


CREATE TABLE IF NOT EXISTS invoice_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    qty REAL NOT NULL,
    unit_price INTEGER NOT NULL,
    discount INTEGER DEFAULT 0,
    tax INTEGER DEFAULT 0,
    line_total INTEGER NOT NULL,
    cost_total INTEGER DEFAULT 0,

    FOREIGN KEY(invoice_id)
        REFERENCES invoices(id)
        ON DELETE CASCADE,

    FOREIGN KEY(product_id)
        REFERENCES products(id)
);


CREATE TABLE IF NOT EXISTS stock_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    movement_type TEXT NOT NULL,
    qty REAL NOT NULL,
    unit_cost INTEGER DEFAULT 0,
    ref_type TEXT,
    ref_id INTEGER,
    created_at TEXT NOT NULL,

    FOREIGN KEY(product_id)
        REFERENCES products(id)
);


CREATE TABLE IF NOT EXISTS journal_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ref_type TEXT,
    ref_id INTEGER,
    description TEXT,
    created_at TEXT NOT NULL
);


CREATE TABLE IF NOT EXISTS journal_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    journal_id INTEGER NOT NULL,
    account_code TEXT NOT NULL,
    debit INTEGER DEFAULT 0,
    credit INTEGER DEFAULT 0,

    FOREIGN KEY(journal_id)
        REFERENCES journal_entries(id)
        ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    amount INTEGER NOT NULL,
    payment_method TEXT,
    note TEXT,
    created_at TEXT NOT NULL
);


CREATE TABLE IF NOT EXISTS subscription_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_user_id INTEGER NOT NULL,
    plan_code TEXT NOT NULL,
    plan_name TEXT NOT NULL,
    amount INTEGER NOT NULL,
    receipt_file_id TEXT,
    receipt_file_unique_id TEXT,
    status TEXT DEFAULT 'pending',
    submitted_at TEXT NOT NULL,
    reviewed_at TEXT,
    reviewed_by INTEGER,
    rejection_reason TEXT,

    FOREIGN KEY(telegram_user_id)
        REFERENCES telegram_users(id)
);


CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_user_id INTEGER NOT NULL,
    plan_code TEXT NOT NULL,
    plan_name TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    payment_id INTEGER,
    created_at TEXT NOT NULL,

    FOREIGN KEY(telegram_user_id)
        REFERENCES telegram_users(id),

    FOREIGN KEY(payment_id)
        REFERENCES subscription_payments(id)
);


CREATE INDEX IF NOT EXISTS
idx_invoice_items_invoice
ON invoice_items(invoice_id);


CREATE INDEX IF NOT EXISTS
idx_stock_product
ON stock_movements(product_id);


CREATE INDEX IF NOT EXISTS
idx_payments_status
ON subscription_payments(status);
"""


def now():
    return datetime.now().isoformat(
        timespec="seconds"
    )


def get_connection():
    connection = sqlite3.connect(
        DB_PATH,
        timeout=30,
    )

    connection.row_factory = sqlite3.Row

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    return connection


@contextmanager
def db_transaction():
    connection = get_connection()

    try:
        yield connection
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def init_db():
    with get_connection() as connection:

        connection.executescript(
            SCHEMA
        )

        customer_count = connection.execute(
            "SELECT COUNT(*) FROM customers"
        ).fetchone()[0]

        if customer_count == 0:
            connection.execute(
                """
                INSERT INTO customers
                (
                    name,
                    phone,
                    created_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    "مشتری نمونه",
                    "09120000000",
                    now(),
                ),
            )

        supplier_count = connection.execute(
            "SELECT COUNT(*) FROM suppliers"
        ).fetchone()[0]

        if supplier_count == 0:
            connection.execute(
                """
                INSERT INTO suppliers
                (
                    name,
                    phone,
                    created_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    "تأمین‌کننده نمونه",
                    "09120000001",
                    now(),
                ),
            )

        product_count = connection.execute(
            "SELECT COUNT(*) FROM products"
        ).fetchone()[0]

        if product_count == 0:
            connection.execute(
                """
                INSERT INTO products
                (
                    code,
                    name,
                    unit,
                    sale_price,
                    purchase_cost,
                    stock,
                    min_stock,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "1001",
                    "کالای نمونه",
                    "عدد",
                    320000,
                    250000,
                    10,
                    2,
                    now(),
                ),
            )


# =========================================================
# TELEGRAM USERS
# =========================================================

def upsert_telegram_user(user):
    timestamp = now()

    with get_connection() as connection:

        connection.execute(
            """
            INSERT INTO telegram_users
            (
                telegram_id,
                username,
                first_name,
                last_name,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)

            ON CONFLICT(telegram_id)
            DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name,
                last_name=excluded.last_name,
                updated_at=excluded.updated_at
            """,
            (
                user.id,
                user.username,
                user.first_name,
                user.last_name,
                timestamp,
                timestamp,
            ),
        )

        return connection.execute(
            """
            SELECT *
            FROM telegram_users
            WHERE telegram_id=?
            """,
            (user.id,),
        ).fetchone()


def get_user(telegram_id):
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT *
            FROM telegram_users
            WHERE telegram_id=?
            """,
            (telegram_id,),
        ).fetchone()


# =========================================================
# CUSTOMERS
# =========================================================

def list_customers():
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT *
            FROM customers
            ORDER BY id DESC
            """
        ).fetchall()


def add_customer(
    name,
    phone="",
    national_id="",
    address="",
):
    with get_connection() as connection:

        cursor = connection.execute(
            """
            INSERT INTO customers
            (
                name,
                phone,
                national_id,
                address,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name,
                phone,
                national_id,
                address,
                now(),
            ),
        )

        return cursor.lastrowid


# =========================================================
# SUPPLIERS
# =========================================================

def list_suppliers():
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT *
            FROM suppliers
            ORDER BY id DESC
            """
        ).fetchall()


def add_supplier(
    name,
    phone="",
    national_id="",
    address="",
):
    with get_connection() as connection:

        cursor = connection.execute(
            """
            INSERT INTO suppliers
            (
                name,
                phone,
                national_id,
                address,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name,
                phone,
                national_id,
                address,
                now(),
            ),
        )

        return cursor.lastrowid


# =========================================================
# PRODUCTS
# =========================================================

def list_products(
    active_only=True,
):
    with get_connection() as connection:

        if active_only:
            query = """
                SELECT *
                FROM products
                WHERE active=1
                ORDER BY id DESC
            """
            return connection.execute(
                query
            ).fetchall()

        return connection.execute(
            """
            SELECT *
            FROM products
            ORDER BY id DESC
            """
        ).fetchall()


def get_product(product_id):
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT *
            FROM products
            WHERE id=?
            """,
            (product_id,),
        ).fetchone()


def add_product(
    code,
    name,
    unit,
    sale_price,
    purchase_cost,
    min_stock,
):
    with get_connection() as connection:

        cursor = connection.execute(
            """
            INSERT INTO products
            (
                code,
                name,
                unit,
                sale_price,
                purchase_cost,
                min_stock,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                code,
                name,
                unit,
                sale_price,
                purchase_cost,
                min_stock,
                now(),
            ),
        )

        return cursor.lastrowid


# =========================================================
# INVOICES
# =========================================================

def next_invoice_no(connection):
    return connection.execute(
        """
        SELECT
            COALESCE(MAX(invoice_no), 0) + 1
        FROM invoices
        """
    ).fetchone()[0]


def create_invoice(
    invoice_type,
    party_id,
    items,
    payment_method,
    discount=0,
    tax=0,
):
    from .accounting import (
        sale_entry_lines,
        purchase_entry_lines,
    )

    if not items:
        raise ValueError(
            "فاکتور بدون قلم قابل ثبت نیست."
        )

    with get_connection() as connection:

        try:
            connection.execute("BEGIN")

            invoice_no = next_invoice_no(
                connection
            )

            subtotal = sum(
                int(item["line_total"])
                for item in items
            )

            total = (
                subtotal
                - int(discount)
                + int(tax)
            )

            if total < 0:
                raise ValueError(
                    "مبلغ نهایی نمی‌تواند منفی باشد."
                )

            field = (
                "customer_id"
                if invoice_type == "sale"
                else "supplier_id"
            )

            cursor = connection.execute(
                f"""
                INSERT INTO invoices
                (
                    invoice_no,
                    invoice_type,
                    {field},
                    subtotal,
                    discount,
                    tax,
                    total,
                    payment_method,
                    status,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    invoice_no,
                    invoice_type,
                    party_id,
                    subtotal,
                    discount,
                    tax,
                    total,
                    payment_method,
                    "confirmed",
                    now(),
                ),
            )

            invoice_id = cursor.lastrowid

            total_cost = 0

            for item in items:

                product = connection.execute(
                    """
                    SELECT *
                    FROM products
                    WHERE id=?
                    AND active=1
                    """,
                    (
                        item["product_id"],
                    ),
                ).fetchone()

                if not product:
                    raise ValueError(
                        "کالا یافت نشد."
                    )

                quantity = float(
                    item["qty"]
                )

                if quantity <= 0:
                    raise ValueError(
                        "تعداد باید بیشتر از صفر باشد."
                    )

                line_total = int(
                    round(
                        quantity
                        * int(item["unit_price"])
                        - int(item.get("discount", 0))
                        + int(item.get("tax", 0))
                    )
                )

                if invoice_type == "sale":

                    if product["stock"] < quantity:
                        raise ValueError(
                            f"موجودی کالای «{product['name']}» کافی نیست."
                        )

                    item_cost = int(
                        round(
                            quantity
                            * product["purchase_cost"]
                        )
                    )

                    total_cost += item_cost

                    new_stock = (
                        product["stock"]
                        - quantity
                    )

                    movement_qty = -quantity
                    movement_cost = (
                        product["purchase_cost"]
                    )

                else:

                    item_cost = 0

                    new_stock = (
                        product["stock"]
                        + quantity
                    )

                    movement_qty = quantity
                    movement_cost = int(
                        item["unit_price"]
                    )

                    connection.execute(
                        """
                        UPDATE products
                        SET purchase_cost=?
                        WHERE id=?
                        """,
                        (
                            item["unit_price"],
                            product["id"],
                        ),
                    )

                connection.execute(
                    """
                    INSERT INTO invoice_items
                    (
                        invoice_id,
                        product_id,
                        qty,
                        unit_price,
                        discount,
                        tax,
                        line_total,
                        cost_total
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        invoice_id,
                        product["id"],
                        quantity,
                        item["unit_price"],
                        item.get(
                            "discount",
                            0,
                        ),
                        item.get(
                            "tax",
                            0,
                        ),
                        line_total,
                        item_cost,
                    ),
                )

                connection.execute(
                    """
                    UPDATE products
                    SET stock=?
                    WHERE id=?
                    """,
                    (
                        new_stock,
                        product["id"],
                    ),
                )

                connection.execute(
                    """
                    INSERT INTO stock_movements
                    (
                        product_id,
                        movement_type,
                        qty,
                        unit_cost,
                        ref_type,
                        ref_id,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        product["id"],
                        invoice_type,
                        movement_qty,
                        movement_cost,
                        "invoice",
                        invoice_id,
                        now(),
                    ),
                )

            journal_cursor = connection.execute(
                """
                INSERT INTO journal_entries
                (
                    ref_type,
                    ref_id,
                    description,
                    created_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    invoice_type,
                    invoice_id,
                    (
                        "ثبت فاکتور فروش"
                        if invoice_type == "sale"
                        else "ثبت فاکتور خرید"
                    ),
                    now(),
                ),
            )

            journal_id = journal_cursor.lastrowid

            if invoice_type == "sale":

                journal_lines = sale_entry_lines(
                    total,
                    total_cost,
                    payment_method,
                )

            else:

                journal_lines = purchase_entry_lines(
                    total,
                    payment_method,
                )

            for (
                account_code,
                debit,
                credit,
            ) in journal_lines:

                connection.execute(
                    """
                    INSERT INTO journal_lines
                    (
                        journal_id,
                        account_code,
                        debit,
                        credit
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        journal_id,
                        account_code,
                        debit,
                        credit,
                    ),
                )

            connection.commit()

            return (
                invoice_id,
                invoice_no,
                total,
                total_cost,
            )

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()


def get_invoice(invoice_id):

    with get_connection() as connection:

        invoice = connection.execute(
            """
            SELECT
                i.*,
                c.name AS customer_name,
                s.name AS supplier_name
            FROM invoices i

            LEFT JOIN customers c
                ON c.id=i.customer_id

            LEFT JOIN suppliers s
                ON s.id=i.supplier_id

            WHERE i.id=?
            """,
            (
                invoice_id,
            ),
        ).fetchone()

        if not invoice:
            return None, []

        items = connection.execute(
            """
            SELECT
                ii.*,
                p.code,
                p.name,
                p.unit
            FROM invoice_items ii

            JOIN products p
                ON p.id=ii.product_id

            WHERE ii.invoice_id=?
            ORDER BY ii.id
            """,
            (
                invoice_id,
            ),
        ).fetchall()

        return invoice, items


def list_invoices(limit=20):

    with get_connection() as connection:

        return connection.execute(
            """
            SELECT
                i.*,
                c.name AS customer_name,
                s.name AS supplier_name
            FROM invoices i

            LEFT JOIN customers c
                ON c.id=i.customer_id

            LEFT JOIN suppliers s
                ON s.id=i.supplier_id

            ORDER BY i.id DESC
            LIMIT ?
            """,
            (
                limit,
            ),
        ).fetchall()


# =========================================================
# STOCK / REPORTS
# =========================================================

def stock_report():

    with get_connection() as connection:

        return connection.execute(
            """
            SELECT *
            FROM products
            WHERE active=1
            ORDER BY name
            """
        ).fetchall()


def low_stock():

    with get_connection() as connection:

        return connection.execute(
            """
            SELECT *
            FROM products
            WHERE active=1
            AND stock <= min_stock
            ORDER BY stock
            """
        ).fetchall()


def sales_summary():

    with get_connection() as connection:

        return connection.execute(
            """
            SELECT
                COUNT(*) AS n,
                COALESCE(
                    SUM(total),
                    0
                ) AS total
            FROM invoices
            WHERE invoice_type='sale'
            AND status='confirmed'
            """
        ).fetchone()


def purchase_summary():

    with get_connection() as connection:

        return connection.execute(
            """
            SELECT
                COUNT(*) AS n,
                COALESCE(
                    SUM(total),
                    0
                ) AS total
            FROM invoices
            WHERE invoice_type='purchase'
            AND status='confirmed'
            """
        ).fetchone()


# =========================================================
# EXPENSES
# =========================================================

def add_expense(
    title,
    amount,
    payment_method,
    note="",
):

    with get_connection() as connection:

        cursor = connection.execute(
            """
            INSERT INTO expenses
            (
                title,
                amount,
                payment_method,
                note,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                title,
                amount,
                payment_method,
                note,
                now(),
            ),
        )

        return cursor.lastrowid


# =========================================================
# SUBSCRIPTIONS
# =========================================================

def create_payment(
    telegram_id,
    plan_code,
    plan_name,
    amount,
):

    user = get_user(
        telegram_id
    )

    if not user:
        raise ValueError(
            "کاربر ثبت نشده است."
        )

    with get_connection() as connection:

        cursor = connection.execute(
            """
            INSERT INTO subscription_payments
            (
                telegram_user_id,
                plan_code,
                plan_name,
                amount,
                submitted_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user["id"],
                plan_code,
                plan_name,
                amount,
                now(),
            ),
        )

        return cursor.lastrowid


def get_payment(payment_id):

    with get_connection() as connection:

        return connection.execute(
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
            (
                payment_id,
            ),
        ).fetchone()


def attach_receipt(
    payment_id,
    file_id,
    unique_id,
):

    with get_connection() as connection:

        connection.execute(
            """
            UPDATE subscription_payments

            SET
                receipt_file_id=?,
                receipt_file_unique_id=?

            WHERE id=?
            """,
            (
                file_id,
                unique_id,
                payment_id,
            ),
        )


def pending_payments():

    with get_connection() as connection:

        return connection.execute(
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

            ORDER BY p.id
            """
        ).fetchall()


def approve_payment(
    payment_id,
    reviewer_id,
    duration_days,
):

    with get_connection() as connection:

        payment = connection.execute(
            """
            SELECT *
            FROM subscription_payments
            WHERE id=?
            AND status='pending'
            """,
            (
                payment_id,
            ),
        ).fetchone()

        if not payment:
            return None

        today = date.today()

        active_subscription = connection.execute(
            """
            SELECT *
            FROM subscriptions

            WHERE telegram_user_id=?

            AND status='active'

            AND end_date>=?

            ORDER BY end_date DESC

            LIMIT 1
            """,
            (
                payment["telegram_user_id"],
                today.isoformat(),
            ),
        ).fetchone()

        if active_subscription:

            start_date = (
                date.fromisoformat(
                    active_subscription[
                        "end_date"
                    ]
                )
                + timedelta(days=1)
            )

        else:

            start_date = today

        end_date = (
            start_date
            + timedelta(
                days=duration_days - 1
            )
        )

        connection.execute(
            """
            UPDATE subscription_payments

            SET
                status='approved',
                reviewed_at=?,
                reviewed_by=?

            WHERE id=?
            """,
            (
                now(),
                reviewer_id,
                payment_id,
            ),
        )

        cursor = connection.execute(
            """
            INSERT INTO subscriptions
            (
                telegram_user_id,
                plan_code,
                plan_name,
                start_date,
                end_date,
                status,
                payment_id,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payment["telegram_user_id"],
                payment["plan_code"],
                payment["plan_name"],
                start_date.isoformat(),
                end_date.isoformat(),
                "active",
                payment_id,
                now(),
            ),
        )

        return {
            "subscription_id": cursor.lastrowid,
            "telegram_id": payment[
                "telegram_user_id"
            ],
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "plan_name": payment["plan_name"],
        }


def reject_payment(
    payment_id,
    reviewer_id,
    reason="",
):

    with get_connection() as connection:

        result = connection.execute(
            """
            UPDATE subscription_payments

            SET
                status='rejected',
                reviewed_at=?,
                reviewed_by=?,
                rejection_reason=?

            WHERE id=?
            AND status='pending'
            """,
            (
                now(),
                reviewer_id,
                reason,
                payment_id,
            ),
        )

        return result.rowcount > 0


def active_subscription(
    telegram_id,
):

    with get_connection() as connection:

        return connection.execute(
            """
            SELECT
                s.*
            FROM subscriptions s

            JOIN telegram_users u
                ON u.id=s.telegram_user_id

            WHERE u.telegram_id=?

            AND s.status='active'

            AND s.end_date>=?

            ORDER BY s.end_date DESC

            LIMIT 1
            """,
            (
                telegram_id,
                date.today().isoformat(),
            ),
        ).fetchone()
