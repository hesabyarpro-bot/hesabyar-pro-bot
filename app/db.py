# app/db.py

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, date, timedelta
from pathlib import Path


# =========================================================
# CONFIG
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = os.getenv(
    "DB_PATH",
    str(BASE_DIR / "hesabyar.db")
)


# =========================================================
# CONNECTION
# =========================================================

def get_connection():
    """
    ایجاد یک اتصال مستقل به SQLite.

    نکته مهم:
    این تابع connection را نمی‌بندد.
    مسئول بستن connection همان تابعی است که آن را ایجاد کرده.
    """

    connection = sqlite3.connect(
        DB_PATH,
        timeout=30,
        check_same_thread=False,
    )

    connection.row_factory = sqlite3.Row

    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 30000")

    return connection


@contextmanager
def db_connection():
    """
    Context manager استاندارد برای عملیات معمول دیتابیس.
    """

    connection = get_connection()

    try:
        yield connection
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


@contextmanager
def db_transaction():
    """
    تراکنش کامل SQLite.

    تمام عملیات داخل تراکنش باید با همین connection
    انجام شوند.
    """

    connection = get_connection()

    try:
        connection.execute("BEGIN")
        yield connection
        connection.commit()

    except Exception:
        try:
            connection.rollback()
        except Exception:
            pass

        raise

    finally:
        connection.close()


# =========================================================
# HELPERS
# =========================================================

def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_text():
    return date.today().isoformat()


def money(value):
    if value is None:
        return 0

    try:
        return int(float(value))
    except Exception:
        return 0


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def init_db():
    """
    ایجاد تمام جدول‌های موردنیاز سیستم.
    """

    Path(DB_PATH).parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with db_connection() as connection:

        connection.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS telegram_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL UNIQUE,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                address TEXT,
                opening_balance REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                address TEXT,
                opening_balance REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                name TEXT NOT NULL,
                unit TEXT NOT NULL DEFAULT 'عدد',
                sale_price REAL NOT NULL DEFAULT 0,
                purchase_cost REAL NOT NULL DEFAULT 0,
                stock REAL NOT NULL DEFAULT 0,
                min_stock REAL NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_no INTEGER NOT NULL UNIQUE,
                invoice_type TEXT NOT NULL,
                customer_id INTEGER,
                supplier_id INTEGER,
                total_amount REAL NOT NULL DEFAULT 0,
                discount REAL NOT NULL DEFAULT 0,
                tax REAL NOT NULL DEFAULT 0,
                final_amount REAL NOT NULL DEFAULT 0,
                payment_method TEXT,
                status TEXT NOT NULL DEFAULT 'confirmed',
                invoice_date TEXT NOT NULL,
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
                quantity REAL NOT NULL,
                unit_price REAL NOT NULL,
                discount REAL NOT NULL DEFAULT 0,
                tax REAL NOT NULL DEFAULT 0,
                line_total REAL NOT NULL DEFAULT 0,

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
                quantity REAL NOT NULL,
                unit_cost REAL NOT NULL DEFAULT 0,
                reference_type TEXT,
                reference_id INTEGER,
                created_at TEXT NOT NULL,

                FOREIGN KEY(product_id)
                    REFERENCES products(id)
            );

            CREATE TABLE IF NOT EXISTS journal_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_no INTEGER NOT NULL UNIQUE,
                entry_date TEXT NOT NULL,
                description TEXT,
                reference_type TEXT,
                reference_id INTEGER,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS journal_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                journal_entry_id INTEGER NOT NULL,
                account_code TEXT NOT NULL,
                account_name TEXT NOT NULL,
                debit REAL NOT NULL DEFAULT 0,
                credit REAL NOT NULL DEFAULT 0,

                FOREIGN KEY(journal_entry_id)
                    REFERENCES journal_entries(id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                plan_code TEXT NOT NULL,
                plan_name TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'inactive',
                payment_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,

                FOREIGN KEY(telegram_user_id)
                    REFERENCES telegram_users(id)
            );

            CREATE TABLE IF NOT EXISTS subscription_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                plan_code TEXT NOT NULL,
                plan_name TEXT NOT NULL,
                amount REAL NOT NULL DEFAULT 0,
                receipt_file_id TEXT,
                receipt_file_unique_id TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                submitted_at TEXT NOT NULL,
                reviewed_at TEXT,
                reviewed_by INTEGER,
                rejection_reason TEXT,

                FOREIGN KEY(telegram_user_id)
                    REFERENCES telegram_users(id)
            );

            CREATE INDEX IF NOT EXISTS idx_invoices_date
                ON invoices(invoice_date);

            CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice
                ON invoice_items(invoice_id);

            CREATE INDEX IF NOT EXISTS idx_stock_product
                ON stock_movements(product_id);

            CREATE INDEX IF NOT EXISTS idx_journal_lines_account
                ON journal_lines(account_code);

            CREATE INDEX IF NOT EXISTS idx_subscription_payments_status
                ON subscription_payments(status);

            CREATE INDEX IF NOT EXISTS idx_subscriptions_user
                ON subscriptions(telegram_user_id);
            """
        )


# =========================================================
# TELEGRAM USERS
# =========================================================

def upsert_telegram_user(
    telegram_id,
    username=None,
    first_name=None,
    last_name=None
):
    current_time = now_text()

    with db_connection() as connection:

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
                is_active = 1,
                updated_at = excluded.updated_at
            """,
            (
                telegram_id,
                username,
                first_name,
                last_name,
                current_time,
                current_time
            )
        )

        row = connection.execute(
            """
            SELECT *
            FROM telegram_users
            WHERE telegram_id = ?
            """,
            (telegram_id,)
        ).fetchone()

        return row


