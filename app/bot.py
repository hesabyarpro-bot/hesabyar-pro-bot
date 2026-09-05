from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from app.sales import (
    get_customer_by_name,
    get_product_by_name,
    create_customer,
    create_sale,
)


# مراحل ثبت فروش
CUSTOMER = 1
PRODUCT = 2
QUANTITY = 3
PRICE = 4
DISCOUNT = 5
PAYMENT = 6
CONFIRM = 7


def main_menu():
    keyboard = [
        ["🛒 ثبت فروش"],
        ["👤 مشتریان", "📦 کالاها"],
        ["📊 گزارش فروش"],
    ]

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
    )


async def show_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "منوی حساب‌یار پرو:",
        reply_markup=main_menu(),
    )


async def sales_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data.clear()

    await update.message.reply_text(
        "🛒 ثبت فروش\n\n"
        "نام مشتری را وارد کنید:",
        reply_markup=ReplyKeyboardRemove(),
    )

    return CUSTOMER


async def get_customer(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    name = update.message.text.strip()

    if not name:
        await update.message.reply_text(
            "لطفاً نام مشتری را وارد کنید."
        )
        return CUSTOMER

    customer = get_customer_by_name(name)

    if customer is None:
        customer_id = create_customer(name)

        await update.message.reply_text(
            f"مشتری «{name}» ثبت شد."
        )
    else:
        customer_id = customer["id"]

        await update.message.reply_text(
            f"مشتری «{name}» پیدا شد."
        )

    context.user_data["customer_id"] = customer_id
    context.user_data["customer_name"] = name

    await update.message.reply_text(
        "حالا نام کالا را وارد کنید:"
    )

    return PRODUCT


async def get_product(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    name = update.message.text.strip()

    if not name:
        await update.message.reply_text(
            "لطفاً نام کالا را وارد کنید."
        )
        return PRODUCT

    product = get_product_by_name(name)

    if product is None:
        await update.message.reply_text(
            "❌ این کالا در سیستم پیدا نشد.\n\n"
            "فعلاً باید کالا ابتدا در دیتابیس ثبت شود."
        )
        return PRODUCT

    context.user_data["product_id"] = product["id"]
    context.user_data["product_name"] = product["name"]
    context.user_data["product_stock"] = float(
        product["stock"] or 0
    )
    context.user_data["default_price"] = float(
        product["sale_price"] or 0
    )

    await update.message.reply_text(
        f"📦 کالا: {product['name']}\n"
        f"موجودی: {product['stock']}\n\n"
        "تعداد فروش را وارد کنید:"
    )

    return QUANTITY


async def get_quantity(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        quantity = float(
            update.message.text.strip()
        )

        if quantity <= 0:
            raise ValueError

    except ValueError:
        await update.message.reply_text(
            "❌ تعداد نامعتبر است.\n"
            "مثلاً: 2"
        )
        return QUANTITY

    stock = context.user_data.get(
        "product_stock",
        0,
    )

    if quantity > stock:
        await update.message.reply_text(
            f"❌ موجودی کافی نیست.\n"
            f"موجودی فعلی: {stock}"
        )
        return QUANTITY

    context.user_data["quantity"] = quantity

    default_price = context.user_data.get(
        "default_price",
        0,
    )

    await update.message.reply_text(
        f"قیمت واحد را وارد کنید:\n\n"
        f"قیمت ثبت‌شده کالا: {default_price}"
    )

    return PRICE


async def get_price(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        price = float(
            update.message.text.strip()
        )

        if price < 0:
            raise ValueError

    except ValueError:
        await update.message.reply_text(
            "❌ قیمت نامعتبر است."
        )
        return PRICE

    context.user_data["unit_price"] = price

    await update.message.reply_text(
        "مبلغ تخفیف را وارد کنید.\n"
        "اگر تخفیف ندارید، عدد 0 را وارد کنید."
    )

    return DISCOUNT


async def get_discount(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        discount = float(
            update.message.text.strip()
        )

        if discount < 0:
            raise ValueError

    except ValueError:
        await update.message.reply_text(
            "❌ مبلغ تخفیف نامعتبر است."
        )
        return DISCOUNT

    quantity = context.user_data["quantity"]
    price = context.user_data["unit_price"]

    subtotal = quantity * price

    if discount > subtotal:
        await update.message.reply_text(
            "❌ تخفیف نمی‌تواند بیشتر از مبلغ فروش باشد."
        )
        return DISCOUNT

    context.user_data["discount"] = discount

    keyboard = [
        ["💵 نقدی", "🏦 بانکی"],
        ["📝 نسیه"],
    ]

    await update.message.reply_text(
        "روش پرداخت را انتخاب کنید:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=True,
        ),
    )

    return PAYMENT


async def get_payment(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    text = update.message.text.strip()

    payment_map = {
        "💵 نقدی": "cash",
        "🏦 بانکی": "bank",
        "📝 نسیه": "credit",
    }

    payment_method = payment_map.get(text)

    if not payment_method:
        await update.message.reply_text(
            "لطفاً یکی از روش‌های پرداخت را انتخاب کنید."
        )
        return PAYMENT

    context.user_data["payment_method"] = payment_method

    quantity = context.user_data["quantity"]
    price = context.user_data["unit_price"]
    discount = context.user_data["discount"]

    subtotal = quantity * price
    total = subtotal - discount

    customer_name = context.user_data[
        "customer_name"
    ]

    product_name = context.user_data[
        "product_name"
    ]

    payment_text = {
        "cash": "نقدی",
        "bank": "بانکی",
        "credit": "نسیه",
    }[payment_method]

    preview = (
        "🧾 پیش‌نمایش فاکتور\n\n"
        f"👤 مشتری: {customer_name}\n"
        f"📦 کالا: {product_name}\n"
        f"🔢 تعداد: {quantity}\n"
        f"💰 قیمت واحد: {price:,.0f}\n"
        f"💵 مبلغ اولیه: {subtotal:,.0f}\n"
        f"🎁 تخفیف: {discount:,.0f}\n"
        f"💳 مبلغ نهایی: {total:,.0f}\n"
        f"💠 پرداخت: {payment_text}\n\n"
        "آیا ثبت شود؟"
    )

    keyboard = [
        ["✅ تأیید ثبت"],
        ["❌ لغو"],
    ]

    await update.message.reply_text(
        preview,
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
        ),
    )

    return CONFIRM


async def confirm_sale(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    text = update.message.text.strip()

    if text == "❌ لغو":
        context.user_data.clear()

        await update.message.reply_text(
            "عملیات لغو شد.",
            reply_markup=main_menu(),
        )

        return ConversationHandler.END

    if text != "✅ تأیید ثبت":
        await update.message.reply_text(
            "لطفاً تأیید یا لغو را انتخاب کنید."
        )
        return CONFIRM

    try:
        result = create_sale(
            customer_id=context.user_data[
                "customer_id"
            ],
            product_id=context.user_data[
                "product_id"
            ],
            quantity=context.user_data[
                "quantity"
            ],
            unit_price=context.user_data[
                "unit_price"
            ],
            discount=context.user_data[
                "discount"
            ],
            tax=0,
            payment_method=context.user_data[
                "payment_method"
            ],
        )

    except Exception as exc:
        await update.message.reply_text(
            "❌ ثبت فروش انجام نشد.\n\n"
            f"دلیل: {exc}",
            reply_markup=main_menu(),
        )

        context.user_data.clear()

        return ConversationHandler.END

    invoice_number = result[
        "invoice_number"
    ]

    total = result["total"]

    remaining_stock = result[
        "stock_remaining"
    ]

    await update.message.reply_text(
        "✅ فروش با موفقیت ثبت شد.\n\n"
        f"🧾 شماره فاکتور: {invoice_number}\n"
        f"💰 مبلغ: {total:,.0f}\n"
        f"📦 موجودی باقی‌مانده: {remaining_stock}\n\n"
        "حساب‌یار پرو آماده ثبت فروش بعدی است.",
        reply_markup=main_menu(),
    )

    context.user_data.clear()

    return ConversationHandler.END


async def cancel_sale(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data.clear()

    await update.message.reply_text(
        "عملیات لغو شد.",
        reply_markup=main_menu(),
    )

    return ConversationHandler.END


async def customers_placeholder(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "👤 بخش مشتریان در حال توسعه است."
    )


async def products_placeholder(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "📦 بخش کالاها در حال توسعه است."
    )


async def reports_placeholder(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "📊 گزارش فروش در حال توسعه است."
    )


def register_handlers(application):
    sales_conversation = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex("^🛒 ثبت فروش$"),
                sales_start,
            )
        ],
        states={
            CUSTOMER: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    get_customer,
                )
            ],
            PRODUCT: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    get_product,
                )
            ],
            QUANTITY: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    get_quantity,
                )
            ],
            PRICE: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    get_price,
                )
            ],
            DISCOUNT: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    get_discount,
                )
            ],
            PAYMENT: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    get_payment,
                )
            ],
            CONFIRM: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    confirm_sale,
                )
            ],
        },
        fallbacks=[
            CommandHandler(
                "cancel",
                cancel_sale,
            )
        ],
        allow_reentry=True,
    )

    application.add_handler(
        sales_conversation
    )

    application.add_handler(
        MessageHandler(
            filters.Regex("^👤 مشتریان$"),
            customers_placeholder,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.Regex("^📦 کالاها$"),
            products_placeholder,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.Regex("^📊 گزارش فروش$"),
            reports_placeholder,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.COMMAND,
            unknown_command,
        )
    )


async def unknown_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "دستور شناخته نشد.\n"
        "برای شروع /start را بزنید."
    )
