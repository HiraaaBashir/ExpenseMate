from exceptions import ValidationError


class TransactionController:
    """Receives the UI's "add transaction" action.

    Responsibilities (and nothing more):
      * turn raw form text into typed values (amount -> float, category name -> id)
      * reject obviously incomplete input with a friendly ValidationError
      * call TransactionService and hand its result straight back

    Business rules (positive amount, valid type/date, category exists, budget alert)
    live in TransactionService; SQL lives in TransactionRepo.
    """

    def __init__(self, transaction_service, category_service):
        self.service = transaction_service
        self.category_service = category_service

    def add_transaction(self, amount_text, type_, date_text, category_name):
        """Add a transaction from raw form input.

        Parameters:
            amount_text: The amount exactly as typed, e.g. "250" or " 99.5 ".
            type_: 'income' or 'expense'.
            date_text: Date as typed (YYYY-MM-DD).
            category_name: The category's display name as chosen in the dropdown.

        Returns:
            The service result: {'transaction': Transaction, 'alert_triggered': bool,
            'percent_spent': float or None}.

        Raises:
            ValidationError: If the category is missing/unknown, the amount is not a
            number, or the service rejects the data.
        """
        category_id = self._category_id(category_name)
        try:
            amount = float(amount_text)
        except (TypeError, ValueError):
            raise ValidationError("Amount must be a number.")
        return self.service.add_transaction(
            amount=amount, type=type_, date=(date_text or "").strip(), category_id=category_id)

    def _category_id(self, category_name):
        for category in self.category_service.get_all_categories():
            if category.category_name == category_name:
                return category.category_id
        raise ValidationError("Please select a category first (add one in the Categories tab).")
