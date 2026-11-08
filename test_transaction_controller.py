import pytest

from exceptions import ValidationError
from transaction_controller import TransactionController


@pytest.fixture
def controller(services):
    return TransactionController(services['transaction_service'], services['category_service'])


def test_add_transaction_converts_form_text_and_saves(controller, services):
    result = controller.add_transaction(" 250 ", 'expense', ' 2026-09-15 ', 'Food')
    t = result['transaction']
    assert (t.amount, t.type, t.date, t.category_id) == (250.0, 'expense', '2026-09-15', services['category_id'])
    assert len(services['transaction_service'].get_all_transactions()) == 1


def test_unknown_category_name_is_rejected_and_nothing_saved(controller, services):
    with pytest.raises(ValidationError, match="select a category"):
        controller.add_transaction('100', 'expense', '2026-09-15', 'Nope')
    assert services['transaction_service'].get_all_transactions() == []


@pytest.mark.parametrize('bad_amount', ['abc', '', '  ', None])
def test_non_numeric_amount_is_rejected(controller, services, bad_amount):
    with pytest.raises(ValidationError, match="must be a number"):
        controller.add_transaction(bad_amount, 'expense', '2026-09-15', 'Food')
    assert services['transaction_service'].get_all_transactions() == []


def test_business_rule_errors_from_service_reach_the_caller(controller):
    with pytest.raises(ValidationError, match="positive"):
        controller.add_transaction('-5', 'expense', '2026-09-15', 'Food')


def test_budget_alert_information_is_passed_through(controller, services):
    services['budget_service'].set_budget(services['category_id'], '2026-09', 100)
    result = controller.add_transaction('90', 'expense', '2026-09-10', 'Food')
    assert result['alert_triggered'] is True
    assert result['percent_spent'] == pytest.approx(90.0)
