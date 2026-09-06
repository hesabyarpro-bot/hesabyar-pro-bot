PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS telegram_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    national_id TEXT,
    address TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    national_id TEXT,
    address TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    unit TEXT DEFAULT 'عدد',
    sale_price INTEGER NOT NULL DEFAULT 0,
    purchase_cost INTEGER NOT NULL DEFAULT 0,
    stock REAL NOT NULL DEFAULT 0,
    min_stock REAL NOT NULL DEFAULT 0,
    active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_no INTEGER UNIQUE NOT NULL,
    invoice_type TEXT NOT NULL,
    customer_id INTEGER,
    supplier_id INTEGER,
    subtotal INTEGER NOT NULL DEFAULT 0,
    discount INTEGER NOT NULL DEFAULT 0,
    tax INTEGER NOT NULL DEFAULT 0,
    total INTEGER NOT NULL DEFAULT 0,
    payment_method TEXT,
    status TEXT DEFAULT 'confirmed',
    created_at TEXT NOT NULL,

    FOREIGN KEY(customer_id)
        REFERENCES customers(id),

    FOREIGN KEY(supplier_id)
        REFERENCES suppliers(id)
);

CREATE TABLE IF NOT EXISTS invoice_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    qty REAL NOT NULL,
    unit_price INTEGER NOT NULL,
    discount INTEGER DEFAULT 0,
    tax INTEGER DEFAULT 0,
    line_total INTEGER NOT NULL,
    cost_total INTEGER DEFAULT 0,

    FOREIGN KEY(invoice_id)
        REFERENCES invoices(id)
        ON DELETE CASCADE,

    FOREIGN KEY(product_id)
        REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS stock_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    movement_type TEXT NOT NULL,
    qty REAL NOT NULL,
    unit_cost INTEGER DEFAULT 0,
    ref_type TEXT,
    ref_id INTEGER,
    created_at TEXT NOT NULL,

    FOREIGN KEY(product_id)
        REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS journal_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ref_type TEXT,
    ref_id INTEGER,
    description TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS journal_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    journal_id INTEGER NOT NULL,
    account_code TEXT NOT NULL,
    debit INTEGER DEFAULT 0,
    credit INTEGER DEFAULT 0,

    FOREIGN KEY(journal_id)
        REFERENCES journal_entries(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    amount INTEGER NOT NULL,
    payment_method TEXT,
    note TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS subscription_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_user_id INTEGER NOT NULL,
    plan_code TEXT NOT NULL,
    plan_name TEXT NOT NULL,
    amount INTEGER NOT NULL,
    receipt_file_id TEXT,
    receipt_file_unique_id TEXT,
    status TEXT DEFAULT 'pending',
    submitted_at TEXT NOT NULL,
    reviewed_at TEXT,
    reviewed_by INTEGER,
    rejection_reason TEXT,

    FOREIGN KEY(telegram_user_id)
        REFERENCES telegram_users(id)
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_user_id INTEGER NOT NULL,
    plan_code TEXT NOT NULL,
    plan_name TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    payment_id INTEGER,
    created_at TEXT NOT NULL,

    FOREIGN KEY(telegram_user_id)
        REFERENCES telegram_users(id),

    FOREIGN KEY(payment_id)
        REFERENCES subscription_payments(id)
);

CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice
ON invoice_items(invoice_id);

CREATE INDEX IF NOT EXISTS idx_stock_product
ON stock_movements(product_id);

CREATE INDEX IF NOT EXISTS idx_payments_status
ON subscription_payments(status);
