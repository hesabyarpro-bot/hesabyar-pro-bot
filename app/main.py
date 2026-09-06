import os
import threading

from http.server import (
    BaseHTTPRequestHandler,
    HTTPServer,
)

from dotenv import load_dotenv

from .bot import build_application


load_dotenv()


class HealthHandler(
    BaseHTTPRequestHandler
):

    def do_GET(self):

        if self.path in (
            "/",
            "/health",
        ):

            body = b"OK"

            self.send_response(200)

            self.send_header(
                "Content-Type",
                "text/plain; charset=utf-8",
            )

            self.send_header(
                "Content-Length",
                str(len(body)),
            )

            self.end_headers()

            self.wfile.write(body)

        else:

            self.send_response(404)
            self.end_headers()

    def log_message(
        self,
        format,
        *args,
    ):
        return


def start_health_server():

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

    bot_token = os.getenv(
        "BOT_TOKEN"
    )

    if not bot_token:
        raise RuntimeError(
            "BOT_TOKEN در Environment Variables "
            "تنظیم نشده است."
        )

    thread = threading.Thread(
        target=start_health_server,
        daemon=True,
    )

    thread.start()

    application = build_application()

    application.run_polling(
        allowed_updates=[
            "message",
            "callback_query",
        ]
    )


if __name__ == "__main__":
    main()