def get_telegram_user(telegram_id):

    with db_connection() as connection:

        return connection.execute(
            """
            SELECT *
            FROM telegram_users
            WHERE telegram_id = ?
            """,
            (telegram_id,)
        ).fetchone()


# =========================================================
# CUSTOMERS
# =========================================================

def create_customer(
    name,
    phone=None,
    address=None,
    opening_balance=0
):

    with db_connection() as connection:

        cursor = connection.execute(
            """
            INSERT INTO customers (
                name,
                phone,
                address,
                opening_balance,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name,
                phone,
                address,
                money(opening_balance),
                now_text()
            )
        )

        return cursor.lastrowid


def get_customer(customer_id):

    with db_connection() as connection:

        return connection.execute(
            """
            SELECT *
            FROM customers
            WHERE id = ?
            """,
            (customer_id,)
        ).fetchone()


def list_customers():

    with db_connection() as connection:

        return connection.execute(
            """
            SELECT *
            FROM customers
            ORDER BY name
            """
        ).fetchall()


# =========================================================
# SUPPLIERS
# =========================================================

def create_supplier(
    name,
    phone=None,
    address=None,
    opening_balance=0
):

    with db_connection() as connection:

        cursor = connection.execute(
            """
            INSERT INTO suppliers (
                name,
                phone,
                address,
                opening_balance,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name,
                phone,
                address,
                money(opening_balance),
                now_text()
            )
        )

        return cursor.lastrowid


def get_supplier(supplier_id):

    with db_connection() as connection:

        return connection.execute(
            """
            SELECT *
            FROM suppliers
            WHERE id = ?
            """,
            (supplier_id,)
        ).fetchone()


def list_suppliers():

    with db_connection() as connection:

        return connection.execute(
            """
            SELECT *
            FROM suppliers
            ORDER BY name
            """
        ).fetchall()


# =========================================================
# PRODUCTS
# =========================================================

def create_product(
    name,
    code=None,
    unit="عدد",
    sale_price=0,
    purchase_cost=0,
    stock=0,
    min_stock=0
):

    current_time = now_text()

    with db_connection() as connection:

        cursor = connection.execute(
            """
            INSERT INTO products (
                code,
                name,
                unit,
                sale_price,
                purchase_cost,
                stock,
                min_stock,
                is_active,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                code,
                name,
                unit,
                money(sale_price),
                money(purchase_cost),
                float(stock),
                float(min_stock),
                current_time,
                current_time
            )
        )

        return cursor.lastrowid


def get_product(product_id):

    with db_connection() as connection:

        return connection.execute(
            """
            SELECT *
            FROM products
            WHERE id = ?
            """,
            (product_id,)
        ).fetchone()


def list_products(active_only=True):

    with db_connection() as connection:

        if active_only:

            return connection.execute(
                """
                SELECT *
                FROM products
                WHERE is_active = 1
                ORDER BY name
                """
            ).fetchall()

        return connection.execute(
            """
            SELECT *
            FROM products
            ORDER BY name
            """
        ).fetchall()


def update_product_stock(
    connection,
    product_id,
    quantity
):
    """
    فقط داخل تراکنش استفاده شود.
    """

    connection.execute(
        """
        UPDATE products
        SET stock = stock + ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            float(quantity),
            now_text(),
            product_id
        )
    )


