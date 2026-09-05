import os
from datetime import date, timedelta
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from app.sales import (
    get_customer_by_name,
    get_product_by_name,
    create_customer,
    create_sale,
)
from app.db import (
    upsert_telegram_user,
    create_subscription_payment,
    attach_receipt_to_payment,
    get_payment,
    get_pending_payments,
    approve_subscription_payment,
    reject_subscription_payment,
    get_subscription_status,
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
SUBSCRIPTION_MONTHLY_PRICE = float(
    os.getenv(
        "SUBSCRIPTION_MONTHLY_PRICE",
        "0",
    )
)
SUBSCRIPTION_MONTHLY_DAYS = int(
    os.getenv(
        "SUBSCRIPTION_MONTHLY_DAYS",
        "30",
    )
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
    keyboard = [
        ["🛒 ثبت فروش"],
        ["🧾 ثبت خرید"],
        ["💳 خرید اشتراک"],
        ["📊 گزارش‌ها"],
        ["👨‍💼 ارتباط با پشتیبانی"],
    ]
    if user_id == ADMIN_ID and ADMIN_ID != 0:
        keyboard.append(
            ["⚙️ پنل مدیریت"]
        )
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
    )
# =========================================================
# /start
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
        "سلام 👋\n\n"
        "به حساب‌یار پرو خوش آمدید.\n\n"
        "🤖 دستیار مالی و حسابداری هوشمند شما آماده است.\n\n"
        "از منوی زیر انتخاب کنید:",
        reply_markup=main_menu(user.id),
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
    customer_name = context.user_data["customer_name"]
    product_name = context.user_data["product_name"]
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
            customer_id=context.user_data["customer_id"],
            product_id=context.user_data["product_id"],
            quantity=context.user_data["quantity"],
            unit_price=context.user_data["unit_price"],
            discount=context.user_data["discount"],
            tax=0,
            payment_method=context.user_data["payment_method"],
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
    invoice_number = result["invoice_number"]
    total = result["total"]
    remaining_stock = result["stock_remaining"]
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
# اشتراک
# =========================================================
async def subscription_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    status = get_subscription_status(
        update.effective_user.id
    )
    text = (
        "💳 خرید اشتراک حساب‌یار پرو\n\n"
        "📦 پلن فعلی: اشتراک ماهانه\n"
        f"⏳ مدت: {SUBSCRIPTION_MONTHLY_DAYS} روز\n"
        f"💰 مبلغ: {SUBSCRIPTION_MONTHLY_PRICE:,.0f}\n\n"
    )
    if status:
        text += (
            "🟢 شما در حال حاضر اشتراک فعال دارید.\n"
            f"📅 پایان اشتراک: {status['end_date']}\n"
            f"⏳ روز باقی‌مانده: {status['remaining_days']}\n\n"
        )
    text += (
        "برای پرداخت، گزینه زیر را انتخاب کنید."
    )
    keyboard = [
        ["💳 پرداخت اشتراک"],
        ["📅 وضعیت اشتراک"],
        ["🔙 بازگشت"],
    ]
    await update.message.reply_text(
        text,
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
        ),
    )
async def subscription_payment(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if SUBSCRIPTION_MONTHLY_PRICE <= 0:
        await update.message.reply_text(
            "⚠️ مبلغ اشتراک هنوز در تنظیمات سیستم ثبت نشده است.\n\n"
            "مدیریت باید متغیر SUBSCRIPTION_MONTHLY_PRICE "
            "را در Render تنظیم کند.",
            reply_markup=main_menu(
                update.effective_user.id
            ),
        )
        return
    user = update.effective_user
    upsert_telegram_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
    )
    payment_id = create_subscription_payment(
        telegram_id=user.id,
        plan_code="monthly",
        plan_name="اشتراک ماهانه",
        amount=SUBSCRIPTION_MONTHLY_PRICE,
    )
    context.user_data["payment_id"] = payment_id
    context.user_data["waiting_for_receipt"] = False
    keyboard = [
        ["📋 شماره کارت"],
        ["✅ پرداخت کردم"],
        ["🔙 بازگشت"],
    ]
    await update.message.reply_text(
        "💳 درخواست پرداخت ایجاد شد.\n\n"
        f"🧾 شماره درخواست: #{payment_id}\n"
        f"💰 مبلغ: {SUBSCRIPTION_MONTHLY_PRICE:,.0f}\n\n"
        f"💳 شماره کارت:\n{CARD_NUMBER}\n\n"
        f"👤 به نام:\n{CARD_HOLDER}\n\n"
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
        "💳 اطلاعات کارت\n\n"
        f"شماره کارت:\n{CARD_NUMBER}\n\n"
        f"👤 به نام:\n{CARD_HOLDER}\n\n"
        f"💰 مبلغ اشتراک:\n"
        f"{SUBSCRIPTION_MONTHLY_PRICE:,.0f}"
    )
