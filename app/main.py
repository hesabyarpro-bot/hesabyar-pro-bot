import os
import threading

from http.server import (
    BaseHTTPRequestHandler,
    HTTPServer,
)

from dotenv import load_dotenv

from telegram import Update

from .db import init_db
from .bot import build_application


load_dotenv()


class HealthHandler(
    BaseHTTPRequestHandler
):

    def do_GET(self):

        if self.path.startswith(
            "/health"
        ):

            self.send_response(200)

            self.send_header(
                "Content-Type",
                "text/plain; charset=utf-8",
            )

            self.end_headers()

            self.wfile.write(
                b"OK"
            )

            return

        self.send_response(404)
        self.end_headers()


    def log_message(
        self,
        format_string,
        *args,
    ):
        pass


def health_server():

    port = int(
        os.getenv(
            "PORT",
            "10000",
        )
    )

    server = HTTPServer(
        (
            "0.0.0.0",
            port,
        ),
        HealthHandler,
    )

    server.serve_forever()


def main():

    load_dotenv()

    init_db()

    thread = threading.Thread(
        target=health_server,
        daemon=True,
    )

    thread.start()

    token = os.getenv(
        "BOT_TOKEN"
    )

    if not token:
        raise RuntimeError(
            "BOT_TOKEN تنظیم نشده است."
        )

    application = build_application(
        token
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
