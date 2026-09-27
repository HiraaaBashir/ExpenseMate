import sqlite3

DB_NAME = 'expensemate.db'

def get_connection():
    """Create and return a new SQLite connection with foreign keys enabled.

    Returns:
    A sqlite3.Connection with foreign keys enabled and row_factory set to
    sqlite3.Row, so query results can be accessed by column name (e.g., row['amount']).
    """
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn