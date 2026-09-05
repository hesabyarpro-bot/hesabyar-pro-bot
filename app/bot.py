import os
import logging
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
    init_db,
    get_conn,
    create_customer,
    get_customer,
    list_customers,
    deactivate_customer,
    create_product,
    get_product,
    list_products,
    create_supplier,
    get_supplier,
    list_suppliers,
    deactivate_supplier,
)
from app.sales import SalesService
from app.purchases import PurchaseService
# ============================================================
# Logging
# ============================================================
logging.basicConfig(
    format=(
        "%(asctime)s - "
        "%(name)s - "
        "%(levelname)s - "
        "%(message)s"
    ),
    level=logging.INFO,
)
logger = logging.getLogger(
    __name__
)
# ============================================================
# تنظیمات
# ============================================================
ADMIN_ID = int(
    os.getenv(
        "ADMIN_ID",
        "8806709666"
    )
)
# ============================================================
# Keyboard
# ============================================================
def main_keyboard():
    keyboard = [
        [
            "🛒 ثبت فروش",
            "🧾 ثبت خرید",
        ],
        [
            "👥 مشتریان",
            "👨‍💼 تأمین‌کنندگان",
        ],
        [
            "📦 کالاها",
            "📊 گزارش‌ها",
        ],
        [
            "👨‍💼 پشتیبانی",
            "⚙️ تنظیمات",
        ],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True
    )
# ============================================================
# /start
# ============================================================
async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    context.user_data.clear()
    await update.message.reply_text(
        "سلام 👋\n\n"
        "به «حساب‌یار پرو» خوش آمدید.\n\n"
        "حسابداری حرفه‌ای، ساده و همیشه در دسترس.\n\n"
        "از منوی زیر انتخاب کنید:",
        reply_markup=main_keyboard()
    )
# ============================================================
# Normalize
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
        .replace("٫", ".")
        .strip()
    )
def to_int(value):
    text = normalize_number(
        value
    )
    if not text:
        return 0
    return int(
        float(text)
    )
def payment_fa(value):
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
# MENU HANDLER
# ============================================================
async def menu_handler(
    update,
    context
):
    text = update.message.text.strip()
    # --------------------------------------------------------
    # فروش
    # --------------------------------------------------------
    if text == "🛒 ثبت فروش":
        await sales_start(
            update,
            context
        )
        return
    # --------------------------------------------------------
    # خرید
    # --------------------------------------------------------
    if text == "🧾 ثبت خرید":
        await purchase_start(
            update,
            context
        )
        return
    # --------------------------------------------------------
    # مشتریان
    # --------------------------------------------------------
    if text == "👥 مشتریان":
        await customers_menu(
            update,
            context
        )
        return
    # --------------------------------------------------------
    # تأمین‌کنندگان
    # --------------------------------------------------------
    if text == "👨‍💼 تأمین‌کنندگان":
        await suppliers_menu(
            update,
            context
        )
        return
    # --------------------------------------------------------
    # کالاها
    # --------------------------------------------------------
    if text == "📦 کالاها":
        await products_menu(
            update,
            context
        )
        return
    # --------------------------------------------------------
    # گزارش
    # --------------------------------------------------------
    if text == "📊 گزارش‌ها":
        await reports_menu(
            update,
            context
        )
        return
    # --------------------------------------------------------
    # پشتیبانی
    # --------------------------------------------------------
    if text == "👨‍💼 پشتیبانی":
        await update.message.reply_text(
            "👨‍💼 پشتیبانی حساب‌یار پرو\n\n"
            "پیام خود را ارسال کنید."
        )
        return
    # --------------------------------------------------------
    # تنظیمات
    # --------------------------------------------------------
    if text == "⚙️ تنظیمات":
        await settings_menu(
            update,
            context
        )
        return
    # --------------------------------------------------------
    # مشتری جدید
    # --------------------------------------------------------
    if text == "➕ مشتری جدید":
        context.user_data.clear()
        context.user_data[
            "state"
        ] = "customer_name"
        await update.message.reply_text(
            "👤 نام مشتری را وارد کنید:"
        )
        return
    # --------------------------------------------------------
    # تأمین‌کننده جدید
    # --------------------------------------------------------
    if text == "➕ تأمین‌کننده جدید":
        context.user_data.clear()
        context.user_data[
            "state"
        ] = "supplier_name"
        await update.message.reply_text(
            "👨‍💼 نام تأمین‌کننده را وارد کنید:"
        )
        return
    # --------------------------------------------------------
    # کالای جدید
    # --------------------------------------------------------
    if text == "➕ کالای جدید":
        context.user_data.clear()
        context.user_data[
            "state"
        ] = "product_name"
        await update.message.reply_text(
            "📦 نام کالا را وارد کنید:"
        )
        return
    # --------------------------------------------------------
    # state
    # --------------------------------------------------------
    state = context.user_data.get(
        "state"
    )
    if state:
        handled = await handle_state(
            update,
            context,
            state
        )
        if handled:
            return
    await update.message.reply_text(
        "لطفاً یکی از گزینه‌های منو را انتخاب کنید.",
        reply_markup=main_keyboard()
    )
