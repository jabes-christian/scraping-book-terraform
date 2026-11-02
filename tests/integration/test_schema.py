import psycopg
import pytest

pytestmark = pytest.mark.integration


def _tables(conn: psycopg.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
    ).fetchall()
    return {row[0] for row in rows}


def _new_execution(conn: psycopg.Connection) -> int:
    return conn.execute(
        "INSERT INTO executions (status) VALUES ('RUNNING') RETURNING id"
    ).fetchone()[0]


def _new_book(conn: psycopg.Connection, url: str = "http://x/book") -> int:
    return conn.execute(
        "INSERT INTO books (url, title, category) VALUES (%s, 'T', 'C') RETURNING id", (url,)
    ).fetchone()[0]


def test_applying_the_ddl_creates_the_three_tables(conn, schema_sql):  # DB-01
    conn.execute(schema_sql)
    assert _tables(conn) == {"executions", "books", "price_history"}


def test_applying_the_ddl_twice_does_not_fail(conn, schema_sql):  # DB-01 (idempotent)
    conn.execute(schema_sql)
    conn.execute(schema_sql)
    assert _tables(conn) == {"executions", "books", "price_history"}


def test_price_is_numeric_10_2(conn, schema_sql):  # DB-09
    conn.execute(schema_sql)
    row = conn.execute(
        "SELECT data_type, numeric_precision, numeric_scale FROM information_schema.columns "
        "WHERE table_name = 'price_history' AND column_name = 'price'"
    ).fetchone()
    assert row == ("numeric", 10, 2)


def test_currency_defaults_to_gbp(conn, schema_sql):  # DB-09
    conn.execute(schema_sql)
    execution_id, book_id = _new_execution(conn), _new_book(conn)
    currency = conn.execute(
        "INSERT INTO price_history (execution_id, book_id, price, availability) "
        "VALUES (%s, %s, 51.77, 'In stock') RETURNING currency",
        (execution_id, book_id),
    ).fetchone()[0]
    assert currency == "GBP"


def test_status_rejects_values_outside_the_enum(conn, schema_sql):  # Done-when: status enum
    conn.execute(schema_sql)
    for valid in ("RUNNING", "SUCCESS", "FAILED"):
        conn.execute("INSERT INTO executions (status) VALUES (%s)", (valid,))
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute("INSERT INTO executions (status) VALUES ('DONE')")


def test_one_price_row_per_execution_and_book(conn, schema_sql):  # Done-when: UNIQUE
    conn.execute(schema_sql)
    execution_id, book_id = _new_execution(conn), _new_book(conn)
    insert = (
        "INSERT INTO price_history (execution_id, book_id, price, availability) "
        "VALUES (%s, %s, 10.00, 'In stock')"
    )
    conn.execute(insert, (execution_id, book_id))
    with pytest.raises(psycopg.errors.UniqueViolation):
        conn.execute(insert, (execution_id, book_id))
    # same book in another execution is allowed (history)
    conn.execute(insert, (_new_execution(conn), book_id))
    count = conn.execute("SELECT count(*) FROM price_history").fetchone()[0]
    assert count == 2


def test_book_url_is_unique(conn, schema_sql):  # base do upsert por URL (T19)
    conn.execute(schema_sql)
    _new_book(conn, "http://x/same")
    with pytest.raises(psycopg.errors.UniqueViolation):
        _new_book(conn, "http://x/same")
