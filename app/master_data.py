from . import db


def customers():
    return db.list_customers()


def suppliers():
    return db.list_suppliers()


def products():
    return db.list_products()


def new_customer(
    name,
    phone="",
    national_id="",
    address="",
):
    return db.add_customer(
        name,
        phone,
        national_id,
        address,
    )


def new_supplier(
    name,
    phone="",
    national_id="",
    address="",
):
    return db.add_supplier(
        name,
        phone,
        national_id,
        address,
    )


def new_product(
    code,
    name,
    unit,
    sale_price,
    purchase_cost,
    min_stock,
):
    return db.add_product(
        code,
        name,
        unit,
        sale_price,
        purchase_cost,
        min_stock,
    )
