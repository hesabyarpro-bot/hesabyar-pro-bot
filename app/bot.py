import os
import sqlite3
from datetime import date, timedelta

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

from app.db import (
    upsert_telegram_user,
    get_telegram_user,
    create_subscription_payment,
    attach_receipt_to_payment,
    get_payment,
    get_pending_payments,
    approve_subscription_payment,
    reject_subscription_payment,
    get_subscription_status,
    get_connection
)

from app.purchases import PurchaseService


# ============================================================
# Configuration
# ============================================================

ADMIN_TELEGRAM_ID = int(
    os.getenv(
        "ADMIN_TELEGRAM_ID",
        "8806709666"
    )
)

CARD_NUMBER = os.getenv(
    "CARD_NUMBER",
    "در تنظیمات Render وارد نشده است"
)

CARD_HOLDER = os.getenv(
    "CARD_HOLDER",
    "حساب‌یار پرو"
)

SUBSCRIPTION_MONTHLY_PRICE = int(
    os.getenv(
        "SUBSCRIPTION_MONTHLY_PRICE",
        "0"
    )
)

SUBSCRIPTION_MONTHLY_DAYS = int(
    os.getenv(
        "SUBSCRIPTION_MONTHLY_DAYS",
        "30"
    )
)


# ============================================================
# Conversation States
# ============================================================

(
    PURCHASE_SUPPLIER,
    PURCHASE_PRODUCT,
    PURCHASE_QUANTITY,
    PURCHASE_PRICE,
    PURCHASE_DISCOUNT,
    PURCHASE_PAYMENT,
    PURCHASE_CONFIRM
) = range(7)


# ============================================================
# Utility
# ============================================================

def normalize_digits(text):

    if text is None:
        return ""

    mapping = str.maketrans(
        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
        "01234567890123456789"
    )

    return str(text).translate(mapping)


def parse_int(text):

    text = normalize_digits(text)

    text = (
        text.replace(",", "")
        .replace("٬", "")
        .replace(" ", "")
    )

    return int(text)


def parse_float(text):

    text = normalize_digits(text)

    text = (
        text.replace(",", "")
        .replace("٬", "")
        .replace(" ", "")
    )

    return float(text)


def money(value):

    return f"{int(value):,}"


# ============================================================
# Main Menu
# ============================================================

def main_menu(is_admin=False):

    rows = [
        ["🛒 ثبت فروش", "🧾 ثبت خرید"],
        ["👥 مشتریان", "📦 کالاها"],
        ["📊 گزارش‌ها", "💳 خرید اشتراک"],
        ["👨‍💼 پشتیبانی", "⚙️ وضعیت اشتراک"]
    ]

    if is_admin:
        rows.append(
            ["🔐 پنل مدیریت"]
        )

    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True
    )


# ============================================================
# /start
# ============================================================

async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    upsert_telegram_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )

    is_admin = (
        user.id == ADMIN_TELEGRAM_ID
    )

    text = (
        "سلام 👋\n\n"
        "به «حساب‌یار پرو» خوش آمدید.\n"
        "حسابداری حرفه‌ای، ساده و همیشه در دسترس.\n\n"
        "از منوی زیر عملیات موردنظر را انتخاب کنید."
    )

    await update.message.reply_text(
        text,
        reply_markup=main_menu(is_admin)
    )


# ============================================================
# Purchase: Start
# ============================================================

