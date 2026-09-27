from collections import defaultdict
from transaction_repo import TransactionRepo
from category_repo import CategoryRepo


class AnalyticsService:
    """Business logic for monthly income/expense/balance summaries and category breakdowns."""

    def __init__(self):
        self.repo = TransactionRepo()
        self.category_repo = CategoryRepo()

    def get_monthly_summary(self, month):
        """Compute total income, expense, and balance for a given month.

        Parameters:
            month: Year-month string (e.g., '2026-09').

        Returns:
            A dict: {'income': float, 'expense': float, 'balance': float}.
        """
        income = self.repo.sum_by_type_and_month('income', month)
        expense = self.repo.sum_by_type_and_month('expense', month)
        balance = income - expense
        return {'income': income, 'expense': expense, 'balance': balance}

    def get_category_breakdown(self, month):
        """Compute total expense per category for a given month.

        Parameters:
            month: Year-month string (e.g., '2026-09').

        Returns:
            A dict mapping category_name -> total expense amount, for
            categories with at least one expense transaction that month.
        """
        categories = {c.category_id: c.category_name for c in self.category_repo.get_all()}
        breakdown = defaultdict(float)
        for t in self.repo.get_all():
            if t.type == "expense" and t.date[:7] == month:
                breakdown[categories.get(t.category_id, "?")] += t.amount
        return dict(breakdown)