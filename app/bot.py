import os
from datetime import date, timedelta

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
)

from app.db import (
    upsert_telegram_user,
    get_telegram_user,
    get_subscription_status,
    create_subscription_payment,
    attach_receipt_to_payment,
    get_payment,
    get_pending_payments,
    approve_subscription_payment,
    reject_subscription_payment,
    list_customers,
    list_products,
    list_suppliers,
    create_customer,
    create_product,
    create_supplier,
    get_stock_report,
    get_low_stock_products,
    get_invoice,
    list_invoices,
    get_last_journal_for_invoice,
)

from app.purchases import PurchaseService


# =========================================================
# CONFIG
# =========================================================

ADMIN_TELEGRAM_ID = int(
    os.getenv("ADMIN_TELEGRAM_ID", "8806709666")
)

CARD_NUMBER = os.getenv(
    "CARD_NUMBER",
    "شماره کارت در تنظیمات Render وارد نشده"
)

CARD_HOLDER = os.getenv(
    "CARD_HOLDER",
    "نام صاحب کارت در تنظیمات Render وارد نشده"
)

SUBSCRIPTION_MONTHLY_PRICE = int(
    os.getenv("SUBSCRIPTION_MONTHLY_PRICE", "0")
)

SUBSCRIPTION_MONTHLY_DAYS = int(
    os.getenv("SUBSCRIPTION_MONTHLY_DAYS", "30")
)


# =========================================================
# HELPERS
# =========================================================

def normalize_digits(text):
    if text is None:
        return ""

    mapping = str.maketrans(
        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
        "01234567890123456789",
    )

    return str(text).translate(mapping)


def parse_float(text):
    text = normalize_digits(text)
    text = text.replace(",", "").replace("٬", "").strip()

    return float(text)


def parse_int(text):
    return int(parse_float(text))


def money(value):
    try:
        value = float(value)
    except Exception:
        value = 0

    return f"{value:,.0f}"


def is_admin(update):
    user = update.effective_user

    return bool(
        user and user.id == ADMIN_TELEGRAM_ID
    )


def main_menu(update):
    buttons = [
        ["🛒 ثبت فروش", "🧾 ثبت خرید"],
        ["👥 مشتریان", "📦 کالاها"],
        ["🚚 تأمین‌کنندگان", "📊 گزارش‌ها"],
        ["💳 خرید اشتراک", "⚙️ وضعیت اشتراک"],
        ["📋 فاکتورها", "👨‍💼 پشتیبانی"],
    ]

    if is_admin(update):
        buttons.append(["⚙️ پنل مدیریت"])

    return ReplyKeyboardMarkup(
        buttons,
        resize_keyboard=True,
    )


# =========================================================
# START
# =========================================================

async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user

    upsert_telegram_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
    )

    await update.message.reply_text(
        "سلام 👋\n"
        "به «حساب‌یار پرو» خوش آمدید.\n\n"
        "حسابداری حرفه‌ای، ساده و همیشه در دسترس",
        reply_markup=main_menu(update),
    )


async def menu_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    text = update.message.text

    if text == "🧾 ثبت خرید":
        await purchase_start(update, context)
        return

    if text == "🛒 ثبت فروش":
        await sale_start(update, context)
        return

    if text == "👥 مشتریان":
        await customers_menu(update, context)
        return

    if text == "📦 کالاها":
        await products_menu(update, context)
        return

    if text == "🚚 تأمین‌کنندگان":
        await suppliers_menu(update, context)
        return

    if text == "📊 گزارش‌ها":
        await reports_menu(update, context)
        return

    if text == "📋 فاکتورها":
        await invoices_menu(update, context)
        return

    if text == "💳 خرید اشتراک":
        await subscription_start(update, context)
        return

    if text == "⚙️ وضعیت اشتراک":
        await subscription_status(update, context)
        return

    if text == "👨‍💼 پشتیبانی":
        await support(update, context)
        return

    if text == "⚙️ پنل مدیریت":
        await admin_panel(update, context)
        return


# =========================================================
# PURCHASE
# =========================================================

(
    PURCHASE_SUPPLIER,
    PURCHASE_PRODUCT,
    PURCHASE_QUANTITY,
    PURCHASE_PRICE,
    PURCHASE_DISCOUNT,
    PURCHASE_PAYMENT,
    PURCHASE_CONFIRM,
) = range(7)


