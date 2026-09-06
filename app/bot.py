import os

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

from . import db
from .sales import SalesService
from .purchases import PurchaseService
from .reports import (
    dashboard_text,
    stock_text,
    low_stock_text,
    invoices_text,
)


ADMIN_ID = int(
    os.getenv(
        "ADMIN_ID",
        "0",
    )
)


CARD_NUMBER = os.getenv(
    "CARD_NUMBER",
    "",
)


PLANS = {
    "monthly": (
        "اشتراک ماهانه",
        30,
        int(
            os.getenv(
                "PLAN_MONTHLY",
                "199000",
            )
        ),
    ),

    "quarterly": (
        "اشتراک سه‌ماهه",
        90,
        int(
            os.getenv(
                "PLAN_QUARTERLY",
                "499000",
            )
        ),
    ),
}


MENU = [
    [
        "🛒 ثبت فروش",
        "🧾 ثبت خرید",
    ],

    [
        "📦 کالاها",
        "👥 مشتریان",
    ],

    [
        "🏭 تأمین‌کنندگان",
        "📊 گزارش‌ها",
    ],

    [
        "💳 خرید اشتراک",
        "👨‍💼 پشتیبانی",
    ],
]


if ADMIN_ID:
    MENU.append(
        [
            "⚙️ پنل مدیریت"
        ]
    )


def main_keyboard():

    return ReplyKeyboardMarkup(
        MENU,
        resize_keyboard=True,
    )


def money(value):

    return (
        f"{int(value):,}"
        " تومان"
    )


def parse_amount(text):

    return int(
        text
        .replace(",", "")
        .replace("٬", "")
        .replace("تومان", "")
        .strip()
    )


def reset_user_data(
    context
):

    context.user_data.clear()


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    db.upsert_telegram_user(
        update.effective_user
    )

    subscription = db.active_subscription(
        update.effective_user.id
    )

    if subscription:

        subscription_text = (
            "\n\n"
            f"✅ اشتراک فعال: "
            f"{subscription['plan_name']}\n"
            f"تا تاریخ: "
            f"{subscription['end_date']}"
        )

    else:

        subscription_text = (
            "\n\n"
            "⚠️ اشتراک فعالی ندارید."
        )

    await update.message.reply_text(

        "سلام 👋\n\n"

        "به حساب‌یار پرو خوش آمدید.\n\n"

        "حسابداری حرفه‌ای، ساده و "
        "همیشه در دسترس."

        + subscription_text,

        reply_markup=main_keyboard(),
    )


# =========================================================
# GENERAL MENU
# =========================================================

async def main_menu(
    update,
    context,
):

    text = update.message.text

    if text == "🛒 ثبت فروش":
        return await sales_start(
            update,
            context,
        )

    if text == "🧾 ثبت خرید":
        return await purchase_start(
            update,
            context,
        )

    if text == "📦 کالاها":
        return await products_menu(
            update,
            context,
        )

    if text == "👥 مشتریان":
        return await customers_menu(
            update,
            context,
        )

    if text == "🏭 تأمین‌کنندگان":
        return await suppliers_menu(
            update,
            context,
        )

    if text == "📊 گزارش‌ها":
        return await reports_menu(
            update,
            context,
        )

    if text == "💳 خرید اشتراک":
        return await subscription_menu(
            update,
            context,
        )

    if text == "👨‍💼 پشتیبانی":

        await update.message.reply_text(
            "👨‍💼 پشتیبانی حساب‌یار پرو\n\n"
            "پیام خود را ارسال کنید."
        )

        return

    if (
        text == "⚙️ پنل مدیریت"
        and update.effective_user.id
        == ADMIN_ID
    ):

        return await admin_menu(
            update,
            context,
        )

    await update.message.reply_text(
        "از منوی زیر یک گزینه را انتخاب کنید.",
        reply_markup=main_keyboard(),
    )


# =========================================================
# PRODUCTS
# =========================================================

async def products_menu(
    update,
    context,
):

    products = db.list_products()

    if products:

        lines = [
            "📦 کالاها",
            "",
        ]

        for product in products:

            lines.append(
                f"• {product['code']} | "
                f"{product['name']}\n"
                f"  موجودی: "
                f"{product['stock']:g} "
                f"{product['unit']}\n"
                f"  قیمت فروش: "
                f"{money(product['sale_price'])}"
            )

        text = "\n".join(lines)

    else:

        text = (
            "📦 هنوز کالایی ثبت نشده است."
        )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "➕ کالای جدید",
                    callback_data="new_product",
                )
            ]
        ]
    )

    await update.message.reply_text(
        text,
        reply_markup=keyboard,
    )


# =========================================================
# CUSTOMERS
# =========================================================

async def customers_menu(
    update,
    context,
):

    customers = db.list_customers()

    if customers:

        lines = [
            "👥 مشتریان",
            "",
        ]

        for customer in customers:

            lines.append(
                f"• {customer['id']} | "
                f"{customer['name']} | "
                f"{customer['phone'] or '-'}"
            )

        text = "\n".join(lines)

    else:

        text = (
            "👥 هنوز مشتری ثبت نشده است."
        )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "➕ مشتری جدید",
                    callback_data="new_customer",
                )
            ]
        ]
    )

    await update.message.reply_text(
        text,
        reply_markup=keyboard,
    )


