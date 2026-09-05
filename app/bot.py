import os
import logging
from telegram import (
    Update,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from app.db import init_db
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)
# =========================
# تنظیمات
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_TELEGRAM_ID = int(
    os.getenv("ADMIN_TELEGRAM_ID", "8806709666")
)
# =========================
# منوی اصلی
# =========================
def main_menu():
    keyboard = [
        ["🛒 ثبت فروش", "🧾 ثبت خرید"],
        ["👥 مشتریان", "📦 کالاها"],
        ["📊 گزارش‌ها", "💳 خرید اشتراک"],
        ["👨‍💼 ارتباط با پشتیبانی", "⚙️ تنظیمات"],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
    )
# =========================
# /start
# =========================
async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user
    logger.info(
        "User started bot: telegram_id=%s username=%s",
        user.id if user else None,
        user.username if user else None,
    )
    await update.message.reply_text(
        "سلام 👋\n\n"
        "به «حساب‌یار پرو» خوش آمدید.\n"
        "دستیار مالی و حسابداری کسب‌وکار شما.\n\n"
        "از منوی زیر گزینه موردنظر را انتخاب کنید:",
        reply_markup=main_menu(),
    )
# =========================
# ثبت فروش
# =========================
async def sales_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "🛒 بخش ثبت فروش\n\n"
        "ماژول ثبت فروش در حال توسعه و اتصال به موتور حسابداری است."
    )
# =========================
# ثبت خرید
# =========================
async def purchase_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "🧾 بخش ثبت خرید\n\n"
        "این بخش در حال توسعه است."
    )
# =========================
# مشتریان
# =========================
async def customers_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "👥 بخش مشتریان\n\n"
        "مدیریت مشتریان حساب‌یار پرو."
    )
# =========================
# کالاها
# =========================
async def products_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "📦 بخش کالاها\n\n"
        "مدیریت کالا و موجودی حساب‌یار پرو."
    )
# =========================
# گزارش‌ها
# =========================
async def reports_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "📊 گزارش‌ها\n\n"
        "گزارش‌های مالی و مدیریتی در حال تکمیل است."
    )
# =========================
# اشتراک
# =========================
async def subscription_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "💳 خرید اشتراک\n\n"
        "بخش اشتراک حساب‌یار پرو در حال آماده‌سازی است."
    )
# =========================
# پشتیبانی
# =========================
async def support_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "👨‍💼 ارتباط با پشتیبانی\n\n"
        "برای ارتباط با پشتیبانی پیام خود را ارسال کنید."
    )
# =========================
# تنظیمات
# =========================
async def settings_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "⚙️ تنظیمات\n\n"
        "تنظیمات حساب کاربری و کسب‌وکار شما."
    )
# =========================
# پیام‌های ناشناخته
# =========================
async def unknown_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.message:
        return
    await update.message.reply_text(
        "لطفاً یکی از گزینه‌های منوی اصلی را انتخاب کنید.",
        reply_markup=main_menu(),
    )
# =========================
# ثبت Handlerها
# =========================
def register_handlers(application: Application):
    application.add_handler(
        MessageHandler(
            filters.Regex("^🛒 ثبت فروش$"),
            sales_handler,
        )
    )
    application.add_handler(
        MessageHandler(
            filters.Regex("^🧾 ثبت خرید$"),
            purchase_handler,
        )
    )
    application.add_handler(
        MessageHandler(
            filters.Regex("^👥 مشتریان$"),
            customers_handler,
        )
    )
    application.add_handler(
        MessageHandler(
            filters.Regex("^📦 کالاها$"),
            products_handler,
        )
    )
    application.add_handler(
        MessageHandler(
            filters.Regex("^📊 گزارش‌ها$"),
            reports_handler,
        )
    )
    application.add_handler(
        MessageHandler(
            filters.Regex("^💳 خرید اشتراک$"),
            subscription_handler,
        )
    )
    application.add_handler(
        MessageHandler(
            filters.Regex("^👨‍💼 ارتباط با پشتیبانی$"),
            support_handler,
        )
    )
    application.add_handler(
        MessageHandler(
            filters.Regex("^⚙️ تنظیمات$"),
            settings_handler,
        )
    )
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            unknown_message,
        )
    )
# =========================
# ساخت Application
# =========================
def build_application():
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN environment variable is not configured."
        )
    # اطمینان از آماده بودن دیتابیس
    init_db()
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .concurrent_updates(False)
        .build()
    )
    application.add_handler(
        CommandHandler(
            "start",
            start_command,
        )
    )
    register_handlers(application)
    return application
