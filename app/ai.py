"""
AI / OCR integration layer.

در این نسخه هیچ نتیجه ساختگی از AI تولید نمی‌شود.
بعداً می‌توان OpenAI یا سرویس OCR واقعی را به این لایه متصل کرد.
"""


def extract_invoice_text(
    text: str,
) -> dict:

    return {
        "status": "needs_review",
        "raw_text": text,
        "message": (
            "سرویس AI هنوز متصل نشده است. "
            "اطلاعات باید به صورت دستی "
            "تأیید شود."
        ),
    }


def classify_document(
    text: str,
) -> dict:

    return {
        "status": "needs_review",
        "document_type": "unknown",
        "confidence": 0,
        "message": (
            "برای طبقه‌بندی خودکار، "
            "اتصال AI لازم است."
        ),
    }
