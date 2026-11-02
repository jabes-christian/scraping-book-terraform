import json
import logging
import socket
from decimal import Decimal

import pytest

from book_monitor import db
from book_monitor.models import BookItem
from book_monitor.runner import run

pytestmark = pytest.mark.integration

SECRET = "pw-ZZ-9917"


@pytest.fixture(autouse=True)
def restore_logging():
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    yield
    root.handlers[:], root.level = handlers, level


def _item(n: int, price: str = "10.00") -> BookItem:
    return BookItem("Travel", f"Book {n}", Decimal(price), "In stock", f"http://site/book-{n}")


def _scraper(items):
    return lambda settings: items


def _raising(exc: Exception):
    def scraper(settings):
        raise exc

    return scraper


def _env(pg_env, **overrides: str) -> dict[str, str]:
    return {**pg_env, **overrides}


def _executions(conn) -> list[tuple]:
    return conn.execute(
        "SELECT status, items_count, error FROM executions ORDER BY id"
    ).fetchall()


def _prices(conn) -> int:
    return conn.execute("SELECT count(*) FROM price_history").fetchone()[0]


def _closed_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


# --- CFG-02: configuration error ---


def test_missing_password_returns_2_names_the_variable_and_opens_no_connection(
    pg_env, monkeypatch, capsys
):
    def fail(*args, **kwargs):
        raise AssertionError("must not touch the database")

    monkeypatch.setattr(db, "connect_with_retry", fail)
    env = _env(pg_env)
    del env["DB_PASSWORD"]

    assert run(env, scraper=_scraper([])) == 2
    assert "DB_PASSWORD" in capsys.readouterr().out


# --- CFG-05 / DB-04 / DB-01: success ---


def test_successful_run_returns_0_and_records_success(conn, pg_env):
    items = [_item(1), _item(2), _item(3)]

    assert run(_env(pg_env), scraper=_scraper(items)) == 0

    assert _executions(conn) == [("SUCCESS", 3, None)]
    assert _prices(conn) == 3


def test_run_marks_stale_running_executions_as_abandoned(conn, pg_env):
    db.ensure_schema(conn)
    conn.execute(
        "INSERT INTO executions (status, started_at) VALUES ('RUNNING', now() - interval '3 hours')"
    )

    assert run(_env(pg_env), scraper=_scraper([_item(1)])) == 0

    assert _executions(conn) == [("FAILED", None, "abandoned"), ("SUCCESS", 1, None)]


def test_two_runs_create_two_independent_executions(conn, pg_env):
    items = [_item(1), _item(2)]
    assert run(_env(pg_env), scraper=_scraper(items)) == 0
    assert run(_env(pg_env), scraper=_scraper(items)) == 0

    assert _executions(conn) == [("SUCCESS", 2, None), ("SUCCESS", 2, None)]
    assert _prices(conn) == 4


# --- CFG-05 / DB-05: failure ---


def test_scraper_error_returns_1_and_records_failed_without_prices(conn, pg_env):
    assert run(_env(pg_env), scraper=_raising(RuntimeError("count mismatch: Travel"))) == 1

    [(status, items_count, error)] = _executions(conn)
    assert (status, items_count) == ("FAILED", None)
    assert "count mismatch: Travel" in error
    assert _prices(conn) == 0


def test_failure_while_saving_rolls_back_and_records_failed(conn, pg_env):
    items = [_item(1), _item(2, price="100000000.00")]  # overflows numeric(10,2)

    assert run(_env(pg_env), scraper=_scraper(items)) == 1

    [(status, _, error)] = _executions(conn)
    assert status == "FAILED"
    assert error
    assert _prices(conn) == 0


# --- DB-07 / CFG-03: database down, secrets ---


def test_unreachable_database_returns_1_without_scraping_or_leaking_the_password(
    pg_env, monkeypatch, capsys
):
    started = []
    monkeypatch.setattr(db, "start_execution", lambda conn: started.append(1))
    scraped = []
    env = _env(
        pg_env, DB_PORT=str(_closed_port()), DB_PASSWORD=SECRET, DB_CONNECT_TIMEOUT_SECONDS="1"
    )

    assert run(env, scraper=lambda s: scraped.append(1) or []) == 1

    captured = capsys.readouterr()
    assert SECRET not in captured.out + captured.err
    assert "could not connect" in captured.out
    assert started == [] and scraped == []


def test_password_in_an_exception_never_reaches_output_or_executions(conn, pg_env, capsys):
    # the test database user gets the secret, so the run really authenticates with it
    user = pg_env["DB_USER"]
    conn.execute(f"ALTER USER {user} PASSWORD '{SECRET}'")
    try:
        env = _env(pg_env, DB_PASSWORD=SECRET)
        code = run(env, scraper=_raising(RuntimeError(f"upstream said password={SECRET}")))
        captured = capsys.readouterr()
        [(_, _, error)] = _executions(conn)
    finally:
        conn.execute(f"ALTER USER {user} PASSWORD '{pg_env['DB_PASSWORD']}'")

    assert code == 1
    assert SECRET not in captured.out + captured.err
    assert SECRET not in error
    assert "password=***" in error
    for line in captured.out.splitlines():
        json.loads(line)  # CFG-06: every log line is JSON
