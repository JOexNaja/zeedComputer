from flask import Flask, render_template, request, redirect, url_for, session

import sqlite3
from datetime import date, datetime


app = Flask(__name__)
app.secret_key = "your-secret-key"   # ✅ ใส่ค่าอะไรก็ได้ แต่ควรเป็น string ยาว ๆ


def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# ฟังก์ชันแปลงวันที่เป็นปี พ.ศ.
def thai_date(value, fmt="%d-%m-%Y"):
    if not value:
        return ""
    dt = datetime.strptime(value, "%Y-%m-%d")
    thai_year = dt.year + 543
    # ใช้ format ที่ส่งเข้ามา แต่แทนปีเป็น พ.ศ.
    return dt.strftime(fmt).replace(str(dt.year), str(thai_year))

# ลงทะเบียน filter ให้ Jinja ใช้งานได้
app.jinja_env.filters['thai_date'] = thai_date


def generate_ref_id(customer_id, date_val):
    """
    สร้าง Ref ID อัตโนมัติ โดยอิงจากลำดับล่าสุดของลูกค้าในวันนั้น
    รูปแบบ: <customer_id>-<ddmmyy>-<sequence>
    """

    dt = datetime.strptime(date_val, "%Y-%m-%d")
    date_str = dt.strftime("%d%m%y")  # เช่น 110926 → 11 Sep 2026

    with get_db_connection() as conn:
        # ✅ หา ref_id ล่าสุดของลูกค้าในวันนั้น
        last_ref = conn.execute(
            "SELECT ref_id FROM bill_summary WHERE customer_id=? AND date=? ORDER BY id DESC LIMIT 1",
            (customer_id, date_val)
        ).fetchone()

    if last_ref and last_ref[0]:
        # ดึง sequence จาก ref_id ล่าสุด เช่น "2-110926-3"
        try:
            last_seq = int(last_ref[0].split("-")[-1])
        except ValueError:
            last_seq = 0
        sequence = last_seq + 1
    else:
        sequence = 1

    return f"{customer_id}-{date_str}-{sequence}"



@app.route('/')
def index():
    today = date.today().strftime("%Y-%m-%d")
    start_date = today
    end_date = today

    with get_db_connection() as conn:
        # ✅ ดึงรายรับ
        incomes = conn.execute(
            "SELECT i.id, i.date, c.name as customer_name, i.activity, i.amount, i.note "
            "FROM income i LEFT JOIN customers c ON i.customer_id=c.id "
            "WHERE i.date BETWEEN ? AND ? ORDER BY i.date ASC",
            (start_date, end_date)
        ).fetchall()

        # ✅ ดึงรายจ่าย
        expenses = conn.execute(
            "SELECT * FROM expenses WHERE date BETWEEN ? AND ? ORDER BY date ASC",
            (start_date, end_date)
        ).fetchall()

        # ✅ คำนวณรวม
        total_income = sum([i['amount'] for i in incomes]) if incomes else 0
        total_expense = sum([e['amount'] for e in expenses]) if expenses else 0
        net = total_income - total_expense

        # ✅ ดึงลูกค้า
        customers = conn.execute("SELECT * FROM customers ORDER BY name ASC").fetchall()

    return render_template(
        'index.html',
        incomes=incomes,
        expenses=expenses,
        total_income=total_income,
        total_expense=total_expense,
        net=net,
        current_date=today,
        start_date=start_date,
        end_date=end_date,
        customers=customers
    )


