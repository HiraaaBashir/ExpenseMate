import os
import pytest
import db
from category_service import CategoryService
from budget_service import BudgetService
from transaction_service import TransactionService
from csv_service import CSVService

TEST_DB = 'test_expensemate.db'


@pytest.fixture
def services():
    """Set up fresh service instances backed by a temporary test database."""
    db.DB_NAME = TEST_DB
    conn = db.get_connection()
    conn.execute("""CREATE TABLE categories (category_id INTEGER PRIMARY KEY AUTOINCREMENT, category_name TEXT UNIQUE NOT NULL)""")
    conn.execute("""CREATE TABLE transactions (transaction_id INTEGER PRIMARY KEY AUTOINCREMENT, amount REAL NOT NULL CHECK (amount > 0), type TEXT NOT NULL CHECK (type IN ('income', 'expense')), date TEXT NOT NULL, category_id INTEGER NOT NULL REFERENCES categories(category_id))""")
    conn.execute("""CREATE TABLE budgets (budget_id INTEGER PRIMARY KEY AUTOINCREMENT, category_id INTEGER NOT NULL REFERENCES categories(category_id), month TEXT NOT NULL, limit_amount REAL NOT NULL CHECK (limit_amount > 0), UNIQUE (category_id, month))""")
    conn.commit()
    conn.close()

    category_service = CategoryService()
    budget_service = BudgetService()
    transaction_service = TransactionService(budget_service)
    csv_service = CSVService(transaction_service)
    category = category_service.add_category("Food")

    yield {
        'category_service': category_service,
        'budget_service': budget_service,
        'transaction_service': transaction_service,
        'csv_service': csv_service,
        'category_id': category.category_id
    }

    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    db.DB_NAME = 'expensemate.db'