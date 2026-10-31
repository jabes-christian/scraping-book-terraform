import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.docker

ROOT = Path(__file__).resolve().parents[2]
PROJECT = "bookmonitor_test"
MB = 1024 * 1024
ENV = {
    **os.environ,
    "COMPOSE_PROJECT_NAME": PROJECT,
    "DB_NAME": "books_test",
    "DB_USER": "books_test",
    "DB_PASSWORD": "compose-test-password",
}


def _compose(*args: str, timeout: int = 300) -> str:
    result = subprocess.run(
        ["docker", "compose", *args],
        cwd=ROOT,
        env=ENV,
        capture_output=True,
        text=True,
        check=True,
        timeout=timeout,
    )
    return result.stdout.strip()


def _psql(sql: str) -> str:
    return _compose(
        "exec", "-T", "postgres", "psql", "-U", "books_test", "-d", "books_test", "-tA", "-c", sql
    )


@pytest.fixture(scope="module")
def config() -> dict:
    return json.loads(_compose("config", "--format", "json"))


@pytest.fixture(scope="module")
def stack():
    yield
    _compose("down", "-v", "--remove-orphans")


def test_postgres_data_lives_in_a_named_volume(config):
    volumes = config["services"]["postgres"]["volumes"]
    mounts = {v["target"]: v for v in volumes}
    mount = mounts["/var/lib/postgresql/data"]
    assert (mount["type"], mount["source"]) == ("volume", "pgdata")
    assert "pgdata" in config["volumes"]


def test_postgres_restarts_unless_stopped(config):
    assert config["services"]["postgres"]["restart"] == "unless-stopped"


def test_memory_limits_fit_an_e2_micro(config):
    # `docker compose config` renders mem_limit as a string of bytes.
    limits = [int(config["services"][name]["mem_limit"]) for name in ("postgres", "robo")]
    assert limits == [192 * MB, 560 * MB]
    assert sum(limits) <= 752 * MB


def test_postgres_has_a_pg_isready_healthcheck(config):
    healthcheck = config["services"]["postgres"]["healthcheck"]
    assert "pg_isready" in " ".join(healthcheck["test"])


def test_postgres_publishes_no_ports(config):
    assert "ports" not in config["services"]["postgres"]


def test_robo_waits_for_a_healthy_postgres(config):
    robo = config["services"]["robo"]
    assert robo["depends_on"]["postgres"]["condition"] == "service_healthy"
    assert robo["init"] is True
    assert robo["restart"] == "no"
    assert robo["environment"]["DB_HOST"] == "postgres"


def test_postgres_runs_with_the_low_memory_tuning(config):
    command = " ".join(config["services"]["postgres"]["command"])
    for setting in ("shared_buffers=32MB", "max_connections=10", "work_mem=2MB"):
        assert setting in command


def test_data_survives_recreating_the_postgres_container(stack):
    _compose("up", "-d", "--wait", "postgres", timeout=600)
    _psql("CREATE TABLE persistence_check (id int); INSERT INTO persistence_check VALUES (42);")
    _compose("up", "-d", "--wait", "--force-recreate", "postgres", timeout=600)
    assert _psql("SELECT id FROM persistence_check") == "42"
