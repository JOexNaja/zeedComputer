from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import date

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS income (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            source TEXT NOT NULL,
            amount REAL NOT NULL,
            note TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            item TEXT NOT NULL,
            amount REAL NOT NULL,
            note TEXT
        )''')
        conn.commit()

@app.route('/')
def index():
    today = date.today().strftime("%Y-%m-%d")
    with get_db_connection() as conn:
        incomes = conn.execute("SELECT * FROM income ORDER BY date DESC").fetchall()
        expenses = conn.execute("SELECT * FROM expenses ORDER BY date DESC").fetchall()
    return render_template('index.html', incomes=incomes, expenses=expenses, current_date=today)

@app.route('/add_income', methods=['POST'])
def add_income():
    date_val = request.form.get('date')
    source = request.form.get('source')
    amount = request.form.get('amount')
    note = request.form.get('note')
    with get_db_connection() as conn:
        conn.execute("INSERT INTO income (date, source, amount, note) VALUES (?, ?, ?, ?)",
                     (date_val, source, amount, note))
        conn.commit()
    return redirect(url_for('index'))

@app.route('/add_expense', methods=['POST'])
def add_expense():
    date_val = request.form.get('date')
    item = request.form.get('item')
    amount = request.form.get('amount')
    note = request.form.get('note')
    with get_db_connection() as conn:
        conn.execute("INSERT INTO expenses (date, item, amount, note) VALUES (?, ?, ?, ?)",
                     (date_val, item, amount, note))
        conn.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
