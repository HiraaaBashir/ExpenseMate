import re

from analytics_service import AnalyticsService
from exceptions import ValidationError

MONTH_PATTERN = re.compile(r'^\d{4}-(0[1-9]|1[0-2])$')


class AnalyticsController:
    """Receives the UI's request, validates basic input, calls the service."""

    def __init__(self, analytics_service=None):
        self.service = analytics_service or AnalyticsService()

    def get_month_report(self, month):
        """Return the summary and category breakdown for a month.

        Raises:
            ValidationError: If month is not in YYYY-MM format.
        """
        month = month.strip()
        if not MONTH_PATTERN.match(month):
            raise ValidationError("Month must be in YYYY-MM format (e.g. 2026-09).")
        return {
            'month': month,
            'summary': self.service.monthly_summary(month),
            'breakdown': self.service.category_breakdown(month),
        }