# =========================================================
# INVOICE NUMBER
# =========================================================

def next_invoice_no(connection):
    """
    شماره فاکتور بعدی.

    نکته:
    حتماً همان connection تراکنش را دریافت می‌کند.
    """

    row = connection.execute(
        """
        SELECT
            COALESCE(MAX(invoice_no), 0) + 1 AS next_no
        FROM invoices
        """
    ).fetchone()

    return int(row["next_no"])


# =========================================================
# JOURNAL NUMBER
# =========================================================

def next_journal_no(connection):

    row = connection.execute(
        """
        SELECT
            COALESCE(MAX(entry_no), 0) + 1 AS next_no
        FROM journal_entries
        """
    ).fetchone()

    return int(row["next_no"])


# =========================================================
# CREATE INVOICE
# =========================================================

def create_invoice(
    invoice_type,
    customer_id=None,
    supplier_id=None,
    items=None,
    payment_method=None,
    discount=0,
    tax=0,
    invoice_date=None
):
    """
    ایجاد کامل فاکتور + اقلام + موجودی + سند حسابداری
    در یک تراکنش.

    invoice_type:
        sale
        purchase
    """

    items = items or []

    if not items:
        raise ValueError(
            "حداقل یک قلم کالا برای فاکتور لازم است."
        )

    invoice_date = (
        invoice_date
        or today_text()
    )

    discount = money(discount)
    tax = money(tax)

    with db_transaction() as connection:

        # ---------------------------------------------
        # محاسبه اقلام
        # ---------------------------------------------

        prepared_items = []

        total_amount = 0

        for item in items:

            product_id = int(
                item["product_id"]
            )

            quantity = float(
                item["quantity"]
            )

            unit_price = money(
                item["unit_price"]
            )

            item_discount = money(
                item.get("discount", 0)
            )

            item_tax = money(
                item.get("tax", 0)
            )

            if quantity <= 0:
                raise ValueError(
                    "تعداد کالا باید بیشتر از صفر باشد."
                )

            if unit_price < 0:
                raise ValueError(
                    "قیمت کالا نمی‌تواند منفی باشد."
                )

            product = connection.execute(
                """
                SELECT *
                FROM products
                WHERE id = ?
                AND is_active = 1
                """,
                (product_id,)
            ).fetchone()

            if product is None:
                raise ValueError(
                    f"کالا با شناسه {product_id} پیدا نشد."
                )

            line_total = (
                quantity * unit_price
                - item_discount
                + item_tax
            )

            if line_total < 0:
                raise ValueError(
                    "مبلغ نهایی قلم کالا نمی‌تواند منفی باشد."
                )

            total_amount += line_total

            prepared_items.append(
                {
                    "product_id": product_id,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "discount": item_discount,
                    "tax": item_tax,
                    "line_total": line_total,
                    "purchase_cost": money(
                        product["purchase_cost"]
                    ),
                }
            )

        final_amount = (
            total_amount
            - discount
            + tax
        )

        if final_amount < 0:
            raise ValueError(
                "مبلغ نهایی فاکتور نمی‌تواند منفی باشد."
            )

        # ---------------------------------------------
        # شماره فاکتور
        # ---------------------------------------------

        invoice_no = next_invoice_no(
            connection
        )

        current_time = now_text()

        # ---------------------------------------------
        # ثبت فاکتور
        # ---------------------------------------------

        cursor = connection.execute(
            """
            INSERT INTO invoices (
                invoice_no,
                invoice_type,
                customer_id,
                supplier_id,
                total_amount,
                discount,
                tax,
                final_amount,
                payment_method,
                status,
                invoice_date,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'confirmed', ?, ?)
            """,
            (
                invoice_no,
                invoice_type,
                customer_id,
                supplier_id,
                total_amount,
                discount,
                tax,
                final_amount,
                payment_method,
                invoice_date,
                current_time
            )
        )

        invoice_id = cursor.lastrowid

        # ---------------------------------------------
        # اقلام فاکتور + موجودی
        # ---------------------------------------------

        total_cogs = 0

        for item in prepared_items:

            connection.execute(
                """
                INSERT INTO invoice_items (
                    invoice_id,
                    product_id,
                    quantity,
                    unit_price,
                    discount,
                    tax,
                    line_total
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    invoice_id,
                    item["product_id"],
                    item["quantity"],
                    item["unit_price"],
                    item["discount"],
                    item["tax"],
                    item["line_total"]
                )
            )

            if invoice_type == "sale":

                product = connection.execute(
                    """
                    SELECT stock
                    FROM products
                    WHERE id = ?
                    """,
                    (
                        item["product_id"],
                    )
                ).fetchone()

                current_stock = float(
                    product["stock"]
                )

                if current_stock < item["quantity"]:
                    raise ValueError(
                        "موجودی کالا کافی نیست."
                    )

                update_product_stock(
                    connection,
                    item["product_id"],
                    -item["quantity"]
                )

                total_cogs += (
                    item["quantity"]
                    * item["purchase_cost"]
                )

                movement_type = "sale"

            else:

                update_product_stock(
                    connection,
                    item["product_id"],
                    item["quantity"]
                )

                movement_type = "purchase"

            connection.execute(
                """
                INSERT INTO stock_movements (
                    product_id,
                    movement_type,
                    quantity,
                    unit_cost,
                    reference_type,
                    reference_id,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item["product_id"],
                    movement_type,
                    item["quantity"],
                    (
                        item["purchase_cost"]
                        if invoice_type == "sale"
                        else item["unit_price"]
                    ),
                    "invoice",
                    invoice_id,
                    current_time
                )
            )

            # در خرید، آخرین قیمت خرید را ذخیره می‌کنیم.
            if invoice_type == "purchase":

                connection.execute(
                    """
                    UPDATE products
                    SET purchase_cost = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        item["unit_price"],
                        current_time,
                        item["product_id"]
                    )
                )

        # ---------------------------------------------
        # سند حسابداری
        # ---------------------------------------------

        entry_no = next_journal_no(
            connection
        )

        if invoice_type == "sale":

            description = (
                f"ثبت فروش فاکتور شماره {invoice_no}"
            )

        else:

            description = (
                f"ثبت خرید فاکتور شماره {invoice_no}"
            )

        journal_cursor = connection.execute(
            """
            INSERT INTO journal_entries (
                entry_no,
                entry_date,
                description,
                reference_type,
                reference_id,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                entry_no,
                invoice_date,
                description,
                "invoice",
                invoice_id,
                current_time
            )
        )

        journal_entry_id = (
            journal_cursor.lastrowid
        )

        # ---------------------------------------------
        # فروش
        # ---------------------------------------------

        if invoice_type == "sale":

            if payment_method == "cash":

                debit_code = "1101"
                debit_name = "صندوق"

            elif payment_method == "bank":

                debit_code = "1102"
                debit_name = "بانک"

            else:

                debit_code = "1201"
                debit_name = "حساب‌های دریافتنی"

            connection.execute(
                """
                INSERT INTO journal_lines (
                    journal_entry_id,
                    account_code,
                    account_name,
                    debit,
                    credit
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    journal_entry_id,
                    debit_code,
                    debit_name,
                    final_amount,
                    0
                )
            )

            connection.execute(
                """
                INSERT INTO journal_lines (
                    journal_entry_id,
                    account_code,
                    account_name,
                    debit,
                    credit
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    journal_entry_id,
                    "4101",
                    "فروش",
                    0,
                    total_amount
                )
            )

            if tax:

                connection.execute(
                    """
                    INSERT INTO journal_lines (
                        journal_entry_id,
                        account_code,
                        account_name,
                        debit,
                        credit
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        journal_entry_id,
                        "2201",
                        "مالیات و عوارض پرداختنی",
                        0,
                        tax
                    )
                )

            # ثبت بهای تمام شده
            if total_cogs > 0:

                connection.execute(
                    """
                    INSERT INTO journal_lines (
                        journal_entry_id,
                        account_code,
                        account_name,
                        debit,
                        credit
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        journal_entry_id,
                        "5101",
                        "بهای تمام شده کالای فروش رفته",
                        total_cogs,
                        0
                    )
                )

                connection.execute(
                    """
                    INSERT INTO journal_lines (
                        journal_entry_id,
                        account_code,
                        account_name,
                        debit,
                        credit
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        journal_entry_id,
                        "1401",
                        "موجودی کالا",
                        0,
                        total_cogs
                    )
                )

        # ---------------------------------------------
        # خرید
        # ---------------------------------------------

        else:

            if payment_method == "cash":

                credit_code = "1101"
                credit_name = "صندوق"

            elif payment_method == "bank":

                credit_code = "1102"
                credit_name = "بانک"

            else:

                credit_code = "2101"
                credit_name = "حساب‌های پرداختنی"

            connection.execute(
                """
                INSERT INTO journal_lines (
                    journal_entry_id,
                    account_code,
                    account_name,
                    debit,
                    credit
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    journal_entry_id,
                    "1401",
                    "موجودی کالا",
                    final_amount,
                    0
                )
            )

            connection.execute(
                """
                INSERT INTO journal_lines (
                    journal_entry_id,
                    account_code,
                    account_name,
                    debit,
                    credit
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    journal_entry_id,
                    credit_code,
                    credit_name,
                    0,
                    final_amount
                )
            )

        return {
            "invoice_id": invoice_id,
            "invoice_no": invoice_no,
            "total_amount": total_amount,
            "discount": discount,
            "tax": tax,
            "final_amount": final_amount,
            "journal_entry_id": journal_entry_id,
        }


# =========================================================
# INVOICE READ
# =========================================================

def get_invoice(invoice_id):

    with db_connection() as connection:

        invoice = connection.execute(
            """
            SELECT
                i.*,
                c.name AS customer_name,
                s.name AS supplier_name
            FROM invoices i

            LEFT JOIN customers c
                ON c.id = i.customer_id

            LEFT JOIN suppliers s
                ON s.id = i.supplier_id

            WHERE i.id = ?
            """,
            (invoice_id,)
        ).fetchone()

        if invoice is None:
            return None

        items = connection.execute(
            """
            SELECT
                ii.*,
                p.name AS product_name,
                p.code AS product_code
            FROM invoice_items ii

            JOIN products p
                ON p.id = ii.product_id

            WHERE ii.invoice_id = ?

            ORDER BY ii.id
            """,
            (invoice_id,)
        ).fetchall()

        return {
            "invoice": invoice,
            "items": items
        }


def list_invoices(
    invoice_type=None,
    limit=50
):

    with db_connection() as connection:

        if invoice_type:

            return connection.execute(
                """
                SELECT
                    i.*,
                    c.name AS customer_name,
                    s.name AS supplier_name
                FROM invoices i

                LEFT JOIN customers c
                    ON c.id = i.customer_id

                LEFT JOIN suppliers s
                    ON s.id = i.supplier_id

                WHERE i.invoice_type = ?

                ORDER BY i.id DESC

                LIMIT ?
                """,
                (
                    invoice_type,
                    int(limit)
                )
            ).fetchall()

        return connection.execute(
            """
            SELECT
                i.*,
                c.name AS customer_name,
                s.name AS supplier_name
            FROM invoices i

            LEFT JOIN customers c
                ON c.id = i.customer_id

            LEFT JOIN suppliers s
                ON s.id = i.supplier_id

            ORDER BY i.id DESC

            LIMIT ?
            """,
            (int(limit),)
        ).fetchall()


# =========================================================
# REPORTS
# =========================================================

def get_dashboard():

    with db_connection() as connection:

        sales = connection.execute(
            """
            SELECT
                COALESCE(
                    SUM(final_amount),
                    0
                ) AS total
            FROM invoices
            WHERE invoice_type = 'sale'
            """
        ).fetchone()

        purchases = connection.execute(
            """
            SELECT
                COALESCE(
                    SUM(final_amount),
                    0
                ) AS total
            FROM invoices
            WHERE invoice_type = 'purchase'
            """
        ).fetchone()

        stock = connection.execute(
            """
            SELECT
                COALESCE(
                    SUM(stock * purchase_cost),
                    0
                ) AS total
            FROM products
            WHERE is_active = 1
            """
        ).fetchone()

        products = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM products
            WHERE is_active = 1
            """
        ).fetchone()

        customers = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM customers
            """
        ).fetchone()

        return {
            "sales": money(
                sales["total"]
            ),
            "purchases": money(
                purchases["total"]
            ),
            "stock_value": money(
                stock["total"]
            ),
            "products": int(
                products["count"]
            ),
            "customers": int(
                customers["count"]
            )
        }


def get_low_stock_products():

    with db_connection() as connection:

        return connection.execute(
            """
            SELECT *
            FROM products
            WHERE is_active = 1
              AND stock <= min_stock
            ORDER BY stock ASC
            """
        ).fetchall()


def get_stock_report():

    with db_connection() as connection:

        return connection.execute(
            """
            SELECT
                id,
                code,
                name,
                unit,
                stock,
                min_stock,
                purchase_cost,
                sale_price,

                stock * purchase_cost
                    AS stock_value

            FROM products

            WHERE is_active = 1

            ORDER BY name
            """
        ).fetchall()


def get_sales_report():

    with db_connection() as connection:

        return connection.execute(
            """
            SELECT
                COUNT(*) AS invoice_count,
                COALESCE(
                    SUM(final_amount),
                    0
                ) AS total_sales
            FROM invoices
            WHERE invoice_type = 'sale'
            """
        ).fetchone()


def get_purchase_report():

    with db_connection() as connection:

        return connection.execute(
            """
            SELECT
                COUNT(*) AS invoice_count,
                COALESCE(
                    SUM(final_amount),
                    0
                ) AS total_purchases
            FROM invoices
            WHERE invoice_type = 'purchase'
            """
        ).fetchone()


# =========================================================
# SUBSCRIPTIONS
# =========================================================

def create_subscription_payment(
    telegram_user_id,
    plan_code,
    plan_name,
    amount
):

    with db_connection() as connection:

        cursor = connection.execute(
            """
            INSERT INTO subscription_payments (
                telegram_user_id,
                plan_code,
                plan_name,
                amount,
                status,
                submitted_at
            )
            VALUES (?, ?, ?, ?, 'pending', ?)
            """,
            (
                telegram_user_id,
                plan_code,
                plan_name,
                money(amount),
                now_text()
            )
        )

        return cursor.lastrowid


def attach_receipt_to_payment(
    payment_id,
    receipt_file_id,
    receipt_file_unique_id=None
):

    with db_connection() as connection:

        connection.execute(
            """
            UPDATE subscription_payments

            SET
                receipt_file_id = ?,
                receipt_file_unique_id = ?

            WHERE id = ?
            """,
            (
                receipt_file_id,
                receipt_file_unique_id,
                payment_id
            )
        )


def get_payment(payment_id):

    with db_connection() as connection:

        return connection.execute(
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
        ).fetchone()


def get_pending_payments():

    with db_connection() as connection:

        return connection.execute(
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
        ).fetchall()


# =========================================================
# APPROVE SUBSCRIPTION
# =========================================================

def approve_subscription_payment(
    payment_id,
    reviewed_by,
    duration_days
):

    duration_days = int(duration_days)

    if duration_days <= 0:
        raise ValueError(
            "مدت اشتراک نامعتبر است."
        )

    with db_transaction() as connection:

        payment = connection.execute(
            """
            SELECT *
            FROM subscription_payments
            WHERE id = ?
            """,
            (payment_id,)
        ).fetchone()

        if payment is None:
            raise ValueError(
                "پرداخت پیدا نشد."
            )

        if payment["status"] != "pending":
            raise ValueError(
                "این پرداخت قبلاً بررسی شده است."
            )

        user_id = payment[
            "telegram_user_id"
        ]

        # ---------------------------------------------
        # تاریخ شروع
        # ---------------------------------------------

        today = date.today()

        active = connection.execute(
            """
            SELECT *
            FROM subscriptions

            WHERE telegram_user_id = ?
              AND status = 'active'
              AND end_date >= ?

            ORDER BY end_date DESC

            LIMIT 1
            """,
            (
                user_id,
                today.isoformat()
            )
        ).fetchone()

        if active:

            old_end = date.fromisoformat(
                active["end_date"]
            )

            start_date = (
                old_end
                + timedelta(days=1)
            )

        else:

            start_date = today

        end_date = (
            start_date
            + timedelta(days=duration_days - 1)
        )

        current_time = now_text()

        # ---------------------------------------------
        # غیرفعال کردن اشتراک‌های قبلی
        # ---------------------------------------------

        connection.execute(
            """
            UPDATE subscriptions

            SET
                status = 'expired',
                updated_at = ?

            WHERE telegram_user_id = ?
              AND status = 'active'
            """,
            (
                current_time,
                user_id
            )
        )

        # ---------------------------------------------
        # ایجاد اشتراک جدید
        # ---------------------------------------------

        cursor = connection.execute(
            """
            INSERT INTO subscriptions (
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
            """,
            (
                user_id,
                payment["plan_code"],
                payment["plan_name"],
                start_date.isoformat(),
                end_date.isoformat(),
                payment_id,
                current_time,
                current_time
            )
        )

        subscription_id = (
            cursor.lastrowid
        )

        # ---------------------------------------------
        # تأیید پرداخت
        # ---------------------------------------------

        connection.execute(
            """
            UPDATE subscription_payments

            SET
                status = 'approved',
                reviewed_at = ?,
                reviewed_by = ?

            WHERE id = ?
            """,
            (
                current_time,
                reviewed_by,
                payment_id
            )
        )

        return {
            "subscription_id": subscription_id,
            "user_id": user_id,
            "plan_code": payment["plan_code"],
            "plan_name": payment["plan_name"],
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }


# =========================================================
# REJECT SUBSCRIPTION
# =========================================================

def reject_subscription_payment(
    payment_id,
    reviewed_by,
    rejection_reason=None
):

    with db_connection() as connection:

        payment = connection.execute(
            """
            SELECT *
            FROM subscription_payments
            WHERE id = ?
            """,
            (payment_id,)
        ).fetchone()

        if payment is None:
            raise ValueError(
                "پرداخت پیدا نشد."
            )

        if payment["status"] != "pending":
            raise ValueError(
                "این پرداخت قبلاً بررسی شده است."
            )

        connection.execute(
            """
            UPDATE subscription_payments

            SET
                status = 'rejected',
                reviewed_at = ?,
                reviewed_by = ?,
                rejection_reason = ?

            WHERE id = ?
            """,
            (
                now_text(),
                reviewed_by,
                rejection_reason,
                payment_id
            )
        )


# =========================================================
# ACTIVE SUBSCRIPTION
# =========================================================

def deactivate_expired_subscriptions():

    with db_connection() as connection:

        connection.execute(
            """
            UPDATE subscriptions

            SET
                status = 'expired',
                updated_at = ?

            WHERE status = 'active'
              AND end_date < ?
            """,
            (
                now_text(),
                today_text()
            )
        )


def get_active_subscription(
    telegram_user_id
):

    deactivate_expired_subscriptions()

    with db_connection() as connection:

        return connection.execute(
            """
            SELECT *
            FROM subscriptions

            WHERE telegram_user_id = ?
              AND status = 'active'
              AND end_date >= ?

            ORDER BY end_date DESC

            LIMIT 1
            """,
            (
                telegram_user_id,
                today_text()
            )
        ).fetchone()


def get_subscription_status(
    telegram_user_id
):

    subscription = get_active_subscription(
        telegram_user_id
    )

    if subscription is None:

        return {
            "active": False,
            "subscription": None
        }

    return {
        "active": True,
        "subscription": subscription
    }


# =========================================================
# COMPATIBILITY ALIASES
# =========================================================
#
# برای جلوگیری از خطا در صورتی که bot.py
# از نام‌های کوتاه‌تر استفاده کرده باشد.
# =========================================================

def approve_payment(
    payment_id,
    reviewed_by,
    duration_days
):

    return approve_subscription_payment(
        payment_id=payment_id,
        reviewed_by=reviewed_by,
        duration_days=duration_days
    )


def reject_payment(
    payment_id,
    reviewed_by,
    rejection_reason=None
):

    return reject_subscription_payment(
        payment_id=payment_id,
        reviewed_by=reviewed_by,
        rejection_reason=rejection_reason
    )


# =========================================================
# AUTO INITIALIZATION
# =========================================================

try:
    init_db()
except Exception as exc:
    print(
        f"[DB INIT ERROR] {exc}"
    )
