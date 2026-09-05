import os

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


# =========================================================
# تنظیمات
# =========================================================

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

CARD_NUMBER = os.getenv(
    "CARD_NUMBER",
    "شماره کارت در تنظیمات Render ثبت نشده است",
)

CARD_HOLDER = os.getenv(
    "CARD_HOLDER",
    "نام صاحب کارت در تنظیمات Render ثبت نشده است",
)

ADMIN_USERNAME = os.getenv(
    "ADMIN_USERNAME",
    "",
)


# =========================================================
# مراحل ثبت فروش
# =========================================================

CUSTOMER = 1
PRODUCT = 2
QUANTITY = 3
PRICE = 4
DISCOUNT = 5
PAYMENT = 6
CONFIRM = 7


# =========================================================
# منوی اصلی
# =========================================================

def main_menu(user_id=None):
    """
    منوی اصلی کاربر.
    پنل مدیریت فقط برای ADMIN_ID نمایش داده می‌شود.
    """

    keyboard = [
        ["🛒 ثبت فروش"],
        ["🧾 ثبت خرید"],
        ["💳 خرید اشتراک"],
        ["📊 گزارش‌ها"],
        ["👨‍💼 ارتباط با پشتیبانی"],
    ]

    if user_id is not None and user_id == ADMIN_ID and ADMIN_ID != 0:
        keyboard.append(["⚙️ پنل مدیریت"])

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
    )


async def show_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user_id = update.effective_user.id

    await update.message.reply_text(
        "منوی حساب‌یار پرو:",
        reply_markup=main_menu(user_id),
    )


# =========================================================
# /start
# =========================================================

async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user_id = update.effective_user.id

    await update.message.reply_text(
        "سلام 👋\n\n"
        "به حساب‌یار پرو خوش آمدید.\n\n"
        "🤖 دستیار مالی و حسابداری هوشمند شما آماده است.\n\n"
        "از منوی زیر انتخاب کنید:",
        reply_markup=main_menu(user_id),
    )


# =========================================================
# ثبت فروش
# =========================================================

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
        "قیمت واحد را وارد کنید:\n\n"
        f"قیمت ثبت‌شده کالا: {default_price:,.0f}"
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
            reply_markup=main_menu(
                update.effective_user.id
            ),
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
            reply_markup=main_menu(
                update.effective_user.id
            ),
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
        reply_markup=main_menu(
            update.effective_user.id
        ),
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
        reply_markup=main_menu(
            update.effective_user.id
        ),
    )

    return ConversationHandler.END


# =========================================================
# خرید
# =========================================================

async def purchase_placeholder(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "🧾 ثبت خرید\n\n"
        "این بخش در حال توسعه است.\n\n"
        "به‌زودی می‌توانید خرید، اقلام خرید، "
        "مبلغ و روش پرداخت را مستقیماً در حساب‌یار پرو ثبت کنید.",
        reply_markup=main_menu(
            update.effective_user.id
        ),
    )


# =========================================================
# خرید اشتراک
# =========================================================

async def subscription_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    keyboard = [
        ["💳 پرداخت اشتراک"],
        ["❌ بازگشت"],
    ]

    await update.message.reply_text(
        "💳 خرید اشتراک حساب‌یار پرو\n\n"
        "برای فعال‌سازی اشتراک، ابتدا مبلغ اشتراک "
        "را طبق پلن انتخابی پرداخت کنید.\n\n"
        "در حال حاضر پرداخت به‌صورت کارت‌به‌کارت انجام می‌شود.\n\n"
        "پس از پرداخت، تصویر رسید را برای ما ارسال کنید "
        "تا توسط مدیریت بررسی و اشتراک شما فعال شود.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
        ),
    )


async def subscription_payment(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    keyboard = [
        ["📋 شماره کارت"],
        ["✅ پرداخت کردم"],
        ["❌ بازگشت"],
    ]

    await update.message.reply_text(
        "💳 اطلاعات پرداخت\n\n"
        f"شماره کارت:\n"
        f"{CARD_NUMBER}\n\n"
        f"به نام:\n"
        f"{CARD_HOLDER}\n\n"
        "پس از انتقال وجه، روی «✅ پرداخت کردم» بزنید "
        "و سپس تصویر رسید را ارسال کنید.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
        ),
    )


async def show_card_number(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "💳 شماره کارت:\n\n"
        f"{CARD_NUMBER}\n\n"
        f"👤 به نام: {CARD_HOLDER}\n\n"
        "لطفاً پس از پرداخت، رسید را ارسال کنید."
    )


