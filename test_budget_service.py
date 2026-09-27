import pytest
from exceptions import ValidationError, DuplicateBudgetError


def test_set_budget_success(services):
    budget = services['budget_service'].set_budget(services['category_id'], '2026-09', 1000)
    assert budget.limit_amount == 1000


def test_set_budget_negative_limit_raises_error(services):
    with pytest.raises(ValidationError):
        services['budget_service'].set_budget(services['category_id'], '2026-09', -500)


def test_set_duplicate_budget_raises_error(services):
    services['budget_service'].set_budget(services['category_id'], '2026-09', 1000)
    with pytest.raises(DuplicateBudgetError):
        services['budget_service'].set_budget(services['category_id'], '2026-09', 2000)


def test_check_budget_status_no_budget_set(services):
    status = services['budget_service'].check_budget_status(services['category_id'], '2026-09')
    assert status['percent_spent'] is None
    assert status['alert_triggered'] is False


def test_check_budget_status_under_threshold(services):
    services['budget_service'].set_budget(services['category_id'], '2026-09', 1000)
    services['transaction_service'].add_transaction(amount=300, type='expense', date='2026-09-27', category_id=services['category_id'])
    status = services['budget_service'].check_budget_status(services['category_id'], '2026-09')
    assert status['alert_triggered'] is False


def test_check_budget_status_over_threshold(services):
    services['budget_service'].set_budget(services['category_id'], '2026-09', 1000)
    services['transaction_service'].add_transaction(amount=900, type='expense', date='2026-09-27', category_id=services['category_id'])
    status = services['budget_service'].check_budget_status(services['category_id'], '2026-09')
    assert status['alert_triggered'] is True