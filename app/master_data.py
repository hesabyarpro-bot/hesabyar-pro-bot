from __future__ import annotations
def norm_text(value: str) -> str:
    return " ".join(
        (value or "").strip().split()
    )
def digits(value: str) -> str:
    """
    تبدیل اعداد فارسی و عربی به انگلیسی.
    """
    value = str(value or "")
    translation = str.maketrans(
        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩٬,",
        "0123456789012345678,,",
    )
    return value.translate(translation)
def to_int(value: str, minimum: int = 0) -> int:
    value = digits(value)
    value = (
        value
        .replace(",", "")
        .replace("٬", "")
        .strip()
    )
    number = int(value)
    if number < minimum:
        raise ValueError
    return number
# =========================================================
# Customers
# =========================================================
def list_customers(
    conn,
    active_only: bool = True,
):
    sql = """
        SELECT
            id,
            name,
            phone,
            opening_balance,
            active,
            created_at
        FROM customers
    """
    if active_only:
        sql += " WHERE active = 1"
    sql += " ORDER BY id DESC"
    return conn.execute(sql).fetchall()
def get_customer(
    conn,
    customer_id: int,
):
    return conn.execute(
        """
        SELECT
            id,
            name,
            phone,
            opening_balance,
            active,
            created_at
        FROM customers
        WHERE id = ?
        """,
        (customer_id,),
    ).fetchone()
def create_customer(
    conn,
    name: str,
    phone: str = "",
    opening_balance: int = 0,
):
    name = norm_text(name)
    phone = norm_text(phone)
    if not name:
        raise ValueError(
            "نام مشتری الزامی است."
        )
    if opening_balance < 0:
        raise ValueError(
            "مانده افتتاحیه منفی مجاز نیست."
        )
    cursor = conn.execute(
        """
        INSERT INTO customers(
            name,
            phone,
            opening_balance,
            active
        )
        VALUES (?, ?, ?, 1)
        """,
        (
            name,
            phone or None,
            opening_balance,
        ),
    )
    return get_customer(
        conn,
        cursor.lastrowid,
    )
def update_customer(
    conn,
    customer_id: int,
    name: str,
    phone: str,
    opening_balance: int,
):
    name = norm_text(name)
    phone = norm_text(phone)
    if not name:
        raise ValueError(
            "نام مشتری الزامی است."
        )
    if opening_balance < 0:
        raise ValueError(
            "مانده افتتاحیه منفی مجاز نیست."
        )
    conn.execute(
        """
        UPDATE customers
        SET
            name = ?,
            phone = ?,
            opening_balance = ?
        WHERE id = ?
        """,
        (
            name,
            phone or None,
            opening_balance,
            customer_id,
        ),
    )
    return get_customer(
        conn,
        customer_id,
    )
def deactivate_customer(
    conn,
    customer_id: int,
):
    conn.execute(
        """
        UPDATE customers
        SET active = 0
        WHERE id = ?
        """,
        (customer_id,),
    )
def activate_customer(
    conn,
    customer_id: int,
):
    conn.execute(
        """
        UPDATE customers
        SET active = 1
        WHERE id = ?
        """,
        (customer_id,),
    )
# =========================================================
# Products
# =========================================================
def list_products(
    conn,
    active_only: bool = True,
):
    sql = """
        SELECT
            id,
            sku,
            name,
            sale_price,
            purchase_cost,
            stock_qty,
            active
        FROM products
    """
    if active_only:
        sql += " WHERE active = 1"
    sql += " ORDER BY id DESC"
    return conn.execute(sql).fetchall()
def get_product(
    conn,
    product_id: int,
):
    return conn.execute(
        """
        SELECT
            id,
            sku,
            name,
            sale_price,
            purchase_cost,
            stock_qty,
            active
        FROM products
        WHERE id = ?
        """,
        (product_id,),
    ).fetchone()
def create_product(
    conn,
    sku: str,
    name: str,
    sale_price: int,
    purchase_cost: int,
    stock_qty: float = 0,
):
    sku = norm_text(sku)
    name = norm_text(name)
    if not name:
        raise ValueError(
            "نام کالا الزامی است."
        )
    if sale_price < 0:
        raise ValueError(
            "قیمت فروش نمی‌تواند منفی باشد."
        )
    if purchase_cost < 0:
        raise ValueError(
            "بهای خرید نمی‌تواند منفی باشد."
        )
    if stock_qty < 0:
        raise ValueError(
            "موجودی نمی‌تواند منفی باشد."
        )
    try:
        cursor = conn.execute(
            """
            INSERT INTO products(
                sku,
                name,
                sale_price,
                purchase_cost,
                stock_qty,
                active
            )
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (
                sku or None,
                name,
                sale_price,
                purchase_cost,
                stock_qty,
            ),
        )
    except sqlite3.IntegrityError as exc:
        if "UNIQUE" in str(exc).upper():
            raise ValueError(
                "کد کالا تکراری است."
            ) from exc
        raise
    return get_product(
        conn,
        cursor.lastrowid,
    )
def update_product(
    conn,
    product_id: int,
    sku: str,
    name: str,
    sale_price: int,
    purchase_cost: int,
):
    sku = norm_text(sku)
    name = norm_text(name)
    if not name:
        raise ValueError(
            "نام کالا الزامی است."
        )
    if sale_price < 0:
        raise ValueError(
            "قیمت فروش نمی‌تواند منفی باشد."
        )
    if purchase_cost < 0:
        raise ValueError(
            "بهای خرید نمی‌تواند منفی باشد."
        )
    try:
        conn.execute(
            """
            UPDATE products
            SET
                sku = ?,
                name = ?,
                sale_price = ?,
                purchase_cost = ?
            WHERE id = ?
            """,
            (
                sku or None,
                name,
                sale_price,
                purchase_cost,
                product_id,
            ),
        )
    except sqlite3.IntegrityError as exc:
        if "UNIQUE" in str(exc).upper():
            raise ValueError(
                "کد کالا تکراری است."
            ) from exc
        raise
    return get_product(
        conn,
        product_id,
    )
def deactivate_product(
    conn,
    product_id: int,
):
    conn.execute(
        """
        UPDATE products
        SET active = 0
        WHERE id = ?
        """,
        (product_id,),
    )
def activate_product(
    conn,
    product_id: int,
):
    conn.execute(
        """
        UPDATE products
        SET active = 1
        WHERE id = ?
        """,
        (product_id,),
    )