async def purchase_start(
    update,
    context,
):
    suppliers = list_suppliers()

    if not suppliers:
        await update.message.reply_text(
            "هیچ تأمین‌کننده‌ای ثبت نشده است."
        )
        return ConversationHandler.END

    keyboard = []

    for supplier in suppliers:
        keyboard.append(
            [
                InlineKeyboardButton(
                    supplier["name"],
                    callback_data=f"pur_supplier:{supplier['id']}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                "❌ لغو",
                callback_data="pur_cancel",
            )
        ]
    )

    context.user_data["purchase"] = {
        "items": [],
        "discount": 0,
        "tax": 0,
    }

    await update.message.reply_text(
        "تأمین‌کننده را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    return PURCHASE_SUPPLIER


async def purchase_supplier_callback(
    update,
    context,
):
    query = update.callback_query
    await query.answer()

    if query.data == "pur_cancel":
        await query.edit_message_text(
            "ثبت خرید لغو شد."
        )
        return ConversationHandler.END

    supplier_id = int(
        query.data.split(":")[1]
    )

    context.user_data["purchase"]["supplier_id"] = supplier_id

    products = list_products()

    keyboard = []

    for product in products:
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"{product['name']} | موجودی: {product['stock']}",
                    callback_data=f"pur_product:{product['id']}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                "❌ لغو",
                callback_data="pur_cancel",
            )
        ]
    )

    await query.edit_message_text(
        "کالا را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    return PURCHASE_PRODUCT


async def purchase_product_callback(
    update,
    context,
):
    query = update.callback_query
    await query.answer()

    if query.data == "pur_cancel":
        await query.edit_message_text(
            "ثبت خرید لغو شد."
        )
        return ConversationHandler.END

    product_id = int(
        query.data.split(":")[1]
    )

    product = next(
        (
            p
            for p in list_products()
            if p["id"] == product_id
        ),
        None,
    )

    if not product:
        await query.edit_message_text(
            "کالا پیدا نشد."
        )
        return ConversationHandler.END

    context.user_data["purchase"]["current_product_id"] = product_id
    context.user_data["purchase"]["current_product_name"] = product["name"]

    await query.message.reply_text(
        f"کالا: {product['name']}\n\n"
        "تعداد را وارد کنید:"
    )

    return PURCHASE_QUANTITY


async def purchase_quantity(
    update,
    context,
):
    try:
        quantity = parse_float(
            update.message.text
        )

        if quantity <= 0:
            raise ValueError
    except Exception:
        await update.message.reply_text(
            "❌ تعداد نامعتبر است.\nمثلاً: 5"
        )
        return PURCHASE_QUANTITY

    context.user_data["purchase"]["quantity"] = quantity

    await update.message.reply_text(
        "قیمت خرید هر واحد را به تومان وارد کنید:"
    )

    return PURCHASE_PRICE


async def purchase_price(
    update,
    context,
):
    try:
        price = parse_float(
            update.message.text
        )

        if price < 0:
            raise ValueError
    except Exception:
        await update.message.reply_text(
            "❌ قیمت نامعتبر است."
        )
        return PURCHASE_PRICE

    context.user_data["purchase"]["unit_price"] = price

    await update.message.reply_text(
        "تخفیف این قلم را وارد کنید.\n"
        "اگر تخفیف ندارد، 0 بزنید:"
    )

    return PURCHASE_DISCOUNT


async def purchase_discount(
    update,
    context,
):
    try:
        discount = parse_float(
            update.message.text
        )

        if discount < 0:
            raise ValueError
    except Exception:
        await update.message.reply_text(
            "❌ مبلغ تخفیف نامعتبر است."
        )
        return PURCHASE_DISCOUNT

    purchase = context.user_data["purchase"]

    purchase["items"].append(
        {
            "product_id": purchase["current_product_id"],
            "quantity": purchase["quantity"],
            "unit_price": purchase["unit_price"],
            "discount": discount,
        }
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "➕ افزودن کالای دیگر",
                callback_data="pur_add_item",
            )
        ],
        [
            InlineKeyboardButton(
                "➡️ ادامه ثبت خرید",
                callback_data="pur_continue",
            )
        ],
        [
            InlineKeyboardButton(
                "❌ لغو",
                callback_data="pur_cancel",
            )
        ],
    ]

    await update.message.reply_text(
        "قلم کالا ثبت شد.\n\n"
        "می‌توانید کالای دیگری اضافه کنید یا ادامه دهید.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    return PURCHASE_PRODUCT


async def purchase_add_item_callback(
    update,
    context,
):
    query = update.callback_query
    await query.answer()

    products = list_products()

    keyboard = []

    for product in products:
        keyboard.append(
            [
                InlineKeyboardButton(
                    product["name"],
                    callback_data=f"pur_product:{product['id']}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                "❌ لغو",
                callback_data="pur_cancel",
            )
        ]
    )

    await query.edit_message_text(
        "کالای بعدی را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    return PURCHASE_PRODUCT


async def purchase_continue_callback(
    update,
    context,
):
    query = update.callback_query
    await query.answer()

    purchase = context.user_data["purchase"]

    lines = []
    subtotal = 0

    for index, item in enumerate(
        purchase["items"],
        start=1,
    ):
        product = next(
            (
                p
                for p in list_products()
                if p["id"] == item["product_id"]
            ),
            None,
        )

        name = (
            product["name"]
            if product
            else "کالای نامشخص"
        )

        line_total = (
            item["quantity"] * item["unit_price"]
            - item["discount"]
        )

        subtotal += line_total

        lines.append(
            f"{index}. {name}\n"
            f"   تعداد: {item['quantity']}\n"
            f"   مبلغ: {money(line_total)} تومان"
        )

    purchase["subtotal"] = subtotal

    text = (
        "📋 پیش‌فاکتور خرید\n\n"
        + "\n".join(lines)
        + "\n\n"
        f"جمع: {money(subtotal)} تومان\n\n"
        "روش پرداخت را انتخاب کنید:"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "💵 نقدی",
                callback_data="pur_pay:cash",
            )
        ],
        [
            InlineKeyboardButton(
                "🏦 بانکی",
                callback_data="pur_pay:bank",
            )
        ],
        [
            InlineKeyboardButton(
                "📒 نسیه / پرداختنی",
                callback_data="pur_pay:credit",
            )
        ],
        [
            InlineKeyboardButton(
                "❌ لغو",
                callback_data="pur_cancel",
            )
        ],
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    return PURCHASE_PAYMENT


async def purchase_payment_callback(
    update,
    context,
):
    query = update.callback_query
    await query.answer()

    if query.data == "pur_cancel":
        await query.edit_message_text(
            "ثبت خرید لغو شد."
        )
        return ConversationHandler.END

    payment_method = query.data.split(":")[1]

    context.user_data["purchase"]["payment_method"] = payment_method

    purchase = context.user_data["purchase"]

    payment_name = {
        "cash": "نقدی",
        "bank": "بانکی",
        "credit": "نسیه / پرداختنی",
    }.get(
        payment_method,
        payment_method,
    )

    total = purchase["subtotal"]

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ تأیید و ثبت خرید",
                callback_data="pur_confirm",
            )
        ],
        [
            InlineKeyboardButton(
                "❌ لغو",
                callback_data="pur_cancel",
            )
        ],
    ]

    await query.edit_message_text(
        "آیا اطلاعات خرید صحیح است؟\n\n"
        f"جمع خرید: {money(total)} تومان\n"
        f"روش پرداخت: {payment_name}",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    return PURCHASE_CONFIRM


async def purchase_confirm_callback(
    update,
    context,
):
    query = update.callback_query
    await query.answer()

    if query.data == "pur_cancel":
        await query.edit_message_text(
            "ثبت خرید لغو شد."
        )
        context.user_data.pop("purchase", None)
        return ConversationHandler.END

    purchase = context.user_data["purchase"]

    try:
        result = PurchaseService.create_purchase(
            supplier_id=purchase["supplier_id"],
            items=purchase["items"],
            discount=purchase.get("discount", 0),
            tax=purchase.get("tax", 0),
            payment_method=purchase.get(
                "payment_method",
                "credit",
            ),
        )

        await query.edit_message_text(
            "✅ خرید با موفقیت ثبت شد.\n\n"
            f"شماره فاکتور: {result['invoice_id']}\n"
            f"تأمین‌کننده: {result['supplier_name']}\n"
            f"جمع خرید: {money(result['total'])} تومان\n\n"
            "موجودی کالا و سند حسابداری نیز ثبت شد."
        )

    except Exception as exc:
        await query.edit_message_text(
            "❌ ثبت خرید انجام نشد.\n\n"
            f"خطا: {exc}"
        )

    context.user_data.pop("purchase", None)

    return ConversationHandler.END


async def purchase_cancel(
    update,
    context,
):
    context.user_data.pop("purchase", None)

    await update.message.reply_text(
        "ثبت خرید لغو شد.",
        reply_markup=main_menu(update),
    )

    return ConversationHandler.END


# =========================================================
# CUSTOMERS
# =========================================================

async def customers_menu(
    update,
    context,
):
    customers = list_customers()

    text = "👥 مشتریان\n\n"

    if not customers:
        text += "هنوز مشتری‌ای ثبت نشده است."
    else:
        for customer in customers[:30]:
            text += (
                f"#{customer['id']} - "
                f"{customer['name']}\n"
            )

            if customer["phone"]:
                text += f"📞 {customer['phone']}\n"

            text += "\n"

    keyboard = [
        [
            InlineKeyboardButton(
                "➕ مشتری جدید",
                callback_data="customer_add",
            )
        ]
    ]

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def customer_add_callback(
    update,
    context,
):
    query = update.callback_query
    await query.answer()

    context.user_data["customer_add"] = True

    await query.message.reply_text(
        "نام مشتری جدید را وارد کنید:"
    )


async def customer_add_text(
    update,
    context,
):
    if not context.user_data.get(
        "customer_add"
    ):
        return

    name = update.message.text.strip()

    if not name:
        await update.message.reply_text(
            "نام مشتری نمی‌تواند خالی باشد."
        )
        return

    customer_id = create_customer(
        name=name,
        phone="",
        address="",
    )

    context.user_data.pop(
        "customer_add",
        None,
    )

    await update.message.reply_text(
        "✅ مشتری ثبت شد.\n\n"
        f"شماره مشتری: {customer_id}",
        reply_markup=main_menu(update),
    )


# =========================================================
# PRODUCTS
# =========================================================

async def products_menu(
    update,
    context,
):
    products = list_products()

    text = "📦 کالاها\n\n"

    if not products:
        text += "هنوز کالایی ثبت نشده است."
    else:
        for product in products[:30]:
            text += (
                f"#{product['id']} - {product['name']}\n"
                f"کد: {product['code'] or '-'}\n"
                f"موجودی: {product['stock']}\n"
                f"قیمت خرید: {money(product['purchase_cost'])}\n"
                f"قیمت فروش: {money(product['sale_price'])}\n\n"
            )

    keyboard = [
        [
            InlineKeyboardButton(
                "➕ کالای جدید",
                callback_data="product_add",
            )
        ]
    ]

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def product_add_callback(
    update,
    context,
):
    query = update.callback_query
    await query.answer()

    context.user_data["product_add"] = True

    await query.message.reply_text(
        "اطلاعات کالا را در یک پیام ارسال کنید:\n\n"
        "نام | کد | واحد | قیمت خرید | قیمت فروش | حداقل موجودی\n\n"
        "مثال:\n"
        "لپ‌تاپ | P002 | دستگاه | 30000000 | 35000000 | 2"
    )


async def product_add_text(
    update,
    context,
):
    if not context.user_data.get(
        "product_add"
    ):
        return

    parts = [
        x.strip()
        for x in update.message.text.split("|")
    ]

    if len(parts) != 6:
        await update.message.reply_text(
            "فرمت صحیح نیست.\n"
            "لطفاً ۶ بخش را با | جدا کنید."
        )
        return

    try:
        product_id = create_product(
            name=parts[0],
            code=parts[1],
            unit=parts[2],
            purchase_cost=parse_float(parts[3]),
            sale_price=parse_float(parts[4]),
            min_stock=parse_float(parts[5]),
        )
    except Exception as exc:
        await update.message.reply_text(
            f"❌ ثبت کالا انجام نشد:\n{exc}"
        )
        return

    context.user_data.pop(
        "product_add",
        None,
    )

    await update.message.reply_text(
        "✅ کالا ثبت شد.\n\n"
        f"شماره کالا: {product_id}",
        reply_markup=main_menu(update),
    )


# =========================================================
# SUPPLIERS
# =========================================================

async def suppliers_menu(
    update,
    context,
):
    suppliers = list_suppliers()

    text = "🚚 تأمین‌کنندگان\n\n"

    if not suppliers:
        text += "هنوز تأمین‌کننده‌ای ثبت نشده است."
    else:
        for supplier in suppliers[:30]:
            text += (
                f"#{supplier['id']} - "
                f"{supplier['name']}\n"
            )

            if supplier["phone"]:
                text += f"📞 {supplier['phone']}\n"

            text += "\n"

    keyboard = [
        [
            InlineKeyboardButton(
                "➕ تأمین‌کننده جدید",
                callback_data="supplier_add",
            )
        ]
    ]

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def supplier_add_callback(
    update,
    context,
):
    query = update.callback_query
    await query.answer()

    context.user_data["supplier_add"] = True

    await query.message.reply_text(
        "نام تأمین‌کننده جدید را وارد کنید:"
    )


async def supplier_add_text(
    update,
    context,
):
    if not context.user_data.get(
        "supplier_add"
    ):
        return

    name = update.message.text.strip()

    if not name:
        await update.message.reply_text(
            "نام تأمین‌کننده نمی‌تواند خالی باشد."
        )
        return

    supplier_id = create_supplier(
        name=name,
        phone="",
        address="",
    )

    context.user_data.pop(
        "supplier_add",
        None,
    )

    await update.message.reply_text(
        "✅ تأمین‌کننده ثبت شد.\n\n"
        f"شماره تأمین‌کننده: {supplier_id}",
        reply_markup=main_menu(update),
    )


# =========================================================
# REPORTS
# =========================================================

async def reports_menu(
    update,
    context,
):
    keyboard = [
        [
            InlineKeyboardButton(
                "📦 گزارش موجودی",
                callback_data="report_stock",
            )
        ],
        [
            InlineKeyboardButton(
                "⚠️ کالاهای کم‌موجودی",
                callback_data="report_low_stock",
            )
        ],
        [
            InlineKeyboardButton(
                "🧾 آخرین خریدها",
                callback_data="report_purchases",
            )
        ],
        [
            InlineKeyboardButton(
                "🛒 آخرین فروش‌ها",
                callback_data="report_sales",
            )
        ],
    ]

    await update.message.reply_text(
        "📊 گزارش‌ها\n\n"
        "گزارش موردنظر را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def report_stock_callback(
    update,
    context,
):
    query = update.callback_query
    await query.answer()

    products = get_stock_report()

    text = "📦 گزارش موجودی\n\n"

    for product in products[:50]:
        text += (
            f"• {product['name']}\n"
            f"  موجودی: {product['stock']} {product['unit']}\n"
            f"  حداقل: {product['min_stock']}\n\n"
        )

    await query.edit_message_text(text)


async def report_low_stock_callback(
    update,
    context,
):
    query = update.callback_query
    await query.answer()

    products = get_low_stock_products()

    if not products:
        text = (
            "✅ در حال حاضر کالایی زیر حداقل موجودی نیست."
        )
    else:
        text = "⚠️ هشدار کمبود موجودی\n\n"

        for product in products:
            text += (
                f"• {product['name']}\n"
                f"موجودی: {product['stock']}\n"
                f"حداقل: {product['min_stock']}\n\n"
            )

    await query.edit_message_text(text)


async def report_purchases_callback(
    update,
    context,
):
    query = update.callback_query
    await query.answer()

    invoices = list_invoices(
        invoice_type="purchase",
        limit=15,
    )

    if not invoices:
        text = "هنوز خریدی ثبت نشده است."
    else:
        text = "🧾 آخرین خریدها\n\n"

        for invoice in invoices:
            text += (
                f"فاکتور #{invoice['id']}\n"
                f"تأمین‌کننده: "
                f"{invoice['supplier_name'] or '-'}\n"
                f"مبلغ: {money(invoice['total'])} تومان\n\n"
            )

    await query.edit_message_text(text)


async def report_sales_callback(
    update,
    context,
):
    query = update.callback_query
    await query.answer()

    invoices = list_invoices(
        invoice_type="sale",
        limit=15,
    )

    if not invoices:
        text = "هنوز فروشی ثبت نشده است."
    else:
        text = "🛒 آخرین فروش‌ها\n\n"

        for invoice in invoices:
            text += (
                f"فاکتور #{invoice['id']}\n"
                f"مشتری: "
                f"{invoice['customer_name'] or '-'}\n"
                f"مبلغ: {money(invoice['total'])} تومان\n\n"
            )

    await query.edit_message_text(text)


# =========================================================
# INVOICES
# =========================================================

async def invoices_menu(
    update,
    context,
):
    invoices = list_invoices(limit=20)

    if not invoices:
        await update.message.reply_text(
            "📋 هنوز فاکتوری ثبت نشده است."
        )
        return

    text = "📋 آخرین فاکتورها\n\n"

    for invoice in invoices:
        if invoice["invoice_type"] == "purchase":
            invoice_type = "خرید"
            party = invoice["supplier_name"]
        else:
            invoice_type = "فروش"
            party = invoice["customer_name"]

        text += (
            f"#{invoice['id']} | {invoice_type}\n"
            f"طرف حساب: {party or '-'}\n"
            f"مبلغ: {money(invoice['total'])} تومان\n\n"
        )

    await update.message.reply_text(text)


# =========================================================
# SUBSCRIPTION
# =========================================================

async def subscription_start(
    update,
    context,
):
    user = update.effective_user

    db_user = get_telegram_user(
        user.id
    )

    if not db_user:
        upsert_telegram_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )

        db_user = get_telegram_user(
            user.id
        )

    price = SUBSCRIPTION_MONTHLY_PRICE

    if price <= 0:
        await update.message.reply_text(
            "⚠️ مبلغ اشتراک در تنظیمات Render تعیین نشده است."
        )
        return

    payment_id = create_subscription_payment(
        telegram_user_id=db_user["id"],
        plan_code="monthly",
        plan_name="اشتراک ماهانه",
        amount=price,
    )

    await update.message.reply_text(
        "💳 خرید اشتراک ماهانه\n\n"
        f"مبلغ: {money(price)} تومان\n\n"
        f"شماره کارت:\n{CARD_NUMBER}\n\n"
        f"به نام:\n{CARD_HOLDER}\n\n"
        f"کد پرداخت: #{payment_id}\n\n"
        "پس از پرداخت، تصویر رسید را همین‌جا ارسال کنید."
    )

    context.user_data[
        "subscription_payment_id"
    ] = payment_id


