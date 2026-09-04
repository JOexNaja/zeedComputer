import sqlite3

def init_db():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    # สร้างตาราง reports ถ้ายังไม่มี
    cur.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        cash REAL DEFAULT 0,
        transfer REAL DEFAULT 0,
        other REAL DEFAULT 0,
        expense REAL DEFAULT 0,
        income REAL DEFAULT 0,
        net REAL DEFAULT 0
    )
    """)

    # ใส่ข้อมูลตัวอย่าง (seed data)
    sample_data = [
        ("2026-09-01", 500, 1000, 200, 800, 1700, 900),
        ("2026-09-02", 300, 700, 100, 600, 1100, 500),
        ("2026-09-03", 200, 400, 50, 700, 650, -50),
    ]

    cur.executemany("""
    INSERT INTO reports (date, cash, transfer, other, expense, income, net)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, sample_data)

    conn.commit()
    conn.close()
    print("✅ สร้างตาราง reports และใส่ข้อมูลตัวอย่างเรียบร้อยแล้ว!")

if __name__ == "__main__":
    init_db()