# -----------------------------
# Add Income
# -----------------------------
@app.route("/add_income", methods=["POST"])
def add_income():
    today = date.today().strftime("%Y-%m-%d")
    customer_id = request.form.get("customer_id")
    activities = request.form.getlist("activity[]")
    amounts = request.form.getlist("amount[]")
    notes = request.form.getlist("note[]")
    shop_get = float(request.form.get("shop_get") or 0)
    date_val = request.form.get("date", today)

    total_income = sum([float(a) for a in amounts if a])
    discount = total_income - shop_get

    # ✅ สร้าง Ref ID โดยอิงจากลำดับล่าสุด
    ref_id = generate_ref_id(customer_id, date_val)

    conn = get_db_connection()

    # ✅ บันทึกสรุปบิล
    conn.execute(
        """
        INSERT INTO bill_summary (date, customer_id, total_income, shop_get, discount, ref_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (date_val, customer_id, total_income, shop_get, discount, ref_id)
    )
    bill_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    # ✅ บันทึกรายการกิจกรรม
    for activity, amount, note in zip(activities, amounts, notes):
        if activity or amount:
            conn.execute(
                """
                INSERT INTO income (bill_id, date, customer_id, activity, amount, note, ref_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (bill_id, date_val, customer_id, activity, amount, note, ref_id)
            )

    conn.commit()
    conn.close()
        # ✅ เก็บวันที่ล่าสุดไว้ใน session
    session["last_date"] = date_val

    return redirect("/report")

# -----------------------------
# Edit Income
# -----------------------------

@app.route("/edit_income/<int:bill_id>", methods=["GET", "POST"])
def edit_income(bill_id):
    conn = get_db_connection()
    if request.method == "POST":
        date_val = request.form.get("date")
        customer_id = request.form.get("customer_id")
        shop_get = float(request.form.get("shop_get") or 0)
        activities = request.form.getlist("activity[]")
        amounts = request.form.getlist("amount[]")
        notes = request.form.getlist("note[]")

        total_income = sum([float(a) for a in amounts if a])
        discount = total_income - shop_get

        # ✅ update bill_summary
        conn.execute(
            "UPDATE bill_summary SET date=?, customer_id=?, total_income=?, shop_get=?, discount=? WHERE id=?",
            (date_val, customer_id, total_income, shop_get, discount, bill_id)
        )

        # ✅ clear old incomes
        conn.execute("DELETE FROM income WHERE bill_id=?", (bill_id,))

        # ✅ insert new incomes
        for activity, amount, note in zip(activities, amounts, notes):
            if activity or amount:
                conn.execute(
                    "INSERT INTO income (bill_id, date, customer_id, activity, amount, note, ref_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (bill_id, date_val, customer_id, activity, amount, note, f"{customer_id}-{date_val}")
                )

        conn.commit()
        conn.close()
        return redirect("/report")
    else:
        bill = conn.execute("SELECT * FROM bill_summary WHERE id=?", (bill_id,)).fetchone()
        incomes = conn.execute("SELECT * FROM income WHERE bill_id=?", (bill_id,)).fetchall()
        customers = conn.execute("SELECT * FROM customers ORDER BY name ASC").fetchall()
        conn.close()
        return render_template("income/edit_income.html", bill=bill, incomes=incomes, customers=customers)


# -----------------------------
# Add Expense
# -----------------------------
@app.route('/add_expense', methods=['GET', 'POST'])
def add_expense():
    with get_db_connection() as conn:
        # ดึงราคาที่เคยใช้มาเป็นไกด์
        past_amounts = conn.execute(
            "SELECT DISTINCT amount FROM expenses ORDER BY amount ASC"
        ).fetchall()

        if request.method == 'POST':
            item = request.form['item']
            amount = request.form.get('amount')  # ✅ ใช้ช่องกรอกเองเสมอ
            note = request.form.get('note')

            conn.execute(
                "INSERT INTO expenses (date, item, amount, note) VALUES (?, ?, ?, ?)",
                (date.today().isoformat(), item, amount, note)
            )
            conn.commit()
            return redirect(url_for('index'))

    return render_template('add_expense.html', past_amounts=past_amounts)



# -----------------------------
# Delete Income
# -----------------------------
@app.route('/delete_income/<int:id>')
def delete_income(id):
    with get_db_connection() as conn:
        conn.execute("DELETE FROM income WHERE id=?", (id,))
        conn.commit()
    return redirect(url_for('index'))

# -----------------------------
# Delete Bill
# -----------------------------
@app.route('/delete_bill/<int:id>')
def delete_bill(id):
    with get_db_connection() as conn:
        # ลบกิจกรรมทั้งหมดที่อยู่ในบิลนี้
        conn.execute("DELETE FROM income WHERE bill_id=?", (id,))
        # ลบบิลออกจาก bill_summary
        conn.execute("DELETE FROM bill_summary WHERE id=?", (id,))
        conn.commit()
    return redirect(url_for('report'))



# -----------------------------
# Edit Expense
@app.route('/edit_expense/<int:id>', methods=['POST'])
def edit_expense(id):
    date_val = request.form.get('date') or date.today().isoformat()
    item = request.form.get('item') or ""
    amount = float(request.form.get('amount', 0))
    note = request.form.get('note')

    # ถ้า item ว่าง → กัน error NOT NULL
    if not item.strip():
        return redirect(url_for('report', start_date=date_val, end_date=date_val))

    with get_db_connection() as conn:
        conn.execute(
            "UPDATE expenses SET date=?, item=?, amount=?, note=? WHERE id=?",
            (date_val, item, amount, note, id)
        )
        conn.commit()

    return redirect(url_for('report', start_date=date_val, end_date=date_val))

# -----------------------------
# Delete Expense
# -----------------------------
@app.route('/delete_expense/<int:id>')
def delete_expense(id):
    with get_db_connection() as conn:
        conn.execute("DELETE FROM expenses WHERE id=?", (id,))
        conn.commit()
    return redirect(url_for('index'))


@app.route("/save_report", methods=["POST"])
def save_report():
    data = request.get_json()

    report_date = data.get("date")
    cash = data.get("cash", 0)
    transfer = data.get("transfer", 0)
    other = data.get("other", 0)
    expense = data.get("expense", 0)
    income = data.get("income", 0)
    net = data.get("net", 0)

    conn = get_db_connection()
    conn.execute("""
        INSERT INTO reports (date, cash, transfer, other, expense, income, net)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (report_date, cash, transfer, other, expense, income, net)
    )
    conn.commit()
    conn.close()

    return jsonify({"message": "บันทึกข้อมูลเรียบร้อยแล้ว!"})

@app.route('/compare_realtime')
def compare_realtime():
    with get_db_connection() as conn:
        reports = conn.execute("SELECT * FROM reports ORDER BY date DESC").fetchall()
        monthly_reports = []
        months = conn.execute("SELECT substr(date,1,7) as month FROM reports GROUP BY month ORDER BY month DESC").fetchall()
        for m in months:
            month_income = conn.execute("SELECT SUM(income) FROM reports WHERE substr(date,1,7)=?", (m['month'],)).fetchone()[0] or 0
            month_expense = conn.execute("SELECT SUM(expense) FROM reports WHERE substr(date,1,7)=?", (m['month'],)).fetchone()[0] or 0
            monthly_reports.append({
                "month": m['month'],
                "income": month_income,
                "expense": month_expense,
                "net": month_income - month_expense
            })

    return render_template('compare_realtime.html',
                           reports=reports,
                           monthly_reports=monthly_reports,
                           current_date=date.today().strftime("%Y-%m-%d"))

@app.route('/customers', methods=['GET', 'POST'])
def customers():
    with get_db_connection() as conn:
        if request.method == 'POST':
            name = request.form['name']
            phone = request.form.get('phone')
            note = request.form.get('note')
            conn.execute("INSERT INTO customers (name, phone, note) VALUES (?, ?, ?)",
                         (name, phone, note))
            conn.commit()

        customers = conn.execute("SELECT * FROM customers ORDER BY name ASC").fetchall()
    return render_template('customers.html', customers=customers)

@app.route('/edit_customer/<int:id>', methods=['GET', 'POST'])
def edit_customer(id):
    conn = get_db_connection()
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form.get('phone')
        note = request.form.get('note')
        conn.execute("UPDATE customers SET name=?, phone=?, note=? WHERE id=?",
                     (name, phone, note, id))
        conn.commit()
        conn.close()
        return redirect(url_for('customers'))
    customer = conn.execute("SELECT * FROM customers WHERE id=?", (id,)).fetchone()
    conn.close()
    return render_template('edit_customer.html', customer=customer)


@app.route('/delete_customer/<int:id>', methods=['GET'])
def delete_customer(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM customers WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('customers'))


@app.route('/report')
def report():
    today = date.today().strftime("%Y-%m-%d")

    # ✅ ใช้ start_date เป็นตัวกรองหลัก
    start_date = request.args.get('start_date', today)
    # ✅ end_date ถ้าไม่เลือก → ใช้ start_date เป็นค่าเดียวกัน
    end_date   = request.args.get('end_date', start_date)

    selected_customers = request.args.getlist('customers')

    show_income   = 'show_income' in request.args or not request.args
    show_expense  = 'show_expense' in request.args or not request.args
    show_discount = 'show_discount' in request.args or not request.args
    show_summary  = 'show_summary' in request.args or not request.args

    with get_db_connection() as conn:
        # รายรับ
        if selected_customers:
            incomes = conn.execute(
                "SELECT i.id, i.bill_id, i.date, c.name as customer_name, "
                "i.activity, i.amount, i.note, i.ref_id "
                "FROM income i LEFT JOIN customers c ON i.customer_id=c.id "
                "WHERE i.date BETWEEN ? AND ? AND c.id IN ({}) ORDER BY i.bill_id ASC".format(
                    ",".join("?"*len(selected_customers))
                ),
                [start_date, end_date] + selected_customers
            ).fetchall()
        else:
            incomes = conn.execute(
                "SELECT i.id, i.bill_id, i.date, c.name as customer_name, "
                "i.activity, i.amount, i.note, i.ref_id "
                "FROM income i LEFT JOIN customers c ON i.customer_id=c.id "
                "WHERE i.date BETWEEN ? AND ? ORDER BY i.bill_id ASC",
                (start_date, end_date)
            ).fetchall()

        # รายจ่าย
        expenses = conn.execute(
            "SELECT * FROM expenses WHERE date BETWEEN ? AND ? ORDER BY date ASC",
            (start_date, end_date)
        ).fetchall()

        # ส่วนลด
        discounts = conn.execute(
            "SELECT c.name as customer_name, SUM(b.discount) as total_discount "
            "FROM bill_summary b LEFT JOIN customers c ON b.customer_id=c.id "
            "WHERE b.date BETWEEN ? AND ? GROUP BY c.name",
            (start_date, end_date)
        ).fetchall()

        # สรุปบิล
        bills = conn.execute(
            "SELECT b.id, b.date, c.name AS customer_name, "
            "b.total_income, b.shop_get, b.discount, b.ref_id "
            "FROM bill_summary b LEFT JOIN customers c ON b.customer_id=c.id "
            "WHERE b.date BETWEEN ? AND ? ORDER BY b.id ASC",
            (start_date, end_date)
        ).fetchall()

        customers = conn.execute("SELECT * FROM customers ORDER BY name ASC").fetchall()

    return render_template(
        'index.html',
        incomes=incomes,
        expenses=expenses,
        discounts=discounts,
        bills=bills,
        customers=customers,
        start_date=start_date,
        end_date=end_date,
        selected_customers=selected_customers,
        show_income=show_income,
        show_expense=show_expense,
        show_discount=show_discount,
        show_summary=show_summary,
        current_date=start_date   # ✅ ใช้ start_date เป็นค่า default
    )


@app.route("/monthly_report")
def monthly_report():
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT strftime('%Y-%m', date) AS month,
               SUM(amount) AS total_income
        FROM income
        GROUP BY month
    """).fetchall()

    # ตัวอย่างสำหรับรายจ่าย
    expenses = conn.execute("""
        SELECT strftime('%Y-%m', date) AS month,
               SUM(amount) AS total_expense
        FROM expenses
        GROUP BY month
    """).fetchall()

    labels = [row["month"] for row in rows]
    income_data = [row["total_income"] for row in rows]
    expense_data = [row["total_expense"] for row in expenses]

    conn.close()
    return render_template("monthly_report.html",
                           labels=labels,
                           income_data=income_data,
                           expense_data=expense_data)





if __name__ == '__main__':
    app.run(debug=True)
