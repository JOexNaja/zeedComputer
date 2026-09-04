-- ตารางลูกค้า
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
);

-- ตารางรายรับ
CREATE TABLE IF NOT EXISTS income (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    source TEXT,          -- เงินสด / เงินโอน
    activity TEXT,        -- กิจกรรม/ทำอะไร
    amount REAL NOT NULL,
    note TEXT,
    customer_id INTEGER,
    FOREIGN KEY(customer_id) REFERENCES customers(id)
);

-- ตารางรายจ่าย
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    item TEXT,            -- รายการ เช่น SSD, ค่าข้าว
    amount REAL NOT NULL,
    note TEXT
);

-- ตารางเปรียบเทียบ (เรียลไทม์/สรุปรายวัน)
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    cash REAL DEFAULT 0,       -- เงินสด
    transfer REAL DEFAULT 0,   -- เงินโอน
    other REAL DEFAULT 0,      -- รายการอื่น ๆ
    expense REAL DEFAULT 0,    -- รายจ่ายรวม
    income REAL DEFAULT 0,     -- รายรับรวม
    net REAL DEFAULT 0         -- สุทธิ (รายรับ - รายจ่าย)
);