async def subscription_receipt_photo(
    update,
    context,
):
    payment_id = context.user_data.get(
        "subscription_payment_id"
    )

    if not payment_id:
        return

    if not update.message.photo:
        return

    photo = update.message.photo[-1]

    attach_receipt_to_payment(
        payment_id=payment_id,
        receipt_file_id=photo.file_id,
        receipt_file_unique_id=photo.file_unique_id,
    )

    payment = get_payment(
        payment_id
    )

    await update.message.reply_text(
        "✅ رسید شما ثبت شد.\n\n"
        "پس از بررسی مدیر، اشتراک فعال خواهد شد."
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ تأیید پرداخت",
                    callback_data=f"pay_approve:{payment_id}",
                ),
                InlineKeyboardButton(
                    "❌ رد پرداخت",
                    callback_data=f"pay_reject:{payment_id}",
                ),
            ]
        ]
    )

    admin_text = (
        "💳 درخواست پرداخت جدید\n\n"
        f"کد پرداخت: #{payment_id}\n"
        f"کاربر: {payment['first_name'] or '-'}\n"
        f"Username: @{payment['username'] or '-'}\n"
        f"Telegram ID: {payment['telegram_id']}\n"
        f"مبلغ: {money(payment['amount'])} تومان"
    )

    await context.bot.send_message(
        chat_id=ADMIN_TELEGRAM_ID,
        text=admin_text,
        reply_markup=keyboard,
    )

    await context.bot.send_photo(
        chat_id=ADMIN_TELEGRAM_ID,
        photo=photo.file_id,
        caption=f"رسید پرداخت #{payment_id}",
    )

    context.user_data.pop(
        "subscription_payment_id",
        None,
    )