# =========================================================
# SUPPLIERS
# =========================================================

async def suppliers_menu(
    update,
    context,
):

    suppliers = db.list_suppliers()

    if suppliers:

        lines = [
            "🏭 تأمین‌کنندگان",
            "",
        ]

        for supplier in suppliers:

            lines.append(
                f"• {supplier['id']} | "
                f"{supplier['name']} | "
                f"{supplier['phone'] or '-'}"
            )

        text = "\n".join(lines)

    else:

        text = (
            "🏭 هنوز تأمین‌کننده ثبت نشده است."
        )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "➕ تأمین‌کننده جدید",
                    callback_data="new_supplier",
                )
            ]
        ]
    )

    await update.message.reply_text(
        text,
        reply_markup=keyboard,
    )


# =========================================================
# MASTER DATA CREATION
# =========================================================

async def master_callback(
    update,
    context,
):

    query = update.callback_query

    await query.answer()

    data = query.data

    if data == "new_customer":

        context.user_data[
            "master_type"
        ] = "customer"

        context.user_data[
            "master_step"
        ] = 1

        await query.message.reply_text(
            "نام مشتری را ارسال کنید:"
        )

        return "MASTER"


    if data == "new_supplier":

        context.user_data[
            "master_type"
        ] = "supplier"

        context.user_data[
            "master_step"
        ] = 1

        await query.message.reply_text(
            "نام تأمین‌کننده را ارسال کنید:"
        )

        return "MASTER"


    if data == "new_product":

        context.user_data[
            "master_type"
        ] = "product"

        context.user_data[
            "master_step"
        ] = 1

        await query.message.reply_text(
            "کد کالا را ارسال کنید:"
        )

        return "MASTER"


    return ConversationHandler.END


async def master_text(
    update,
    context,
):

    value = update.message.text.strip()

    master_type = context.user_data.get(
        "master_type"
    )

    step = context.user_data.get(
        "master_step",
        1,
    )


    # -----------------------------------------------------
    # CUSTOMER
    # -----------------------------------------------------

    if master_type == "customer":

        if step == 1:

            context.user_data[
                "master_name"
            ] = value

            context.user_data[
                "master_step"
            ] = 2

            await update.message.reply_text(
                "شماره تماس مشتری را ارسال کنید "
                "یا - بزنید:"
            )

            return "MASTER"


        if step == 2:

            name = context.user_data[
                "master_name"
            ]

            phone = (
                ""
                if value == "-"
                else value
            )

            db.add_customer(
                name=name,
                phone=phone,
            )

            reset_user_data(
                context
            )

            await update.message.reply_text(
                "✅ مشتری با موفقیت ثبت شد.",
                reply_markup=main_keyboard(),
            )

            return ConversationHandler.END


    # -----------------------------------------------------
    # SUPPLIER
    # -----------------------------------------------------

    if master_type == "supplier":

        if step == 1:

            context.user_data[
                "master_name"
            ] = value

            context.user_data[
                "master_step"
            ] = 2

            await update.message.reply_text(
                "شماره تماس تأمین‌کننده را "
                "ارسال کنید یا - بزنید:"
            )

            return "MASTER"


        if step == 2:

            name = context.user_data[
                "master_name"
            ]

            phone = (
                ""
                if value == "-"
                else value
            )

            db.add_supplier(
                name=name,
                phone=phone,
            )

            reset_user_data(
                context
            )

            await update.message.reply_text(
                "✅ تأمین‌کننده با موفقیت ثبت شد.",
                reply_markup=main_keyboard(),
            )

            return ConversationHandler.END


    # -----------------------------------------------------
    # PRODUCT
    # -----------------------------------------------------

    if master_type == "product":

        fields = [
            "code",
            "name",
            "unit",
            "sale_price",
            "purchase_cost",
            "min_stock",
        ]

        field = fields[
            step - 1
        ]

        context.user_data[
            field
        ] = value

        if step < len(fields):

            context.user_data[
                "master_step"
            ] = step + 1

            prompts = {
                1: "نام کالا را ارسال کنید:",

                2: (
                    "واحد کالا را ارسال کنید "
                    "(مثلاً عدد، کیلو، متر):"
                ),

                3: (
                    "قیمت فروش واحد را "
                    "به تومان ارسال کنید:"
                ),

                4: (
                    "قیمت خرید واحد را "
                    "به تومان ارسال کنید:"
                ),

                5: (
                    "حداقل موجودی را "
                    "ارسال کنید:"
                ),
            }

            await update.message.reply_text(
                prompts[step]
            )

            return "MASTER"


        try:

            db.add_product(
                code=context.user_data[
                    "code"
                ],

                name=context.user_data[
                    "name"
                ],

                unit=context.user_data[
                    "unit"
                ],

                sale_price=parse_amount(
                    context.user_data[
                        "sale_price"
                    ]
                ),

                purchase_cost=parse_amount(
                    context.user_data[
                        "purchase_cost"
                    ]
                ),

                min_stock=float(
                    context.user_data[
                        "min_stock"
                    ]
                ),
            )

        except Exception as error:

            await update.message.reply_text(
                f"❌ ثبت کالا انجام نشد:\n"
                f"{error}"
            )

            return ConversationHandler.END


        reset_user_data(
            context
        )

        await update.message.reply_text(
            "✅ کالا با موفقیت ثبت شد.",
            reply_markup=main_keyboard(),
        )

        return ConversationHandler.END


    return ConversationHandler.END


