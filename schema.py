import sqlite3
conn = sqlite3.connect('expensemate.db')
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS categories(
        category_id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_name TEXT UNIQUE NOT NULL
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions
    (
        transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL NOT NULL CHECK (amount > 0),
        type TEXT NOT NULL CHECK (type IN ('income', 'expense')),
        date TEXT NOT NULL,
        category_id INTEGER NOT NULL REFERENCES categories(category_id)
    )
""")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS budgets
    (
        budget_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id  INTEGER NOT NULL REFERENCES categories(category_id),
        month        TEXT    NOT NULL,
        limit_amount INTEGER NOT NULL CHECK (limit_amount > 0),
        UNIQUE (category_id, month)
    )
""")
conn.commit()