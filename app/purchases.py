from datetime import date

from app.db import get_connection


class PurchaseService:

    # ========================================================
    # Purchase Invoice
    # ========================================================

    def create_purchase(
        self,
        supplier_id,
        items,
        discount=0,
        tax=0,
        payment_method="credit",
        notes=""
    ):

        if not items:
            raise ValueError(
                "حداقل یک قلم کالا باید ثبت شود."
            )

        conn = get_connection()

        try:

            # ------------------------------------------------
            # Validate supplier
            # ------------------------------------------------

            supplier = conn.execute("""
                SELECT *
                FROM suppliers
                WHERE id = ?
                  AND active = 1
            """, (
                supplier_id,
            )).fetchone()

            if not supplier:
                raise ValueError(
                    "تأمین‌کننده پیدا نشد."
                )

            # ------------------------------------------------
            # Calculate totals
            # ------------------------------------------------

            subtotal = 0
            validated_items = []

            for item in items:

                product_id = int(
                    item["product_id"]
                )

                quantity = float(
                    item["quantity"]
                )

                unit_price = int(
                    item["unit_price"]
                )

                item_discount = int(
                    item.get("discount", 0)
                )

                if quantity <= 0:
                    raise ValueError(
                        "تعداد کالا باید بیشتر از صفر باشد."
                    )

                if unit_price < 0:
                    raise ValueError(
                        "قیمت خرید نمی‌تواند منفی باشد."
                    )

                product = conn.execute("""
                    SELECT *
                    FROM products
                    WHERE id = ?
                      AND active = 1
                """, (
                    product_id,
                )).fetchone()

                if not product:
                    raise ValueError(
                        f"کالا با شناسه {product_id} پیدا نشد."
                    )

                gross = int(
                    quantity * unit_price
                )

                line_total = max(
                    0,
                    gross - item_discount
                )

                subtotal += line_total

                validated_items.append({
                    "product_id": product_id,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "discount": item_discount,
                    "tax": int(item.get("tax", 0)),
                    "line_total": line_total
                })

            total = (
                subtotal
                - int(discount)
                + int(tax)
            )

            if total < 0:
                total = 0

            # ------------------------------------------------
            # Invoice
            # ------------------------------------------------

            invoice_date = date.today().isoformat()

            cur = conn.execute("""
                INSERT INTO invoices
                (
                    invoice_type,
                    invoice_number,
                    supplier_id,
                    invoice_date,
                    subtotal,
                    discount,
                    tax,
                    total,
                    payment_method,
                    status,
                    notes,
                    created_at
                )
                VALUES
                (
                    'purchase',
                    NULL,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    'confirmed',
                    ?,
                    datetime('now')
                )
            """, (
                supplier_id,
                invoice_date,
                subtotal,
                int(discount),
                int(tax),
                total,
                payment_method,
                notes
            ))

            invoice_id = cur.lastrowid

            # ------------------------------------------------
            # Items + Stock
            # ------------------------------------------------

            for item in validated_items:

                conn.execute("""
                    INSERT INTO invoice_items
                    (
                        invoice_id,
                        product_id,
                        quantity,
                        unit_price,
                        discount,
                        tax,
                        line_total
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    invoice_id,
                    item["product_id"],
                    item["quantity"],
                    item["unit_price"],
                    item["discount"],
                    item["tax"],
                    item["line_total"]
                ))

                # Increase stock
                conn.execute("""
                    UPDATE products
                    SET stock = COALESCE(stock, 0) + ?,
                        purchase_cost = ?
                    WHERE id = ?
                """, (
                    item["quantity"],
                    item["unit_price"],
                    item["product_id"]
                ))

                # Stock movement
                conn.execute("""
                    INSERT INTO stock_movements
                    (
                        product_id,
                        movement_type,
                        quantity,
                        unit_cost,
                        reference_type,
                        reference_id,
                        movement_date,
                        notes
                    )
                    VALUES (?, 'purchase', ?, ?, 'purchase', ?, ?, ?)
                """, (
                    item["product_id"],
                    item["quantity"],
                    item["unit_price"],
                    invoice_id,
                    invoice_date,
                    "ثبت خرید"
                ))

            # ------------------------------------------------
            # Accounting Entry
            # ------------------------------------------------

            journal_cur = conn.execute("""
                INSERT INTO journal_entries
                (
                    entry_number,
                    entry_date,
                    description,
                    reference_type,
                    reference_id,
                    status,
                    created_at
                )
                VALUES (?, ?, ?, 'purchase', ?, 'posted', datetime('now'))
            """, (
                f"PUR-{invoice_id}",
                invoice_date,
                f"ثبت فاکتور خرید شماره {invoice_id}",
                invoice_id
            ))

            journal_entry_id = journal_cur.lastrowid

            # Inventory / Purchase debit
            conn.execute("""
                INSERT INTO journal_lines
                (
                    journal_entry_id,
                    account_code,
                    account_name,
                    debit,
                    credit
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                journal_entry_id,
                "1401",
                "موجودی کالا",
                total,
                0
            ))

            # Credit side
            if payment_method == "cash":

                credit_code = "1101"
                credit_name = "صندوق"

            elif payment_method == "bank":

                credit_code = "1102"
                credit_name = "بانک"

            else:

                credit_code = "2101"
                credit_name = "حساب‌های پرداختنی"

            conn.execute("""
                INSERT INTO journal_lines
                (
                    journal_entry_id,
                    account_code,
                    account_name,
                    debit,
                    credit
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                journal_entry_id,
                credit_code,
                credit_name,
                0,
                total
            ))

            conn.commit()

            return {
                "invoice_id": invoice_id,
                "supplier_id": supplier_id,
                "subtotal": subtotal,
                "discount": int(discount),
                "tax": int(tax),
                "total": total,
                "payment_method": payment_method,
                "items": validated_items
            }

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()


# ============================================================
# Helpers
# ============================================================

def get_purchase(invoice_id):

    conn = get_connection()

    try:

        invoice = conn.execute("""
            SELECT
                i.*,
                s.name AS supplier_name,
                s.phone AS supplier_phone
            FROM invoices i
            LEFT JOIN suppliers s
                ON s.id = i.supplier_id
            WHERE i.id = ?
              AND i.invoice_type = 'purchase'
        """, (
            invoice_id,
        )).fetchone()

        if not invoice:
            return None

        items = conn.execute("""
            SELECT
                ii.*,
                p.name AS product_name,
                p.unit
            FROM invoice_items ii
            JOIN products p
                ON p.id = ii.product_id
            WHERE ii.invoice_id = ?
            ORDER BY ii.id
        """, (
            invoice_id,
        )).fetchall()

        return {
            "invoice": invoice,
            "items": items
        }

    finally:
        conn.close()


def list_purchases(limit=20):

    conn = get_connection()

    try:

        return conn.execute("""
            SELECT
                i.*,
                s.name AS supplier_name
            FROM invoices i
            LEFT JOIN suppliers s
                ON s.id = i.supplier_id
            WHERE i.invoice_type = 'purchase'
            ORDER BY i.id DESC
            LIMIT ?
        """, (
            limit,
        )).fetchall()

    finally:
        conn.close()
