import socket
import time

import psycopg
import pytest

from book_monitor import db
from book_monitor.config import Settings

pytestmark = pytest.mark.integration

SECRET = "s3cret-pass-123"


def _settings(env: dict[str, str], **overrides: str) -> Settings:
    return Settings.from_env({**env, **overrides})


def _tables(conn: psycopg.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
    ).fetchall()
    return {row[0] for row in rows}


def _closed_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _execution(conn: psycopg.Connection, status: str, age_hours: int) -> int:
    return conn.execute(
        "INSERT INTO executions (status, started_at) "
        "VALUES (%s, now() - make_interval(hours => %s)) RETURNING id",
        (status, age_hours),
    ).fetchone()[0]


def _row(conn: psycopg.Connection, exec_id: int) -> tuple:
    return conn.execute(
        "SELECT status, error, finished_at IS NOT NULL FROM executions WHERE id = %s", (exec_id,)
    ).fetchone()


# --- ensure_schema (DB-01) ---


def test_ensure_schema_creates_the_schema_in_an_empty_database(conn):
    assert _tables(conn) == set()
    db.ensure_schema(conn)
    assert _tables(conn) == {"executions", "books", "price_history"}


def test_ensure_schema_is_reentrant_and_keeps_data(conn):
    db.ensure_schema(conn)
    exec_id = _execution(conn, "SUCCESS", 0)
    db.ensure_schema(conn)
    assert _tables(conn) == {"executions", "books", "price_history"}
    assert _row(conn, exec_id)[0] == "SUCCESS"


# --- mark_abandoned (DB-06) ---


def test_mark_abandoned_fails_a_running_execution_older_than_the_limit(conn):
    db.ensure_schema(conn)
    stale = _execution(conn, "RUNNING", 3)
    assert db.mark_abandoned(conn, 2) == 1
    assert _row(conn, stale) == ("FAILED", "abandoned", True)


def test_mark_abandoned_keeps_a_recent_running_execution(conn):
    db.ensure_schema(conn)
    recent = _execution(conn, "RUNNING", 1)
    assert db.mark_abandoned(conn, 2) == 0
    assert _row(conn, recent) == ("RUNNING", None, False)


def test_mark_abandoned_keeps_finished_executions(conn):
    db.ensure_schema(conn)
    success = _execution(conn, "SUCCESS", 3)
    failed = _execution(conn, "FAILED", 3)
    assert db.mark_abandoned(conn, 2) == 0
    assert _row(conn, success)[:2] == ("SUCCESS", None)
    assert _row(conn, failed)[:2] == ("FAILED", None)


# --- connect_with_retry (DB-07) ---


def test_connect_with_retry_returns_a_working_autocommit_connection(pg_env):
    connection = db.connect_with_retry(_settings(pg_env), timeout=10)
    try:
        assert connection.autocommit is True
        assert connection.execute("SELECT 1").fetchone() == (1,)
    finally:
        connection.close()


def test_connect_with_retry_gives_up_at_the_timeout_when_the_host_is_unreachable(pg_env):
    settings = _settings(pg_env, DB_PORT=str(_closed_port()))
    start = time.monotonic()
    with pytest.raises(db.DatabaseUnavailableError) as excinfo:
        db.connect_with_retry(settings, timeout=2, interval=0.2)
    elapsed = time.monotonic() - start
    assert 2 <= elapsed < 8
    assert pg_env["DB_PASSWORD"] not in str(excinfo.value)


def test_connect_with_retry_keeps_trying_until_the_database_answers(pg_env, monkeypatch):
    real_connect = psycopg.connect
    attempts = []

    def flaky_connect(*args, **kwargs):
        attempts.append(1)
        if len(attempts) < 3:
            raise psycopg.OperationalError("connection refused")
        return real_connect(*args, **kwargs)

    monkeypatch.setattr(db.psycopg, "connect", flaky_connect)
    connection = db.connect_with_retry(_settings(pg_env), timeout=10, interval=0.01)
    connection.close()
    assert len(attempts) == 3


def test_connect_with_retry_error_never_contains_the_password(pg_env, monkeypatch):
    def failing_connect(*args, **kwargs):
        raise psycopg.OperationalError(f"auth failed for password={SECRET}")

    monkeypatch.setattr(db.psycopg, "connect", failing_connect)
    settings = _settings(pg_env, DB_PASSWORD=SECRET)
    with pytest.raises(db.DatabaseUnavailableError) as excinfo:
        db.connect_with_retry(settings, timeout=0.3, interval=0.05)
    assert SECRET not in str(excinfo.value)
    assert "***" in str(excinfo.value)