async def purchase_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data["purchase"] = {
        "items": [],
        "discount": 0,
        "tax": 0
    }

    conn = get_connection()

    try:

        suppliers = conn.execute("""
            SELECT id, name, phone
            FROM suppliers
            WHERE active = 1
            ORDER BY name
            LIMIT 50
        """).fetchall()

    finally:
        conn.close()

    if not suppliers:

        await update.message.reply_text(
            "هنوز تأمین‌کننده‌ای ثبت نشده است.\n"
            "ابتدا یک تأمین‌کننده ایجاد کنید."
        )

        return ConversationHandler.END

    keyboard = []

    for supplier in suppliers:

        label = supplier["name"]

        if supplier["phone"]:
            label += f" - {supplier['phone']}"

        keyboard.append([
            InlineKeyboardButton(
                label,
                callback_data=f"pur_supplier:{supplier['id']}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "❌ انصراف",
            callback_data="pur_cancel"
        )
    ])

    await update.message.reply_text(
        "🧾 ثبت خرید\n\n"
        "تأمین‌کننده را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )

    return PURCHASE_SUPPLIER


# ============================================================
# Purchase: Supplier
# ============================================================

async def purchase_supplier_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
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

    conn = get_connection()

    try:

        supplier = conn.execute("""
            SELECT *
            FROM suppliers
            WHERE id = ?
              AND active = 1
        """, (
            supplier_id,
        )).fetchone()

        products = conn.execute("""
            SELECT id, name, sku, unit
            FROM products
            WHERE active = 1
            ORDER BY name
            LIMIT 100
        """).fetchall()

    finally:
        conn.close()

    if not supplier:

        await query.edit_message_text(
            "تأمین‌کننده پیدا نشد."
        )

        return ConversationHandler.END

    context.user_data["purchase"][
        "supplier_id"
    ] = supplier_id

    context.user_data["purchase"][
        "supplier_name"
    ] = supplier["name"]

    if not products:

        await query.edit_message_text(
            "هیچ کالای فعالی در سیستم وجود ندارد."
        )

        return ConversationHandler.END

    keyboard = []

    for product in products:

        label = product["name"]

        if product["sku"]:
            label += f" | {product['sku']}"

        keyboard.append([
            InlineKeyboardButton(
                label,
                callback_data=f"pur_product:{product['id']}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "❌ انصراف",
            callback_data="pur_cancel"
        )
    ])

    await query.edit_message_text(
        f"تأمین‌کننده: {supplier['name']}\n\n"
        "کالا را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )

    return PURCHASE_PRODUCT


# ============================================================
# Purchase: Product
# ============================================================

async def purchase_product_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
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

    conn = get_connection()

    try:

        product = conn.execute("""
            SELECT *
            FROM products
            WHERE id = ?
              AND active = 1
        """, (
            product_id,
        )).fetchone()

    finally:
        conn.close()

    if not product:

        await query.edit_message_text(
            "کالا پیدا نشد."
        )

        return ConversationHandler.END

    purchase = context.user_data["purchase"]

    purchase["current_product_id"] = product_id
    purchase["current_product_name"] = product["name"]
    purchase["current_unit"] = product["unit"]

    await query.edit_message_text(
        f"کالا: {product['name']}\n"
        f"واحد: {product['unit']}\n\n"
        "تعداد خرید را وارد کنید:"
    )

    return PURCHASE_QUANTITY


# ============================================================
# Purchase: Quantity
# ============================================================

async def purchase_quantity(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    try:

        quantity = parse_float(
            update.message.text
        )

        if quantity <= 0:
            raise ValueError

    except Exception:

        await update.message.reply_text(
            "❌ تعداد نامعتبر است.\n"
            "مثال: 10"
        )

        return PURCHASE_QUANTITY

    purchase = context.user_data["purchase"]

    purchase["current_quantity"] = quantity

    await update.message.reply_text(
        "قیمت خرید هر واحد را به تومان وارد کنید:\n\n"
        "مثال:\n"
        "150000"
    )

    return PURCHASE_PRICE


# ============================================================
# Purchase: Price
# ============================================================

async def purchase_price(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    try:

        price = parse_int(
            update.message.text
        )

        if price < 0:
            raise ValueError

    except Exception:

        await update.message.reply_text(
            "❌ قیمت نامعتبر است."
        )

        return PURCHASE_PRICE

    purchase = context.user_data["purchase"]

    purchase["current_price"] = price

    await update.message.reply_text(
        "تخفیف این قلم را وارد کنید.\n"
        "اگر تخفیف ندارد، عدد 0 را بفرستید."
    )

    return PURCHASE_DISCOUNT


# ============================================================
# Purchase: Discount
# ============================================================

async def purchase_discount(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    try:

        discount = parse_int(
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

    item = {
        "product_id": purchase["current_product_id"],
        "product_name": purchase["current_product_name"],
        "unit": purchase["current_unit"],
        "quantity": purchase["current_quantity"],
        "unit_price": purchase["current_price"],
        "discount": discount,
        "tax": 0
    }

    purchase["items"].append(item)

    keyboard = [
        [
            InlineKeyboardButton(
                "➕ افزودن کالای دیگر",
                callback_data="pur_add_item"
            )
        ],
        [
            InlineKeyboardButton(
                "➡️ ادامه ثبت خرید",
                callback_data="pur_continue"
            )
        ],
        [
            InlineKeyboardButton(
                "❌ لغو",
                callback_data="pur_cancel"
            )
        ]
    ]

    await update.message.reply_text(
        "قلم کالا ثبت شد.\n\n"
        "می‌توانید کالای دیگری اضافه کنید یا ادامه دهید.",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )

    return PURCHASE_PRODUCT


# ============================================================
# Purchase: Continue
# ============================================================

async def purchase_continue_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query
    await query.answer()

    purchase = context.user_data["purchase"]

    if not purchase["items"]:

        await query.edit_message_text(
            "حداقل یک کالا باید ثبت شود."
        )

        return PURCHASE_PRODUCT

    subtotal = 0

    lines = []

    for index, item in enumerate(
        purchase["items"],
        start=1
    ):

        gross = int(
            item["quantity"]
            * item["unit_price"]
        )

        total = max(
            0,
            gross - item["discount"]
        )

        subtotal += total

        lines.append(
            f"{index}. {item['product_name']}\n"
            f"   تعداد: {item['quantity']:g}\n"
            f"   قیمت واحد: {money(item['unit_price'])}\n"
            f"   تخفیف: {money(item['discount'])}\n"
            f"   مبلغ: {money(total)} تومان"
        )

    purchase["subtotal"] = subtotal

    text = (
        "📋 خلاصه خرید\n\n"
        f"تأمین‌کننده: {purchase['supplier_name']}\n\n"
        + "\n\n".join(lines)
        + "\n\n"
        f"جمع خرید: {money(subtotal)} تومان\n\n"
        "روش پرداخت را انتخاب کنید:"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "💵 نقدی",
                callback_data="pur_pay:cash"
            ),
            InlineKeyboardButton(
                "🏦 بانکی",
                callback_data="pur_pay:bank"
            )
        ],
        [
            InlineKeyboardButton(
                "🧾 نسیه / پرداختنی",
                callback_data="pur_pay:credit"
            )
        ],
        [
            InlineKeyboardButton(
                "❌ انصراف",
                callback_data="pur_cancel"
            )
        ]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )

    return PURCHASE_PAYMENT


# ============================================================
# Purchase: Add another item
# ============================================================

async def purchase_add_item_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query
    await query.answer()

    conn = get_connection()

    try:

        products = conn.execute("""
            SELECT id, name, sku, unit
            FROM products
            WHERE active = 1
            ORDER BY name
            LIMIT 100
        """).fetchall()

    finally:
        conn.close()

    keyboard = []

    for product in products:

        label = product["name"]

        if product["sku"]:
            label += f" | {product['sku']}"

        keyboard.append([
            InlineKeyboardButton(
                label,
                callback_data=f"pur_product:{product['id']}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "➡️ ادامه ثبت خرید",
            callback_data="pur_continue"
        )
    ])

    await query.edit_message_text(
        "کالای بعدی را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )

    return PURCHASE_PRODUCT


# ============================================================
# Purchase: Payment Method
# ============================================================

async def purchase_payment_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query
    await query.answer()

    payment_method = (
        query.data.split(":")[1]
    )

    purchase = context.user_data["purchase"]

    purchase["payment_method"] = (
        payment_method
    )

    if payment_method == "cash":
        payment_label = "نقدی"

    elif payment_method == "bank":
        payment_label = "بانکی"

    else:
        payment_label = "نسیه / پرداختنی"

    text = (
        "⚠️ تأیید نهایی خرید\n\n"
        f"تأمین‌کننده: {purchase['supplier_name']}\n"
        f"تعداد اقلام: {len(purchase['items'])}\n"
        f"جمع خرید: {money(purchase['subtotal'])} تومان\n"
        f"روش پرداخت: {payment_label}\n\n"
        "با تأیید، عملیات زیر انجام می‌شود:\n"
        "✅ ثبت فاکتور خرید\n"
        "✅ افزایش موجودی کالا\n"
        "✅ ثبت گردش انبار\n"
        "✅ ثبت سند حسابداری\n\n"
        "آیا تأیید می‌کنید؟"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ تأیید و ثبت",
                callback_data="pur_confirm"
            )
        ],
        [
            InlineKeyboardButton(
                "❌ لغو",
                callback_data="pur_cancel"
            )
        ]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )

    return PURCHASE_CONFIRM


# ============================================================
# Purchase: Confirm
# ============================================================

async def purchase_confirm_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query
    await query.answer()

    if query.data == "pur_cancel":

        context.user_data.pop(
            "purchase",
            None
        )

        await query.edit_message_text(
            "ثبت خرید لغو شد."
        )

        return ConversationHandler.END

    purchase = context.user_data.get(
        "purchase"
    )

    if not purchase:

        await query.edit_message_text(
            "اطلاعات خرید پیدا نشد. دوباره تلاش کنید."
        )

        return ConversationHandler.END

    try:

        service = PurchaseService()

        result = service.create_purchase(
            supplier_id=purchase["supplier_id"],
            items=purchase["items"],
            discount=purchase.get(
                "discount",
                0
            ),
            tax=purchase.get(
                "tax",
                0
            ),
            payment_method=purchase[
                "payment_method"
            ],
            notes="ثبت از طریق ربات حساب‌یار پرو"
        )

    except Exception as exc:

        await query.edit_message_text(
            "❌ ثبت خرید انجام نشد.\n\n"
            f"خطا: {str(exc)}"
        )

        return ConversationHandler.END

    invoice_id = result["invoice_id"]

    await query.edit_message_text(
        "✅ خرید با موفقیت ثبت شد.\n\n"
        f"شماره فاکتور: {invoice_id}\n"
        f"تأمین‌کننده: {purchase['supplier_name']}\n"
        f"جمع خرید: {money(result['total'])} تومان\n\n"
        "موجودی کالا و سند حسابداری نیز ثبت شد."
    )

    context.user_data.pop(
        "purchase",
        None
    )

    return ConversationHandler.END


# ============================================================
# Purchase: Cancel by text
# ============================================================

async def purchase_cancel_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data.pop(
        "purchase",
        None
    )

    await update.message.reply_text(
        "عملیات لغو شد."
    )

    return ConversationHandler.END


# ============================================================
# Subscription
# ============================================================

async def subscription_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    price = SUBSCRIPTION_MONTHLY_PRICE

    if price <= 0:

        await update.message.reply_text(
            "💳 خرید اشتراک\n\n"
            "قیمت اشتراک هنوز در تنظیمات سیستم "
            "ثبت نشده است."
        )

        return

    text = (
        "💳 خرید اشتراک\n\n"
        "طرح فعال فعلی:\n"
        "📅 اشتراک ماهانه\n"
        f"💰 مبلغ: {money(price)} تومان\n"
        f"⏱ مدت: {SUBSCRIPTION_MONTHLY_DAYS} روز\n\n"
        "برای شروع پرداخت، دکمه زیر را بزنید."
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "💳 شروع پرداخت",
                callback_data="sub_start"
            )
        ]
    ]

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


async def subscription_start_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query
    await query.answer()

    user = update.effective_user

    telegram_user_id = upsert_telegram_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )

    if SUBSCRIPTION_MONTHLY_PRICE <= 0:

        await query.edit_message_text(
            "قیمت اشتراک هنوز تنظیم نشده است."
        )

        return

    payment_id = create_subscription_payment(
        telegram_user_id=telegram_user_id,
        plan_code="monthly",
        plan_name="اشتراک ماهانه",
        amount=SUBSCRIPTION_MONTHLY_PRICE
    )

    text = (
        "💳 اطلاعات پرداخت\n\n"
        f"مبلغ: {money(SUBSCRIPTION_MONTHLY_PRICE)} تومان\n\n"
        f"شماره کارت:\n{CARD_NUMBER}\n\n"
        f"به نام:\n{CARD_HOLDER}\n\n"
        f"کد پرداخت شما: {payment_id}\n\n"
        "پس از انتقال وجه، تصویر رسید را همین‌جا ارسال کنید."
    )

    await query.edit_message_text(
        text
    )


