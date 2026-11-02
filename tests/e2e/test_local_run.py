"""End-to-end: two full runs of the robot through Compose against the real site.

Uses an isolated Compose project (own network and ``pgdata`` volume), so the development
volume is never touched. Credentials come from the local ``.env`` (the same file the ``robo``
service reads through ``env_file``). Run with ``-s`` to see the duration/memory report.

``E2E_BASE_URL`` (optional) is passed to the robot as ``BASE_URL``; without it the robot uses
its default (the site over HTTPS). Set it to the ``http://`` URL on networks that intercept TLS.
"""

import json
import os
import re
import subprocess
import threading
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e

ROOT = Path(__file__).resolve().parents[2]
PROJECT = "bookmonitor_e2e"
EXPECTED_ITEMS = 1000
BASE_URL = os.environ.get("E2E_BASE_URL")
UNITS = {"B": 1, "KIB": 1024, "MIB": 1024**2, "GIB": 1024**3, "KB": 1000, "MB": 1000**2}


def _dotenv() -> dict[str, str]:
    path = ROOT / ".env"
    assert path.exists(), ".env local ausente: copie .env.example para .env"
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


DOTENV = _dotenv()
# DB_* come from .env (compose interpolation and the robo env_file); drop any host override.
ENV = {
    **{k: v for k, v in os.environ.items() if not k.startswith("DB_")},
    "COMPOSE_PROJECT_NAME": PROJECT,
}


def _run(args: list[str], timeout: int, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        args, cwd=ROOT, env=ENV, capture_output=True, text=True, check=check, timeout=timeout
    )


def _compose(*args: str, timeout: int = 600, check: bool = True) -> subprocess.CompletedProcess:
    # -f explicit: never loads the developer's docker-compose.override.yml
    return _run(["docker", "compose", "-f", "docker-compose.yml", *args], timeout, check)


def _psql(sql: str) -> str:
    result = _compose(
        "exec", "-T", "postgres", "psql", "-U", DOTENV["DB_USER"], "-d", DOTENV["DB_NAME"],
        "-tA", "-c", sql,
    )  # fmt: skip
    return result.stdout.strip()


def _counts() -> dict[str, int]:
    return {
        table: int(_psql(f"SELECT count(*) FROM {table}"))
        for table in ("executions", "books", "price_history")
    }


def _to_bytes(text: str) -> int:
    match = re.match(r"\s*([\d.]+)\s*([A-Za-z]+)", text)
    return int(float(match.group(1)) * UNITS[match.group(2).upper()])


def _service(container: str) -> str:
    return "robo" if "-robo-" in container else "postgres"


class MemorySampler(threading.Thread):
    """Samples ``docker stats`` and the cgroup peak of every container of the project."""

    def __init__(self) -> None:
        super().__init__(daemon=True)
        self._stop_event = threading.Event()
        self.stats_peak = {"robo": 0, "postgres": 0}
        self.cgroup_peak = {"robo": 0, "postgres": 0}

    def stop(self) -> None:
        self._stop_event.set()
        self.join(timeout=60)

    def run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._sample()
            except Exception:  # sampling must never break the run
                pass
            self._stop_event.wait(0.5)

    def _sample(self) -> None:
        names = _run(
            ["docker", "ps", "--filter", f"label=com.docker.compose.project={PROJECT}",
             "--format", "{{.Names}}"],
            30,
        ).stdout.split()  # fmt: skip
        if not names:
            return
        stats = _run(
            ["docker", "stats", "--no-stream", "--format", "{{.Name}}|{{.MemUsage}}", *names],
            60,
            check=False,
        ).stdout
        for line in stats.splitlines():
            name, usage = line.split("|", 1)
            service = _service(name)
            self.stats_peak[service] = max(
                self.stats_peak[service], _to_bytes(usage.split("/")[0])
            )
        for name in names:
            peak = _run(
                ["docker", "exec", name, "sh", "-c",
                 "cat /sys/fs/cgroup/memory.peak 2>/dev/null"
                 " || cat /sys/fs/cgroup/memory/memory.max_usage_in_bytes"],
                30,
                check=False,
            ).stdout.strip()  # fmt: skip
            if peak.isdigit():
                service = _service(name)
                self.cgroup_peak[service] = max(self.cgroup_peak[service], int(peak))


def _mib(value: int) -> float:
    return round(value / 1024**2, 1)


@pytest.fixture(scope="module")
def runs():
    """Start the isolated stack, run the robot twice and measure duration and memory."""
    _compose("build", "robo", timeout=1200)
    _compose("up", "-d", "--wait", "postgres", timeout=600)
    sampler = MemorySampler()
    results = []
    try:
        sampler.start()
        for _ in range(2):
            started = time.monotonic()
            env_args = ["-e", f"BASE_URL={BASE_URL}"] if BASE_URL else []
            process = _compose("run", "--rm", "-T", *env_args, "robo", timeout=3600, check=False)
            results.append(
                {
                    "exit_code": process.returncode,
                    "output": process.stdout + process.stderr,
                    "seconds": round(time.monotonic() - started, 1),
                }
            )
        sampler.stop()
        report = {
            "durations_seconds": [r["seconds"] for r in results],
            "peak_mib_docker_stats": {k: _mib(v) for k, v in sampler.stats_peak.items()},
            "peak_mib_cgroup_incl_cache": {k: _mib(v) for k, v in sampler.cgroup_peak.items()},
        }
        print("\nE2E_RESOURCE_REPORT " + json.dumps(report))
        yield results
    finally:
        sampler.stop()
        _compose("down", "-v", "--remove-orphans", check=False)


def test_two_runs_succeed_and_persist_1000_books_each(runs):  # LOC-01, LOC-02, LOC-06, SCR-09
    assert [r["exit_code"] for r in runs] == [0, 0], [r["output"][-2000:] for r in runs]

    rows = _psql(
        "SELECT status || ':' || items_count FROM executions ORDER BY id"
    ).splitlines()
    assert rows == [f"SUCCESS:{EXPECTED_ITEMS}"] * 2
    assert _counts() == {
        "executions": 2,
        "books": EXPECTED_ITEMS,
        "price_history": 2 * EXPECTED_ITEMS,
    }


def test_the_database_password_never_appears_in_the_run_output(runs):  # CFG-03
    password = DOTENV["DB_PASSWORD"]
    assert password
    assert all(password not in r["output"] for r in runs)


def test_counts_survive_recreating_the_postgres_container(runs):  # DB-08
    before = _counts()
    _compose("up", "-d", "--wait", "--force-recreate", "postgres", timeout=600)
    assert _counts() == before == {
        "executions": 2,
        "books": EXPECTED_ITEMS,
        "price_history": 2 * EXPECTED_ITEMS,
    }