# ============================================================
# STATE HANDLER
# ============================================================
async def handle_state(
    update,
    context,
    state
):
    text = update.message.text.strip()
    # ========================================================
    # CUSTOMER
    # ========================================================
    if state == "customer_name":
        context.user_data[
            "customer_name"
        ] = text
        context.user_data[
            "state"
        ] = "customer_phone"
        await update.message.reply_text(
            "📱 شماره تلفن را وارد کنید.\n"
            "اگر ندارد، - بفرستید."
        )
        return True
    if state == "customer_phone":
        context.user_data[
            "customer_phone"
        ] = (
            ""
            if text == "-"
            else text
        )
        context.user_data[
            "state"
        ] = "customer_address"
        await update.message.reply_text(
            "📍 آدرس مشتری را وارد کنید.\n"
            "اگر ندارد، - بفرستید."
        )
        return True
    if state == "customer_address":
        context.user_data[
            "customer_address"
        ] = (
            ""
            if text == "-"
            else text
        )
        context.user_data[
            "state"
        ] = "customer_notes"
        await update.message.reply_text(
            "📝 توضیحات را وارد کنید.\n"
            "اگر ندارد، - بفرستید."
        )
        return True
    if state == "customer_notes":
        notes = (
            ""
            if text == "-"
            else text
        )
        customer_id = create_customer(
            name=context.user_data[
                "customer_name"
            ],
            phone=context.user_data[
                "customer_phone"
            ],
            address=context.user_data[
                "customer_address"
            ],
            notes=notes
        )
        name = context.user_data[
            "customer_name"
        ]
        context.user_data.clear()
        await update.message.reply_text(
            "✅ مشتری ثبت شد.\n\n"
            f"شناسه: {customer_id}\n"
            f"نام: {name}",
            reply_markup=main_keyboard()
        )
        return True
    # ========================================================
    # SUPPLIER
    # ========================================================
    if state == "supplier_name":
        context.user_data[
            "supplier_name"
        ] = text
        context.user_data[
            "state"
        ] = "supplier_phone"
        await update.message.reply_text(
            "📱 شماره تلفن تأمین‌کننده را وارد کنید.\n"
            "اگر ندارد، - بفرستید."
        )
        return True
    if state == "supplier_phone":
        context.user_data[
            "supplier_phone"
        ] = (
            ""
            if text == "-"
            else text
        )
        context.user_data[
            "state"
        ] = "supplier_address"
        await update.message.reply_text(
            "📍 آدرس تأمین‌کننده را وارد کنید.\n"
            "اگر ندارد، - بفرستید."
        )
        return True
    if state == "supplier_address":
        context.user_data[
            "supplier_address"
        ] = (
            ""
            if text == "-"
            else text
        )
        context.user_data[
            "state"
        ] = "supplier_notes"
        await update.message.reply_text(
            "📝 توضیحات را وارد کنید.\n"
            "اگر ندارد، - بفرستید."
        )
        return True
    if state == "supplier_notes":
        notes = (
            ""
            if text == "-"
            else text
        )
        supplier_id = create_supplier(
            name=context.user_data[
                "supplier_name"
            ],
            phone=context.user_data[
                "supplier_phone"
            ],
            address=context.user_data[
                "supplier_address"
            ],
            notes=notes
        )
        name = context.user_data[
            "supplier_name"
        ]
        context.user_data.clear()
        await update.message.reply_text(
            "✅ تأمین‌کننده ثبت شد.\n\n"
            f"شناسه: {supplier_id}\n"
            f"نام: {name}",
            reply_markup=main_keyboard()
        )
        return True
    # ========================================================
    # PRODUCT
    # ========================================================
    if state == "product_name":
        context.user_data[
            "product_name"
        ] = text
        context.user_data[
            "state"
        ] = "product_sku"
        await update.message.reply_text(
            "🔢 کد کالا / SKU را وارد کنید.\n"
            "اگر ندارد، - بفرستید."
        )
        return True
    if state == "product_sku":
        context.user_data[
            "product_sku"
        ] = (
            None
            if text == "-"
            else text
        )
        context.user_data[
            "state"
        ] = "product_unit"
        await update.message.reply_text(
            "📏 واحد کالا را وارد کنید.\n"
            "مثلاً: عدد، کیلو، متر"
        )
        return True
    if state == "product_unit":
        context.user_data[
            "product_unit"
        ] = text
        context.user_data[
            "state"
        ] = "product_sale_price"
        await update.message.reply_text(
            "💰 قیمت فروش را وارد کنید:"
        )
        return True
    if state == "product_sale_price":
        try:
            price = to_int(text)
        except ValueError:
            await update.message.reply_text(
                "❌ قیمت نامعتبر است."
            )
            return True
        context.user_data[
            "product_sale_price"
        ] = price
        context.user_data[
            "state"
        ] = "product_purchase_cost"
        await update.message.reply_text(
            "💵 بهای خرید فعلی را وارد کنید:"
        )
        return True
    if state == "product_purchase_cost":
        try:
            purchase_cost = to_int(
                text
            )
        except ValueError:
            await update.message.reply_text(
                "❌ مبلغ نامعتبر است."
            )
            return True
        try:
            product_id = create_product(
                name=context.user_data[
                    "product_name"
                ],
                sku=context.user_data[
                    "product_sku"
                ],
                unit=context.user_data[
                    "product_unit"
                ],
                sale_price=context.user_data[
                    "product_sale_price"
                ],
                purchase_cost=purchase_cost,
                stock=0
            )
        except Exception as exc:
            logger.exception(
                "Product creation error"
            )
            context.user_data.clear()
            await update.message.reply_text(
                f"❌ ثبت کالا انجام نشد.\n\n"
                f"{exc}",
                reply_markup=main_keyboard()
            )
            return True
        name = context.user_data[
            "product_name"
        ]
        context.user_data.clear()
        await update.message.reply_text(
            "✅ کالا ثبت شد.\n\n"
            f"شناسه: {product_id}\n"
            f"نام: {name}",
            reply_markup=main_keyboard()
        )
        return True
    # ========================================================
    # SALE
    # ========================================================
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
        context.user_data[
            "sale_customer_id"
        ] = customer_id
        context.user_data[
            "state"
        ] = "sale_product"
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
        context.user_data[
            "sale_product_id"
        ] = product_id
        context.user_data[
            "state"
        ] = "sale_quantity"
        await update.message.reply_text(
            f"📦 کالا: {product['name']}\n"
            f"موجودی: "
            f"{float(product['stock'] or 0):g}\n\n"
            "تعداد فروش را وارد کنید:"
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
        context.user_data[
            "sale_quantity"
        ] = quantity
        context.user_data[
            "state"
        ] = "sale_price"
        await update.message.reply_text(
            "💰 قیمت فروش واحد را وارد کنید:"
        )
        return True
    if state == "sale_price":
        try:
            price = to_int(text)
        except ValueError:
            await update.message.reply_text(
                "❌ قیمت نامعتبر است."
            )
            return True
        context.user_data[
            "sale_price"
        ] = price
        context.user_data[
            "state"
        ] = "sale_discount"
        await update.message.reply_text(
            "🏷️ تخفیف را وارد کنید.\n"
            "بدون تخفیف: 0"
        )
        return True
    if state == "sale_discount":
        try:
            discount = to_int(text)
        except ValueError:
            await update.message.reply_text(
                "❌ تخفیف نامعتبر است."
            )
            return True
        context.user_data[
            "sale_discount"
        ] = discount
        context.user_data[
            "state"
        ] = "sale_payment"
        await update.message.reply_text(
            "💳 روش پرداخت:\n\n"
            "1️⃣ نقدی\n"
            "2️⃣ بانکی\n"
            "3️⃣ نسیه"
        )
        return True
    if state == "sale_payment":
        payment = {
            "1": "cash",
            "2": "bank",
            "3": "credit",
            "نقدی": "cash",
            "نقد": "cash",
            "بانکی": "bank",
            "بانک": "bank",
            "نسیه": "credit"
        }.get(
            text.lower()
        )
        if not payment:
            await update.message.reply_text(
                "❌ روش پرداخت نامعتبر است."
            )
            return True
        context.user_data[
            "sale_payment"
        ] = payment
        await sale_preview(
            update,
            context
        )
        return True
    if state == "sale_confirm":
        if text not in [
            "بله",
            "خیر",
            "yes",
            "no"
        ]:
            await update.message.reply_text(
                "لطفاً بله یا خیر وارد کنید."
            )
            return True
        if text in [
            "خیر",
            "no"
        ]:
            context.user_data.clear()
            await update.message.reply_text(
                "❌ فروش لغو شد.",
                reply_markup=main_keyboard()
            )
            return True
        try:
            service = SalesService()
            result = service.create_sale(
                customer_id=context.user_data[
                    "sale_customer_id"
                ],
                product_id=context.user_data[
                    "sale_product_id"
                ],
                quantity=context.user_data[
                    "sale_quantity"
                ],
                unit_price=context.user_data[
                    "sale_price"
                ],
                discount=context.user_data[
                    "sale_discount"
                ],
                tax=0,
                payment_method=context.user_data[
                    "sale_payment"
                ]
            )
        except Exception as exc:
            logger.exception(
                "Sale error"
            )
            context.user_data.clear()
            await update.message.reply_text(
                f"❌ ثبت فروش ناموفق بود.\n\n"
                f"{exc}",
                reply_markup=main_keyboard()
            )
            return True
        context.user_data.clear()
        await update.message.reply_text(
            "✅ فروش ثبت شد.\n\n"
            f"🧾 فاکتور: {result['invoice_no']}\n"
            f"💰 مبلغ: "
            f"{result['payable_amount']:,} تومان\n"
            f"📦 بهای تمام‌شده: "
            f"{result['cogs']:,} تومان",
            reply_markup=main_keyboard()
        )
        return True
    # ========================================================
    # PURCHASE
    # ========================================================
    if state == "purchase_supplier":
        try:
            supplier_id = int(
                normalize_number(text)
            )
        except ValueError:
            await update.message.reply_text(
                "❌ شناسه تأمین‌کننده نامعتبر است."
            )
            return True
        supplier = get_supplier(
            supplier_id
        )
        if not supplier or not supplier["active"]:
            await update.message.reply_text(
                "❌ تأمین‌کننده پیدا نشد."
            )
            return True
        context.user_data[
            "purchase_supplier_id"
        ] = supplier_id
        context.user_data[
            "state"
        ] = "purchase_product"
        await update.message.reply_text(
            "📦 شناسه کالا را وارد کنید:"
        )
        return True
    if state == "purchase_product":
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
        context.user_data[
            "purchase_product_id"
        ] = product_id
        context.user_data[
            "state"
        ] = "purchase_quantity"
        await update.message.reply_text(
            "🔢 تعداد خرید را وارد کنید:"
        )
        return True
    if state == "purchase_quantity":
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
        context.user_data[
            "purchase_quantity"
        ] = quantity
        context.user_data[
            "state"
        ] = "purchase_price"
        await update.message.reply_text(
            "💰 قیمت خرید واحد را وارد کنید:"
        )
        return True
    if state == "purchase_price":
        try:
            price = to_int(text)
        except ValueError:
            await update.message.reply_text(
                "❌ قیمت نامعتبر است."
            )
            return True
        context.user_data[
            "purchase_price"
        ] = price
        context.user_data[
            "state"
        ] = "purchase_discount"
        await update.message.reply_text(
            "🏷️ مبلغ تخفیف را وارد کنید.\n"
            "بدون تخفیف: 0"
        )
        return True
    if state == "purchase_discount":
        try:
            discount = to_int(text)
        except ValueError:
            await update.message.reply_text(
                "❌ مبلغ تخفیف نامعتبر است."
            )
            return True
        context.user_data[
            "purchase_discount"
        ] = discount
        context.user_data[
            "state"
        ] = "purchase_tax"
        await update.message.reply_text(
            "🧮 مالیات خرید را وارد کنید.\n"
            "اگر ندارید: 0"
        )
        return True
    if state == "purchase_tax":
        try:
            tax = to_int(text)
        except ValueError:
            await update.message.reply_text(
                "❌ مالیات نامعتبر است."
            )
            return True
        context.user_data[
            "purchase_tax"
        ] = tax
        context.user_data[
            "state"
        ] = "purchase_payment"
        await update.message.reply_text(
            "💳 روش پرداخت:\n\n"
            "1️⃣ نقدی\n"
            "2️⃣ بانکی\n"
            "3️⃣ نسیه"
        )
        return True
    if state == "purchase_payment":
        payment = {
            "1": "cash",
            "2": "bank",
            "3": "credit",
            "نقدی": "cash",
            "نقد": "cash",
            "بانکی": "bank",
            "بانک": "bank",
            "نسیه": "credit"
        }.get(
            text.lower()
        )
        if not payment:
            await update.message.reply_text(
                "❌ روش پرداخت نامعتبر است."
            )
            return True
        context.user_data[
            "purchase_payment"
        ] = payment
        await purchase_preview(
            update,
            context
        )
        return True
    if state == "purchase_confirm":
        if text not in [
            "بله",
            "خیر",
            "yes",
            "no"
        ]:
            await update.message.reply_text(
                "لطفاً بله یا خیر وارد کنید."
            )
            return True
        if text in [
            "خیر",
            "no"
        ]:
            context.user_data.clear()
            await update.message.reply_text(
                "❌ ثبت خرید لغو شد.",
                reply_markup=main_keyboard()
            )
            return True
        try:
            service = PurchaseService()
            result = service.create_purchase(
                supplier_id=context.user_data[
                    "purchase_supplier_id"
                ],
                product_id=context.user_data[
                    "purchase_product_id"
                ],
                quantity=context.user_data[
                    "purchase_quantity"
                ],
                unit_price=context.user_data[
                    "purchase_price"
                ],
                discount=context.user_data[
                    "purchase_discount"
                ],
                tax=context.user_data[
                    "purchase_tax"
                ],
                payment_method=context.user_data[
                    "purchase_payment"
                ]
            )
        except Exception as exc:
            logger.exception(
                "Purchase error"
            )
            context.user_data.clear()
            await update.message.reply_text(
                f"❌ ثبت خرید ناموفق بود.\n\n"
                f"{exc}",
                reply_markup=main_keyboard()
            )
            return True
        context.user_data.clear()
        await update.message.reply_text(
            "✅ خرید با موفقیت ثبت شد.\n\n"
            f"🧾 فاکتور: "
            f"{result['invoice_no']}\n"
            f"💰 مبلغ نهایی: "
            f"{result['payable_amount']:,} تومان\n"
            f"📦 موجودی جدید: "
            f"{result['new_stock']:g}\n"
            f"📊 میانگین بهای خرید: "
            f"{result['weighted_cost']:,} تومان",
            reply_markup=main_keyboard()
        )
        return True
    return False
# ============================================================
# CUSTOMERS
# ============================================================
async def customers_menu(
    update,
    context
):
    customers = list_customers(
        True
    )
    lines = [
        "👥 مشتریان فعال",
        ""
    ]
    for item in customers[:30]:
        lines.append(
            f"#{item['id']} - "
            f"{item['name']}"
        )
    if not customers:
        lines.append(
            "هنوز مشتری ثبت نشده است."
        )
    lines.append("")
    lines.append(
        "برای افزودن مشتری:"
    )
    lines.append(
        "➕ مشتری جدید"
    )
    await update.message.reply_text(
        "\n".join(lines)
    )
# ============================================================
# SUPPLIERS
# ============================================================
async def suppliers_menu(
    update,
    context
):
    suppliers = list_suppliers(
        True
    )
    lines = [
        "👨‍💼 تأمین‌کنندگان فعال",
        ""
    ]
    for item in suppliers[:30]:
        lines.append(
            f"#{item['id']} - "
            f"{item['name']}"
        )
    if not suppliers:
        lines.append(
            "هنوز تأمین‌کننده ثبت نشده است."
        )
    lines.append("")
    lines.append(
        "برای افزودن:"
    )
    lines.append(
        "➕ تأمین‌کننده جدید"
    )
    await update.message.reply_text(
        "\n".join(lines)
    )
# ============================================================
# PRODUCTS
# ============================================================
async def products_menu(
    update,
    context
):
    products = list_products(
        True
    )
    lines = [
        "📦 کالاهای فعال",
        ""
    ]
    for item in products[:30]:
        lines.append(
            f"#{item['id']} - "
            f"{item['name']}"
        )
        lines.append(
            f"موجودی: "
            f"{float(item['stock'] or 0):g}"
        )
        lines.append("")
    if not products:
        lines.append(
            "هنوز کالایی ثبت نشده است."
        )
    lines.append(
        "➕ کالای جدید"
    )
    await update.message.reply_text(
        "\n".join(lines)
    )
# ============================================================
# SALES START
# ============================================================
async def sales_start(
    update,
    context
):
    context.user_data.clear()
    customers = list_customers(
        True
    )
    if not customers:
        await update.message.reply_text(
            "❌ ابتدا حداقل یک مشتری ثبت کنید."
        )
        return
    context.user_data[
        "state"
    ] = "sale_customer"
    lines = [
        "🛒 ثبت فروش",
        "",
        "شناسه مشتری را وارد کنید:",
        ""
    ]
    for item in customers[:20]:
        lines.append(
            f"#{item['id']} - "
            f"{item['name']}"
        )
    await update.message.reply_text(
        "\n".join(lines)
    )
# ============================================================
# SALE PREVIEW
# ============================================================
async def sale_preview(
    update,
    context
):
    customer = get_customer(
        context.user_data[
            "sale_customer_id"
        ]
    )
    product = get_product(
        context.user_data[
            "sale_product_id"
        ]
    )
    quantity = context.user_data[
        "sale_quantity"
    ]
    price = context.user_data[
        "sale_price"
    ]
    discount = context.user_data[
        "sale_discount"
    ]
    payment = context.user_data[
        "sale_payment"
    ]
    gross = int(
        round(
            quantity * price
        )
    )
    net = max(
        gross - discount,
        0
    )
    await update.message.reply_text(
        "🧾 پیش‌نمایش فروش\n\n"
        f"👤 مشتری: "
        f"{customer['name']}\n"
        f"📦 کالا: "
        f"{product['name']}\n"
        f"🔢 تعداد: "
        f"{quantity:g}\n"
        f"💰 قیمت واحد: "
        f"{price:,}\n"
        f"💵 مبلغ ناخالص: "
        f"{gross:,}\n"
        f"🏷️ تخفیف: "
        f"{discount:,}\n"
        f"💳 مبلغ نهایی: "
        f"{net:,}\n"
        f"💳 پرداخت: "
        f"{payment_fa(payment)}\n\n"
        "ثبت شود؟\n"
        "بله / خیر"
    )
    context.user_data[
        "state"
    ] = "sale_confirm"
# ============================================================
# PURCHASE START
# ============================================================
async def purchase_start(
    update,
    context
):
    context.user_data.clear()
    suppliers = list_suppliers(
        True
    )
    if not suppliers:
        await update.message.reply_text(
            "❌ ابتدا یک تأمین‌کننده ثبت کنید."
        )
        return
    context.user_data[
        "state"
    ] = "purchase_supplier"
    lines = [
        "🧾 ثبت خرید",
        "",
        "شناسه تأمین‌کننده را وارد کنید:",
        ""
    ]
    for item in suppliers[:20]:
        lines.append(
            f"#{item['id']} - "
            f"{item['name']}"
        )
    await update.message.reply_text(
        "\n".join(lines)
    )
# ============================================================
# PURCHASE PREVIEW
# ============================================================
async def purchase_preview(
    update,
    context
):
    supplier = get_supplier(
        context.user_data[
            "purchase_supplier_id"
        ]
    )
    product = get_product(
        context.user_data[
            "purchase_product_id"
        ]
    )
    quantity = context.user_data[
        "purchase_quantity"
    ]
    price = context.user_data[
        "purchase_price"
    ]
    discount = context.user_data[
        "purchase_discount"
    ]
    tax = context.user_data[
        "purchase_tax"
    ]
    payment = context.user_data[
        "purchase_payment"
    ]
    gross = int(
        round(
            quantity * price
        )
    )
    net = max(
        gross - discount,
        0
    )
    total = net + tax
    await update.message.reply_text(
        "🧾 پیش‌نمایش خرید\n\n"
        f"👨‍💼 تأمین‌کننده: "
        f"{supplier['name']}\n"
        f"📦 کالا: "
        f"{product['name']}\n"
        f"🔢 تعداد: "
        f"{quantity:g}\n"
        f"💰 قیمت واحد: "
        f"{price:,}\n"
        f"💵 مبلغ ناخالص: "
        f"{gross:,}\n"
        f"🏷️ تخفیف: "
        f"{discount:,}\n"
        f"🧮 مالیات: "
        f"{tax:,}\n"
        f"💳 مبلغ نهایی: "
        f"{total:,}\n"
        f"💳 پرداخت: "
        f"{payment_fa(payment)}\n\n"
        "ثبت خرید انجام شود؟\n"
        "بله / خیر"
    )
    context.user_data[
        "state"
    ] = "purchase_confirm"
# ============================================================
# REPORTS
# ============================================================
async def reports_menu(
    update,
    context
):
    conn = get_conn()
    try:
        sales = conn.execute(
            """
            SELECT
                COUNT(*) AS count,
                COALESCE(
                    SUM(payable_amount),
                    0
                ) AS total
            FROM invoices
            WHERE invoice_type = 'SALE'
            """
        ).fetchone()
        purchases = conn.execute(
            """
            SELECT
                COUNT(*) AS count,
                COALESCE(
                    SUM(payable_amount),
                    0
                ) AS total
            FROM invoices
            WHERE invoice_type = 'PURCHASE'
            """
        ).fetchone()
        stock_value = conn.execute(
            """
            SELECT
                COALESCE(
                    SUM(
                        stock *
                        purchase_cost
                    ),
                    0
                ) AS total
            FROM products
            WHERE active = 1
            """
        ).fetchone()["total"]
        customers = conn.execute(
            """
            SELECT COUNT(*)
            FROM customers
            WHERE active = 1
            """
        ).fetchone()[0]
        suppliers = conn.execute(
            """
            SELECT COUNT(*)
            FROM suppliers
            WHERE active = 1
            """
        ).fetchone()[0]
        products = conn.execute(
            """
            SELECT COUNT(*)
            FROM products
            WHERE active = 1
            """
        ).fetchone()[0]
    finally:
        conn.close()
    await update.message.reply_text(
        "📊 گزارش سریع حساب‌یار پرو\n\n"
        f"🛒 فروش:\n"
        f"تعداد: {sales['count']}\n"
        f"مبلغ: {int(sales['total']):,} تومان\n\n"
        f"🧾 خرید:\n"
        f"تعداد: {purchases['count']}\n"
        f"مبلغ: {int(purchases['total']):,} تومان\n\n"
        f"📦 ارزش تقریبی موجودی:\n"
        f"{int(stock_value):,} تومان\n\n"
        f"👥 مشتری فعال: {customers}\n"
        f"👨‍💼 تأمین‌کننده فعال: {suppliers}\n"
        f"📦 کالای فعال: {products}"
    )
# ============================================================
# SETTINGS
# ============================================================
async def settings_menu(
    update,
    context
):
    await update.message.reply_text(
        "⚙️ تنظیمات حساب‌یار پرو\n\n"
        "نسخه: MVP\n"
        "دیتابیس: SQLite\n"
        "ثبت فروش: فعال\n"
        "ثبت خرید: فعال\n"
        "مدیریت مشتری: فعال\n"
        "مدیریت تأمین‌کننده: فعال\n"
        "مدیریت کالا: فعال\n"
        "موتور حسابداری: فعال"
    )
# ============================================================
# TEXT HANDLER
# ============================================================
async def text_handler(
    update,
    context
):
    await menu_handler(
        update,
        context
    )
# ============================================================
# REGISTER HANDLERS
# ============================================================
def register_handlers(
    application: Application
):
    application.add_handler(
        MessageHandler(
            filters.TEXT &
            ~filters.COMMAND,
            text_handler
        )
    )
# ============================================================
# BUILD APPLICATION
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
# MAIN
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
