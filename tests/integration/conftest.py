"""Integration fixtures: an isolated Compose project with its own Postgres and volume.

The project name (``bookmonitor_it``) and a random published port keep these tests away from
the development stack (``pgdata`` volume, port 5432). The stack is removed with ``down -v``
at the end of the session.
"""

import os
import socket
import subprocess
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest

ROOT = Path(__file__).resolve().parents[2]
PROJECT = "bookmonitor_it"
DB_NAME = "books_it"
DB_USER = "books_it"
DB_PASSWORD = "integration-test-password"
SCHEMA_SQL = ROOT / "src" / "book_monitor" / "schema.sql"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="session")
def pg_env(tmp_path_factory: pytest.TempPathFactory) -> Iterator[dict[str, str]]:
    """Start the isolated Postgres and yield the DB_* variables that reach it."""
    port = _free_port()
    override = tmp_path_factory.mktemp("compose") / "override.yml"
    override.write_text(
        f'services:\n  postgres:\n    ports:\n      - "127.0.0.1:{port}:5432"\n',
        encoding="utf-8",
    )
    env = {
        **os.environ,
        "COMPOSE_PROJECT_NAME": PROJECT,
        "DB_NAME": DB_NAME,
        "DB_USER": DB_USER,
        "DB_PASSWORD": DB_PASSWORD,
    }

    def compose(*args: str) -> None:
        # -f explicit: never loads the developer's docker-compose.override.yml
        subprocess.run(
            ["docker", "compose", "-f", "docker-compose.yml", "-f", str(override), *args],
            cwd=ROOT,
            env=env,
            check=True,
            capture_output=True,
            timeout=600,
        )

    compose("up", "-d", "--wait", "postgres")
    try:
        yield {
            "DB_HOST": "127.0.0.1",
            "DB_PORT": str(port),
            "DB_NAME": DB_NAME,
            "DB_USER": DB_USER,
            "DB_PASSWORD": DB_PASSWORD,
        }
    finally:
        compose("down", "-v", "--remove-orphans")


@pytest.fixture
def conn(pg_env: dict[str, str]) -> Iterator[psycopg.Connection]:
    """Autocommit connection to an empty database (schema dropped before each test)."""
    with psycopg.connect(
        host=pg_env["DB_HOST"],
        port=int(pg_env["DB_PORT"]),
        dbname=pg_env["DB_NAME"],
        user=pg_env["DB_USER"],
        password=pg_env["DB_PASSWORD"],
        autocommit=True,
    ) as connection:
        connection.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public")
        yield connection


@pytest.fixture(scope="session")
def schema_sql() -> str:
    return SCHEMA_SQL.read_text(encoding="utf-8")
