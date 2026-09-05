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
class SalesService:
    def __init__(self):
        pass
    # ========================================================
    # شماره فاکتور
    # ========================================================
    def generate_invoice_no(
        self,
        conn
    ):
        today = datetime.now().strftime(
            "%Y%m%d"
        )
        prefix = f"INV-{today}-"
        row = conn.execute(
            """
            SELECT invoice_no
            FROM invoices
            WHERE invoice_type = 'SALE'
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
        try:
            number = int(
                row["invoice_no"].split("-")[-1]
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
    # ثبت فروش
    # ========================================================
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
                "تعداد فروش باید بیشتر از صفر باشد."
            )
        if unit_price < 0:
            raise ValueError(
                "قیمت فروش نمی‌تواند منفی باشد."
            )
        conn = get_conn()
        try:
            # =================================================
            # مشتری
            # =================================================
            customer = conn.execute(
                """
                SELECT *
                FROM customers
                WHERE id = ?
                AND active = 1
                """,
                (
                    customer_id,
                )
            ).fetchone()
            if not customer:
                raise ValueError(
                    "مشتری پیدا نشد یا غیرفعال است."
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
            stock = float(
                product["stock"] or 0
            )
            if stock < quantity:
                raise ValueError(
                    f"موجودی کافی نیست. "
                    f"موجودی فعلی: {stock:g}"
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
            if discount < 0:
                discount = 0
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
            invoice_no = self.generate_invoice_no(
                conn
            )
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
                (?, 'SALE', ?, ?, ?, ?, ?, ?, 'CONFIRMED')
                """,
                (
                    invoice_no,
                    customer_id,
                    gross_amount,
                    discount,
                    tax,
                    payable_amount,
                    payment_method
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
                    payable_amount
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
                    product_id
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
                (?, 'SALE', ?, ?, 'SALE', ?)
                """,
                (
                    product_id,
                    -quantity,
                    purchase_cost,
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
                (?, ?, 'SALE', ?, ?)
                """,
                (
                    entry_no,
                    f"ثبت فروش {invoice_no}",
                    invoice_id,
                    datetime.now().strftime(
                        "%Y-%m-%d"
                    )
                )
            )
            journal_entry_id = cursor.lastrowid
            # =================================================
            # بدهکار
            # =================================================
            if payment_method == "cash":
                debit_account = "1101"
            elif payment_method == "bank":
                debit_account = "1102"
            else:
                debit_account = "1201"
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
                (?, ?, ?, ?, 0)
                """,
                (
                    journal_entry_id,
                    debit_account,
                    f"فروش {invoice_no}",
                    payable_amount
                )
            )
            # =================================================
            # فروش
            # =================================================
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
                (?, '4101', ?, 0, ?)
                """,
                (
                    journal_entry_id,
                    f"درآمد فروش {invoice_no}",
                    net_amount
                )
            )
            # =================================================
            # مالیات فروش
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
                    (?, '2101', ?, 0, ?)
                    """,
                    (
                        journal_entry_id,
                        f"مالیات فروش {invoice_no}",
                        tax
                    )
                )
            # =================================================
            # بهای تمام‌شده
            # =================================================
            cogs = int(
                round(
                    quantity *
                    purchase_cost
                )
            )
            if cogs > 0:
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
                    (?, '5101', ?, ?, 0)
                    """,
                    (
                        journal_entry_id,
                        f"بهای تمام‌شده {invoice_no}",
                        cogs
                    )
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
                    (?, '1401', ?, 0, ?)
                    """,
                    (
                        journal_entry_id,
                        f"خروج موجودی {invoice_no}",
                        cogs
                    )
                )
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
                "cogs": cogs
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
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
            payment_method=payment_method
        )
# ============================================================
# تابع سطح ماژول
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
        payment_method=payment_method
    )