# =========================================================
# SALES
# =========================================================

async def sales_start(
    update,
    context,
):

    customers = db.list_customers()

    if not customers:

        await update.message.reply_text(
            "❌ ابتدا حداقل یک مشتری ثبت کنید."
        )

        return ConversationHandler.END


    reset_user_data(
        context
    )

    context.user_data[
        "flow"
    ] = "sale"

    context.user_data[
        "items"
    ] = []


    buttons = []

    for customer in customers:

        buttons.append(
            [
                InlineKeyboardButton(
                    customer["name"],
                    callback_data=(
                        f"sale_customer:"
                        f"{customer['id']}"
                    ),
                )
            ]
        )


    await update.message.reply_text(
        "👤 مشتری فاکتور را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(
            buttons
        ),
    )

    return "SALE_CUSTOMER"


async def sale_customer_callback(
    update,
    context,
):

    query = update.callback_query

    await query.answer()

    customer_id = int(
        query.data.split(":")[1]
    )

    context.user_data[
        "party_id"
    ] = customer_id

    return await show_sale_products(
        query.message,
        context,
    )


async def show_sale_products(
    message,
    context,
):

    products = db.list_products()

    if not products:

        await message.reply_text(
            "❌ ابتدا کالا ثبت کنید."
        )

        return ConversationHandler.END


    buttons = []

    for product in products:

        label = (
            f"{product['name']} | "
            f"موجودی "
            f"{product['stock']:g}"
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    label,
                    callback_data=(
                        f"sale_product:"
                        f"{product['id']}"
                    ),
                )
            ]
        )


    await message.reply_text(
        "📦 کالا را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(
            buttons
        ),
    )

    return "SALE_PRODUCT"


async def sale_product_callback(
    update,
    context,
):

    query = update.callback_query

    await query.answer()

    product_id = int(
        query.data.split(":")[1]
    )

    product = db.get_product(
        product_id
    )

    if not product:

        await query.message.reply_text(
            "❌ کالا پیدا نشد."
        )

        return ConversationHandler.END


    context.user_data[
        "current_product"
    ] = product_id

    await query.message.reply_text(
        f"📦 {product['name']}\n\n"
        f"تعداد را وارد کنید:"
    )

    return "SALE_QTY"


async def sale_qty(
    update,
    context,
):

    try:

        quantity = float(
            update.message.text
        )

        if quantity <= 0:
            raise ValueError

    except ValueError:

        await update.message.reply_text(
            "❌ تعداد نامعتبر است."
        )

        return "SALE_QTY"


    product = db.get_product(
        context.user_data[
            "current_product"
        ]
    )

    if quantity > product["stock"]:

        await update.message.reply_text(
            f"❌ موجودی کافی نیست.\n"
            f"موجودی فعلی: "
            f"{product['stock']:g}"
        )

        return "SALE_QTY"


    context.user_data[
        "current_qty"
    ] = quantity


    await update.message.reply_text(
        "💰 قیمت فروش واحد را وارد کنید:\n\n"
        f"قیمت فعلی: "
        f"{money(product['sale_price'])}"
    )

    return "SALE_PRICE"


async def sale_price(
    update,
    context,
):

    try:

        price = parse_amount(
            update.message.text
        )

        if price < 0:
            raise ValueError

    except ValueError:

        await update.message.reply_text(
            "❌ مبلغ نامعتبر است."
        )

        return "SALE_PRICE"


    product_id = context.user_data[
        "current_product"
    ]

    quantity = context.user_data[
        "current_qty"
    ]

    product = db.get_product(
        product_id
    )

    line_total = int(
        round(
            quantity * price
        )
    )


    context.user_data[
        "items"
    ].append(
        {
            "product_id": product_id,
            "qty": quantity,
            "unit_price": price,
            "discount": 0,
            "tax": 0,
            "line_total": line_total,
        }
    )


    context.user_data.pop(
        "current_product",
        None,
    )

    context.user_data.pop(
        "current_qty",
        None,
    )


    current_total = sum(
        item["line_total"]
        for item in context.user_data[
            "items"
        ]
    )


    await update.message.reply_text(

        f"✅ {product['name']} اضافه شد.\n\n"

        f"جمع فعلی: "
        f"{money(current_total)}",

        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "➕ افزودن کالا",
                        callback_data="sale_more",
                    ),

                    InlineKeyboardButton(
                        "➡️ ادامه",
                        callback_data="sale_continue",
                    ),
                ]
            ]
        ),
    )

    return "SALE_ITEMS"


