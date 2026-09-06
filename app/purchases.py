from app.db import (
    db_transaction,
    get_supplier,
    get_product,
    get_invoice,
    list_invoices,
    now,
)


class PurchaseService:

    @staticmethod
    def create_purchase(
        supplier_id,
        items,
        discount=0,
        tax=0,
        payment_method="credit",
        notes="",
    ):
        if not items:
            raise ValueError("حداقل یک قلم کالا لازم است.")

        supplier = get_supplier(supplier_id)

        if not supplier or supplier["active"] != 1:
            raise ValueError("تأمین‌کننده معتبر نیست.")

        subtotal = 0
        prepared_items = []

        for item in items:
            product_id = int(item["product_id"])
            quantity = float(item["quantity"])
            unit_price = float(item["unit_price"])
            item_discount = float(item.get("discount", 0))

            if quantity <= 0:
                raise ValueError("تعداد کالا باید بیشتر از صفر باشد.")

            if unit_price < 0:
                raise ValueError("قیمت کالا نمی‌تواند منفی باشد.")

            product = get_product(product_id)

            if not product or product["active"] != 1:
                raise ValueError(
                    f"کالای شماره {product_id} معتبر نیست."
                )

            line_gross = quantity * unit_price
            line_total = line_gross - item_discount

            if line_total < 0:
                raise ValueError(
                    "تخفیف یک قلم نمی‌تواند بیشتر از مبلغ آن قلم باشد."
                )

            subtotal += line_total

            prepared_items.append(
                {
                    "product_id": product_id,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "discount": item_discount,
                    "tax": float(item.get("tax", 0)),
                    "total": line_total,
                }
            )

        discount = float(discount or 0)
        tax = float(tax or 0)

        total = subtotal - discount + tax

        if total < 0:
            raise ValueError("مبلغ نهایی نمی‌تواند منفی باشد.")

        with db_transaction() as conn:

            cursor = conn.execute(
                """
                INSERT INTO invoices
                (
                    invoice_type,
                    supplier_id,
                    invoice_date,
                    subtotal,
                    discount,
                    tax,
                    total,
                    payment_method,
                    notes,
                    created_at
                )
                VALUES
                (
                    'purchase',
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?
                )
                """,
                (
                    supplier_id,
                    now(),
                    subtotal,
                    discount,
                    tax,
                    total,
                    payment_method,
                    notes,
                    now(),
                ),
            )

            invoice_id = cursor.lastrowid

            for item in prepared_items:

                conn.execute(
                    """
                    INSERT INTO invoice_items
                    (
                        invoice_id,
                        product_id,
                        quantity,
                        unit_price,
                        discount,
                        tax,
                        total
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
                        item["total"],
                    ),
                )

                # افزایش موجودی
                conn.execute(
                    """
                    UPDATE products
                    SET stock = stock + ?,
                        purchase_cost = ?
                    WHERE id=?
                    """,
                    (
                        item["quantity"],
                        item["unit_price"],
                        item["product_id"],
                    ),
                )

                conn.execute(
                    """
                    INSERT INTO stock_movements
                    (
                        product_id,
                        invoice_id,
                        movement_type,
                        quantity,
                        unit_cost,
                        movement_date,
                        notes
                    )
                    VALUES (?, ?, 'purchase', ?, ?, ?, ?)
                    """,
                    (
                        item["product_id"],
                        invoice_id,
                        item["quantity"],
                        item["unit_price"],
                        now(),
                        f"خرید فاکتور {invoice_id}",
                    ),
                )

            # سند حسابداری
            journal_cursor = conn.execute(
                """
                INSERT INTO journal_entries
                (
                    entry_date,
                    description,
                    reference_type,
                    reference_id,
                    created_at
                )
                VALUES (?, ?, 'purchase', ?, ?)
                """,
                (
                    now(),
                    f"ثبت خرید فاکتور {invoice_id}",
                    invoice_id,
                    now(),
                ),
            )

            journal_id = journal_cursor.lastrowid

            # موجودی کالا
            conn.execute(
                """
                INSERT INTO journal_lines
                (
                    journal_entry_id,
                    account_code,
                    account_name,
                    debit,
                    credit
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    journal_id,
                    "1401",
                    "موجودی کالا",
                    total,
                    0,
                ),
            )

            if payment_method == "cash":
                account_code = "1101"
                account_name = "صندوق"

            elif payment_method == "bank":
                account_code = "1102"
                account_name = "بانک"

            else:
                account_code = "2101"
                account_name = "حساب‌های پرداختنی"

            conn.execute(
                """
                INSERT INTO journal_lines
                (
                    journal_entry_id,
                    account_code,
                    account_name,
                    debit,
                    credit
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    journal_id,
                    account_code,
                    account_name,
                    0,
                    total,
                ),
            )

        return {
            "invoice_id": invoice_id,
            "supplier_id": supplier_id,
            "supplier_name": supplier["name"],
            "subtotal": subtotal,
            "discount": discount,
            "tax": tax,
            "total": total,
            "payment_method": payment_method,
        }

    @staticmethod
    def get_purchase(invoice_id):
        result = get_invoice(invoice_id)

        if not result["invoice"]:
            return None

        if result["invoice"]["invoice_type"] != "purchase":
            return None

        return result

    @staticmethod
    def list_purchases(limit=20):
        return list_invoices(
            invoice_type="purchase",
            limit=limit,
        )
