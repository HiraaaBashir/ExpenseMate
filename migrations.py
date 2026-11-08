"""
Versioned schema migrations for ExpenseMate (Assignment 02, Part A).

Why this exists
---------------
In Assignment 01 the database schema was written out three separate times
(schema.py, main.py, conftest.py) and the copies had drifted apart:
budgets.limit_amount was INTEGER in the app database but REAL in the test
database, while models.Budget declares it as a float.  There was also no record
of which schema version a given expensemate.db file was on.

This module is now the single source of truth for the schema.  The version of
a database is stored inside the database file itself using SQLite's
``PRAGMA user_version`` and each migration runs at most once, in order,
inside a transaction (all-or-nothing).

Versions
--------
  0  no version recorded (a fresh file, or an Assignment 01 database)
  1  baseline schema = the Assignment 01 schema, created with IF NOT EXISTS so
     it is a no-op on an existing Assignment 01 database
  2  budgets.limit_amount INTEGER -> REAL (existing rows copied across)

Usage
-----
    from migrations import migrate
    migrate()                      # upgrade the database named in db.DB_NAME

    python migrations.py           # same, from the command line
    python migrations.py --status  # show current version, change nothing
"""
import os
import sqlite3
import sys

import db


class MigrationError(Exception):
    """Raised when a migration fails; the database is left at its previous version."""
    pass


# --------------------------------------------------------------------------- #
# Individual migrations.  Each receives a connection that is already inside a
# transaction and must not commit or roll back itself.
# --------------------------------------------------------------------------- #

def _m001_baseline_schema(conn):
    """Create the Assignment 01 tables if they are not there yet."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS categories(
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name TEXT UNIQUE NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions(
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL CHECK (amount > 0),
            type TEXT NOT NULL CHECK (type IN ('income', 'expense')),
            date TEXT NOT NULL,
            category_id INTEGER NOT NULL REFERENCES categories(category_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS budgets(
            budget_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL REFERENCES categories(category_id),
            month TEXT NOT NULL,
            limit_amount INTEGER NOT NULL CHECK (limit_amount > 0),
            UNIQUE (category_id, month)
        )
    """)


def _m002_budget_limit_to_real(conn):
    """Rebuild budgets so limit_amount is declared REAL instead of INTEGER.

    SQLite cannot change a column type with ALTER TABLE, so the standard
    "create new, copy, drop old, rename" procedure is used.  The AUTOINCREMENT
    counter is carried over so ids of deleted budgets are never reused.
    """
    row = conn.execute("SELECT seq FROM sqlite_sequence WHERE name = 'budgets'").fetchone()
    old_seq = row[0] if row else None

    conn.execute("""
        CREATE TABLE budgets_new(
            budget_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL REFERENCES categories(category_id),
            month TEXT NOT NULL,
            limit_amount REAL NOT NULL CHECK (limit_amount > 0),
            UNIQUE (category_id, month)
        )
    """)
    conn.execute("""
        INSERT INTO budgets_new (budget_id, category_id, month, limit_amount)
        SELECT budget_id, category_id, month, limit_amount FROM budgets
    """)
    conn.execute("DROP TABLE budgets")
    conn.execute("ALTER TABLE budgets_new RENAME TO budgets")

    if old_seq is not None:
        conn.execute("UPDATE sqlite_sequence SET seq = ? WHERE name = 'budgets'", (old_seq,))

    problems = conn.execute("PRAGMA foreign_key_check").fetchall()
    if problems:
        raise MigrationError(f"Foreign key check failed after rebuilding budgets: {problems}")


# (target_version, description, function) - append new migrations at the end only.
MIGRATIONS = [
    (1, "baseline schema (Assignment 01)", _m001_baseline_schema),
    (2, "budgets.limit_amount INTEGER -> REAL", _m002_budget_limit_to_real),
]
LATEST_VERSION = MIGRATIONS[-1][0]


# --------------------------------------------------------------------------- #
# Runner
# --------------------------------------------------------------------------- #

def get_version(conn):
    """Return the schema version stored in the database (0 if none recorded)."""
    return conn.execute("PRAGMA user_version").fetchone()[0]


def _has_user_tables(conn):
    row = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    ).fetchone()
    return row[0] > 0


def backup_database(conn, version):
    """Copy the database to '<name>.bak-v<version>' using SQLite's online backup API.

    Returns the backup path.  An existing backup for the same version is kept
    and a numeric suffix is added, so a backup is never overwritten.
    """
    base = f"{db.DB_NAME}.bak-v{version}"
    path, n = base, 1
    while os.path.exists(path):
        n += 1
        path = f"{base}-{n}"
    target = sqlite3.connect(path)
    try:
        conn.backup(target)
    finally:
        target.close()
    return path


def migrate(backup=True, log=print):
    """Upgrade the database in db.DB_NAME to LATEST_VERSION.

    Parameters:
        backup: If True and an existing database needs upgrading, a copy is
            saved first (see backup_database).
        log: Callable used for progress messages; pass ``lambda *_: None`` to silence.

    Returns:
        A dict: {'from_version': int, 'to_version': int, 'applied': [versions], 'backup': path or None}

    Raises:
        MigrationError: If a migration fails.  Everything done by the failing
        migration is rolled back and the version number is not advanced.
    """
    conn = db.get_connection()
    conn.isolation_level = None  # we issue BEGIN/COMMIT ourselves
    start = get_version(conn)
    result = {'from_version': start, 'to_version': start, 'applied': [], 'backup': None}
    try:
        if start > LATEST_VERSION:
            raise MigrationError(
                f"Database is at version {start} but this code only knows up to {LATEST_VERSION}.")

        pending = [m for m in MIGRATIONS if m[0] > start]
        if not pending:
            log(f"Database already at version {start}; nothing to do.")
            return result

        if backup and _has_user_tables(conn):
            result['backup'] = backup_database(conn, start)
            log(f"Backup written to {result['backup']}")

        for version, description, fn in pending:
            log(f"Applying v{version}: {description} ...")
            conn.execute("BEGIN")
            try:
                fn(conn)
                conn.execute(f"PRAGMA user_version = {int(version)}")
                conn.execute("COMMIT")
            except Exception as exc:
                conn.execute("ROLLBACK")
                raise MigrationError(f"Migration v{version} failed and was rolled back: {exc}") from exc
            result['applied'].append(version)
            result['to_version'] = version
        log(f"Database upgraded from v{start} to v{result['to_version']}.")
        return result
    finally:
        conn.close()


if __name__ == "__main__":
    if "--status" in sys.argv:
        c = db.get_connection()
        print(f"{db.DB_NAME}: schema version {get_version(c)} (latest is {LATEST_VERSION})")
        c.close()
    else:
        migrate()
