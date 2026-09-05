import sqlite3
from datetime import datetime
from app.db import get_conn
# ============================================================
# ابزارها
# ============================================================
def normalize_number(value):
    if value is None:
        return "0"
    text = str(value).strip()
    translation = str.maketrans(
        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
        "01234567890123456789"
    )
    return (
        text
        .translate(translation)
        .replace(",", "")
        .replace("٬", "")
        .replace(" ", "")
        .replace("٫", ".")
    )
def to_int(value):
    text = normalize_number(value)
    if not text:
        return 0
    return int(float(text))
def normalize_payment_method(value):
    if value is None:
        return "cash"
    text = str(value).strip().lower()
    mapping = {
        "1": "cash",
        "نقد": "cash",
        "نقدی": "cash",
        "cash": "cash",
        "2": "bank",
        "بانک": "bank",
        "بانکی": "bank",
        "کارت": "bank",
        "کارتخوان": "bank",
        "bank": "bank",
        "3": "credit",
        "نسیه": "credit",
        "اعتباری": "credit",
        "credit": "credit",
    }
    return mapping.get(
        text,
        text
    )
def payment_method_fa(value):
    mapping = {
        "cash": "نقدی",
        "bank": "بانکی",
        "credit": "نسیه",
    }
    return mapping.get(
        value,
        value
    )
