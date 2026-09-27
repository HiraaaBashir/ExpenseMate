
import sqlite3
import pytest

import db
from ui import ExpenseMateUI
from tkinter import messagebox


def _create_schema():
    """Create the three tables fresh in whatever DB db.DB_NAME points to."""
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE categories(
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name TEXT UNIQUE NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE transactions(
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL CHECK (amount > 0),
            type TEXT NOT NULL CHECK (type IN ('income', 'expense')),
            date TEXT NOT NULL,
            category_id INTEGER NOT NULL REFERENCES categories(category_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE budgets(
            budget_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL REFERENCES categories(category_id),
            month TEXT NOT NULL,
            limit_amount INTEGER NOT NULL CHECK (limit_amount > 0),
            UNIQUE (category_id, month)
        )
    """)
    conn.commit()
    conn.close()


@pytest.fixture
def app(tmp_path, monkeypatch):
    """A real ExpenseMateUI wired to a throwaway SQLite file, auto-closed after the test."""
    test_db = str(tmp_path / "test_expensemate.db")
    monkeypatch.setattr(db, "DB_NAME", test_db)
    _create_schema()

    ui = ExpenseMateUI()
    yield ui
    ui.destroy()


@pytest.fixture
def no_dialogs(monkeypatch):
    """Replace the three messagebox popups with fakes that just record what they were called with."""
    calls = {"error": [], "info": [], "warning": []}
    monkeypatch.setattr(messagebox, "showerror", lambda title, msg: calls["error"].append(msg))
    monkeypatch.setattr(messagebox, "showinfo", lambda title, msg: calls["info"].append(msg))
    monkeypatch.setattr(messagebox, "showwarning", lambda title, msg: calls["warning"].append(msg))
    return calls


# ---------------------------------------------------------------
# Categories
# ---------------------------------------------------------------

def test_add_category_appears_in_tree(app, no_dialogs):
    app.category_name_var.set("Food")
    app.add_category()

    names = [app.category_tree.item(i)["values"][1] for i in app.category_tree.get_children()]
    assert names == ["Food"]
    assert app.category_name_var.get() == ""          # field cleared after success
    assert no_dialogs["error"] == []                  # no error shown


def test_add_category_blank_name_shows_error_and_adds_nothing(app, no_dialogs):
    app.category_name_var.set("   ")
    app.add_category()

    assert app.category_tree.get_children() == ()
    assert len(no_dialogs["error"]) == 1


def test_add_category_updates_dropdowns(app, no_dialogs):
    """New categories should immediately be selectable when adding a transaction or budget."""
    app.category_name_var.set("Rent")
    app.add_category()

    assert "Rent" in app.transaction_category_combo["values"]
    assert "Rent" in app.budget_category_combo["values"]


def test_delete_category_removes_it(app, no_dialogs):
    app.category_name_var.set("Utilities")
    app.add_category()
    row_id = app.category_tree.get_children()[0]
    app.category_tree.selection_set(row_id)

    app.delete_category()

    assert app.category_tree.get_children() == ()


def test_delete_category_in_use_shows_friendly_error(app, no_dialogs):
    """Deleting a category that still has a transaction should not crash the UI - it should
    show the friendly message defined in delete_category, not the raw DB error."""
    app.category_name_var.set("Food")
    app.add_category()
    row_id = app.category_tree.get_children()[0]
    category_id = app.category_tree.item(row_id)["values"][0]

    app.transaction_service.add_transaction(amount=10, type="expense", date="2026-09-01",
                                             category_id=category_id)

    app.category_tree.selection_set(row_id)
    app.delete_category()

    assert app.category_tree.get_children()  # still there, delete was blocked
    assert "can't be deleted" in no_dialogs["error"][0]


# ---------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------

def test_add_transaction_without_category_shows_error(app, no_dialogs):
    app.transaction_category_var.set("Nope")   # not a real category
    app.amount_var.set("100")
    app.add_transaction()

    assert app.transaction_tree.get_children() == ()
    assert len(no_dialogs["error"]) == 1


def test_add_transaction_non_numeric_amount_shows_error(app, no_dialogs):
    app.category_name_var.set("Food")
    app.add_category()
    app.transaction_category_var.set("Food")
    app.amount_var.set("abc")

    app.add_transaction()

    assert app.transaction_tree.get_children() == ()
    assert "must be a number" in no_dialogs["error"][0]


def test_add_transaction_success_appears_in_tree_and_clears_amount(app, no_dialogs):
    app.category_name_var.set("Food")
    app.add_category()
    app.transaction_category_var.set("Food")
    app.amount_var.set("250")
    app.type_var.set("expense")
    app.date_var.set("2026-09-15")

    app.add_transaction()

    rows = app.transaction_tree.get_children()
    assert len(rows) == 1
    values = app.transaction_tree.item(rows[0])["values"]
    assert values[2] == "expense"
    assert values[3] == "Food"
    assert app.amount_var.get() == ""


def test_add_transaction_triggers_budget_alert_over_80_percent(app, no_dialogs):
    app.category_name_var.set("Food")
    app.add_category()
    category_id = app.category_map["Food"]
    app.budget_service.set_budget(category_id, "2026-09", 100)

    app.transaction_category_var.set("Food")
    app.amount_var.set("85")
    app.date_var.set("2026-09-10")
    app.add_transaction()

    assert len(no_dialogs["warning"]) == 1
    assert "80" in no_dialogs["warning"][0] or "85" in no_dialogs["warning"][0]


def test_delete_transaction_removes_row(app, no_dialogs):
    app.category_name_var.set("Food")
    app.add_category()
    app.transaction_category_var.set("Food")
    app.amount_var.set("50")
    app.add_transaction()
    row_id = app.transaction_tree.get_children()[0]
    app.transaction_tree.selection_set(row_id)

    app.delete_transaction()

    assert app.transaction_tree.get_children() == ()


def test_delete_transaction_with_nothing_selected_is_a_no_op(app, no_dialogs):
    """Clicking delete with no row selected should do nothing, not raise."""
    app.delete_transaction()
    assert no_dialogs["error"] == []


# ---------------------------------------------------------------
# Budgets
# ---------------------------------------------------------------

def test_set_budget_without_category_shows_error(app, no_dialogs):
    app.budget_category_var.set("Nope")
    app.budget_limit_var.set("500")

    app.set_budget()

    assert app.budget_tree.get_children() == ()
    assert len(no_dialogs["error"]) == 1


def test_set_budget_non_numeric_limit_shows_error(app, no_dialogs):
    app.category_name_var.set("Food")
    app.add_category()
    app.budget_category_var.set("Food")
    app.budget_limit_var.set("not-a-number")

    app.set_budget()

    assert app.budget_tree.get_children() == ()
    assert "must be a number" in no_dialogs["error"][0]


def test_set_budget_success_appears_in_tree(app, no_dialogs):
    app.category_name_var.set("Food")
    app.add_category()
    app.budget_category_var.set("Food")
    app.budget_month_var.set("2026-09")
    app.budget_limit_var.set("500")

    app.set_budget()

    rows = app.budget_tree.get_children()
    assert len(rows) == 1
    values = app.budget_tree.item(rows[0])["values"]
    assert values[1] == "Food"
    assert values[3] == "500.00"
    assert app.budget_limit_var.get() == ""


def test_set_duplicate_budget_shows_error(app, no_dialogs):
    app.category_name_var.set("Food")
    app.add_category()
    app.budget_category_var.set("Food")
    app.budget_month_var.set("2026-09")
    app.budget_limit_var.set("500")
    app.set_budget()

    app.budget_limit_var.set("700")
    app.set_budget()

    assert len(app.budget_tree.get_children()) == 1     # second attempt was rejected
    assert len(no_dialogs["error"]) == 1


# ---------------------------------------------------------------
# Budget pulse indicator (the emoji + % shown under the transaction form)
# ---------------------------------------------------------------

def test_budget_pulse_green_under_80_percent(app, no_dialogs):
    app.category_name_var.set("Food")
    app.add_category()
    category_id = app.category_map["Food"]
    app.budget_service.set_budget(category_id, "2026-09", 100)

    app._show_budget_pulse(category_id, "2026-09")

    assert "\U0001F7E2" in app.budget_pulse.cget("text")  # green circle, spend is 0%


def test_budget_pulse_red_at_or_over_100_percent(app, no_dialogs):
    app.category_name_var.set("Food")
    app.add_category()
    category_id = app.category_map["Food"]
    app.budget_service.set_budget(category_id, "2026-09", 100)
    app.transaction_service.add_transaction(amount=120, type="expense", date="2026-09-05",
                                             category_id=category_id)

    app._show_budget_pulse(category_id, "2026-09")

    assert "\U0001F534" in app.budget_pulse.cget("text")


def test_budget_pulse_blank_when_no_budget_set(app, no_dialogs):
    app.category_name_var.set("Food")
    app.add_category()
    category_id = app.category_map["Food"]

    app._show_budget_pulse(category_id, "2026-09")

    assert app.budget_pulse.cget("text") == ""