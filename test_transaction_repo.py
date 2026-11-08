import sqlite3

import pytest

import db
from transaction_repo import TransactionRepo, TransactionNotFoundError


@pytest.fixture
def repo(services):
    return TransactionRepo()


def test_add_then_get_by_id_round_trip(repo, services):
    saved = repo.add(120.5, 'expense', '2026-09-01', services['category_id'])
    assert repo.get_by_id(saved.transaction_id) == saved


def test_get_all_returns_every_row(repo, services):
    repo.add(10, 'expense', '2026-09-01', services['category_id'])
    repo.add(20, 'income', '2026-09-02', services['category_id'])
    assert [t.amount for t in repo.get_all()] == [10, 20]


def test_get_by_id_missing_raises(repo):
    with pytest.raises(TransactionNotFoundError):
        repo.get_by_id(999)


def test_delete_removes_row_and_missing_id_raises(repo, services):
    saved = repo.add(10, 'expense', '2026-09-01', services['category_id'])
    repo.delete(saved.transaction_id)
    assert repo.get_all() == []
    with pytest.raises(TransactionNotFoundError):
        repo.delete(saved.transaction_id)


def test_exists_matches_only_identical_rows(repo, services):
    cid = services['category_id']
    repo.add(10, 'expense', '2026-09-01', cid)
    assert repo.exists(10, 'expense', '2026-09-01', cid) is True
    assert repo.exists(11, 'expense', '2026-09-01', cid) is False


def test_sum_by_category_and_month_counts_only_expenses_of_that_month(repo, services):
    cid = services['category_id']
    repo.add(100, 'expense', '2026-09-01', cid)
    repo.add(50, 'expense', '2026-09-20', cid)
    repo.add(500, 'income', '2026-09-05', cid)
    repo.add(70, 'expense', '2026-10-01', cid)
    assert repo.sum_by_category_and_month(cid, '2026-09') == 150
    assert repo.sum_by_category_and_month(cid, '2026-01') == 0.0


class _SpyConnection:
    """Wraps a real connection and records whether close() was called."""

    def __init__(self, real):
        self._real = real
        self.closed = False

    def __getattr__(self, name):
        return getattr(self._real, name)

    def close(self):
        self.closed = True
        self._real.close()


def test_connection_is_closed_even_when_the_query_fails(repo, monkeypatch):
    """Regression test for the Assignment 01 leak: a failing query used to leave the connection open."""
    spies = []
    real_get_connection = db.get_connection

    def spying_get_connection():
        spy = _SpyConnection(real_get_connection())
        spies.append(spy)
        return spy

    monkeypatch.setattr(db, 'get_connection', spying_get_connection)

    with pytest.raises(sqlite3.IntegrityError):
        repo.add(10, 'expense', '2026-09-01', 999)  # category 999 does not exist -> foreign key error

    assert len(spies) == 1 and spies[0].closed is True
