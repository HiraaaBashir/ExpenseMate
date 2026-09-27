from db import get_connection
from models import Transaction


class TransactionNotFoundError(Exception):
    """Raised when a requested transaction does not exist in the database."""
    pass


class TransactionRepo:
    """Handles database operations for Transaction records."""

    def add(self, amount, type, date, category_id):
        """Insert a new transaction and return the created Transaction object.

        Parameters:
            amount: The transaction amount, must be positive.
            type: Either 'income' or 'expense'.
            date: ISO-format date string (e.g., '2026-09-26').
            category_id: ID of the associated category.

        Returns:
            The newly created Transaction, including its auto-generated ID.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO transactions (amount, type, date, category_id) VALUES (?, ?, ?, ?)",
            (amount, type, date, category_id)
        )
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return Transaction(transaction_id=new_id, amount=amount, type=type, date=date, category_id=category_id)

    def get_all(self):
        """Fetch all transactions.

        Returns:
            A list of Transaction objects, empty if none exist.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transactions")
        rows = cursor.fetchall()
        conn.close()
        return [
            Transaction(
                transaction_id=row['transaction_id'],
                amount=row['amount'],
                type=row['type'],
                date=row['date'],
                category_id=row['category_id']
            ) for row in rows
        ]

    def get_by_id(self, transaction_id):
        """Fetch a single transaction by its ID.

        Parameters:
            transaction_id: ID of the transaction to fetch.

        Returns:
            The matching Transaction object.

        Raises:
            TransactionNotFoundError: If no transaction with that ID exists.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transactions WHERE transaction_id = ?", (transaction_id,))
        row = cursor.fetchone()
        conn.close()
        if row is None:
            raise TransactionNotFoundError(f"No transaction found with id {transaction_id}")
        return Transaction(
            transaction_id=row['transaction_id'],
            amount=row['amount'],
            type=row['type'],
            date=row['date'],
            category_id=row['category_id']
        )

    def delete(self, transaction_id):
        """Delete a transaction by its ID.

        Parameters:
            transaction_id: ID of the transaction to delete.

        Raises:
            TransactionNotFoundError: If no transaction with that ID exists.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transactions WHERE transaction_id = ?", (transaction_id,))
        if cursor.rowcount == 0:
            conn.close()
            raise TransactionNotFoundError(f"No transaction found with id {transaction_id}")
        conn.commit()
        conn.close()

    def exists(self, amount, type, date, category_id):
        """Check whether a transaction with this exact amount/type/date/category already exists.

        Used by CSV import to avoid creating duplicate entries when the same
        file (or an overlapping one) is imported more than once.

        Parameters:
            amount: The transaction amount to match.
            type: Either 'income' or 'expense'.
            date: ISO-format date string (e.g., '2026-09-26').
            category_id: ID of the associated category.

        Returns:
            True if a matching transaction already exists, False otherwise.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM transactions WHERE amount = ? AND type = ? AND date = ? AND category_id = ? LIMIT 1",
            (amount, type, date, category_id)
        )
        row = cursor.fetchone()
        conn.close()
        return row is not None

    def sum_by_type_and_month(self, type, month):
        """Sum all amounts of a given type ('income' or 'expense') in a given month.

        Parameters:
            type: Either 'income' or 'expense'.
            month: Year-month string (e.g., '2026-09').

        Returns:
            The total as a float, or 0.0 if no matching transactions.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT SUM(amount) as total FROM transactions WHERE type = ? AND date LIKE ?",
            (type, f"{month}%")
        )
        row = cursor.fetchone()
        conn.close()
        return row['total'] if row['total'] is not None else 0.0

    def sum_by_category_and_month(self, category_id, month):
        """Sum all expense amounts for a category in a given month.

        Parameters:
            category_id: ID of the category to sum.
            month: Year-month string (e.g., '2026-09').

        Returns:
            The total spent as a float, or 0.0 if no matching transactions.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT SUM(amount) as total FROM transactions WHERE category_id = ? AND type = 'expense' AND date LIKE ?",
            (category_id, f"{month}%")
        )
        row = cursor.fetchone()
        conn.close()
        return row['total'] if row['total'] is not None else 0.0