# ============================================================
# Receipt Handler
# ============================================================

async def receipt_photo_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    telegram_user = get_telegram_user(
        user.id
    )

    if not telegram_user:
        upsert_telegram_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )

        telegram_user = get_telegram_user(
            user.id
        )

    photo = update.message.photo[-1]

    # آخرین پرداخت pending
    conn = get_connection()

    try:

        payment = conn.execute("""
            SELECT *
            FROM subscription_payments
            WHERE telegram_user_id = ?
              AND status = 'pending'
            ORDER BY id DESC
            LIMIT 1
        """, (
            telegram_user["id"],
        )).fetchone()

    finally:
        conn.close()

    if not payment:

        await update.message.reply_text(
            "پرداخت در انتظار رسیدی برای شما پیدا نشد."
        )

        return

    attach_receipt_to_payment(
        payment_id=payment["id"],
        receipt_file_id=photo.file_id,
        receipt_file_unique_id=photo.file_unique_id
    )

    # --------------------------------------------------------
    # Send to Admin
    # --------------------------------------------------------

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ تأیید پرداخت",
                callback_data=f"pay_approve:{payment['id']}"
            ),
            InlineKeyboardButton(
                "❌ رد پرداخت",
                callback_data=f"pay_reject:{payment['id']}"
            )
        ]
    ]

    caption = (
        "💳 رسید پرداخت جدید\n\n"
        f"کد پرداخت: {payment['id']}\n"
        f"کاربر: {user.first_name or '-'}\n"
        f"Username: @{user.username or '-'}\n"
        f"مبلغ: {money(payment['amount'])} تومان\n"
        f"طرح: {payment['plan_name']}"
    )

    try:

        await context.bot.send_photo(
            chat_id=ADMIN_TELEGRAM_ID,
            photo=photo.file_id,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

    except Exception:

        await update.message.reply_text(
            "رسید ذخیره شد، اما ارسال آن برای مدیر "
            "با مشکل مواجه شد."
        )

        return

    await update.message.reply_text(
        "✅ رسید شما دریافت شد.\n\n"
        "پس از بررسی توسط مدیریت، اشتراک شما فعال خواهد شد."
    )


# ============================================================
# Admin Payments
# ============================================================

async def admin_payments(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_user.id != ADMIN_TELEGRAM_ID:

        await update.message.reply_text(
            "⛔ دسترسی غیرمجاز."
        )

        return

    payments = get_pending_payments()

    if not payments:

        await update.message.reply_text(
            "در حال حاضر پرداخت در انتظاری وجود ندارد."
        )

        return

    for payment in payments:

        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ تأیید",
                    callback_data=f"pay_approve:{payment['id']}"
                ),
                InlineKeyboardButton(
                    "❌ رد",
                    callback_data=f"pay_reject:{payment['id']}"
                )
            ]
        ]

        text = (
            "💳 پرداخت در انتظار\n\n"
            f"کد: {payment['id']}\n"
            f"کاربر: {payment['first_name'] or '-'}\n"
            f"Username: @{payment['username'] or '-'}\n"
            f"مبلغ: {money(payment['amount'])} تومان\n"
            f"طرح: {payment['plan_name']}"
        )

        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )


