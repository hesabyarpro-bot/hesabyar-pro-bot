from datetime import date

from app.db import get_connection


def create_journal_entry(
    entry_number,
    entry_date,
    description,
    reference_type=None,
    reference_id=None,
    lines=None,
):
    """
    ایجاد یک سند حسابداری و خطوط بدهکار/بستانکار.

    lines:
    [
        {
            "account_code": "1101",
            "description": "صندوق",
            "debit": 1000000,
            "credit": 0
        },
        ...
    ]
    """

    if not lines:
        raise ValueError("حداقل یک خط حسابداری لازم است.")

    total_debit = sum(float(line.get("debit", 0) or 0) for line in lines)
    total_credit = sum(float(line.get("credit", 0) or 0) for line in lines)

    # کنترل توازن سند
    if round(total_debit, 2) != round(total_credit, 2):
        raise ValueError(
            f"سند تراز نیست. بدهکار={total_debit} "
            f"بستانکار={total_credit}"
        )

    connection = get_connection()

    try:
        cursor = connection.cursor()

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
                entry_date,
                description,
                reference_type,
                reference_id,
            ),
        )

        journal_entry_id = cursor.lastrowid

        for line in lines:
            debit = float(line.get("debit", 0) or 0)
            credit = float(line.get("credit", 0) or 0)

            if debit < 0 or credit < 0:
                raise ValueError(
                    "مبلغ بدهکار یا بستانکار نمی‌تواند منفی باشد."
                )

            if debit > 0 and credit > 0:
                raise ValueError(
                    "یک خط حسابداری نباید همزمان بدهکار و بستانکار باشد."
                )

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
                    line["account_code"],
                    line.get("description", ""),
                    debit,
                    credit,
                ),
            )

        connection.commit()

        return journal_entry_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def create_sale_journal(
    invoice_id,
    invoice_number,
    invoice_date,
    total,
    payment_method,
):
    """
    ثبت سند حسابداری فروش.

    حساب‌ها:
    1101 = صندوق
    1102 = بانک
    1201 = حساب‌های دریافتنی
    4101 = فروش
    """

    payment_accounts = {
        "cash": "1101",
        "bank": "1102",
        "credit": "1201",
    }

    account_code = payment_accounts.get(payment_method)

    if not account_code:
        raise ValueError(
            "روش پرداخت نامعتبر است."
        )

    lines = [
        {
            "account_code": account_code,
            "description": f"دریافت بابت فاکتور فروش {invoice_number}",
            "debit": float(total),
            "credit": 0,
        },
        {
            "account_code": "4101",
            "description": f"فروش فاکتور {invoice_number}",
            "debit": 0,
            "credit": float(total),
        },
    ]

    return create_journal_entry(
        entry_number=f"SALE-{invoice_id}",
        entry_date=invoice_date or str(date.today()),
        description=f"ثبت فروش فاکتور {invoice_number}",
        reference_type="sale",
        reference_id=invoice_id,
        lines=lines,
    )
