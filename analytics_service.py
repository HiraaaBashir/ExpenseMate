from collections import defaultdict

from transaction_repo import TransactionRepo
from category_repo import CategoryRepo


class AnalyticsService:
    """Business logic for monthly summaries and category breakdowns."""

    def __init__(self):
        self.transaction_repo = TransactionRepo()
        self.category_repo = CategoryRepo()

    def monthly_summary(self, month):
        """Total income, total expense and balance for a month (YYYY-MM).

        Returns:
            A dict: {'income': float, 'expense': float, 'balance': float}.
        """
        transactions = self._transactions_in_month(month)
        income = sum(t.amount for t in transactions if t.type == 'income')
        expense = sum(t.amount for t in transactions if t.type == 'expense')
        return {'income': income, 'expense': expense, 'balance': income - expense}

    def category_breakdown(self, month):
        """Total expense per category name for a month (YYYY-MM).

        Returns:
            A dict like {'Food': 300.0}; empty if there are no expenses.
        """
        names = {c.category_id: c.category_name for c in self.category_repo.get_all()}
        breakdown = defaultdict(float)
        for t in self._transactions_in_month(month):
            if t.type == 'expense':
                breakdown[names.get(t.category_id, '?')] += t.amount
        return dict(breakdown)

    def _transactions_in_month(self, month):
        return [t for t in self.transaction_repo.get_all() if t.date[:7] == month]