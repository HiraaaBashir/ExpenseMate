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