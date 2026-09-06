from . import db


def money(value):

    return (
        f"{int(value):,}"
        " تومان"
    )


def dashboard_text():

    sales = db.sales_summary()
    purchases = db.purchase_summary()
    low = db.low_stock()

    return (
        "📊 داشبورد مدیریتی\n\n"

        f"🛒 فروش:\n"
        f"{sales['n']} فاکتور | "
        f"{money(sales['total'])}\n\n"

        f"🧾 خرید:\n"
        f"{purchases['n']} فاکتور | "
        f"{money(purchases['total'])}\n\n"

        f"⚠️ کالاهای کم‌موجودی:\n"
        f"{len(low)} قلم"
    )


def stock_text():

    products = db.stock_report()

    if not products:
        return (
            "📦 هنوز کالایی ثبت نشده است."
        )

    lines = [
        "📦 گزارش موجودی کالا",
        "",
    ]

    for product in products:

        lines.append(
            f"• {product['code']} | "
            f"{product['name']}\n"
            f"  موجودی: "
            f"{product['stock']:g} "
            f"{product['unit']}\n"
            f"  حداقل: "
            f"{product['min_stock']:g}"
        )

    return "\n".join(lines)


def low_stock_text():

    products = db.low_stock()

    if not products:

        return (
            "✅ هیچ کالایی در وضعیت "
            "کم‌موجودی نیست."
        )

    lines = [
        "⚠️ کالاهای کم‌موجودی",
        "",
    ]

    for product in products:

        lines.append(
            f"• {product['name']} — "
            f"{product['stock']:g} "
            f"{product['unit']}"
        )

    return "\n".join(lines)


def invoices_text():

    invoices = db.list_invoices(
        limit=20
    )

    if not invoices:
        return (
            "🧾 هنوز فاکتوری ثبت نشده است."
        )

    lines = [
        "🧾 آخرین فاکتورها",
        "",
    ]

    for invoice in invoices:

        if invoice["invoice_type"] == "sale":
            invoice_type = "فروش"
            party = (
                invoice["customer_name"]
                or "-"
            )
        else:
            invoice_type = "خرید"
            party = (
                invoice["supplier_name"]
                or "-"
            )

        lines.append(
            f"• #{invoice['invoice_no']} | "
            f"{invoice_type}\n"
            f"  {party} | "
            f"{money(invoice['total'])}"
        )

    return "\n".join(lines)
