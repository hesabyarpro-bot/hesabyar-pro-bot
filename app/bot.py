from __future__ import annotations
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from .db import get_conn
from .sales import SalesService
from .master_data import (
    create_customer,
    create_product,
    deactivate_customer,
    deactivate_product,
    digits,
    get_customer,
    get_product,
    list_customers,
    list_products,
    to_int,
    update_customer,
    update_product,
)
# =========================================================
# Conversation states
# =========================================================
(
    CHOOSE_CUSTOMER,
    CHOOSE_PRODUCT,
    ENTER_QTY,
    ENTER_PRICE,
    ENTER_DISCOUNT,
    CHOOSE_PAYMENT,
    CONFIRM,
) = range(7)
(
    C_NAME,
    C_PHONE,
    C_BALANCE,
) = range(20, 23)
(
    P_SKU,
    P_NAME,
    P_SALE,
    P_COST,
    P_STOCK,
) = range(30, 35)
# =========================================================
# Helpers
# =========================================================
def money(value) -> str:
    return f"{int(value):,} ریال"
def main_menu():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🛒 ثبت فروش",
                    callback_data="sale:start",
                )
            ],
            [
                InlineKeyboardButton(
                    "🧾 ثبت خرید",
                    callback_data="coming:purchase",
                )
            ],
            [
                InlineKeyboardButton(
                    "👥 مشتریان",
                    callback_data="customers:list",
                ),
                InlineKeyboardButton(
                    "📦 کالاها",
                    callback_data="products:list",
                ),
            ],
            [
                InlineKeyboardButton(
                    "📊 گزارش‌ها",
                    callback_data="coming:reports",
                )
            ],
            [
                InlineKeyboardButton(
                    "⚙️ تنظیمات",
                    callback_data="coming:settings",
                )
            ],
        ]
    )
def back_home_markup():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🏠 منوی اصلی",
                    callback_data="home",
                )
            ]
        ]
    )
# =========================================================
# Start / Home
# =========================================================
async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "سلام 👋\n\n"
        "به حساب‌یار پرو خوش آمدید.\n\n"
        "🤖 دستیار مالی و حسابداری هوشمند شما آماده است.\n\n"
        "از منوی زیر انتخاب کنید:",
        reply_markup=main_menu(),
    )
async def home(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🏠 منوی اصلی حساب‌یار پرو",
        reply_markup=main_menu(),
    )
async def coming(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🚧 این بخش در حال تکمیل است.\n\n"
        "به‌زودی فعال می‌شود.",
        reply_markup=back_home_markup(),
    )
# =========================================================
# Customers
# =========================================================
async def customers_list(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()
    with get_conn(
        context.application.bot_data["db_path"]
    ) as conn:
        rows = list_customers(conn)
    buttons = []
    for row in rows[:30]:
        buttons.append(
            [
                InlineKeyboardButton(
                    f"👤 {row['name']}",
                    callback_data=f"customer:view:{row['id']}",
                )
            ]
        )
    buttons.append(
        [
            InlineKeyboardButton(
                "➕ مشتری جدید",
                callback_data="customer:add",
            )
        ]
    )
    buttons.append(
        [
            InlineKeyboardButton(
                "🏠 منوی اصلی",
                callback_data="home",
            )
        ]
    )
    if not rows:
        text = (
            "👥 مدیریت مشتریان\n\n"
            "هنوز مشتری فعالی ثبت نشده است."
        )
    else:
        text = (
            "👥 مدیریت مشتریان\n\n"
            f"تعداد مشتریان فعال: {len(rows)}\n\n"
            "یک مشتری را انتخاب کنید:"
        )
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons),
    )
