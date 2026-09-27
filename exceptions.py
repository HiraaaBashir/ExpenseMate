
class ValidationError(Exception):
    """Raised when input data fails a business rule validation check."""
    pass


class DuplicateBudgetError(Exception):
    """Raised when trying to set a budget for a category/month that already has one."""
    pass