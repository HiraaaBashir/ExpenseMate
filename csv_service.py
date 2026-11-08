import csv

from exceptions import ValidationError

EXPORT_COLUMNS = ['transaction_id', 'amount', 'type', 'date', 'category_id']


class CSVService:
    """Imports and exports transactions as CSV.

    This class only deals with the file format. Every business rule (validation,
    duplicate detection, budget checks) is delegated to TransactionService.
    """

    def __init__(self, transaction_service):
        self.transaction_service = transaction_service

    def import_csv(self, filepath):
        """Import transactions from a CSV file, skipping invalid and duplicate rows.

        Parameters:
            filepath: Path to the CSV file. Expected columns: amount,type,date,category_id

        Returns:
            A dict: {'imported': int, 'skipped_duplicates': int, 'errors': list of (row_number, error_message)}.
        """
        result = {'imported': 0, 'skipped_duplicates': 0, 'errors': []}
        with open(filepath, newline='') as f:
            # Row 1 is the header, so the first data row is row 2.
            for row_number, row in enumerate(csv.DictReader(f), start=2):
                try:
                    outcome = self._import_row(row)
                except (ValidationError, ValueError, KeyError) as e:
                    result['errors'].append((row_number, str(e)))
                else:
                    result[outcome] += 1
        return result

    def export_csv(self, filepath):
        """Export all transactions to a CSV file.

        Parameters:
            filepath: Path where the CSV file will be written.
        """
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(EXPORT_COLUMNS)
            for t in self.transaction_service.get_all_transactions():
                writer.writerow([t.transaction_id, t.amount, t.type, t.date, t.category_id])

    def _import_row(self, row):
        """Save one CSV row. Returns 'imported' or 'skipped_duplicates'."""
        fields = self._parse_row(row)
        if self.transaction_service.is_duplicate(**fields):
            return 'skipped_duplicates'
        self.transaction_service.add_transaction(**fields)
        return 'imported'

    @staticmethod
    def _parse_row(row):
        """Convert one raw CSV row into typed keyword arguments (raises ValueError/KeyError if malformed)."""
        return {
            'amount': float(row['amount']),
            'type': row['type'].strip(),
            'date': row['date'].strip(),
            'category_id': int(row['category_id']),
        }