# ============================================================
# PurchaseService
# ============================================================
class PurchaseService:
    def __init__(self):
        pass
    # ========================================================
    # شماره فاکتور
    # ========================================================
    def generate_purchase_no(
        self,
        conn
    ):
        today = datetime.now().strftime(
            "%Y%m%d"
        )
        prefix = f"PUR-{today}-"
        row = conn.execute(
            """
            SELECT invoice_no
            FROM invoices
            WHERE invoice_type = 'PURCHASE'
            AND invoice_no LIKE ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (
                prefix + "%"
            )
        ).fetchone()
        if not row:
            return prefix + "0001"
        last = row["invoice_no"]
        try:
            number = int(
                last.split("-")[-1]
            )
        except (
            ValueError,
            IndexError
        ):
            number = 0
        return (
            prefix +
            f"{number + 1:04d}"
        )
    # ========================================================
    # ثبت خرید
    # ========================================================
    def create_purchase(
        self,
        supplier_id,
        product_id,
        quantity,
        unit_price,
        discount=0,
        tax=0,
        payment_method="cash"
    ):
        quantity = float(
            normalize_number(quantity)
        )
        unit_price = to_int(
            unit_price
        )
        discount = to_int(
            discount
        )
        tax = to_int(
            tax
        )
        payment_method = normalize_payment_method(
            payment_method
        )
        if quantity <= 0:
            raise ValueError(
                "تعداد خرید باید بیشتر از صفر باشد."
            )
        if unit_price < 0:
            raise ValueError(
                "قیمت خرید نمی‌تواند منفی باشد."
            )
        if discount < 0:
            discount = 0
        if tax < 0:
            tax = 0
        conn = get_conn()
        try:
            # =================================================
            # تأمین‌کننده
            # =================================================
            supplier = conn.execute(
                """
                SELECT *
                FROM suppliers
                WHERE id = ?
                AND active = 1
                """,
                (
                    supplier_id,
                )
            ).fetchone()
            if not supplier:
                raise ValueError(
                    "تأمین‌کننده پیدا نشد یا غیرفعال است."
                )
            # =================================================
            # کالا
            # =================================================
            product = conn.execute(
                """
                SELECT *
                FROM products
                WHERE id = ?
                AND active = 1
                """,
                (
                    product_id,
                )
            ).fetchone()
            if not product:
                raise ValueError(
                    "کالا پیدا نشد یا غیرفعال است."
                )
            # =================================================
            # محاسبات
            # =================================================
            gross_amount = int(
                round(
                    quantity *
                    unit_price
                )
            )
            if discount > gross_amount:
                discount = gross_amount
            net_amount = (
                gross_amount -
                discount
            )
            payable_amount = (
                net_amount +
                tax
            )
            # =================================================
            # شماره فاکتور
            # =================================================
            invoice_no = self.generate_purchase_no(
                conn
            )
            # =================================================
            # فاکتور خرید
            # =================================================
            cursor = conn.execute(
                """
                INSERT INTO invoices
                (
                    invoice_no,
                    invoice_type,
                    supplier_id,
                    total_amount,
                    discount_amount,
                    tax_amount,
                    payable_amount,
                    payment_method,
                    status
                )
                VALUES
                (?, 'PURCHASE', ?, ?, ?, ?, ?, ?, 'CONFIRMED')
                """,
                (
                    invoice_no,
                    supplier_id,
                    gross_amount,
                    discount,
                    tax,
                    payable_amount,
                    payment_method
                )
            )
            invoice_id = cursor.lastrowid
            # =================================================
            # قلم خرید
            # =================================================
            conn.execute(
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
                    discount,
                    tax,
                    payable_amount
                )
            )
            # =================================================
            # محاسبه بهای جدید
            # =================================================
            old_stock = float(
                product["stock"] or 0
            )
            old_cost = to_int(
                product["purchase_cost"]
            )
            new_stock = (
                old_stock +
                quantity
            )
            if new_stock > 0:
                weighted_cost = int(
                    round(
                        (
                            (
                                old_stock *
                                old_cost
                            )
                            +
                            (
                                quantity *
                                unit_price
                            )
                        )
                        /
                        new_stock
                    )
                )
            else:
                weighted_cost = unit_price
            # =================================================
            # افزایش موجودی
            # =================================================
            conn.execute(
                """
                UPDATE products
                SET
                    stock = stock + ?,
                    purchase_cost = ?
                WHERE id = ?
                """,
                (
                    quantity,
                    weighted_cost,
                    product_id
                )
            )
            # =================================================
            # گردش انبار
            # =================================================
            conn.execute(
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
                (?, 'PURCHASE', ?, ?, 'PURCHASE', ?)
                """,
                (
                    product_id,
                    quantity,
                    unit_price,
                    invoice_id
                )
            )
            # =================================================
            # سند حسابداری
            # =================================================
            entry_no = (
                f"JE-{invoice_no}"
            )
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
                (?, ?, 'PURCHASE', ?, ?)
                """,
                (
                    entry_no,
                    f"ثبت خرید {invoice_no}",
                    invoice_id,
                    datetime.now().strftime(
                        "%Y-%m-%d"
                    )
                )
            )
            journal_entry_id = cursor.lastrowid
            # =================================================
            # بدهکار: موجودی کالا
            # =================================================
            inventory_amount = net_amount
            conn.execute(
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
                (?, '1401', ?, ?, 0)
                """,
                (
                    journal_entry_id,
                    f"خرید کالا {invoice_no}",
                    inventory_amount
                )
            )
            # =================================================
            # مالیات خرید
            # =================================================
            if tax > 0:
                conn.execute(
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
                    (?, '1301', ?, ?, 0)
                    """,
                    (
                        journal_entry_id,
                        f"مالیات خرید {invoice_no}",
                        tax
                    )
                )
            # =================================================
            # بستانکار
            # =================================================
            if payment_method == "cash":
                credit_account = "1101"
            elif payment_method == "bank":
                credit_account = "1102"
            else:
                credit_account = "2101"
            conn.execute(
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
                (?, ?, ?, 0, ?)
                """,
                (
                    journal_entry_id,
                    credit_account,
                    f"پرداخت بابت خرید {invoice_no}",
                    payable_amount
                )
            )
            # =================================================
            # Commit
            # =================================================
            conn.commit()
            return {
                "success": True,
                "invoice_id": invoice_id,
                "invoice_no": invoice_no,
                "total_amount": gross_amount,
                "discount_amount": discount,
                "tax_amount": tax,
                "payable_amount": payable_amount,
                "payment_method": payment_method,
                "old_stock": old_stock,
                "new_stock": new_stock,
                "weighted_cost": weighted_cost
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    # ========================================================
    # alias
    # ========================================================
    def register_purchase(
        self,
        supplier_id,
        product_id,
        quantity,
        unit_price,
        discount=0,
        tax=0,
        payment_method="cash"
    ):
        return self.create_purchase(
            supplier_id=supplier_id,
            product_id=product_id,
            quantity=quantity,
            unit_price=unit_price,
            discount=discount,
            tax=tax,
            payment_method=payment_method
        )
# ============================================================
# تابع سطح ماژول
# ============================================================
def create_purchase(
    supplier_id,
    product_id,
    quantity,
    unit_price,
    discount=0,
    tax=0,
    payment_method="cash"
):
    service = PurchaseService()
    return service.create_purchase(
        supplier_id=supplier_id,
        product_id=product_id,
        quantity=quantity,
        unit_price=unit_price,
        discount=discount,
        tax=tax,
        payment_method=payment_method
    )
