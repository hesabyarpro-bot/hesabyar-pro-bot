from .db import post_journal


class AccountingEngine:
    ACCOUNTS = {
        "cash": ("1101", "صندوق"),
        "bank": ("1102", "بانک"),
        "receivable": ("1201", "حساب‌های دریافتنی"),
        "inventory": ("1401", "موجودی کالا"),
        "payable": ("2101", "حساب‌های پرداختنی"),
        "sales": ("4101", "فروش"),
        "cogs": ("5101", "بهای تمام‌شده کالای فروش‌رفته"),
    }

    @classmethod
    def line(cls, key, debit=0, credit=0):
        code, name = cls.ACCOUNTS[key]

        return {
            "account_code": code,
            "account_name": name,
            "debit": debit,
            "credit": credit,
        }

    @classmethod
    def post_sale(
        cls,
        conn,
        invoice_id,
        total,
        cogs,
        payment_method,
    ):
        payment_account = {
            "cash": "cash",
            "bank": "bank",
            "credit": "receivable",
        }.get(payment_method)

        if not payment_account:
            raise ValueError("روش پرداخت نامعتبر است.")

        lines = [
            cls.line(payment_account, debit=total),
            cls.line("sales", credit=total),
        ]

        if cogs > 0:
            lines.extend(
                [
                    cls.line("cogs", debit=cogs),
                    cls.line("inventory", credit=cogs),
                ]
            )

        return post_journal(
            conn,
            "ثبت فاکتور فروش",
            "sale",
            invoice_id,
            lines,
        )

    @classmethod
    def post_purchase(
        cls,
        conn,
        invoice_id,
        total,
        payment_method,
    ):
        payment_account = {
            "cash": "cash",
            "bank": "bank",
            "credit": "payable",
        }.get(payment_method)

        if not payment_account:
            raise ValueError("روش پرداخت نامعتبر است.")

        lines = [
            cls.line("inventory", debit=total),
            cls.line(payment_account, credit=total),
        ]

        return post_journal(
            conn,
            "ثبت فاکتور خرید",
            "purchase",
            invoice_id,
            lines,
        )
