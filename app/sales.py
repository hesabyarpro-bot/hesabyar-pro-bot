import sqlite3
from datetime import datetime
from app.db import get_conn
# ============================================================
# ابزارهای داخلی
# ============================================================
def generate_invoice_no(conn):
    """
    ساخت شماره فاکتور فروش.
    مثال:
        INV-20260906-0001
    """
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"INV-{today}-"
    row = conn.execute(
        """
        SELECT invoice_no
        FROM invoices
        WHERE invoice_no LIKE ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (prefix + "%",)
    ).fetchone()
    if not row or not row["invoice_no"]:
        return prefix + "0001"
    try:
        last_number = int(
            row["invoice_no"].split("-")[-1]
        )
    except (ValueError, IndexError):
        last_number = 0
    return prefix + f"{last_number + 1:04d}"
def to_int(value):
    """
    تبدیل عدد فارسی/رشته‌ای به عدد صحیح.
    """
    if value is None:
        return 0
    text = str(value).strip()
    translation = str.maketrans(
        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
        "01234567890123456789"
    )
    text = text.translate(translation)
    text = (
        text
        .replace(",", "")
        .replace("٬", "")
        .replace(" ", "")
        .replace("٫", ".")
    )
    if not text:
        return 0
    try:
        return int(float(text))
    except ValueError:
        return 0
def normalize_payment_method(value):
    """
    تبدیل نام روش پرداخت به مقدار استاندارد.
    """
    if value is None:
        return "cash"
    text = str(value).strip().lower()
    mapping = {
        "نقد": "cash",
        "نقدی": "cash",
        "cash": "cash",
        "کارت": "bank",
        "بانک": "bank",
        "بانکی": "bank",
        "کارتخوان": "bank",
        "bank": "bank",
        "نسیه": "credit",
        "اعتباری": "credit",
        "credit": "credit",
    }
    return mapping.get(text, text)
def payment_account_code(payment_method):
    """
    کد حساب طرف بستانکار در فروش.
    """
    method = normalize_payment_method(payment_method)
    if method == "bank":
        return "1102"
    if method == "credit":
        return "1201"
    return "1101"
# ============================================================
# SalesService
# ============================================================
class SalesService:
    """
    سرویس ثبت فروش حساب‌یار پرو.
    وظایف:
    - ایجاد فاکتور فروش
    - ثبت اقلام فاکتور
    - کاهش موجودی
    - ثبت گردش انبار
    - ثبت سند حسابداری
    """
    def __init__(self):
        pass
    # --------------------------------------------------------
    # ثبت فروش
    # --------------------------------------------------------
    def create_sale(
        self,
        customer_id,
        product_id,
        quantity,
        unit_price,
        discount=0,
        tax=0,
        payment_method="cash"
    ):
        """
        ثبت کامل فروش.
        خروجی:
        {
            "success": True,
            "invoice_id": ...,
            "invoice_no": ...,
            "total_amount": ...,
            "payable_amount": ...
        }
        """
        quantity = float(quantity)
        unit_price = to_int(unit_price)
        discount = to_int(discount)
        tax = to_int(tax)
        if quantity <= 0:
            raise ValueError("تعداد کالا باید بیشتر از صفر باشد.")
        if unit_price < 0:
            raise ValueError("قیمت فروش نامعتبر است.")
        if discount < 0:
            discount = 0
        if tax < 0:
            tax = 0
        payment_method = normalize_payment_method(
            payment_method
        )
        conn = get_conn()
        try:
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
                (product_id,)
            ).fetchone()
            if not product:
                raise ValueError(
                    "کالای انتخاب‌شده پیدا نشد یا غیرفعال است."
                )
            current_stock = float(
                product["stock"] or 0
            )
            if current_stock < quantity:
                raise ValueError(
                    f"موجودی کافی نیست. موجودی فعلی: "
                    f"{current_stock:g}"
                )
            # =================================================
            # محاسبه
            # =================================================
            gross_amount = int(
                round(quantity * unit_price)
            )
            if discount > gross_amount:
                discount = gross_amount
            net_amount = gross_amount - discount
            payable_amount = net_amount + tax
            # =================================================
            # شماره فاکتور
            # =================================================
            invoice_no = generate_invoice_no(conn)
            # =================================================
            # فاکتور
            # =================================================
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
                    "SALE",
                    customer_id,
                    gross_amount,
                    discount,
                    tax,
                    payable_amount,
                    payment_method,
                    "CONFIRMED",
                )
            )
            invoice_id = cursor.lastrowid
            # =================================================
            # قلم فاکتور
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
                    payable_amount,
                )
            )
            # =================================================
            # کاهش موجودی
            # =================================================
            conn.execute(
                """
                UPDATE products
                SET stock = stock - ?
                WHERE id = ?
                """,
                (
                    quantity,
                    product_id,
                )
            )
            # =================================================
            # گردش انبار
            # =================================================
            purchase_cost = to_int(
                product["purchase_cost"]
            )
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
                (?, ?, ?, ?, ?, ?)
                """,
                (
                    product_id,
                    "SALE",
                    -quantity,
                    purchase_cost,
                    "SALE",
                    invoice_id,
                )
            )
            # =================================================
            # سند حسابداری
            # =================================================
            entry_no = f"JE-{invoice_no}"
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
                    f"ثبت فروش {invoice_no}",
                    "SALE",
                    invoice_id,
                    datetime.now().strftime("%Y-%m-%d"),
                )
            )
            journal_entry_id = cursor.lastrowid
            # -------------------------------------------------
            # بدهکار: صندوق / بانک / حساب دریافتنی
            # -------------------------------------------------
            debit_account = payment_account_code(
                payment_method
            )
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
                (?, ?, ?, ?, ?)
                """,
                (
                    journal_entry_id,
                    debit_account,
                    f"دریافت بابت فروش {invoice_no}",
                    payable_amount,
                    0,
                )
            )
            # -------------------------------------------------
            # بستانکار: فروش
            # -------------------------------------------------
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
                (?, ?, ?, ?, ?)
                """,
                (
                    journal_entry_id,
                    "4101",
                    f"فروش کالا - {invoice_no}",
                    0,
                    net_amount,
                )
            )
            # -------------------------------------------------
            # مالیات
            # -------------------------------------------------
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
                    (?, ?, ?, ?, ?)
                    """,
                    (
                        journal_entry_id,
                        "2101",
                        f"مالیات فروش - {invoice_no}",
                        0,
                        tax,
                    )
                )
            # =================================================
            # بهای تمام‌شده
            # =================================================
            cogs = int(
                round(quantity * purchase_cost)
            )
            if cogs > 0:
                # بدهکار بهای تمام‌شده
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
                    (?, ?, ?, ?, ?)
                    """,
                    (
                        journal_entry_id,
                        "5101",
                        f"بهای تمام‌شده فروش {invoice_no}",
                        cogs,
                        0,
                    )
                )
                # بستانکار موجودی کالا
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
                    (?, ?, ?, ?, ?)
                    """,
                    (
                        journal_entry_id,
                        "1401",
                        f"خروج موجودی بابت فروش {invoice_no}",
                        0,
                        cogs,
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
                "cogs": cogs,
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    # --------------------------------------------------------
    # نام جایگزین برای سازگاری با کدهای مختلف
    # --------------------------------------------------------
    def register_sale(
        self,
        customer_id,
        product_id,
        quantity,
        unit_price,
        discount=0,
        tax=0,
        payment_method="cash"
    ):
        return self.create_sale(
            customer_id=customer_id,
            product_id=product_id,
            quantity=quantity,
            unit_price=unit_price,
            discount=discount,
            tax=tax,
            payment_method=payment_method,
        )
    def add_sale(
        self,
        customer_id,
        product_id,
        quantity,
        unit_price,
        discount=0,
        tax=0,
        payment_method="cash"
    ):
        return self.create_sale(
            customer_id=customer_id,
            product_id=product_id,
            quantity=quantity,
            unit_price=unit_price,
            discount=discount,
            tax=tax,
            payment_method=payment_method,
        )
# ============================================================
# توابع سطح ماژول برای سازگاری
# ============================================================
def create_sale(
    customer_id,
    product_id,
    quantity,
    unit_price,
    discount=0,
    tax=0,
    payment_method="cash"
):
    service = SalesService()
    return service.create_sale(
        customer_id=customer_id,
        product_id=product_id,
        quantity=quantity,
        unit_price=unit_price,
        discount=discount,
        tax=tax,
        payment_method=payment_method,
    )
def register_sale(
    customer_id,
    product_id,
    quantity,
    unit_price,
    discount=0,
    tax=0,
    payment_method="cash"
):
    return create_sale(
        customer_id=customer_id,
        product_id=product_id,
        quantity=quantity,
        unit_price=unit_price,
        discount=discount,
        tax=tax,
        payment_method=payment_method,
    )
