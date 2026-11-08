from db import connection
from models import Transaction


class TransactionNotFoundError(Exception):
    """Raised when a requested transaction does not exist in the database."""
    pass


class TransactionRepo:
    """Data access for Transaction records. Contains SQL only - no business rules."""

    @staticmethod
    def _to_transaction(row):
        """Convert a database row into a Transaction (the one place this mapping lives)."""
        return Transaction(
            transaction_id=row['transaction_id'],
            amount=row['amount'],
            type=row['type'],
            date=row['date'],
            category_id=row['category_id'],
        )

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
        with connection(commit=True) as conn:
            cursor = conn.execute(
                "INSERT INTO transactions (amount, type, date, category_id) VALUES (?, ?, ?, ?)",
                (amount, type, date, category_id),
            )
            new_id = cursor.lastrowid
        return Transaction(transaction_id=new_id, amount=amount, type=type, date=date, category_id=category_id)

    def get_all(self):
        """Fetch all transactions.

        Returns:
            A list of Transaction objects, empty if none exist.
        """
        with connection() as conn:
            rows = conn.execute("SELECT * FROM transactions").fetchall()
        return [self._to_transaction(row) for row in rows]

    def get_by_id(self, transaction_id):
        """Fetch a single transaction by its ID.

        Raises:
            TransactionNotFoundError: If no transaction with that ID exists.
        """
        with connection() as conn:
            row = conn.execute(
                "SELECT * FROM transactions WHERE transaction_id = ?", (transaction_id,)
            ).fetchone()
        if row is None:
            raise TransactionNotFoundError(f"No transaction found with id {transaction_id}")
        return self._to_transaction(row)

    def delete(self, transaction_id):
        """Delete a transaction by its ID.

        Raises:
            TransactionNotFoundError: If no transaction with that ID exists.
        """
        with connection(commit=True) as conn:
            deleted = conn.execute(
                "DELETE FROM transactions WHERE transaction_id = ?", (transaction_id,)
            ).rowcount
        if deleted == 0:
            raise TransactionNotFoundError(f"No transaction found with id {transaction_id}")

    def exists(self, amount, type, date, category_id):
        """Check whether a transaction with this exact amount/type/date/category already exists.

        Used to avoid creating duplicate entries when the same CSV file is imported twice.

        Returns:
            True if a matching transaction already exists, False otherwise.
        """
        with connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM transactions WHERE amount = ? AND type = ? AND date = ? AND category_id = ? LIMIT 1",
                (amount, type, date, category_id),
            ).fetchone()
        return row is not None

    def sum_by_category_and_month(self, category_id, month):
        """Sum all expense amounts for a category in a given month (YYYY-MM).

        Returns:
            The total spent as a float, or 0.0 if no matching transactions.
        """
        with connection() as conn:
            row = conn.execute(
                "SELECT SUM(amount) AS total FROM transactions "
                "WHERE category_id = ? AND type = 'expense' AND date LIKE ?",
                (category_id, f"{month}%"),
            ).fetchone()
        return row['total'] if row['total'] is not None else 0.0
