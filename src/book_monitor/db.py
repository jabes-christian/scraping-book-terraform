import time
from collections.abc import Sequence
from pathlib import Path

import psycopg

from book_monitor.config import Settings
from book_monitor.logging_setup import redact
from book_monitor.models import BookItem

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
ATTEMPT_TIMEOUT_SECONDS = 5
MAX_ERROR_LENGTH = 2000

UPSERT_BOOK_AND_PRICE = """
WITH b AS (
  INSERT INTO books (url, title, category) VALUES (%s, %s, %s)
  ON CONFLICT (url) DO UPDATE
    SET title = EXCLUDED.title, category = EXCLUDED.category, last_seen_at = now()
  RETURNING id)
INSERT INTO price_history (execution_id, book_id, price, availability)
SELECT %s, id, %s, %s FROM b
"""


class DatabaseUnavailableError(Exception):
    """PostgreSQL did not accept a connection before the deadline."""


def connect_with_retry(
    settings: Settings, timeout: float = 60, interval: float = 1.0
) -> psycopg.Connection:
    """Connect in autocommit mode, retrying until ``timeout`` seconds have passed."""
    deadline = time.monotonic() + timeout
    while True:
        try:
            return psycopg.connect(
                host=settings.db_host,
                port=settings.db_port,
                dbname=settings.db_name,
                user=settings.db_user,
                password=settings.db_password,
                connect_timeout=ATTEMPT_TIMEOUT_SECONDS,
                autocommit=True,
            )
        except psycopg.OperationalError as exc:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                reason = redact(str(exc), [settings.db_password]).strip()
                raise DatabaseUnavailableError(
                    f"could not connect to postgres at {settings.db_host}:{settings.db_port} "
                    f"within {timeout}s: {reason}"
                ) from None
        time.sleep(min(interval, remaining))


def ensure_schema(conn: psycopg.Connection) -> None:
    conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))


def mark_abandoned(conn: psycopg.Connection, hours: int) -> int:
    """Fail RUNNING executions started more than ``hours`` ago; return how many."""
    cursor = conn.execute(
        "UPDATE executions SET status = 'FAILED', finished_at = now(), error = 'abandoned' "
        "WHERE status = 'RUNNING' AND started_at < now() - make_interval(hours => %s)",
        (hours,),
    )
    return cursor.rowcount


def start_execution(conn: psycopg.Connection) -> int:
    row = conn.execute("INSERT INTO executions (status) VALUES ('RUNNING') RETURNING id").fetchone()
    return row[0]


def save_success(conn: psycopg.Connection, exec_id: int, items: Sequence[BookItem]) -> None:
    """Upsert books, add price rows and mark the execution SUCCESS in one transaction."""
    params = [
        (item.url, item.title, item.category, exec_id, item.price, item.availability)
        for item in items
    ]
    with conn.transaction():
        conn.cursor().executemany(UPSERT_BOOK_AND_PRICE, params)
        conn.execute(
            "UPDATE executions SET status = 'SUCCESS', finished_at = now(), items_count = %s "
            "WHERE id = %s",
            (len(items), exec_id),
        )


def mark_failed(conn: psycopg.Connection, exec_id: int, error: str) -> None:
    conn.execute(
        "UPDATE executions SET status = 'FAILED', finished_at = now(), error = %s WHERE id = %s",
        (error[:MAX_ERROR_LENGTH], exec_id),
    )