async def sale_items_callback(
    update,
    context,
):

    query = update.callback_query

    await query.answer()

    if query.data == "sale_more":

        return await show_sale_products(
            query.message,
            context,
        )


    await query.message.reply_text(
        "روش پرداخت را انتخاب کنید:",
        reply_markup=payment_keyboard(
            "sale"
        ),
    )

    return "SALE_PAYMENT"


async def sale_payment_callback(
    update,
    context,
):

    query = update.callback_query

    await query.answer()

    payment_method = (
        query.data.split(":")[1]
    )

    context.user_data[
        "payment"
    ] = payment_method


    names = {
        "cash": "نقدی",
        "bank": "کارت / بانک",
        "credit": "نسیه / اعتباری",
    }


    lines = []

    for item in context.user_data[
        "items"
    ]:

        product = db.get_product(
            item["product_id"]
        )

        lines.append(
            f"• {product['name']} × "
            f"{item['qty']:g} = "
            f"{money(item['line_total'])}"
        )


    total = sum(
        item["line_total"]
        for item in context.user_data[
            "items"
        ]
    )


    text = (
        "🧾 پیش‌نمایش فاکتور فروش\n\n"
        + "\n".join(lines)
        + "\n\n"
        f"جمع کل: {money(total)}\n"
        f"روش پرداخت: "
        f"{names[payment_method]}\n\n"
        "آیا ثبت نهایی شود؟"
    )


    await query.message.reply_text(

        text,

        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ تأیید و ثبت",
                        callback_data="sale_confirm",
                    ),

                    InlineKeyboardButton(
                        "❌ لغو",
                        callback_data="cancel_flow",
                    ),
                ]
            ]
        ),
    )

    return "SALE_CONFIRM"


async def sale_confirm_callback(
    update,
    context,
):

    query = update.callback_query

    await query.answer()


    try:

        (
            invoice_id,
            invoice_no,
            total,
            cost,
        ) = SalesService.create_sale(
            customer_id=context.user_data[
                "party_id"
            ],

            items=context.user_data[
                "items"
            ],

            payment_method=context.user_data[
                "payment"
            ],
        )


        reset_user_data(
            context
        )


        await query.message.reply_text(

            "✅ فروش با موفقیت ثبت شد.\n\n"

            f"شماره فاکتور: "
            f"{invoice_no}\n"

            f"مبلغ فروش: "
            f"{money(total)}\n"

            f"بهای تمام‌شده: "
            f"{money(cost)}",

            reply_markup=main_keyboard(),
        )


    except Exception as error:

        await query.message.reply_text(
            f"❌ ثبت فروش انجام نشد:\n"
            f"{error}",
            reply_markup=main_keyboard(),
        )


    return ConversationHandler.END


# =========================================================
# PURCHASES
# =========================================================

async def purchase_start(
    update,
    context,
):

    suppliers = db.list_suppliers()

    if not suppliers:

        await update.message.reply_text(
            "❌ ابتدا تأمین‌کننده ثبت کنید."
        )

        return ConversationHandler.END


    reset_user_data(
        context
    )

    context.user_data[
        "flow"
    ] = "purchase"

    context.user_data[
        "items"
    ] = []


    buttons = []

    for supplier in suppliers:

        buttons.append(
            [
                InlineKeyboardButton(
                    supplier["name"],
                    callback_data=(
                        f"purchase_supplier:"
                        f"{supplier['id']}"
                    ),
                )
            ]
        )


    await update.message.reply_text(
        "🏭 تأمین‌کننده را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(
            buttons
        ),
    )

    return "PURCHASE_SUPPLIER"


async def purchase_supplier_callback(
    update,
    context,
):

    query = update.callback_query

    await query.answer()

    supplier_id = int(
        query.data.split(":")[1]
    )

    context.user_data[
        "party_id"
    ] = supplier_id

    return await show_purchase_products(
        query.message,
        context,
    )


async def show_purchase_products(
    message,
    context,
):

    products = db.list_products()

    if not products:

        await message.reply_text(
            "❌ ابتدا کالا ثبت کنید."
        )

        return ConversationHandler.END


    buttons = []

    for product in products:

        buttons.append(
            [
                InlineKeyboardButton(
                    product["name"],
                    callback_data=(
                        f"purchase_product:"
                        f"{product['id']}"
                    ),
                )
            ]
        )


    await message.reply_text(
        "📦 کالای خرید را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(
            buttons
        ),
    )

    return "PURCHASE_PRODUCT"


async def purchase_product_callback(
    update,
    context,
):

    query = update.callback_query

    await query.answer()

    product_id = int(
        query.data.split(":")[1]
    )

    product = db.get_product(
        product_id
    )

    if not product:

        await query.message.reply_text(
            "❌ کالا پیدا نشد."
        )

        return ConversationHandler.END


    context.user_data[
        "current_product"
    ] = product_id


    await query.message.reply_text(
        f"📦 {product['name']}\n\n"
        "تعداد را وارد کنید:"
    )

    return "PURCHASE_QTY"


