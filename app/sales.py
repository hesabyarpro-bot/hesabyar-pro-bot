from datetime import date, datetime

from app.db import get_connection
from app.accounting import create_sale_journal


def create_customer(name, phone=None, national_id=None):
    if not name or not name.strip():
        raise ValueError("نام مشتری الزامی است.")

    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            INSERT INTO customers (
                name,
                phone,
                national_id
            )
            VALUES (?, ?, ?)
            """,
            (
                name.strip(),
                phone,
                national_id,
            ),
        )

        connection.commit()
        return cursor.lastrowid

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def create_product(
    name,
    code=None,
    unit="عدد",
    purchase_cost=0,
    sale_price=0,
):
    if not name or not name.strip():
        raise ValueError("نام کالا الزامی است.")

    purchase_cost = float(purchase_cost or 0)
    sale_price = float(sale_price or 0)

    if purchase_cost < 0 or sale_price < 0:
        raise ValueError("قیمت نمی‌تواند منفی باشد.")

    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            INSERT INTO products (
                code,
                name,
                unit,
                purchase_cost,
                sale_price,
                stock
            )
            VALUES (?, ?, ?, ?, ?, 0)
            """,
            (
                code,
                name.strip(),
                unit or "عدد",
                purchase_cost,
                sale_price,
            ),
        )

        connection.commit()
        return cursor.lastrowid

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_customer_by_name(name):
    return _fetch_one(
        """
        SELECT *
        FROM customers
        WHERE name = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (name,),
    )


def get_product_by_name(name):
    return _fetch_one(
        """
        SELECT *
        FROM products
        WHERE name = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (name,),
    )


def get_product_by_id(product_id):
    return _fetch_one(
        """
        SELECT *
        FROM products
        WHERE id = ?
        """,
        (product_id,),
    )


def _fetch_one(query, params=()):
    connection = get_connection()

    try:
        cursor = connection.execute(query, params)
        return cursor.fetchone()

    finally:
        connection.close()


def _generate_invoice_number(connection):
    cursor = connection.execute(
        """
        SELECT id
        FROM invoices
        ORDER BY id DESC
        LIMIT 1
        """
    )

    row = cursor.fetchone()

    next_id = 1 if row is None else int(row["id"]) + 1

    return f"INV-{next_id:06d}"


def _generate_entry_number(connection):
    cursor = connection.execute(
        """
        SELECT id
        FROM journal_entries
        ORDER BY id DESC
        LIMIT 1
        """
    )

    row = cursor.fetchone()

    next_id = 1 if row is None else int(row["id"]) + 1

    return f"JE-{next_id:06d}"


