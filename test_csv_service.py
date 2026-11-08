def test_import_csv_valid_rows(services, tmp_path):
    csv_file = tmp_path / "transactions.csv"
    csv_file.write_text(f"amount,type,date,category_id\n500,expense,2026-09-27,{services['category_id']}\n300,income,2026-09-26,{services['category_id']}\n")
    result = services['csv_service'].import_csv(str(csv_file))
    assert result['imported'] == 2
    assert result['errors'] == []


def test_import_csv_skips_invalid_rows(services, tmp_path):
    csv_file = tmp_path / "transactions.csv"
    csv_file.write_text(f"amount,type,date,category_id\n500,expense,2026-09-27,{services['category_id']}\n-100,expense,2026-09-26,{services['category_id']}\n")
    result = services['csv_service'].import_csv(str(csv_file))
    assert result['imported'] == 1
    assert len(result['errors']) == 1


def test_export_csv_writes_all_transactions(services, tmp_path):
    services['transaction_service'].add_transaction(amount=500, type='expense', date='2026-09-27', category_id=services['category_id'])
    out_file = tmp_path / "export.csv"
    services['csv_service'].export_csv(str(out_file))
    content = out_file.read_text()
    assert "500" in content
    assert "expense" in content

def test_import_csv_skips_duplicate_rows(services, tmp_path):
    services['transaction_service'].add_transaction(amount=500, type='expense', date='2026-09-27', category_id=services['category_id'])
    csv_file = tmp_path / "transactions.csv"
    csv_file.write_text(f"amount,type,date,category_id\n500,expense,2026-09-27,{services['category_id']}\n")
    result = services['csv_service'].import_csv(str(csv_file))
    assert result['imported'] == 0
    assert result['skipped_duplicates'] == 1

def test_import_csv_reports_imported_duplicates_and_errors_together(services, tmp_path):
    cid = services['category_id']
    services['transaction_service'].add_transaction(amount=500, type='expense', date='2026-09-27', category_id=cid)
    csv_file = tmp_path / "mixed.csv"
    csv_file.write_text(
        "amount,type,date,category_id\n"
        f"500,expense,2026-09-27,{cid}\n"      # row 2: duplicate
        f"250,expense,2026-09-28,{cid}\n"      # row 3: new
        f"abc,expense,2026-09-28,{cid}\n"      # row 4: bad amount
        f"100,expense,2026-09-29,999\n"        # row 5: unknown category
    )
    result = services['csv_service'].import_csv(str(csv_file))
    assert result['imported'] == 1
    assert result['skipped_duplicates'] == 1
    assert [row for row, _ in result['errors']] == [4, 5]


def test_import_csv_missing_column_is_reported_not_raised(services, tmp_path):
    csv_file = tmp_path / "no_amount.csv"
    csv_file.write_text("type,date,category_id\nexpense,2026-09-27,1\n")
    result = services['csv_service'].import_csv(str(csv_file))
    assert result['imported'] == 0
    assert len(result['errors']) == 1


def test_import_csv_uses_service_duplicate_check_not_the_repo(services, tmp_path, monkeypatch):
    """Layering: CSVService must go through TransactionService.is_duplicate."""
    calls = []
    monkeypatch.setattr(services['transaction_service'], 'is_duplicate',
                        lambda **kw: calls.append(kw) or False)
    csv_file = tmp_path / "one.csv"
    csv_file.write_text(f"amount,type,date,category_id\n5,expense,2026-09-27,{services['category_id']}\n")
    services['csv_service'].import_csv(str(csv_file))
    assert len(calls) == 1
