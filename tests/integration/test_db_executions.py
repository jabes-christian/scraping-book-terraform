from decimal import Decimal

import psycopg
import pytest

from book_monitor import db
from book_monitor.models import BookItem

pytestmark = pytest.mark.integration


@pytest.fixture
def dbc(conn):
    db.ensure_schema(conn)
    return conn


def _item(n: int, **overrides) -> BookItem:
    fields = {
        "category": "Travel",
        "title": f"Book {n}",
        "price": Decimal(f"{n}.50"),
        "availability": "In stock",
        "url": f"http://site/book-{n}",
    }
    return BookItem(**{**fields, **overrides})


def _count(conn, table: str, where: str = "true", params: tuple = ()) -> int:
    return conn.execute(f"SELECT count(*) FROM {table} WHERE {where}", params).fetchone()[0]


def _execution(conn, exec_id: int) -> tuple:
    return conn.execute(
        "SELECT status, started_at IS NOT NULL, finished_at IS NOT NULL, items_count, error "
        "FROM executions WHERE id = %s",
        (exec_id,),
    ).fetchone()


# --- start_execution (DB-02) ---


def test_start_execution_inserts_a_running_row_with_started_at(dbc):
    exec_id = db.start_execution(dbc)
    assert _execution(dbc, exec_id) == ("RUNNING", True, False, None, None)


# --- save_success (DB-03, DB-04) ---


def test_save_success_writes_books_prices_and_marks_success(dbc):
    exec_id = db.start_execution(dbc)
    items = [_item(1), _item(2), _item(3, availability="Out of stock")]
    db.save_success(dbc, exec_id, items)

    assert _count(dbc, "books") == 3
    rows = dbc.execute(
        "SELECT b.url, b.title, b.category, p.price, p.currency, p.availability "
        "FROM price_history p JOIN books b ON b.id = p.book_id "
        "WHERE p.execution_id = %s ORDER BY b.url",
        (exec_id,),
    ).fetchall()
    assert rows == [
        ("http://site/book-1", "Book 1", "Travel", Decimal("1.50"), "GBP", "In stock"),
        ("http://site/book-2", "Book 2", "Travel", Decimal("2.50"), "GBP", "In stock"),
        ("http://site/book-3", "Book 3", "Travel", Decimal("3.50"), "GBP", "Out of stock"),
    ]
    assert _execution(dbc, exec_id) == ("SUCCESS", True, True, 3, None)


def test_save_success_rolls_back_everything_when_a_write_fails_midway(dbc):
    exec_id = db.start_execution(dbc)
    # 10**8 does not fit numeric(10,2): the 2nd item fails after the 1st was already written
    items = [_item(1), _item(2, price=Decimal("100000000.00")), _item(3)]
    with pytest.raises(psycopg.errors.NumericValueOutOfRange):
        db.save_success(dbc, exec_id, items)

    assert _count(dbc, "price_history") == 0
    assert _count(dbc, "books") == 0
    assert _execution(dbc, exec_id) == ("RUNNING", True, False, None, None)


# --- mark_failed (DB-05) ---


def test_mark_failed_records_the_error_without_touching_price_history(dbc):
    earlier = db.start_execution(dbc)
    db.save_success(dbc, earlier, [_item(1)])
    exec_id = db.start_execution(dbc)

    db.mark_failed(dbc, exec_id, "boom: page failed")

    assert _execution(dbc, exec_id) == ("FAILED", True, True, None, "boom: page failed")
    assert _count(dbc, "price_history", "execution_id = %s", (exec_id,)) == 0
    assert _count(dbc, "price_history") == 1


def test_mark_failed_truncates_the_error_to_2000_characters(dbc):
    exec_id = db.start_execution(dbc)
    error = "x" * 1999 + "AB" + "y" * 3000

    db.mark_failed(dbc, exec_id, error)

    stored = dbc.execute("SELECT error FROM executions WHERE id = %s", (exec_id,)).fetchone()[0]
    assert stored == error[:2000]
    assert len(stored) == 2000


# --- EDG-04 / DB-03 (upsert) / EDG-03 ---


def test_two_runs_create_independent_executions_each_with_its_own_prices(dbc):
    first, second = db.start_execution(dbc), db.start_execution(dbc)
    db.save_success(dbc, first, [_item(1), _item(2)])
    db.save_success(dbc, second, [_item(1), _item(2)])

    assert first != second
    assert _count(dbc, "executions", "status = 'SUCCESS'") == 2
    for exec_id in (first, second):
        assert _count(dbc, "price_history", "execution_id = %s", (exec_id,)) == 2
    assert _count(dbc, "price_history") == 4


def test_rerunning_the_same_book_updates_it_without_duplicating(dbc):
    first = db.start_execution(dbc)
    db.save_success(dbc, first, [_item(1, title="Old title", price=Decimal("10.00"))])
    before = dbc.execute("SELECT id, first_seen_at, last_seen_at FROM books").fetchone()

    second = db.start_execution(dbc)
    db.save_success(
        dbc, second, [_item(1, title="New title", category="Poetry", price=Decimal("12.00"))]
    )

    assert _count(dbc, "books") == 1
    book = dbc.execute(
        "SELECT id, title, category, first_seen_at, last_seen_at FROM books"
    ).fetchone()
    assert book[:3] == (before[0], "New title", "Poetry")
    assert book[3] == before[1]
    assert book[4] > before[2]
    prices = dbc.execute("SELECT price FROM price_history ORDER BY execution_id").fetchall()
    assert prices == [(Decimal("10.00"),), (Decimal("12.00"),)]


def test_title_with_quotes_and_accents_round_trips_intact(dbc):
    title = 'O "Pequeno" Príncipe: it\'s 100% açaí – 日本語'
    exec_id = db.start_execution(dbc)
    db.save_success(dbc, exec_id, [_item(1, title=title)])
    assert dbc.execute("SELECT title FROM books").fetchone()[0] == title
