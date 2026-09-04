from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import date

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    today = date.today().strftime("%Y-%m-%d")
    current_month = date.today().strftime("%Y-%m")

    with get_db_connection() as conn:
        incomes = conn.execute("""
            SELECT income.id, income.date, income.source, income.amount, income.note,
                   customers.name as customer_name
            FROM income
            LEFT JOIN customers ON income.customer_id = customers.id
            ORDER BY income.date DESC
        """).fetchall()

        expenses = conn.execute("SELECT * FROM expenses ORDER BY date DESC").fetchall()
        customers = conn.execute("SELECT * FROM customers ORDER BY name ASC").fetchall()

        # รายวัน
        today_income = conn.execute("SELECT SUM(amount) FROM income WHERE date=?", (today,)).fetchone()[0] or 0
        today_expense = conn.execute("SELECT SUM(amount) FROM expenses WHERE date=?", (today,)).fetchone()[0] or 0
        today_net = today_income - today_expense

        # แยกเงินสด/เงินโอน
        cash_income = conn.execute("SELECT SUM(amount) FROM income WHERE date=? AND source='เงินสด'", (today,)).fetchone()[0] or 0
        transfer_income = conn.execute("SELECT SUM(amount) FROM income WHERE date=? AND source='เงินโอน'", (today,)).fetchone()[0] or 0
        total_inflow = cash_income + transfer_income
        remaining_after_expense = total_inflow - today_expense

        # รายเดือน
        monthly_income = conn.execute("SELECT SUM(amount) FROM income WHERE substr(date,1,7)=?", (current_month,)).fetchone()[0] or 0
        monthly_expense = conn.execute("SELECT SUM(amount) FROM expenses WHERE substr(date,1,7)=?", (current_month,)).fetchone()[0] or 0
        monthly_net = monthly_income - monthly_expense

    return render_template('index.html',
                           incomes=incomes,
                           expenses=expenses,
                           customers=customers,
                           current_date=today,
                           today_income=today_income,
                           today_expense=today_expense,
                           today_net=today_net,
                           cash_income=cash_income,
                           transfer_income=transfer_income,
                           total_inflow=total_inflow,
                           remaining_after_expense=remaining_after_expense,
                           monthly_income=monthly_income,
                           monthly_expense=monthly_expense,
                           monthly_net=monthly_net)



@app.route('/add_income', methods=['POST'])
def add_income():
    date_val = request.form['date']
    source = request.form['source']
    amount = float(request.form['amount'])
    note = request.form.get('note')
    customer_id = request.form.get('customer_id')

    with get_db_connection() as conn:
        conn.execute("INSERT INTO income (date, source, amount, note, customer_id) VALUES (?, ?, ?, ?, ?)",
                     (date_val, source, amount, note, customer_id))
        conn.commit()
    return redirect(url_for('index'))

@app.route('/add_expense', methods=['POST'])
def add_expense():
    date_val = request.form['date']
    item = request.form['item']
    amount = float(request.form['amount'])
    note = request.form.get('note')

    with get_db_connection() as conn:
        conn.execute("INSERT INTO expenses (date, item, amount, note) VALUES (?, ?, ?, ?)",
                     (date_val, item, amount, note))
        conn.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
