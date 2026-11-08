"""Integration / system tests: whole workflows through Controller -> Service -> Repository -> Database."""
import sqlite3

import pytest

import db
from analytics_controller import AnalyticsController
from budget_service import BudgetService
from exceptions import ValidationError
from migrations import get_version, migrate
from transaction_controller import TransactionController


@pytest.fixture
def app(services):
    """The real layers wired together on a fresh test database (schema comes from migrations)."""
    services['tx_controller'] = TransactionController(
        services['transaction_service'], services['category_service'])
    services['analytics_controller'] = AnalyticsController()
    return services


def test_it1_add_expense_through_controller_triggers_budget_alert_at_80_percent(app):
    app['budget_service'].set_budget(app['category_id'], '2026-09', 1000)
    first = app['tx_controller'].add_transaction('700', 'expense', '2026-09-10', 'Food')
    second = app['tx_controller'].add_transaction('150', 'expense', '2026-09-11', 'Food')
    assert first['alert_triggered'] is False
    assert second['alert_triggered'] is True
    assert second['percent_spent'] == pytest.approx(85.0)


def test_it2_csv_import_then_monthly_report_matches(app, tmp_path):
    travel = app['category_service'].add_category('Travel')
    csv_file = tmp_path / "sept.csv"
    csv_file.write_text(
        "amount,type,date,category_id\n"
        f"2000,income,2026-09-01,{app['category_id']}\n"
        f"300,expense,2026-09-03,{app['category_id']}\n"
        f"700,expense,2026-09-04,{travel.category_id}\n"
    )
    assert app['csv_service'].import_csv(str(csv_file))['imported'] == 3

    report = app['analytics_controller'].get_month_report('2026-09')
    assert report['summary'] == {'income': 2000, 'expense': 1000, 'balance': 1000}
    assert report['breakdown'] == {'Food': 300, 'Travel': 700}


def test_it3_deleting_a_transaction_lowers_the_budget_percentage(app):
    app['budget_service'].set_budget(app['category_id'], '2026-09', 200)
    saved = app['tx_controller'].add_transaction('100', 'expense', '2026-09-05', 'Food')['transaction']
    assert app['budget_service'].check_budget_status(app['category_id'], '2026-09')['percent_spent'] == 50
    app['transaction_service'].delete_transaction(saved.transaction_id)
    assert app['budget_service'].check_budget_status(app['category_id'], '2026-09')['percent_spent'] == 0


def test_it4_rejected_input_leaves_database_unchanged(app):
    for args in [('abc', 'expense', '2026-09-05', 'Food'),
                 ('10', 'expense', '05/09/2026', 'Food'),
                 ('10', 'savings', '2026-09-05', 'Food'),
                 ('10', 'expense', '2026-09-05', 'Unknown')]:
        with pytest.raises(ValidationError):
            app['tx_controller'].add_transaction(*args)
    assert app['transaction_service'].get_all_transactions() == []


def test_it5_export_then_reimport_is_idempotent(app, tmp_path):
    app['tx_controller'].add_transaction('10', 'expense', '2026-09-01', 'Food')
    app['tx_controller'].add_transaction('20', 'income', '2026-09-02', 'Food')
    out = tmp_path / "export.csv"
    app['csv_service'].export_csv(str(out))

    # The export has a transaction_id column, which the importer simply ignores.
    result = app['csv_service'].import_csv(str(out))
    assert (result['imported'], result['skipped_duplicates'], result['errors']) == (0, 2, [])
    assert len(app['transaction_service'].get_all_transactions()) == 2


def test_it6_assignment01_database_survives_migration_and_keeps_working(tmp_path, monkeypatch):
    """Regression for Part A: an old v0 database is upgraded in place and the app still works on it."""
    path = str(tmp_path / "assignment01.db")
    monkeypatch.setattr(db, 'DB_NAME', path)
    raw = sqlite3.connect(path)
    raw.executescript("""
        CREATE TABLE categories(category_id INTEGER PRIMARY KEY AUTOINCREMENT, category_name TEXT UNIQUE NOT NULL);
        CREATE TABLE transactions(transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL CHECK (amount > 0), type TEXT NOT NULL CHECK (type IN ('income','expense')),
            date TEXT NOT NULL, category_id INTEGER NOT NULL REFERENCES categories(category_id));
        CREATE TABLE budgets(budget_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL REFERENCES categories(category_id), month TEXT NOT NULL,
            limit_amount INTEGER NOT NULL CHECK (limit_amount > 0), UNIQUE (category_id, month));
        INSERT INTO categories(category_name) VALUES ('Food');
        INSERT INTO transactions(amount, type, date, category_id) VALUES (1000,'income','2026-09-01',1),
                                                                         (200,'expense','2026-09-05',1);
        INSERT INTO budgets(category_id, month, limit_amount) VALUES (1,'2026-09',500);
    """)
    raw.commit()
    raw.close()

    result = migrate(backup=False, log=lambda *_: None)
    assert (result['from_version'], result['to_version']) == (0, 2)

    conn = db.get_connection()
    assert get_version(conn) == 2
    conn.close()

    assert AnalyticsController().get_month_report('2026-09')['summary'] == {
        'income': 1000, 'expense': 200, 'balance': 800}
    assert BudgetService().check_budget_status(1, '2026-09')['percent_spent'] == pytest.approx(40.0)
