import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler

from app.db import init_db
from app.bot import register_handlers


load_dotenv()


class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"HesabYar Pro is running")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return


def start_health_server():
    port = int(os.getenv("PORT", "10000"))

    server = HTTPServer(
        ("0.0.0.0", port),
        HealthHandler
    )

    print(f"Health server running on port {port}")

    server.serve_forever()


async def start_command(
    update: Update,
    context
):
    await update.message.reply_text(
        "سلام 👋\n\n"
        "به حساب‌یار پرو خوش آمدید.\n"
        "دستیار مالی و حسابداری شما آماده است."
    )


def main():

    bot_token = os.getenv("BOT_TOKEN")

    if not bot_token:
        raise RuntimeError(
            "BOT_TOKEN environment variable is not configured."
        )

    init_db()

    threading.Thread(
        target=start_health_server,
        daemon=True
    ).start()

    application = (
        ApplicationBuilder()
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

    register_handlers(application)

    print("HesabYar Pro Bot is starting...")

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