async def customer_view(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()
    customer_id = int(
        query.data.split(":")[-1]
    )
    with get_conn(
        context.application.bot_data["db_path"]
    ) as conn:
        row = get_customer(
            conn,
            customer_id,
        )
    if not row:
        await query.edit_message_text(
            "❌ مشتری پیدا نشد.",
            reply_markup=back_home_markup(),
        )
        return
    text = (
        f"👤 {row['name']}\n\n"
        f"☎️ تلفن: {row['phone'] or '-'}\n"
        f"💰 مانده افتتاحیه: "
        f"{money(row['opening_balance'])}\n"
        f"📌 وضعیت: "
        f"{'فعال' if row['active'] else 'غیرفعال'}"
    )
    buttons = [
        [
            InlineKeyboardButton(
                "✏️ ویرایش",
                callback_data=f"customer:edit:{customer_id}",
            ),
            InlineKeyboardButton(
                "🗑 غیرفعال",
                callback_data=f"customer:deactivate:{customer_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                "↩️ بازگشت",
                callback_data="customers:list",
            )
        ],
    ]
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons),
    )
async def customer_add_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()
    context.user_data["new_customer"] = {}
    await query.edit_message_text(
        "👤 ثبت مشتری جدید\n\n"
        "نام مشتری را وارد کنید:"
    )
    return C_NAME