def create_sale(
    customer_id,
    product_id,
    quantity,
    unit_price,
    discount=0,
    tax=0,
    payment_method="cash",
    invoice_date=None,
):
    """
    ثبت کامل فروش:

    1. فاکتور
    2. قلم فاکتور
    3. کاهش موجودی
    4. گردش انبار
    5. سند حسابداری

    همه عملیات در یک Transaction انجام می‌شوند.
    """

    quantity = float(quantity)
    unit_price = float(unit_price)
    discount = float(discount or 0)
    tax = float(tax or 0)

    if quantity <= 0:
        raise ValueError("تعداد باید بیشتر از صفر باشد.")

    if unit_price < 0:
        raise ValueError("قیمت نمی‌تواند منفی باشد.")

    if discount < 0:
        raise ValueError("تخفیف نمی‌تواند منفی باشد.")

    if tax < 0:
        raise ValueError("مالیات نمی‌تواند منفی باشد.")

    valid_payment_methods = {
        "cash",
        "bank",
        "credit",
    }

    if payment_method not in valid_payment_methods:
        raise ValueError(
            "روش پرداخت باید cash، bank یا credit باشد."
        )

    invoice_date = (
        invoice_date
        or date.today().isoformat()
    )

    connection = get_connection()

    try:
        cursor = connection.cursor()

        # -------------------------
        # بررسی مشتری
        # -------------------------

        cursor.execute(
            """
            SELECT *
            FROM customers
            WHERE id = ?
            """,
            (customer_id,),
        )

        customer = cursor.fetchone()

        if customer is None:
            raise ValueError("مشتری پیدا نشد.")

        # -------------------------
        # بررسی کالا
        # -------------------------

        cursor.execute(
            """
            SELECT *
            FROM products
            WHERE id = ?
            """,
            (product_id,),
        )

        product = cursor.fetchone()

        if product is None:
            raise ValueError("کالا پیدا نشد.")

        current_stock = float(
            product["stock"] or 0
        )

        if current_stock < quantity:
            raise ValueError(
                f"موجودی کافی نیست. "
                f"موجودی فعلی: {current_stock}"
            )

        # -------------------------
        # محاسبه فاکتور
        # -------------------------

        subtotal = quantity * unit_price

        taxable_amount = max(
            subtotal - discount,
            0,
        )

        total = (
            taxable_amount
            + tax
        )

        # -------------------------
        # شماره فاکتور
        # -------------------------

        invoice_number = _generate_invoice_number(
            connection
        )

        # -------------------------
        # ایجاد فاکتور
        # -------------------------

        cursor.execute(
            """
            INSERT INTO invoices (
                invoice_number,
                customer_id,
                invoice_date,
                subtotal,
                discount,
                tax,
                total,
                payment_method,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                invoice_number,
                customer_id,
                invoice_date,
                subtotal,
                discount,
                tax,
                total,
                payment_method,
                "confirmed",
            ),
        )

        invoice_id = cursor.lastrowid

        # -------------------------
        # ایجاد قلم فاکتور
        # -------------------------

        cursor.execute(
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
                product_id,
                quantity,
                unit_price,
                discount,
                tax,
                total,
            ),
        )

        # -------------------------
        # کاهش موجودی
        # -------------------------

        new_stock = (
            current_stock - quantity
        )

        cursor.execute(
            """
            UPDATE products
            SET stock = ?
            WHERE id = ?
            """,
            (
                new_stock,
                product_id,
            ),
        )

        # -------------------------
        # گردش انبار
        # -------------------------

        cursor.execute(
            """
            INSERT INTO stock_movements (
                product_id,
                movement_type,
                quantity,
                unit_cost,
                reference_type,
                reference_id,
                movement_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                product_id,
                "sale",
                -quantity,
                float(
                    product["purchase_cost"] or 0
                ),
                "sale",
                invoice_id,
                invoice_date,
            ),
        )

        # -------------------------
        # سند حسابداری
        # -------------------------

        entry_number = _generate_entry_number(
            connection
        )

        if payment_method == "cash":
            debit_account = "1101"

        elif payment_method == "bank":
            debit_account = "1102"

        else:
            debit_account = "1201"

        # سند فروش
        cursor.execute(
            """
            INSERT INTO journal_entries (
                entry_number,
                entry_date,
                description,
                reference_type,
                reference_id
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                entry_number,
                invoice_date,
                f"ثبت فروش فاکتور {invoice_number}",
                "sale",
                invoice_id,
            ),
        )

        journal_entry_id = cursor.lastrowid

        # بدهکار
        cursor.execute(
            """
            INSERT INTO journal_lines (
                journal_entry_id,
                account_code,
                description,
                debit,
                credit
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                journal_entry_id,
                debit_account,
                f"دریافت بابت فاکتور {invoice_number}",
                total,
                0,
            ),
        )

        # بستانکار فروش
        cursor.execute(
            """
            INSERT INTO journal_lines (
                journal_entry_id,
                account_code,
                description,
                debit,
                credit
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                journal_entry_id,
                "4101",
                f"فروش فاکتور {invoice_number}",
                0,
                taxable_amount,
            ),
        )

        # بستانکار مالیات
        if tax > 0:
            cursor.execute(
                """
                INSERT INTO journal_lines (
                    journal_entry_id,
                    account_code,
                    description,
                    debit,
                    credit
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    journal_entry_id,
                    "2101",
                    f"مالیات فاکتور {invoice_number}",
                    0,
                    tax,
                ),
            )

        # -------------------------
        # کنترل توازن سند
        # -------------------------

        cursor.execute(
            """
            SELECT
                COALESCE(SUM(debit), 0) AS debit,
                COALESCE(SUM(credit), 0) AS credit
            FROM journal_lines
            WHERE journal_entry_id = ?
            """,
            (journal_entry_id,),
        )

        totals = cursor.fetchone()

        debit_total = float(
            totals["debit"]
        )

        credit_total = float(
            totals["credit"]
        )

        if round(debit_total, 2) != round(
            credit_total, 2
        ):
            raise ValueError(
                "سند حسابداری تراز نیست."
            )

        connection.commit()

        return {
            "invoice_id": invoice_id,
            "invoice_number": invoice_number,
            "journal_entry_id": journal_entry_id,
            "total": total,
            "stock_remaining": new_stock,
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