async def payment_done(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    payment_id = context.user_data.get(
        "payment_id"
    )
    if not payment_id:
        await update.message.reply_text(
            "⚠️ ابتدا گزینه «💳 پرداخت اشتراک» را انتخاب کنید."
        )
        return
    context.user_data["waiting_for_receipt"] = True
    await update.message.reply_text(
        "📸 لطفاً اکنون تصویر رسید پرداخت را ارسال کنید.\n\n"
        f"🧾 شماره درخواست: #{payment_id}\n\n"
        "رسید پس از دریافت برای مدیریت ارسال می‌شود."
    )
async def handle_receipt(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not context.user_data.get(
        "waiting_for_receipt",
        False,
    ):
        return
    user = update.effective_user
    payment_id = context.user_data.get(
        "payment_id"
    )
    if not payment_id:
        await update.message.reply_text(
            "❌ درخواست پرداخت پیدا نشد.\n"
            "لطفاً دوباره از بخش خرید اشتراک شروع کنید."
        )
        return
    if not update.message.photo:
        await update.message.reply_text(
            "❌ لطفاً تصویر رسید پرداخت را ارسال کنید."
        )
        return
    payment = get_payment(payment_id)
    if payment is None:
        await update.message.reply_text(
            "❌ درخواست پرداخت پیدا نشد."
        )
        return
    photo = update.message.photo[-1]
    attached = attach_receipt_to_payment(
        payment_id=payment_id,
        receipt_file_id=photo.file_id,
        receipt_file_unique_id=photo.file_unique_id,
    )
    if not attached:
        await update.message.reply_text(
            "❌ این درخواست پرداخت قبلاً بررسی شده "
            "یا معتبر نیست."
        )
        return
    username = (
        f"@{user.username}"
        if user.username
        else "بدون username"
    )
    admin_caption = (
        "🔔 رسید پرداخت جدید\n\n"
        f"🧾 شماره درخواست: #{payment_id}\n"
        f"👤 نام: {user.full_name}\n"
        f"🆔 Telegram ID: {user.id}\n"
        f"📱 Username: {username}\n"
        f"📦 پلن: {payment['plan_name']}\n"
        f"💰 مبلغ: {payment['amount']:,.0f}\n\n"
        "لطفاً رسید را بررسی کنید."
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
    if ADMIN_ID == 0:
        await update.message.reply_text(
            "⚠️ رسید دریافت شد، اما ADMIN_ID در تنظیمات "
            "سیستم ثبت نشده است."
        )
        return
    try:
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo.file_id,
            caption=admin_caption,
            reply_markup=keyboard,
        )
    except Exception as exc:
        await update.message.reply_text(
            "⚠️ رسید در سیستم ثبت شد، اما ارسال آن برای "
            "مدیریت با مشکل مواجه شد.\n\n"
            f"خطا: {exc}"
        )
        return
    context.user_data["waiting_for_receipt"] = False
    await update.message.reply_text(
        "✅ رسید شما با موفقیت دریافت شد.\n\n"
        f"🧾 شماره درخواست: #{payment_id}\n"
        "📨 رسید برای مدیریت ارسال شد.\n\n"
        "پس از تأیید، اشتراک شما به‌صورت خودکار فعال می‌شود.",
        reply_markup=main_menu(user.id),
    )
# =========================================================
# وضعیت اشتراک
# =========================================================
async def subscription_status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    status = get_subscription_status(
        update.effective_user.id
    )
    if not status:
        await update.message.reply_text(
            "🔴 شما در حال حاضر اشتراک فعال ندارید.\n\n"
            "برای خرید اشتراک از گزینه «💳 خرید اشتراک» استفاده کنید.",
            reply_markup=main_menu(
                update.effective_user.id
            ),
        )
        return
    await update.message.reply_text(
        "📅 وضعیت اشتراک\n\n"
        f"📦 پلن: {status['plan_name']}\n"
        f"🟢 وضعیت: فعال\n"
        f"📅 شروع: {status['start_date']}\n"
        f"📅 پایان: {status['end_date']}\n"
        f"⏳ روز باقی‌مانده: {status['remaining_days']}",
        reply_markup=main_menu(
            update.effective_user.id
        ),
    )
# =========================================================
# تأیید / رد پرداخت توسط ادمین
# =========================================================
async def admin_payment_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()
    if update.effective_user.id != ADMIN_ID:
        await query.answer(
            "⛔ شما دسترسی مدیریت ندارید.",
            show_alert=True,
        )
        return
    data = query.data or ""
    if ":" not in data:
        return
    action, payment_id_text = data.split(
        ":",
        1,
    )
    try:
        payment_id = int(payment_id_text)
    except ValueError:
        await query.edit_message_caption(
            caption="❌ شناسه پرداخت نامعتبر است."
        )
        return
    payment = get_payment(payment_id)
    if payment is None:
        await query.edit_message_caption(
            caption="❌ درخواست پرداخت پیدا نشد."
        )
        return
    if payment["status"] != "pending":
        await query.edit_message_caption(
            caption=(
                f"⚠️ این درخواست قبلاً بررسی شده است.\n\n"
                f"وضعیت: {payment['status']}"
            )
        )
        return
    if action == "pay_approve":
        today = date.today()
        start_date = today
        end_date = today + timedelta(
            days=SUBSCRIPTION_MONTHLY_DAYS
        )
        success = approve_subscription_payment(
            payment_id=payment_id,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            reviewed_by=ADMIN_ID,
        )
        if not success:
            await query.edit_message_caption(
                caption="❌ تأیید پرداخت انجام نشد."
            )
            return
        await query.edit_message_caption(
            caption=(
                "✅ پرداخت تأیید شد.\n\n"
                f"🧾 درخواست: #{payment_id}\n"
                f"📦 پلن: {payment['plan_name']}\n"
                f"💰 مبلغ: {payment['amount']:,.0f}\n"
                f"📅 شروع: {start_date.isoformat()}\n"
                f"📅 پایان: {end_date.isoformat()}"
            )
        )
        try:
            await context.bot.send_message(
                chat_id=payment["telegram_id"],
                text=(
                    "🎉 پرداخت شما تأیید شد.\n\n"
                    "اشتراک حساب‌یار پرو با موفقیت فعال شد.\n\n"
                    f"📦 پلن: {payment['plan_name']}\n"
                    f"📅 شروع: {start_date.isoformat()}\n"
                    f"📅 پایان: {end_date.isoformat()}\n\n"
                    "از حساب‌یار پرو استفاده کنید."
                ),
                reply_markup=main_menu(
                    payment["telegram_id"]
                ),
            )
        except Exception:
            pass
        return
    if action == "pay_reject":
        success = reject_subscription_payment(
            payment_id=payment_id,
            reviewed_by=ADMIN_ID,
            rejection_reason="رسید پرداخت توسط مدیریت تأیید نشد.",
        )
        if not success:
            await query.edit_message_caption(
                caption="❌ رد پرداخت انجام نشد."
            )
            return
        await query.edit_message_caption(
            caption=(
                "❌ پرداخت رد شد.\n\n"
                f"🧾 درخواست: #{payment_id}\n"
                f"👤 کاربر: {payment['first_name'] or 'بدون نام'}"
            )
        )
        try:
            await context.bot.send_message(
                chat_id=payment["telegram_id"],
                text=(
                    "❌ پرداخت شما تأیید نشد.\n\n"
                    f"🧾 شماره درخواست: #{payment_id}\n\n"
                    "لطفاً اطلاعات پرداخت و تصویر رسید را "
                    "بررسی کرده و در صورت نیاز مجدداً اقدام کنید."
                ),
                reply_markup=main_menu(
                    payment["telegram_id"]
                ),
            )
        except Exception:
            pass
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
        "ماژول گزارش فروش در حال توسعه است.",
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
        "مدیریت کامل مشتریان در حال توسعه است.",
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
        "مدیریت کالا و موجودی در حال توسعه است.",
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
        "لطفاً شرح مشکل را واضح بنویسید."
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
    payments = get_pending_payments()
    if not payments:
        await update.message.reply_text(
            "✅ هیچ پرداخت در انتظار بررسی وجود ندارد.",
            reply_markup=ReplyKeyboardMarkup(
                [
                    ["⚙️ پنل مدیریت"],
                    ["🔙 بازگشت"],
                ],
                resize_keyboard=True,
            ),
        )
        return
    text = "💳 پرداخت‌های در انتظار بررسی:\n\n"
    for payment in payments[:20]:
        text += (
            f"🧾 #{payment['id']}\n"
            f"👤 {payment['first_name'] or 'بدون نام'}\n"
            f"💰 {payment['amount']:,.0f}\n"
            f"📦 {payment['plan_name']}\n\n"
        )
    text += (
        "برای مشاهده و بررسی هر رسید، "
        "رسید پس از ارسال کاربر برای شما ارسال می‌شود."
    )
    await update.message.reply_text(
        text,
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
    if update.effective_user.id != ADMIN_ID:
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
    if update.effective_user.id != ADMIN_ID:
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
# بازگشت
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
    # ثبت فروش
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
    # اشتراک
    # -----------------------------------------------------
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
    application.add_handler(
        MessageHandler(
            filters.Regex("^📅 وضعیت اشتراک$"),
            subscription_status,
        )
    )
    # -----------------------------------------------------
    # رسید
    # -----------------------------------------------------
    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            handle_receipt,
        )
    )
    # -----------------------------------------------------
    # دکمه‌های تأیید/رد ادمین
    # -----------------------------------------------------
    application.add_handler(
        CallbackQueryHandler(
            admin_payment_callback,
            pattern=r"^pay_(approve|reject):\d+$",
        )
    )
    # -----------------------------------------------------
    # خرید
    # -----------------------------------------------------
    application.add_handler(
        MessageHandler(
            filters.Regex("^🧾 ثبت خرید$"),
            purchase_placeholder,
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
