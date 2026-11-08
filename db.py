import sqlite3
from contextlib import contextmanager

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


@contextmanager
def connection(commit=False):
    """Yield a connection that is ALWAYS closed, even if the query raises.

    Parameters:
        commit: If True, commit when the block finishes without an error.
            If the block raises, the transaction is rolled back instead.

    Usage:
        with connection(commit=True) as conn:
            conn.execute("INSERT ...", params)
    """
    conn = get_connection()
    try:
        yield conn
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()