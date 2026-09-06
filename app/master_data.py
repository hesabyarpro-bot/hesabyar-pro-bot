from .db import (
    create_customer,
    create_product,
    create_supplier,
    list_customers,
    list_products,
    list_suppliers,
)


def add_customer(
    name,
    phone=None,
    address=None,
):
    return create_customer(
        name,
        phone,
        address,
    )


def add_product(
    name,
    code=None,
    unit="عدد",
    sale_price=0,
    purchase_cost=0,
    stock=0,
    min_stock=0,
):
    return create_product(
        name,
        code,
        unit,
        sale_price,
        purchase_cost,
        stock,
        min_stock,
    )


def add_supplier(
    name,
    phone=None,
    address=None,
):
    return create_supplier(
        name,
        phone,
        address,
    )


def customers():
    return list_customers()


def products():
    return list_products()


def suppliers():
    return list_suppliers()
