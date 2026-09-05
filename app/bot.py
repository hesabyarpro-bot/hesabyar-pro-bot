import os
import logging
from datetime import datetime
from telegram import (
    Update,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from app.db import (
    get_conn,
    init_db,
    create_customer,
    get_customer,
    list_customers,
    update_customer,
    deactivate_customer,
    activate_customer,
    create_product,
    get_product,
    list_products,
    update_product,
    deactivate_product,
    activate_product,
)
from app.sales import SalesService
# ============================================================
# Logging
# ============================================================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)
# ============================================================
# تنظیمات
# ============================================================
ADMIN_ID = int(
    os.getenv("ADMIN_ID", "8806709666")
)
# ============================================================
# Keyboard اصلی
# ============================================================
def main_keyboard():
    keyboard = [
        [
            "🛒 ثبت فروش",
            "🧾 ثبت خرید",
        ],
        [
            "👥 مشتریان",
            "📦 کالاها",
        ],
        [
            "📊 گزارش‌ها",
            "👨‍💼 پشتیبانی",
        ],
        [
            "⚙️ تنظیمات",
        ],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
    )
# ============================================================
# /start
# ============================================================
async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user = update.effective_user
    logger.info(
        "User started bot: %s",
        user.id if user else None,
    )
    await update.message.reply_text(
        "سلام 👋\n\n"
        "به «حساب‌یار پرو» خوش آمدید.\n\n"
        "حسابداری حرفه‌ای، ساده و همیشه در دسترس.",
        reply_markup=main_keyboard(),
    )
# ============================================================
# منوی اصلی
# ============================================================
async def menu_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    text = update.message.text
    if text == "🛒 ثبت فروش":
        await sales_start(update, context)
        return
    if text == "🧾 ثبت خرید":
        await update.message.reply_text(
            "🧾 بخش ثبت خرید در حال تکمیل است.\n\n"
            "این بخش در مرحله بعد به صورت کامل فعال می‌شود."
        )
        return
    if text == "👥 مشتریان":
        await customers_menu(update, context)
        return
    if text == "📦 کالاها":
        await products_menu(update, context)
        return
    if text == "📊 گزارش‌ها":
        await reports_menu(update, context)
        return
    if text == "👨‍💼 پشتیبانی":
        await update.message.reply_text(
            "👨‍💼 پشتیبانی حساب‌یار پرو\n\n"
            "برای ارتباط با پشتیبانی، پیام خود را ارسال کنید."
        )
        return
    if text == "⚙️ تنظیمات":
        await settings_menu(update, context)
        return
    # --------------------------------------------------------
    # حالت‌های داخلی مشتری
    # --------------------------------------------------------
    state = context.user_data.get("state")
    if state:
        handled = await handle_state(
            update,
            context,
            state,
        )
        if handled:
            return
    await update.message.reply_text(
        "لطفاً یکی از گزینه‌های منوی اصلی را انتخاب کنید.",
        reply_markup=main_keyboard(),
    )
# ============================================================
# State Handler
# ============================================================
async def handle_state(
    update,
    context,
    state,
):
    text = update.message.text
    # --------------------------------------------------------
    # افزودن مشتری
    # --------------------------------------------------------
    if state == "customer_add_name":
        context.user_data["customer_name"] = text
        context.user_data["state"] = "customer_add_phone"
        await update.message.reply_text(
            "📱 شماره تلفن مشتری را وارد کنید.\n"
            "اگر ندارد، «-» بفرستید."
        )
        return True
    if state == "customer_add_phone":
        phone = "" if text == "-" else text
        context.user_data["customer_phone"] = phone
        context.user_data["state"] = "customer_add_address"
        await update.message.reply_text(
            "📍 آدرس مشتری را وارد کنید.\n"
            "اگر ندارد، «-» بفرستید."
        )
        return True
    if state == "customer_add_address":
        address = "" if text == "-" else text
        context.user_data["customer_address"] = address
        context.user_data["state"] = "customer_add_notes"
        await update.message.reply_text(
            "📝 توضیحات مشتری را وارد کنید.\n"
            "اگر ندارد، «-» بفرستید."
        )
        return True
    if state == "customer_add_notes":
        notes = "" if text == "-" else text
        name = context.user_data.get(
            "customer_name",
            ""
        )
        phone = context.user_data.get(
            "customer_phone",
            ""
        )
        address = context.user_data.get(
            "customer_address",
            ""
        )
        customer_id = create_customer(
            name=name,
            phone=phone,
            address=address,
            notes=notes,
        )
        context.user_data.clear()
        await update.message.reply_text(
            f"✅ مشتری با موفقیت ثبت شد.\n\n"
            f"شناسه مشتری: {customer_id}\n"
            f"نام: {name}",
            reply_markup=main_keyboard(),
        )
        return True
    # --------------------------------------------------------
    # افزودن کالا
    # --------------------------------------------------------
    if state == "product_add_name":
        context.user_data["product_name"] = text
        context.user_data["state"] = "product_add_sku"
        await update.message.reply_text(
            "🔢 کد کالا / SKU را وارد کنید.\n"
            "اگر ندارد، «-» بفرستید."
        )
        return True
    if state == "product_add_sku":
        sku = None if text == "-" else text
        context.user_data["product_sku"] = sku
        context.user_data["state"] = "product_add_unit"
        await update.message.reply_text(
            "📏 واحد کالا را وارد کنید.\n"
            "مثلاً: عدد، کیلو، متر"
        )
        return True
    if state == "product_add_unit":
        context.user_data["product_unit"] = text
        context.user_data["state"] = "product_add_sale_price"
        await update.message.reply_text(
            "💰 قیمت فروش را به تومان وارد کنید."
        )
        return True
    if state == "product_add_sale_price":
        try:
            sale_price = int(
                normalize_number(text)
            )
        except ValueError:
            await update.message.reply_text(
                "❌ قیمت نامعتبر است.\n"
                "مثلاً 150000 وارد کنید."
            )
            return True
        context.user_data["product_sale_price"] = sale_price
        context.user_data["state"] = "product_add_purchase_cost"
        await update.message.reply_text(
            "💵 قیمت خرید / بهای تمام‌شده فعلی را وارد کنید."
        )
        return True
    if state == "product_add_purchase_cost":
        try:
            purchase_cost = int(
                normalize_number(text)
            )
        except ValueError:
            await update.message.reply_text(
                "❌ قیمت نامعتبر است."
            )
            return True
        name = context.user_data.get(
            "product_name",
            ""
        )
        sku = context.user_data.get(
            "product_sku"
        )
        unit = context.user_data.get(
            "product_unit",
            "عدد"
        )
        sale_price = context.user_data.get(
            "product_sale_price",
            0
        )
        try:
            product_id = create_product(
                name=name,
                sku=sku,
                unit=unit,
                sale_price=sale_price,
                purchase_cost=purchase_cost,
                stock=0,
            )
        except Exception as exc:
            logger.exception(
                "Product creation error"
            )
            context.user_data.clear()
            await update.message.reply_text(
                f"❌ ثبت کالا انجام نشد.\n\n"
                f"علت: {exc}",
                reply_markup=main_keyboard(),
            )
            return True
        context.user_data.clear()
        await update.message.reply_text(
            f"✅ کالا با موفقیت ثبت شد.\n\n"
            f"شناسه: {product_id}\n"
            f"نام: {name}\n"
            f"کد: {sku or '-'}\n"
            f"واحد: {unit}\n"
            f"قیمت فروش: {sale_price:,}\n"
            f"بهای خرید: {purchase_cost:,}",
            reply_markup=main_keyboard(),
        )
        return True
    # --------------------------------------------------------
    # فروش
    # --------------------------------------------------------
    if state == "sale_customer":
        try:
            customer_id = int(
                normalize_number(text)
            )
        except ValueError:
            await update.message.reply_text(
                "❌ شناسه مشتری نامعتبر است."
            )
            return True
        customer = get_customer(
            customer_id
        )
        if not customer or not customer["active"]:
            await update.message.reply_text(
                "❌ مشتری پیدا نشد."
            )
            return True
        context.user_data["sale_customer_id"] = customer_id
        context.user_data["state"] = "sale_product"
        await update.message.reply_text(
            "📦 شناسه کالا را وارد کنید."
        )
        return True
    if state == "sale_product":
        try:
            product_id = int(
                normalize_number(text)
            )
        except ValueError:
            await update.message.reply_text(
                "❌ شناسه کالا نامعتبر است."
            )
            return True
        product = get_product(
            product_id
        )
        if not product or not product["active"]:
            await update.message.reply_text(
                "❌ کالا پیدا نشد."
            )
            return True
        context.user_data["sale_product_id"] = product_id
        context.user_data["state"] = "sale_quantity"
        await update.message.reply_text(
            f"📦 کالا: {product['name']}\n"
            f"موجودی: {float(product['stock'] or 0):g}\n\n"
            f"تعداد فروش را وارد کنید."
        )
        return True
    if state == "sale_quantity":
        try:
            quantity = float(
                normalize_number(text)
            )
        except ValueError:
            await update.message.reply_text(
                "❌ تعداد نامعتبر است."
            )
            return True
        if quantity <= 0:
            await update.message.reply_text(
                "❌ تعداد باید بیشتر از صفر باشد."
            )
            return True
        context.user_data["sale_quantity"] = quantity
        context.user_data["state"] = "sale_price"
        product = get_product(
            context.user_data["sale_product_id"]
        )
        await update.message.reply_text(
            f"💰 قیمت فروش فعلی کالا: "
            f"{int(product['sale_price'] or 0):,}\n\n"
            f"قیمت فروش واحد را وارد کنید:"
        )
        return True
    if state == "sale_price":
        try:
            price = int(
                normalize_number(text)
            )
        except ValueError:
            await update.message.reply_text(
                "❌ قیمت نامعتبر است."
            )
            return True
        if price < 0:
            await update.message.reply_text(
                "❌ قیمت نمی‌تواند منفی باشد."
            )
            return True
        context.user_data["sale_price"] = price
        context.user_data["state"] = "sale_discount"
        await update.message.reply_text(
            "🏷️ مبلغ تخفیف را وارد کنید.\n"
            "اگر تخفیف ندارید، 0 بفرستید."
        )
        return True
    if state == "sale_discount":
        try:
            discount = int(
                normalize_number(text)
            )
        except ValueError:
            await update.message.reply_text(
                "❌ مبلغ تخفیف نامعتبر است."
            )
            return True
        if discount < 0:
            discount = 0
        context.user_data["sale_discount"] = discount
        context.user_data["state"] = "sale_payment"
        await update.message.reply_text(
            "💳 روش پرداخت را وارد کنید:\n\n"
            "1️⃣ نقدی\n"
            "2️⃣ بانکی\n"
            "3️⃣ نسیه"
        )
        return True
    if state == "sale_payment":
        payment_map = {
            "1": "cash",
            "نقد": "cash",
            "نقدی": "cash",
            "2": "bank",
            "بانک": "bank",
            "بانکی": "bank",
            "3": "credit",
            "نسیه": "credit",
        }
        payment = payment_map.get(
            text.strip().lower()
        )
        if not payment:
            await update.message.reply_text(
                "❌ روش پرداخت نامعتبر است.\n\n"
                "1️⃣ نقدی\n"
                "2️⃣ بانکی\n"
                "3️⃣ نسیه"
            )
            return True
        context.user_data["sale_payment"] = payment
        await show_sale_preview(
            update,
            context
        )
        return True
    if state == "sale_confirm":
        answer = text.strip().lower()
        if answer not in [
            "بله",
            "خیر",
            "yes",
            "no",
            "y",
            "n",
        ]:
            await update.message.reply_text(
                "لطفاً «بله» یا «خیر» وارد کنید."
            )
            return True
        if answer in ["خیر", "no", "n"]:
            context.user_data.clear()
            await update.message.reply_text(
                "❌ ثبت فروش لغو شد.",
                reply_markup=main_keyboard(),
            )
            return True
        try:
            service = SalesService()
            result = service.create_sale(
                customer_id=context.user_data.get(
                    "sale_customer_id"
                ),
                product_id=context.user_data.get(
                    "sale_product_id"
                ),
                quantity=context.user_data.get(
                    "sale_quantity"
                ),
                unit_price=context.user_data.get(
                    "sale_price"
                ),
                discount=context.user_data.get(
                    "sale_discount",
                    0
                ),
                tax=0,
                payment_method=context.user_data.get(
                    "sale_payment",
                    "cash"
                ),
            )
        except Exception as exc:
            logger.exception(
                "Sale registration error"
            )
            context.user_data.clear()
            await update.message.reply_text(
                f"❌ ثبت فروش انجام نشد.\n\n"
                f"علت: {exc}",
                reply_markup=main_keyboard(),
            )
            return True
        context.user_data.clear()
        await update.message.reply_text(
            "✅ فروش با موفقیت ثبت شد.\n\n"
            f"🧾 شماره فاکتور: {result['invoice_no']}\n"
            f"💰 مبلغ: {result['payable_amount']:,} تومان\n"
            f"🏷️ تخفیف: {result['discount_amount']:,} تومان\n"
            f"💳 روش پرداخت: "
            f"{payment_method_fa(result['payment_method'])}\n"
            f"📦 بهای تمام‌شده: "
            f"{result['cogs']:,} تومان",
            reply_markup=main_keyboard(),
        )
        return True
    return False
# ============================================================
# نرمال‌سازی اعداد
# ============================================================
def normalize_number(value):
    translation = str.maketrans(
        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
        "01234567890123456789"
    )
    return (
        str(value)
        .translate(translation)
        .replace(",", "")
        .replace("٬", "")
        .replace(" ", "")
        .strip()
    )
def payment_method_fa(value):
    mapping = {
        "cash": "نقدی",
        "bank": "بانکی",
        "credit": "نسیه",
    }
    return mapping.get(
        value,
        value
    )
# ============================================================
# مشتریان
# ============================================================
async def customers_menu(
    update,
    context
):
    customers = list_customers(
        active_only=True
    )
    if not customers:
        await update.message.reply_text(
            "👥 هنوز مشتری فعالی ثبت نشده است."
        )
    else:
        lines = [
            "👥 مشتریان فعال:",
            "",
        ]
        for customer in customers[:30]:
            lines.append(
                f"#{customer['id']} - "
                f"{customer['name']}"
            )
            if customer["phone"]:
                lines.append(
                    f"📱 {customer['phone']}"
                )
        await update.message.reply_text(
            "\n".join(lines)
        )
    await update.message.reply_text(
        "برای افزودن مشتری جدید، بنویسید:\n"
        "➕ مشتری جدید"
    )
# ============================================================
# شروع افزودن مشتری
# ============================================================
async def customer_new(
    update,
    context
):
    context.user_data.clear()
    context.user_data["state"] = "customer_add_name"
    await update.message.reply_text(
        "👤 نام مشتری را وارد کنید:"
    )
# ============================================================
# کالاها
# ============================================================
async def products_menu(
    update,
    context
):
    products = list_products(
        active_only=True
    )
    if not products:
        await update.message.reply_text(
            "📦 هنوز کالای فعالی ثبت نشده است."
        )
    else:
        lines = [
            "📦 کالاهای فعال:",
            "",
        ]
        for product in products[:30]:
            lines.append(
                f"#{product['id']} - "
                f"{product['name']}"
            )
            lines.append(
                f"💰 فروش: "
                f"{int(product['sale_price'] or 0):,}"
            )
            lines.append(
                f"📦 موجودی: "
                f"{float(product['stock'] or 0):g}"
            )
            lines.append("")
        await update.message.reply_text(
            "\n".join(lines)
        )
    await update.message.reply_text(
        "برای افزودن کالا جدید، بنویسید:\n"
        "➕ کالای جدید"
    )
# ============================================================
# شروع افزودن کالا
# ============================================================
async def product_new(
    update,
    context
):
    context.user_data.clear()
    context.user_data["state"] = "product_add_name"
    await update.message.reply_text(
        "📦 نام کالا را وارد کنید:"
    )
# ============================================================
# فروش
# ============================================================
async def sales_start(
    update,
    context
):
    context.user_data.clear()
    customers = list_customers(
        active_only=True
    )
    if not customers:
        await update.message.reply_text(
            "❌ ابتدا حداقل یک مشتری ثبت کنید."
        )
        return
    context.user_data["state"] = "sale_customer"
    lines = [
        "🛒 ثبت فروش",
        "",
        "شناسه مشتری را وارد کنید:",
        "",
    ]
    for customer in customers[:20]:
        lines.append(
            f"#{customer['id']} - "
            f"{customer['name']}"
        )
    await update.message.reply_text(
        "\n".join(lines)
    )
async def show_sale_preview(
    update,
    context
):
    customer = get_customer(
        context.user_data.get(
            "sale_customer_id"
        )
    )
    product = get_product(
        context.user_data.get(
            "sale_product_id"
        )
    )
    quantity = context.user_data.get(
        "sale_quantity",
        0
    )
    price = context.user_data.get(
        "sale_price",
        0
    )
    discount = context.user_data.get(
        "sale_discount",
        0
    )
    payment = context.user_data.get(
        "sale_payment",
        "cash"
    )
    gross = int(
        round(quantity * price)
    )
    net = max(
        gross - discount,
        0
    )
    await update.message.reply_text(
        "🧾 پیش‌نمایش فروش\n\n"
        f"👤 مشتری: "
        f"{customer['name'] if customer else '-'}\n"
        f"📦 کالا: "
        f"{product['name'] if product else '-'}\n"
        f"🔢 تعداد: {quantity:g}\n"
        f"💰 قیمت واحد: {price:,}\n"
        f"💵 مبلغ ناخالص: {gross:,}\n"
        f"🏷️ تخفیف: {discount:,}\n"
        f"💳 مبلغ نهایی: {net:,}\n"
        f"💳 روش پرداخت: "
        f"{payment_method_fa(payment)}\n\n"
        "آیا فروش ثبت شود؟\n"
        "بله / خیر"
    )
    context.user_data["state"] = "sale_confirm"
# ============================================================
# گزارش‌ها
# ============================================================
async def reports_menu(
    update,
    context
):
    conn = get_conn()
    try:
        sales_count = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM invoices
            WHERE invoice_type = 'SALE'
            """
        ).fetchone()["c"]
        sales_total = conn.execute(
            """
            SELECT COALESCE(
                SUM(payable_amount),
                0
            ) AS total
            FROM invoices
            WHERE invoice_type = 'SALE'
            """
        ).fetchone()["total"]
        customers_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM customers
            WHERE active = 1
            """
        ).fetchone()[0]
        products_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM products
            WHERE active = 1
            """
        ).fetchone()[0]
    finally:
        conn.close()
    await update.message.reply_text(
        "📊 گزارش سریع\n\n"
        f"🧾 تعداد فروش: {sales_count}\n"
        f"💰 مجموع فروش: {int(sales_total):,} تومان\n"
        f"👥 مشتری فعال: {customers_count}\n"
        f"📦 کالای فعال: {products_count}"
    )
# ============================================================
# تنظیمات
# ============================================================
async def settings_menu(
    update,
    context
):
    await update.message.reply_text(
        "⚙️ تنظیمات حساب‌یار پرو\n\n"
        "نسخه فعلی: MVP\n"
        "موتور حسابداری: فعال\n"
        "دیتابیس: SQLite\n"
        "ثبت فروش: فعال\n"
        "مدیریت مشتری: فعال\n"
        "مدیریت کالا: فعال"
    )
# ============================================================
# دستورات متنی اختصاصی
# ============================================================
async def text_command_handler(
    update,
    context
):
    text = update.message.text.strip()
    if text == "➕ مشتری جدید":
        await customer_new(
            update,
            context
        )
        return
    if text == "➕ کالای جدید":
        await product_new(
            update,
            context
        )
        return
    await menu_handler(
        update,
        context
    )
# ============================================================
# register_handlers
# ============================================================
def register_handlers(
    application: Application
):
    """
    ثبت تمام Handlerهای بات.
    این تابع توسط app.main فراخوانی می‌شود.
    """
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_command_handler,
        )
    )
# ============================================================
# ساخت Application
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
            "BOT_TOKEN environment variable "
            "is not configured."
        )
    init_db()
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
# ============================================================
# اجرای مستقیم bot.py
# ============================================================
def main():
    token = os.getenv(
        "BOT_TOKEN"
    )
    if not token:
        raise RuntimeError(
            "BOT_TOKEN environment variable "
            "is not configured."
        )
    application = build_application(
        token
    )
    logger.info(
        "HesabYar Pro Bot is starting..."
    )
    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )
if __name__ == "__main__":
    main()
