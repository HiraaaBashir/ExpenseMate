import os
import pytest
import db
from migrations import migrate
from category_service import CategoryService
from budget_service import BudgetService
from transaction_service import TransactionService
from csv_service import CSVService

TEST_DB = 'test_expensemate.db'


@pytest.fixture
def services():
    """Set up fresh service instances backed by a temporary test database."""
    db.DB_NAME = TEST_DB
    migrate(backup=False, log=lambda *_: None)  # same schema as the real app, no copy-pasted DDL

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