async def customer_add_name(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text(
            "❌ نام نمی‌تواند خالی باشد.\n"
            "لطفاً نام مشتری را وارد کنید:"
        )
        return C_NAME
    context.user_data["new_customer"][
        "name"
    ] = name
    await update.message.reply_text(
        "☎️ شماره تماس را وارد کنید.\n"
        "اگر ندارد، فقط - بزنید:"
    )
    return C_PHONE
async def customer_add_phone(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    phone = update.message.text.strip()
    context.user_data["new_customer"][
        "phone"
    ] = "" if phone == "-" else phone
    await update.message.reply_text(
        "💰 مانده افتتاحیه را به ریال وارد کنید.\n"
        "اگر ندارد، 0 وارد کنید:"
    )
    return C_BALANCE
async def customer_add_balance(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        balance = to_int(
            update.message.text,
            0,
        )
        data = context.user_data.pop(
            "new_customer"
        )
        with get_conn(
            context.application.bot_data["db_path"]
        ) as conn:
            row = create_customer(
                conn,
                data["name"],
                data["phone"],
                balance,
            )
        await update.message.reply_text(
            "✅ مشتری با موفقیت ثبت شد.\n\n"
            f"👤 {row['name']}\n"
            f"☎️ {row['phone'] or '-'}\n"
            f"💰 مانده افتتاحیه: "
            f"{money(row['opening_balance'])}",
            reply_markup=main_menu(),
        )
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text(
            "❌ مبلغ نامعتبر است.\n"
            "فقط عدد وارد کنید؛ مثال:\n"
            "5000000"
        )
        return C_BALANCE
    except Exception as exc:
        await update.message.reply_text(
            f"❌ ثبت مشتری انجام نشد:\n{exc}"
        )
        return C_BALANCE
async def customer_edit_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()
    customer_id = int(
        query.data.split(":")[-1]
    )
    with get_conn(
        context.application.bot_data["db_path"]
    ) as conn:
        row = get_customer(
            conn,
            customer_id,
        )
    if not row:
        await query.edit_message_text(
            "❌ مشتری پیدا نشد.",
            reply_markup=back_home_markup(),
        )
        return ConversationHandler.END
    context.user_data[
        "edit_customer"
    ] = {
        "id": customer_id,
        "name": row["name"],
        "phone": row["phone"] or "",
        "balance": row["opening_balance"],
    }
    await query.edit_message_text(
        "✏️ ویرایش مشتری\n\n"
        f"نام فعلی: {row['name']}\n\n"
        "نام جدید را وارد کنید:"
    )
    return C_NAME
async def customer_edit_name(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text(
            "❌ نام نمی‌تواند خالی باشد."
        )
        return C_NAME
    data = context.user_data[
        "edit_customer"
    ]
    data["name"] = name
    await update.message.reply_text(
        "☎️ شماره جدید را وارد کنید.\n"
        f"فعلی: {data['phone'] or '-'}"
    )
    return C_PHONE
async def customer_edit_phone(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    data = context.user_data[
        "edit_customer"
    ]
    phone = update.message.text.strip()
    data["phone"] = (
        ""
        if phone == "-"
        else phone
    )
    await update.message.reply_text(
        "💰 مانده افتتاحیه جدید را وارد کنید.\n"
        f"فعلی: {money(data['balance'])}"
    )
    return C_BALANCE
async def customer_edit_balance(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        balance = to_int(
            update.message.text,
            0,
        )
        data = context.user_data.pop(
            "edit_customer"
        )
        with get_conn(
            context.application.bot_data["db_path"]
        ) as conn:
            row = update_customer(
                conn,
                data["id"],
                data["name"],
                data["phone"],
                balance,
            )
        await update.message.reply_text(
            "✅ مشتری با موفقیت ویرایش شد.\n\n"
            f"👤 {row['name']}\n"
            f"☎️ {row['phone'] or '-'}\n"
            f"💰 مانده افتتاحیه: "
            f"{money(row['opening_balance'])}",
            reply_markup=main_menu(),
        )
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text(
            "❌ مبلغ نامعتبر است."
        )
        return C_BALANCE
    except Exception as exc:
        await update.message.reply_text(
            f"❌ ویرایش انجام نشد:\n{exc}"
        )
        return C_BALANCE
async def customer_deactivate(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()
    customer_id = int(
        query.data.split(":")[-1]
    )
    with get_conn(
        context.application.bot_data["db_path"]
    ) as conn:
        deactivate_customer(
            conn,
            customer_id,
        )
    await query.edit_message_text(
        "✅ مشتری غیرفعال شد.",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "👥 مشتریان",
                        callback_data="customers:list",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🏠 منوی اصلی",
                        callback_data="home",
                    )
                ],
            ]
        ),
    )
# =========================================================
# Products
# =========================================================
async def products_list(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()
    with get_conn(
        context.application.bot_data["db_path"]
    ) as conn:
        rows = list_products(conn)
    buttons = []
    for row in rows[:30]:
        buttons.append(
            [
                InlineKeyboardButton(
                    f"📦 {row['name']} | "
                    f"موجودی {row['stock_qty']:g}",
                    callback_data=f"product:view:{row['id']}",
                )
            ]
        )
    buttons.append(
        [
            InlineKeyboardButton(
                "➕ کالای جدید",
                callback_data="product:add",
            )
        ]
    )
    buttons.append(
        [
            InlineKeyboardButton(
                "🏠 منوی اصلی",
                callback_data="home",
            )
        ]
    )
    if not rows:
        text = (
            "📦 مدیریت کالاها\n\n"
            "هنوز کالای فعالی ثبت نشده است."
        )
    else:
        text = (
            "📦 مدیریت کالاها\n\n"
            f"تعداد کالاهای فعال: {len(rows)}\n\n"
            "یک کالا را انتخاب کنید:"
        )
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons),
    )
async def product_view(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()
    product_id = int(
        query.data.split(":")[-1]
    )
    with get_conn(
        context.application.bot_data["db_path"]
    ) as conn:
        row = get_product(
            conn,
            product_id,
        )
    if not row:
        await query.edit_message_text(
            "❌ کالا پیدا نشد.",
            reply_markup=back_home_markup(),
        )
        return
    text = (
        f"📦 {row['name']}\n\n"
        f"🏷 کد کالا: {row['sku'] or '-'}\n"
        f"💰 قیمت فروش: {money(row['sale_price'])}\n"
        f"🛒 بهای خرید: {money(row['purchase_cost'])}\n"
        f"📊 موجودی: {row['stock_qty']:g}\n"
        f"📌 وضعیت: "
        f"{'فعال' if row['active'] else 'غیرفعال'}"
    )
    buttons = [
        [
            InlineKeyboardButton(
                "✏️ ویرایش",
                callback_data=f"product:edit:{product_id}",
            ),
            InlineKeyboardButton(
                "🗑 غیرفعال",
                callback_data=f"product:deactivate:{product_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                "↩️ بازگشت",
                callback_data="products:list",
            )
        ],
    ]
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons),
    )
async def product_add_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()
    context.user_data["new_product"] = {}
    await query.edit_message_text(
        "📦 ثبت کالای جدید\n\n"
        "🏷 کد کالا را وارد کنید.\n"
        "اگر کد ندارد، - بزنید:"
    )
    return P_SKU
async def product_add_sku(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    sku = update.message.text.strip()
    context.user_data[
        "new_product"
    ]["sku"] = (
        ""
        if sku == "-"
        else sku
    )
    await update.message.reply_text(
        "📦 نام کالا را وارد کنید:"
    )
    return P_NAME
async def product_add_name(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text(
            "❌ نام کالا الزامی است."
        )
        return P_NAME
    context.user_data[
        "new_product"
    ]["name"] = name
    await update.message.reply_text(
        "💰 قیمت فروش را به ریال وارد کنید:"
    )
    return P_SALE
async def product_add_sale(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        sale = to_int(
            update.message.text,
            0,
        )
        context.user_data[
            "new_product"
        ]["sale"] = sale
        await update.message.reply_text(
            "🛒 بهای خرید را به ریال وارد کنید:"
        )
        return P_COST
    except ValueError:
        await update.message.reply_text(
            "❌ قیمت نامعتبر است.\n"
            "مثال: 25000000"
        )
        return P_SALE
async def product_add_cost(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        cost = to_int(
            update.message.text,
            0,
        )
        context.user_data[
            "new_product"
        ]["cost"] = cost
        await update.message.reply_text(
            "📊 موجودی اولیه را وارد کنید.\n"
            "مثال: 10 یا 2.5"
        )
        return P_STOCK
    except ValueError:
        await update.message.reply_text(
            "❌ بهای خرید نامعتبر است."
        )
        return P_COST
async def product_add_stock(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        stock_text = digits(
            update.message.text
        )
        stock_text = (
            stock_text
            .replace(",", "")
            .replace("٬", "")
            .strip()
        )
        stock = float(stock_text)
        if stock < 0:
            raise ValueError
        data = context.user_data.pop(
            "new_product"
        )
        with get_conn(
            context.application.bot_data["db_path"]
        ) as conn:
            row = create_product(
                conn,
                data["sku"],
                data["name"],
                data["sale"],
                data["cost"],
                stock,
            )
        await update.message.reply_text(
            "✅ کالا با موفقیت ثبت شد.\n\n"
            f"📦 {row['name']}\n"
            f"🏷 کد: {row['sku'] or '-'}\n"
            f"💰 فروش: {money(row['sale_price'])}\n"
            f"🛒 خرید: {money(row['purchase_cost'])}\n"
            f"📊 موجودی: {row['stock_qty']:g}",
            reply_markup=main_menu(),
        )
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text(
            "❌ موجودی نامعتبر است.\n"
            "مثال: 10 یا 2.5"
        )
        return P_STOCK
    except Exception as exc:
        await update.message.reply_text(
            f"❌ ثبت کالا انجام نشد:\n{exc}"
        )
        return P_STOCK
async def product_edit_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()
    product_id = int(
        query.data.split(":")[-1]
    )
    with get_conn(
        context.application.bot_data["db_path"]
    ) as conn:
        row = get_product(
            conn,
            product_id,
        )
    if not row:
        await query.edit_message_text(
            "❌ کالا پیدا نشد.",
            reply_markup=back_home_markup(),
        )
        return ConversationHandler.END
    context.user_data[
        "edit_product"
    ] = {
        "id": product_id,
        "sku": row["sku"] or "",
        "name": row["name"],
        "sale": row["sale_price"],
        "cost": row["purchase_cost"],
    }
    await query.edit_message_text(
        "✏️ ویرایش کالا\n\n"
        f"کد فعلی: {row['sku'] or '-'}\n\n"
        "کد جدید را وارد کنید:"
    )
    return P_SKU
async def product_edit_sku(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    data = context.user_data[
        "edit_product"
    ]
    sku = update.message.text.strip()
    data["sku"] = (
        ""
        if sku == "-"
        else sku
    )
    await update.message.reply_text(
        "📦 نام جدید را وارد کنید.\n"
        f"فعلی: {data['name']}"
    )
    return P_NAME
async def product_edit_name(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text(
            "❌ نام کالا الزامی است."
        )
        return P_NAME
    data = context.user_data[
        "edit_product"
    ]
    data["name"] = name
    await update.message.reply_text(
        "💰 قیمت فروش جدید را وارد کنید.\n"
        f"فعلی: {money(data['sale'])}"
    )
    return P_SALE
async def product_edit_sale(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        sale = to_int(
            update.message.text,
            0,
        )
        data = context.user_data[
            "edit_product"
        ]
        data["sale"] = sale
        await update.message.reply_text(
            "🛒 بهای خرید جدید را وارد کنید.\n"
            f"فعلی: {money(data['cost'])}"
        )
        return P_COST
    except ValueError:
        await update.message.reply_text(
            "❌ قیمت نامعتبر است."
        )
        return P_SALE
async def product_edit_cost(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        cost = to_int(
            update.message.text,
            0,
        )
        data = context.user_data.pop(
            "edit_product"
        )
        data["cost"] = cost
        with get_conn(
            context.application.bot_data["db_path"]
        ) as conn:
            row = update_product(
                conn,
                data["id"],
                data["sku"],
                data["name"],
                data["sale"],
                data["cost"],
            )
        await update.message.reply_text(
            "✅ کالا با موفقیت ویرایش شد.\n\n"
            f"📦 {row['name']}\n"
            f"🏷 کد: {row['sku'] or '-'}\n"
            f"💰 فروش: {money(row['sale_price'])}\n"
            f"🛒 خرید: {money(row['purchase_cost'])}\n"
            f"📊 موجودی: {row['stock_qty']:g}",
            reply_markup=main_menu(),
        )
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text(
            "❌ بهای خرید نامعتبر است."
        )
        return P_COST
    except Exception as exc:
        await update.message.reply_text(
            f"❌ ویرایش کالا انجام نشد:\n{exc}"
        )
        return P_COST
async def product_deactivate(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()
    product_id = int(
        query.data.split(":")[-1]
    )
    with get_conn(
        context.application.bot_data["db_path"]
    ) as conn:
        deactivate_product(
            conn,
            product_id,
        )
    await query.edit_message_text(
        "✅ کالا غیرفعال شد.",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "📦 کالاها",
                        callback_data="products:list",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🏠 منوی اصلی",
                        callback_data="home",
                    )
                ],
            ]
        ),
    )
# =========================================================
# Sales
# =========================================================
async def sale_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()
    context.user_data["sale"] = {}
    with get_conn(
        context.application.bot_data["db_path"]
    ) as conn:
        customers = SalesService(
            conn
        ).list_customers()
    buttons = [
        [
            InlineKeyboardButton(
                customer["name"],
                callback_data=f"sale:customer:{customer['id']}",
            )
        ]
        for customer in customers
    ]
    buttons.append(
        [
            InlineKeyboardButton(
                "❌ لغو",
                callback_data="sale:cancel",
            )
        ]
    )
    await query.edit_message_text(
        "🛒 ثبت فروش\n\n"
        "👤 مشتری را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(
            buttons
        ),
    )
    return CHOOSE_CUSTOMER
async def choose_customer(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()
    customer_id = int(
        query.data.split(":")[-1]
    )
    context.user_data[
        "sale"
    ]["customer_id"] = customer_id
    with get_conn(
        context.application.bot_data["db_path"]
    ) as conn:
        products = SalesService(
            conn
        ).list_products()
    buttons = [
        [
            InlineKeyboardButton(
                f"{product['name']} | "
                f"موجودی {product['stock_qty']:g}",
                callback_data=f"sale:product:{product['id']}",
            )
        ]
        for product in products
    ]
    buttons.append(
        [
            InlineKeyboardButton(
                "❌ لغو",
                callback_data="sale:cancel",
            )
        ]
    )
    await query.edit_message_text(
        "📦 کالا را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(
            buttons
        ),
    )
    return CHOOSE_PRODUCT
async def choose_product(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()
    product_id = int(
        query.data.split(":")[-1]
    )
    with get_conn(
        context.application.bot_data["db_path"]
    ) as conn:
        product = SalesService(
            conn
        ).get_product(product_id)
    if not product:
        await query.edit_message_text(
            "❌ کالا پیدا نشد.",
            reply_markup=back_home_markup(),
        )
        return ConversationHandler.END
    context.user_data[
        "sale"
    ].update(
        {
            "product_id": product_id,
            "product_name": product["name"],
            "default_price": product["sale_price"],
        }
    )
    await query.edit_message_text(
        f"📦 {product['name']}\n\n"
        f"💰 قیمت پیشنهادی: "
        f"{money(product['sale_price'])}\n\n"
        "🔢 تعداد را وارد کنید:"
    )
    return ENTER_QTY
async def enter_qty(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        quantity_text = digits(
            update.message.text
        )
        quantity = float(
            quantity_text
            .replace(",", "")
            .replace("٬", "")
        )
        if quantity <= 0:
            raise ValueError
    except Exception:
        await update.message.reply_text(
            "❌ تعداد معتبر وارد کنید.\n"
            "مثال: 2 یا 2.5"
        )
        return ENTER_QTY
    context.user_data[
        "sale"
    ]["qty"] = quantity
    default_price = context.user_data[
        "sale"
    ]["default_price"]
    await update.message.reply_text(
        "💰 قیمت واحد به ریال:\n"
        f"پیشنهادی: {money(default_price)}"
    )
    return ENTER_PRICE
async def enter_price(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        price = to_int(
            update.message.text,
            0,
        )
        context.user_data[
            "sale"
        ]["unit_price"] = price
        await update.message.reply_text(
            "🎁 تخفیف به ریال وارد کنید.\n"
            "اگر ندارد، 0:"
        )
        return ENTER_DISCOUNT
    except ValueError:
        await update.message.reply_text(
            "❌ قیمت معتبر وارد کنید."
        )
        return ENTER_PRICE
async def enter_discount(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        discount = to_int(
            update.message.text,
            0,
        )
    except ValueError:
        await update.message.reply_text(
            "❌ تخفیف معتبر وارد کنید."
        )
        return ENTER_DISCOUNT
    sale = context.user_data["sale"]
    subtotal = round(
        sale["qty"] * sale["unit_price"]
    )
    if discount > subtotal:
        await update.message.reply_text(
            "❌ تخفیف نمی‌تواند از مبلغ فروش بیشتر باشد."
        )
        return ENTER_DISCOUNT
    sale["discount"] = discount
    await update.message.reply_text(
        "💳 روش تسویه را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "💵 نقدی",
                        callback_data="sale:pay:cash",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🏦 بانکی",
                        callback_data="sale:pay:bank",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🧾 نسیه",
                        callback_data="sale:pay:credit",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "❌ لغو",
                        callback_data="sale:cancel",
                    )
                ],
            ]
        ),
    )
    return CHOOSE_PAYMENT
async def choose_payment(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()
    payment = query.data.split(":")[-1]
    sale = context.user_data["sale"]
    sale["payment_method"] = payment
    subtotal = round(
        sale["qty"] * sale["unit_price"]
    )
    total = (
        subtotal
        - sale["discount"]
    )
    labels = {
        "cash": "نقدی",
        "bank": "بانکی",
        "credit": "نسیه / دریافتنی",
    }
    payment_label = labels[payment]
    text = (
        "🧾 پیش‌نمایش فروش\n\n"
        f"📦 کالا: {sale['product_name']}\n"
        f"🔢 تعداد: {sale['qty']:g}\n"
        f"💰 قیمت واحد: "
        f"{money(sale['unit_price'])}\n"
        f"جمع: {money(subtotal)}\n"
        f"🎁 تخفیف: {money(sale['discount'])}\n"
        f"مالیات: فعلاً 0\n"
        f"💵 مبلغ نهایی: {money(total)}\n"
        f"💳 تسویه: {payment_label}\n\n"
        "ثبت نهایی شود؟"
    )
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ ثبت نهایی",
                        callback_data="sale:confirm",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "❌ لغو",
                        callback_data="sale:cancel",
                    )
                ],
            ]
        ),
    )
    return CONFIRM
async def confirm_sale(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()
    sale = context.user_data["sale"]
    try:
        with get_conn(
            context.application.bot_data["db_path"]
        ) as conn:
            result = SalesService(
                conn
            ).create_sale(
                customer_id=sale["customer_id"],
                product_id=sale["product_id"],
                qty=sale["qty"],
                unit_price=sale["unit_price"],
                discount=sale["discount"],
                payment_method=sale["payment_method"],
                telegram_user_id=update.effective_user.id,
            )
    except Exception as exc:
        await query.edit_message_text(
            "❌ ثبت فروش انجام نشد:\n\n"
            f"{exc}",
            reply_markup=back_home_markup(),
        )
        context.user_data.pop(
            "sale",
            None,
        )
        return ConversationHandler.END
    await query.edit_message_text(
        "✅ فروش با موفقیت ثبت شد.\n\n"
        f"🧾 شماره فاکتور: "
        f"{result['invoice_no']}\n"
        f"👤 مشتری: {result['customer_name']}\n"
        f"📦 کالا: {result['product_name']}\n"
        f"💵 مبلغ: {money(result['total'])}\n\n"
        "📒 سند حسابداری ثبت شد.\n"
        "📦 خروج موجودی ثبت شد.",
        reply_markup=back_home_markup(),
    )
    context.user_data.pop(
        "sale",
        None,
    )
    return ConversationHandler.END
async def cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text(
        "❌ عملیات لغو شد.",
        reply_markup=main_menu(),
    )
    return ConversationHandler.END
async def cancel_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data.clear()
    await update.message.reply_text(
        "❌ عملیات لغو شد.",
        reply_markup=main_menu(),
    )
    return ConversationHandler.END
# =========================================================
# Application
# =========================================================
def build_application(
    token: str,
    db_path: str,
) -> Application:
    application = (
        Application
        .builder()
        .token(token)
        .concurrent_updates(False)
        .build()
    )
    application.bot_data[
        "db_path"
    ] = db_path
    # -----------------------------------------------------
    # Sales Conversation
    # -----------------------------------------------------
    sale_conversation = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                sale_start,
                pattern=r"^sale:start$",
            )
        ],
        states={
            CHOOSE_CUSTOMER: [
                CallbackQueryHandler(
                    choose_customer,
                    pattern=r"^sale:customer:\d+$",
                )
            ],
            CHOOSE_PRODUCT: [
                CallbackQueryHandler(
                    choose_product,
                    pattern=r"^sale:product:\d+$",
                )
            ],
            ENTER_QTY: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    enter_qty,
                )
            ],
            ENTER_PRICE: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    enter_price,
                )
            ],
            ENTER_DISCOUNT: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    enter_discount,
                )
            ],
            CHOOSE_PAYMENT: [
                CallbackQueryHandler(
                    choose_payment,
                    pattern=r"^sale:pay:(cash|bank|credit)$",
                )
            ],
            CONFIRM: [
                CallbackQueryHandler(
                    confirm_sale,
                    pattern=r"^sale:confirm$",
                )
            ],
        },
        fallbacks=[
            CommandHandler(
                "cancel",
                cancel_command,
            ),
            CallbackQueryHandler(
                cancel,
                pattern=r"^sale:cancel$",
            ),
        ],
        allow_reentry=True,
    )
    # -----------------------------------------------------
    # Customer Add
    # -----------------------------------------------------
    customer_add = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                customer_add_start,
                pattern=r"^customer:add$",
            )
        ],
        states={
            C_NAME: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    customer_add_name,
                )
            ],
            C_PHONE: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    customer_add_phone,
                )
            ],
            C_BALANCE: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    customer_add_balance,
                )
            ],
        },
        fallbacks=[
            CommandHandler(
                "cancel",
                cancel_command,
            )
        ],
        allow_reentry=True,
    )
    # -----------------------------------------------------
    # Customer Edit
    # -----------------------------------------------------
    customer_edit = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                customer_edit_start,
                pattern=r"^customer:edit:\d+$",
            )
        ],
        states={
            C_NAME: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    customer_edit_name,
                )
            ],
            C_PHONE: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    customer_edit_phone,
                )
            ],
            C_BALANCE: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    customer_edit_balance,
                )
            ],
        },
        fallbacks=[
            CommandHandler(
                "cancel",
                cancel_command,
            )
        ],
        allow_reentry=True,
    )
    # -----------------------------------------------------
    # Product Add
    # -----------------------------------------------------
    product_add = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                product_add_start,
                pattern=r"^product:add$",
            )
        ],
        states={
            P_SKU: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    product_add_sku,
                )
            ],
            P_NAME: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    product_add_name,
                )
            ],
            P_SALE: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    product_add_sale,
                )
            ],
            P_COST: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    product_add_cost,
                )
            ],
            P_STOCK: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    product_add_stock,
                )
            ],
        },
        fallbacks=[
            CommandHandler(
                "cancel",
                cancel_command,
            )
        ],
        allow_reentry=True,
    )
    # -----------------------------------------------------
    # Product Edit
    # -----------------------------------------------------
    product_edit = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                product_edit_start,
                pattern=r"^product:edit:\d+$",
            )
        ],
        states={
            P_SKU: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    product_edit_sku,
                )
            ],
            P_NAME: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    product_edit_name,
                )
            ],
            P_SALE: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    product_edit_sale,
                )
            ],
            P_COST: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    product_edit_cost,
                )
            ],
        },
        fallbacks=[
            CommandHandler(
                "cancel",
                cancel_command,
            )
        ],
        allow_reentry=True,
    )
    # -----------------------------------------------------
    # Register handlers
    # -----------------------------------------------------
    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )
    application.add_handler(
        sale_conversation
    )
    application.add_handler(
        customer_add
    )
    application.add_handler(
        customer_edit
    )
    application.add_handler(
        product_add
    )
    application.add_handler(
        product_edit
    )
    application.add_handler(
        CallbackQueryHandler(
            home,
            pattern=r"^home$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            coming,
            pattern=r"^coming:(purchase|reports|settings)$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            customers_list,
            pattern=r"^customers:list$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            customer_view,
            pattern=r"^customer:view:\d+$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            customer_deactivate,
            pattern=r"^customer:deactivate:\d+$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            products_list,
            pattern=r"^products:list$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            product_view,
            pattern=r"^product:view:\d+$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            product_deactivate,
            pattern=r"^product:deactivate:\d+$",
        )
    )
    return application
