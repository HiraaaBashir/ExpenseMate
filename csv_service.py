import csv
from exceptions import ValidationError


class CSVService:
    """Handles CSV import and export of transactions."""

    def __init__(self, transaction_service):
        self.transaction_service = transaction_service

    def import_csv(self, filepath):
        """Import transactions from a CSV file, skipping invalid and duplicate rows.

        Parameters:
            filepath: Path to the CSV file. Expected columns: amount,type,date,category_id

        Returns:
            A dict: {'imported': int, 'skipped_duplicates': int, 'errors': list of (row_number, error_message)}.
        """
        imported = 0
        skipped_duplicates = 0
        errors = []
        with open(filepath, newline='') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, start=2):
                try:
                    amount = float(row['amount'])
                    type_ = row['type']
                    date = row['date']
                    category_id = int(row['category_id'])
                    if self.transaction_service.repo.exists(amount, type_, date, category_id):
                        skipped_duplicates += 1
                        continue
                    self.transaction_service.add_transaction(amount=amount, type=type_, date=date,
                                                             category_id=category_id)
                    imported += 1
                except (ValidationError, ValueError, KeyError) as e:
                    errors.append((i, str(e)))
        return {'imported': imported, 'skipped_duplicates': skipped_duplicates, 'errors': errors}

    def export_csv(self, filepath):
        """Export all transactions to a CSV file.

        Parameters:
            filepath: Path where the CSV file will be written.
        """
        transactions = self.transaction_service.get_all_transactions()
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['transaction_id', 'amount', 'type', 'date', 'category_id'])
            for t in transactions:
                writer.writerow([t.transaction_id, t.amount, t.type, t.date, t.category_id])