"""Tests for migrations.py (Assignment 02, Part A)."""
import os
import sqlite3
import pytest

import db
import migrations
from migrations import migrate, get_version, MigrationError, LATEST_VERSION

SILENT = lambda *_: None

# The exact schema Assignment 01 created (budgets.limit_amount is INTEGER, no version).
LEGACY_DDL = [
    """CREATE TABLE categories(category_id INTEGER PRIMARY KEY AUTOINCREMENT, category_name TEXT UNIQUE NOT NULL)""",
    """CREATE TABLE transactions(transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL NOT NULL CHECK (amount > 0), type TEXT NOT NULL CHECK (type IN ('income', 'expense')),
        date TEXT NOT NULL, category_id INTEGER NOT NULL REFERENCES categories(category_id))""",
    """CREATE TABLE budgets(budget_id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id INTEGER NOT NULL REFERENCES categories(category_id), month TEXT NOT NULL,
        limit_amount INTEGER NOT NULL CHECK (limit_amount > 0), UNIQUE (category_id, month))""",
]


@pytest.fixture
def dbfile(tmp_path):
    """Point db.DB_NAME at an empty temp file for the duration of a test."""
    old = db.DB_NAME
    db.DB_NAME = str(tmp_path / "mig_test.db")
    yield db.DB_NAME
    db.DB_NAME = old


def make_legacy_db():
    """Create an Assignment 01 database with sample records; returns nothing."""
    conn = db.get_connection()
    for ddl in LEGACY_DDL:
        conn.execute(ddl)
    conn.executemany("INSERT INTO categories (category_name) VALUES (?)", [("Food",), ("Rent",), ("Fun",)])
    conn.executemany("INSERT INTO transactions (amount, type, date, category_id) VALUES (?,?,?,?)",
                     [(120.5, 'expense', '2026-09-03', 1), (5000, 'income', '2026-09-01', 2),
                      (80, 'expense', '2026-09-10', 3)])
    conn.executemany("INSERT INTO budgets (category_id, month, limit_amount) VALUES (?,?,?)",
                     [(1, '2026-09', 250), (2, '2026-09', 1000), (3, '2026-09', 560)])
    conn.commit()
    conn.close()


def column_type(conn, table, column):
    return {r[1]: r[2] for r in conn.execute(f"PRAGMA table_info({table})")}[column]


def test_fresh_database_reaches_latest_version(dbfile):
    result = migrate(log=SILENT)
    conn = db.get_connection()
    assert get_version(conn) == LATEST_VERSION
    assert result['applied'] == [1, 2]
    assert result['backup'] is None  # nothing to back up for a brand-new file
    assert column_type(conn, 'budgets', 'limit_amount') == 'REAL'
    conn.close()


def test_legacy_database_is_upgraded_and_records_preserved(dbfile):
    make_legacy_db()
    conn = db.get_connection()
    before = conn.execute("SELECT budget_id, category_id, month, limit_amount FROM budgets ORDER BY budget_id").fetchall()
    before_tx = conn.execute("SELECT * FROM transactions ORDER BY transaction_id").fetchall()
    before_cat = conn.execute("SELECT * FROM categories ORDER BY category_id").fetchall()
    assert get_version(conn) == 0 and column_type(conn, 'budgets', 'limit_amount') == 'INTEGER'
    conn.close()

    migrate(log=SILENT)

    conn = db.get_connection()
    assert get_version(conn) == LATEST_VERSION
    assert column_type(conn, 'budgets', 'limit_amount') == 'REAL'
    after = conn.execute("SELECT budget_id, category_id, month, limit_amount FROM budgets ORDER BY budget_id").fetchall()
    assert [tuple(r) for r in after] == [tuple(r) for r in before]            # same ids, months and limits
    assert [tuple(r) for r in conn.execute("SELECT * FROM transactions ORDER BY transaction_id")] == [tuple(r) for r in before_tx]
    assert [tuple(r) for r in conn.execute("SELECT * FROM categories ORDER BY category_id")] == [tuple(r) for r in before_cat]
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    conn.close()


def test_migration_is_idempotent(dbfile):
    make_legacy_db()
    migrate(log=SILENT)
    second = migrate(log=SILENT)
    assert second['applied'] == []
    assert second['backup'] is None


def test_backup_contains_pre_migration_data(dbfile):
    make_legacy_db()
    result = migrate(log=SILENT)
    assert result['backup'] and os.path.exists(result['backup'])
    b = sqlite3.connect(result['backup'])
    assert b.execute("PRAGMA user_version").fetchone()[0] == 0
    assert column_type(b, 'budgets', 'limit_amount') == 'INTEGER'
    assert b.execute("SELECT COUNT(*) FROM budgets").fetchone()[0] == 3
    b.close()


def test_fractional_limit_stored_as_real_after_migration(dbfile):
    make_legacy_db()
    migrate(log=SILENT)
    conn = db.get_connection()
    conn.execute("INSERT INTO budgets (category_id, month, limit_amount) VALUES (1, '2026-10', 99.5)")
    row = conn.execute("SELECT limit_amount, typeof(limit_amount) FROM budgets WHERE month = '2026-10'").fetchone()
    assert (row[0], row[1]) == (99.5, 'real')
    conn.close()


def test_constraints_survive_rebuild(dbfile):
    make_legacy_db()
    migrate(log=SILENT)
    conn = db.get_connection()
    with pytest.raises(sqlite3.IntegrityError):   # UNIQUE (category_id, month)
        conn.execute("INSERT INTO budgets (category_id, month, limit_amount) VALUES (1, '2026-09', 10)")
    with pytest.raises(sqlite3.IntegrityError):   # CHECK (limit_amount > 0)
        conn.execute("INSERT INTO budgets (category_id, month, limit_amount) VALUES (1, '2026-11', 0)")
    with pytest.raises(sqlite3.IntegrityError):   # FOREIGN KEY
        conn.execute("INSERT INTO budgets (category_id, month, limit_amount) VALUES (999, '2026-11', 10)")
    conn.close()


def test_autoincrement_counter_not_reset_by_rebuild(dbfile):
    """If the newest budget was deleted before migrating, its id must not be handed out again."""
    make_legacy_db()
    conn = db.get_connection()
    conn.execute("DELETE FROM budgets WHERE budget_id = 3")   # highest id removed; counter stays at 3
    conn.commit()
    conn.close()
    migrate(log=SILENT)
    conn = db.get_connection()
    cur = conn.execute("INSERT INTO budgets (category_id, month, limit_amount) VALUES (3, '2026-10', 70)")
    assert cur.lastrowid == 4
    conn.close()


def test_failed_migration_rolls_back_and_keeps_version(dbfile, monkeypatch):
    make_legacy_db()

    def broken(conn):
        conn.execute("DROP TABLE budgets")          # destructive step...
        raise RuntimeError("simulated failure")     # ...then the migration blows up

    monkeypatch.setattr(migrations, "MIGRATIONS", migrations.MIGRATIONS[:1] + [(2, "broken", broken)])
    with pytest.raises(MigrationError):
        migrate(log=SILENT)

    conn = db.get_connection()
    assert get_version(conn) == 1                                          # v1 applied, v2 not
    assert conn.execute("SELECT COUNT(*) FROM budgets").fetchone()[0] == 3  # DROP was rolled back
    conn.close()


def test_database_newer_than_code_is_refused(dbfile):
    conn = db.get_connection()
    conn.execute(f"PRAGMA user_version = {LATEST_VERSION + 5}")
    conn.close()
    with pytest.raises(MigrationError):
        migrate(log=SILENT)