# ============================================================
# Admin Payment Callback
# ============================================================

async def admin_payment_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query
    await query.answer()

    if update.effective_user.id != ADMIN_TELEGRAM_ID:

        await query.answer(
            "دسترسی غیرمجاز",
            show_alert=True
        )

        return

    action, payment_id_text = (
        query.data.split(":")
    )

    payment_id = int(
        payment_id_text
    )

    payment = get_payment(
        payment_id
    )

    if not payment:

        await query.edit_message_text(
            "پرداخت پیدا نشد."
        )

        return

    if action == "pay_approve":

        start_date = date.today()

        end_date = (
            start_date
            + timedelta(
                days=SUBSCRIPTION_MONTHLY_DAYS
            )
        )

        actual_start, actual_end = (
            approve_subscription_payment(
                payment_id=payment_id,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                reviewed_by=update.effective_user.id
            )
        )

        await query.edit_message_text(
            "✅ پرداخت تأیید شد.\n\n"
            f"کد پرداخت: {payment_id}\n"
            f"اشتراک: {payment['plan_name']}\n"
            f"شروع: {actual_start}\n"
            f"پایان: {actual_end}"
        )

        try:

            await context.bot.send_message(
                chat_id=payment["telegram_id"],
                text=(
                    "🎉 پرداخت شما تأیید شد.\n\n"
                    f"اشتراک «{payment['plan_name']}» فعال شد.\n"
                    f"شروع: {actual_start}\n"
                    f"پایان: {actual_end}"
                )
            )

        except Exception:
            pass

    elif action == "pay_reject":

        reject_subscription_payment(
            payment_id=payment_id,
            reviewed_by=update.effective_user.id,
            reason="رد توسط مدیریت"
        )

        await query.edit_message_text(
            "❌ پرداخت رد شد."
        )

        try:

            await context.bot.send_message(
                chat_id=payment["telegram_id"],
                text=(
                    "❌ رسید پرداخت شما تأیید نشد.\n\n"
                    "لطفاً اطلاعات پرداخت را بررسی کرده "
                    "و در صورت نیاز مجدداً اقدام کنید."
                )
            )

        except Exception:
            pass