async def payment_done(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data["waiting_for_receipt"] = True

    await update.message.reply_text(
        "✅ بسیار خوب.\n\n"
        "لطفاً اکنون تصویر رسید پرداخت را ارسال کنید.\n\n"
        "بعد از دریافت رسید، درخواست شما برای مدیریت ارسال "
        "و پس از تأیید، اشتراک فعال خواهد شد.",
        reply_markup=ReplyKeyboardRemove(),
    )


async def handle_receipt(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user

    if not context.user_data.get(
        "waiting_for_receipt",
        False,
    ):
        return

    if not update.message.photo:
        await update.message.reply_text(
            "❌ لطفاً تصویر رسید پرداخت را ارسال کنید."
        )
        return

    photo = update.message.photo[-1]

    user_name = user.full_name or "بدون نام"

    username = (
        f"@{user.username}"
        if user.username
        else "بدون username"
    )

    admin_message = (
        "🔔 رسید پرداخت جدید\n\n"
        f"👤 نام کاربر: {user_name}\n"
        f"🆔 Telegram ID: {user.id}\n"
        f"📱 Username: {username}\n\n"
        "برای بررسی، رسید بالا را مشاهده کنید."
    )

    if ADMIN_ID:
        try:
            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=photo.file_id,
                caption=admin_message,
            )
        except Exception:
            await update.message.reply_text(
                "⚠️ رسید دریافت شد، اما ارسال آن برای مدیریت "
                "با مشکل مواجه شد.\n"
                "لطفاً با پشتیبانی تماس بگیرید."
            )

            return

    context.user_data["waiting_for_receipt"] = False

    await update.message.reply_text(
        "✅ رسید شما دریافت شد.\n\n"
        "درخواست پرداخت برای مدیریت ارسال شد.\n"
        "پس از بررسی، اشتراک شما فعال خواهد شد.",
        reply_markup=main_menu(user.id),
    )


# =========================================================
# گزارش‌ها
# =========================================================

async def reports_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    keyboard = [
        ["📊 گزارش فروش"],
        ["💰 گزارش دریافت و پرداخت"],
        ["📦 گزارش موجودی"],
        ["👥 مانده مشتریان"],
        ["🔙 بازگشت"],
    ]

    await update.message.reply_text(
        "📊 گزارش‌های حساب‌یار پرو\n\n"
        "گزارش موردنظر را انتخاب کنید:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
        ),
    )


async def sales_report_placeholder(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "📊 گزارش فروش\n\n"
        "ماژول گزارش فروش در حال توسعه است.\n\n"
        "در نسخه بعدی گزارش‌های روزانه، ماهانه، "
        "فروش بر اساس مشتری و فروش بر اساس کالا اضافه می‌شود.",
        reply_markup=main_menu(
            update.effective_user.id
        ),
    )


async def payment_report_placeholder(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "💰 گزارش دریافت و پرداخت در حال توسعه است.",
        reply_markup=main_menu(
            update.effective_user.id
        ),
    )


async def inventory_report_placeholder(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "📦 گزارش موجودی در حال توسعه است.",
        reply_markup=main_menu(
            update.effective_user.id
        ),
    )


async def customer_balance_placeholder(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "👥 گزارش مانده مشتریان در حال توسعه است.",
        reply_markup=main_menu(
            update.effective_user.id
        ),
    )


# =========================================================
# مشتریان
# =========================================================

async def customers_placeholder(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "👤 بخش مشتریان\n\n"
        "مدیریت کامل مشتریان در حال توسعه است.\n\n"
        "در نسخه بعدی امکان افزودن، ویرایش، "
        "جستجو و مشاهده مانده حساب مشتری اضافه خواهد شد.",
        reply_markup=main_menu(
            update.effective_user.id
        ),
    )


# =========================================================
# کالاها
# =========================================================

async def products_placeholder(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "📦 بخش کالاها\n\n"
        "مدیریت کالا و موجودی در حال توسعه است.\n\n"
        "در حال حاضر کالاها باید مستقیماً در دیتابیس ثبت شوند.",
        reply_markup=main_menu(
            update.effective_user.id
        ),
    )


# =========================================================
# پشتیبانی
# =========================================================

async def support_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    support_text = (
        "👨‍💼 ارتباط با پشتیبانی\n\n"
        "اگر در ثبت فروش، خرید، اشتراک یا استفاده از "
        "حساب‌یار پرو مشکلی دارید، پیام خود را ارسال کنید.\n\n"
    )

    if ADMIN_USERNAME:
        support_text += (
            f"📱 پشتیبانی:\n"
            f"{ADMIN_USERNAME}\n\n"
        )

    support_text += (
        "لطفاً شرح مشکل را واضح بنویسید تا بررسی شود."
    )

    await update.message.reply_text(
        support_text,
        reply_markup=main_menu(
            update.effective_user.id
        ),
    )


# =========================================================
# پنل مدیریت
# =========================================================

async def admin_panel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user_id = update.effective_user.id

    if user_id != ADMIN_ID or ADMIN_ID == 0:
        await update.message.reply_text(
            "⛔ شما اجازه دسترسی به پنل مدیریت را ندارید.",
            reply_markup=main_menu(user_id),
        )
        return

    keyboard = [
        ["💳 بررسی پرداخت‌ها"],
        ["👥 کاربران"],
        ["📊 گزارش سیستم"],
        ["🔙 بازگشت"],
    ]

    await update.message.reply_text(
        "⚙️ پنل مدیریت حساب‌یار پرو\n\n"
        "بخش موردنظر را انتخاب کنید:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
        ),
    )


