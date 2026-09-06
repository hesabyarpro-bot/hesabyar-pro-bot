PRAGMA foreign_keys = ON;

-- ============================================================
-- Telegram Users
-- ============================================================

CREATE TABLE IF NOT EXISTS telegram_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL UNIQUE,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);


-- ============================================================
-- Customers
-- ============================================================

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    national_id TEXT,
    address TEXT,
    notes TEXT,
    active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
);


-- ============================================================
-- Suppliers
-- ============================================================

CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    national_id TEXT,
    address TEXT,
    notes TEXT,
    active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
);


-- ============================================================
-- Products
-- ============================================================

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    sku TEXT UNIQUE,
    unit TEXT DEFAULT 'عدد',
    sale_price INTEGER DEFAULT 0,
    purchase_cost INTEGER DEFAULT 0,
    stock REAL DEFAULT 0,
    min_stock REAL DEFAULT 0,
    active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
);


-- ============================================================
-- Invoices
-- ============================================================

CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_type TEXT NOT NULL,
    invoice_number TEXT,
    customer_id INTEGER,
    supplier_id INTEGER,
    invoice_date TEXT NOT NULL,
    subtotal INTEGER DEFAULT 0,
    discount INTEGER DEFAULT 0,
    tax INTEGER DEFAULT 0,
    total INTEGER DEFAULT 0,
    payment_method TEXT,
    status TEXT DEFAULT 'confirmed',
    notes TEXT,
    created_at TEXT NOT NULL,

    FOREIGN KEY(customer_id)
        REFERENCES customers(id),

    FOREIGN KEY(supplier_id)
        REFERENCES suppliers(id)
);


-- ============================================================
-- Invoice Items
-- ============================================================

CREATE TABLE IF NOT EXISTS invoice_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity REAL NOT NULL,
    unit_price INTEGER NOT NULL,
    discount INTEGER DEFAULT 0,
    tax INTEGER DEFAULT 0,
    line_total INTEGER NOT NULL,

    FOREIGN KEY(invoice_id)
        REFERENCES invoices(id)
        ON DELETE CASCADE,

    FOREIGN KEY(product_id)
        REFERENCES products(id)
);


-- ============================================================
-- Stock Movements
-- ============================================================

CREATE TABLE IF NOT EXISTS stock_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    movement_type TEXT NOT NULL,
    quantity REAL NOT NULL,
    unit_cost INTEGER DEFAULT 0,
    reference_type TEXT,
    reference_id INTEGER,
    movement_date TEXT NOT NULL,
    notes TEXT,

    FOREIGN KEY(product_id)
        REFERENCES products(id)
);


-- ============================================================
-- Journal Entries
-- ============================================================

CREATE TABLE IF NOT EXISTS journal_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_number TEXT,
    entry_date TEXT NOT NULL,
    description TEXT,
    reference_type TEXT,
    reference_id INTEGER,
    status TEXT DEFAULT 'posted',
    created_at TEXT NOT NULL
);


-- ============================================================
-- Journal Lines
-- ============================================================

CREATE TABLE IF NOT EXISTS journal_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    journal_entry_id INTEGER NOT NULL,
    account_code TEXT NOT NULL,
    account_name TEXT,
    debit INTEGER DEFAULT 0,
    credit INTEGER DEFAULT 0,

    FOREIGN KEY(journal_entry_id)
        REFERENCES journal_entries(id)
        ON DELETE CASCADE
);


-- ============================================================
-- Subscription Payments
-- ============================================================

CREATE TABLE IF NOT EXISTS subscription_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_user_id INTEGER NOT NULL,
    plan_code TEXT,
    plan_name TEXT,
    amount INTEGER DEFAULT 0,
    receipt_file_id TEXT,
    receipt_file_unique_id TEXT,
    status TEXT DEFAULT 'pending',
    submitted_at TEXT,
    reviewed_at TEXT,
    reviewed_by INTEGER,
    rejection_reason TEXT,

    FOREIGN KEY(telegram_user_id)
        REFERENCES telegram_users(id)
);


-- ============================================================
-- Subscriptions
-- ============================================================

CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_user_id INTEGER NOT NULL,
    plan_code TEXT,
    plan_name TEXT,
    start_date TEXT,
    end_date TEXT,
    status TEXT DEFAULT 'inactive',
    payment_id INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    FOREIGN KEY(telegram_user_id)
        REFERENCES telegram_users(id)
);


-- ============================================================
-- Indexes
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_customers_active
ON customers(active);

CREATE INDEX IF NOT EXISTS idx_suppliers_active
ON suppliers(active);

CREATE INDEX IF NOT EXISTS idx_products_active
ON products(active);

CREATE INDEX IF NOT EXISTS idx_invoices_type
ON invoices(invoice_type);

CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice
ON invoice_items(invoice_id);

CREATE INDEX IF NOT EXISTS idx_stock_product
ON stock_movements(product_id);

CREATE INDEX IF NOT EXISTS idx_journal_reference
ON journal_entries(reference_type, reference_id);