async def admin_payment_callback(
    update,
    context,
):
    query = update.callback_query

    if not is_admin(update):
        await query.answer(
            "دسترسی غیرمجاز",
            show_alert=True,
        )
        return

    await query.answer()

    action, payment_id_text = query.data.split(
        ":",
        1,
    )

    payment_id = int(payment_id_text)

    payment = get_payment(
        payment_id
    )

    if not payment:
        await query.edit_message_text(
            "❌ پرداخت پیدا نشد."
        )
        return

    if action == "pay_approve":

        start_date = date.today()

        end_date = (
            start_date
            + timedelta(
                days=SUBSCRIPTION_MONTHLY_DAYS - 1
            )
        )

        subscription = approve_subscription_payment(
            payment_id=payment_id,
            reviewed_by=ADMIN_TELEGRAM_ID,
            start_date=start_date,
            end_date=end_date,
        )

        await query.edit_message_text(
            "✅ پرداخت تأیید شد.\n\n"
            f"کد پرداخت: #{payment_id}\n"
            f"اشتراک: {payment['plan_name']}\n"
            f"شروع: {subscription['start_date']}\n"
            f"پایان: {subscription['end_date']}"
        )

        await context.bot.send_message(
            chat_id=payment["telegram_id"],
            text=(
                "🎉 پرداخت شما تأیید شد.\n\n"
                "اشتراک شما فعال شد.\n"
                f"از {subscription['start_date']}\n"
                f"تا {subscription['end_date']}"
            ),
        )

    elif action == "pay_reject":

        reject_subscription_payment(
            payment_id=payment_id,
            reviewed_by=ADMIN_TELEGRAM_ID,
            reason="توسط مدیر رد شد",
        )

        await query.edit_message_text(
            "❌ پرداخت رد شد.\n\n"
            f"کد پرداخت: #{payment_id}"
        )

        await context.bot.send_message(
            chat_id=payment["telegram_id"],
            text=(
                "❌ رسید پرداخت شما تأیید نشد.\n\n"
                "لطفاً اطلاعات پرداخت را بررسی کرده "
                "و رسید صحیح را ارسال کنید."
            ),
        )


