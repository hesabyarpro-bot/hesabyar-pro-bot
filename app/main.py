import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler
from app.db import init_db
from app.bot import register_handlers, start_command
# Load environment variables
load_dotenv()
# ============================================================
# Health Check Server
# Compatible with UptimeRobot HEAD + GET
# ============================================================
class HealthHandler(BaseHTTPRequestHandler):
    def _health_response(self, send_body=True):
        body = b"HesabYar Pro is running"
        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )
        self.send_header(
            "Content-Length",
            str(len(body))
        )
        self.send_header(
            "Cache-Control",
            "no-cache"
        )
        self.end_headers()
        # GET باید Body داشته باشد
        # HEAD نباید Body داشته باشد
        if send_body:
            self.wfile.write(body)
    # --------------------------------------------------------
    # GET /health
    # --------------------------------------------------------
    def do_GET(self):
        if self.path == "/health":
            self._health_response(send_body=True)
            return
        self.send_response(404)
        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )
        self.end_headers()
    # --------------------------------------------------------
    # HEAD /health
    # --------------------------------------------------------
    def do_HEAD(self):
        if self.path == "/health":
            self._health_response(send_body=False)
            return
        self.send_response(404)
        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )
        self.end_headers()
    # --------------------------------------------------------
    # Disable default HTTP logs
    # --------------------------------------------------------
    def log_message(self, format, *args):
        return
# ============================================================
# Start Health Server
# ============================================================
def start_health_server():
    port = int(os.getenv("PORT", "10000"))
    server = HTTPServer(
        ("0.0.0.0", port),
        HealthHandler
    )
    print(
        f"Health server running on 0.0.0.0:{port}"
    )
    server.serve_forever()
# ============================================================
# Main Application
# ============================================================
def main():
    # --------------------------------------------------------
    # Read Telegram Bot Token
    # --------------------------------------------------------
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise RuntimeError(
            "BOT_TOKEN environment variable is not configured."
        )
    # --------------------------------------------------------
    # Initialize Database
    # --------------------------------------------------------
    init_db()
    print(
        "Database initialized successfully."
    )
    # --------------------------------------------------------
    # Start Render Health Server
    # --------------------------------------------------------
    health_thread = threading.Thread(
        target=start_health_server,
        daemon=True
    )
    health_thread.start()
    # --------------------------------------------------------
    # Build Telegram Application
    # --------------------------------------------------------
    application = (
        ApplicationBuilder()
        .token(bot_token)
        .concurrent_updates(False)
        .build()
    )
    # --------------------------------------------------------
    # /start Command
    # --------------------------------------------------------
    application.add_handler(
        CommandHandler(
            "start",
            start_command
        )
    )
    # --------------------------------------------------------
    # Register All Bot Handlers
    # --------------------------------------------------------
    register_handlers(application)
    print(
        "HesabYar Pro Bot is starting..."
    )
    # --------------------------------------------------------
    # Start Telegram Polling
    # --------------------------------------------------------
    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )
# ============================================================
# Entry Point
# ============================================================
if __name__ == "__main__":
    main()
