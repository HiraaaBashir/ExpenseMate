"""
Entry point for ExpenseMate.

Brings the database up to the latest schema version (creating it if it does not
exist yet, or migrating an older database in place), then opens the UI.
"""
from migrations import migrate
from ui import ExpenseMateUI


def ensure_schema():
    """Bring the database up to the latest schema version (see migrations.py)."""
    migrate()


if __name__ == "__main__":
    ensure_schema()
    app = ExpenseMateUI()
    app.mainloop()