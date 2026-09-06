from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import date, datetime


app = Flask(__name__)

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


@app.route('/')
def index():
    today = date.today().strftime("%Y-%m-%d")
    start_date = today
    end_date = today

    with get_db_connection() as conn:
        incomes = conn.execute(
            "SELECT i.id, i.date, c.name as customer_name, i.source, i.amount, i.note "
            "FROM income i LEFT JOIN customers c ON i.customer_id=c.id "
            "WHERE i.date BETWEEN ? AND ? ORDER BY i.date ASC",
            (start_date, end_date)
        ).fetchall()

        expenses = conn.execute(
            "SELECT * FROM expenses WHERE date BETWEEN ? AND ? ORDER BY date ASC",
            (start_date, end_date)
        ).fetchall()

        total_income = sum([i['amount'] for i in incomes]) if incomes else 0
        total_expense = sum([e['amount'] for e in expenses]) if expenses else 0
        net = total_income - total_expense

        customers = conn.execute("SELECT * FROM customers ORDER BY name ASC").fetchall()

    return render_template('index.html',
                           incomes=incomes,
                           expenses=expenses,
                           total_income=total_income,
                           total_expense=total_expense,
                           net=net,
                           current_date=today,
                           start_date=start_date,
                           end_date=end_date,
                           customers=customers)

# -----------------------------
# Add Income
# -----------------------------
@app.route("/add_income", methods=["POST"])
def add_income():
    today = date.today().strftime("%Y-%m-%d")

    customer_id = request.form.get("customer_id")
    activities = request.form.getlist("activity[]")
    amounts = request.form.getlist("amount[]")
    shop_get = request.form.get("shop_get")
    date_val = request.form.get("date", today)
    note = request.form.get("note")

    # คำนวณส่วนลด (ผลตอบแทนลูกค้า)
    total = sum([float(a) for a in amounts if a])
    discount = float(total) - float(shop_get or 0)

    conn = get_db_connection()
    for activity, amount in zip(activities, amounts):
        if activity or amount:  # บันทึกเฉพาะแถวที่มีข้อมูล
            conn.execute(
                """
                INSERT INTO income (date, customer_id, activity, amount, shop_get, discount, note)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (date_val, customer_id, activity, amount, shop_get, discount, note)
            )
    conn.commit()
    conn.close()

    return redirect("/report")


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
# Edit Income
# -----------------------------
@app.route('/edit_income/<int:id>', methods=['GET', 'POST'])
def edit_income(id):
    with get_db_connection() as conn:
        income = conn.execute("SELECT * FROM income WHERE id=?", (id,)).fetchone()
        customers = conn.execute("SELECT * FROM customers ORDER BY name ASC").fetchall()

        if request.method == 'POST':
            date_val = request.form['date']
            source = request.form['source']
            amount = float(request.form['amount'])
            note = request.form.get('note')
            customer_id = request.form.get('customer_id')

            conn.execute(
                "UPDATE income SET date=?, source=?, amount=?, note=?, customer_id=? WHERE id=?",
                (date_val, source, amount, note, customer_id, id)
            )
            conn.commit()

            # ✅ redirect กลับไปที่ช่วงวันที่ที่แก้ไข
            return redirect(url_for('report', start_date=date_val, end_date=date_val))

    return render_template('edit_income.html', income=income, customers=customers)


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
    start_date = request.args.get('start_date', today)
    end_date = request.args.get('end_date', today)

    with get_db_connection() as conn:
        incomes = conn.execute(
            "SELECT i.id, i.date, c.name as customer_name, i.source, i.amount, i.note "
            "FROM income i LEFT JOIN customers c ON i.customer_id=c.id "
            "WHERE i.date BETWEEN ? AND ? ORDER BY i.date ASC",
            (start_date, end_date)
        ).fetchall()

        expenses = conn.execute(
            "SELECT * FROM expenses WHERE date BETWEEN ? AND ? ORDER BY date ASC",
            (start_date, end_date)
        ).fetchall()

        # ✅ คำนวณรวมตามช่วงเวลา
        total_income = sum([i['amount'] for i in incomes]) if incomes else 0
        total_expense = sum([e['amount'] for e in expenses]) if expenses else 0
        net = total_income - total_expense

        customers = conn.execute("SELECT * FROM customers ORDER BY name ASC").fetchall()

    return render_template('index.html',
                           incomes=incomes,
                           expenses=expenses,
                           total_income=total_income,
                           total_expense=total_expense,
                           net=net,   # ✅ ส่งค่า net เข้าไป
                           current_date=today,
                           start_date=start_date,
                           end_date=end_date,
                           customers=customers)


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
