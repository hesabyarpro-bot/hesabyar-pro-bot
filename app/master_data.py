import sqlite3

from app.db import (
    list_customers,
    create_customer,
    deactivate_customer,
    list_products,
    create_product,
    deactivate_product,
    list_suppliers,
    create_supplier,
    deactivate_supplier,
)


def add_customer(name, phone="", address=""):
    name = (name or "").strip()

    if not name:
        raise ValueError("نام مشتری الزامی است.")

    try:
        return create_customer(
            name=name,
            phone=phone.strip(),
            address=address.strip(),
        )
    except sqlite3.IntegrityError:
        raise ValueError("ثبت مشتری انجام نشد.")


def add_product(
    name,
    code="",
    unit="عدد",
    purchase_cost=0,
    sale_price=0,
    min_stock=0,
):
    name = (name or "").strip()

    if not name:
        raise ValueError("نام کالا الزامی است.")

    try:
        return create_product(
            name=name,
            code=code.strip(),
            unit=unit.strip() or "عدد",
            purchase_cost=float(purchase_cost or 0),
            sale_price=float(sale_price or 0),
            min_stock=float(min_stock or 0),
        )
    except sqlite3.IntegrityError:
        raise ValueError("ثبت کالا انجام نشد.")


def add_supplier(name, phone="", address=""):
    name = (name or "").strip()

    if not name:
        raise ValueError("نام تأمین‌کننده الزامی است.")

    try:
        return create_supplier(
            name=name,
            phone=phone.strip(),
            address=address.strip(),
        )
    except sqlite3.IntegrityError:
        raise ValueError("ثبت تأمین‌کننده انجام نشد.")


def customers():
    return list_customers()


def products():
    return list_products()


def suppliers():
    return list_suppliers()


def remove_customer(customer_id):
    deactivate_customer(customer_id)


def remove_product(product_id):
    deactivate_product(product_id)


def remove_supplier(supplier_id):
    deactivate_supplier(supplier_id)
