from . import db


class PurchaseService:

    @staticmethod
    def create_purchase(
        supplier_id,
        items,
        payment_method,
        discount=0,
        tax=0,
    ):

        return db.create_invoice(
            invoice_type="purchase",
            party_id=supplier_id,
            items=items,
            payment_method=payment_method,
            discount=discount,
            tax=tax,
        )


    @staticmethod
    def get_purchase(invoice_id):

        return db.get_invoice(
            invoice_id
        )


    @staticmethod
    def list_purchases(limit=20):

        invoices = db.list_invoices(
            limit
        )

        return [
            invoice
            for invoice in invoices
            if invoice["invoice_type"]
            == "purchase"
        ]
