from dataclasses import dataclass


@dataclass(frozen=True)
class Account:
    code: str
    name: str
    nature: str


ACCOUNTS = {
    "1101": Account(
        code="1101",
        name="صندوق",
        nature="debit",
    ),

    "1102": Account(
        code="1102",
        name="بانک",
        nature="debit",
    ),

    "1201": Account(
        code="1201",
        name="حساب‌های دریافتنی",
        nature="debit",
    ),

    "1401": Account(
        code="1401",
        name="موجودی کالا",
        nature="debit",
    ),

    "2101": Account(
        code="2101",
        name="حساب‌های پرداختنی",
        nature="credit",
    ),

    "4101": Account(
        code="4101",
        name="فروش",
        nature="credit",
    ),

    "5101": Account(
        code="5101",
        name="بهای تمام‌شده کالای فروش‌رفته",
        nature="debit",
    ),
}


def payment_account(method: str, sale: bool = True) -> str:
    method = (method or "").lower().strip()

    if method == "cash":
        return "1101"

    if method == "bank":
        return "1102"

    if sale:
        return "1201"

    return "2101"


def purchase_payment_account(method: str) -> str:
    method = (method or "").lower().strip()

    if method == "cash":
        return "1101"

    if method == "bank":
        return "1102"

    return "2101"


def sale_entry_lines(
    total: int,
    cost: int,
    payment_method: str,
):
    payment_account_code = payment_account(
        payment_method,
        sale=True,
    )

    lines = [
        (
            payment_account_code,
            total,
            0,
        ),
        (
            "4101",
            0,
            total,
        ),
    ]

    if cost > 0:
        lines.extend(
            [
                (
                    "5101",
                    cost,
                    0,
                ),
                (
                    "1401",
                    0,
                    cost,
                ),
            ]
        )

    return lines


def purchase_entry_lines(
    total: int,
    payment_method: str,
):
    payment_account_code = purchase_payment_account(
        payment_method
    )

    return [
        (
            "1401",
            total,
            0,
        ),
        (
            payment_account_code,
            0,
            total,
        ),
    ]
