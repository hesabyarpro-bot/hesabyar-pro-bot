from . import db


class SalesService:

    @staticmethod
    def create_sale(
        customer_id,
        items,
        payment_method,
        discount=0,
        tax=0,
    ):

        return db.create_invoice(
            invoice_type="sale",
            party_id=customer_id,
            items=items,
            payment_method=payment_method,
            discount=discount,
            tax=tax,
        )


    @staticmethod
    def get_sale(invoice_id):

        return db.get_invoice(
            invoice_id
        )


    @staticmethod
    def list_sales(limit=20):

        invoices = db.list_invoices(
            limit
        )

        return [
            invoice
            for invoice in invoices
            if invoice["invoice_type"]
            == "sale"
        ]