# ============================================================
# Subscription Status
# ============================================================

async def subscription_status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    status = get_subscription_status(
        update.effective_user.id
    )

    if not status:

        await update.message.reply_text(
            "📊 وضعیت اشتراک\n\n"
            "در حال حاضر اشتراک فعالی ندارید."
        )

        return

    await update.message.reply_text(
        "📊 وضعیت اشتراک\n\n"
        f"طرح: {status['plan_name']}\n"
        f"شروع: {status['start_date']}\n"
        f"پایان: {status['end_date']}\n"
        f"روزهای باقی‌مانده: {status['remaining_days']}"
    )


# ============================================================
# Simple Menu Handlers
# ============================================================

async def placeholder_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = update.message.text

    if text == "👥 مشتریان":

        await update.message.reply_text(
            "👥 بخش مشتریان فعال است.\n"
            "مدیریت کامل مشتریان در مرحله بعد توسعه داده می‌شود."
        )

    elif text == "📦 کالاها":

        await update.message.reply_text(
            "📦 بخش کالاها فعال است.\n"
            "مدیریت کامل کالاها در مرحله بعد توسعه داده می‌شود."
        )

    elif text == "🛒 ثبت فروش":

        await update.message.reply_text(
            "🛒 ماژول ثبت فروش در حال آماده‌سازی است."
        )

    elif text == "📊 گزارش‌ها":

        await update.message.reply_text(
            "📊 ماژول گزارش‌ها در مرحله بعد تکمیل می‌شود."
        )

    elif text == "👨‍💼 پشتیبانی":

        await update.message.reply_text(
            "👨‍💼 برای ارتباط با پشتیبانی پیام خود را ارسال کنید."
        )


