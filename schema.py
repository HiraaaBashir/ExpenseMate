"""
Kept for backward compatibility with Assignment 01.

The schema now lives in migrations.py (single source of truth). Running this
file simply upgrades expensemate.db to the latest schema version.
"""
from migrations import migrate

if __name__ == "__main__":
    migrate()
