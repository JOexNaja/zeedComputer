import sqlite3

def migrate_income_schema(db_path="mydb.sqlite"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # ตรวจสอบคอลัมน์ที่มีอยู่ใน income
    cursor.execute("PRAGMA table_info(income)")
    columns = [col[1] for col in cursor.fetchall()]

    # ถ้าไม่มี activity → เพิ่ม
    if "activity" not in columns:
        cursor.execute("ALTER TABLE income ADD COLUMN activity TEXT")
        print("เพิ่มคอลัมน์ activity แล้ว")

    # ถ้าไม่มี shop_get → เพิ่ม
    if "shop_get" not in columns:
        cursor.execute("ALTER TABLE income ADD COLUMN shop_get REAL")
        print("เพิ่มคอลัมน์ shop_get แล้ว")

    # ถ้าไม่มี discount → เพิ่ม
    if "discount" not in columns:
        cursor.execute("ALTER TABLE income ADD COLUMN discount REAL")
        print("เพิ่มคอลัมน์ discount แล้ว")

    conn.commit()
    conn.close()
    print("Migration เสร็จสมบูรณ์")

if __name__ == "__main__":
    migrate_income_schema()
