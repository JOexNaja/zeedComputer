CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    note TEXT
);

CREATE TABLE IF NOT EXISTS income (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    customer_id INTEGER,
    activity TEXT,
    amount REAL,
    shop_get REAL,
    discount REAL,
    note TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers (id)
);

CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    item TEXT NOT NULL,
    amount REAL NOT NULL,
    note TEXT
);

CREATE TABLE IF NOT EXISTS credits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shop_name TEXT NOT NULL,
    item TEXT NOT NULL,
    amount REAL NOT NULL,
    date TEXT NOT NULL,
    paid INTEGER DEFAULT 0,
    note TEXT
);

CREATE TABLE IF NOT EXISTS debtors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    item TEXT NOT NULL,
    amount REAL NOT NULL,
    date TEXT NOT NULL,
    paid INTEGER DEFAULT 0,
    note TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers (id)
);

CREATE TABLE IF NOT EXISTS partners (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    share_percent REAL NOT NULL,
    note TEXT
);

CREATE TABLE IF NOT EXISTS partner_withdrawals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    partner_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    amount REAL NOT NULL,
    note TEXT,
    FOREIGN KEY (partner_id) REFERENCES partners (id)
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    cash REAL DEFAULT 0,
    transfer REAL DEFAULT 0,
    other REAL DEFAULT 0,
    expense REAL DEFAULT 0,
    income REAL DEFAULT 0,
    net REAL DEFAULT 0
);
