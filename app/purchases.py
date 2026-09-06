from .db import (
    db_transaction,
    get_supplier,
    get_product,
    create_invoice,
    add_invoice_item,
)

from .accounting import AccountingEngine


class PurchaseService:

    @staticmethod
    def create_purchase(
        supplier_id,
        items,
        payment_method="cash",
        discount=0,
        tax=0,
    ):
        if not items:
            raise ValueError(
                "حداقل یک قلم کالا لازم است."
            )

        if payment_method not in {
            "cash",
            "bank",
            "credit",
        }:
            raise ValueError(
                "روش پرداخت نامعتبر است."
            )

        supplier = get_supplier(
            supplier_id
        )

        if supplier is None:
            raise ValueError(
                "تأمین‌کننده پیدا نشد."
            )

        prepared_items = []

        subtotal = 0.0

        for item in items:

            product_id = int(
                item["product_id"]
            )

            quantity = float(
                item["quantity"]
            )

            if quantity <= 0:
                raise ValueError(
                    "تعداد باید بیشتر از صفر باشد."
                )

            product = get_product(
                product_id
            )

            if product is None:
                raise ValueError(
                    f"کالا با شناسه {product_id} "
                    "پیدا نشد."
                )

            unit_price = float(
                item.get(
                    "unit_price",
                    product["purchase_cost"] or 0,
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
                "purchase",
                supplier_id=supplier_id,
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
                    SET
                        stock = stock + ?,
                        purchase_cost = ?
                    WHERE id = ?
                    """,
                    (
                        item["quantity"],
                        item["unit_price"],
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
                        item["quantity"],
                        "purchase",
                        invoice_id,
                        f"خرید فاکتور {invoice_no}",
                    ),
                )

            journal_entry_id, journal_entry_no = (
                AccountingEngine.post_purchase(
                    conn,
                    invoice_id,
                    total,
                    payment_method,
                )
            )

            return {
                "invoice_id": invoice_id,
                "invoice_no": invoice_no,
                "total": total,
                "journal_entry_id": journal_entry_id,
                "journal_entry_no": journal_entry_no,
            }

    @staticmethod
    def get_purchase(invoice_id):
        from .db import get_invoice

        return get_invoice(invoice_id)

    @staticmethod
    def list_purchases(limit=20):
        from .db import list_invoices

        return list_invoices(
            "purchase",
            limit,
        )
