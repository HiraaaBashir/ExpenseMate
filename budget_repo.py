from db import get_connection
from models import Budget


class BudgetNotFoundError(Exception):
    """Raised when a requested budget does not exist in the database."""
    pass


class BudgetRepo:
    """Handles database operations for Budget records."""

    def add(self, category_id, month, limit_amount):
        """Insert a new budget and return the created Budget object.

        Parameters:
            category_id: ID of the associated category.
            month: Year-month string (e.g., '2026-09').
            limit_amount: The spending limit, must be positive.

        Returns:
            The newly created Budget, including its auto-generated ID.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO budgets (category_id, month, limit_amount) VALUES (?, ?, ?)",
            (category_id, month, limit_amount)
        )
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return Budget(budget_id=new_id, category_id=category_id, month=month, limit_amount=limit_amount)

    def get_all(self):
        """Fetch all budgets.

        Returns:
            A list of Budget objects, empty if none exist.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM budgets")
        rows = cursor.fetchall()
        conn.close()
        return [
            Budget(
                budget_id=row['budget_id'],
                category_id=row['category_id'],
                month=row['month'],
                limit_amount=row['limit_amount']
            ) for row in rows
        ]

    def get_by_id(self, budget_id):
        """Fetch a single budget by its ID.

        Parameters:
            budget_id: ID of the budget to fetch.

        Returns:
            The matching Budget object.

        Raises:
            BudgetNotFoundError: If no budget with that ID exists.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM budgets WHERE budget_id = ?", (budget_id,))
        row = cursor.fetchone()
        conn.close()
        if row is None:
            raise BudgetNotFoundError(f"No budget found with id {budget_id}")
        return Budget(
            budget_id=row['budget_id'],
            category_id=row['category_id'],
            month=row['month'],
            limit_amount=row['limit_amount']
        )

    def delete(self, budget_id):
        """Delete a budget by its ID.

        Parameters:
            budget_id: ID of the budget to delete.

        Raises:
            BudgetNotFoundError: If no budget with that ID exists.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM budgets WHERE budget_id = ?", (budget_id,))
        if cursor.rowcount == 0:
            conn.close()
            raise BudgetNotFoundError(f"No budget found with id {budget_id}")
        conn.commit()
        conn.close()

    def get_by_category_and_month(self, category_id, month):
        """Fetch the budget for a specific category and month, if one exists.

        Parameters:
            category_id: ID of the category.
            month: Year-month string (e.g., '2026-09').

        Returns:
            The matching Budget object, or None if no budget is set.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM budgets WHERE category_id = ? AND month = ?",
            (category_id, month)
        )
        row = cursor.fetchone()
        conn.close()
        if row is None:
            return None
        return Budget(budget_id=row['budget_id'], category_id=row['category_id'], month=row['month'], limit_amount=row['limit_amount'])