# ============================================================
# Register Handlers
# ============================================================

def register_handlers(
    application: Application
):

    # --------------------------------------------------------
    # Purchase Conversation
    # --------------------------------------------------------

    purchase_conversation = ConversationHandler(

        entry_points=[
            MessageHandler(
                filters.Regex("^🧾 ثبت خرید$"),
                purchase_start
            )
        ],

        states={

            PURCHASE_SUPPLIER: [
                CallbackQueryHandler(
                    purchase_supplier_callback,
                    pattern=r"^pur_(supplier|cancel):?"
                )
            ],

            PURCHASE_PRODUCT: [
                CallbackQueryHandler(
                    purchase_add_item_callback,
                    pattern=r"^pur_add_item$"
                ),
                CallbackQueryHandler(
                    purchase_continue_callback,
                    pattern=r"^pur_continue$"
                ),
                CallbackQueryHandler(
                    purchase_product_callback,
                    pattern=r"^pur_product:"
                ),
                CallbackQueryHandler(
                    purchase_confirm_callback,
                    pattern=r"^pur_cancel$"
                )
            ],

            PURCHASE_QUANTITY: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    purchase_quantity
                )
            ],

            PURCHASE_PRICE: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    purchase_price
                )
            ],

            PURCHASE_DISCOUNT: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    purchase_discount
                )
            ],

            PURCHASE_PAYMENT: [
                CallbackQueryHandler(
                    purchase_payment_callback,
                    pattern=r"^pur_pay:"
                ),
                CallbackQueryHandler(
                    purchase_confirm_callback,
                    pattern=r"^pur_cancel$"
                )
            ],

            PURCHASE_CONFIRM: [
                CallbackQueryHandler(
                    purchase_confirm_callback,
                    pattern=r"^pur_(confirm|cancel)$"
                )
            ]
        },

        fallbacks=[
            MessageHandler(
                filters.Regex("^❌ لغو$"),
                purchase_cancel_text
            )
        ],

        allow_reentry=True
    )

    application.add_handler(
        purchase_conversation
    )

    # --------------------------------------------------------
    # Subscription
    # --------------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.Regex("^💳 خرید اشتراک$"),
            subscription_menu
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            subscription_start_callback,
            pattern=r"^sub_start$"
        )
    )

    application.add_handler(
        MessageHandler(
            filters.Regex("^⚙️ وضعیت اشتراک$"),
            subscription_status
        )
    )

    # --------------------------------------------------------
    # Admin
    # --------------------------------------------------------

    application.add_handler(
        CommandHandler(
            "admin_payments",
            admin_payments
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            admin_payment_callback,
            pattern=r"^pay_(approve|reject):"
        )
    )

    # --------------------------------------------------------
    # Receipt Photo
    # --------------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            receipt_photo_handler
        )
    )

    # --------------------------------------------------------
    # Other Menu Items
    # --------------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.Regex(
                r"^(👥 مشتریان|📦 کالاها|🛒 ثبت فروش|📊 گزارش‌ها|👨‍💼 پشتیبانی)$"
            ),
            placeholder_handler
        )
    )


# ============================================================
# Application Builder
# ============================================================

def build_application(
    bot_token=None
):

    if not bot_token:
        bot_token = os.getenv(
            "BOT_TOKEN"
        )

    if not bot_token:
        raise RuntimeError(
            "BOT_TOKEN environment variable is not configured."
        )

    application = (
        Application.builder()
        .token(bot_token)
        .concurrent_updates(False)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start_command
        )
    )

    register_handlers(
        application
    )

    return application
