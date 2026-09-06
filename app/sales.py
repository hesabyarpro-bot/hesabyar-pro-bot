from .db import (
    db_transaction,
    get_product,
    get_customer,
    create_invoice,
    add_invoice_item,
)

from .accounting import AccountingEngine


class SalesService:
    """
    سرویس ثبت فروش.

    نکته:
    بهای تمام‌شده فعلاً از purchase_cost جاری کالا استفاده می‌شود.
    FIFO و میانگین موزون در این نسخه هنوز پیاده‌سازی نشده‌اند.
    """

    @staticmethod
    def create_sale(
        customer_id,
        items,
        payment_method="cash",
        discount=0,
        tax=0,
    ):
        if not items:
            raise ValueError("حداقل یک قلم کالا لازم است.")

        if payment_method not in {
            "cash",
            "bank",
            "credit",
        }:
            raise ValueError("روش پرداخت نامعتبر است.")

        customer = get_customer(customer_id)

        if customer is None:
            raise ValueError("مشتری پیدا نشد.")

        prepared_items = []

        subtotal = 0.0
        cogs = 0.0

        for item in items:
            product_id = int(item["product_id"])
            quantity = float(item["quantity"])

            if quantity <= 0:
                raise ValueError("تعداد باید بیشتر از صفر باشد.")

            product = get_product(product_id)

            if product is None:
                raise ValueError(
                    f"کالا با شناسه {product_id} پیدا نشد."
                )

            stock = float(product["stock"])

            if stock < quantity:
                raise ValueError(
                    f"موجودی «{product['name']}» کافی نیست. "
                    f"موجودی فعلی: {stock}"
                )

            unit_price = float(
                item.get(
                    "unit_price",
                    product["sale_price"],
                )
            )

            line_discount = float(
                item.get("discount", 0)
            )

            line_tax = float(
                item.get("tax", 0)
            )

            line_total = max(
                0,
                quantity * unit_price
                - line_discount
                + line_tax,
            )

            subtotal += line_total

            purchase_cost = float(
                product["purchase_cost"] or 0
            )

            cogs += quantity * purchase_cost

            prepared_items.append(
                {
                    "product": product,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "discount": line_discount,
                    "tax": line_tax,
                    "line_total": line_total,
                }
            )

        total = max(
            0,
            subtotal
            - float(discount)
            + float(tax),
        )

        with db_transaction() as conn:

            invoice_id, invoice_no = create_invoice(
                conn,
                "sale",
                customer_id=customer_id,
                total=total,
                discount=discount,
                tax=tax,
            )

            for item in prepared_items:

                product = item["product"]

                add_invoice_item(
                    conn,
                    invoice_id,
                    product["id"],
                    item["quantity"],
                    item["unit_price"],
                    item["discount"],
                    item["tax"],
                    item["line_total"],
                )

                conn.execute(
                    """
                    UPDATE products
                    SET stock = stock - ?
                    WHERE id = ?
                    """,
                    (
                        item["quantity"],
                        product["id"],
                    ),
                )

                conn.execute(
                    """
                    INSERT INTO stock_movements
                    (
                        product_id,
                        quantity,
                        movement_type,
                        reference_id,
                        note
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        product["id"],
                        -item["quantity"],
                        "sale",
                        invoice_id,
                        f"فروش فاکتور {invoice_no}",
                    ),
                )

            journal_entry_id, journal_entry_no = (
                AccountingEngine.post_sale(
                    conn,
                    invoice_id,
                    total,
                    cogs,
                    payment_method,
                )
            )

            return {
                "invoice_id": invoice_id,
                "invoice_no": invoice_no,
                "total": total,
                "cogs": cogs,
                "journal_entry_id": journal_entry_id,
                "journal_entry_no": journal_entry_no,
            }

    @staticmethod
    def get_sale(invoice_id):
        from .db import get_invoice

        return get_invoice(invoice_id)

    @staticmethod
    def list_sales(limit=20):
        from .db import list_invoices

        return list_invoices(
            "sale",
            limit,
        )