async def admin_payments(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        return

    await update.message.reply_text(
        "💳 بررسی پرداخت‌ها\n\n"
        "رسیدهای پرداخت در حال حاضر مستقیماً "
        "برای مدیریت ارسال می‌شوند.\n\n"
        "سیستم تأیید/رد خودکار پرداخت در مرحله بعد "
        "به دیتابیس اشتراک‌ها متصل خواهد شد.",
        reply_markup=ReplyKeyboardMarkup(
            [
                ["⚙️ پنل مدیریت"],
                ["🔙 بازگشت"],
            ],
            resize_keyboard=True,
        ),
    )


async def admin_users(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        return

    await update.message.reply_text(
        "👥 مدیریت کاربران در حال توسعه است.",
        reply_markup=ReplyKeyboardMarkup(
            [
                ["⚙️ پنل مدیریت"],
                ["🔙 بازگشت"],
            ],
            resize_keyboard=True,
        ),
    )


async def admin_reports(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        return

    await update.message.reply_text(
        "📊 گزارش سیستم در حال توسعه است.",
        reply_markup=ReplyKeyboardMarkup(
            [
                ["⚙️ پنل مدیریت"],
                ["🔙 بازگشت"],
            ],
            resize_keyboard=True,
        ),
    )


# =========================================================
# بازگشت به منوی اصلی
# =========================================================

async def back_to_main(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "منوی اصلی حساب‌یار پرو:",
        reply_markup=main_menu(
            update.effective_user.id
        ),
    )


# =========================================================
# لغو عمومی
# =========================================================

async def cancel_operation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data.clear()

    await update.message.reply_text(
        "عملیات لغو شد.",
        reply_markup=main_menu(
            update.effective_user.id
        ),
    )


# =========================================================
# دستور ناشناخته
# =========================================================

async def unknown_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "دستور شناخته نشد.\n\n"
        "برای شروع /start را بزنید.",
        reply_markup=main_menu(
            update.effective_user.id
        ),
    )


# =========================================================
# ثبت Handlerها
# =========================================================

def register_handlers(application):

    # -----------------------------------------------------
    # Conversation مربوط به ثبت فروش
    # -----------------------------------------------------

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
                    filters.TEXT & ~filters.COMMAND,
                    get_customer,
                )
            ],
            PRODUCT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    get_product,
                )
            ],
            QUANTITY: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    get_quantity,
                )
            ],
            PRICE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    get_price,
                )
            ],
            DISCOUNT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    get_discount,
                )
            ],
            PAYMENT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    get_payment,
                )
            ],
            CONFIRM: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
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

    # -----------------------------------------------------
    # منوی اصلی
    # -----------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.Regex("^🧾 ثبت خرید$"),
            purchase_placeholder,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.Regex("^💳 خرید اشتراک$"),
            subscription_start,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.Regex("^💳 پرداخت اشتراک$"),
            subscription_payment,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.Regex("^📋 شماره کارت$"),
            show_card_number,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.Regex("^✅ پرداخت کردم$"),
            payment_done,
        )
    )

    # -----------------------------------------------------
    # دریافت رسید
    # -----------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            handle_receipt,
        )
    )

    # -----------------------------------------------------
    # گزارش‌ها
    # -----------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.Regex("^📊 گزارش‌ها$"),
            reports_menu,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.Regex("^📊 گزارش فروش$"),
            sales_report_placeholder,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.Regex("^💰 گزارش دریافت و پرداخت$"),
            payment_report_placeholder,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.Regex("^📦 گزارش موجودی$"),
            inventory_report_placeholder,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.Regex("^👥 مانده مشتریان$"),
            customer_balance_placeholder,
        )
    )

    # -----------------------------------------------------
    # مشتریان
    # -----------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.Regex("^👤 مشتریان$"),
            customers_placeholder,
        )
    )

    # -----------------------------------------------------
    # کالاها
    # -----------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.Regex("^📦 کالاها$"),
            products_placeholder,
        )
    )

    # -----------------------------------------------------
    # پشتیبانی
    # -----------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.Regex("^👨‍💼 ارتباط با پشتیبانی$"),
            support_menu,
        )
    )

    # -----------------------------------------------------
    # پنل مدیریت
    # -----------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.Regex("^⚙️ پنل مدیریت$"),
            admin_panel,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.Regex("^💳 بررسی پرداخت‌ها$"),
            admin_payments,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.Regex("^👥 کاربران$"),
            admin_users,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.Regex("^📊 گزارش سیستم$"),
            admin_reports,
        )
    )

    # -----------------------------------------------------
    # بازگشت
    # -----------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.Regex("^🔙 بازگشت$"),
            back_to_main,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.Regex("^❌ بازگشت$"),
            back_to_main,
        )
    )

    # -----------------------------------------------------
    # دستورات ناشناخته
    # -----------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.COMMAND,
            unknown_command,
        )
    )