async def purchase_qty(
    update,
    context,
):

    try:

        quantity = float(
            update.message.text
        )

        if quantity <= 0:
            raise ValueError

    except ValueError:

        await update.message.reply_text(
            "❌ تعداد نامعتبر است."
        )

        return "PURCHASE_QTY"


    context.user_data[
        "current_qty"
    ] = quantity


    product = db.get_product(
        context.user_data[
            "current_product"
        ]
    )


    await update.message.reply_text(
        "💰 قیمت خرید واحد را وارد کنید:\n\n"
        f"قیمت خرید فعلی: "
        f"{money(product['purchase_cost'])}"
    )

    return "PURCHASE_PRICE"


async def purchase_price(
    update,
    context,
):

    try:

        price = parse_amount(
            update.message.text
        )

        if price < 0:
            raise ValueError

    except ValueError:

        await update.message.reply_text(
            "❌ مبلغ نامعتبر است."
        )

        return "PURCHASE_PRICE"


    product_id = context.user_data[
        "current_product"
    ]

    quantity = context.user_data[
        "current_qty"
    ]


    context.user_data[
        "items"
    ].append(
        {
            "product_id": product_id,
            "qty": quantity,
            "unit_price": price,
            "discount": 0,
            "tax": 0,
            "line_total": int(
                round(
                    quantity * price
                )
            ),
        }
    )


    context.user_data.pop(
        "current_product",
        None,
    )

    context.user_data.pop(
        "current_qty",
        None,
    )


    await update.message.reply_text(

        "✅ قلم خرید اضافه شد.",

        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "➕ افزودن کالا",
                        callback_data="purchase_more",
                    ),

                    InlineKeyboardButton(
                        "➡️ ادامه",
                        callback_data="purchase_continue",
                    ),
                ]
            ]
        ),
    )

    return "PURCHASE_ITEMS"


async def purchase_items_callback(
    update,
    context,
):

    query = update.callback_query

    await query.answer()


    if query.data == "purchase_more":

        return await show_purchase_products(
            query.message,
            context,
        )


    await query.message.reply_text(
        "روش پرداخت را انتخاب کنید:",
        reply_markup=payment_keyboard(
            "purchase"
        ),
    )

    return "PURCHASE_PAYMENT"


async def purchase_payment_callback(
    update,
    context,
):

    query = update.callback_query

    await query.answer()

    method = (
        query.data.split(":")[1]
    )

    context.user_data[
        "payment"
    ] = method


    total = sum(
        item["line_total"]
        for item in context.user_data[
            "items"
        ]
    )


    await query.message.reply_text(

        "🧾 پیش‌نمایش خرید\n\n"

        f"تعداد اقلام: "
        f"{len(context.user_data['items'])}\n"

        f"جمع خرید: "
        f"{money(total)}\n\n"

        "آیا ثبت نهایی شود؟",

        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ ثبت خرید",
                        callback_data="purchase_confirm",
                    ),

                    InlineKeyboardButton(
                        "❌ لغو",
                        callback_data="cancel_flow",
                    ),
                ]
            ]
        ),
    )

    return "PURCHASE_CONFIRM"


async def purchase_confirm_callback(
    update,
    context,
):

    query = update.callback_query

    await query.answer()


    try:

        (
            invoice_id,
            invoice_no,
            total,
            cost,
        ) = PurchaseService.create_purchase(
            supplier_id=context.user_data[
                "party_id"
            ],

            items=context.user_data[
                "items"
            ],

            payment_method=context.user_data[
                "payment"
            ],
        )


        reset_user_data(
            context
        )


        await query.message.reply_text(

            "✅ خرید با موفقیت ثبت شد.\n\n"

            f"شماره فاکتور: "
            f"{invoice_no}\n"

            f"جمع خرید: "
            f"{money(total)}\n\n"

            "موجودی کالا و سند حسابداری "
            "نیز ثبت شد.",

            reply_markup=main_keyboard(),
        )


    except Exception as error:

        await query.message.reply_text(
            f"❌ ثبت خرید انجام نشد:\n"
            f"{error}",
            reply_markup=main_keyboard(),
        )


    return ConversationHandler.END


# =========================================================
# REPORTS
# =========================================================

async def reports_menu(
    update,
    context,
):

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📦 موجودی",
                    callback_data="report_stock",
                ),

                InlineKeyboardButton(
                    "⚠️ کم‌موجودی",
                    callback_data="report_low",
                ),
            ],

            [
                InlineKeyboardButton(
                    "🧾 فاکتورها",
                    callback_data="report_invoices",
                ),
            ],
        ]
    )


    await update.message.reply_text(
        dashboard_text(),
        reply_markup=keyboard,
    )


async def reports_callback(
    update,
    context,
):

    query = update.callback_query

    await query.answer()


    if query.data == "report_stock":

        text = stock_text()


    elif query.data == "report_low":

        text = low_stock_text()


    else:

        text = invoices_text()


    await query.message.reply_text(
        text
    )


# =========================================================
# SUBSCRIPTIONS
# =========================================================

def subscription_keyboard():

    buttons = []

    for code, (
        name,
        days,
        amount,
    ) in PLANS.items():

        buttons.append(
            [
                InlineKeyboardButton(
                    f"{name} — {money(amount)}",
                    callback_data=(
                        f"plan:{code}"
                    ),
                )
            ]
        )

    return InlineKeyboardMarkup(
        buttons
    )