async def subscription_status(
    update,
    context,
):
    status = get_subscription_status(
        update.effective_user.id
    )

    if not status["active"]:
        await update.message.reply_text(
            "⚪ شما در حال حاضر اشتراک فعال ندارید.",
            reply_markup=main_menu(update),
        )
        return

    sub = status["subscription"]

    await update.message.reply_text(
        "⚙️ وضعیت اشتراک\n\n"
        f"طرح: {sub['plan_name']}\n"
        f"شروع: {sub['start_date']}\n"
        f"پایان: {sub['end_date']}\n"
        f"روزهای باقی‌مانده: {status['remaining_days']}",
        reply_markup=main_menu(update),
    )


# =========================================================
# ADMIN
# =========================================================

async def admin_panel(
    update,
    context,
):
    if not is_admin(update):
        await update.message.reply_text(
            "⛔ دسترسی غیرمجاز."
        )
        return

    pending = get_pending_payments()

    keyboard = [
        [
            InlineKeyboardButton(
                "💳 پرداخت‌های در انتظار",
                callback_data="admin_payments",
            )
        ],
        [
            InlineKeyboardButton(
                "👥 تعداد کاربران",
                callback_data="admin_users",
            )
        ],
        [
            InlineKeyboardButton(
                "📦 موجودی",
                callback_data="admin_stock",
            )
        ],
    ]

    await update.message.reply_text(
        "⚙️ پنل مدیریت\n\n"
        f"پرداخت‌های در انتظار: {len(pending)}",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def admin_callback(
    update,
    context,
):
    query = update.callback_query

    if not is_admin(update):
        await query.answer(
            "دسترسی غیرمجاز",
            show_alert=True,
        )
        return

    await query.answer()

    if query.data == "admin_payments":

        payments = get_pending_payments()

        if not payments:
            await query.edit_message_text(
                "✅ پرداخت در انتظاری وجود ندارد."
            )
            return

        text = "💳 پرداخت‌های در انتظار\n\n"

        for payment in payments[:30]:
            text += (
                f"#{payment['id']} | "
                f"{payment['first_name'] or '-'} | "
                f"{money(payment['amount'])} تومان\n"
            )

        await query.edit_message_text(text)

    elif query.data == "admin_users":

        from app.db import get_connection

        conn = get_connection()

        row = conn.execute(
            "SELECT COUNT(*) AS count FROM telegram_users"
        ).fetchone()

        conn.close()

        await query.edit_message_text(
            f"👥 تعداد کاربران ثبت‌شده: {row['count']}"
        )

    elif query.data == "admin_stock":

        products = get_stock_report()

        text = "📦 وضعیت موجودی\n\n"

        for product in products[:30]:
            text += (
                f"{product['name']}: "
                f"{product['stock']}\n"
            )

        await query.edit_message_text(text)


# =========================================================
# SUPPORT
# =========================================================

async def support(
    update,
    context,
):
    await update.message.reply_text(
        "👨‍💼 پشتیبانی حساب‌یار پرو\n\n"
        "برای ارتباط با پشتیبانی، پیام خود را "
        "در همین چت ارسال کنید.\n\n"
        "در نسخه بعدی، سیستم تیکت پشتیبانی نیز اضافه می‌شود.",
        reply_markup=main_menu(update),
    )


# =========================================================
# SALES - پایه فعال
# =========================================================

async def sale_start(
    update,
    context,
):
    customers = list_customers()

    if not customers:
        await update.message.reply_text(
            "برای ثبت فروش ابتدا حداقل یک مشتری ثبت کنید."
        )
        return

    products = list_products()

    if not products:
        await update.message.reply_text(
            "برای ثبت فروش ابتدا حداقل یک کالا ثبت کنید."
        )
        return

    await update.message.reply_text(
        "🛒 ماژول ثبت فروش\n\n"
        "موتور فروش آماده است؛ "
        "در این نسخه، تکمیل گردش ثبت فروش "
        "در مرحله بعدی انجام می‌شود."
    )


# =========================================================
# REGISTER
# =========================================================

def register_handlers(application):

    purchase_conversation = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex("^🧾 ثبت خرید$"),
                purchase_start,
            )
        ],
        states={
            PURCHASE_SUPPLIER: [
                CallbackQueryHandler(
                    purchase_supplier_callback,
                    pattern=r"^pur_(supplier|cancel)",
                )
            ],

            PURCHASE_PRODUCT: [
                CallbackQueryHandler(
                    purchase_add_item_callback,
                    pattern=r"^pur_add_item$",
                ),
                CallbackQueryHandler(
                    purchase_continue_callback,
                    pattern=r"^pur_continue$",
                ),
                CallbackQueryHandler(
                    purchase_product_callback,
                    pattern=r"^pur_product:",
                ),
                CallbackQueryHandler(
                    purchase_product_callback,
                    pattern=r"^pur_cancel$",
                ),
            ],

            PURCHASE_QUANTITY: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    purchase_quantity,
                )
            ],

            PURCHASE_PRICE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    purchase_price,
                )
            ],

            PURCHASE_DISCOUNT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    purchase_discount,
                )
            ],

            PURCHASE_PAYMENT: [
                CallbackQueryHandler(
                    purchase_payment_callback,
                    pattern=r"^pur_(pay|cancel)",
                )
            ],

            PURCHASE_CONFIRM: [
                CallbackQueryHandler(
                    purchase_confirm_callback,
                    pattern=r"^pur_(confirm|cancel)$",
                )
            ],
        },

        fallbacks=[
            CommandHandler(
                "cancel",
                purchase_cancel,
            )
        ],

        allow_reentry=True,
    )

    application.add_handler(
        purchase_conversation
    )

    # Start
    application.add_handler(
        CommandHandler(
            "start",
            start_command,
        )
    )

    # Subscription
    application.add_handler(
        CallbackQueryHandler(
            admin_payment_callback,
            pattern=r"^pay_(approve|reject):",
        )
    )

    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            subscription_receipt_photo,
        )
    )

    # Customer/Product/Supplier callbacks
    application.add_handler(
        CallbackQueryHandler(
            customer_add_callback,
            pattern=r"^customer_add$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            product_add_callback,
            pattern=r"^product_add$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            supplier_add_callback,
            pattern=r"^supplier_add$",
        )
    )

    # Reports
    application.add_handler(
        CallbackQueryHandler(
            report_stock_callback,
            pattern=r"^report_stock$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            report_low_stock_callback,
            pattern=r"^report_low_stock$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            report_purchases_callback,
            pattern=r"^report_purchases$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            report_sales_callback,
            pattern=r"^report_sales$",
        )
    )

    # Admin
    application.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern=r"^admin_(payments|users|stock)$",
        )
    )

    # Text menu
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            menu_text,
        )
    )

    # Dynamic master-data text handlers
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            customer_add_text,
        ),
        group=1,
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            product_add_text,
        ),
        group=2,
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            supplier_add_text,
        ),
        group=3,
    )


def build_application(application):
    register_handlers(application)
    return application
