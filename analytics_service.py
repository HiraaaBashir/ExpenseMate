from transaction_repo import TransactionRepo


class AnalyticsService:
    """Business logic for monthly income/expense/balance summaries."""

    def __init__(self):
        self.repo = TransactionRepo()

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