async def subscription_menu(
    update,
    context,
):

    await update.message.reply_text(

        "💳 خرید اشتراک حساب‌یار پرو\n\n"
        "پلن موردنظر را انتخاب کنید:",

        reply_markup=subscription_keyboard(),
    )

    return "SUBSCRIPTION_PLAN"


async def subscription_plan_callback(
    update,
    context,
):

    query = update.callback_query

    await query.answer()

    code = query.data.split(":")[1]

    plan = PLANS.get(code)

    if not plan:

        await query.message.reply_text(
            "❌ پلن نامعتبر است."
        )

        return ConversationHandler.END


    name, days, amount = plan


    payment_id = db.create_payment(
        telegram_id=update.effective_user.id,
        plan_code=code,
        plan_name=name,
        amount=amount,
    )


    context.user_data[
        "subscription_payment_id"
    ] = payment_id


    card = (
        CARD_NUMBER
        if CARD_NUMBER
        else "در تنظیمات ربات ثبت نشده"
    )


    await query.message.reply_text(

        f"💳 {name}\n\n"

        f"مبلغ: {money(amount)}\n\n"

        f"شماره کارت:\n"
        f"{card}\n\n"

        "پس از پرداخت، تصویر رسید را "
        "همینجا ارسال کنید.",

    )

    return "SUBSCRIPTION_RECEIPT"


async def subscription_receipt(
    update,
    context,
):

    if not update.message.photo:

        await update.message.reply_text(
            "❌ لطفاً تصویر رسید پرداخت "
            "را ارسال کنید."
        )

        return "SUBSCRIPTION_RECEIPT"


    payment_id = context.user_data.get(
        "subscription_payment_id"
    )

    if not payment_id:

        await update.message.reply_text(
            "❌ تراکنش پیدا نشد."
        )

        return ConversationHandler.END


    photo = (
        update.message.photo[-1]
    )


    db.attach_receipt(
        payment_id=payment_id,
        file_id=photo.file_id,
        unique_id=photo.file_unique_id,
    )


    payment = db.get_payment(
        payment_id
    )


    reset_user_data(
        context
    )


    await update.message.reply_text(

        "✅ رسید پرداخت دریافت شد.\n\n"

        f"کد پیگیری: {payment_id}\n\n"

        "پس از بررسی مدیریت، "
        "اشتراک فعال خواهد شد.",

        reply_markup=main_keyboard(),
    )


    if ADMIN_ID:

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ تأیید پرداخت",
                        callback_data=(
                            f"payment_approve:"
                            f"{payment_id}"
                        ),
                    ),

                    InlineKeyboardButton(
                        "❌ رد پرداخت",
                        callback_data=(
                            f"payment_reject:"
                            f"{payment_id}"
                        ),
                    ),
                ]
            ]
        )


        await context.bot.send_message(

            chat_id=ADMIN_ID,

            text=(
                "🔔 رسید جدید اشتراک\n\n"

                f"Payment ID: "
                f"{payment_id}\n"

                f"کاربر: "
                f"{payment['telegram_id']}\n"

                f"پلن: "
                f"{payment['plan_name']}\n"

                f"مبلغ: "
                f"{money(payment['amount'])}"
            ),

            reply_markup=keyboard,
        )


        try:

            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=photo.file_id,
                caption=(
                    f"🧾 رسید پرداخت #{payment_id}"
                ),
            )

        except Exception:
            pass


    return ConversationHandler.END


# =========================================================
# ADMIN
# =========================================================

async def admin_menu(
    update,
    context,
):

    if update.effective_user.id != ADMIN_ID:

        await update.message.reply_text(
            "⛔ دسترسی غیرمجاز."
        )

        return


    payments = db.pending_payments()


    if not payments:

        text = (
            "⚙️ پنل مدیریت\n\n"
            "✅ پرداخت در انتظار بررسی وجود ندارد."
        )

        await update.message.reply_text(
            text
        )

        return


    lines = [
        "⚙️ پرداخت‌های در انتظار بررسی",
        "",
    ]


    buttons = []


    for payment in payments:

        lines.append(
            f"#{payment['id']} | "
            f"{payment['plan_name']} | "
            f"{money(payment['amount'])}\n"
            f"کاربر: "
            f"{payment['telegram_id']}"
        )


        buttons.append(
            [
                InlineKeyboardButton(
                    f"✅ تأیید #{payment['id']}",
                    callback_data=(
                        f"payment_approve:"
                        f"{payment['id']}"
                    ),
                ),

                InlineKeyboardButton(
                    f"❌ رد #{payment['id']}",
                    callback_data=(
                        f"payment_reject:"
                        f"{payment['id']}"
                    ),
                ),
            ]
        )


    await update.message.reply_text(

        "\n".join(lines),

        reply_markup=InlineKeyboardMarkup(
            buttons
        ),
    )


