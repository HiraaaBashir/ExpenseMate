"""
Entry point for ExpenseMate.

Creates the database tables if they don't exist yet (using IF NOT EXISTS,
so it's safe to run even if schema.py already set them up once), then
opens the UI.
"""
from db import get_connection
from ui import ExpenseMateUI


def ensure_schema():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories(
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name TEXT UNIQUE NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions(
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL CHECK (amount > 0),
            type TEXT NOT NULL CHECK (type IN ('income', 'expense')),
            date TEXT NOT NULL,
            category_id INTEGER NOT NULL REFERENCES categories(category_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS budgets(
            budget_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL REFERENCES categories(category_id),
            month TEXT NOT NULL,
            limit_amount INTEGER NOT NULL CHECK (limit_amount > 0),
            UNIQUE (category_id, month)
        )
    """)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    ensure_schema()
    app = ExpenseMateUI()
    app.mainloop()