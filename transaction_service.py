from datetime import datetime
from transaction_repo import TransactionRepo
from category_repo import CategoryRepo, CategoryNotFoundError
from exceptions import ValidationError


class TransactionService:
    """Business logic for adding and managing transactions."""

    def __init__(self, budget_service):
        self.repo = TransactionRepo()
        self.category_repo = CategoryRepo()
        self.budget_service = budget_service

    def add_transaction(self, amount, type, date, category_id):
        """Validate, save a transaction, and trigger a budget check.

        Parameters:
            amount: Transaction amount, must be positive.
            type: Either 'income' or 'expense'.
            date: ISO-format date string (e.g., '2026-09-26').
            category_id: ID of the associated category.

        Returns:
            A dict with the saved transaction and budget alert info:
            {'transaction': Transaction, 'alert_triggered': bool, 'percent_spent': float or None}

        Raises:
            ValidationError: If any field fails validation.
        """
        if amount <= 0:
            raise ValidationError("Amount must be positive.")
        if type not in ('income', 'expense'):
            raise ValidationError("Type must be 'income' or 'expense'.")
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            raise ValidationError("Date must be in YYYY-MM-DD format.")
        try:
            self.category_repo.get_by_id(category_id)
        except CategoryNotFoundError:
            raise ValidationError(f"Category {category_id} does not exist.")

        transaction = self.repo.add(amount, type, date, category_id)

        alert_triggered = False
        percent_spent = None
        if type == 'expense':
            month = date[:7]
            status = self.budget_service.check_budget_status(category_id, month)
            alert_triggered = status['alert_triggered']
            percent_spent = status['percent_spent']

        return {'transaction': transaction, 'alert_triggered': alert_triggered, 'percent_spent': percent_spent}

    def is_duplicate(self, amount, type, date, category_id):
        """Return True if an identical transaction (amount/type/date/category) is already saved."""
        return self.repo.exists(amount, type, date, category_id)

    def get_all_transactions(self):
        """Return all transactions."""
        return self.repo.get_all()

    def delete_transaction(self, transaction_id):
        """Delete a transaction by ID."""
        self.repo.delete(transaction_id)