async def admin_payment_callback(
    update,
    context,
):

    query = update.callback_query

    await query.answer()


    if (
        update.effective_user.id
        != ADMIN_ID
    ):

        await query.message.reply_text(
            "⛔ دسترسی غیرمجاز."
        )

        return


    action, payment_id_text = (
        query.data.split(":")
    )

    payment_id = int(
        payment_id_text
    )


    payment = db.get_payment(
        payment_id
    )


    if not payment:

        await query.message.reply_text(
            "❌ پرداخت پیدا نشد."
        )

        return


    if action == "payment_approve":

        plan = PLANS.get(
            payment["plan_code"]
        )

        if not plan:

            await query.message.reply_text(
                "❌ پلن اشتراک پیدا نشد."
            )

            return


        name, days, amount = plan


        result = db.approve_payment(
            payment_id=payment_id,
            reviewer_id=ADMIN_ID,
            duration_days=days,
        )


        if not result:

            await query.message.reply_text(
                "⚠️ این پرداخت قبلاً بررسی شده است."
            )

            return


        await query.message.reply_text(

            "✅ پرداخت تأیید شد.\n\n"

            f"پلن: "
            f"{result['plan_name']}\n"

            f"شروع: "
            f"{result['start_date']}\n"

            f"پایان: "
            f"{result['end_date']}"
        )


        try:

            await context.bot.send_message(

                chat_id=payment[
                    "telegram_id"
                ],

                text=(

                    "🎉 پرداخت شما تأیید شد.\n\n"

                    f"اشتراک: "
                    f"{result['plan_name']}\n"

                    f"شروع: "
                    f"{result['start_date']}\n"

                    f"پایان: "
                    f"{result['end_date']}\n\n"

                    "اشتراک شما با موفقیت فعال شد."
                ),
            )

        except Exception:
            pass


    elif action == "payment_reject":

        result = db.reject_payment(
            payment_id=payment_id,
            reviewer_id=ADMIN_ID,
            reason="رد توسط مدیریت",
        )


        if not result:

            await query.message.reply_text(
                "⚠️ این پرداخت قبلاً بررسی شده است."
            )

            return


        await query.message.reply_text(
            "❌ پرداخت رد شد."
        )


        try:

            await context.bot.send_message(

                chat_id=payment[
                    "telegram_id"
                ],

                text=(
                    "❌ رسید پرداخت شما تأیید نشد.\n\n"
                    "لطفاً با پشتیبانی تماس بگیرید."
                ),
            )

        except Exception:
            pass


# =========================================================
# PAYMENT KEYBOARD
# =========================================================

def payment_keyboard(
    prefix,
):

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "💵 نقدی",
                    callback_data=(
                        f"{prefix}:cash"
                    ),
                ),

                InlineKeyboardButton(
                    "🏦 کارت / بانک",
                    callback_data=(
                        f"{prefix}:bank"
                    ),
                ),
            ],

            [
                InlineKeyboardButton(
                    "📒 نسیه / اعتباری",
                    callback_data=(
                        f"{prefix}:credit"
                    ),
                ),
            ],
        ]
    )


# =========================================================
# CANCEL
# =========================================================

async def cancel_flow(
    update,
    context,
):

    reset_user_data(
        context
    )

    query = update.callback_query

    if query:

        await query.answer()

        await query.message.reply_text(
            "❌ عملیات لغو شد.",
            reply_markup=main_keyboard(),
        )

    else:

        await update.message.reply_text(
            "❌ عملیات لغو شد.",
            reply_markup=main_keyboard(),
        )

    return ConversationHandler.END


# =========================================================
# UNKNOWN
# =========================================================

async def unknown(
    update,
    context,
):

    await update.message.reply_text(
        "❓ گزینه نامعتبر است.\n"
        "برای شروع دوباره /start را ارسال کنید.",
        reply_markup=main_keyboard(),
    )


# =========================================================
# APPLICATION
# =========================================================

