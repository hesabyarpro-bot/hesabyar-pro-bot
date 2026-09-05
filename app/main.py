import os
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

from app.db import init_db
from app.bot import register_handlers


load_dotenv()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام 👋\n"
        "به حساب‌یار پرو خوش آمدید.\n\n"
        "دستیار مالی و حسابداری هوشمند شما آماده است."
    )


def main():
    bot_token = os.getenv("BOT_TOKEN")

    if not bot_token:
        raise RuntimeError(
            "BOT_TOKEN environment variable is not configured."
        )

    init_db()

    application = (
        ApplicationBuilder()
        .token(bot_token)
        .concurrent_updates(False)
        .build()
    )

    application.add_handler(CommandHandler("start", start))

    register_handlers(application)

    print("HesabYar Pro Bot is running...")

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
