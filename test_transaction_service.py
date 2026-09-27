import pytest
from exceptions import ValidationError


def test_add_transaction_success(services):
    result = services['transaction_service'].add_transaction(
        amount=500, type='expense', date='2026-09-27', category_id=services['category_id']
    )
    assert result['transaction'].amount == 500
    assert result['alert_triggered'] is False


def test_add_transaction_negative_amount_raises_error(services):
    with pytest.raises(ValidationError):
        services['transaction_service'].add_transaction(
            amount=-100, type='expense', date='2026-09-27', category_id=services['category_id']
        )


def test_add_transaction_invalid_type_raises_error(services):
    with pytest.raises(ValidationError):
        services['transaction_service'].add_transaction(
            amount=100, type='savings', date='2026-09-27', category_id=services['category_id']
        )


def test_add_transaction_invalid_date_raises_error(services):
    with pytest.raises(ValidationError):
        services['transaction_service'].add_transaction(
            amount=100, type='expense', date='27-09-2026', category_id=services['category_id']
        )


def test_add_transaction_nonexistent_category_raises_error(services):
    with pytest.raises(ValidationError):
        services['transaction_service'].add_transaction(
            amount=100, type='expense', date='2026-09-27', category_id=999
        )


def test_add_transaction_triggers_budget_alert(services):
    services['budget_service'].set_budget(services['category_id'], '2026-09', 1000)
    services['transaction_service'].add_transaction(
        amount=850, type='expense', date='2026-09-27', category_id=services['category_id']
    )
    result = services['transaction_service'].add_transaction(
        amount=50, type='expense', date='2026-09-28', category_id=services['category_id']
    )
    assert result['alert_triggered'] is True
    assert result['percent_spent'] >= 80