def build_application(
    token,
):

    application = (
        Application
        .builder()
        .token(token)
        .concurrent_updates(False)
        .build()
    )


    # -----------------------------------------------------
    # START
    # -----------------------------------------------------

    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )


    # -----------------------------------------------------
    # MASTER DATA
    # -----------------------------------------------------

    master_conversation = (
        ConversationHandler(

            entry_points=[
                CallbackQueryHandler(
                    master_callback,
                    pattern=(
                        r"^(new_customer|"
                        r"new_supplier|"
                        r"new_product)$"
                    ),
                )
            ],

            states={
                "MASTER": [
                    MessageHandler(
                        filters.TEXT
                        & ~filters.COMMAND,
                        master_text,
                    )
                ]
            },

            fallbacks=[
                CommandHandler(
                    "cancel",
                    cancel_flow,
                )
            ],

            allow_reentry=True,
        )
    )


    application.add_handler(
        master_conversation
    )


    # -----------------------------------------------------
    # SALES
    # -----------------------------------------------------

    sales_conversation = (
        ConversationHandler(

            entry_points=[
                MessageHandler(
                    filters.Regex(
                        r"^🛒 ثبت فروش$"
                    ),
                    sales_start,
                )
            ],

            states={

                "SALE_CUSTOMER": [
                    CallbackQueryHandler(
                        sale_customer_callback,
                        pattern=r"^sale_customer:",
                    )
                ],

                "SALE_PRODUCT": [
                    CallbackQueryHandler(
                        sale_product_callback,
                        pattern=r"^sale_product:",
                    )
                ],

                "SALE_QTY": [
                    MessageHandler(
                        filters.TEXT
                        & ~filters.COMMAND,
                        sale_qty,
                    )
                ],

                "SALE_PRICE": [
                    MessageHandler(
                        filters.TEXT
                        & ~filters.COMMAND,
                        sale_price,
                    )
                ],

                "SALE_ITEMS": [
                    CallbackQueryHandler(
                        sale_items_callback,
                        pattern=(
                            r"^(sale_more|"
                            r"sale_continue)$"
                        ),
                    )
                ],

                "SALE_PAYMENT": [
                    CallbackQueryHandler(
                        sale_payment_callback,
                        pattern=r"^sale:",
                    )
                ],

                "SALE_CONFIRM": [
                    CallbackQueryHandler(
                        sale_confirm_callback,
                        pattern=r"^sale_confirm$",
                    ),

                    CallbackQueryHandler(
                        cancel_flow,
                        pattern=r"^cancel_flow$",
                    ),
                ],
            },

            fallbacks=[
                CallbackQueryHandler(
                    cancel_flow,
                    pattern=r"^cancel_flow$",
                )
            ],

            allow_reentry=True,
        )
    )


    application.add_handler(
        sales_conversation
    )


    # -----------------------------------------------------
    # PURCHASES
    # -----------------------------------------------------

    purchase_conversation = (
        ConversationHandler(

            entry_points=[
                MessageHandler(
                    filters.Regex(
                        r"^🧾 ثبت خرید$"
                    ),
                    purchase_start,
                )
            ],

            states={

                "PURCHASE_SUPPLIER": [
                    CallbackQueryHandler(
                        purchase_supplier_callback,
                        pattern=(
                            r"^purchase_supplier:"
                        ),
                    )
                ],

                "PURCHASE_PRODUCT": [
                    CallbackQueryHandler(
                        purchase_product_callback,
                        pattern=(
                            r"^purchase_product:"
                        ),
                    )
                ],

                "PURCHASE_QTY": [
                    MessageHandler(
                        filters.TEXT
                        & ~filters.COMMAND,
                        purchase_qty,
                    )
                ],

                "PURCHASE_PRICE": [
                    MessageHandler(
                        filters.TEXT
                        & ~filters.COMMAND,
                        purchase_price,
                    )
                ],

                "PURCHASE_ITEMS": [
                    CallbackQueryHandler(
                        purchase_items_callback,
                        pattern=(
                            r"^(purchase_more|"
                            r"purchase_continue)$"
                        ),
                    )
                ],

                "PURCHASE_PAYMENT": [
                    CallbackQueryHandler(
                        purchase_payment_callback,
                        pattern=r"^purchase:",
                    )
                ],

                "PURCHASE_CONFIRM": [
                    CallbackQueryHandler(
                        purchase_confirm_callback,
                        pattern=(
                            r"^purchase_confirm$"
                        ),
                    ),

                    CallbackQueryHandler(
                        cancel_flow,
                        pattern=r"^cancel_flow$",
                    ),
                ],
            },

            fallbacks=[
                CallbackQueryHandler(
                    cancel_flow,
                    pattern=r"^cancel_flow$",
                )
            ],

            allow_reentry=True,
        )
    )


    application.add_handler(
        purchase_conversation
    )


    # -----------------------------------------------------
    # SUBSCRIPTION
    # -----------------------------------------------------

    subscription_conversation = (
        ConversationHandler(

            entry_points=[
                MessageHandler(
                    filters.Regex(
                        r"^💳 خرید اشتراک$"
                    ),
                    subscription_menu,
                ),

                CallbackQueryHandler(
                    subscription_plan_callback,
                    pattern=r"^plan:",
                ),
            ],

            states={

                "SUBSCRIPTION_PLAN": [
                    CallbackQueryHandler(
                        subscription_plan_callback,
                        pattern=r"^plan:",
                    )
                ],

                "SUBSCRIPTION_RECEIPT": [
                    MessageHandler(
                        filters.PHOTO,
                        subscription_receipt,
                    )
                ],
            },

            fallbacks=[
                CallbackQueryHandler(
                    cancel_flow,
                    pattern=r"^cancel_flow$",
                )
            ],

            allow_reentry=True,
        )
    )


    application.add_handler(
        subscription_conversation
    )


    # -----------------------------------------------------
    # REPORTS
    # -----------------------------------------------------

    application.add_handler(
        CallbackQueryHandler(
            reports_callback,
            pattern=(
                r"^report_(stock|low|invoices)$"
            ),
        )
    )


    # -----------------------------------------------------
    # ADMIN PAYMENTS
    # -----------------------------------------------------

    application.add_handler(
        CallbackQueryHandler(
            admin_payment_callback,
            pattern=(
                r"^payment_"
                r"(approve|reject):"
            ),
        )
    )


    # -----------------------------------------------------
    # GENERAL MENU
    # -----------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            main_menu,
        )
    )


    # -----------------------------------------------------
    # UNKNOWN
    # -----------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.ALL,
            unknown,
        )
    )


    return application
