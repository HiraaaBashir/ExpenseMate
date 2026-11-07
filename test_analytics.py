import pytest
from analytics_service import AnalyticsService
from analytics_controller import AnalyticsController
from exceptions import ValidationError


def _add(services, amount, type_, date):
    services['transaction_service'].add_transaction(
        amount=amount, type=type_, date=date, category_id=services['category_id'])


def test_monthly_summary_totals_and_balance(services):
    _add(services, 1000, 'income', '2026-09-05')
    _add(services, 300, 'expense', '2026-09-06')
    summary = AnalyticsService().monthly_summary('2026-09')
    assert summary == {'income': 1000, 'expense': 300, 'balance': 700}


def test_monthly_summary_ignores_other_months(services):
    _add(services, 500, 'expense', '2026-08-30')
    summary = AnalyticsService().monthly_summary('2026-09')
    assert summary == {'income': 0, 'expense': 0, 'balance': 0}


def test_category_breakdown_counts_only_expenses(services):
    _add(services, 200, 'expense', '2026-09-02')
    _add(services, 100, 'expense', '2026-09-03')
    _add(services, 900, 'income', '2026-09-04')
    assert AnalyticsService().category_breakdown('2026-09') == {'Food': 300}


def test_category_breakdown_empty_month(services):
    assert AnalyticsService().category_breakdown('2026-01') == {}


def test_controller_returns_report(services):
    _add(services, 250, 'expense', '2026-09-10')
    report = AnalyticsController().get_month_report(' 2026-09 ')
    assert report['month'] == '2026-09'
    assert report['summary']['expense'] == 250
    assert report['breakdown'] == {'Food': 250}


@pytest.mark.parametrize('bad', ['', '2026', '2026-13', 'Sept-2026', '2026-9'])
def test_controller_rejects_bad_month(services, bad):
    with pytest.raises(ValidationError):
        AnalyticsController().get_month_report(bad)