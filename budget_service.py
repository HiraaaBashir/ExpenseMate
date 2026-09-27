from budget_repo import BudgetRepo
from transaction_repo import TransactionRepo
from exceptions import ValidationError, DuplicateBudgetError

ALERT_THRESHOLD = 80


class BudgetService:
    """Business logic for setting budgets and checking alert thresholds."""

    def __init__(self):
        self.repo = BudgetRepo()
        self.transaction_repo = TransactionRepo()

    def set_budget(self, category_id, month, limit_amount):
        """Validate and create a new budget for a category and month.

        Parameters:
            category_id: ID of the category.
            month: Year-month string (e.g., '2026-09').
            limit_amount: Spending limit, must be positive.

        Returns:
            The newly created Budget.

        Raises:
            ValidationError: If limit_amount is not positive.
            DuplicateBudgetError: If a budget already exists for this category/month.
        """
        if limit_amount <= 0:
            raise ValidationError("Limit amount must be positive.")
        if self.repo.get_by_category_and_month(category_id, month) is not None:
            raise DuplicateBudgetError(f"Budget already exists for category {category_id} in {month}.")
        return self.repo.add(category_id, month, limit_amount)

    def get_all_budgets(self):
        """Return every budget across all categories and months.

        Returns:
            A list of Budget objects, empty if none exist.
        """
        return self.repo.get_all()

    def check_budget_status(self, category_id, month):
        """Check spending against the budget for a category and month.

        Parameters:
            category_id: ID of the category.
            month: Year-month string (e.g., '2026-09').

        Returns:
            A dict: {'percent_spent': float or None, 'alert_triggered': bool}.
            percent_spent is None if no budget is set for this category/month.
        """
        budget = self.repo.get_by_category_and_month(category_id, month)
        if budget is None:
            return {'percent_spent': None, 'alert_triggered': False}

        total_spent = self.transaction_repo.sum_by_category_and_month(category_id, month)
        percent_spent = (total_spent / budget.limit_amount) * 100

        alert_triggered = percent_spent >= ALERT_THRESHOLD
        return {'percent_spent': percent_spent, 'alert_triggered': alert_triggered}
        